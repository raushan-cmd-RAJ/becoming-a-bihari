"""
Unit tests for ONNX Semantic Decision Intelligence (Option B) and Option A fallback hierarchy.
"""

import unittest
from dataclasses import dataclass
from bihari.inference import Vibe, VibeClassifier, VibeResult
from bihari.onnx_brain import ONNXBrain, SimpleWordPieceTokenizer, HAS_ORT


@dataclass
class MockTelemetryEvent:
    app_name: str
    window_title: str
    typing_speed: float = 35.0
    backspace_rate: float = 0.04
    backspace_count: int = 1
    window_switches_3min: int = 1
    dwell_minutes: float = 3.0
    session_minutes: float = 15.0
    idle_seconds: float = 0.0
    hour_of_day: int = 11


class TestONNXBrain(unittest.TestCase):

    def setUp(self):
        self.brain = ONNXBrain()

    def test_availability(self):
        if HAS_ORT:
            self.assertTrue(self.brain.is_available())
        else:
            self.assertFalse(self.brain.is_available())

    def test_powershell_terminal_flow_state(self):
        if not self.brain.is_available():
            self.skipTest("onnxruntime or ONNX model not present")

        event = MockTelemetryEvent(
            app_name="powershell.exe",
            window_title="Administrator: Windows PowerShell - git status && pytest tests/",
            typing_speed=38.0,
            backspace_rate=0.03,
            dwell_minutes=2.0,
        )
        res = self.brain.classify_vibe(event)
        self.assertIsInstance(res, VibeResult)
        self.assertEqual(res.vibe, Vibe.FLOW_STATE)
        self.assertTrue(res.confidence >= 0.70)
        self.assertEqual(res.source, "onnx_brain")

    def test_syntax_rage_terminal_compiler_error(self):
        if not self.brain.is_available():
            self.skipTest("onnxruntime or ONNX model not present")

        event = MockTelemetryEvent(
            app_name="powershell.exe",
            window_title="cargo build --release - failed with 14 errors SyntaxError",
            typing_speed=40.0,
            backspace_rate=0.36,
            dwell_minutes=3.0,
        )
        res = self.brain.classify_vibe(event)
        self.assertEqual(res.vibe, Vibe.SYNTAX_RAGE)
        self.assertTrue(res.confidence >= 0.70)

    def test_browser_reddit_lost_in_scroll(self):
        if not self.brain.is_available():
            self.skipTest("onnxruntime or ONNX model not present")

        event = MockTelemetryEvent(
            app_name="chrome.exe",
            window_title="Reddit: The heart of the internet - r/funny memes and video clips",
            typing_speed=0.0,
            backspace_rate=0.0,
            dwell_minutes=8.0,
        )
        res = self.brain.classify_vibe(event)
        self.assertEqual(res.vibe, Vibe.LOST_IN_SCROLL)
        self.assertTrue(res.confidence >= 0.65)

    def test_browser_stackoverflow_help_seeking(self):
        if not self.brain.is_available():
            self.skipTest("onnxruntime or ONNX model not present")

        event = MockTelemetryEvent(
            app_name="chrome.exe",
            window_title="python - TypeError: Object is not callable - Stack Overflow",
            typing_speed=12.0,
            backspace_rate=0.02,
            dwell_minutes=4.0,
        )
        res = self.brain.classify_vibe(event)
        self.assertEqual(res.vibe, Vibe.HELP_SEEKING)
        self.assertTrue(res.confidence >= 0.60)

    def test_pure_python_tokenizer_fallback(self):
        vocab_file = self.brain.vocab_path
        if not vocab_file.exists():
            self.skipTest("vocab.txt not found")

        tok = SimpleWordPieceTokenizer(vocab_file)
        ids, mask = tok.encode("Windows Terminal - cargo build")
        self.assertEqual(len(ids), 128)
        self.assertEqual(len(mask), 128)
        self.assertTrue(sum(mask) > 0)
        self.assertEqual(ids[0], tok.cls_id)

    def test_hybrid_hierarchy_fallback_to_microbrain(self):
        # Classifier with ONNX disabled to verify Option A fallback
        classifier = VibeClassifier(use_laya=False)
        classifier.onnx_brain = None  # simulate ONNX missing

        event = MockTelemetryEvent(
            app_name="powershell.exe",
            window_title="Administrator: Windows PowerShell - git status && pytest tests/",
            typing_speed=38.0,
            backspace_rate=0.03,
            dwell_minutes=2.0,
        )
        res = classifier.classify(event)
        self.assertIsNotNone(res)
        self.assertEqual(res.vibe, Vibe.FLOW_STATE)
        self.assertEqual(res.source, "micro_brain")


if __name__ == "__main__":
    unittest.main()
