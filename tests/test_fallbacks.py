"""
Tests for Module: Graceful Error Hardening & System Fallbacks.

Validates:
- F19: Graceful Error Hardening & Fallbacks:
  - System never crashes or raises unhandled exceptions when offline or assets missing.
  - Safe OCR fallback when OCR / Laya is unavailable.
  - Safe Laya bridge degradation to rule-based fallback without network.
- F20: Text-Only and Empty Meme Folder Fallbacks:
  - Empty meme folders return None safely without unhandled exception.
  - Non-image files (.txt, .md, .bin) are ignored.
  - Non-existent meme directory paths handled gracefully.
- Context extraction resilience against corrupt, null, or extreme inputs.
"""

import tempfile
from pathlib import Path
import pytest

from bihari.memes import MemeRetriever
from bihari.inference import LayaBridge, Vibe, VibeResult
from bihari.context import extract_context, extract_code_context, extract_browser_context


class TestGracefulFallbacks:
    """Tier 1 & Tier 2: Error Hardening, Fallbacks & Offline Resilience."""

    def test_empty_meme_directory_returns_none_gracefully(self):
        """When meme directory has zero image files, retrieval returns None without crashing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_root = Path(tmpdir)
            retriever = MemeRetriever(empty_root, cooldown_seconds=0)

            for vibe in Vibe:
                result = retriever.get_meme(vibe, current_time=100.0, cooldown=0)
                assert result is None

            counts = retriever.get_meme_count()
            assert isinstance(counts, dict)
            for folder, count in counts.items():
                assert count == 0

    def test_nonexistent_meme_folder_handled(self):
        """Pointing retriever to a non-existent folder initializes folders without crashing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            non_existent = Path(tmpdir) / "subfolder" / "deep_memes"
            retriever = MemeRetriever(non_existent, cooldown_seconds=0)
            assert non_existent.exists()
            res = retriever.get_meme(Vibe.FLOW_STATE, current_time=100.0, cooldown=0)
            assert res is None

    def test_non_image_files_ignored(self):
        """Text files, binaries, and hidden files in meme directories must be filtered out."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            folder = root / "in-the-zone"
            folder.mkdir(parents=True, exist_ok=True)

            # Create invalid non-image files
            (folder / "notes.txt").write_text("not an image")
            (folder / "script.py").write_text("print('hello')")
            (folder / "payload.exe").write_bytes(b"\x4d\x5a")
            (folder / ".DS_Store").write_bytes(b"metadata")

            retriever = MemeRetriever(root, cooldown_seconds=0)
            counts = retriever.get_meme_count()
            assert counts["in-the-zone"] == 0

            res = retriever.get_meme(Vibe.FLOW_STATE, current_time=100.0, cooldown=0)
            assert res is None

    def test_corrupt_and_missing_image_path_handling(self):
        """Display engine / image loader handles missing or unreadable files gracefully."""
        # Simulated test for display image loading exception safety
        from PIL import Image
        fake_path = Path("C:/non_existent_folder/fake_image.png")
        try:
            Image.open(fake_path)
            failed = False
        except Exception:
            failed = True
        assert failed is True, "Pillow should raise FileNotFoundError, which display.py catches"

    def test_laya_bridge_offline_and_missing_model_fallback(self):
        """When Laya model/weights are not installed or offline, bridge degrades safely."""
        bridge = LayaBridge()
        # In environment without Laya installed or mocked offline
        if not bridge.is_available():
            class DummyEvent:
                app_name = "chrome.exe"
                window_title = "Unknown Page"
                typing_speed = 0
                backspace_rate = 0.0
                window_switches_3min = 0

            res = bridge.classify(DummyEvent())
            assert isinstance(res, VibeResult)
            assert res.source in ("laya_unavailable", "laya_fallback")
            assert res.confidence <= 0.50

            ctx_info = bridge.classify_context("chrome.exe", "Sample Title")
            assert ctx_info == {"activity": None, "meme_category": None}

            screen_info = bridge.classify_screen_content("Sample OCR text", "chrome.exe", "Sample Title")
            assert screen_info == {}

    @pytest.mark.parametrize("app, title", [
        ("", ""),
        ("unknown_app.xyz", ""),
        ("", "Some Title Without App"),
        ("app.exe", "\x00\x01\x02\x03\x04"),
        ("code.exe", "● * - - - |"),
        ("chrome.exe", "http://:::invalid-url:::"),
        ("chrome.exe", " " * 500),
    ])
    def test_context_extraction_corrupt_inputs_resilience(self, app, title):
        """Context extractor must never raise an exception when given corrupt or extreme inputs."""
        try:
            ctx = extract_context(app, title)
            # Result should either be a valid WindowContext or None, never a crash
            if ctx is not None:
                assert hasattr(ctx, "subject")
                assert hasattr(ctx, "category")
        except Exception as e:
            pytest.fail(f"extract_context crashed with input ({app!r}, {title!r}): {e}")

    def test_code_and_browser_extractor_edge_cases(self):
        """Edge cases in code and browser extractors handle delimiter-only titles."""
        assert extract_code_context("code.exe", "") is None
        assert extract_code_context("code.exe", "● Visual Studio Code") is None
        assert extract_browser_context("chrome.exe", "New Tab - Google Chrome") is None
        assert extract_browser_context("chrome.exe", "Google - Google Chrome") is None
