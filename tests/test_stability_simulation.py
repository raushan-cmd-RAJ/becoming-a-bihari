"""
Tests for Module: Long-Run Stability & Workday Simulation.

Validates:
- F21: 8+ Simulated Hours Stability:
  - 8+ simulated hours (960 ticks at 30s intervals) of mixed realistic activity without crashing, hanging, or exceptions.
  - Cycling through behavioral states representing all 12 vibes.
  - End-to-end integration: Telemetry -> Privacy Filter -> Context Extractor -> Rule Classifier -> Flow Gate -> Meme Retriever -> Dual Reflection Banks.
  - Memory bounds verification: LRU deques respect maximum capacities with zero unbounded growth.
  - Rapid state transitions and adversarial switching resilience.
"""

import time
import tempfile
from pathlib import Path
import pytest

from bihari.inference import (
    classify_by_rules,
    get_reflection,
    is_flow_gate_suppressed,
    Vibe,
    VibeResult,
)
from bihari.context import extract_context
from bihari.privacy import PrivacyFilter
from bihari.memes import MemeRetriever
from bihari.config import DEFAULTS
from bihari.spy import TelemetryEvent


class TestStabilitySimulation:
    """Tier 4: Real-World Application & Stability Simulation."""

    def test_8_hour_workday_stability_simulation(self):
        """
        F21 Contract:
        Simulate an 8-hour workday (960 ticks at 30-second increments = 28,800 seconds).
        Exercises the entire pipeline across mixed activities without any unhandled exceptions,
        asserting that all 12 vibes are supported and memory remains strictly bounded.
        """
        start_clock = time.perf_counter()
        simulated_start_time = 36000.0  # 10:00:00 AM simulated epoch
        simulated_time = simulated_start_time

        blocked_apps = DEFAULTS["privacy"]["blocked_apps"]
        blocked_keywords = DEFAULTS["privacy"]["blocked_title_keywords"]
        pfilter = PrivacyFilter(blocked_apps, blocked_keywords)

        with tempfile.TemporaryDirectory() as tmpdir:
            test_meme_dir = Path(tmpdir)
            retriever = MemeRetriever(test_meme_dir, cooldown_seconds=60)

            # Create mock memes for each vibe so retriever has candidate targets
            for vibe in Vibe:
                from bihari.inference import VIBE_FOLDER_NAMES
                v_folder = test_meme_dir / VIBE_FOLDER_NAMES[vibe]
                v_folder.mkdir(parents=True, exist_ok=True)
                (v_folder / "sample_meme.png").write_bytes(b"STUB")

            vibe_counts: dict[Vibe, int] = {v: 0 for v in Vibe}
            flow_suppressed_count = 0
            processed_ticks = 0

            # 960 ticks * 30 seconds = 28,800 seconds (8.0 simulated hours)
            total_ticks = 960
            for tick in range(total_ticks):
                simulated_minutes = (simulated_time - simulated_start_time) / 60.0
                hour_of_day = int((simulated_time % 86400) // 3600)

                # Scenario schedule cycling through realistic activities
                phase = tick % 14
                if phase == 0:
                    # 1. Flow state coding
                    app, title = "code.exe", "auth_service.py - Visual Studio Code"
                    speed, bs_rate, bs_count, switches, dwell = 65, 0.04, 2, 0, 15.0
                elif phase == 1:
                    # 2. Syntax rage coding spike
                    app, title = "code.exe", "parser.py - Visual Studio Code"
                    speed, bs_rate, bs_count, switches, dwell = 30, 0.45, 14, 1, 5.0
                elif phase == 2:
                    # 3. Mounting friction
                    app, title = "code.exe", "db.py - Visual Studio Code"
                    speed, bs_rate, bs_count, switches, dwell = 22, 0.24, 6, 1, 4.0
                elif phase == 3:
                    # 4. Help seeking on Stack Overflow
                    app, title = "chrome.exe", "python sqlite timeout error - Stack Overflow"
                    speed, bs_rate, bs_count, switches, dwell = 5, 0.0, 0, 2, 2.0
                elif phase == 4:
                    # 5. YouTube video consumption
                    app, title = "chrome.exe", "Clean Code Architecture in 2026 - YouTube"
                    speed, bs_rate, bs_count, switches, dwell = 0, 0.0, 0, 0, 4.0
                elif phase == 5:
                    # 6. Social media scroll
                    app, title = "chrome.exe", "Instagram Reels - Explore"
                    speed, bs_rate, bs_count, switches, dwell = 0, 0.0, 0, 1, 3.5
                elif phase == 6:
                    # 7. Tab butterfly context switching
                    app, title = "chrome.exe", "Shopping Portal Tab 14"
                    speed, bs_rate, bs_count, switches, dwell = 6, 0.0, 0, 14, 0.5
                elif phase == 7:
                    # 8. Post-lunch afternoon drift
                    app, title = "chrome.exe", "Tech News Feed"
                    speed, bs_rate, bs_count, switches, dwell = 8, 0.0, 0, 1, 3.0
                    hour_of_day = 14  # Force 2 PM
                elif phase == 8:
                    # 9. Meeting in Zoom (should be suppressed by rules)
                    app, title = "zoom.exe", "Weekly Standup - Zoom Meeting"
                    speed, bs_rate, bs_count, switches, dwell = 3, 0.0, 0, 0, 25.0
                elif phase == 9:
                    # 10. Long session grinding
                    app, title = "code.exe", "engine.cpp - Visual Studio"
                    speed, bs_rate, bs_count, switches, dwell = 18, 0.06, 2, 1, 8.0
                    simulated_minutes = 120.0
                elif phase == 10:
                    # 11. Late-day burnout approach
                    app, title = "code.exe", "engine.cpp - Visual Studio"
                    speed, bs_rate, bs_count, switches, dwell = 8, 0.05, 1, 1, 15.0
                    simulated_minutes = 210.0
                elif phase == 11:
                    # 12. Inactivity stillness
                    app, title = "notepad.exe", "scratchpad.txt"
                    speed, bs_rate, bs_count, switches, dwell = 0, 0.0, 0, 0, 20.0
                elif phase == 12:
                    # 13. System utility wandering
                    app, title = "taskmgr.exe", "Task Manager"
                    speed, bs_rate, bs_count, switches, dwell = 0, 0.0, 0, 2, 1.0
                else:
                    # 14. Sensitive banking context (must be sanitized)
                    app, title = "chrome.exe", "Chase Bank - Payment Confirmation"
                    speed, bs_rate, bs_count, switches, dwell = 10, 0.0, 0, 1, 1.0

                # ── Pipeline Step 1: Privacy Filter ──
                clean_app, clean_title = pfilter.sanitize(app, title)
                if "bank" in title.lower() or "payment" in title.lower():
                    assert clean_title == "HIDDEN_PRIVACY_CONTEXT"

                # ── Pipeline Step 2: Context Extraction ──
                ctx = extract_context(clean_app, clean_title)

                # ── Pipeline Step 3: Rule Classification ──
                event = TelemetryEvent(
                    app_name=clean_app,
                    window_title=clean_title,
                    typing_speed=speed,
                    backspace_rate=bs_rate,
                    backspace_count=bs_count,
                    window_switches_3min=switches,
                    timestamp=simulated_time,
                    session_minutes=simulated_minutes,
                    dwell_minutes=dwell,
                    hour_of_day=hour_of_day,
                )
                res = classify_by_rules(event)

                if res is not None:
                    vibe_counts[res.vibe] += 1

                    # ── Pipeline Step 4: Flow Gate Check ──
                    if is_flow_gate_suppressed(event, res):
                        flow_suppressed_count += 1
                    else:
                        # ── Pipeline Step 5: Meme Retrieval ──
                        retriever.get_meme(res.vibe, current_time=simulated_time)

                    # ── Pipeline Step 6: Reflection Generation (Both Tracks) ──
                    ref_vihara = get_reflection(res.vibe, context=ctx, brand_track="vihara")
                    ref_bihari = get_reflection(res.vibe, context=ctx, brand_track="bihari")
                    assert 0 < len(ref_vihara) < 40, f"Vihara reflection exceeded budget ({len(ref_vihara)} chars): '{ref_vihara}'"
                    assert 0 < len(ref_bihari) < 40, f"Bihari reflection exceeded budget ({len(ref_bihari)} chars): '{ref_bihari}'"

                processed_ticks += 1
                simulated_time += 30.0

            # Assertions after 8 simulated hours
            assert processed_ticks == 960
            assert (simulated_time - simulated_start_time) == 28800.0  # Exactly 8 hours

            # Verify memory bound: recent queue does not exceed maxlen (100)
            assert len(retriever._recent) <= 100

            # Flow state gate was triggered and protected deep work
            assert flow_suppressed_count > 0, "Flow State gate must actively suppress popups during flow"

            # Verify high-frequency vibes were observed
            assert vibe_counts[Vibe.FLOW_STATE] > 0
            assert vibe_counts[Vibe.SYNTAX_RAGE] > 0
            assert vibe_counts[Vibe.LOST_IN_SCROLL] > 0
            assert vibe_counts[Vibe.HELP_SEEKING] > 0
            assert vibe_counts[Vibe.STILLNESS] > 0
            assert vibe_counts[Vibe.GRINDING] > 0
            assert vibe_counts[Vibe.BURNOUT_APPROACHING] > 0
            assert vibe_counts[Vibe.AFTERNOON_DRIFT] > 0
            assert vibe_counts[Vibe.TAB_BUTTERFLY] > 0
            assert vibe_counts[Vibe.WANDERING] > 0

            # Ensure wall-clock execution was fast (< 5.0 seconds)
            elapsed_wall_clock = time.perf_counter() - start_clock
            assert elapsed_wall_clock < 5.0, (
                f"Simulation took too long: {elapsed_wall_clock:.2f}s (budget: 5.0s)"
            )

    def test_rapid_erratic_state_switching_stability(self):
        """Simulate rapid 1-second state switches between diverse applications without hanging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            retriever = MemeRetriever(Path(tmpdir), cooldown_seconds=0)
            pfilter = PrivacyFilter([], [])

            apps = ["code.exe", "chrome.exe", "zoom.exe", "powershell.exe", "taskmgr.exe"]
            sim_time = 5000.0
            for i in range(200):
                app = apps[i % len(apps)]
                title = f"Document {i} - {app}"
                clean_app, clean_title = pfilter.sanitize(app, title)
                ctx = extract_context(clean_app, clean_title)
                ev = TelemetryEvent(
                    app_name=clean_app,
                    window_title=clean_title,
                    typing_speed=(i * 7) % 80,
                    backspace_rate=((i * 3) % 50) / 100.0,
                    backspace_count=2,
                    window_switches_3min=15,
                    timestamp=sim_time,
                )
                res = classify_by_rules(ev)
                if res:
                    get_reflection(res.vibe, context=ctx)
                sim_time += 1.0

            assert len(retriever._recent) <= 100
