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
from pathlib import Path

from .inference import VibeResult

logger = logging.getLogger(__name__)


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
        self._conn.commit()

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
