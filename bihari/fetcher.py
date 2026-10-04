"""
Module 3B: THE MEME FETCHER — Reddit seed mode.

Downloads memes on first launch or on manual "Fetch / Refresh Memes" trigger.
Saves them to local vibe folders so runtime stays completely offline.

Sources:
  1. Primary: meme-api.com (open-source public wrapper for Reddit memes)
  2. Fallback: old.reddit.com/r/{subreddit}/hot.json with browser emulation

Privacy:
  - Opt-in via config.toml (online_fetch = false by default)
  - Only fetches public image URLs — no telemetry is sent
"""

import os
import time
import logging
import threading
import collections
import hashlib
from pathlib import Path
from typing import Optional, Union
from urllib.parse import urlparse, quote_plus

import re
import random
import requests

from .inference import Vibe, VIBE_FOLDER_NAMES
from .logger import extract_canonical_id


def compute_file_hash(path: Union[str, Path]) -> str:
    """Compute SHA-256 hash of image contents for duplicate detection."""
    p = Path(path)
    if not p.is_file():
        return ""
    try:
        h = hashlib.sha256()
        with open(p, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""


logger = logging.getLogger(__name__)

# ── Subreddit mapping per vibe (visual-first, minimal/no text) ──
VIBE_SUBREDDITS: dict[Vibe, list[str]] = {
    Vibe.FLOW_STATE: [
        "oddlysatisfying",
        "Eyebleach",
        "wholesomememes",
    ],
    Vibe.GRINDING: [
        "reactionpics",
        "AnimalsBeingDerps",
        "wunkus",
    ],
    Vibe.BURNOUT_APPROACHING: [
        "Eyebleach",
        "reactionpics",
        "aww",
    ],
    Vibe.SYNTAX_RAGE: [
        "reactionpics",
        "blurrypicturesofcats",
        "ReactionMemes",
        "softwaregore",
    ],
    Vibe.HELP_SEEKING: [
        "reactionpics",
        "ReactionMemes",
        "AnimalsBeingDerps",
    ],
    Vibe.MOUNTING_FRICTION: [
        "reactionpics",
        "hmmm",
        "AnimalsBeingDerps",
    ],
    Vibe.WANDERING: [
        "hmmm",
        "AnimalsBeingDerps",
        "reactionpics",
    ],
    Vibe.LOST_IN_SCROLL: [
        "reactionpics",
        "wunkus",
        "hmmm",
    ],
    Vibe.TAB_BUTTERFLY: [
        "reactionpics",
        "AnimalsBeingDerps",
        "blurrypicturesofcats",
    ],
    Vibe.STILLNESS: [
        "Eyebleach",
        "aww",
        "wholesomememes",
    ],
    Vibe.MEETING_RECOVERY: [
        "reactionpics",
        "Eyebleach",
        "AnimalsBeingDerps",
    ],
    Vibe.AFTERNOON_DRIFT: [
        "Eyebleach",
        "AnimalsBeingDerps",
        "wunkus",
        "aww",
        "rarepuppers",
    ],
}

VALID_IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".gif", ".webp"})

API_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

RSS_HEADERS = {
    "User-Agent": "windows:bihari_mindful_desktop:v0.1.0 (by /u/bihari_mirror)",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}

IMAGE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    "Referer": "https://www.reddit.com/",
}

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def _is_valid_image_url(url: str) -> bool:
    """Check if a URL points to a downloadable image."""
    if not url:
        return False
    parsed = urlparse(url)
    path_lower = parsed.path.lower()

    if not any(path_lower.endswith(ext) for ext in VALID_IMAGE_EXTENSIONS):
        return False

    if "v.redd.it" in parsed.netloc:
        return False

    return True


def _download_image(url: str, save_path: Path, timeout: int = 10) -> bool:
    """Download a single image to disk with size and type checks."""
    try:
        resp = requests.get(url, headers=IMAGE_HEADERS, timeout=timeout, stream=True)
        resp.raise_for_status()

        content_length = resp.headers.get("Content-Length")
        if content_length and int(content_length) > MAX_FILE_SIZE:
            logger.debug(f"Skipping {url} — too large ({content_length} bytes)")
            return False

        content_type = resp.headers.get("Content-Type", "")
        # Allow image types or octet-stream (some CDNs serve images with binary type)
        if content_type and not (content_type.startswith("image/") or "octet-stream" in content_type):
            logger.debug(f"Skipping {url} — not an image ({content_type})")
            return False

        chunks = []
        total = 0
        for chunk in resp.iter_content(chunk_size=8192):
            total += len(chunk)
            if total > MAX_FILE_SIZE:
                return False
            chunks.append(chunk)

        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "wb") as f:
            for chunk in chunks:
                f.write(chunk)

        return True

    except Exception as e:
        logger.debug(f"Download failed for {url}: {e}")
        if save_path.exists():
            try:
                save_path.unlink()
            except OSError:
                pass
        return False


def _fetch_from_meme_api(subreddit: str, count: int) -> list[dict]:
    """Fetch memes using the open meme-api service."""
    url = f"https://meme-api.com/gimme/{subreddit}/{count}"
    try:
        resp = requests.get(url, headers=API_HEADERS, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        memes = data.get("memes", [])
        valid = []
        for m in memes:
            if m.get("nsfw", False):
                continue
            img_url = m.get("url", "")
            if _is_valid_image_url(img_url):
                valid.append({
                    "url": img_url,
                    "title": m.get("title", ""),
                    "id": m.get("postLink", "").split("/")[-1] or str(hash(img_url)),
                })
        return valid
    except Exception as e:
        logger.debug(f"meme-api.com failed for r/{subreddit}: {e}")
        return []


def _fetch_from_reddit_json(subreddit: str, count: int) -> list[dict]:
    """Fallback: fetch using old.reddit.com JSON endpoint."""
    url = f"https://old.reddit.com/r/{subreddit}/hot.json?limit=25"
    try:
        resp = requests.get(url, headers=API_HEADERS, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        children = data.get("data", {}).get("children", [])
        valid = []
        for child in children:
            post = child.get("data", {})
            if post.get("over_18", False) or post.get("is_video", False) or post.get("is_self", False):
                continue
            img_url = post.get("url", "")
            if _is_valid_image_url(img_url):
                valid.append({
                    "url": img_url,
                    "title": post.get("title", ""),
                    "id": post.get("id", ""),
                })
        return valid
    except Exception as e:
        logger.debug(f"old.reddit.com failed for r/{subreddit}: {e}")
        return []


def fetch_memes_for_vibe(
    vibe: Vibe,
    meme_dir: Path,
    count: int = 10,
    seen_ids: Optional[set[str]] = None,
) -> int:
    """Fetch memes for a specific vibe, saving them locally, avoiding any lifetime seen IDs."""
    target_dir = meme_dir / VIBE_FOLDER_NAMES[vibe]
    target_dir.mkdir(parents=True, exist_ok=True)

    subreddits = VIBE_SUBREDDITS.get(vibe, [])
    if not subreddits:
        return 0

    downloaded = 0
    seen_urls = set()
    existing_stems = {f.stem for f in target_dir.iterdir() if f.is_file()}

    for subreddit in subreddits:
        if downloaded >= count:
            break

        logger.info(f"Fetching from r/{subreddit} for {VIBE_FOLDER_NAMES[vibe]}...")
        needed_here = count - downloaded

        # 1. Try meme-api.com first
        posts = _fetch_from_meme_api(subreddit, min(needed_here * 2, 25))

        # 2. If empty, fallback to old.reddit.com
        if not posts:
            posts = _fetch_from_reddit_json(subreddit, min(needed_here * 2, 25))

        if not posts:
            logger.warning(f"No usable images found from r/{subreddit}")
            time.sleep(1)
            continue

        for post in posts:
            if downloaded >= count:
                break

            img_url = post["url"]
            if img_url in seen_urls:
                continue
            seen_urls.add(img_url)

            ext = Path(urlparse(img_url).path).suffix.lower()
            if ext not in VALID_IMAGE_EXTENSIONS:
                ext = ".jpg"

            post_id = post["id"] or str(int(time.time() * 1000))
            filename = f"reddit_{subreddit}_{post_id}{ext}"
            cid = extract_canonical_id(filename)

            # Never seed memes that the user has already seen!
            if seen_ids and cid in seen_ids:
                continue

            if filename.replace(ext, "") in existing_stems:
                continue

            save_path = target_dir / filename
            if _download_image(img_url, save_path):
                downloaded += 1
                logger.info(f"  [{downloaded}/{count}] Saved: {filename}")

        time.sleep(1.0)

    return downloaded


def seed_all_vibes(
    meme_dir: Path,
    min_threshold: int = 3,
    target_count: int = 10,
    force: bool = False,
    seen_ids: Optional[set[str]] = None,
) -> dict[str, int]:
    """Seed memes for all vibe categories that are below threshold of unseen memes."""
    results = {}

    logger.info("=" * 45)
    logger.info("  Meme Seeder — Fetching from Reddit")
    logger.info("=" * 45)

    for vibe in Vibe:
        folder_name = VIBE_FOLDER_NAMES[vibe]
        folder = meme_dir / folder_name
        folder.mkdir(parents=True, exist_ok=True)

        if seen_ids:
            unseen_count = sum(
                1 for f in folder.iterdir()
                if f.is_file() and f.suffix.lower() in VALID_IMAGE_EXTENSIONS and extract_canonical_id(f.name) not in seen_ids
            )
        else:
            unseen_count = sum(
                1 for f in folder.iterdir()
                if f.is_file() and f.suffix.lower() in VALID_IMAGE_EXTENSIONS
            )

        if not force and unseen_count >= min_threshold:
            logger.info(f"  {folder_name}: {unseen_count} unseen memes — sufficient, skipping.")
            results[folder_name] = 0
            continue

        needed = max(target_count - unseen_count, 1) if not force else target_count
        logger.info(f"  {folder_name}: unseen={unseen_count} — downloading {needed} fresh memes...")

        fetched = fetch_memes_for_vibe(vibe, meme_dir, count=needed, seen_ids=seen_ids)
        results[folder_name] = fetched
        logger.info(f"  {folder_name}: downloaded {fetched} new memes.")

    total = sum(results.values())
    logger.info(f"Seeding complete: {total} total memes downloaded.")
    return results


def seed_in_background(
    meme_dir: Path,
    min_threshold: int = 3,
    target_count: int = 10,
    force: bool = False,
    callback=None,
    seen_ids: Optional[set[str]] = None,
):
    """Run the meme seeder in a background thread."""

    def _worker():
        try:
            results = seed_all_vibes(meme_dir, min_threshold, target_count, force, seen_ids=seen_ids)
            if callback:
                callback(results)
        except Exception as e:
            logger.error(f"Background meme seeder failed: {e}", exc_info=True)

    thread = threading.Thread(target=_worker, name="MemeSeeder", daemon=True)
    thread.start()
    return thread


def _get_target_reaction_subreddit(query: str) -> str:
    """Map reaction queries to the most visually expressive subreddit."""
    q = query.lower()
    if any(w in q for w in ["cat", "kitty", "feline", "meow"]):
        return "blurrypicturesofcats"
    if any(w in q for w in ["dog", "puppy", "bark", "otter"]):
        return "rarepuppers"
    if any(w in q for w in ["groov", "danc", "bopp", "sway", "bob", "vibe", "chill"]):
        return "wunkus"
    if any(w in q for w in ["derp", "animal", "food", "cook", "eat"]):
        return "AnimalsBeingDerps"
    if any(w in q for w in ["hmmm", "weird", "curious"]):
        return "hmmm"
    return "reactionpics"


def search_live_contextual_meme(
    query: Union[str, list[str]],
    meme_dir: Path,
    timeout: int = 5,
    recent_memes: Optional[Union[list, set, collections.deque]] = None,
    seen_ids: Optional[set[str]] = None,
    seen_hashes: Optional[set[str]] = None,
) -> Optional[Path]:
    """
    Search for a live contextual meme based on active search queries (e.g. ['GTA 6', 'gaming']).
    Multi-tier strategy:
      Tier 1: Targeted direct search on Reddit RSS.
      Tier 2: Instant resilient fetch via meme-api.com if Reddit RSS is rate-limited (429) or empty.
    Downloads fresh candidate images into a local 'live-cache/' directory.
    Strictly excludes any memes present in `seen_ids` or `recent_memes` to prevent repeats forever.
    Returns the Path to the image, or None if completely offline.
    """
    candidates = [query] if isinstance(query, str) else query
    valid_candidates = [q.strip() for q in candidates if q and len(q.strip()) >= 2]
    if not valid_candidates:
        return None

    cache_dir = Path(meme_dir) / "live-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    recent_stems = set()
    if recent_memes:
        for m in recent_memes:
            if hasattr(m, "stem"):
                recent_stems.add(m.stem)
            elif isinstance(m, (str, Path)):
                recent_stems.add(Path(m).stem)

    # Try the most salient visual reaction query
    for q_item in valid_candidates[:1]:
        target_sub = _get_target_reaction_subreddit(q_item)
        logger.info(f"🔍 Searching live visual reaction for: '{q_item}' (targeting r/{target_sub})...")

        # ── Tier 1: Try direct Reddit RSS search ──
        rss_subs = [target_sub]
        if target_sub != "reactionpics":
            rss_subs.append("reactionpics")

        for sub in rss_subs:
            encoded = quote_plus(q_item)
            url = f"https://www.reddit.com/r/{sub}/search.rss?q={encoded}&restrict_sr=1&sort=relevance"

            try:
                resp = requests.get(url, headers=RSS_HEADERS, timeout=timeout)
                if resp.status_code == 200:
                    img_urls = re.findall(
                        r'https?://(?:i\.redd\.it|preview\.redd\.it|i\.imgur\.com)/[a-zA-Z0-9_\-\.]+\.(?:jpg|png|webp)',
                        resp.text
                    )
                    candidates_list = []
                    seen = set()
                    for img_url in img_urls:
                        if img_url in seen:
                            continue
                        seen.add(img_url)
                        direct_url = img_url.replace("preview.redd.it", "i.redd.it")
                        ext = Path(urlparse(direct_url).path).suffix.lower()
                        if ext not in VALID_IMAGE_EXTENSIONS:
                            ext = ".jpg"
                        filename = f"live_{abs(hash(direct_url)) % 10000000}{ext}"
                        cid = extract_canonical_id(filename)

                        # Exclude any meme seen before in lifetime history
                        if seen_ids and cid in seen_ids:
                            continue
                        save_path = cache_dir / filename
                        if save_path.stem in recent_stems or save_path.name in recent_stems:
                            continue
                        candidates_list.append((direct_url, save_path, filename))

                    if candidates_list:
                        random.shuffle(candidates_list)
                        for direct_url, save_path, filename in candidates_list:
                            if save_path.exists() and save_path.stat().st_size > 1000:
                                if seen_hashes and compute_file_hash(save_path) in seen_hashes:
                                    continue
                                logger.info(f"🎯 Reusing cached unshown live meme: {filename} for '{q_item}'")
                                return save_path
                            if _download_image(direct_url, save_path, timeout=timeout):
                                if seen_hashes and compute_file_hash(save_path) in seen_hashes:
                                    try:
                                        save_path.unlink()
                                    except OSError:
                                        pass
                                    continue
                                logger.info(f"🎯 Downloaded live visual reaction: {filename} for '{q_item}'")
                                _prune_cache(cache_dir, max_files=60)
                                return save_path
            except Exception as e:
                logger.debug(f"RSS search failed for '{q_item}' on r/{sub}: {e}")

        # ── Tier 2: Resilient live fetch via meme-api (bypasses Reddit 429) ──
        logger.debug(f"Reddit RSS unavailable or empty for '{q_item}' — pulling live reaction from r/{target_sub} via API...")
        try:
            api_subs = [target_sub]
            if target_sub != "reactionpics":
                api_subs.append("reactionpics")

            for sub in api_subs:
                posts = _fetch_from_meme_api(sub, count=15)
                if not posts:
                    continue

                random.shuffle(posts)
                for post in posts:
                    img_url = post.get("url")
                    if not img_url:
                        continue
                    post_id = post.get("id") or str(abs(hash(img_url)) % 10000000)
                    ext = Path(urlparse(img_url).path).suffix.lower()
                    if ext not in VALID_IMAGE_EXTENSIONS:
                        ext = ".jpg"
                    filename = f"live_{post_id}{ext}"
                    cid = extract_canonical_id(filename)

                    # Exclude any meme seen before in lifetime history
                    if seen_ids and cid in seen_ids:
                        continue

                    save_path = cache_dir / filename
                    if save_path.stem in recent_stems or save_path.name in recent_stems:
                        continue

                    if save_path.exists() and save_path.stat().st_size > 1000:
                        if seen_hashes and compute_file_hash(save_path) in seen_hashes:
                            continue
                        logger.info(f"🎯 Reusing cached unshown live reaction: {filename} for '{q_item}'")
                        return save_path

                    if _download_image(img_url, save_path, timeout=timeout):
                        if seen_hashes and compute_file_hash(save_path) in seen_hashes:
                            try:
                                save_path.unlink()
                            except OSError:
                                pass
                            continue
                        logger.info(f"🎯 Downloaded live visual reaction: {filename} for '{q_item}' (from r/{sub})")
                        _prune_cache(cache_dir, max_files=60)
                        return save_path
        except Exception as e:
            logger.debug(f"Tier 2 meme-api live fetch failed: {e}")

    logger.info(f"No live meme images found for {valid_candidates} across subreddits.")
    return None


def _prune_cache(cache_dir: Path, max_files: int = 20, max_age_seconds: int = 21600):
    """Keep the live cache fresh and bounded so old downloads from past days never linger."""
    try:
        now = time.time()
        files = [f for f in cache_dir.iterdir() if f.is_file()]
        # Remove files older than 6 hours
        for f in files[:]:
            try:
                if (now - f.stat().st_mtime) > max_age_seconds:
                    f.unlink()
                    files.remove(f)
            except OSError:
                pass
        # If still over max_files, remove oldest
        files.sort(key=lambda p: p.stat().st_mtime)
        while len(files) > max_files:
            oldest = files.pop(0)
            try:
                oldest.unlink()
            except OSError:
                pass
    except Exception:
        pass

