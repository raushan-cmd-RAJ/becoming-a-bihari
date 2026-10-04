"""
Unit tests for the Zero-Repeat Meme Engine.
Verifies that:
1. Canonical IDs are extracted accurately across naming patterns (reddit_*, live_*, hash_*).
2. Content SHA-256 hash matching catches identical image bytes regardless of filename.
3. MemeRetriever in never_repeat=True mode strictly disallows repeating any meme.
4. Cross-vibe candidate sharing works when a vibe folder's unseen memes are exhausted.
5. Returns None gracefully when 100% of memes have been shown, without ever recycling.
6. SQLite seen_memes persistence ensures deduplication persists across restarts.
"""

import tempfile
import sqlite3
import pytest
from pathlib import Path
from bihari.logger import extract_canonical_id, VibeLogger
from bihari.memes import MemeRetriever, compute_file_hash
from bihari.inference import Vibe, VIBE_FOLDER_NAMES


class TestNeverRepeatEngine:
    def test_canonical_id_extraction(self):
        """Verify canonical IDs are unified across reddit downloads and live fetches."""
        assert extract_canonical_id("reddit_reactionpics_1vytgiu.png") == "1vytgiu"
        assert extract_canonical_id("live_1vytgiu.png") == "1vytgiu"
        assert extract_canonical_id("reddit_aww_1wtpqwb.png") == "1wtpqwb"
        assert extract_canonical_id("live_1wtpqwb.jpg") == "1wtpqwb"
        assert extract_canonical_id("reddit_dankmemes_abc123_test.webp") == "abc123"
        assert extract_canonical_id("custom_meme_xyz.png") == "custom_meme_xyz"

    def test_file_hash_computation(self, tmp_path):
        """Verify SHA-256 file hashing works accurately."""
        f1 = tmp_path / "img1.png"
        f2 = tmp_path / "img2.png"
        f1.write_bytes(b"image data alpha")
        f2.write_bytes(b"image data alpha")
        
        h1 = compute_file_hash(f1)
        h2 = compute_file_hash(f2)
        assert len(h1) == 64
        assert h1 == h2

        f3 = tmp_path / "img3.png"
        f3.write_bytes(b"different image data beta")
        assert compute_file_hash(f3) != h1

    def test_never_repeat_strict_deduplication(self, tmp_path):
        """Verify MemeRetriever with never_repeat=True never returns a seen meme."""
        meme_dir = tmp_path / "memes"
        vibe_folder = meme_dir / VIBE_FOLDER_NAMES[Vibe.FLOW_STATE]
        vibe_folder.mkdir(parents=True)

        # Create 3 unique dummy memes
        (vibe_folder / "reddit_sub_post1.png").write_bytes(b"content 1")
        (vibe_folder / "reddit_sub_post2.png").write_bytes(b"content 2")
        (vibe_folder / "reddit_sub_post3.png").write_bytes(b"content 3")

        db_file = tmp_path / "test_history.db"
        retriever = MemeRetriever(meme_dir=meme_dir, cooldown_seconds=0, history_db=db_file, never_repeat=True)

        seen = set()
        for i in range(3):
            chosen = retriever.get_meme(Vibe.FLOW_STATE, current_time=100.0 + i, cooldown=0)
            assert chosen is not None
            assert chosen.name not in seen
            seen.add(chosen.name)

        assert len(seen) == 3

        # 4th attempt: all 3 memes have been shown, and no other vibes have memes
        exhausted = retriever.get_meme(Vibe.FLOW_STATE, current_time=200.0, cooldown=0)
        assert exhausted is None, "Should return None instead of repeating any seen meme"

    def test_canonical_id_prevents_duplicate_across_formats(self, tmp_path):
        """If 'reddit_sub_abc.png' has been seen, 'live_abc.png' must never be shown."""
        meme_dir = tmp_path / "memes"
        vibe_folder = meme_dir / VIBE_FOLDER_NAMES[Vibe.LOST_IN_SCROLL]
        vibe_folder.mkdir(parents=True)

        (vibe_folder / "live_abc.png").write_bytes(b"some content")

        db_file = tmp_path / "test_history.db"
        # Pre-seed database with reddit_reactionpics_abc.png
        conn = sqlite3.connect(str(db_file))
        conn.execute("""
            CREATE TABLE seen_memes (
                meme_id TEXT PRIMARY KEY,
                file_hash TEXT,
                filename TEXT,
                shown_at REAL
            )
        """)
        conn.execute(
            "INSERT INTO seen_memes VALUES (?, ?, ?, ?)",
            ("abc", "dummyhash", "reddit_reactionpics_abc.png", 1000.0)
        )
        conn.commit()
        conn.close()

        retriever = MemeRetriever(meme_dir=meme_dir, cooldown_seconds=0, history_db=db_file, never_repeat=True)
        assert "abc" in retriever.seen_ids

        # Attempt to get a meme from LOST_IN_SCROLL — live_abc.png must be excluded!
        chosen = retriever.get_meme(Vibe.LOST_IN_SCROLL, current_time=2000.0, cooldown=0)
        assert chosen is None

    def test_hash_match_prevents_identical_image_with_different_name(self, tmp_path):
        """If an image with different name but identical content hash is shown, it's excluded."""
        meme_dir = tmp_path / "memes"
        vibe_folder = meme_dir / VIBE_FOLDER_NAMES[Vibe.WANDERING]
        vibe_folder.mkdir(parents=True)

        img_bytes = b"exact duplicate binary bytes 9999"
        (vibe_folder / "meme_first.png").write_bytes(img_bytes)
        (vibe_folder / "meme_second.png").write_bytes(img_bytes)

        db_file = tmp_path / "test_history.db"
        retriever = MemeRetriever(meme_dir=meme_dir, cooldown_seconds=0, history_db=db_file, never_repeat=True)

        first_chosen = retriever.get_meme(Vibe.WANDERING, current_time=10.0, cooldown=0)
        assert first_chosen is not None

        # Second call: the other file has the exact same hash, so it should not be chosen!
        second_chosen = retriever.get_meme(Vibe.WANDERING, current_time=20.0, cooldown=0)
        assert second_chosen is None

    def test_cross_vibe_sharing_when_folder_exhausted(self, tmp_path):
        """When a vibe's local memes are all seen, retriever can borrow unseen memes from other folders."""
        meme_dir = tmp_path / "memes"
        zone_folder = meme_dir / VIBE_FOLDER_NAMES[Vibe.FLOW_STATE]
        scroll_folder = meme_dir / VIBE_FOLDER_NAMES[Vibe.LOST_IN_SCROLL]
        zone_folder.mkdir(parents=True)
        scroll_folder.mkdir(parents=True)

        (zone_folder / "zone_meme1.png").write_bytes(b"zone 1")
        (scroll_folder / "scroll_meme1.png").write_bytes(b"scroll 1")

        db_file = tmp_path / "test_history.db"
        retriever = MemeRetriever(meme_dir=meme_dir, cooldown_seconds=0, history_db=db_file, never_repeat=True)

        # 1st call for ZONE: returns zone_meme1.png
        m1 = retriever.get_meme(Vibe.FLOW_STATE, current_time=10.0, cooldown=0)
        assert m1.name == "zone_meme1.png"

        # 2nd call for ZONE: zone folder is exhausted, so it borrows from scroll_folder
        m2 = retriever.get_meme(Vibe.FLOW_STATE, current_time=20.0, cooldown=0)
        assert m2 is not None
        assert m2.name == "scroll_meme1.png"

        # 3rd call: everything is now exhausted!
        m3 = retriever.get_meme(Vibe.FLOW_STATE, current_time=30.0, cooldown=0)
        assert m3 is None

    def test_persistence_across_instances(self, tmp_path):
        """Verify seen memes survive across MemeRetriever restarts via SQLite."""
        meme_dir = tmp_path / "memes"
        vibe_folder = meme_dir / VIBE_FOLDER_NAMES[Vibe.STILLNESS]
        vibe_folder.mkdir(parents=True)

        (vibe_folder / "reddit_zen_pic1.png").write_bytes(b"zen 1")
        (vibe_folder / "reddit_zen_pic2.png").write_bytes(b"zen 2")

        db_file = tmp_path / "test_history.db"

        # Instance 1: Shows pic1
        r1 = MemeRetriever(meme_dir=meme_dir, cooldown_seconds=0, history_db=db_file, never_repeat=True)
        chosen1 = r1.get_meme(Vibe.STILLNESS, current_time=100.0, cooldown=0)
        assert chosen1 is not None

        # Instance 2 (simulating app restart)
        r2 = MemeRetriever(meme_dir=meme_dir, cooldown_seconds=0, history_db=db_file, never_repeat=True)
        assert extract_canonical_id(chosen1.name) in r2.seen_ids

        chosen2 = r2.get_meme(Vibe.STILLNESS, current_time=200.0, cooldown=0)
        assert chosen2 is not None
        assert chosen2.name != chosen1.name
