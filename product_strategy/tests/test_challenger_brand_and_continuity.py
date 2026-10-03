"""
Challenger 2 Empirical Verification Suite: Brand, Content & Continuity.

Validates:
- Target 1: Non-technical persona accessibility and absence of residual friction in positioning matrix and installer architecture.
- Target 2: Viral video playbook storyboards (5 scripts, all structural elements, zero placeholders).
- Target 3: 30-day post-launch execution checklist (30 uninterrupted days, tasks, owners, measurable KPIs, zero placeholders).
"""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
STRATEGY_DIR = REPO_ROOT / "product_strategy"


class TestChallengerViralVideoPlaybook(unittest.TestCase):
    """Adversarially validates the Viral Video Playbook content and structure."""

    def setUp(self):
        self.playbook_path = STRATEGY_DIR / "04_gtm_launch_playbook" / "viral_video_playbook.md"
        self.assertTrue(self.playbook_path.is_file(), f"Missing {self.playbook_path}")
        self.content = self.playbook_path.read_text(encoding="utf-8")

    def test_zero_placeholders_in_viral_video_playbook(self):
        """Verify zero placeholder strings (TODO, TBD, [insert], etc.) across viral video playbook."""
        placeholder_patterns = [
            r"\bTODO\b",
            r"\bTBD\b",
            r"\[insert\b.*?\]",
            r"\[replace\b.*?\]",
            r"<insert\b.*?>",
            r"\bFIXME\b",
            r"\bXXX\b",
            r"\[\.\.\.\]",
        ]
        found = []
        for pat in placeholder_patterns:
            matches = re.findall(pat, self.content, re.IGNORECASE)
            if matches:
                found.extend(matches)
        self.assertEqual(len(found), 0, f"Found placeholders in viral_video_playbook.md: {found}")

    def test_all_five_scripts_structural_completeness(self):
        """Verify each of the 5 scripts contains all required production components."""
        script_splits = re.split(r"###\s+Script\s+(\d+):", self.content)
        scripts = {}
        for i in range(1, len(script_splits), 2):
            s_num = int(script_splits[i])
            s_body = script_splits[i+1]
            scripts[s_num] = s_body

        self.assertEqual(len(scripts), 5, f"Expected exactly 5 scripts, found {len(scripts)}")

        required_script_elements = {
            "concept_title": r"Concept Title\s*[:*]+",
            "persona": r"(Target )?Persona\s*[:*]+",
            "runtime": r"Runtime\s*[:*]+\s*\d+\s*Seconds?",
            "audio_sound_design": r"Audio\s*(&|and)\s*Sound\s*Design",
            "camera_framing_visual_cues": r"Camera\s*Framing\s*(&|and)\s*Visual\s*Cue",
            "onscreen_text": r"On-Screen\s*Text(\s*Overlays)?",
            "hook_0_3s": r"0:00[–\-]0:03|0–3s",
            "narrative_conflict": r"(rabbit\s*hole|blocker|syntax\s*rage|prank|interruption|tab\s*butterfly|paralysis|defects|frantic|rebel)",
            "turn_climax": r"(toast\s*slides|slides\s*in|meme|reflection|laugh|spell\s*breaks|pause|silence|Tok|freeze)",
            "call_to_action": r"(link\s*in\s*bio|download|free\s*download|github|try\s*it|try\s*the\s*mirror)"
        }

        for s_num in range(1, 6):
            s_body = scripts.get(s_num)
            self.assertIsNotNone(s_body, f"Script {s_num} is missing")
            for elem_name, elem_regex in required_script_elements.items():
                match = re.search(elem_regex, s_body, re.IGNORECASE)
                self.assertIsNotNone(match, f"Script {s_num} missing {elem_name} matching {elem_regex}")

            # Check table rows for action beats
            table_rows = re.findall(r"\|\s*\*\*0:\d+.*?\|\s*.*?\s*\|\s*.*?\s*\|\s*.*?\s*\|", s_body)
            self.assertGreaterEqual(len(table_rows), 4, f"Script {s_num} has insufficient action beats ({len(table_rows)})")


class TestChallengerPostLaunchChecklist(unittest.TestCase):
    """Adversarially validates the 30-Day Post-Launch Checklist continuity and completeness."""

    def setUp(self):
        self.checklist_path = STRATEGY_DIR / "04_gtm_launch_playbook" / "post_launch_30day_checklist.md"
        self.assertTrue(self.checklist_path.is_file(), f"Missing {self.checklist_path}")
        self.content = self.checklist_path.read_text(encoding="utf-8")

    def test_zero_placeholders_in_30day_checklist(self):
        """Verify zero placeholder strings across 30-day checklist."""
        placeholder_patterns = [
            r"\bTODO\b",
            r"\bTBD\b",
            r"\[insert\b.*?\]",
            r"\[replace\b.*?\]",
            r"<insert\b.*?>",
            r"\bFIXME\b",
            r"\bXXX\b",
            r"\[\.\.\.\]",
        ]
        found = []
        for pat in placeholder_patterns:
            matches = re.findall(pat, self.content, re.IGNORECASE)
            if matches:
                found.extend(matches)
        self.assertEqual(len(found), 0, f"Found placeholders in post_launch_30day_checklist.md: {found}")

    def test_all_30_days_continuity_tasks_owners_and_kpis(self):
        """Verify every single day from Day 1 to Day 30 is present with tasks, owners, and measurable KPIs."""
        day_splits = re.split(r"###\s+Day\s+(\d+):", self.content)
        days = {}
        for i in range(1, len(day_splits), 2):
            d_num = int(day_splits[i])
            d_body = day_splits[i+1]
            days[d_num] = d_body

        self.assertEqual(len(days), 30, f"Expected 30 days, found {len(days)}")

        for d_num in range(1, 31):
            d_body = days.get(d_num)
            self.assertIsNotNone(d_body, f"Day {d_num} is missing from checklist")

            # Check action items
            has_tasks = re.search(r"(Detailed Action Items|Tasks|Action Items)", d_body, re.IGNORECASE)
            self.assertIsNotNone(has_tasks, f"Day {d_num} missing action items")

            # Check owner
            owner_match = re.search(r"Owner\s*/\s*Channel\s*[:*]+([^\n\r]+)", d_body, re.IGNORECASE)
            self.assertIsNotNone(owner_match, f"Day {d_num} missing Owner / Channel")
            owner_str = owner_match.group(1).strip()
            self.assertGreater(len(owner_str), 5, f"Day {d_num} owner string too short: '{owner_str}'")

            # Check KPI
            kpi_inline_match = re.search(r"Target KPI\s*(?:\([^\)]*\))?\s*[:*]+\s*([^\n\r]+)", d_body, re.IGNORECASE)
            kpi_subbullets = re.findall(r"Target KPI[\s\S]*?(?:(?:\r?\n\s+-\s+.*)+)", d_body, re.IGNORECASE)
            kpi_str = ""
            if kpi_inline_match and len(kpi_inline_match.group(1).strip()) > 3:
                kpi_str = kpi_inline_match.group(1).strip()
            elif kpi_subbullets:
                kpi_str = kpi_subbullets[0].strip()

            self.assertGreater(len(kpi_str), 10, f"Day {d_num} KPI string too short or missing: '{kpi_str}'")

            # Bullet points
            bullet_items = re.findall(r"^\s*-\s+.*", d_body, re.MULTILINE)
            self.assertGreaterEqual(len(bullet_items), 2, f"Day {d_num} has insufficient detail ({len(bullet_items)} bullets)")


class TestChallengerNonTechnicalAccessibility(unittest.TestCase):
    """Adversarially validates that non-technical personas are addressable by zero-friction packaging."""

    def test_persona_and_packaging_coherence(self):
        pos_path = STRATEGY_DIR / "02_brand_positioning" / "positioning_matrix.md"
        inst_path = STRATEGY_DIR / "01_technical_packaging" / "standalone_installer_and_autoupdate_architecture.md"
        
        pos_content = pos_path.read_text(encoding="utf-8")
        inst_content = inst_path.read_text(encoding="utf-8")

        # Persona 1: Aarav / Maya
        self.assertTrue(re.search(r"Persona 1:.*?Aarav", pos_content, re.IGNORECASE))
        self.assertTrue(re.search(r"Non-technical casual computer user", pos_content, re.IGNORECASE))
        self.assertTrue(re.search(r"Intimidated by the terminal|command prompt|Python", pos_content, re.IGNORECASE))
        self.assertTrue(re.search(r"single-click download", pos_content, re.IGNORECASE))

        # Persona 3: Sarah
        self.assertTrue(re.search(r"Persona 3:.*?Sarah", pos_content, re.IGNORECASE))
        self.assertTrue(re.search(r"Non-technical corporate professional", pos_content, re.IGNORECASE))
        self.assertTrue(re.search(r"IT-restricted machine|no admin privileges|CrowdStrike", pos_content, re.IGNORECASE))
        self.assertTrue(re.search(r"Track B.*?Vihara", pos_content, re.IGNORECASE))

        # Windows Packaging: Inno Setup PrivilegesRequired=lowest for standard user / enterprise non-admin
        self.assertTrue(re.search(r"PrivilegesRequired\s*=\s*lowest", inst_content))
        self.assertTrue(re.search(r"\{localappdata\}\\Programs\\Vihara", inst_content))
        self.assertTrue(re.search(r"/VERYSILENT", inst_content))

        # macOS Packaging: Notarization, hardened runtime, graceful degradation
        self.assertTrue(re.search(r"notarytool", inst_content))
        self.assertTrue(re.search(r"gracefully downgrades to window-title-only", inst_content, re.IGNORECASE))

        # Zero-Surveillance Architecture
        self.assertTrue(re.search(r"Zero Keylogging", pos_content, re.IGNORECASE))
        self.assertTrue(re.search(r"RAM-Only Volatile", pos_content, re.IGNORECASE))
        self.assertTrue(re.search(r"1Password|Bitwarden|KeePass", pos_content))


if __name__ == "__main__":
    unittest.main()
