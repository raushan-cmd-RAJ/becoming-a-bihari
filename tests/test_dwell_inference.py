"""
Module: Automated Verification Suite for Dwell-Time Vibe Transitions and Consciousness Mirroring.

Validates:
1. Context-specific dwell-time state transitions:
   - Social / Video apps: glance (<2 min) -> engaged (2-8 min) -> trance (>12 min).
   - Code / Productivity apps: orientation (<5 min) -> flow (5-30 min) -> grind/fatigue (>45 min).
   - Idle / Inactive apps: stillness vs afternoon drift over prolonged durations.
2. Window switching:
   - Resets continuous dwell counter per active window.
   - Appropriately preserves accumulated dwell counter when configured.
3. Non-judgmental tone audit:
   - Asserts zero patronizing, scolding, preachy, or productivity-policing vocabulary.
   - Asserts strict adherence to < 40 characters for all reflections and templates.
4. Dwell-aware reflection generation:
   - Clean, lighthearted, blissful mirroring of elapsed time in the current space.
5. System compilation and telemetry integration.
"""

import compileall
import os
import re
import unittest
from pathlib import Path

from bihari.context import WindowContext, extract_context
from bihari.inference import (
    Vibe,
    VibeResult,
    classify_by_rules,
    format_dwell_reflection,
    get_reflection,
    is_flow_gate_suppressed,
    REFLECTIONS_TRACK_A,
    REFLECTIONS_TRACK_B,
    CONTEXTUAL_TEMPLATES_TRACK_A,
    CONTEXTUAL_TEMPLATES_TRACK_B,
    SHORT_VIDEO_REFLECTIONS,
    SHORT_VIDEO_REFLECTIONS_TRACK_B,
    SHORT_PUNCHY_REFLECTIONS,
    SHORT_PUNCHY_REFLECTIONS_TRACK_B,
    SHORT_SOCIAL_REFLECTIONS,
    SHORT_SOCIAL_REFLECTIONS_TRACK_B,
    SHORT_SOCIAL_CONTEXTUAL,
    SHORT_SOCIAL_CONTEXTUAL_TRACK_B,
    MINDFUL_THEME_REFLECTIONS,
    VibeClassifier,
)
from bihari.spy import DwellTracker, TelemetryEvent


class TestDwellTimeVibeTransitions(unittest.TestCase):
    """R2: Context-Specific Window/App Dwell-Time Vibe Determination."""

    def test_social_dwell_progression_glance_engaged_trance(self):
        """
        Social apps transition:
          - Short dwell (<2 min) = transient glance (TAB_BUTTERFLY)
          - Medium dwell (2-8 min) = focused engagement (LOST_IN_SCROLL)
          - Extended dwell (>12 min) = absorbed trance state (WANDERING)
        """
        app = "chrome.exe"
        title = "Instagram Reels - Explore Feed"

        # 1. Short dwell (<2 min): transient glance
        glance_event = TelemetryEvent(
            app_name=app,
            window_title=title,
            typing_speed=0,
            backspace_rate=0.0,
            backspace_count=0,
            window_switches_3min=0,
            dwell_minutes=0.8,
        )
        res_glance = classify_by_rules(glance_event)
        self.assertIsNotNone(res_glance)
        self.assertEqual(res_glance.vibe, Vibe.TAB_BUTTERFLY)

        # 2. Medium dwell (2-8 min): focused engagement
        engaged_event = TelemetryEvent(
            app_name=app,
            window_title=title,
            typing_speed=0,
            backspace_rate=0.0,
            backspace_count=0,
            window_switches_3min=0,
            dwell_minutes=5.0,
        )
        res_engaged = classify_by_rules(engaged_event)
        self.assertIsNotNone(res_engaged)
        self.assertEqual(res_engaged.vibe, Vibe.LOST_IN_SCROLL)

        # 3. Extended dwell (>12 min): absorbed trance state
        trance_event = TelemetryEvent(
            app_name=app,
            window_title=title,
            typing_speed=0,
            backspace_rate=0.0,
            backspace_count=0,
            window_switches_3min=0,
            dwell_minutes=16.0,
        )
        res_trance = classify_by_rules(trance_event)
        self.assertIsNotNone(res_trance)
        self.assertEqual(res_trance.vibe, Vibe.WANDERING)

        # Confirm distinct progression
        progression = [res_glance.vibe, res_engaged.vibe, res_trance.vibe]
        self.assertEqual(
            progression,
            [Vibe.TAB_BUTTERFLY, Vibe.LOST_IN_SCROLL, Vibe.WANDERING],
            "Social dwell must progress from glance -> engaged -> trance",
        )

    def test_coding_dwell_progression_orientation_flow_grind_fatigue(self):
        """
        Code apps transition:
          - Short dwell (<5 min) = orientation/settling (WANDERING)
          - Medium dwell (5-30 min) = immersion / sustained flow (FLOW_STATE)
          - Extended dwell (>45 min) = deep grind / fatigue (GRINDING / BURNOUT_APPROACHING)
        """
        app = "code.exe"
        title = "auth_handler.py - Visual Studio Code"

        # 1. Short dwell (<5 min): orientation/settling
        settling_event = TelemetryEvent(
            app_name=app,
            window_title=title,
            typing_speed=28,
            backspace_rate=0.04,
            backspace_count=1,
            window_switches_3min=1,
            dwell_minutes=2.5,
        )
        res_settling = classify_by_rules(settling_event)
        self.assertIsNotNone(res_settling)
        self.assertEqual(res_settling.vibe, Vibe.WANDERING)

        # 2. Medium dwell (5-30 min): immersion / sustained flow
        flow_event = TelemetryEvent(
            app_name=app,
            window_title=title,
            typing_speed=28,
            backspace_rate=0.04,
            backspace_count=1,
            window_switches_3min=1,
            dwell_minutes=18.0,
        )
        res_flow = classify_by_rules(flow_event)
        self.assertIsNotNone(res_flow)
        self.assertEqual(res_flow.vibe, Vibe.FLOW_STATE)

        # 3. Extended dwell (>45 min): deep grind
        grind_event = TelemetryEvent(
            app_name=app,
            window_title=title,
            typing_speed=28,
            backspace_rate=0.04,
            backspace_count=1,
            window_switches_3min=1,
            dwell_minutes=55.0,
        )
        res_grind = classify_by_rules(grind_event)
        self.assertIsNotNone(res_grind)
        self.assertEqual(res_grind.vibe, Vibe.GRINDING)

        # 4. Extended dwell (>45 min) with declining pace: mental fatigue
        fatigue_event = TelemetryEvent(
            app_name=app,
            window_title=title,
            typing_speed=8,
            backspace_rate=0.04,
            backspace_count=1,
            window_switches_3min=1,
            dwell_minutes=65.0,
        )
        res_fatigue = classify_by_rules(fatigue_event)
        self.assertIsNotNone(res_fatigue)
        self.assertEqual(res_fatigue.vibe, Vibe.BURNOUT_APPROACHING)

        # Confirm distinct progression
        self.assertEqual(
            [res_settling.vibe, res_flow.vibe, res_grind.vibe],
            [Vibe.WANDERING, Vibe.FLOW_STATE, Vibe.GRINDING],
            "Coding dwell must progress from orientation -> flow -> grind",
        )

    def test_productivity_writing_app_dwell_progression(self):
        """
        Productivity and writing apps (e.g. Obsidian, Notion, Word) transition:
          - Short dwell (<5 min) = orientation/settling (WANDERING)
          - Medium dwell (5-30 min) = immersion / sustained flow (FLOW_STATE)
          - Extended dwell (>45 min) = deep grind / fatigue (GRINDING / BURNOUT_APPROACHING)
        """
        app = "obsidian.exe"
        title = "philosophy_notes.md - Obsidian"

        # 1. Orientation (<5m)
        ev_orient = TelemetryEvent(app_name=app, window_title=title, typing_speed=20, dwell_minutes=2.0)
        self.assertEqual(classify_by_rules(ev_orient).vibe, Vibe.WANDERING)

        # 2. Flow (5-30m)
        ev_flow = TelemetryEvent(app_name=app, window_title=title, typing_speed=25, dwell_minutes=15.0)
        self.assertEqual(classify_by_rules(ev_flow).vibe, Vibe.FLOW_STATE)

        # 3. Grind (>45m)
        ev_grind = TelemetryEvent(app_name=app, window_title=title, typing_speed=25, dwell_minutes=50.0)
        self.assertEqual(classify_by_rules(ev_grind).vibe, Vibe.GRINDING)

        # 4. Burnout approaching (>45m, declining speed)
        ev_burnout = TelemetryEvent(app_name=app, window_title=title, typing_speed=8, dwell_minutes=55.0)
        self.assertEqual(classify_by_rules(ev_burnout).vibe, Vibe.BURNOUT_APPROACHING)

    def test_video_media_app_dwell_progression(self):
        """
        Video media apps (e.g. VLC, media players) transition:
          - Short dwell (<2 min) = transient glance (TAB_BUTTERFLY)
          - Medium dwell (2-8 min) = focused engagement (LOST_IN_SCROLL)
          - Extended dwell (>12 min) = absorbed trance state (WANDERING)
        """
        app = "vlc.exe"
        title = "lecture_documentary.mp4 - VLC media player"

        ev_glance = TelemetryEvent(app_name=app, window_title=title, dwell_minutes=1.0)
        self.assertEqual(classify_by_rules(ev_glance).vibe, Vibe.TAB_BUTTERFLY)

        ev_engaged = TelemetryEvent(app_name=app, window_title=title, dwell_minutes=6.0)
        self.assertEqual(classify_by_rules(ev_engaged).vibe, Vibe.LOST_IN_SCROLL)

        ev_trance = TelemetryEvent(app_name=app, window_title=title, dwell_minutes=15.0)
        self.assertEqual(classify_by_rules(ev_trance).vibe, Vibe.WANDERING)

    def test_idle_dwell_progression_stillness_and_drift(self):
        """
        Idle / Inactive apps translate into STILLNESS or AFTERNOON_DRIFT:
          - Regular hours: STILLNESS
          - Post-lunch hours (13-15h) with dwell > 3 min: AFTERNOON_DRIFT
        """
        event_still = TelemetryEvent(
            app_name="notepad.exe",
            window_title="draft.txt",
            typing_speed=0,
            backspace_rate=0.0,
            backspace_count=0,
            window_switches_3min=0,
            dwell_minutes=10.0,
            hour_of_day=10,
        )
        res_still = classify_by_rules(event_still)
        self.assertIsNotNone(res_still)
        self.assertEqual(res_still.vibe, Vibe.STILLNESS)

        event_drift = TelemetryEvent(
            app_name="notepad.exe",
            window_title="draft.txt",
            typing_speed=0,
            backspace_rate=0.0,
            backspace_count=0,
            window_switches_3min=0,
            dwell_minutes=10.0,
            hour_of_day=14,
        )
        res_drift = classify_by_rules(event_drift)
        self.assertIsNotNone(res_drift)
        self.assertEqual(res_drift.vibe, Vibe.AFTERNOON_DRIFT)

    def test_dwell_boundary_transitions(self):
        """
        Verify exact boundary transitions:
          - Social apps: 0.0, 1.9 (<2 min -> TAB_BUTTERFLY); 2.0, 8.0, 12.0 (2-12 min -> LOST_IN_SCROLL); 12.1 (>12 min -> WANDERING).
          - Work apps: 0.0, 4.9 (<5 min -> WANDERING); 5.0, 30.0, 45.0 (5-45 min -> FLOW_STATE); 45.1 (>45 min -> GRINDING); 60.1 (>60 min -> BURNOUT_APPROACHING).
        """
        # Social boundaries
        app_soc = "chrome.exe"
        title_soc = "YouTube - Explore"
        self.assertEqual(classify_by_rules(TelemetryEvent(app_name=app_soc, window_title=title_soc, dwell_minutes=0.0)).vibe, Vibe.TAB_BUTTERFLY)
        self.assertEqual(classify_by_rules(TelemetryEvent(app_name=app_soc, window_title=title_soc, dwell_minutes=1.9)).vibe, Vibe.TAB_BUTTERFLY)
        self.assertEqual(classify_by_rules(TelemetryEvent(app_name=app_soc, window_title=title_soc, dwell_minutes=2.0)).vibe, Vibe.LOST_IN_SCROLL)
        self.assertEqual(classify_by_rules(TelemetryEvent(app_name=app_soc, window_title=title_soc, dwell_minutes=8.0)).vibe, Vibe.LOST_IN_SCROLL)
        self.assertEqual(classify_by_rules(TelemetryEvent(app_name=app_soc, window_title=title_soc, dwell_minutes=12.0)).vibe, Vibe.LOST_IN_SCROLL)
        self.assertEqual(classify_by_rules(TelemetryEvent(app_name=app_soc, window_title=title_soc, dwell_minutes=12.1)).vibe, Vibe.WANDERING)

        # Work app boundaries
        app_code = "code.exe"
        title_code = "server.py"
        self.assertEqual(classify_by_rules(TelemetryEvent(app_name=app_code, window_title=title_code, dwell_minutes=0.0, typing_speed=25)).vibe, Vibe.WANDERING)
        self.assertEqual(classify_by_rules(TelemetryEvent(app_name=app_code, window_title=title_code, dwell_minutes=4.9, typing_speed=25)).vibe, Vibe.WANDERING)
        self.assertEqual(classify_by_rules(TelemetryEvent(app_name=app_code, window_title=title_code, dwell_minutes=5.0, typing_speed=25)).vibe, Vibe.FLOW_STATE)
        self.assertEqual(classify_by_rules(TelemetryEvent(app_name=app_code, window_title=title_code, dwell_minutes=30.0, typing_speed=25)).vibe, Vibe.FLOW_STATE)
        self.assertEqual(classify_by_rules(TelemetryEvent(app_name=app_code, window_title=title_code, dwell_minutes=45.0, typing_speed=25)).vibe, Vibe.FLOW_STATE)
        self.assertEqual(classify_by_rules(TelemetryEvent(app_name=app_code, window_title=title_code, dwell_minutes=45.1, typing_speed=25)).vibe, Vibe.GRINDING)
        self.assertEqual(classify_by_rules(TelemetryEvent(app_name=app_code, window_title=title_code, dwell_minutes=60.1, typing_speed=25)).vibe, Vibe.BURNOUT_APPROACHING)

    def test_work_app_zero_typing_orientation_vs_prolonged_stillness(self):
        """
        In work apps, short dwell (<3 min) with 0 typing is orientation/settling (WANDERING),
        whereas prolonged zero activity (>=3 min) translates into STILLNESS.
        """
        app = "code.exe"
        title = "main.py"
        # Reading/settling in (<3 min): WANDERING (orientation)
        ev_orient = TelemetryEvent(app_name=app, window_title=title, typing_speed=0, dwell_minutes=1.5)
        self.assertEqual(classify_by_rules(ev_orient).vibe, Vibe.WANDERING)

        # Prolonged inactivity (>=3 min): STILLNESS
        ev_still = TelemetryEvent(app_name=app, window_title=title, typing_speed=0, dwell_minutes=5.0)
        self.assertEqual(classify_by_rules(ev_still).vibe, Vibe.STILLNESS)

    def test_window_switching_resets_dwell_counters(self):
        """Window switching resets dwell counter for the newly active window."""
        tracker = DwellTracker(preserve_on_switch=False)
        sim_time = 1000.0

        # Activate Window A and dwell 5 minutes (300s)
        tracker.switch_window("code.exe", "main.py", now=sim_time)
        sim_time += 300.0
        self.assertAlmostEqual(tracker.get_dwell_minutes(now=sim_time), 5.0, places=1)

        # Switch to Window B: dwell counter resets to 0
        tracker.switch_window("chrome.exe", "YouTube", now=sim_time)
        self.assertEqual(tracker.get_dwell_minutes(now=sim_time), 0.0)

        # Dwell 2 minutes (120s) in Window B
        sim_time += 120.0
        self.assertAlmostEqual(tracker.get_dwell_minutes(now=sim_time), 2.0, places=1)

        # Switch back to Window A: resets continuous counter for this new session
        tracker.switch_window("code.exe", "main.py", now=sim_time)
        self.assertEqual(tracker.get_dwell_minutes(now=sim_time), 0.0)

    def test_window_switching_preserves_dwell_counters_when_configured(self):
        """Window switching appropriately preserves dwell counters per active window."""
        tracker = DwellTracker(preserve_on_switch=True)
        sim_time = 1000.0

        # Dwell in Window A for 5 minutes (300s)
        tracker.switch_window("code.exe", "auth.py", now=sim_time)
        sim_time += 300.0
        self.assertAlmostEqual(tracker.get_dwell_minutes(now=sim_time), 5.0, places=1)

        # Switch to Window B and dwell 2 minutes (120s)
        tracker.switch_window("chrome.exe", "Docs", now=sim_time)
        sim_time += 120.0
        self.assertAlmostEqual(tracker.get_dwell_minutes(now=sim_time), 2.0, places=1)

        # Switch back to Window A: preserves previously accumulated 5 minutes
        tracker.switch_window("code.exe", "auth.py", now=sim_time)
        self.assertAlmostEqual(tracker.get_dwell_minutes(now=sim_time), 5.0, places=1)
        sim_time += 60.0
        self.assertAlmostEqual(tracker.get_dwell_minutes(now=sim_time), 6.0, places=1)

    def test_dwell_tracker_uninitialized_and_rapid_switching_edge_cases(self):
        """Edge cases: uninitialized state, sub-second alt-tabbing, clock skew, app reset."""
        # 1. Uninitialized tracker must return 0.0 before any window switch
        fresh_tracker = DwellTracker()
        self.assertEqual(fresh_tracker.get_dwell_minutes(), 0.0)

        # 2. Sub-second rapid switching (alt-tab rapid cycling)
        tracker = DwellTracker(preserve_on_switch=True)
        now = 1000.0
        for _ in range(10):
            tracker.switch_window("code.exe", "main.py", now=now)
            now += 0.1
            tracker.switch_window("chrome.exe", "docs", now=now)
            now += 0.1
        # Continuous dwell in chrome after rapid 0.1s clicks is negligible (~0.0 min)
        self.assertAlmostEqual(tracker.get_dwell_minutes(now=now), 0.0, places=1)

        # 3. Monotonic clock jitter / backward timestamp
        tracker.switch_window("code.exe", "main.py", now=now)
        # Jitter: now is slightly earlier than _active_start
        jitter_now = now - 5.0
        self.assertEqual(tracker.get_dwell_minutes(now=jitter_now), 0.0)

        # 4. App-level reset (all windows for that app)
        now += 120.0  # 2 minutes in code.exe
        self.assertAlmostEqual(tracker.get_dwell_minutes(now=now), 2.0, places=1)
        tracker.reset(app="code.exe", now=now)
        self.assertEqual(tracker.get_dwell_minutes(now=now), 0.0)


class TestNonJudgmentalReflectionAudit(unittest.TestCase):
    """R1 & R3: Pure Consciousness Mirroring & Non-Judgmental Reflection Audit."""

    JUDGMENTAL_PATTERNS = [
        r"\bshould\b",
        r"\bought\b",
        r"\bmust\b",
        r"\bprocrastinat",
        r"\bwast",
        r"\bstop\b",
        r"\bget back\b",
        r"\bback to work\b",
        r"\bto-do list\b",
        r"\bpay rent\b",
        r"\bproductivity\b",
        r"\blazy\b",
        r"\bguilt\b",
        r"\bshame\b",
        r"\bhypnotiz",
        r"\bwins again\b",
        r"\bdoing everything except\b",
        # Directive / prescriptive imperative commands
        r"\b(stretch and hydrate|hydrate and|walk restores|walk helps)\b",
        r"\b(awaken to|ground yourself|step back to debug|center and debug)\b",
        r"\b(synthesize (your )?question|integrate ideas|pause to ground)\b",
        r"\b(focus on one|release agitation|balance with rest)\b",
        r"\b(breathe\.|pause\.)\b",
    ]

    def _assert_clean_tone(self, phrase: str, source_desc: str):
        for pattern in self.JUDGMENTAL_PATTERNS:
            match = re.search(pattern, phrase, re.IGNORECASE)
            self.assertIsNone(
                match,
                f"Found judgmental vocabulary '{match.group(0) if match else ''}' in [{source_desc}]: '{phrase}'",
            )

    def test_static_reflection_banks_tone_and_budget(self):
        """All static phrases in Track A and Track B pass tone audit and len < 40 chars."""
        all_banks = [
            ("Track A", REFLECTIONS_TRACK_A),
            ("Track B", REFLECTIONS_TRACK_B),
        ]
        for track_name, bank in all_banks:
            for vibe, phrases in bank.items():
                for p in phrases:
                    self.assertLess(
                        len(p),
                        40,
                        f"Phrase exceeded 40-char limit ({len(p)}): '{p}' in [{track_name} {vibe}]",
                    )
                    self._assert_clean_tone(p, f"{track_name} {vibe}")

    def test_short_pools_tone_and_budget(self):
        """Short video, punchy, and social reflection pools pass tone audit and len < 40 chars."""
        pools = [
            ("SHORT_PUNCHY_REFLECTIONS", SHORT_PUNCHY_REFLECTIONS),
            ("SHORT_PUNCHY_REFLECTIONS_TRACK_B", SHORT_PUNCHY_REFLECTIONS_TRACK_B),
            ("SHORT_SOCIAL_REFLECTIONS", SHORT_SOCIAL_REFLECTIONS),
            ("SHORT_SOCIAL_REFLECTIONS_TRACK_B", SHORT_SOCIAL_REFLECTIONS_TRACK_B),
        ]
        for name, pool in pools:
            for p in pool:
                self.assertLess(len(p), 40, f"Phrase too long ({len(p)}): '{p}' in {name}")
                self._assert_clean_tone(p, name)

    def test_contextual_templates_tone_and_budget(self):
        """Contextual templates formatted with condensed subject stay strictly under 40 chars."""
        sample_subject = "auth_handler.py"
        all_template_groups = [
            ("Track A Contextual", CONTEXTUAL_TEMPLATES_TRACK_A),
            ("Track B Contextual", CONTEXTUAL_TEMPLATES_TRACK_B),
        ]
        for group_name, group in all_template_groups:
            for vibe, templates in group.items():
                for t in templates:
                    formatted = t.format(subject=sample_subject)
                    self.assertLess(
                        len(formatted),
                        40,
                        f"Template too long ({len(formatted)}): '{formatted}' in [{group_name} {vibe}]",
                    )
                    self._assert_clean_tone(formatted, f"{group_name} {vibe}")

    def test_dwell_aware_reflections_generate_cleanly_and_under_40_chars(self):
        """
        R3: Dwell-aware reflections dynamically mirror elapsed time with warmth/humor
        and strictly adhere to < 40 characters without judgmental vocabulary.
        """
        test_dwells = [1.5, 5.0, 15.0, 20.0, 45.0, 60.0, 120.0]
        test_subjects = ["auth.py", "Rust Tutorial", "Instagram Reels", "main.rs", None]

        for dwell in test_dwells:
            for sub in test_subjects:
                for vibe in Vibe:
                    refl = format_dwell_reflection(dwell_minutes=dwell, subject=sub, vibe=vibe)
                    self.assertIsInstance(refl, str)
                    self.assertGreater(len(refl), 0)
                    self.assertLess(
                        len(refl),
                        40,
                        f"Dwell reflection exceeded 40 chars ({len(refl)}): '{refl}'",
                    )
                    self._assert_clean_tone(refl, f"Dwell reflection (dwell={dwell}, sub={sub})")

    def test_mindful_theme_reflections_tone_and_budget(self):
        """All OCR mindful theme reflections pass tone audit and strict len < 40 chars."""
        for theme, phrases in MINDFUL_THEME_REFLECTIONS.items():
            for p in phrases:
                self.assertLess(
                    len(p),
                    40,
                    f"Mindful theme reflection exceeded 40 chars ({len(p)}): '{p}' in theme {theme}",
                )
                self._assert_clean_tone(p, f"MINDFUL_THEME_REFLECTIONS {theme}")

    def test_get_reflection_integration_with_dwell(self):
        """get_reflection integrates dwell_minutes and produces blissful dwell mirroring < 40 chars."""
        ctx_code = WindowContext(subject="pipeline.py", category="code", is_specific=True, dwell_minutes=25.0)
        ctx_video = WindowContext(subject="Rust Tutorial", category="video", is_specific=True, dwell_minutes=20.0)

        for track in ("bihari", "vihara"):
            dwell_mirrored = False
            for _ in range(50):
                r = get_reflection(Vibe.FLOW_STATE, context=ctx_code, brand_track=track, dwell_minutes=25.0)
                self.assertLess(len(r), 40, f"Caption too long ({len(r)}): '{r}'")
                self._assert_clean_tone(r, f"get_reflection with dwell ({track})")
                if "🪞" in r:
                    dwell_mirrored = True

            self.assertTrue(
                dwell_mirrored,
                f"Expected dwell-aware reflection format (🪞) to be generated when dwell is significant in track {track}",
            )

        # Video context with dwell also generates dwell reflections
        video_dwell_mirrored = False
        for _ in range(50):
            r = get_reflection(Vibe.LOST_IN_SCROLL, context=ctx_video, brand_track="bihari", dwell_minutes=20.0)
            self.assertLess(len(r), 40, f"Caption too long ({len(r)}): '{r}'")
            self._assert_clean_tone(r, "get_reflection with video dwell")
            if "🪞" in r:
                video_dwell_mirrored = True
        self.assertTrue(video_dwell_mirrored, "Expected video context with dwell to generate dwell reflections")

    def test_readme_and_memes_tone_audit(self):
        """Verify documentation and meme generators contain zero judgmental phrasing."""
        readme_path = Path(__file__).resolve().parent.parent / "memes" / "README.txt"
        if readme_path.exists():
            content = readme_path.read_text(encoding="utf-8")
            self._assert_clean_tone(content, "memes/README.txt")

        from bihari.memes import MEME_README_TEXT
        self._assert_clean_tone(MEME_README_TEXT, "bihari.memes MEME_README_TEXT")

    def test_prompt_sample_dwell_reflections_tone_and_format(self):
        """
        Verify the exact sample reflections from R3 requirement:
        e.g. 🪞 20 minutes with: {subject}. Present., 🪞 45 minutes deep in the code., 🪞 Lost in time: {subject}
        All must be concise, non-prescriptive, and strictly under 40 characters.
        """
        refl_code = format_dwell_reflection(45.0, subject=None, vibe=Vibe.FLOW_STATE)
        self.assertLess(len(refl_code), 40)
        self._assert_clean_tone(refl_code, "code dwell sample")

        refl_sub = format_dwell_reflection(20.0, subject="auth.py", vibe=Vibe.FLOW_STATE)
        self.assertLess(len(refl_sub), 40)
        self._assert_clean_tone(refl_sub, "subject dwell sample")

        refl_video = format_dwell_reflection(15.0, subject="Rust", vibe=Vibe.LOST_IN_SCROLL)
        self.assertLess(len(refl_video), 40)
        self._assert_clean_tone(refl_video, "video dwell sample")

    def test_extract_context_preserves_dwell_minutes(self):
        """extract_context accepts and preserves continuous dwell minutes on WindowContext."""
        ctx = extract_context("code.exe", "main.py - Visual Studio Code", dwell_minutes=18.5)
        self.assertIsNotNone(ctx)
        self.assertEqual(ctx.dwell_minutes, 18.5)

    def test_dwell_tracker_handles_none_inputs_cleanly(self):
        """DwellTracker handles None or empty app/title without raising exceptions."""
        tracker = DwellTracker()
        minutes = tracker.switch_window(None, None)
        self.assertEqual(minutes, 0.0)
        self.assertEqual(tracker.get_dwell_minutes(), 0.0)

    def test_format_dwell_reflection_robustness_on_edge_inputs(self):
        """Format dwell reflection handles edge inputs (zero, negative, NaN, huge numbers) safely under 40 chars."""
        edge_dwells = [0.0, -10.0, float("nan"), float("inf"), 99999.0, 1e6]
        for d in edge_dwells:
            for s in [None, "", "a" * 50, "auth.py"]:
                refl = format_dwell_reflection(dwell_minutes=d, subject=s, vibe=Vibe.FLOW_STATE)
                self.assertIsInstance(refl, str)
                self.assertGreater(len(refl), 0)
                self.assertLess(len(refl), 40, f"Dwell reflection exceeded 40 chars on input d={d}, s={s}: '{refl}'")


class TestSystemCompilationAndTelemetry(unittest.TestCase):
    """R4: System compiles and runs cleanly with existing telemetry."""

    def test_bihari_compilation(self):
        """Ensure all files in bihari package compile cleanly with 0 errors."""
        pkg_dir = Path(__file__).resolve().parent.parent / "bihari"
        compiled = compileall.compile_dir(str(pkg_dir), quiet=True)
        self.assertTrue(compiled, "bihari package must compile cleanly with zero errors")

    def test_classifier_and_dwell_tracker_integration(self):
        """VibeClassifier and DwellTracker work smoothly together."""
        classifier = VibeClassifier(use_laya=False)
        tracker = DwellTracker()
        tracker.switch_window("code.exe", "main.py")

        event = TelemetryEvent(
            app_name="code.exe",
            window_title="main.py",
            typing_speed=40,
            backspace_rate=0.03,
            backspace_count=1,
            window_switches_3min=0,
            dwell_minutes=15.0,
        )
        res = classifier.classify(event)
        self.assertEqual(res.vibe, Vibe.FLOW_STATE)
        self.assertTrue(res.confidence >= 0.70)


if __name__ == "__main__":
    unittest.main()
