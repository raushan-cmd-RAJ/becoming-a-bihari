"""
Tests for Module: Reflection Generation & Caption Budget.

Validates:
- F4: Strict Reflection Caption Budget: All reflection captions < 40 chars; template <= 20 chars, condensed subject <= 16 chars.
- F5: Contextual Subject Inclusion Rate: >= 80% of events where subject is extractable include context-specific subject.
- F8 & F10: Dual Reflection Banks: Separate copy tracks for Track A (Bihari roasts) and Track B (Vihara reflections).
- Condensation logic: Truncation, punctuation stripping, delimiter splitting, trailing preposition removal.
- Dedicated video reflections (SHORT_PUNCHY_REFLECTIONS, SHORT_VIDEO_REFLECTIONS).
- Dedicated social reflections (SHORT_SOCIAL_REFLECTIONS).
- Contextual reflection templates for code editors, docs, and terminals.
"""

import random
import pytest

from bihari.inference import (
    get_reflection,
    condense_subject,
    Vibe,
    REFLECTIONS,
    CONTEXTUAL_TEMPLATES,
    CONTEXTUAL_TEMPLATES_TRACK_A,
    CONTEXTUAL_TEMPLATES_TRACK_B,
    SHORT_VIDEO_REFLECTIONS,
    SHORT_PUNCHY_REFLECTIONS,
    SHORT_SOCIAL_REFLECTIONS,
    SHORT_SOCIAL_CONTEXTUAL,
    SHORT_VIDEO_REFLECTIONS_TRACK_B,
    SHORT_PUNCHY_REFLECTIONS_TRACK_B,
    SHORT_SOCIAL_REFLECTIONS_TRACK_B,
    SHORT_SOCIAL_CONTEXTUAL_TRACK_B,
)
from bihari.context import WindowContext


class TestReflectionsAndCaptionBudget:
    """Tier 1, 2 & 3: Reflection Precision & Character Budget Verification."""

    def test_short_punchy_reflections_budget(self):
        """F4: Every punchline in SHORT_PUNCHY_REFLECTIONS (Track A) must be strictly under 40 characters."""
        for phrase in SHORT_PUNCHY_REFLECTIONS:
            assert len(phrase) < 40, f"Track A punchline too long ({len(phrase)} chars): '{phrase}'"

    def test_short_punchy_reflections_track_b_budget(self):
        """F4: Every punchline in SHORT_PUNCHY_REFLECTIONS_TRACK_B (Track B) must be strictly under 40 characters."""
        for phrase in SHORT_PUNCHY_REFLECTIONS_TRACK_B:
            assert len(phrase) < 40, f"Track B punchline too long ({len(phrase)} chars): '{phrase}'"

    def test_short_social_reflections_budget(self):
        """F4: Every caption in SHORT_SOCIAL_REFLECTIONS (Track A) must be strictly under 40 characters."""
        for phrase in SHORT_SOCIAL_REFLECTIONS:
            assert len(phrase) < 40, f"Track A social reflection too long ({len(phrase)} chars): '{phrase}'"

    def test_short_social_reflections_track_b_budget(self):
        """F4: Every caption in SHORT_SOCIAL_REFLECTIONS_TRACK_B (Track B) must be strictly under 40 characters."""
        for phrase in SHORT_SOCIAL_REFLECTIONS_TRACK_B:
            assert len(phrase) < 40, f"Track B social reflection too long ({len(phrase)} chars): '{phrase}'"

    def test_short_video_reflections_budget_with_condensed_subject(self):
        """F4: Video reflections with a condensed subject (<=16 chars) must stay under 40 characters."""
        sample_subject = "A" * 16  # Max condensed subject length
        for template in SHORT_VIDEO_REFLECTIONS + SHORT_VIDEO_REFLECTIONS_TRACK_B:
            formatted = template.format(subject=sample_subject)
            assert len(formatted) < 40, f"Video template exceeded budget ({len(formatted)} chars): '{formatted}'"

    @pytest.mark.parametrize("input_title, max_c, expected_substr", [
        ("Long Tutorial: How to Build Modern Web Applications", 16, "How to Build"),
        ("auth_service.py - vihara - Visual Studio Code", 16, "auth_service.py"),
        ("Super Long Video Title That Goes On Forever and Ever", 14, "Super Long"),
        ("Video Title with trailing preposition on", 20, "Video Title"),
    ])
    def test_condense_subject_budget_and_sanitization(self, input_title, max_c, expected_substr):
        """Subject condenser must enforce length budget and strip noise/trailing prepositions."""
        condensed = condense_subject(input_title, max_chars=max_c)
        assert len(condensed) <= max_c
        assert expected_substr.lower() in condensed.lower()

    def test_contextual_subject_inclusion_rate_code(self):
        """
        F5 Contract:
        When a specific subject is available in code context, at least 80% of
        generated reflections include the context-specific subject reference.
        """
        random.seed(42)
        ctx = WindowContext(
            subject="auth_service.py",
            category="code",
            is_specific=True,
        )

        sample_size = 1000
        included_count = 0
        for _ in range(sample_size):
            text = get_reflection(Vibe.SYNTAX_RAGE, context=ctx, brand_track="bihari")
            assert len(text) < 40, f"Caption too long ({len(text)}): '{text}'"
            if "auth_service.py" in text:
                included_count += 1

        inclusion_rate = included_count / sample_size
        assert inclusion_rate >= 0.80, (
            f"Subject inclusion rate {inclusion_rate:.1%} fell below target (expected >= 80%)."
        )

    def test_contextual_subject_inclusion_rate_video(self):
        """F5 Contract: Video context achieves >= 80% subject inclusion rate with len < 40."""
        ctx = WindowContext(
            subject="Tutorial: PyTorch Basics",
            category="video",
            is_specific=True,
        )
        sample_size = 500
        included_count = 0
        for _ in range(sample_size):
            text = get_reflection(Vibe.LOST_IN_SCROLL, context=ctx, brand_track="bihari")
            assert len(text) < 40, f"Caption too long ({len(text)}): '{text}'"
            if "PyTorch Basics" in text:
                included_count += 1

        inclusion_rate = included_count / sample_size
        assert inclusion_rate >= 0.80, (
            f"Video subject inclusion rate {inclusion_rate:.1%} fell below target (expected >= 80%)."
        )

    def test_contextual_subject_inclusion_rate_social(self):
        """F5 Contract: Social context achieves >= 80% subject inclusion rate with len < 40."""
        ctx = WindowContext(
            subject="Design Trends 2026",
            category="social",
            is_specific=True,
            is_social=True,
        )
        sample_size = 500
        included_count = 0
        for _ in range(sample_size):
            text = get_reflection(Vibe.LOST_IN_SCROLL, context=ctx, brand_track="bihari")
            assert len(text) < 40, f"Caption too long ({len(text)}): '{text}'"
            if "Design Trends" in text:
                included_count += 1

        inclusion_rate = included_count / sample_size
        assert inclusion_rate >= 0.80, (
            f"Social subject inclusion rate {inclusion_rate:.1%} fell below target (expected >= 80%)."
        )

    def test_video_context_reflection_precision_dual_track(self):
        """F2 & F5: Video context surfaces category-specific reflections for both tracks."""
        ctx = WindowContext(
            subject="Neural Networks",
            category="video",
            is_specific=True,
        )

        # Track A: Bihari consumer track
        for _ in range(25):
            ref_a = get_reflection(Vibe.LOST_IN_SCROLL, context=ctx, brand_track="bihari")
            assert len(ref_a) < 40
            valid_prefixes_a = [t.split("{")[0] for t in SHORT_VIDEO_REFLECTIONS]
            matches_a = (
                ref_a in SHORT_PUNCHY_REFLECTIONS
                or any(ref_a.startswith(p) for p in valid_prefixes_a)
            )
            assert matches_a is True

        # Track B: Vihara professional track
        for _ in range(25):
            ref_b = get_reflection(Vibe.LOST_IN_SCROLL, context=ctx, brand_track="vihara")
            assert len(ref_b) < 40
            valid_prefixes_b = [t.split("{")[0] for t in SHORT_VIDEO_REFLECTIONS_TRACK_B]
            matches_b = (
                ref_b in SHORT_PUNCHY_REFLECTIONS_TRACK_B
                or any(ref_b.startswith(p) for p in valid_prefixes_b)
            )
            assert matches_b is True

    def test_social_context_reflection_precision_dual_track(self):
        """F8 & F10: Social context surfaces dedicated social scroll reflections per brand track."""
        ctx = WindowContext(
            subject="Instagram Reels",
            category="social",
            is_specific=True,
            is_social=True,
        )

        valid_social_prefixes_a = [t.split("{")[0] for t in SHORT_SOCIAL_CONTEXTUAL]
        # Track A returns from SHORT_SOCIAL_REFLECTIONS or SHORT_SOCIAL_CONTEXTUAL
        for _ in range(15):
            ref_a = get_reflection(Vibe.LOST_IN_SCROLL, context=ctx, brand_track="bihari")
            assert len(ref_a) < 40
            assert ref_a in SHORT_SOCIAL_REFLECTIONS or any(ref_a.startswith(p) for p in valid_social_prefixes_a)

        valid_social_prefixes_b = [t.split("{")[0] for t in SHORT_SOCIAL_CONTEXTUAL_TRACK_B]
        # Track B returns from SHORT_SOCIAL_REFLECTIONS_TRACK_B or SHORT_SOCIAL_CONTEXTUAL_TRACK_B
        for _ in range(15):
            ref_b = get_reflection(Vibe.LOST_IN_SCROLL, context=ctx, brand_track="vihara")
            assert len(ref_b) < 40
            assert ref_b in SHORT_SOCIAL_REFLECTIONS_TRACK_B or any(ref_b.startswith(p) for p in valid_social_prefixes_b)

    def test_generic_fallback_when_no_context(self):
        """When no context is provided, a non-empty reflection from the general pool is returned."""
        for track in ("bihari", "vihara"):
            for vibe in Vibe:
                reflection = get_reflection(vibe, context=None, brand_track=track)
                assert isinstance(reflection, str)
                assert len(reflection) > 0

    def test_all_prototype_reflection_phrases_under_40_chars(self):
        """
        F4 Milestone M2 Gating Test:
        Validates that all static phrases across all 12 vibes in REFLECTIONS
        are strictly < 40 characters.
        """
        violations = []
        for vibe, phrases in REFLECTIONS.items():
            for p in phrases:
                if len(p) >= 40:
                    violations.append((vibe.value, p, len(p)))

        assert not violations, f"Found {len(violations)} reflections >= 40 chars: {violations}"

    def test_all_contextual_templates_with_max_subject_under_40_chars(self):
        """Validate all contextual templates formatted with max 16-char subject are strictly < 40 chars."""
        sub = "A" * 16
        for track, pool in [("Track A", CONTEXTUAL_TEMPLATES_TRACK_A), ("Track B", CONTEXTUAL_TEMPLATES_TRACK_B)]:
            for vibe, templates in pool.items():
                for t in templates:
                    formatted = t.format(subject=sub)
                    assert len(formatted) < 40, f"[{track}] {vibe} template too long ({len(formatted)} chars): '{formatted}'"
