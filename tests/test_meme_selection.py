"""
Tests for Module: Meme Selection & Anti-Repetition LRU Window.

Validates:
- F6: 60-Event Anti-Repetition LRU Window (100-event simulation with 0 repeats in any 60-event window).
- Boundary safety windows for small candidate pools (N candidates -> safety window N-1).
- Single candidate handling (no deadlocks or exceptions).
- Empty folder handling (returns None gracefully).
- Cooldown gating and timestamp management.
- Cross-vibe pooling for browsing/scrolling vibes.
- Persistent history DB loading across restarts.
"""

import tempfile
import sqlite3
from pathlib import Path
import pytest

from bihari.memes import MemeRetriever
from bihari.inference import Vibe, VIBE_FOLDER_NAMES


@pytest.fixture
def temp_meme_env():
    """Create a temporary directory structure for meme testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        yield root


class TestMemeSelection:
    """Tier 1, 2 & 4: Meme Selection & Anti-Repetition Simulation."""

    def test_100_event_simulation_zero_repeats_in_60_window(self, temp_meme_env):
        """
        F6 Contract:
        Running a 100-event simulation against a pool of >=61 candidates
        guarantees ZERO repeated memes within any 60-event sliding window.
        """
        vibe = Vibe.FLOW_STATE
        folder = temp_meme_env / VIBE_FOLDER_NAMES[vibe]
        folder.mkdir(parents=True, exist_ok=True)

        # Create 70 unique candidate meme image files
        total_candidates = 70
        for i in range(total_candidates):
            (folder / f"focus_meme_{i:03d}.png").write_bytes(b"STUB_IMAGE_DATA")

        retriever = MemeRetriever(temp_meme_env, cooldown_seconds=0)

        # Simulate 100 consecutive retrieval events
        history = []
        simulated_time = 1000.0
        for _ in range(100):
            selected = retriever.get_meme(vibe, current_time=simulated_time, cooldown=0)
            assert selected is not None, "Meme must be returned when eligible candidates exist"
            history.append(selected.name)
            simulated_time += 1.0

        assert len(history) == 100

        # Assert zero duplicates in every 60-event window
        window_size = 60
        num_windows = len(history) - window_size + 1
        for i in range(num_windows):
            window = history[i : i + window_size]
            unique_memes = set(window)
            assert len(unique_memes) == window_size, (
                f"Window {i} contains duplicates! Unique {len(unique_memes)} vs Expected {window_size}."
            )

    def test_small_pool_safety_window(self, temp_meme_env):
        """When candidate pool is smaller than 60 (e.g. 5), safety window is N-1 (4)."""
        vibe = Vibe.SYNTAX_RAGE
        folder = temp_meme_env / VIBE_FOLDER_NAMES[vibe]
        folder.mkdir(parents=True, exist_ok=True)

        # 5 candidates -> safety window min(5-1, 60) = 4
        for i in range(5):
            (folder / f"rage_{i}.jpg").write_bytes(b"STUB_JPG")

        retriever = MemeRetriever(temp_meme_env, cooldown_seconds=0)
        history = []
        sim_time = 100.0
        for _ in range(25):
            m = retriever.get_meme(vibe, current_time=sim_time, cooldown=0)
            assert m is not None
            history.append(m.name)
            sim_time += 1.0

        # Every 4-event window must have 4 unique memes
        for i in range(len(history) - 4 + 1):
            window = history[i : i + 4]
            assert len(set(window)) == 4, f"Duplicate detected in 4-event window: {window}"

    def test_single_candidate_pool(self, temp_meme_env):
        """A folder with exactly 1 meme must safely return it without hanging or crashing."""
        vibe = Vibe.STILLNESS
        folder = temp_meme_env / VIBE_FOLDER_NAMES[vibe]
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "only_one.png").write_bytes(b"STUB")

        retriever = MemeRetriever(temp_meme_env, cooldown_seconds=0)
        for t in range(5):
            m = retriever.get_meme(vibe, current_time=float(t), cooldown=0)
            assert m is not None
            assert m.name == "only_one.png"

    def test_empty_candidate_folder(self, temp_meme_env):
        """An empty vibe folder returns None safely without raising exceptions."""
        retriever = MemeRetriever(temp_meme_env, cooldown_seconds=0)
        m = retriever.get_meme(Vibe.HELP_SEEKING, current_time=100.0, cooldown=0)
        assert m is None

    def test_cooldown_enforcement(self, temp_meme_env):
        """Cooldown prevents showing memes too frequently unless elapsed time >= cooldown."""
        vibe = Vibe.GRINDING
        folder = temp_meme_env / VIBE_FOLDER_NAMES[vibe]
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "grind.png").write_bytes(b"STUB")

        cooldown = 120.0
        retriever = MemeRetriever(temp_meme_env, cooldown_seconds=int(cooldown))

        # First request at t=1000.0 -> succeeds
        m1 = retriever.get_meme(vibe, current_time=1000.0)
        assert m1 is not None

        # Second request at t=1060.0 (before 120s cooldown elapsed) -> blocked
        m2 = retriever.get_meme(vibe, current_time=1060.0)
        assert m2 is None

        # Third request at t=1120.1 -> succeeds
        m3 = retriever.get_meme(vibe, current_time=1120.1)
        assert m3 is not None

    def test_cross_vibe_pooling_for_browsing(self, temp_meme_env):
        """Browsing/scrolling vibes expand candidate pool across related reaction folders."""
        scroll_folder = temp_meme_env / VIBE_FOLDER_NAMES[Vibe.LOST_IN_SCROLL]
        scroll_folder.mkdir(parents=True, exist_ok=True)
        (scroll_folder / "scroll_1.png").write_bytes(b"STUB")

        # Put related memes in wandering folder
        wander_folder = temp_meme_env / VIBE_FOLDER_NAMES[Vibe.WANDERING]
        wander_folder.mkdir(parents=True, exist_ok=True)
        for i in range(10):
            (wander_folder / f"wander_{i}.png").write_bytes(b"STUB")

        retriever = MemeRetriever(temp_meme_env, cooldown_seconds=0)

        # Retrieve multiple memes for LOST_IN_SCROLL; should pull from both folders
        picked_names = set()
        for t in range(15):
            m = retriever.get_meme(Vibe.LOST_IN_SCROLL, current_time=float(t), cooldown=0)
            if m:
                picked_names.add(m.name)

        # Confirm memes from the related folder were successfully eligible and picked
        wander_picked = [name for name in picked_names if name.startswith("wander_")]
        assert len(wander_picked) > 0, "Cross-pooling must include related vibe memes"

    def test_sqlite_history_db_loading(self, temp_meme_env):
        """Persistent DB history is loaded into LRU cache on retriever initialization."""
        db_path = temp_meme_env / "vibe_history.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute(
            "CREATE TABLE vibe_log (id INTEGER PRIMARY KEY, meme_shown TEXT, timestamp TEXT)"
        )
        # Seed 10 previous memes
        for i in range(10):
            cursor.execute(
                "INSERT INTO vibe_log (meme_shown, timestamp) VALUES (?, ?)",
                (f"past_meme_{i}.png", str(100.0 + i)),
            )
        conn.commit()
        conn.close()

        retriever = MemeRetriever(temp_meme_env, cooldown_seconds=0, history_db=db_path)
        assert len(retriever._recent) == 10
        assert "past_meme_0.png" in retriever._recent
        assert "past_meme_9.png" in retriever._recent
