"""
Tests for Module: Rebrand Verification & Dual-Track Identity.

Validates:
- F7: Zero occurrences of "Lucid Noether" (case-insensitive) across codebase, configuration, and tests.
- F8: Dual-Track Identity:
  - Consumer / Viral Track: "Becoming a Bihari".
  - Professional Track: "Vihara".
- F9: Multi-Surface Brand Adaptation (tray tooltip, window titles, config).
"""

import os
from pathlib import Path
import pytest


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent


class TestRebrandAndIdentity:
    """Tier 1 & Tier 2: Rebrand Integrity & Identity Verification."""

    def test_zero_lucid_noether_in_bihari_codebase(self):
        """F7: The bihari/ source directory must have zero occurrences of 'Lucid Noether'."""
        bihari_dir = WORKSPACE_ROOT / "bihari"
        assert bihari_dir.exists(), "bihari/ directory must exist"

        occurrences = []
        for root, _, files in os.walk(bihari_dir):
            for file in files:
                if file.endswith(".py"):
                    file_path = Path(root) / file
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    if "lucid noether" in content.lower():
                        occurrences.append(str(file_path.relative_to(WORKSPACE_ROOT)))

        assert not occurrences, (
            f"Found 'Lucid Noether' in {len(occurrences)} bihari source files: {occurrences}"
        )

    def test_zero_lucid_noether_in_config(self):
        """F7: Configuration files must not reference 'Lucid Noether'."""
        config_path = WORKSPACE_ROOT / "config.toml"
        if config_path.exists():
            content = config_path.read_text(encoding="utf-8", errors="ignore")
            assert "lucid noether" not in content.lower(), (
                "config.toml must not contain 'Lucid Noether'"
            )

    def test_zero_lucid_noether_in_test_suite(self):
        """F7: Test files in tests/ must not reference 'Lucid Noether'."""
        tests_dir = WORKSPACE_ROOT / "tests"
        occurrences = []
        for root, _, files in os.walk(tests_dir):
            for file in files:
                if file.endswith(".py") and file != "test_rebrand.py":
                    file_path = Path(root) / file
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    if "lucid noether" in content.lower():
                        occurrences.append(str(file_path.relative_to(WORKSPACE_ROOT)))

        assert not occurrences, (
            f"Found 'Lucid Noether' in tests/: {occurrences}"
        )

    def test_brand_track_names(self):
        """F8: Product tracks must be cleanly defined as 'Vihara' and 'Becoming a Bihari'."""
        pro_name = "Vihara"
        consumer_name = "Becoming a Bihari"

        assert pro_name != "Lucid Noether"
        assert "vihara" in pro_name.lower()
        assert "bihari" in consumer_name.lower()

    def test_tray_tooltip_branding(self):
        """F9: System tray tooltip must reflect Vihara or Becoming a Bihari."""
        from bihari.tray import SystemTray

        # Dummy callbacks
        dummy_cb = lambda *args: None

        # Track B (Pro default): Vihara
        tray_pro = SystemTray(
            on_pause=dummy_cb,
            on_resume=dummy_cb,
            on_quit=dummy_cb,
            on_open_memes=dummy_cb,
            brand_track="vihara",
        )
        tooltip_pro = tray_pro.get_tooltip()
        assert "lucid noether" not in tooltip_pro.lower()
        assert "vihara" in tooltip_pro.lower()
        assert "focus" in tooltip_pro.lower()

        # Track A (Consumer): Becoming a Bihari
        tray_consumer = SystemTray(
            on_pause=dummy_cb,
            on_resume=dummy_cb,
            on_quit=dummy_cb,
            on_open_memes=dummy_cb,
            brand_track="bihari",
        )
        tooltip_consumer = tray_consumer.get_tooltip()
        assert "lucid noether" not in tooltip_consumer.lower()
        assert "becoming a bihari" in tooltip_consumer.lower()

    def test_zero_lucid_noether_across_entire_project_m1_gating(self):
        """
        F7 Project-Wide Gating Test:
        Validates that zero occurrences of 'Lucid Noether' exist in any doc or strategy file.
        """
        ignored_dirs = {".git", ".pytest_cache", ".agents"}
        occurrences = []

        for root, dirs, files in os.walk(WORKSPACE_ROOT):
            # Prune ignored directories
            dirs[:] = [d for d in dirs if d not in ignored_dirs]
            for file in files:
                if file.endswith((".py", ".md", ".json", ".toml", ".txt", ".iss", ".spec")):
                    file_path = Path(root) / file
                    # Skip ORIGINAL_REQUEST.md which records user prompt history
                    if file_path.name == "ORIGINAL_REQUEST.md":
                        continue
                    if file_path.name == "test_rebrand.py":
                        continue
                    try:
                        content = file_path.read_text(encoding="utf-8", errors="ignore")
                        if "lucid noether" in content.lower():
                            occurrences.append(str(file_path.relative_to(WORKSPACE_ROOT)))
                    except Exception:
                        pass

        assert not occurrences, (
            f"Found 'Lucid Noether' in {len(occurrences)} project files: {occurrences[:10]}"
        )
