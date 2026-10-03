"""
End-to-End Test Suite for Vihara ("Becoming a Bihari") Product Strategy & GTM Package.

Validates:
- Tier 1: Deliverable file existence, markdown completeness, and document section integrity.
- Tier 2: Draft-07 JSON Schema validity, pack manifest conformance, adversarial schema boundary cases,
          persona matrix depth (>=3 personas, casual user inclusion), dual-track branding specifications,
          pricing tier matrix ($0, $9/mo, $79/yr, $149, $15/seat), viral video storyboards (>=5 scripts),
          and 30-day day-by-day continuity without gaps.
- Tier 3: Cross-deliverable consistency across Product Hunt FAQ, Show HN, 30-day checklist, and branding contracts.
"""

import json
import os
import re
import unittest
from pathlib import Path
import jsonschema
from jsonschema import Draft7Validator


# Base directories
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
STRATEGY_DIR = REPO_ROOT / "product_strategy"


class TestTier1FileExistenceAndStructure(unittest.TestCase):
    """Tier 1: Verifies existence and substantive markdown structural completeness for all deliverables."""

    REQUIRED_FILES = [
        # M1: Technical Packaging & Packs
        STRATEGY_DIR / "01_technical_packaging" / "standalone_installer_and_autoupdate_architecture.md",
        STRATEGY_DIR / "01_technical_packaging" / "meme_pack_specification.md",
        STRATEGY_DIR / "01_technical_packaging" / "meme_pack_schema.json",
        STRATEGY_DIR / "01_technical_packaging" / "sample_pack" / "pack.json",
        STRATEGY_DIR / "01_technical_packaging" / "sample_pack" / "memes" / "lost_in_scroll.png.meta.json",
        STRATEGY_DIR / "01_technical_packaging" / "sample_pack" / "memes" / "syntax_rage.png.meta.json",
        STRATEGY_DIR / "01_technical_packaging" / "sample_pack" / "audio" / "soft_chime.wav.meta.json",
        # M2: Brand Positioning
        STRATEGY_DIR / "02_brand_positioning" / "positioning_matrix.md",
        STRATEGY_DIR / "02_brand_positioning" / "dual_track_branding_guide.md",
        # M3: Commercial Strategy
        STRATEGY_DIR / "03_commercial_strategy" / "commercial_strategy.md",
        # M4: Viral GTM & Launch Playbook
        STRATEGY_DIR / "04_gtm_launch_playbook" / "product_hunt_launch_kit.md",
        STRATEGY_DIR / "04_gtm_launch_playbook" / "show_hn_launch_kit.md",
        STRATEGY_DIR / "04_gtm_launch_playbook" / "viral_video_playbook.md",
        STRATEGY_DIR / "04_gtm_launch_playbook" / "post_launch_30day_checklist.md",
    ]

    def test_all_required_deliverable_files_exist(self):
        """Verify that every single required file across M1-M4 exists on disk."""
        missing = []
        for file_path in self.REQUIRED_FILES:
            if not file_path.is_file():
                missing.append(str(file_path.relative_to(REPO_ROOT)))
        self.assertEqual(len(missing), 0, f"Missing required deliverables: {missing}")

    def test_markdown_files_have_substantive_content(self):
        """Verify that all markdown deliverables have substantive content (>1,500 characters)."""
        markdown_files = [f for f in self.REQUIRED_FILES if f.suffix == ".md"]
        for md_path in markdown_files:
            content = md_path.read_text(encoding="utf-8")
            self.assertGreater(
                len(content),
                1500,
                f"File {md_path.name} is too brief or a placeholder ({len(content)} chars)",
            )

    def test_installer_and_autoupdate_doc_structure(self):
        """Verify standalone installer architecture covers all 3 platforms, PyInstaller, and auto-update."""
        doc = (STRATEGY_DIR / "01_technical_packaging" / "standalone_installer_and_autoupdate_architecture.md").read_text(encoding="utf-8")
        required_patterns = [
            r"Inno Setup",
            r"\.dmg|notarytool|Apple",
            r"AppImage",
            r"PyInstaller",
            r"Auto-Update|version\.json",
            r"System Tray|<40MB|<0\.1%",
        ]
        for pat in required_patterns:
            self.assertTrue(
                re.search(pat, doc, re.IGNORECASE),
                f"Installer architecture document missing required topic matching /{pat}/",
            )

    def test_meme_pack_specification_doc_structure(self):
        """Verify meme pack specification covers .lucidpack format, 12 vibes, and manifest loader."""
        doc = (STRATEGY_DIR / "01_technical_packaging" / "meme_pack_specification.md").read_text(encoding="utf-8")
        required_patterns = [
            r"\.lucidpack",
            r"pack\.json",
            r"12\s+Canonical",
            r"FLOW_STATE",
            r"SYNTAX_RAGE",
            r"LOST_IN_SCROLL",
            r"Dynamic.*Loading|Hot-Reloading",
        ]
        for pat in required_patterns:
            self.assertTrue(
                re.search(pat, doc, re.IGNORECASE),
                f"Meme pack specification missing required topic matching /{pat}/",
            )

    def test_positioning_matrix_doc_structure(self):
        """Verify positioning matrix covers core philosophy, <150ms mechanics, and zero-surveillance."""
        doc = (STRATEGY_DIR / "02_brand_positioning" / "positioning_matrix.md").read_text(encoding="utf-8")
        required_patterns = [
            r"Mirror,\s*Not\s*a\s*Judge",
            r"150\s*ms",
            r"Metacognitive Gap|Cognitive Defusion",
            r"Zero-Surveillance|Zero Keylogging",
            r"RAM-Only|Volatile.*OCR",
        ]
        for pat in required_patterns:
            self.assertTrue(
                re.search(pat, doc, re.IGNORECASE),
                f"Positioning matrix missing required topic matching /{pat}/",
            )

    def test_dual_track_branding_guide_structure(self):
        """Verify branding guide covers Track A vs Track B, color palettes, and toast design specs."""
        doc = (STRATEGY_DIR / "02_brand_positioning" / "dual_track_branding_guide.md").read_text(encoding="utf-8")
        required_patterns = [
            r"Becoming a Bihari",
            r"Vihara",
            r"Electric Amber|#FF8C00",
            r"Obsidian|#121212",
            r"Prussian Blue|Prussian Slate|#0B1B2B",
            r"Frosted Mica|#162638",
            r"Toast.*Design|Toast Notification",
        ]
        for pat in required_patterns:
            self.assertTrue(
                re.search(pat, doc, re.IGNORECASE),
                f"Dual-track branding guide missing required topic matching /{pat}/",
            )

    def test_commercial_strategy_doc_structure(self):
        """Verify commercial strategy covers tier matrix, feature gating, 70/30 split, and unit economics."""
        doc = (STRATEGY_DIR / "03_commercial_strategy" / "commercial_strategy.md").read_text(encoding="utf-8")
        required_patterns = [
            r"Free Community",
            r"Pro Individual",
            r"Creator Marketplace|Creator Packs",
            r"Enterprise|Team.*B2B",
            r"70/30",
            r"Unit Economics|Breakeven",
        ]
        for pat in required_patterns:
            self.assertTrue(
                re.search(pat, doc, re.IGNORECASE),
                f"Commercial strategy missing required topic matching /{pat}/",
            )

    def test_gtm_launch_playbooks_structure(self):
        """Verify GTM playbooks cover Product Hunt, Show HN, video scripts, and 30-day checklist."""
        ph_doc = (STRATEGY_DIR / "04_gtm_launch_playbook" / "product_hunt_launch_kit.md").read_text(encoding="utf-8")
        hn_doc = (STRATEGY_DIR / "04_gtm_launch_playbook" / "show_hn_launch_kit.md").read_text(encoding="utf-8")
        video_doc = (STRATEGY_DIR / "04_gtm_launch_playbook" / "viral_video_playbook.md").read_text(encoding="utf-8")
        check_doc = (STRATEGY_DIR / "04_gtm_launch_playbook" / "post_launch_30day_checklist.md").read_text(encoding="utf-8")

        self.assertIn("Maker First-Comment", ph_doc)
        self.assertIn("Comprehensive Launch FAQ", ph_doc)
        self.assertIn("Show HN", hn_doc)
        self.assertIn("Privacy Battlecard", hn_doc)
        self.assertIn("Viral Video Playbook", video_doc)
        self.assertIn("Phase 1: Launch Spike", check_doc)
        self.assertIn("Phase 4: Pro Conversion Optimization", check_doc)


class TestTier2BoundaryAndContentValidation(unittest.TestCase):
    """Tier 2: Deep boundary, schema, and content validation."""

    CANONICAL_VIBES = [
        "FLOW_STATE",
        "GRINDING",
        "BURNOUT_APPROACHING",
        "SYNTAX_RAGE",
        "HELP_SEEKING",
        "MOUNTING_FRICTION",
        "WANDERING",
        "LOST_IN_SCROLL",
        "TAB_BUTTERFLY",
        "STILLNESS",
        "MEETING_RECOVERY",
        "AFTERNOON_DRIFT",
    ]

    def setUp(self):
        self.schema_path = STRATEGY_DIR / "01_technical_packaging" / "meme_pack_schema.json"
        self.sample_pack_path = STRATEGY_DIR / "01_technical_packaging" / "sample_pack" / "pack.json"

        with open(self.schema_path, "r", encoding="utf-8") as f:
            self.schema = json.load(f)

        with open(self.sample_pack_path, "r", encoding="utf-8") as f:
            self.sample_pack = json.load(f)

    def test_meme_pack_schema_is_valid_draft7(self):
        """Verify meme_pack_schema.json is a valid Draft-07 JSON Schema."""
        Draft7Validator.check_schema(self.schema)
        self.assertEqual(self.schema.get("$schema"), "http://json-schema.org/draft-07/schema#")
        required_fields = self.schema.get("required", [])
        for field in ["id", "schema_version", "name", "version", "author", "brand_track", "vibes"]:
            self.assertIn(field, required_fields)

    def test_sample_pack_validates_against_schema(self):
        """Verify sample_pack/pack.json passes Draft-07 schema validation without errors."""
        validator = Draft7Validator(self.schema)
        errors = list(validator.iter_errors(self.sample_pack))
        self.assertEqual(len(errors), 0, f"Sample pack validation failed: {[e.message for e in errors]}")

    def test_sample_pack_contains_all_12_canonical_vibes(self):
        """Verify sample pack implements all 12 canonical cognitive drift vibes."""
        vibes = self.sample_pack.get("vibes", {})
        for vibe in self.CANONICAL_VIBES:
            self.assertIn(vibe, vibes, f"Sample pack missing canonical vibe: {vibe}")
            self.assertIn("reflections", vibes[vibe])
            self.assertGreater(len(vibes[vibe]["reflections"]), 0)

    def test_sample_pack_metadata_files_are_valid(self):
        """Verify sample pack asset metadata files exist and have valid structure."""
        meta_files = [
            STRATEGY_DIR / "01_technical_packaging" / "sample_pack" / "memes" / "lost_in_scroll.png.meta.json",
            STRATEGY_DIR / "01_technical_packaging" / "sample_pack" / "memes" / "syntax_rage.png.meta.json",
            STRATEGY_DIR / "01_technical_packaging" / "sample_pack" / "audio" / "soft_chime.wav.meta.json",
        ]
        for meta_path in meta_files:
            with open(meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertTrue(
                "asset_name" in data or "filename" in data,
                f"Neither 'asset_name' nor 'filename' found in {meta_path.name}",
            )
            self.assertIn("sha256", data)

    def test_adversarial_schema_validation_rejections(self):
        """Adversarial Verification: Ensure schema strictly rejects invalid manifests."""
        validator = Draft7Validator(self.schema)

        # Case 1: Missing required field 'id'
        bad_manifest_1 = dict(self.sample_pack)
        del bad_manifest_1["id"]
        self.assertTrue(any("id" in e.message for e in validator.iter_errors(bad_manifest_1)))

        # Case 2: Invalid semantic version
        bad_manifest_2 = dict(self.sample_pack)
        bad_manifest_2["version"] = "1.0-invalid"
        self.assertTrue(any("version" in e.path for e in validator.iter_errors(bad_manifest_2)))

        # Case 3: Invalid brand_track
        bad_manifest_3 = dict(self.sample_pack)
        bad_manifest_3["brand_track"] = "cyber_goth"
        self.assertTrue(any("brand_track" in e.path for e in validator.iter_errors(bad_manifest_3)))

        # Case 4: Invalid hex color
        bad_manifest_4 = dict(self.sample_pack)
        bad_manifest_4["ui_theme"] = dict(self.sample_pack.get("ui_theme", {}))
        bad_manifest_4["ui_theme"]["bg_color"] = "invalid_color"
        self.assertTrue(any("bg_color" in e.path for e in validator.iter_errors(bad_manifest_4)))

        # Case 5: Sound volume out of range (>1.0)
        bad_manifest_5 = dict(self.sample_pack)
        bad_manifest_5["ui_theme"] = dict(self.sample_pack.get("ui_theme", {}))
        bad_manifest_5["ui_theme"]["sound_volume"] = 2.5
        self.assertTrue(any("sound_volume" in e.path for e in validator.iter_errors(bad_manifest_5)))

    def test_personas_depth_and_non_technical_presence(self):
        """Verify positioning matrix defines at least 3 personas including non-technical users."""
        doc = (STRATEGY_DIR / "02_brand_positioning" / "positioning_matrix.md").read_text(encoding="utf-8")

        # Find persona headers (### 2.x Persona ...)
        persona_headers = re.findall(r"^###\s+2\.\d+\s+Persona\s+\d+.*", doc, re.MULTILINE)
        self.assertGreaterEqual(
            len(persona_headers),
            3,
            f"Expected at least 3 personas, found {len(persona_headers)}",
        )

        # Check for non-technical casual user persona presence
        non_tech_match = re.search(
            r"non-technical\s+(?:casual\s+)?(?:computer\s+)?user|Doomscrolling Student|casual computer user",
            doc,
            re.IGNORECASE,
        )
        self.assertIsNotNone(non_tech_match, "No explicit non-technical casual computer user persona found.")

        # Ensure all personas contain pains, triggers, and value propositions
        self.assertGreaterEqual(len(re.findall(r"Primary Pains", doc, re.IGNORECASE)), 3)
        self.assertGreaterEqual(len(re.findall(r"Emotional Triggers", doc, re.IGNORECASE)), 3)
        self.assertGreaterEqual(len(re.findall(r"Tailored Value Proposition", doc, re.IGNORECASE)), 3)

    def test_dual_track_branding_specifications(self):
        """Verify dual-track branding guidelines: names, taglines, color palettes, and tones."""
        doc = (STRATEGY_DIR / "02_brand_positioning" / "dual_track_branding_guide.md").read_text(encoding="utf-8")

        # Track A Validation
        self.assertIn("Becoming a Bihari", doc)
        self.assertTrue(
            re.search(r"The Savage Mindfulness Mirror|The savage mirror for your screen time", doc),
            "Track A tagline missing or inaccurate",
        )
        self.assertIn("#FF8C00", doc, "Electric Amber hex code #FF8C00 missing")
        self.assertIn("#121212", doc, "Obsidian hex code #121212 missing")
        self.assertTrue(re.search(r"Jester|Rebel|unvarnished|comedic|roasting", doc, re.IGNORECASE))

        # Track B Validation
        self.assertIn("Vihara", doc)
        self.assertTrue(
            re.search(r"The Mindful Focus Catalyst|A gentle mirror for the wandering mind", doc),
            "Track B tagline missing or inaccurate",
        )
        self.assertIn("#0B1B2B", doc, "Prussian Blue / Slate hex code #0B1B2B missing")
        self.assertIn("#162638", doc, "Frosted Mica hex code #162638 missing")
        self.assertTrue(re.search(r"Sage|Catalyst|stoic|dignified|restorative", doc, re.IGNORECASE))

    def test_pricing_tier_matrix_exact_points(self):
        """Verify pricing tier matrix contains exact price points ($9/mo, $79/yr, $149, $15/seat/mo)."""
        doc = (STRATEGY_DIR / "03_commercial_strategy" / "commercial_strategy.md").read_text(encoding="utf-8")

        # Free tier
        self.assertTrue(re.search(r"\$0\b|Forever Free", doc))

        # Pro tier: $9/mo, $79/yr, $149 lifetime
        self.assertTrue(re.search(r"\$9(?:\.00)?\s*/\s*mo(?:nth)?", doc), "Pro monthly price ($9/mo) missing")
        self.assertTrue(re.search(r"\$79(?:\.00)?\s*/\s*y(?:ea)?r", doc), "Pro annual price ($79/yr) missing")
        self.assertTrue(re.search(r"\$149(?:\.00)?\s*(?:Lifetime|lifetime)", doc), "Pro lifetime price ($149) missing")

        # Creator packs: $1.99 - $4.99 and 70/30 split
        self.assertTrue(re.search(r"\$1\.99\s*(?:to|-)\s*\$4\.99", doc), "Creator pack price range ($1.99-$4.99) missing")
        self.assertIn("70/30", doc, "Creator 70/30 revenue split missing")

        # Team tier: $15/seat/mo
        self.assertTrue(re.search(r"\$15(?:\.00)?\s*/\s*(?:seat|user)\s*/\s*mo(?:nth)?", doc), "Team price ($15/seat/mo) missing")

        # Unit economics: hosting $0.010, gross margin >90%, breakeven 568
        self.assertIn("$0.010", doc, "Hosting cost $0.010/user/mo missing")
        self.assertTrue(re.search(r"93%|96\.5%|>90%", doc), "Gross margin calculation missing")
        self.assertIn("568", doc, "Breakeven 568 subscribers missing")

    def test_viral_video_playbook_has_5_complete_scripts(self):
        """Verify viral video playbook contains at least 5 complete scripts with all required components."""
        doc = (STRATEGY_DIR / "04_gtm_launch_playbook" / "viral_video_playbook.md").read_text(encoding="utf-8")

        script_headers = re.findall(r"^###\s+Script\s+\d+:.*", doc, re.MULTILINE)
        self.assertGreaterEqual(len(script_headers), 5, f"Expected at least 5 scripts, found {len(script_headers)}")

        scripts = re.split(r"###\s+Script\s+\d+:", doc)[1:6]
        for i, script_content in enumerate(scripts, 1):
            self.assertIn("Concept Title", script_content, f"Script {i} missing Concept Title")
            self.assertIn("Target Persona", script_content, f"Script {i} missing Target Persona")
            self.assertIn("Target Brand Track", script_content, f"Script {i} missing Target Brand Track")
            self.assertIn("Runtime", script_content, f"Script {i} missing Runtime")
            self.assertIn("Audio & Sound Design", script_content, f"Script {i} missing Audio & Sound Design")
            self.assertTrue(
                "Visual Cue" in script_content or "Camera Framing" in script_content,
                f"Script {i} missing Visual Cues / Camera Framing",
            )
            self.assertTrue(
                "0:00" in script_content or "Hook" in script_content,
                f"Script {i} missing opening 0-3s Hook line",
            )
            self.assertTrue(
                any(cta in script_content.lower() for cta in ["link in bio", "download", "cta", "github"]),
                f"Script {i} missing Call to Action (CTA)",
            )

    def test_post_launch_30day_checklist_continuity_without_gaps(self):
        """Verify 30-day post-launch checklist has day-by-day continuity from Day 1 to Day 30 without gaps."""
        doc = (STRATEGY_DIR / "04_gtm_launch_playbook" / "post_launch_30day_checklist.md").read_text(encoding="utf-8")

        # Extract all days matching "### Day X:"
        found_days = [int(m) for m in re.findall(r"^###\s+Day\s+(\d+):", doc, re.MULTILINE)]
        expected_days = list(range(1, 31))

        self.assertEqual(
            found_days,
            expected_days,
            f"Checklist day continuity broken! Found: {found_days}, Expected: 1..30",
        )

        # Verify all 4 phases are defined
        self.assertIn("Phase 1: Launch Spike", doc)
        self.assertIn("Phase 2: Community & Creator Flywheel", doc)
        self.assertIn("Phase 3: Pack Drops & Retention", doc)
        self.assertIn("Phase 4: Pro Conversion Optimization", doc)


class TestTier3CrossReferenceAndContractConsistency(unittest.TestCase):
    """Tier 3: Verifies cross-document contractual consistency and offer alignment."""

    def test_pricing_consistency_across_ph_faq_and_checklist(self):
        """Verify pricing cited in Product Hunt FAQ and 30-day checklist matches commercial strategy."""
        comm_doc = (STRATEGY_DIR / "03_commercial_strategy" / "commercial_strategy.md").read_text(encoding="utf-8")
        ph_doc = (STRATEGY_DIR / "04_gtm_launch_playbook" / "product_hunt_launch_kit.md").read_text(encoding="utf-8")
        check_doc = (STRATEGY_DIR / "04_gtm_launch_playbook" / "post_launch_30day_checklist.md").read_text(encoding="utf-8")

        # Core price points
        price_points = ["$9", "$79", "$149", "$15"]

        for price in price_points:
            self.assertIn(price, comm_doc, f"Price {price} missing from commercial strategy")
            self.assertIn(price, ph_doc, f"Price {price} missing from Product Hunt Launch Kit FAQ")
            self.assertIn(price, check_doc, f"Price {price} missing from 30-Day Checklist")

    def test_dual_track_naming_consistency_in_video_playbook(self):
        """Verify dual-track naming in video playbook matches branding guide."""
        brand_doc = (STRATEGY_DIR / "02_brand_positioning" / "dual_track_branding_guide.md").read_text(encoding="utf-8")
        video_doc = (STRATEGY_DIR / "04_gtm_launch_playbook" / "viral_video_playbook.md").read_text(encoding="utf-8")

        # Both documents must cite identical brand tracks
        brand_terms = [
            "Becoming a Bihari",
            "Vihara",
            "The Savage Mindfulness Mirror",
            "The Mindful Focus Catalyst",
        ]
        for term in brand_terms:
            self.assertIn(term, brand_doc, f"Term '{term}' missing from branding guide")
            self.assertIn(term, video_doc, f"Term '{term}' missing from viral video playbook")

    def test_pack_manifest_brand_track_contract(self):
        """Verify pack manifest schema brand_track property strictly matches M2 dual-track strategy."""
        schema_path = STRATEGY_DIR / "01_technical_packaging" / "meme_pack_schema.json"
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)

        brand_track_enum = schema["properties"]["brand_track"]["enum"]
        self.assertEqual(
            set(brand_track_enum),
            {"consumer", "professional", "universal", "vihara", "bihari"},
            f"Unexpected brand_track enum values: {brand_track_enum}",
        )

        sample_pack_path = STRATEGY_DIR / "01_technical_packaging" / "sample_pack" / "pack.json"
        with open(sample_pack_path, "r", encoding="utf-8") as f:
            sample_pack = json.load(f)

        self.assertIn(
            sample_pack["brand_track"],
            brand_track_enum,
            f"Sample pack brand_track '{sample_pack['brand_track']}' not in schema enum",
        )

    def test_tier_gating_contract_alignment(self):
        """Verify tier gating definitions in pack schema and commercial strategy align."""
        comm_doc = (STRATEGY_DIR / "03_commercial_strategy" / "commercial_strategy.md").read_text(encoding="utf-8")
        schema_path = STRATEGY_DIR / "01_technical_packaging" / "meme_pack_schema.json"
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)

        # 1. Verify schema defines tier_requirement matching commercial tiers
        tier_enum = schema["properties"]["tier_requirement"]["enum"]
        self.assertEqual(
            set(tier_enum),
            {"free", "pro", "team"},
            f"tier_requirement enum in schema {tier_enum} does not match ['free', 'pro', 'team']",
        )

        # 2. Verify commercial strategy defines the feature flags governing these tiers
        gated_flags = ["custom_packs", "cloud_sync", "analytics_export", "team_index"]
        for flag in gated_flags:
            self.assertIn(flag, comm_doc, f"Feature flag '{flag}' missing from commercial strategy")


if __name__ == "__main__":
    unittest.main()
