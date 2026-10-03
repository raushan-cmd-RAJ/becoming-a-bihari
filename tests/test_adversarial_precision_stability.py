"""
Adversarial Precision & Stability Test Harness (mvp_challenger_1_gen2).

Empirically challenges and stress-tests:
1. Meme Deduplication: 100-event simulation with 60-event sliding window
   (multi-vibe and single-vibe candidate pools).
2. Caption Length Fuzzing: 5,000+ randomized contexts with extreme strings,
   huge titles, special characters, unicode, and emojis (< 40 characters budget).
3. Flow State Boundary Challenge: typing speed (49/50/51), backspace rate
   (0.079/0.080/0.081), dwell (9.9/10.0 min) on classification and suppression.
4. 8-Hour Simulated Workday Stress Test: 28,800s / 960 ticks across 12 vibes,
   rapid switching, idle periods, error injection, asserting 0 crashes and bounded memory.
"""

import gc
import json
import random
import string
import sys
import tempfile
import tracemalloc
import unittest
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from bihari.context import WindowContext, extract_context
from bihari.inference import (
    Vibe,
    VibeResult,
    classify_by_rules,
    condense_subject,
    get_reflection,
    VIBE_FOLDER_NAMES,
    REFLECTIONS_TRACK_A,
    REFLECTIONS_TRACK_B,
    CONTEXTUAL_TEMPLATES_TRACK_A,
    CONTEXTUAL_TEMPLATES_TRACK_B,
)
from bihari.memes import MemeRetriever
from bihari.config import DEFAULTS
from bihari.privacy import PrivacyFilter, HIDDEN
from bihari.spy import TelemetryEvent


class AdversarialEmpiricalChallenger(unittest.TestCase):
    """Deep adversarial stress-testing harness for R1 and R4 MVP requirements."""

    # ─────────────────────────────────────────────────────────────
    # HARNESS 1: 100-EVENT SIMULATION & 60-EVENT SLIDING WINDOW
    # ─────────────────────────────────────────────────────────────

    def test_harness_1a_single_vibe_pool_gte_60(self):
        """
        Harness 1A: Single-vibe candidate pool with >= 60 candidates (e.g. 70 memes).
        Asserts len(set(window)) == 60 for EVERY 60-event sliding window across 100 events.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            vibe = Vibe.FLOW_STATE
            folder = root / VIBE_FOLDER_NAMES[vibe]
            folder.mkdir(parents=True, exist_ok=True)

            pool_size = 70
            for i in range(pool_size):
                (folder / f"focus_{i:03d}.png").write_bytes(b"STUB")

            retriever = MemeRetriever(root, cooldown_seconds=0)
            history: List[str] = []
            sim_time = 1000.0

            for _ in range(100):
                meme = retriever.get_meme(vibe, current_time=sim_time, cooldown=0)
                self.assertIsNotNone(meme, "Retriever must return a meme when pool has candidates")
                history.append(meme.name)
                sim_time += 1.0

            self.assertEqual(len(history), 100)
            num_windows = len(history) - 60 + 1
            self.assertEqual(num_windows, 41)

            for i in range(num_windows):
                window = history[i : i + 60]
                unique_memes = set(window)
                self.assertEqual(
                    len(unique_memes),
                    60,
                    f"Window {i} contains duplicates! Found {len(unique_memes)} unique memes, expected 60.",
                )

    def test_harness_1b_single_vibe_pool_small(self):
        """
        Harness 1B: Single-vibe candidate pool with < 60 candidates (e.g. 10 memes, default pack).
        Empirically probes whether len(set(window)) == 60 can hold.
        Mathematically, by Pigeonhole Principle, len(set(window)) <= 10.
        Verifies that safety_window adapts to min(N-1, 60) without deadlock.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            vibe = Vibe.SYNTAX_RAGE
            folder = root / VIBE_FOLDER_NAMES[vibe]
            folder.mkdir(parents=True, exist_ok=True)

            pool_size = 10
            for i in range(pool_size):
                (folder / f"rage_{i:02d}.png").write_bytes(b"STUB")

            retriever = MemeRetriever(root, cooldown_seconds=0)
            history: List[str] = []
            sim_time = 1000.0

            for _ in range(100):
                meme = retriever.get_meme(vibe, current_time=sim_time, cooldown=0)
                self.assertIsNotNone(meme)
                history.append(meme.name)
                sim_time += 1.0

            # Empirical check: every 60-event window has exactly 10 unique memes (pool exhaustion)
            num_windows = len(history) - 60 + 1
            for i in range(num_windows):
                window = history[i : i + 60]
                self.assertEqual(
                    len(set(window)),
                    10,
                    "Small pool of 10 must utilize all 10 available memes in 60-window",
                )

            # Safety window of min(10-1, 60) = 9 guarantees every 9-event window has 9 unique memes
            for i in range(len(history) - 9 + 1):
                sub_win = history[i : i + 9]
                self.assertEqual(len(set(sub_win)), 9, f"Safety window violated in sub-window {i}")

    def test_harness_1c_multi_vibe_pool_uniform_cycling(self):
        """
        Harness 1C: Multi-vibe candidate pool (12 vibes x 10 memes = 120 memes total).
        Uniform round-robin cycling across all 12 vibes over 100 events.
        Asserts len(set(window)) == 60 for all 41 sliding windows.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            vibes = list(Vibe)
            for v in vibes:
                folder = root / VIBE_FOLDER_NAMES[v]
                folder.mkdir(parents=True, exist_ok=True)
                for i in range(10):
                    (folder / f"{v.value}_meme_{i:02d}.png").write_bytes(b"STUB")

            retriever = MemeRetriever(root, cooldown_seconds=0)
            history: List[str] = []
            sim_time = 1000.0

            for step in range(100):
                v = vibes[step % len(vibes)]
                meme = retriever.get_meme(v, current_time=sim_time, cooldown=0)
                self.assertIsNotNone(meme)
                history.append(meme.name)
                sim_time += 1.0

            num_windows = len(history) - 60 + 1
            for i in range(num_windows):
                window = history[i : i + 60]
                self.assertEqual(
                    len(set(window)),
                    60,
                    f"Uniform multi-vibe window {i} had {len(set(window))} unique, expected 60",
                )

    def test_harness_1d_multi_vibe_pool_bursty_adversarial(self):
        """
        Harness 1D: Adversarial multi-vibe challenge:
        When user behavior concentrates on a single vibe (e.g. 15 events of GRINDING)
        within a 60-event window where candidates per vibe = 10 (as in default pack):
        Because safety_window = min(len(candidates)-1, 60) is calculated per-vibe (9),
        memes from the bursty vibe reappear after 9 intervening events, causing
        duplicates in the 60-event window.
        We empirically document this failure mode.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            vibes = list(Vibe)
            for v in vibes:
                folder = root / VIBE_FOLDER_NAMES[v]
                folder.mkdir(parents=True, exist_ok=True)
                for i in range(10):
                    (folder / f"{v.value}_meme_{i:02d}.png").write_bytes(b"STUB")

            retriever = MemeRetriever(root, cooldown_seconds=0)
            history: List[str] = []
            sim_time = 1000.0

            # Simulate bursty pattern: 11 GRINDING requests separated by other vibes
            pattern = (
                [Vibe.GRINDING] * 5
                + [Vibe.SYNTAX_RAGE, Vibe.FLOW_STATE, Vibe.LOST_IN_SCROLL, Vibe.HELP_SEEKING, Vibe.STILLNESS]
                + [Vibe.GRINDING] * 6
            )
            # Pad with other vibes to reach 100 events
            full_schedule = pattern + [vibes[i % len(vibes)] for i in range(100 - len(pattern))]

            for v in full_schedule:
                meme = retriever.get_meme(v, current_time=sim_time, cooldown=0)
                self.assertIsNotNone(meme)
                history.append(meme.name)
                sim_time += 1.0

            window_0 = history[:60]
            # Empirical demonstration: 11 GRINDING memes requested from a pool of 10 memes
            # must produce at least 1 duplicate in the 60-event window.
            self.assertLess(
                len(set(window_0)),
                60,
                "Empirically confirmed: Bursty vibe requests exceeding single-vibe pool size (10) "
                "cause duplicates within the 60-event window.",
            )

    # ─────────────────────────────────────────────────────────────
    # HARNESS 2: CAPTION LENGTH FUZZING (5,000+ RANDOMIZED CONTEXTS)
    # ─────────────────────────────────────────────────────────────

    def test_harness_2_caption_length_fuzzing_5000_samples(self):
        """
        Harness 2: Generates 5,000+ randomized contexts with extreme strings,
        huge titles, special characters, unicode, emojis, and all categories.
        Measures caption lengths and checks the < 40 character budget.
        """
        random.seed(1337)
        emojis = ["🔥", "🪞", "😂", "💻", "💀", "🤦‍♂️", "🚀", "✨", "⚡", "🎉", "🧘", "👀", "🧠", "💣"]
        unicode_scripts = [
            "日本語テキスト_プログラミング",
            "العربية_تطوير_البرمجيات",
            "Русский_текст_ошибки_компиляции",
            "Español_desarrollo_web_rápido",
            "हिन्दी_प्रोग्रामिंग_सॉफ्टवेयर",
            "한국어_코드_디버깅_작업",
            "äöüß_Große_Systemarchitektur",
            "你好世界_超长标题文本",
        ]
        special_injections = [
            "{subject}", "{0}", "%s", "%d", "<script>alert('pwn')</script>",
            "\"double_quote\"", "'single_quote'", "C:\\Windows\\System32\\cmd.exe",
            "https://youtube.com/watch?v=dQw4w9WgXcQ&t=42s&feature=emb_title",
            "SELECT * FROM secrets WHERE '1'='1' --",
            "a" * 300, "b" * 600, " \t \n \r ", "---:::;;;===", "!@#$%^&*()_+"
        ]

        sample_contexts: List[WindowContext] = []
        for _ in range(5000):
            strat = random.randint(0, 4)
            if strat == 0:
                # Extreme length string
                title = "".join(random.choices(string.ascii_letters + string.digits, k=random.randint(60, 300)))
            elif strat == 1:
                # Special character injection
                title = random.choice(special_injections) + " - " + "".join(random.choices(string.ascii_letters, k=25))
            elif strat == 2:
                # Unicode and emoji combinations
                title = f"{random.choice(unicode_scripts)} {' '.join(random.choices(emojis, k=3))} {random.choice(special_injections)}"
            elif strat == 3:
                # Realistic long title with delimiters
                title = "Mega Project: How to Architect Ultra-Low Latency Trading Systems in C++ and Rust - YouTube"
            else:
                # Short specific code file
                title = "auth_manager.py - vihara - Visual Studio Code"

            category = random.choice(["code", "video", "social", "docs", "terminal", "web", ""])
            is_social = (category == "social")
            is_specific = random.choice([True, False])

            ctx = WindowContext(
                subject=title,
                category=category,
                is_specific=is_specific,
                is_social=is_social,
            )
            sample_contexts.append(ctx)

        self.assertEqual(len(sample_contexts), 5000)

        vibes = list(Vibe)
        tracks = ["bihari", "vihara"]

        violations = []
        total_evaluations = 0

        for ctx in sample_contexts:
            for track in tracks:
                vibe = random.choice(vibes)
                caption = get_reflection(vibe, context=ctx, brand_track=track)
                total_evaluations += 1

                self.assertIsInstance(caption, str)
                self.assertGreater(len(caption), 0, "Caption must never be empty")

                if len(caption) >= 40:
                    violations.append({
                        "length": len(caption),
                        "caption": caption,
                        "vibe": vibe.value,
                        "track": track,
                        "category": ctx.category,
                        "subject": ctx.subject[:30],
                    })

        violation_rate = (len(violations) / total_evaluations) * 100.0
        print(f"\n[Fuzzing Results] Total tested: {total_evaluations}, Violations (>=40 chars): {len(violations)} ({violation_rate:.2f}%)")

        if violations:
            violations.sort(key=lambda x: x["length"], reverse=True)
            print("Top 3 Longest Violations:")
            for v in violations[:3]:
                print(f"  {v['length']} chars [{v['track']} / {v['vibe']} / {v['category']}]: '{v['caption']}'")

        # Record findings: does the system strictly meet < 40 chars 100% of the time?
        self.assertEqual(
            len(violations),
            0,
            f"Caption budget violated in {len(violations)}/{total_evaluations} cases ({violation_rate:.2f}%). "
            f"Max length: {violations[0]['length'] if violations else 0} chars."
        )

    # ─────────────────────────────────────────────────────────────
    # HARNESS 3: FLOW STATE BOUNDARY CHALLENGE
    # ─────────────────────────────────────────────────────────────

    def test_harness_3_flow_state_boundary_classification_and_suppression(self):
        """
        Harness 3: Tests boundary conditions around Flow State:
        - Typing speed: 49 vs 50 vs 51 chars/min
        - Backspace rate: 0.079 vs 0.080 vs 0.081
        - Dwell minutes: 9.9 min vs 10.0 min

        Evaluates 3x3x3 = 27 boundary permutations against:
        1. classify_by_rules(event) -> asserts whether classified as FLOW_STATE.
        2. Application popup suppression guardrail -> asserts whether popup is suppressed.
        """
        speeds = [49, 50, 51]
        backspace_rates = [0.079, 0.080, 0.081]
        dwells = [9.9, 10.0]

        results_matrix = []

        for speed in speeds:
            for bs_rate in backspace_rates:
                for dwell in dwells:
                    event = TelemetryEvent(
                        app_name="code.exe",
                        window_title="engine.py - Visual Studio Code",
                        typing_speed=speed,
                        backspace_rate=bs_rate,
                        backspace_count=int(speed * bs_rate),
                        window_switches_3min=0,
                        dwell_minutes=dwell,
                        session_minutes=30.0,
                    )

                    classified = classify_by_rules(event)
                    is_flow_classified = (
                        classified is not None and classified.vibe == Vibe.FLOW_STATE
                    )

                    # In bihari/__main__.py lines 367-371, popup suppression is:
                    # result.vibe == Vibe.FLOW_STATE and event.typing_speed > 40 and event.backspace_rate < 0.10
                    main_py_suppressed = (
                        is_flow_classified
                        and event.typing_speed > 40
                        and event.backspace_rate < 0.10
                    )

                    # Strict F1 Contract: speed > 50 and bs_rate < 0.08 and dwell >= 10.0
                    strict_contract_satisfied = (
                        speed > 50 and bs_rate < 0.08 and dwell >= 10.0
                    )

                    results_matrix.append({
                        "speed": speed,
                        "bs_rate": bs_rate,
                        "dwell": dwell,
                        "classified_flow": is_flow_classified,
                        "classified_conf": classified.confidence if classified else 0.0,
                        "main_suppressed": main_py_suppressed,
                        "strict_contract": strict_contract_satisfied,
                    })

        # Count conditions where strict contract is satisfied
        strict_matches = [r for r in results_matrix if r["strict_contract"]]
        self.assertEqual(len(strict_matches), 1, "Exactly 1 permutation satisfies >50, <0.08, >=10.0 (51, 0.079, 10.0)")

        single_strict = strict_matches[0]
        self.assertTrue(single_strict["classified_flow"])
        self.assertTrue(single_strict["main_suppressed"])

        # Boundary checks:
        # 1. speed == 49 (< 50):
        # In classify_by_rules: speed=49, bs=0.079 matches rule 703 (speed > 25, bs < 0.08)!
        # So it is classified as FLOW_STATE even at speed=49!
        # In bihari/__main__.py: speed=49 > 40, bs=0.079 < 0.10 -> SUPPRESSED!
        # Thus, popups are suppressed at 49 WPM, violating the >50 requirement!
        speed_49_cases = [r for r in results_matrix if r["speed"] == 49 and r["bs_rate"] == 0.079]
        for c in speed_49_cases:
            self.assertTrue(
                c["main_suppressed"],
                "Observation: bihari/__main__.py suppresses at speed 49 because threshold is >40 instead of >50"
            )

        # 2. bs_rate == 0.081 (>= 0.08):
        # In classify_by_rules: speed=51, bs=0.081 matches rule 698 (speed > 50, bs < 0.12)!
        # In bihari/__main__.py: speed=51 > 40, bs=0.081 < 0.10 -> SUPPRESSED!
        # Thus, popups are suppressed at 8.1% backspace rate, violating the <8% requirement!
        bs_081_cases = [r for r in results_matrix if r["speed"] == 51 and r["bs_rate"] == 0.081]
        for c in bs_081_cases:
            self.assertTrue(
                c["main_suppressed"],
                "Observation: bihari/__main__.py suppresses at bs_rate 0.081 because threshold is <0.10 instead of <0.08"
            )

        # 3. dwell == 9.9 (< 10.0 min):
        # In bihari/__main__.py: dwell_minutes is NOT checked at all!
        # Thus, popups are suppressed at dwell 9.9 min (and even 0.0 min), violating the >=10 min requirement!
        dwell_99_cases = [r for r in results_matrix if r["dwell"] == 9.9 and r["speed"] == 51 and r["bs_rate"] == 0.079]
        for c in dwell_99_cases:
            self.assertTrue(
                c["main_suppressed"],
                "Observation: bihari/__main__.py suppresses at dwell 9.9 min because dwell_minutes is omitted from guardrail"
            )

    # ─────────────────────────────────────────────────────────────
    # HARNESS 4: 8-HOUR SIMULATED WORKDAY STRESS TEST
    # ─────────────────────────────────────────────────────────────

    def test_harness_4_eight_hour_simulated_workday_stress_test(self):
        """
        Harness 4: Executes an 8-hour / 28,800-second simulated workday spanning
        960 discrete ticks (30s intervals) cycling through all 12 vibes, idle periods,
        meeting interruptions, erratic switching, and adversarial error injections.

        Asserts:
        - 0 unhandled exceptions across all 960 ticks.
        - 0 crashes.
        - Bounded memory usage (tracemalloc growth < 15 MB).
        """
        tracemalloc.start()
        snapshot_start = tracemalloc.take_snapshot()

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # Set up 12 vibe directories with meme files
            for v in Vibe:
                folder = root / VIBE_FOLDER_NAMES[v]
                folder.mkdir(parents=True, exist_ok=True)
                for i in range(12):
                    (folder / f"{v.value}_{i:02d}.jpg").write_bytes(b"STUB_IMAGE")

            retriever = MemeRetriever(root, cooldown_seconds=0)
            privacy_filter = PrivacyFilter(
                DEFAULTS["privacy"]["blocked_apps"],
                DEFAULTS["privacy"]["blocked_title_keywords"],
            )

            total_ticks = 960  # 960 * 30s = 28,800s = 8 hours
            sim_time = 10000.0

            ticks_processed = 0
            exceptions_caught = []
            vibes_encountered = set()

            for tick in range(total_ticks):
                elapsed_seconds = tick * 30
                hour_of_day = (9 + (elapsed_seconds // 3600)) % 24
                session_minutes = elapsed_seconds / 60.0

                try:
                    # Construct realistic workday phases across 960 ticks
                    phase = (tick // 96) % 10  # 10 phases of 96 ticks (~48 mins each)

                    if phase == 0:
                        # Deep Flow State (VS Code, fast typing, low errors, long dwell)
                        app = "code.exe"
                        title = "core_engine.py - vihara - Visual Studio Code"
                        speed = 65
                        bs_rate = 0.03
                        bs_count = 2
                        switches = 0
                        dwell = 25.0
                    elif phase == 1:
                        # Syntax Rage (VS Code, high backspace rate)
                        app = "code.exe"
                        title = "test_adversarial.py - vihara - Visual Studio Code"
                        speed = 40
                        bs_rate = 0.45
                        bs_count = 18
                        switches = 1
                        dwell = 8.0
                    elif phase == 2:
                        # Help Seeking (Chrome, Stack Overflow / Docs)
                        app = "chrome.exe"
                        title = "python asyncio task timeout - Stack Overflow - Google Chrome"
                        speed = 8
                        bs_rate = 0.02
                        bs_count = 1
                        switches = 3
                        dwell = 4.0
                    elif phase == 3:
                        # Team Standup / Meeting (Teams - meeting suppression)
                        app = "teams.exe"
                        title = "Daily Engineering Sync - Microsoft Teams"
                        speed = 0
                        bs_rate = 0.0
                        bs_count = 0
                        switches = 0
                        dwell = 30.0
                    elif phase == 4:
                        # Meeting Recovery & Afternoon Drift
                        app = "notepad.exe"
                        title = "Meeting Notes.txt - Notepad"
                        speed = 10
                        bs_rate = 0.05
                        bs_count = 1
                        switches = 2
                        dwell = 12.0
                        hour_of_day = 14  # 2 PM
                    elif phase == 5:
                        # Lost in Scroll (YouTube video watching)
                        app = "chrome.exe"
                        title = "Building an OS from scratch in Rust - Episode 1 - YouTube"
                        speed = 0
                        bs_rate = 0.0
                        bs_count = 0
                        switches = 0
                        dwell = 15.0
                    elif phase == 6:
                        # Tab Butterfly (rapid context switches)
                        app = "chrome.exe"
                        title = "Tab 42 - Google Chrome"
                        speed = 5
                        bs_rate = 0.01
                        bs_count = 0
                        switches = 14
                        dwell = 0.5
                    elif phase == 7:
                        # Prolonged Grinding & Burnout Approaching
                        app = "code.exe"
                        title = "compiler.cpp - Visual Studio Code"
                        speed = 15
                        bs_rate = 0.15
                        bs_count = 5
                        switches = 2
                        dwell = 45.0
                        session_minutes = 220.0
                    elif phase == 8:
                        # Stillness / Idle period (away from keyboard)
                        app = "code.exe"
                        title = "compiler.cpp - Visual Studio Code"
                        speed = 0
                        bs_rate = 0.0
                        bs_count = 0
                        switches = 0
                        dwell = 0.0
                    else:
                        # Adversarial Error Injection: extreme, null, or boundary values
                        app = random.choice(["CODE.EXE", "chrome.exe", "", "unknown_app.exe"])
                        title = random.choice([
                            "", " ", "A" * 500, "🔥 unicode bomb 🚀",
                            "KeePassXC - Passwords.kdbx",  # Blocklisted app
                            "Bitwarden - Master Vault",   # Blocklisted app
                        ])
                        speed = random.choice([0, 150, -5])
                        bs_rate = random.choice([0.0, 1.0, 1.5, -0.1])
                        bs_count = random.choice([0, 50, -2])
                        switches = random.choice([0, 30, -1])
                        dwell = random.choice([0.0, 100.0, -10.0])

                    raw_event = TelemetryEvent(
                        app_name=app,
                        window_title=title,
                        typing_speed=max(0, speed),
                        backspace_rate=max(0.0, min(1.0, bs_rate)),
                        backspace_count=max(0, bs_count),
                        window_switches_3min=max(0, switches),
                        dwell_minutes=max(0.0, dwell),
                        session_minutes=session_minutes,
                        hour_of_day=hour_of_day,
                    )

                    # 1. Privacy filter
                    _, sanitized_title = privacy_filter.sanitize(raw_event.app_name, raw_event.window_title)
                    sanitized_event = TelemetryEvent(
                        app_name=raw_event.app_name,
                        window_title=sanitized_title,
                        typing_speed=raw_event.typing_speed,
                        backspace_rate=raw_event.backspace_rate,
                        backspace_count=raw_event.backspace_count,
                        window_switches_3min=raw_event.window_switches_3min,
                        dwell_minutes=raw_event.dwell_minutes,
                        session_minutes=raw_event.session_minutes,
                        hour_of_day=raw_event.hour_of_day,
                    )

                    # 2. Context extraction
                    ctx = extract_context(sanitized_event.app_name, sanitized_event.window_title)

                    # 3. Rule classification
                    vibe_res = classify_by_rules(sanitized_event)

                    if vibe_res is not None:
                        vibes_encountered.add(vibe_res.vibe)

                        # 4. Dual-track reflection generation
                        refl_a = get_reflection(vibe_res.vibe, context=ctx, brand_track="bihari")
                        refl_b = get_reflection(vibe_res.vibe, context=ctx, brand_track="vihara")
                        self.assertIsInstance(refl_a, str)
                        self.assertIsInstance(refl_b, str)

                        # 5. Meme retrieval (only when not meeting and not flow-suppressed)
                        is_meeting = any(
                            kw in sanitized_event.window_title.lower()
                            for kw in ["meeting", "zoom", "teams", "sync"]
                        )
                        is_flow = (
                            vibe_res.vibe == Vibe.FLOW_STATE
                            and sanitized_event.typing_speed > 50
                            and sanitized_event.backspace_rate < 0.08
                            and sanitized_event.dwell_minutes >= 10.0
                        )

                        if not is_meeting and not is_flow:
                            meme_path = retriever.get_meme(
                                vibe_res.vibe, current_time=sim_time, cooldown=0
                            )

                    sim_time += 30.0
                    ticks_processed += 1

                except Exception as exc:
                    exceptions_caught.append((tick, exc))

            snapshot_end = tracemalloc.take_snapshot()
            top_stats = snapshot_end.compare_to(snapshot_start, "lineno")
            total_memory_diff = sum(stat.size_diff for stat in top_stats)
            tracemalloc.stop()

            # Assertions
            self.assertEqual(ticks_processed, 960, "Must complete all 960 simulation ticks")
            self.assertEqual(len(exceptions_caught), 0, f"Encountered unhandled exceptions: {exceptions_caught}")
            self.assertGreaterEqual(
                len(vibes_encountered),
                8,
                f"Workday simulation must exercise diverse vibes (found {len(vibes_encountered)}: {vibes_encountered})",
            )

            # Memory bound: total growth over 960 ticks should be < 15MB
            memory_growth_mb = total_memory_diff / (1024 * 1024)
            print(f"\n[Workday Simulation] 960 ticks completed in memory: {memory_growth_mb:.2f} MB growth")
            self.assertLess(
                memory_growth_mb,
                15.0,
                f"Memory leak detected: memory grew by {memory_growth_mb:.2f} MB (threshold 15 MB)",
            )


if __name__ == "__main__":
    unittest.main()
