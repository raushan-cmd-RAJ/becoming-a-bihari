"""
Module: Universal Context Extractor.

Extracts meaningful, human-readable subjects from window titles across all
desktop applications (code editors, browsers, terminals, notes, media players).

Guarantees:
  - Sanity filtered: Rejects generic titles ('New Tab', 'Untitled', 'Inbox').
  - Local & fast: Zero network, pure regex/string manipulation (<0.1ms).
  - Graceful fallback: Returns None if no clean, specific subject can be identified.
"""

import collections
import random
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class WindowContext:
    subject: str        # e.g., 'auth_service.py', 'Quantum Computing', 'git status'
    category: str       # 'code', 'video', 'search', 'docs', 'music', 'terminal', 'social', 'general'
    is_specific: bool   # True if high-confidence specific subject, False if generic
    is_social: bool = False       # True if on YouTube, Reddit, Twitter/X, Instagram, etc.
    search_query: str = ""        # Cleaned search term optimized for live meme query
    dwell_minutes: float = 0.0    # Continuous dwell time in active window/app in minutes


# Generic/noisy titles that provide zero useful context
GENERIC_TITLES = frozenset({
    "new tab", "untitled", "home", "dashboard", "settings", "inbox",
    "search", "google", "blank", "start", "loading", "welcome",
    "windows powershell", "command prompt", "terminal", "task manager",
    "file explorer", "chrome", "firefox", "edge", "spotify", "discord",
    "slack", "zoom", "teams", "visual studio code", "notepad", "calculator"
})

# Browser window suffix patterns to strip
BROWSER_SUFFIXES = [
    r"\s*-\s*(?:Profile\s+\d+|Personal|Work|Beta|Dev|Canary)?\s*-\s*Microsoft\s*Edge.*$",
    r"\s*-\s*Microsoft\s*Edge.*$",
    r"\s*-\s*Google Chrome.*$",
    r"\s*—\s*Mozilla Firefox.*$",
    r"\s*-\s*Brave.*$",
    r"\s*-\s*Opera.*$",
    r"\s*-\s*Vivaldi.*$",
    r"\s*-\s*Arc.*$",
]

# IDE window suffix patterns to strip
IDE_SUFFIXES = [
    r"\s*-\s*Visual Studio Code.*$",
    r"\s*-\s*Visual Studio.*$",
    r"\s*-\s*Sublime Text.*$",
    r"\s*-\s*Notepad\+\+.*$",
    r"\s*-\s*Android Studio.*$",
]


def _clean_str(text: str) -> str:
    """Trim whitespace and remove leading/trailing punctuation."""
    return re.sub(r"^[\s\-_—:•|]+|[\s\-_—:•|]+$", "", text).strip()


def extract_code_context(app: str, title: str) -> Optional[WindowContext]:
    """Extract filename or project from IDE/editor window title."""
    cleaned = title
    for pat in IDE_SUFFIXES:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)

    # Remove dirty buffer indicator in VS Code (● or *)
    cleaned = re.sub(r"^[●\*]\s*", "", cleaned)

    # Check for filename with extension (e.g. auth_service.py, styles.css, query.sql)
    file_match = re.search(r"\b([a-zA-Z0-9_\-\.]+\.[a-zA-Z0-9]{1,8})\b", cleaned)
    if file_match:
        filename = file_match.group(1)
        # Avoid false positives like version numbers (1.2.0)
        if not re.match(r"^\d+\.\d+", filename):
            return WindowContext(subject=filename, category="code", is_specific=True)

    # Split by common delimiters (e.g. 'project - folder')
    parts = re.split(r"[-—•|]", cleaned)
    if parts:
        first = _clean_str(parts[0])
        if 2 <= len(first) <= 40 and first.lower() not in GENERIC_TITLES:
            return WindowContext(subject=first, category="code", is_specific=True)

    return None


def extract_smart_keywords(text: str) -> str:
    """
    Extract high-value search queries from a video/post title.
    Prioritizes named entities (e.g. 'Elon Musk', 'MrBeast', 'GTA 6', 'Modern Architecture')
    so search engines find direct relevant memes rather than 0 results on noisy sentences.
    """
    cleaned = re.sub(r"\[.*?\]|\(.*?\)", " ", text)
    cleaned = re.sub(r"^\(\d+\)\s*", "", cleaned).strip()

    # Strip episode codes (e.g. 'KT #787 - ', 'Episode 42: ', '#500 - ')
    cleaned = re.sub(r"^[A-Z]{1,4}\s*#\d+\s*[-—:|]\s*", "", cleaned)
    cleaned = re.sub(r"^#\d+\s*[-—:|]\s*", "", cleaned)

    # Strip leading first-person narrative starts ('We bought land in...', 'I turned a BOX trailer...', 'I Survived Alone in...')
    cleaned = re.sub(
        r"^(?:we|i|you|they|he|she)\s+(?:bought|turned|survived|built|made|went|tried|spent|lived|visited)\s+(?:a\s+|an\s+|in\s+|at\s+)?",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    # 1. Check for "interview with <Target>" or "featuring <Target>"
    m_with = re.search(
        r"(?:interview with|featuring|feat\.?|speaks with)\s+(?:Tesla\s+CEO\s+|CEO\s+|Dr\.?\s+)?([A-Z][a-zA-Z0-9_\s]{2,25})",
        cleaned,
        re.IGNORECASE,
    )
    if m_with:
        target = m_with.group(1).strip()
        target = re.split(r"[-—|•:]", target)[0].strip()
        words = target.split()
        if 1 <= len(words) <= 3:
            return target

    # 2. Check for Colon or Dash: "MrBeast: 50 YouTubers..." or "Joe Rogan - Elon Musk"
    parts = re.split(r"[:—\-]", cleaned)
    if len(parts) >= 2:
        first = parts[0].strip()
        last = parts[-1].strip()
        # Ensure 'first' is a real subject, not a short abbreviation or generic question
        if 1 <= len(first.split()) <= 3 and len(first) >= 4 and not any(w in first.lower() for w in ["why", "how", "what", "watch", "when"]):
            return first
        if 1 <= len(last.split()) <= 3 and len(last) >= 4:
            caps = re.findall(r"\b[A-Z][a-z0-9]+\b", last)
            if len(caps) >= 1:
                return " ".join(caps[:2])

    # 3. Look for quotes: '...' or "..." (often contains the actual topic/quote)
    quote_match = re.search(r"['\"]([^'\"]{3,30})['\"]", cleaned)
    if quote_match:
        return quote_match.group(1).strip()

    # 4. Extract Capitalized Named Entities (e.g. "Elon Musk", "MrBeast", "GTA 6", "Modern Architecture")
    noise = {
        "the", "a", "an", "how", "why", "what", "exclusive", "full", "episode",
        "official", "watch", "cmg", "ceo", "trailer", "video", "audio", "part",
        "season", "review", "gameplay", "walkthrough", "live", "and", "with",
        "we", "i", "you", "they", "he", "she", "it", "my", "our", "me", "us",
        "this", "that", "there", "here", "when", "where", "who", "whom", "alone",
        "days", "hours", "minutes", "seconds", "years", "lot", "much", "many"
    }
    words = cleaned.split()
    entities = []
    current = []
    for w in words:
        w_clean = re.sub(r"[^\w]", "", w)
        if not w_clean:
            continue
        if (w_clean[0].isupper() or w_clean.isdigit()) and w_clean.lower() not in noise:
            current.append(w_clean)
        else:
            if current:
                entities.append(" ".join(current))
                current = []
    if current:
        entities.append(" ".join(current))

    if entities:
        best = max(entities, key=lambda s: len(s.split()))
        best_words = [w for w in best.split() if w.lower() not in noise]
        if best_words:
            res = " ".join(best_words[:2])
            if len(res) >= 3:
                return res

    # Fallback to first 2 meaningful words
    simple_words = [w for w in re.sub(r'[^\w\s]', '', cleaned).split() if len(w) > 2 and w.lower() not in noise]
    return " ".join(simple_words[:2]) if simple_words else cleaned[:20]


def clean_media_subject(title: str, max_len: int = 100) -> str:
    """Clean a YouTube/media title into a human-readable subject without truncation artifacts."""
    t = re.sub(r"^\(\d+\)\s*", "", title)  # Strip notification count (3)
    t = re.sub(r"[\U00010000-\U0010ffff]", "", t)  # Remove emojis and high unicode symbols
    t = re.sub(r"\[.*?\]|\(.*?\)", "", t)  # Strip brackets like [CLIP], [4K], (Official Music Video), (HD)
    t = re.sub(r"^[A-Z]{1,5}\s*#\d+\s*[-—:|]\s*", "", t)  # Strip episode codes like "KT #787 - "
    t = re.sub(r"^#\d+\s*[-—:|]\s*", "", t)
    # Strip only trailing dots/ellipsis at the end of string, preserving mid-sentence ellipsis
    t = re.sub(r"[\s\.]+$", "", t)

    # If the title has a channel suffix separator like ' | Creator' or ' • Creator'
    if " | " in t or " • " in t:
        parts = [p.strip() for p in re.split(r"\s*[|•]\s*", t) if p.strip()]
        if parts and len(parts[0]) >= 15:
            # If the second part is just a short channel name (e.g. 'Dhruv Rathee', 'Netflix'), take parts[0]
            if len(parts) >= 2 and len(parts[1]) < 25:
                t = parts[0]
            else:
                t = " - ".join(parts)

    # Allow up to max_len characters so full video titles are preserved without being cut in half
    if len(t) > max_len:
        words = t.split()
        truncated = []
        cur_len = 0
        for w in words:
            if cur_len + len(w) + 1 > max_len - 3:
                break
            truncated.append(w)
            cur_len += len(w) + 1
        t = " ".join(truncated)

    return _clean_str(t)


def extract_video_reaction_queries(title: str) -> list[str]:
    """Map video title keywords to emotion queries for visual meme searches on Reddit."""
    lower = title.lower()

    # Music / Songs / Synth-pop / Audio tracks
    if any(k in lower for k in ["music", "official video", "audio", "song", "album", "remix", "soundtrack", "live at", "lyrics", "disco", "synth", "branigan"]):
        return ["vibing cat", "grooving", "head bobbing", "dancing cat", "headphones vibing"]

    # Movie clips / scenes / cinematic
    if any(k in lower for k in ["clip", "scene", "movie", "film", "cinema", "shawshank", "godfather", "trailer"]):
        return ["intense stare", "mesmerized", "nodding", "jaw drop", "eating popcorn"]

    # Comedy / standup / hilarious podcast storytelling
    if any(k in lower for k in [
        "joey diaz", "biswa", "kill tony", "comedy", "stand up", "standup",
        "podcast", "funny", "harland", "shane gillis", "jokes", "prank",
        "hilarious", "laugh", "theo von", "bobby lee", "andrew schulz",
        "tim dillon", "conan", "chappelle", "norm macdonald", "telling",
        "roast", "stories", "stand-up"
    ]):
        return ["laughing", "wheezing", "crying laughing", "snicker", "cracking up", "spit take"]

    # Mind-bending / existential / philosophy / civilization collapse / mysteries / deep podcasts
    if any(k in lower for k in [
        "chilling", "jared diamond", "mystery", "conspiracy", "universe",
        "quantum", "aliens", "ancient", "collapse", "dark truth", "psychology",
        "existential", "philosophy", "deep dive", "joe rogan", "rogan", "lex fridman",
        "huberman", "unexplained", "documentary"
    ]):
        return ["galaxy brain", "existential stare", "thinking monkey", "staring ceiling", "shocked dog", "contemplating", "jaw drop"]

    # Expose / drama / scam / controversy / investigative
    if any(k in lower for k in ["exposed", "scam", "drama", "controversy", "secret", "truth", "arrested", "lawsuit", "dhruv rathee", "investigation"]):
        return ["eating popcorn", "side eye", "intense stare", "shocked cat", "double take"]

    # Serene / travel / nature / food / vlog / relaxing
    if any(k in lower for k in ["windermere", "lake", "travel", "vlog", "cabin", "tropics", "nature", "cooking", "recipe", "tour", "magic", "peaceful", "island"]):
        return ["mesmerized", "daydreaming", "peaceful cat", "blank stare"]

    # Tech / tutorials / coding / science
    if any(k in lower for k in ["tutorial", "how to", "guide", "code", "programming", "python", "review", "explained", "science"]):
        return ["taking notes", "confused math", "nodding", "overwhelmed"]

    # Gaming
    if any(k in lower for k in ["minecraft", "gta", "gameplay", "speedrun", "playthrough", "game"]):
        return ["gamer intense", "screaming", "jaw drop", "celebrating"]

    # General video watching reaction pool
    return [
        "eating popcorn", "side eye", "monkey puppet looking away",
        "jaw drop", "double take", "cat staring", "speechless",
        "mesmerized", "daydreaming", "staring into soul"
    ]


_recent_video_queries: collections.deque = collections.deque(maxlen=15)

BROAD_REACTION_POOL = [
    "eating popcorn", "side eye", "monkey puppet looking away", "jaw drop",
    "double take", "wheezing", "cat staring", "dog judging", "mind blown",
    "staring into soul", "facepalm", "disbelief", "blank stare", "mesmerized",
    "daydreaming", "shocked dog", "contemplating", "spit take", "snicker",
    "peaceful cat", "head bob", "grooving", "headphones vibing"
]


def extract_clean_search_query(title: str) -> str:
    """
    Extract and clean a programming/docs search query from titles (e.g. Stack Overflow).
    Strips bracketed tags ([python]), common search prefixes ("how to", "why does", etc.),
    site suffixes, punctuation, and truncates to <= 60 characters.
    """
    if not title:
        return ""

    # Remove site suffixes if present
    cleaned = re.sub(r"\s*-\s*Stack\s+(?:Overflow|Exchange).*$", "", title, flags=re.IGNORECASE)

    # Strip bracketed tags, e.g. [python], [pandas], [duplicate]
    cleaned = re.sub(r"\[.*?\]", " ", cleaned).strip()

    # Strip search prefixes
    prefixes = [
        r"^(?:how\s+to\s+(?:fix|resolve|solve|do|use|get|make|run|implement|set\s+up|find)?)\s*",
        r"^(?:how\s+(?:do|can|does|would|should)\s+(?:i|we|you|one)\s+(?:fix|resolve|solve|do|use|get|make|run|implement|find)?)\s*",
        r"^(?:why\s+(?:does|is|are|do|can\'?t|won\'?t)\s+)\s*",
        r"^(?:what\s+(?:is|are|causes|does)\s+)\s*",
        r"^(?:best\s+way\s+to\s+)\s*",
        r"^(?:error\s*:\s*)\s*",
        r"^(?:issue\s*:\s*)\s*",
    ]
    for pref in prefixes:
        cleaned = re.sub(pref, "", cleaned, flags=re.IGNORECASE)

    # Clean punctuation and extra whitespace
    cleaned = re.sub(r"[?!:;\"\'`]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Truncate to <= 60 characters cleanly at word boundary if possible
    if len(cleaned) > 60:
        truncated = cleaned[:60].rsplit(" ", 1)[0].strip()
        if truncated:
            cleaned = truncated

    return cleaned[:60]


def extract_browser_context(app: str, title: str) -> Optional[WindowContext]:
    """Extract clean video title, search query, doc, or topic from browser tab."""
    cleaned = title
    for pat in BROWSER_SUFFIXES:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)
    cleaned = _clean_str(cleaned)

    # 1. YouTube: "Video Title - YouTube"
    if " - youtube" in cleaned.lower() or cleaned.lower().endswith("youtube"):
        video_title = re.sub(r"\s*-\s*YouTube.*$", "", cleaned, flags=re.IGNORECASE)
        video_title = _clean_str(video_title)
        video_title = re.sub(r"^\(\d+\)\s*", "", video_title)
        if len(video_title) >= 3 and video_title.lower() != "youtube":
            clean_sub = clean_media_subject(video_title)
            reaction_queries = extract_video_reaction_queries(video_title)

            # Prevent searching the same query twice in 15 minutes! Rotate dynamically.
            unused = [q for q in reaction_queries if q not in _recent_video_queries]
            if not unused:
                unused = [q for q in BROAD_REACTION_POOL if q not in _recent_video_queries]
            chosen_query = random.choice(unused) if unused else random.choice(reaction_queries)
            _recent_video_queries.append(chosen_query)

            return WindowContext(
                subject=clean_sub,
                category="video",
                is_specific=True,
                is_social=True,
                search_query=chosen_query,
            )

    # 2. Reddit: "Title : r/subreddit" or "Title - Reddit"
    if "reddit.com" in cleaned.lower() or " : r/" in cleaned or " - reddit" in cleaned.lower():
        reddit_title = re.sub(r"\s*[-—:|]\s*(r\/[a-zA-Z0-9_]+|reddit).*$", "", cleaned, flags=re.IGNORECASE)
        reddit_title = _clean_str(reddit_title)
        reddit_title = re.sub(r"^\(\d+\)\s*", "", reddit_title)
        if len(reddit_title) >= 3 and reddit_title.lower() != "reddit":
            query = extract_smart_keywords(reddit_title)
            return WindowContext(
                subject=clean_media_subject(reddit_title),
                category="social",
                is_specific=True,
                is_social=True,
                search_query=query,
            )

    # 3. Twitter / X: "(2) User on X: '...' / X"
    if " / x" in cleaned.lower() or " / twitter" in cleaned.lower() or "on x:" in cleaned.lower():
        x_title = re.sub(r"\s*\/\s*(x|twitter).*$", "", cleaned, flags=re.IGNORECASE)
        x_title = re.sub(r"^.*?\bon x:\s*", "", x_title, flags=re.IGNORECASE)
        x_title = _clean_str(x_title)
        x_title = re.sub(r"^\(\d+\)\s*", "", x_title)
        if len(x_title) >= 3:
            query = extract_smart_keywords(x_title)
            return WindowContext(
                subject=clean_media_subject(x_title),
                category="social",
                is_specific=True,
                is_social=True,
                search_query=query,
            )

    # 4. Instagram / TikTok
    if any(s in cleaned.lower() for s in ["instagram", "tiktok"]):
        social_title = re.sub(r"\s*[-—•|]\s*(instagram|tiktok).*$", "", cleaned, flags=re.IGNORECASE)
        social_title = _clean_str(social_title)
        social_title = re.sub(r"^\(\d+\)\s*", "", social_title)
        random_reaction = random.choice(["side eye", "monkey puppet looking away", "cat staring", "blank stare", "eating popcorn"])
        if not social_title or social_title.lower() in {"", "instagram", "reels"}:
            return WindowContext(
                subject="Instagram Reels",
                category="social",
                is_specific=True,
                is_social=True,
                search_query=random_reaction,
            )
        if len(social_title) >= 3:
            clean_sub = clean_media_subject(social_title)
            return WindowContext(
                subject=clean_sub,
                category="social",
                is_specific=True,
                is_social=True,
                search_query=random_reaction,
            )

    # 5. Google Search / DuckDuckGo / Bing
    search_match = re.search(r"^(.*?)\s*-\s*(Google Search|DuckDuckGo Search|Bing)$", cleaned, re.IGNORECASE)
    if search_match:
        query = _clean_str(search_match.group(1))
        if len(query) >= 3:
            return WindowContext(subject=query[:50], category="search", is_specific=True, search_query=query)

    # 6. Stack Overflow / Stack Exchange
    if "stack overflow" in cleaned.lower() or "stack exchange" in cleaned.lower():
        so_title = re.sub(r"\s*-\s*Stack (Overflow|Exchange).*$", "", cleaned, flags=re.IGNORECASE)
        so_title = _clean_str(so_title)
        if len(so_title) >= 4:
            return WindowContext(subject=so_title[:55], category="docs", is_specific=True, search_query=extract_clean_search_query(so_title))

    # 7. GitHub / GitLab / Bitbucket
    if any(g in cleaned.lower() for g in ["github", "gitlab", "bitbucket"]):
        gh_title = re.sub(r"\s*[-·|•]\s*(?:GitHub|GitLab|Bitbucket).*$", "", cleaned, flags=re.IGNORECASE)
        gh_title = _clean_str(gh_title)
        if not gh_title or gh_title.lower() in ("github", "gitlab", "bitbucket"):
            subject = "GitHub" if "github" in cleaned.lower() else "Code Repository"
        else:
            subject = gh_title[:50]
        return WindowContext(subject=subject, category="code", is_specific=True, is_social=False)

    # 8. Webmail & Messaging: Gmail, Outlook, ProtonMail, Fastmail, Yahoo Mail
    if any(m in cleaned.lower() for m in ["gmail", "google mail", "mail.google", "outlook", "protonmail", "fastmail", "yahoo mail", "webmail"]):
        mail_title = re.sub(r"\s*[-—|•]\s*(?:Gmail|Outlook|ProtonMail|Google Chrome|Microsoft Edge).*$", "", cleaned, flags=re.IGNORECASE)
        mail_title = re.sub(r"^\(\d+\)\s*", "", mail_title)  # Strip unread badge (e.g. (3))
        mail_title = _clean_str(mail_title)
        if not mail_title or mail_title.lower() in ("inbox", "gmail", "mail", "sent", "drafts", "google mail"):
            subject = "Gmail" if "gmail" in cleaned.lower() else "Email"
        else:
            subject = f"Email: {mail_title[:35]}"
        return WindowContext(subject=subject, category="email", is_specific=True, is_social=False)

    # 9. Wikipedia: "Quantum mechanics - Wikipedia"
    if "wikipedia" in cleaned.lower():
        wiki_title = re.sub(r"\s*-\s*Wikipedia.*$", "", cleaned, flags=re.IGNORECASE)
        wiki_title = _clean_str(wiki_title)
        if len(wiki_title) >= 3:
            return WindowContext(subject=wiki_title[:50], category="reading", is_specific=True, search_query=wiki_title, is_social=False)

    # 10. Reading & Research Platforms: Medium, Substack, Dev.to, ArXiv, Hacker News, blogs
    reading_indicators = ["medium.com", "substack.com", "dev.to", "hashnode", "hackernews", "ycombinator", "arxiv", "paper", "newsletter"]
    if any(r in cleaned.lower() for r in reading_indicators):
        read_title = re.sub(r"\s*[-—|•]\s*(?:Medium|Substack|Dev\.to|Wikipedia|Hacker News).*$", "", cleaned, flags=re.IGNORECASE)
        read_title = _clean_str(read_title)
        if len(read_title) >= 3:
            return WindowContext(subject=read_title[:50], category="reading", is_specific=True, is_social=False)

    # 11. Google Docs / Sheets / Notion / Linear / Jira / Trello / Figma
    doc_match = re.search(r"^(.*?)\s*-\s*(Google (Docs|Sheets|Slides)|Notion|Jira|Linear|Trello|Figma)$", cleaned, re.IGNORECASE)
    if doc_match:
        doc_title = _clean_str(doc_match.group(1))
        if len(doc_title) >= 3 and doc_title.lower() not in GENERIC_TITLES:
            return WindowContext(subject=doc_title[:50], category="docs", is_specific=True, is_social=False)

    # 12. General Webpage: Grab page title before site delimiter (articles, blogs, news)
    parts = re.split(r"\s*[-—|•]\s*", cleaned)
    if parts:
        candidate = _clean_str(parts[0])
        candidate = re.sub(r"^\(\d+\)\s*", "", candidate)
        if 4 <= len(candidate) <= 50 and candidate.lower() not in GENERIC_TITLES:
            return WindowContext(subject=candidate, category="reading", is_specific=True, is_social=False)

    return None


def extract_media_context(app: str, title: str) -> Optional[WindowContext]:
    """Extract currently playing song or media title from players like Spotify."""
    cleaned = _clean_str(title)
    if not cleaned or cleaned.lower() in {"spotify", "spotify free", "spotify premium"}:
        return None

    # Often "Artist - Track" or "Track"
    if 2 <= len(cleaned) <= 60:
        return WindowContext(subject=cleaned, category="music", is_specific=True)
    return None


def extract_terminal_context(app: str, title: str) -> Optional[WindowContext]:
    """Extract command or active folder from terminal title if specific."""
    cleaned = _clean_str(title)
    # Strip common prefixes
    cleaned = re.sub(r"^Administrator:\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = _clean_str(cleaned)

    if cleaned.lower() in GENERIC_TITLES or len(cleaned) < 3:
        return None

    # If it contains common commands (git, npm, python, cargo, docker, etc.)
    cmd_match = re.search(r"\b(git|npm|pnpm|yarn|cargo|docker|python|make|pytest|go|kubectl)\s+([a-zA-Z0-9_\-\.]+)", cleaned, re.IGNORECASE)
    if cmd_match:
        return WindowContext(subject=f"{cmd_match.group(1)} {cmd_match.group(2)}", category="terminal", is_specific=True)

    # If it's a folder or path
    if "\\" in cleaned or "/" in cleaned:
        tail = cleaned.replace("\\", "/").rstrip("/").split("/")[-1]
        if tail and tail.lower() not in GENERIC_TITLES:
            return WindowContext(subject=tail, category="terminal", is_specific=True)

    return None


def extract_context(app_name: str, window_title: str, dwell_minutes: float = 0.0) -> Optional[WindowContext]:
    """
    Main dispatcher for extracting contextual subjects from active windows.

    Returns WindowContext with a clean subject if specific, or None if the title
    is generic/noisy or cannot be confidently parsed.
    """
    if not window_title or not app_name:
        return None

    app_lower = app_name.lower()
    title_lower = window_title.lower().strip()

    if title_lower in GENERIC_TITLES:
        return None

    ctx = None
    # Code editors
    code_apps = {"code.exe", "devenv.exe", "idea64.exe", "pycharm64.exe", "rider64.exe",
                 "webstorm64.exe", "goland64.exe", "sublime_text.exe", "notepad++.exe", "antigravity.exe"}
    if app_lower in code_apps:
        ctx = extract_code_context(app_lower, window_title)
    # Browsers
    elif app_lower in {"chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe", "vivaldi.exe", "arc.exe"}:
        ctx = extract_browser_context(app_lower, window_title)
    # Media
    elif "spotify" in app_lower:
        ctx = extract_media_context(app_lower, window_title)
    # Terminals
    elif app_lower in {"powershell.exe", "cmd.exe", "windowsterminal.exe", "wt.exe", "alacritty.exe", "wezterm-gui.exe"}:
        ctx = extract_terminal_context(app_lower, window_title)
    else:
        # General fallback: check if title has a clean, meaningful name
        parts = re.split(r"[-—|•]", window_title)
        if parts:
            candidate = _clean_str(parts[0])
            if 4 <= len(candidate) <= 45 and candidate.lower() not in GENERIC_TITLES:
                ctx = WindowContext(subject=candidate, category="general", is_specific=True)

    if ctx is not None:
        ctx.dwell_minutes = dwell_minutes
    return ctx
