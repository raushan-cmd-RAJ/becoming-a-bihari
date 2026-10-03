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
from pathlib import Path
from typing import Any, Optional

from .inference import Vibe, VIBE_FOLDER_NAMES

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
    ):
        """
        Args:
            meme_dir: Root directory containing vibe subfolders.
            cooldown_seconds: Minimum seconds between meme displays.
            history_db: Path to vibe_history.db for persistent cross-session deduplication.
            pack_manager: Optional PackManager instance for loaded .lucidpack memes.
        """
        self.meme_dir = Path(meme_dir)
        self.cooldown = cooldown_seconds
        self.pack_manager = pack_manager

        # Track recently shown memes to avoid repeats (persisted across restarts)
        self._recent: collections.deque = collections.deque(maxlen=100)
        self._last_shown_time: float = 0

        self._last_shown_map: dict[str, float] = {}

        # Load recent meme history from SQLite if available
        if history_db and Path(history_db).exists():
            try:
                import sqlite3
                conn = sqlite3.connect(str(history_db), timeout=2.0)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT meme_shown, timestamp FROM vibe_log "
                    "WHERE meme_shown IS NOT NULL AND meme_shown != '' "
                    "ORDER BY id ASC"
                )
                rows = cursor.fetchall()
                conn.close()
                for (m_name, ts) in rows:
                    if m_name:
                        self._recent.append(m_name)
                        try:
                            self._last_shown_map[m_name] = float(ts)
                        except (ValueError, TypeError):
                            self._last_shown_map[m_name] = 0.0
                logger.info(f"Loaded {len(rows)} recent memes from history database for persistent deduplication.")
            except Exception as e:
                logger.warning(f"Could not load meme history from DB: {e}")

        # Ensure folder structure exists on init
        self._ensure_folders()

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
            readme_path.write_text(
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
                "    just-wandering/       — doing everything except the thing\n"
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
                "More memes = more variety!\n",
                encoding="utf-8",
            )
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
        """Record that a meme was shown (e.g. from live search) and track it in recent history."""
        self._last_shown_time = current_time
        if meme_path:
            name = Path(meme_path).name
            self._recent.append(name)
            self._last_shown_map[name] = current_time

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
        # This dramatically expands the pool to 170+ memes so candidate exhaustion is eliminated.
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

        # Strict deduplication: forbid memes shown in the immediate recent window
        # Safety window: prevent showing any meme shown in the last N events (up to 60)
        safety_window = min(len(candidates) - 1, 60) if len(candidates) > 1 else 0
        recent_list = list(self._recent)
        forbidden_names = set(recent_list[-safety_window:]) if safety_window > 0 else set()

        eligible = [c for c in candidates if c.name not in forbidden_names]
        if not eligible:
            eligible = candidates

        # 1. First priority: Candidates NEVER shown before at all
        never_shown = [c for c in eligible if c.name not in self._last_shown_map]
        if never_shown:
            chosen = random.choice(never_shown)
        else:
            # 2. Second priority: Truly Least Recently Used by timestamp
            # Sort ascending by last shown timestamp (oldest first)
            eligible.sort(key=lambda c: self._last_shown_map.get(c.name, 0.0))
            # Pick randomly from the oldest 30% to maintain healthy variety
            pool_size = max(1, len(eligible) // 3)
            chosen = random.choice(eligible[:pool_size])

        self._recent.append(chosen.name)
        self._last_shown_map[chosen.name] = current_time
        self._last_shown_time = current_time

        logger.info(f"Selected meme: {chosen.name} for vibe {vibe.value}")
        return chosen
