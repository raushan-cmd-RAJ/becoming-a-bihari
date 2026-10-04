"""
SQLite-based vibe history logger.

Records every classification event so the user can later answer
questions like "what was my vibe today?" or "how productive was I
this week?"

Thread-safety: Uses check_same_thread=False with serialized writes.
"""

import sqlite3
import time
import logging
import re
from pathlib import Path
from typing import Optional, Union

from .inference import VibeResult

logger = logging.getLogger(__name__)


def extract_canonical_id(path_or_name: Union[str, Path]) -> str:
    """
    Extract canonical Reddit Post ID or normalized stem from a meme filename.
    Unifies e.g.:
      'reddit_reactionpics_1vytgiu.png' -> '1vytgiu'
      'live_1vytgiu.png'                -> '1vytgiu'
      'reddit_wunkus_1wuok5r.gif'       -> '1wuok5r'
      'live_1wuok5r.gif'                -> '1wuok5r'
      'reddit_dankmemes_abc123_test.webp' -> 'abc123'
    """
    stem = Path(path_or_name).stem
    if stem.startswith("reddit_"):
        parts = stem.split("_")
        if len(parts) >= 3:
            return parts[2].lower()
    elif stem.startswith("live_"):
        parts = stem.split("_", 1)
        if len(parts) >= 2:
            return parts[1].lower()
    return stem.lower()


class VibeLogger:
    """Persistent vibe history stored in a local SQLite database."""

    def __init__(self, db_path: Path):
        """
        Args:
            db_path: Path to the SQLite database file.
                     Parent directories are created if they don't exist.
        """
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")  # Better concurrent reads
        self._create_tables()
        logger.info(f"Vibe logger initialized: {db_path}")

    def _create_tables(self):
        """Create the schema if it doesn't exist."""
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS vibe_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                app_name TEXT NOT NULL,
                window_title TEXT,
                vibe TEXT NOT NULL,
                confidence REAL NOT NULL,
                source TEXT NOT NULL,
                trigger_reason TEXT,
                meme_shown TEXT
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_vibe_log_timestamp 
            ON vibe_log(timestamp)
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS seen_memes (
                meme_id TEXT PRIMARY KEY,
                file_hash TEXT,
                filename TEXT,
                shown_at REAL
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_seen_memes_hash
            ON seen_memes(file_hash)
        """)
        self._conn.commit()
        self._migrate_existing_seen()

    def _migrate_existing_seen(self):
        """Populate seen_memes from vibe_log so existing history is preserved."""
        try:
            cursor = self._conn.execute(
                "SELECT DISTINCT meme_shown, timestamp FROM vibe_log "
                "WHERE meme_shown IS NOT NULL AND meme_shown != ''"
            )
            rows = cursor.fetchall()
            for filename, ts in rows:
                if filename:
                    cid = extract_canonical_id(filename)
                    self._conn.execute(
                        "INSERT OR IGNORE INTO seen_memes (meme_id, file_hash, filename, shown_at) "
                        "VALUES (?, ?, ?, ?)",
                        (cid, "", filename, float(ts) if ts else time.time()),
                    )
            self._conn.commit()
        except sqlite3.Error as e:
            logger.warning(f"Could not migrate seen_memes: {e}")

    def record_seen_meme(self, meme_id: str, file_hash: str = "", filename: str = ""):
        """Record that a meme has been shown to prevent repeat sightings forever."""
        try:
            self._conn.execute(
                "INSERT OR REPLACE INTO seen_memes (meme_id, file_hash, filename, shown_at) "
                "VALUES (?, ?, ?, ?)",
                (meme_id.lower(), file_hash.lower(), filename, time.time()),
            )
            self._conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to record seen meme: {e}")

    def get_all_seen_memes(self) -> tuple[set[str], set[str]]:
        """Return (seen_ids, seen_hashes) for all memes ever shown in history."""
        try:
            cursor = self._conn.execute("SELECT meme_id, file_hash FROM seen_memes")
            rows = cursor.fetchall()
            ids = {r[0].lower() for r in rows if r[0]}
            hashes = {r[1].lower() for r in rows if r[1]}
            return ids, hashes
        except sqlite3.Error as e:
            logger.error(f"Failed to fetch seen memes: {e}")
            return set(), set()

    def log(
        self,
        app_name: str,
        window_title: str,
        result: VibeResult,
        trigger: str,
        meme_shown: str | None = None,
    ):
        """
        Record a classification event.

        Args:
            app_name: The active application name.
            window_title: The sanitized window title.
            result: The VibeResult from the classifier.
            trigger: What triggered this event (window_change, backspace_spike, etc.)
            meme_shown: Filename of the meme shown, or None if no meme was triggered.
        """
        try:
            self._conn.execute(
                "INSERT INTO vibe_log "
                "(timestamp, app_name, window_title, vibe, confidence, source, trigger_reason, meme_shown) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    time.time(),
                    app_name,
                    window_title,
                    result.vibe.value,
                    result.confidence,
                    result.source,
                    trigger,
                    meme_shown,
                ),
            )
            self._conn.commit()
            if meme_shown:
                self.record_seen_meme(extract_canonical_id(meme_shown), filename=meme_shown)
        except sqlite3.Error as e:
            logger.error(f"Failed to log vibe: {e}")

    def get_summary(self, hours: float = 24) -> dict[str, int]:
        """
        Get a vibe frequency summary for the last N hours.

        Returns:
            Dict mapping vibe names to occurrence counts.
        """
        cutoff = time.time() - (hours * 3600)
        cursor = self._conn.execute(
            "SELECT vibe, COUNT(*) FROM vibe_log WHERE timestamp > ? GROUP BY vibe",
            (cutoff,),
        )
        return dict(cursor.fetchall())

    def close(self):
        """Close the database connection."""
        try:
            self._conn.close()
            logger.info("Vibe logger closed.")
        except Exception:
            pass
