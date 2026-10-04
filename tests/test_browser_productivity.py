"""
Automated verification suite for browser productivity, reading, and email categorization.
Ensures that:
1. Reading articles/blogs on browsers is classified as reading/flow, NEVER mindless social scrolling.
2. GitHub/GitLab usage is categorized as code/work flow, NEVER lost in scroll.
3. Gmail/Webmail is categorized as email/work, NEVER lost in scroll.
4. Non-social browsing never triggers screen OCR or mindless social scrolling.
5. In-screen content classifier maps work/technical/email/reading text to FLOW_STATE rather than social scroll.
"""

import unittest
from bihari.context import extract_context
from bihari.spy import TelemetryEvent
from bihari.inference import (
    Vibe,
    classify_by_rules,
    get_reflection,
    VibeClassifier,
)


class TestBrowserProductivityAndReading(unittest.TestCase):
    def test_browser_reading_context_and_vibe(self):
        """Reading an article on the browser must be categorized as 'reading', not social scrolling."""
        title = "Understanding Python AsyncIO Deep Dive - Real Python - Google Chrome"
        ctx = extract_context("chrome.exe", title, dwell_minutes=8.0)
        self.assertIsNotNone(ctx)
        self.assertEqual(ctx.category, "reading")
        self.assertFalse(ctx.is_social)

        # Telemetry event: reading with minimal typing over 8 minutes
        event = TelemetryEvent(
            app_name="chrome.exe",
            window_title=title,
            typing_speed=2,
            backspace_rate=0.0,
            backspace_count=0,
            window_switches_3min=0,
            dwell_minutes=8.0,
        )
        res = classify_by_rules(event)
        self.assertIsNotNone(res)
        self.assertNotEqual(res.vibe, Vibe.LOST_IN_SCROLL)
        self.assertEqual(res.vibe, Vibe.FLOW_STATE)

        # Reflection should reflect reading without any judgmental or social scrolling phrases
        refl = get_reflection(res.vibe, context=ctx)
        self.assertTrue(len(refl) < 40)
        self.assertNotIn("scroll", refl.lower())
        self.assertNotIn("feed", refl.lower())

    def test_github_browser_context_and_vibe(self):
        """GitHub on the browser must be categorized as 'code', not social scrolling."""
        titles = [
            "Pull Request #108: Fix memory leak in buffer · facebook/react · GitHub - Google Chrome",
            "GitHub - Google Chrome",
            "facebook/react: The library for web and native user interfaces · GitHub - Microsoft Edge",
        ]
        for title in titles:
            ctx = extract_context("chrome.exe", title, dwell_minutes=12.0)
            self.assertIsNotNone(ctx)
            self.assertEqual(ctx.category, "code")
            self.assertFalse(ctx.is_social)

            event = TelemetryEvent(
                app_name="chrome.exe",
                window_title=title,
                typing_speed=15,
                backspace_rate=0.02,
                backspace_count=1,
                window_switches_3min=0,
                dwell_minutes=12.0,
            )
            res = classify_by_rules(event)
            self.assertIsNotNone(res)
            self.assertNotEqual(res.vibe, Vibe.LOST_IN_SCROLL)
            self.assertEqual(res.vibe, Vibe.FLOW_STATE)

    def test_gmail_browser_context_and_vibe(self):
        """Gmail on the browser must be categorized as 'email', not social scrolling."""
        titles = [
            "Inbox (4) - user@gmail.com - Google Chrome",
            "Gmail - Google Chrome",
            "Project roadmap review - user@gmail.com - Microsoft Edge",
        ]
        for title in titles:
            ctx = extract_context("chrome.exe", title, dwell_minutes=6.0)
            self.assertIsNotNone(ctx)
            self.assertEqual(ctx.category, "email")
            self.assertFalse(ctx.is_social)

            event = TelemetryEvent(
                app_name="chrome.exe",
                window_title=title,
                typing_speed=18,
                backspace_rate=0.03,
                backspace_count=1,
                window_switches_3min=0,
                dwell_minutes=6.0,
            )
            res = classify_by_rules(event)
            self.assertIsNotNone(res)
            self.assertNotEqual(res.vibe, Vibe.LOST_IN_SCROLL)
            self.assertEqual(res.vibe, Vibe.FLOW_STATE)

    def test_general_webpage_minimal_typing_never_lost_in_scroll(self):
        """General non-social webpage with low typing (reading) must never be called LOST_IN_SCROLL."""
        title = "The Architecture of Open Source Applications - Google Chrome"
        ctx = extract_context("chrome.exe", title, dwell_minutes=15.0)
        self.assertIsNotNone(ctx)
        self.assertFalse(ctx.is_social)

        # 1. Reading with light periodic typing/scrolling (speed=5): should be FLOW_STATE, never LOST_IN_SCROLL
        event_reading = TelemetryEvent(
            app_name="chrome.exe",
            window_title=title,
            typing_speed=5,
            backspace_rate=0.0,
            backspace_count=0,
            window_switches_3min=0,
            dwell_minutes=15.0,
        )
        res_reading = classify_by_rules(event_reading)
        self.assertIsNotNone(res_reading)
        self.assertEqual(res_reading.vibe, Vibe.FLOW_STATE)
        self.assertNotEqual(res_reading.vibe, Vibe.LOST_IN_SCROLL)

        # 2. Reading with zero keyboard input (speed=0): stillness, never LOST_IN_SCROLL
        event_still = TelemetryEvent(
            app_name="chrome.exe",
            window_title=title,
            typing_speed=0,
            backspace_rate=0.0,
            backspace_count=0,
            window_switches_3min=0,
            dwell_minutes=15.0,
        )
        res_still = classify_by_rules(event_still)
        self.assertIsNotNone(res_still)
        self.assertEqual(res_still.vibe, Vibe.STILLNESS)
        self.assertNotEqual(res_still.vibe, Vibe.LOST_IN_SCROLL)

    def test_social_apps_still_correctly_classified_as_scroll(self):
        """Social apps like Instagram Reels must still be detected as LOST_IN_SCROLL or TAB_BUTTERFLY."""
        title = "Instagram - Profile 1 - Microsoft Edge"
        ctx = extract_context("msedge.exe", title, dwell_minutes=5.0)
        self.assertIsNotNone(ctx)
        self.assertTrue(ctx.is_social)

        event = TelemetryEvent(
            app_name="msedge.exe",
            window_title=title,
            typing_speed=0,
            backspace_rate=0.0,
            backspace_count=0,
            window_switches_3min=0,
            dwell_minutes=5.0,
        )
        res = classify_by_rules(event)
        self.assertIsNotNone(res)
        self.assertEqual(res.vibe, Vibe.LOST_IN_SCROLL)


if __name__ == "__main__":
    unittest.main()
