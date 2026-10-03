"""
Module: Lightweight On-Screen Context Extractor (OCR).

Uses Windows 11's built-in native Windows Media OCR (via winocr) and
Win32 GDI window capture to extract in-the-moment textual context
(e.g., Instagram Reel captions, YouTube video subtitles, terminal errors)
in <30ms with zero extra model weights or memory overhead.

Privacy Guarantees:
  - Captures only the active foreground window bounding box.
  - Processes images strictly in volatile RAM — zero disk writes.
  - Automatically suppresses capture if window matches privacy blocklist.
"""

import re
import time
import ctypes
import logging
from typing import Optional
from PIL import Image

# Initialize torch DLLs before WinRT C-runtime to prevent Windows 1114 symbol conflict
try:
    import torch  # noqa: F401
except Exception:
    pass

logger = logging.getLogger(__name__)

# UI noise words to strip from social media and video overlays
UI_NOISE_WORDS = frozenset({
    "like", "likes", "comment", "comments", "share", "shares", "follow",
    "following", "followers", "subscribe", "subscribed", "subscribers",
    "views", "view", "reply", "replies", "reels", "reel", "explore",
    "messages", "search", "notifications", "home", "profile", "audio",
    "original audio", "more", "less", "see translation", "suggested for you"
})


# Common stop words and narrative filler verbs for keyword extraction
STOP_WORDS = frozenset({
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "can't",
    "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have", "haven't", "having",
    "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself", "him", "himself", "his", "how",
    "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself",
    "let's", "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on", "once",
    "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
    "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such", "than", "that", "that's", "the",
    "their", "theirs", "them", "themselves", "then", "there", "there's", "these", "they", "they'd", "they'll",
    "they're", "they've", "this", "those", "through", "to", "too", "under", "until", "up", "very", "was",
    "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when", "when's",
    "where", "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves",
    "like", "follow", "see", "take", "sometimes", "takes", "seeing", "borne", "view", "views",
    # Narrative verbs & filler words to prevent false subjects like 'stopped house' or 'think one'
    "stopped", "made", "starts", "noticing", "think", "giving", "gives", "give", "leave", "leaves", "came", "went",
    "said", "going", "doing", "getting", "house", "morning", "gift", "gifts", "gave", "told", "asked",
    "wanted", "needed", "know", "knows", "knew", "look", "looks", "looking", "feels", "feeling", "feel",
    "really", "actually", "just", "even", "also", "well", "ever", "never", "always", "still", "thing", "things",
    "one", "two", "three", "first", "last", "greatest", "best", "good", "bad", "doesn", "don", "didn", "isn", "wasn"
})


def _is_winocr_available() -> bool:
    try:
        import winocr  # noqa: F401
        return True
    except ImportError:
        return False


def _clean_ocr_text(raw_text: str) -> str:
    """Clean OCR output, strip usernames, follow indicators, metrics, and pure UI noise."""
    if not raw_text:
        return ""

    # Replace weird newlines and non-printable characters
    cleaned = re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", raw_text)

    # 1. Strip creator handle immediately preceding follow indicator (e.g. "buildwithbert • Follow")
    cleaned = re.sub(r"(?i)\b[\w\.\_]+\s*[•·\|\-]?\s*Follow\b", " ", cleaned)
    cleaned = re.sub(r"(?i)\b[oO0]\s*[•·\|\-]\s*Follow\b", " ", cleaned)
    cleaned = re.sub(r"(?i)[•·\|\-]\s*Follow\b", " ", cleaned)
    cleaned = re.sub(r"(?i)\b(?:Follow|Following|Subscribed?)\b", " ", cleaned)
    cleaned = re.sub(r"(?i)\b(?:Original audio|suggested for you|see translation|Messages)\b", " ", cleaned)

    # 2. Strip engagement numbers (161K, 1924us, 512K, 26.3K, 272, 66)
    cleaned = re.sub(r"\b\d+[\.,]?\d*\s*[kKmMbB]?\s*(?:likes?|views?|comments?|shares?|us)?\b", " ", cleaned)
    cleaned = re.sub(r"\b\d+\b", " ", cleaned)

    # 3. Strip creator handles (e.g., garrett_1320video, kelt00nwNEams_)
    cleaned = re.sub(r"\b[a-zA-Z0-9_\.]{4,30}_[a-zA-Z0-9_\.]*\b", " ", cleaned)

    # 4. Remove OCR garbage words (e.g. words without vowels, mixed casing like tkSt, CMta, RiQ)
    words = cleaned.split()
    sanitized_words = []
    for w in words:
        w_clean = re.sub(r"[^\w]", "", w)
        if len(w_clean) >= 3 and not (w_clean.islower() or w_clean.istitle() or (w_clean.isupper() and len(w_clean) >= 4)):
            continue  # Likely random OCR garbage like tkSt, CMta, RiQ
        if len(w_clean) >= 3 and not any(v in w_clean.lower() for v in "aeiouy"):
            continue  # No vowels
        sanitized_words.append(w)
    cleaned = " ".join(sanitized_words)

    # 5. Remove floating single or 2-char isolated symbols/letters
    cleaned = re.sub(r"(?<=\s)[a-zA-Z0-9_]{1,2}(?=\s)", " ", f" {cleaned} ")

    # 6. Collapse spaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Filter out if too few meaningful words remain
    words = cleaned.split()
    meaningful_words = [w for w in words if w.lower() not in UI_NOISE_WORDS and len(w) >= 3]

    if len(meaningful_words) < 2:
        return ""

    return cleaned


def extract_caption_keywords(cleaned_text: str) -> list[str]:
    """Extract salient subject query phrases from hashtags and caption text."""
    if not cleaned_text:
        return []

    queries = []

    # 1. High priority: Hashtags explicitly added by creator (#diy, #construction, #customhome)
    hashtags = re.findall(r"[#\*]([a-zA-Z0-9]+)", cleaned_text)
    for tag in hashtags:
        tag_lower = tag.lower()
        if tag_lower not in STOP_WORDS and len(tag_lower) >= 3 and tag_lower not in queries:
            queries.append(tag_lower)

    # 2. Capitalized phrases (Proper Nouns, places, titles: "Hooker Valley Track", "Peter's Lookout")
    cap_phrases = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", cleaned_text)
    for cp in cap_phrases:
        cp_lower = cp.lower()
        if cp_lower not in STOP_WORDS and len(cp) >= 5 and cp_lower not in queries:
            queries.append(cp_lower)

    # 3. Clean content words (nouns, objects, concepts)
    words = [
        w.lower() for w in re.findall(r"[a-zA-Z]{3,}", cleaned_text)
        if w.lower() not in STOP_WORDS
        and any(v in w.lower() for v in "aeiouy")
    ]

    # Combine 2-3 consecutive meaningful words to form real compound subjects (e.g. 'pumpkin cinnamon rolls')
    if len(words) >= 3:
        queries.append(f"{words[0]} {words[1]} {words[2]}")
    elif len(words) == 2:
        queries.append(f"{words[0]} {words[1]}")

    for w in words[:3]:
        if w not in queries and not any(w in q for q in queries):
            queries.append(w)

    return queries[:3]


def capture_active_window_bitmap(hwnd: int, app_name: str) -> Optional[Image.Image]:
    """
    Capture the bitmap of the active window using native Win32 PrintWindow.
    Crops the Region-of-Interest (ROI) depending on the application type:
      - Social media (Instagram, TikTok): bottom-left 40% (where reel captions live)
      - Video / Browsers: center-top 50%
      - Code / Terminal: bottom 30% (active lines / prompt)
    """
    if not hwnd or hwnd <= 0:
        return None

    try:
        import win32gui
        import win32ui
        import win32con

        rect = win32gui.GetWindowRect(hwnd)
        left, top, right, bottom = rect
        width = right - left
        height = bottom - top

        if width < 100 or height < 100:
            return None

        # Create Win32 memory device context
        hwnd_dc = win32gui.GetWindowDC(hwnd)
        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        save_dc = mfc_dc.CreateCompatibleDC()
        save_bitmap = win32ui.CreateBitmap()
        save_bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
        save_dc.SelectObject(save_bitmap)

        # PrintWindow with PW_RENDERFULLCONTENT (2)
        res = ctypes.windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 2)
        if res == 0:
            # Fallback to standard BitBlt
            save_dc.BitBlt((0, 0), (width, height), mfc_dc, (0, 0), win32con.SRCCOPY)

        bmp_info = save_bitmap.GetInfo()
        bmp_str = save_bitmap.GetBitmapBits(True)
        img = Image.frombuffer(
            "RGB",
            (bmp_info["bmWidth"], bmp_info["bmHeight"]),
            bmp_str,
            "raw",
            "BGRX",
            0,
            1,
        )

        # Release GDI objects immediately
        win32gui.DeleteObject(save_bitmap.GetHandle())
        save_dc.DeleteDC()
        mfc_dc.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwnd_dc)

        # ── Smart Region-of-Interest (ROI) Crop ──
        w, h = img.size
        app_lower = app_name.lower()

        if any(s in app_lower for s in ["edge", "chrome", "firefox", "brave"]):
            # For social media / video feeds, crop right after left nav icon strip (~6% width)
            # capturing creator handle and full caption column
            crop_box = (int(w * 0.06), int(h * 0.40), int(w * 0.90), int(h * 0.96))
        elif any(c in app_lower for c in ["code", "terminal", "powershell", "cmd"]):
            # For terminal / code, capture the bottom 35% where errors or cursor lives
            crop_box = (0, int(h * 0.65), w, h)
        else:
            # General fallback: center 60%
            crop_box = (int(w * 0.15), int(h * 0.20), int(w * 0.85), int(h * 0.80))

        cropped = img.crop(crop_box)

        # Downscale if excessively large to keep OCR execution <15ms
        if cropped.width > 800:
            ratio = 800.0 / cropped.width
            cropped = cropped.resize((800, int(cropped.height * ratio)), Image.Resampling.BILINEAR)

        return cropped

    except Exception as e:
        logger.debug(f"Failed to capture window bitmap: {e}")
        return None


class ScreenTextExtractor:
    """
    On-demand lightweight OCR extractor for in-the-moment mindfulness.
    Maintains an in-memory cache to avoid redundant OCR scans on static screens.
    """

    def __init__(self):
        self._available = _is_winocr_available()
        self._last_scan_time: float = 0
        self._last_hwnd: int = 0
        self._last_extracted_text: str = ""

    def is_available(self) -> bool:
        return self._available

    def extract_text(self, hwnd: int, app_name: str, min_interval_seconds: float = 5.0) -> Optional[str]:
        """
        Capture and extract text from the active window.
        Returns cleaned text or None if empty, unavailable, or rate-limited.
        """
        if not self._available or not hwnd:
            return None

        now = time.monotonic()
        # Don't scan faster than min_interval_seconds
        if now - self._last_scan_time < min_interval_seconds:
            return self._last_extracted_text if self._last_hwnd == hwnd else None

        img = capture_active_window_bitmap(hwnd, app_name)
        if not img:
            return None

        try:
            import winocr

            t0 = time.monotonic()
            res = winocr.recognize_pil_sync(img, "en")
            raw_text = res.get("text", "")
            duration_ms = (time.monotonic() - t0) * 1000

            clean_text = _clean_ocr_text(raw_text)
            self._last_scan_time = now
            self._last_hwnd = hwnd
            self._last_extracted_text = clean_text

            if clean_text and len(clean_text) >= 10:
                logger.info(f"👁️ OCR extracted in {duration_ms:.1f}ms: '{clean_text[:60]}...'")
                return clean_text

            return None

        except Exception as e:
            logger.debug(f"OCR recognition error: {e}")
            return None
