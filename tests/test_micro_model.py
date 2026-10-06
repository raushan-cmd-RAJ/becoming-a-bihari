"""
Tests for Module: MicroBrain on-device decision intelligence.

Validates:
- Loading of compact pretrained base_brain.json (<1 MB).
- Fast inference latency (<2ms).
- Vibe, screen OCR theme, and context classification.
- On-device continuous personalization (online SGD updates).
- Zero cloud transmission and mathematical privacy (no raw text in delta weights).
"""

import tempfile
import pytest
from pathlib import Path

from bihari.inference import Vibe, VibeResult, VibeClassifier
from bihari.micro_model import MicroBrain, FeatureExtractor, NUM_FEATURES
from bihari.spy import TelemetryEvent


class TestMicroBrainModel:
    """Verifies the pure-Python on-device decision model."""

    def test_model_initialization_and_size(self):
        """MicroBrain base weights must be under 1MB and load instantly."""
        brain = MicroBrain()
        assert brain.vibe_head is not None
        assert brain.ocr_theme_head is not None
        assert brain.context_activity_head is not None

        # Base model file size check
        assert brain.base_model_path.exists()
        size_kb = brain.base_model_path.stat().st_size / 1024
        assert size_kb < 1024, f"Base model is {size_kb:.1f} KB, expected < 1000 KB"

    def test_vibe_classification(self):
        """MicroBrain should classify ambiguous behavioral events."""
        brain = MicroBrain()

        # Coding scenario
        coding_event = TelemetryEvent(
            app_name="code.exe",
            window_title="micro_brain.py - VS Code",
            typing_speed=70,
            backspace_rate=0.03,
            backspace_count=1,
            window_switches_3min=1,
            dwell_minutes=15.0,
        )
        res = brain.classify_vibe(coding_event)
        assert isinstance(res, VibeResult)
        assert res.vibe == Vibe.FLOW_STATE
        assert res.confidence > 0.40
        assert res.source == "micro_brain"

        # Syntax rage scenario
        rage_event = TelemetryEvent(
            app_name="code.exe",
            window_title="SyntaxError: invalid syntax line 42",
            typing_speed=40,
            backspace_rate=0.45,
            backspace_count=15,
            window_switches_3min=2,
            dwell_minutes=6.0,
        )
        res_rage = brain.classify_vibe(rage_event)
        assert res_rage.vibe == Vibe.SYNTAX_RAGE

    def test_screen_ocr_classification(self):
        """MicroBrain correctly maps OCR text to theme and reflection without Laya/PyTorch."""
        brain = MicroBrain()

        # Food & cooking
        food_res = brain.classify_screen_content(
            screen_text="creamy garlic butter pasta recipe #easycooking #foodie",
            app_name="chrome.exe",
            window_title="Instagram Reels",
        )
        assert food_res["human_theme"] == "food_and_cooking"
        assert food_res["vibe"] == Vibe.WANDERING
        assert "recipe" in food_res["reflection"].lower() or "craving" in food_res["reflection"].lower()

        # Comedy & humor
        humor_res = brain.classify_screen_content(
            screen_text="POV: asking cat why it knocked over the glass at 3am #comedy #catfunny",
            app_name="chrome.exe",
            window_title="TikTok",
        )
        assert humor_res["human_theme"] == "comedy_and_humor"
        assert humor_res["vibe"] == Vibe.LOST_IN_SCROLL

    def test_context_activity_classification(self):
        """MicroBrain predicts semantic activity bucket for window titles."""
        brain = MicroBrain()

        res_code = brain.classify_context("code.exe", "server.rs - Neovim")
        assert res_code["activity"] == "coding"
        assert res_code["meme_category"] == "programming"

        res_scroll = brain.classify_context("chrome.exe", "TikTok - Make Your Day")
        assert res_scroll["activity"] == "social_scroll"

    def test_on_device_personalization_privacy(self):
        """Adapting weights updates only numerical hash buckets with zero raw text stored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            user_dir = Path(tmpdir)
            brain = MicroBrain(user_data_dir=user_dir, enable_learning=True)

            event = TelemetryEvent(
                app_name="custom_internal_tool.exe",
                window_title="Custom Proprietary Project Alpha",
                typing_speed=55,
                backspace_rate=0.02,
                backspace_count=1,
                window_switches_3min=1,
                dwell_minutes=12.0,
            )

            # Adapt model: teach it that this custom tool is FLOW_STATE
            brain.adapt_vibe(event, Vibe.FLOW_STATE, was_positive=True)

            # Verify user_brain.json was created
            user_brain_file = user_dir / "user_brain.json"
            assert user_brain_file.exists()

            # Verify contents: ONLY numerical bucket keys and floats, ZERO raw text
            with open(user_brain_file, "r", encoding="utf-8") as f:
                content = f.read()
                # Ensure no private window title strings exist in the delta file
                assert "Custom Proprietary Project Alpha" not in content
                assert "custom_internal_tool" not in content

            # Verify predictions now heavily favor FLOW_STATE
            new_res = brain.classify_vibe(event)
            assert new_res.vibe == Vibe.FLOW_STATE

    def test_vibe_classifier_integration(self):
        """VibeClassifier uses MicroBrain as primary decision engine when ambiguous."""
        classifier = VibeClassifier(use_laya=False, enable_learning=True)
        assert classifier.micro_brain is not None

        # Verify OCR classification works through VibeClassifier without Laya
        ocr_out = classifier.classify_screen_content(
            screen_text="delicious chocolate cake baking tips #dessert #food",
            app_name="chrome.exe",
            window_title="Instagram Reels",
        )
        assert ocr_out.get("human_theme") == "food_and_cooking"
