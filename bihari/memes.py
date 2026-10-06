"""
Module 3: THE MEME RETRIEVER — Local meme selector.

Maintains a local directory tree with subfolders for each vibe tag.
When a vibe is classified with sufficient confidence, selects a random
meme image from the corresponding folder, with deduplication to avoid
showing the same meme twice in a row.
"""

import random
import collections
import logging
import hashlib
import re
from pathlib import Path
from typing import Any, Optional, Union

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


MEME_README_TEXT = (
    "=== Becoming a Bihari — Meme Library ===\n"
    "\n"
    "Drop your meme images (.jpg, .png, .gif, .webp) into the\n"
    "matching subfolder:\n"
    "\n"
    "  🔥 Intensity:\n"
    "    in-the-zone/          — when code flows effortlessly\n"
    "    the-long-grind/       — hour after hour, still going\n"
    "    running-on-fumes/     — gentle \"maybe take a break\" vibes\n"
    "\n"
    "  😤 Frustration:\n"
    "    fighting-the-code/    — backspace warfare, rewriting everything\n"
    "    asking-the-internet/  — the sacred Stack Overflow pilgrimage\n"
    "    mounting-friction/    — \"everything is fine\" energy\n"
    "\n"
    "  😴 Avoidance:\n"
    "    just-wandering/       — scenic detour in thought\n"
    "    lost-in-the-scroll/   — deep in the infinite feed\n"
    "    tab-butterfly/        — 47 tabs, none of them right\n"
    "\n"
    "  ☕ Downtime:\n"
    "    the-great-pause/      — away, being human\n"
    "    post-meeting-recovery/ — survived another one\n"
    "    afternoon-drift/      — post-lunch autopilot\n"
    "\n"
    "The tool shows a meme as a gentle mirror of your current\n"
    "state — no judgments, just a laugh of recognition.\n"
    "More memes = more variety!\n"
)

logger = logging.getLogger(__name__)


class MemeRetriever:
    """
    Selects memes from a local folder structure.

    Directory layout:
      <meme_dir>/
        in-the-zone/       *.jpg, *.png, *.gif, *.webp
        fighting-the-code/ ...
        just-wandering/    ...
        lost-in-the-scroll/...
        the-great-pause/   ...
    """

    VALID_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".gif", ".webp"})

    def __init__(
        self,
        meme_dir: Path,
        cooldown_seconds: int = 300,
        history_db: Optional[Path] = None,
        pack_manager: Optional[Any] = None,
        never_repeat: bool = False,
    ):
        """
        Args:
            meme_dir: Root directory containing vibe subfolders.
            cooldown_seconds: Minimum seconds between meme displays.
            history_db: Path to vibe_history.db for persistent cross-session deduplication.
            pack_manager: Optional PackManager instance for loaded .lucidpack memes.
            never_repeat: Strict zero-repeat mode — never show a meme twice ever.
        """
        self.meme_dir = Path(meme_dir)
        self.cooldown = cooldown_seconds
        self.pack_manager = pack_manager
        self.never_repeat = never_repeat
        self.history_db = Path(history_db) if history_db else None

        # Track lifetime seen IDs and content hashes
        self._seen_ids: set[str] = set()
        self._seen_hashes: set[str] = set()
        self._hash_cache: dict[str, str] = {}
        self._recent: collections.deque = collections.deque(maxlen=100)
        self._last_shown_time: float = 0
        self._last_shown_map: dict[str, float] = {}

        # Load lifetime seen history from SQLite if available
        if self.history_db and self.history_db.exists():
            self._load_seen_history()

        # Ensure folder structure exists on init
        self._ensure_folders()

    def _load_seen_history(self):
        """Load all lifetime seen meme IDs and hashes from SQLite."""
        try:
            import sqlite3
            conn = sqlite3.connect(str(self.history_db), timeout=2.0)
            cursor = conn.cursor()
            # Ensure seen_memes table exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS seen_memes (
                    meme_id TEXT PRIMARY KEY,
                    file_hash TEXT,
                    filename TEXT,
                    shown_at REAL
                )
            """)
            # Check if seen_memes has data; if empty, migrate from vibe_log
            cursor.execute("SELECT COUNT(*) FROM seen_memes")
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    "SELECT DISTINCT meme_shown, timestamp FROM vibe_log "
                    "WHERE meme_shown IS NOT NULL AND meme_shown != ''"
                )
                for (m_name, ts) in cursor.fetchall():
                    if m_name:
                        cid = extract_canonical_id(m_name)
                        cursor.execute(
                            "INSERT OR IGNORE INTO seen_memes (meme_id, file_hash, filename, shown_at) "
                            "VALUES (?, ?, ?, ?)",
                            (cid, "", m_name, float(ts) if ts else 0.0),
                        )
                conn.commit()

            cursor.execute("SELECT meme_id, file_hash, filename, shown_at FROM seen_memes")
            rows = cursor.fetchall()
            conn.close()

            for meme_id, f_hash, filename, shown_at in rows:
                if meme_id:
                    self._seen_ids.add(meme_id.lower())
                if f_hash:
                    self._seen_hashes.add(f_hash.lower())
                if filename:
                    self._recent.append(filename)
                    self._last_shown_map[filename] = float(shown_at or 0.0)

            logger.info(
                f"Loaded {len(self._seen_ids)} lifetime seen memes from database "
                f"(never_repeat={self.never_repeat})."
            )
        except Exception as e:
            logger.warning(f"Could not load meme history from DB: {e}")

    @property
    def seen_ids(self) -> set[str]:
        """Return the set of all canonical meme IDs ever seen."""
        return self._seen_ids

    @property
    def seen_hashes(self) -> set[str]:
        """Return the set of all image content hashes ever seen."""
        return self._seen_hashes

    def get_file_hash(self, path: Union[str, Path]) -> str:
        """Cached file hash computation."""
        key = str(path)
        if key not in self._hash_cache:
            self._hash_cache[key] = compute_file_hash(path)
        return self._hash_cache[key]

    def migrate_old_folders(self):
        """Migrate old vibe folder names to new human-readable ones."""
        old_to_new = {
            "SYNTAX_RAGE": "fighting-the-code",
            "DEEP_FOCUS": "in-the-zone",
            "PROCRASTINATING": "just-wandering",
            "LAZY_BROWSING": "lost-in-the-scroll",
            "COFFEE_BREAK": "the-great-pause",
        }
        for old_name, new_name in old_to_new.items():
            old_folder = self.meme_dir / old_name
            new_folder = self.meme_dir / new_name
            if old_folder.exists() and old_folder.is_dir():
                new_folder.mkdir(parents=True, exist_ok=True)
                for item in old_folder.iterdir():
                    if item.is_file():
                        dest = new_folder / item.name
                        if not dest.exists():
                            item.rename(dest)
                try:
                    old_folder.rmdir()
                except OSError:
                    pass

        # Also delete old README.txt so it can be regenerated with new folder names
        readme_path = self.meme_dir / "README.txt"
        if readme_path.exists():
            try:
                content = readme_path.read_text(encoding="utf-8")
                if "SYNTAX_RAGE/" in content:
                    readme_path.unlink()
            except Exception:
                pass

    def _ensure_folders(self):
        """Create the meme directory tree if it doesn't exist."""
        self.migrate_old_folders()

        for vibe in Vibe:
            folder = self.meme_dir / VIBE_FOLDER_NAMES[vibe]
            folder.mkdir(parents=True, exist_ok=True)

        # Write a README if the root is freshly created
        readme_path = self.meme_dir / "README.txt"
        if not readme_path.exists():
            readme_path.write_text(MEME_README_TEXT, encoding="utf-8")
            logger.info(f"Created meme directory structure at: {self.meme_dir}")

    def get_meme_count(self) -> dict[str, int]:
        """Return the number of memes available per vibe folder across active pack and local directory."""
        counts = {}
        active_pack = self.pack_manager.get_active_pack() if self.pack_manager else None

        for vibe in Vibe:
            folder_name = VIBE_FOLDER_NAMES[vibe]
            folder = self.meme_dir / folder_name
            local_count = 0
            if folder.exists():
                local_count = sum(
                    1 for f in folder.iterdir()
                    if f.is_file() and f.suffix.lower() in self.VALID_EXTENSIONS
                )
            pack_count = len(active_pack.get_memes(vibe)) if active_pack else 0
            counts[folder_name] = max(local_count, pack_count) if (local_count == 0 or pack_count == 0) else (local_count + pack_count)
        return counts

    def record_shown(self, current_time: float, meme_path: Optional[Path] = None):
        """Record that a meme was shown (e.g. from live search) and track it in lifetime history."""
        self._last_shown_time = current_time
        if meme_path:
            p = Path(meme_path)
            name = p.name
            self._recent.append(name)
            self._last_shown_map[name] = current_time

            cid = extract_canonical_id(name)
            self._seen_ids.add(cid)
            f_hash = self.get_file_hash(p)
            if f_hash:
                self._seen_hashes.add(f_hash)

            if self.history_db:
                try:
                    import sqlite3
                    self.history_db.parent.mkdir(parents=True, exist_ok=True)
                    conn = sqlite3.connect(str(self.history_db), timeout=2.0)
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS seen_memes (
                            meme_id TEXT PRIMARY KEY,
                            file_hash TEXT,
                            filename TEXT,
                            shown_at REAL
                        )
                    """)
                    conn.execute(
                        "INSERT OR REPLACE INTO seen_memes (meme_id, file_hash, filename, shown_at) "
                        "VALUES (?, ?, ?, ?)",
                        (cid, f_hash, name, current_time),
                    )
                    conn.commit()
                    conn.close()
                except Exception as e:
                    logger.debug(f"Failed to persist seen meme {name}: {e}")

    def get_meme(self, vibe: Vibe, current_time: float, cooldown: Optional[float] = None) -> Optional[Path]:
        """
        Select a random meme for the given vibe.

        Args:
            vibe: The classified vibe tag.
            current_time: Current Unix timestamp (time.time()).
            cooldown: Optional custom cooldown override in seconds.

        Returns:
            Path to a meme image, or None if on cooldown or folder is empty.
        """
        # Cooldown check — don't spam the user
        check_cooldown = self.cooldown if cooldown is None else cooldown
        if current_time - self._last_shown_time < check_cooldown:
            logger.debug(
                f"Meme on cooldown ({check_cooldown}s). "
                f"Next eligible in {check_cooldown - (current_time - self._last_shown_time):.0f}s."
            )
            return None

        folder_name = VIBE_FOLDER_NAMES[vibe]
        folder = self.meme_dir / folder_name

        candidates: list[Path] = []
        active_pack = self.pack_manager.get_active_pack() if self.pack_manager else None
        if active_pack:
            candidates.extend(active_pack.get_memes(vibe))

        # Check local folder as fallback or supplement if active pack has no memes for this vibe
        if not candidates and folder.exists():
            candidates.extend([
                f for f in folder.iterdir()
                if f.is_file() and f.suffix.lower() in self.VALID_EXTENSIONS
            ])

        # If still empty, check default bundled pack if available
        if not candidates and self.pack_manager:
            bundled = self.pack_manager.get_pack("vihara-core-default")
            if bundled and bundled != active_pack:
                candidates.extend(bundled.get_memes(vibe))

        # For browsing/scrolling/wandering, cross-pool across all visual reaction folders!
        # This dramatically expands the pool so candidate exhaustion is minimized.
        if vibe in (Vibe.LOST_IN_SCROLL, Vibe.WANDERING):
            related_vibes = [
                Vibe.WANDERING,
                Vibe.TAB_BUTTERFLY,
                Vibe.STILLNESS,
                Vibe.MEETING_RECOVERY,
                Vibe.BURNOUT_APPROACHING,
                Vibe.AFTERNOON_DRIFT,
            ]
            seen_names = {c.name for c in candidates}
            for rv in related_vibes:
                if active_pack:
                    for m in active_pack.get_memes(rv):
                        if m.name not in seen_names:
                            candidates.append(m)
                            seen_names.add(m.name)
                r_folder = self.meme_dir / VIBE_FOLDER_NAMES[rv]
                if r_folder.exists() and r_folder != folder:
                    for f in r_folder.iterdir():
                        if f.is_file() and f.suffix.lower() in self.VALID_EXTENSIONS and f.name not in seen_names:
                            candidates.append(f)
                            seen_names.add(f.name)

        if not candidates:
            logger.info(
                f"No memes found in {folder}. "
                f"Add images to {folder} to enable memes for {vibe.value}."
            )
            return None

        if self.never_repeat:
            # ── STRICT NEVER-REPEAT MODE ──
            # Completely eliminate any meme whose canonical ID or content hash was ever seen
            eligible = [
                c for c in candidates
                if extract_canonical_id(c.name) not in self._seen_ids
                and (not self.get_file_hash(c) or self.get_file_hash(c) not in self._seen_hashes)
            ]

            if not eligible:
                # Local vibe folder exhausted! Search other folders across all 12 vibes for unseen memes
                other_unseen = []
                for other_vibe in Vibe:
                    if other_vibe == vibe:
                        continue
                    ov_folder = self.meme_dir / VIBE_FOLDER_NAMES[other_vibe]
                    ov_candidates = []
                    if active_pack:
                        ov_candidates.extend(active_pack.get_memes(other_vibe))
                    if ov_folder.exists():
                        ov_candidates.extend([
                            f for f in ov_folder.iterdir()
                            if f.is_file() and f.suffix.lower() in self.VALID_EXTENSIONS
                        ])
                    for oc in ov_candidates:
                        if (
                            extract_canonical_id(oc.name) not in self._seen_ids
                            and (not self.get_file_hash(oc) or self.get_file_hash(oc) not in self._seen_hashes)
                        ):
                            other_unseen.append(oc)

                if other_unseen:
                    logger.info(
                        f"Vibe {vibe.value} local unseen candidates exhausted — "
                        f"borrowing from related unseen pool ({len(other_unseen)} available)."
                    )
                    eligible = other_unseen
                else:
                    logger.warning("All local memes across all folders have been seen! Permanent zero-repeat active.")
                    return None

            chosen = random.choice(eligible)
        else:
            # Standard LRU deduplication
            recent_names = list(self._recent)
            candidate_names = {c.name for c in candidates}
            recent_candidates = [name for name in recent_names[-60:] if name in candidate_names]
            max_forbid = min(len(candidates) - 1, 60) if len(candidates) > 1 else 0
            forbidden_candidates = set(recent_candidates[-max_forbid:]) if max_forbid > 0 else set()

            eligible = [c for c in candidates if c.name not in forbidden_candidates]
            if not eligible:
                eligible = candidates

            never_shown = [c for c in eligible if c.name not in self._last_shown_map]
            if never_shown:
                chosen = random.choice(never_shown)
            else:
                eligible.sort(key=lambda c: self._last_shown_map.get(c.name, 0.0))
                pool_size = max(1, len(eligible) // 3)
                chosen = random.choice(eligible[:pool_size])

        self.record_shown(current_time, chosen)
        logger.info(f"Selected meme: {chosen.name} for vibe {vibe.value} (never_repeat={self.never_repeat})")
        return chosen
