"""
Tests for Module: Detection & Inference Pipeline.

Validates:
- F1: Flow State Zero-Interruption Gate (>50 cpm, <8% bs, >=10 min dwell -> suppressed).
- F2: Lost-In-Scroll video precedence (>3 min YouTube, 0 typing -> video context over stillness).
- F3: Syntax Rage coding frustration mirror (>35% backspaces in editor -> compiler/coding caption).
- Classification of all 12 vibes across intensity, frustration, avoidance, and downtime.
- Meeting suppression (Zoom/Teams returns None to prevent interruptions).
- Boundary conditions and edge cases in telemetry inputs.
"""

import pytest
from bihari.inference import (
    classify_by_rules,
    Vibe,
    VibeResult,
    get_reflection,
    is_flow_gate_suppressed,
    SHORT_VIDEO_REFLECTIONS,
    SHORT_PUNCHY_REFLECTIONS,
)
from bihari.context import extract_context, WindowContext
from bihari.spy import TelemetryEvent


class TestDetectionAndFlowGate:
    """Tier 1, 2 & 3: Behavioral Detection & Flow Gate Verification."""

    def test_flow_state_classification(self):
        """High typing speed and low error rate in code editor classifies as FLOW_STATE."""
        event = TelemetryEvent(
            app_name="code.exe",
            window_title="auth_service.py - Visual Studio Code",
            typing_speed=65,
            backspace_rate=0.04,
            backspace_count=2,
            window_switches_3min=1,
            dwell_minutes=15.0,
        )
        res = classify_by_rules(event)
        assert res is not None
        assert res.vibe == Vibe.FLOW_STATE
        assert res.confidence >= 0.80

    def test_flow_state_gate_suppresses_popups(self):
        """F1: When user is in intense flow (>50 cpm, <8% bs, >=10 min dwell), popups are suppressed."""
        event = TelemetryEvent(
            app_name="code.exe",
            window_title="engine.rs - Alacritty",
            typing_speed=72,
            backspace_rate=0.03,
            backspace_count=2,
            window_switches_3min=0,
            dwell_minutes=12.5,
        )
        res = classify_by_rules(event)
        assert res is not None
        assert res.vibe == Vibe.FLOW_STATE
        assert is_flow_gate_suppressed(event, res) is True

    @pytest.mark.parametrize("speed, bs_rate, dwell, expected_suppressed", [
        (50.0, 0.05, 12.0, False),   # Speed boundary: must be strictly > 50
        (50.1, 0.05, 12.0, True),    # Just above 50 cpm
        (75.0, 0.08, 12.0, False),   # Backspace boundary: must be strictly < 0.08
        (75.0, 0.079, 12.0, True),   # Just below 8%
        (75.0, 0.04, 9.9, False),    # Dwell boundary: must be >= 10.0 minutes
        (75.0, 0.04, 10.0, True),    # Exactly 10.0 minutes
        (30.0, 0.02, 15.0, False),   # Low speed -> not suppressed by gate
        (80.0, 0.20, 15.0, False),   # High error rate -> not suppressed by gate
    ])
    def test_flow_state_gate_boundaries(self, speed, bs_rate, dwell, expected_suppressed):
        """Boundary values for speed, backspace rate, and dwell time."""
        event = TelemetryEvent(
            app_name="code.exe",
            window_title="main.py - Visual Studio Code",
            typing_speed=speed,
            backspace_rate=bs_rate,
            backspace_count=int(speed * bs_rate),
            window_switches_3min=1,
            dwell_minutes=dwell,
        )
        res = classify_by_rules(event)
        suppressed = is_flow_gate_suppressed(event, res)
        assert suppressed == expected_suppressed

    def test_lost_in_scroll_video_context_precedence(self):
        """F2: YouTube video watching with 0 typing classifies as LOST_IN_SCROLL, not STILLNESS."""
        event = TelemetryEvent(
            app_name="chrome.exe",
            window_title="Building an OS in Rust - YouTube",
            typing_speed=0,
            backspace_rate=0.0,
            backspace_count=0,
            window_switches_3min=0,
            dwell_minutes=4.5,
        )
        res = classify_by_rules(event)
        assert res is not None
        assert res.vibe == Vibe.LOST_IN_SCROLL
        assert res.source == "rules"

        # Context extractor must parse this as category='video'
        ctx = extract_context("chrome.exe", "Building an OS in Rust - YouTube")
        assert ctx is not None
        assert ctx.category == "video"
        assert ctx.is_specific is True
        assert "OS in Rust" in ctx.subject or "Building" in ctx.subject

        # Reflection generation must produce video-specific reaction or punchline
        reflection = get_reflection(Vibe.LOST_IN_SCROLL, context=ctx)
        assert len(reflection) < 40
        from bihari.inference import (
            SHORT_VIDEO_REFLECTIONS_TRACK_B,
            SHORT_PUNCHY_REFLECTIONS_TRACK_B,
        )
        all_punchy = SHORT_PUNCHY_REFLECTIONS + SHORT_PUNCHY_REFLECTIONS_TRACK_B
        all_prefixes = [t.split("{")[0] for t in SHORT_VIDEO_REFLECTIONS + SHORT_VIDEO_REFLECTIONS_TRACK_B]
        is_valid_video_reflection = (
            reflection in all_punchy
            or any(reflection.startswith(prefix) for prefix in all_prefixes)
        )
        assert is_valid_video_reflection is True

    def test_syntax_rage_coding_frustration(self):
        """F3: Coding app with >35% backspaces classifies as SYNTAX_RAGE with coding-specific reflections."""
        event = TelemetryEvent(
            app_name="code.exe",
            window_title="auth_handler.py - Visual Studio Code",
            typing_speed=32,
            backspace_rate=0.42,
            backspace_count=18,
            window_switches_3min=1,
            dwell_minutes=5.0,
        )
        res = classify_by_rules(event)
        assert res is not None
        assert res.vibe == Vibe.SYNTAX_RAGE
        assert res.confidence >= 0.70

        ctx = extract_context("code.exe", "auth_handler.py - Visual Studio Code")
        assert ctx is not None
        assert ctx.category == "code"
        assert "auth_handler.py" in ctx.subject

        reflection_bihari = get_reflection(Vibe.SYNTAX_RAGE, context=ctx, brand_track="bihari")
        assert len(reflection_bihari) < 40
        assert "auth_handler.py" in reflection_bihari or any(k in reflection_bihari.lower() for k in ["compiler", "backspace", "semicolons", "rubber duck", "ritual", "line", "moment"])

        reflection_vihara = get_reflection(Vibe.SYNTAX_RAGE, context=ctx, brand_track="vihara")
        assert 0 < len(reflection_vihara) < 40
        assert "auth_handler.py" in reflection_vihara or any(k in reflection_vihara.lower() for k in ["syntax", "friction", "debugging", "error", "calm", "step back", "observe", "complexity", "compiler", "debug"])

    def test_mounting_friction_classification(self):
        """Moderate backspaces (0.18-0.30) in code editor classifies as MOUNTING_FRICTION."""
        event = TelemetryEvent(
            app_name="code.exe",
            window_title="data_pipeline.py",
            typing_speed=22,
            backspace_rate=0.24,
            backspace_count=7,
            window_switches_3min=1,
        )
        res = classify_by_rules(event)
        assert res is not None
        assert res.vibe == Vibe.MOUNTING_FRICTION

    def test_help_seeking_classification(self):
        """Browser searching Stack Overflow or docs classifies as HELP_SEEKING."""
        event = TelemetryEvent(
            app_name="chrome.exe",
            window_title="python index out of range - Stack Overflow",
            typing_speed=4,
            backspace_rate=0.0,
            backspace_count=0,
            window_switches_3min=2,
        )
        res = classify_by_rules(event)
        assert res is not None
        assert res.vibe == Vibe.HELP_SEEKING

    def test_tab_butterfly_classification(self):
        """Rapid window switching (>10 switches in 3 min) classifies as TAB_BUTTERFLY."""
        event = TelemetryEvent(
            app_name="chrome.exe",
            window_title="Wikipedia - General",
            typing_speed=6,
            backspace_rate=0.0,
            backspace_count=0,
            window_switches_3min=14,
        )
        res = classify_by_rules(event)
        assert res is not None
        assert res.vibe == Vibe.TAB_BUTTERFLY

    def test_afternoon_drift_classification(self):
        """Post-lunch slow activity (hours 13-15) classifies as AFTERNOON_DRIFT."""
        event = TelemetryEvent(
            app_name="chrome.exe",
            window_title="Tech Article",
            typing_speed=8,
            backspace_rate=0.0,
            backspace_count=0,
            window_switches_3min=1,
            hour_of_day=14,
        )
        res = classify_by_rules(event)
        assert res is not None
        assert res.vibe == Vibe.AFTERNOON_DRIFT

    def test_grinding_session_classification(self):
        """Long coding session (>90 min) with steady output classifies as GRINDING."""
        event = TelemetryEvent(
            app_name="code.exe",
            window_title="compiler.cpp",
            typing_speed=18,
            backspace_rate=0.06,
            backspace_count=2,
            window_switches_3min=1,
            session_minutes=120.0,
        )
        res = classify_by_rules(event)
        assert res is not None
        assert res.vibe == Vibe.GRINDING

    def test_burnout_approaching_classification(self):
        """Extended session (>180 min) with declining pace (speed < 10) classifies as BURNOUT_APPROACHING."""
        event = TelemetryEvent(
            app_name="code.exe",
            window_title="compiler.cpp",
            typing_speed=8,
            backspace_rate=0.05,
            backspace_count=1,
            window_switches_3min=1,
            session_minutes=210.0,
        )
        res = classify_by_rules(event)
        assert res is not None
        assert res.vibe == Vibe.BURNOUT_APPROACHING

    def test_stillness_classification(self):
        """Complete inactivity or idle heartbeat triggers STILLNESS."""
        event = TelemetryEvent(
            app_name="notepad.exe",
            window_title="draft.txt",
            typing_speed=0,
            backspace_rate=0.0,
            backspace_count=0,
            window_switches_3min=0,
        )
        res = classify_by_rules(event)
        assert res is not None
        assert res.vibe == Vibe.STILLNESS

        event_heartbeat = TelemetryEvent(
            app_name="notepad.exe",
            window_title="draft.txt",
            typing_speed=0,
            backspace_rate=0.0,
            backspace_count=0,
            window_switches_3min=0,
            trigger_reason="idle_heartbeat",
        )
        res_heartbeat = classify_by_rules(event_heartbeat)
        assert res_heartbeat is not None
        assert res_heartbeat.vibe == Vibe.STILLNESS

    def test_wandering_utility_apps(self):
        """Task Manager, regedit, or settings classifies as WANDERING."""
        event = TelemetryEvent(
            app_name="taskmgr.exe",
            window_title="Task Manager",
            typing_speed=0,
            backspace_rate=0.0,
            backspace_count=0,
            window_switches_3min=1,
        )
        res = classify_by_rules(event)
        assert res is not None
        assert res.vibe == Vibe.WANDERING

    def test_meeting_interruption_suppression(self):
        """Active meetings in Zoom/Teams return None to avoid popup interruptions."""
        event = TelemetryEvent(
            app_name="zoom.exe",
            window_title="Sprint Planning Meeting - Zoom",
            typing_speed=5,
            backspace_rate=0.0,
            backspace_count=0,
            window_switches_3min=1,
        )
        res = classify_by_rules(event)
        assert res is None, "In-meeting events must not trigger meme interruptions"
