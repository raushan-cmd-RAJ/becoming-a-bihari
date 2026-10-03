"""
Empirical Adversarial Test Harness for Meme Pack Schema and Sample Pack.

Tests boundary conditions, adversarial mutations, corrupt asset mappings,
and strict rejection of non-conforming manifests.
"""

import copy
import json
import unittest
from pathlib import Path
from jsonschema import Draft7Validator

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
STRATEGY_DIR = REPO_ROOT / "product_strategy"
SCHEMA_PATH = STRATEGY_DIR / "01_technical_packaging" / "meme_pack_schema.json"
SAMPLE_PACK_PATH = STRATEGY_DIR / "01_technical_packaging" / "sample_pack" / "pack.json"


class TestAdversarialSchemaEmpirical(unittest.TestCase):
    """Deep adversarial boundary validation for Draft-07 JSON Schema."""

    @classmethod
    def setUpClass(cls):
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            cls.schema = json.load(f)
        with open(SAMPLE_PACK_PATH, "r", encoding="utf-8") as f:
            cls.valid_pack = json.load(f)
        cls.validator = Draft7Validator(cls.schema)

    def assert_rejected(self, manifest, context=""):
        """Helper to assert that manifest produces at least one schema validation error."""
        errors = list(self.validator.iter_errors(manifest))
        self.assertGreater(
            len(errors),
            0,
            f"Expected schema validation failure for [{context}], but manifest was accepted!",
        )

    def assert_accepted(self, manifest, context=""):
        """Helper to assert that manifest passes validation cleanly."""
        errors = list(self.validator.iter_errors(manifest))
        err_msgs = [f"[{' -> '.join(str(p) for p in e.path)}]: {e.message}" for e in errors]
        self.assertEqual(
            len(errors),
            0,
            f"Expected clean validation for [{context}], but got errors: {err_msgs}",
        )

    # ---------------------------------------------------------
    # Baseline Validity
    # ---------------------------------------------------------
    def test_00_baseline_sample_pack_validity(self):
        """Verify the unmutated sample_pack/pack.json passes validation cleanly."""
        self.assert_accepted(self.valid_pack, "Canonical baseline sample pack")

    # ---------------------------------------------------------
    # 1. ID Field Boundary & Pattern Tests
    # ---------------------------------------------------------
    def test_01_id_missing(self):
        """Schema must reject manifest without 'id'."""
        m = copy.deepcopy(self.valid_pack)
        del m["id"]
        self.assert_rejected(m, "Missing mandatory field 'id'")

    def test_02_id_invalid_patterns(self):
        """Schema must reject IDs with uppercase, spaces, invalid chars, or bad starts."""
        invalid_ids = [
            "",                        # Empty string
            "a",                       # Single character (regex requires at least 2 chars)
            "UPPERCASE_ID",            # Uppercase not allowed
            "com.lucid.Pack",          # CamelCase / uppercase
            "has space",               # Spaces forbidden
            "-leading-dash",           # Must start with [a-z0-9]
            ".leading-dot",            # Must start with [a-z0-9]
            "_leading-underscore",     # Must start with [a-z0-9]
            "id_with_$pecial!",        # Special chars
            "id_with_@sign",           # Special chars
            "id/with/slashes",         # Slashes forbidden
            12345,                     # Integer instead of string
            None,                      # Null
        ]
        for bad_id in invalid_ids:
            m = copy.deepcopy(self.valid_pack)
            m["id"] = bad_id
            self.assert_rejected(m, f"Invalid ID pattern: {bad_id}")

    def test_03_id_valid_patterns(self):
        """Schema must accept conforming kebab-case, snake_case, and reverse-DNS IDs."""
        valid_ids = [
            "com.vihara.sample.mindful-focus",
            "bihari-savage-pack",
            "pack_v1.0",
            "ab",
            "01-test-pack",
            "pack.123_456-789",
        ]
        for good_id in valid_ids:
            m = copy.deepcopy(self.valid_pack)
            m["id"] = good_id
            self.assert_accepted(m, f"Valid ID pattern: {good_id}")

    # ---------------------------------------------------------
    # 2. Missing Mandatory Fields Tests
    # ---------------------------------------------------------
    def test_04_missing_root_mandatory_fields(self):
        """Schema must reject manifests missing any required root field."""
        required_fields = ["id", "schema_version", "name", "version", "author", "brand_track", "vibes"]
        for field in required_fields:
            m = copy.deepcopy(self.valid_pack)
            del m[field]
            self.assert_rejected(m, f"Missing required root field '{field}'")

    def test_05_missing_author_name(self):
        """Schema must reject author object missing 'name'."""
        m = copy.deepcopy(self.valid_pack)
        del m["author"]["name"]
        self.assert_rejected(m, "Missing author.name")

    def test_06_missing_each_canonical_vibe(self):
        """Schema must reject manifest if any of the 12 canonical vibes is omitted."""
        canonical_12 = [
            "FLOW_STATE", "GRINDING", "BURNOUT_APPROACHING", "SYNTAX_RAGE",
            "HELP_SEEKING", "MOUNTING_FRICTION", "WANDERING", "LOST_IN_SCROLL",
            "TAB_BUTTERFLY", "STILLNESS", "MEETING_RECOVERY", "AFTERNOON_DRIFT"
        ]
        for vibe in canonical_12:
            m = copy.deepcopy(self.valid_pack)
            del m["vibes"][vibe]
            self.assert_rejected(m, f"Missing canonical vibe '{vibe}'")

    def test_07_missing_vibe_folder_or_reflections(self):
        """Schema must reject vibe entries missing 'folder' or 'reflections'."""
        m1 = copy.deepcopy(self.valid_pack)
        del m1["vibes"]["FLOW_STATE"]["folder"]
        self.assert_rejected(m1, "Missing vibe folder")

        m2 = copy.deepcopy(self.valid_pack)
        del m2["vibes"]["FLOW_STATE"]["reflections"]
        self.assert_rejected(m2, "Missing vibe reflections")

    def test_08_empty_reflections_array(self):
        """Schema must reject vibe with empty reflections array (minItems: 1)."""
        m = copy.deepcopy(self.valid_pack)
        m["vibes"]["FLOW_STATE"]["reflections"] = []
        self.assert_rejected(m, "Empty reflections array")

    # ---------------------------------------------------------
    # 3. Non-Semantic Version Strings Tests
    # ---------------------------------------------------------
    def test_09_non_semantic_version_strings(self):
        """Schema must strictly reject non-semantic version strings."""
        invalid_versions = [
            "1.0",           # Missing patch component
            "v1.0.0",        # Leading 'v'
            "1.0.0-beta",    # Pre-release tag (pattern requires strict digits)
            "1.0.0.0",       # Four components
            "alpha",         # Pure string
            "1.0.0b",        # Appended letter
            "1..0",          # Empty component
            "",              # Empty string
            " 1.0.0",        # Leading whitespace
            "1.0.0 ",        # Trailing whitespace
            1.0,             # Float type
        ]
        for bad_ver in invalid_versions:
            m = copy.deepcopy(self.valid_pack)
            m["version"] = bad_ver
            self.assert_rejected(m, f"Invalid semantic version: {bad_ver}")

    def test_10_valid_semantic_version_strings(self):
        """Schema must accept valid MAJOR.MINOR.PATCH digits."""
        valid_versions = ["0.0.1", "1.0.0", "2.14.300", "10.200.3000"]
        for good_ver in valid_versions:
            m = copy.deepcopy(self.valid_pack)
            m["version"] = good_ver
            self.assert_accepted(m, f"Valid semantic version: {good_ver}")

    # ---------------------------------------------------------
    # 4. Unknown Vibes Tests
    # ---------------------------------------------------------
    def test_11_unknown_vibe_injected(self):
        """Schema must reject unrecognized vibes in 'vibes' (additionalProperties: false)."""
        unknown_vibes = ["COFFEE_BREAK", "PROCRASTINATION", "DEATH_MARCH", "RANDOM_VIBE"]
        for bad_vibe in unknown_vibes:
            m = copy.deepcopy(self.valid_pack)
            m["vibes"][bad_vibe] = {
                "folder": f"memes/{bad_vibe.lower()}",
                "reflections": ["an unauthorized test reflection"]
            }
            self.assert_rejected(m, f"Injected unknown vibe: {bad_vibe}")

    # ---------------------------------------------------------
    # 5. Out-of-Bounds Sound Volume Float Tests
    # ---------------------------------------------------------
    def test_12_sound_volume_out_of_bounds(self):
        """Schema must reject sound_volume outside [0.0, 1.0] range or wrong type."""
        invalid_volumes = [-0.01, -1.0, 1.01, 2.5, 100.0, "0.5", None]
        for bad_vol in invalid_volumes:
            m = copy.deepcopy(self.valid_pack)
            m["ui_theme"]["sound_volume"] = bad_vol
            self.assert_rejected(m, f"Out-of-bounds sound_volume: {bad_vol}")

    def test_13_sound_volume_boundaries(self):
        """Schema must accept sound_volume at boundary values 0.0, 1.0, and intermediate floats."""
        for good_vol in [0.0, 0.001, 0.5, 0.999, 1.0]:
            m = copy.deepcopy(self.valid_pack)
            m["ui_theme"]["sound_volume"] = good_vol
            self.assert_accepted(m, f"Valid sound_volume boundary: {good_vol}")

    # ---------------------------------------------------------
    # 6. Invalid Hex Colors Tests
    # ---------------------------------------------------------
    def test_14_invalid_hex_colors(self):
        """Schema must reject malformed hex colors in ui_theme."""
        color_fields = ["bg_color", "header_color", "text_color", "accent_color"]
        invalid_colors = [
            "red",          # Named color
            "#fff",         # 3-digit shorthand
            "#12345",       # 5-digit hex
            "#1234567",     # 7-digit hex
            "#GGGGGG",      # Non-hex characters
            "18181b",       # Missing leading '#'
            "#18181B ",     # Trailing space
            "#18181",       # 5-digit hex
            "",             # Empty string
            123456,         # Integer
        ]
        for field in color_fields:
            for bad_color in invalid_colors:
                m = copy.deepcopy(self.valid_pack)
                m["ui_theme"][field] = bad_color
                self.assert_rejected(m, f"Invalid color '{bad_color}' for field '{field}'")

    def test_15_valid_hex_colors(self):
        """Schema must accept 6-digit hex colors with uppercase, lowercase, and digits."""
        valid_colors = ["#18181b", "#FFFFFF", "#000000", "#3b82f6", "#FF8C00", "#aAbBcC"]
        for good_color in valid_colors:
            m = copy.deepcopy(self.valid_pack)
            m["ui_theme"]["bg_color"] = good_color
            self.assert_accepted(m, f"Valid hex color: {good_color}")

    # ---------------------------------------------------------
    # 7. Corrupted Asset Mappings & Anti-Tamper Tests
    # ---------------------------------------------------------
    def test_16_corrupted_asset_sha256(self):
        """Schema must reject assets with malformed SHA-256 hashes."""
        invalid_hashes = [
            "short_hash",                                                # Too short
            "8f4e2c91b5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0123456789abcdef01234567",   # 63 chars (1 short)
            "8f4e2c91b5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0123456789abcdef0123456789", # 65 chars (1 long)
            "8f4e2c91b5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0123456789abcdef0123456zz", # Non-hex chars 'zz'
            "",                                                          # Empty
        ]
        for bad_hash in invalid_hashes:
            m = copy.deepcopy(self.valid_pack)
            m["vibes"]["FLOW_STATE"]["assets"] = [
                {"filename": "test.png", "sha256": bad_hash}
            ]
            self.assert_rejected(m, f"Corrupted asset SHA-256: {bad_hash}")

    def test_17_asset_missing_filename(self):
        """Schema must reject asset object missing required 'filename'."""
        m = copy.deepcopy(self.valid_pack)
        m["vibes"]["FLOW_STATE"]["assets"] = [
            {"sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}
        ]
        self.assert_rejected(m, "Asset missing filename")

    def test_18_asset_unexpected_properties(self):
        """Schema must reject asset objects with unrecognized properties (additionalProperties: false)."""
        m = copy.deepcopy(self.valid_pack)
        m["vibes"]["FLOW_STATE"]["assets"] = [
            {
                "filename": "test.png",
                "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "malicious_executable": "/bin/sh"
            }
        ]
        self.assert_rejected(m, "Asset with injected unexpected properties")

    def test_19_root_asset_hashes_validation(self):
        """Schema must reject invalid hash values in root 'asset_hashes'."""
        m = copy.deepcopy(self.valid_pack)
        m["asset_hashes"]["invalid_file.png"] = "not_a_valid_sha256_hash"
        self.assert_rejected(m, "Invalid root asset_hashes value")

    def test_20_contextual_template_missing_placeholder(self):
        """Schema must reject contextual_templates that omit the '{subject}' token."""
        m = copy.deepcopy(self.valid_pack)
        m["vibes"]["FLOW_STATE"]["contextual_templates"] = [
            "This template is missing the required interpolation token."
        ]
        self.assert_rejected(m, "Contextual template missing '{subject}'")

    def test_21_reflection_string_bounds(self):
        """Schema must reject reflections shorter than 3 or longer than 120 chars."""
        # Too short (<3 chars)
        m1 = copy.deepcopy(self.valid_pack)
        m1["vibes"]["FLOW_STATE"]["reflections"] = ["no"]
        self.assert_rejected(m1, "Reflection string too short (2 chars)")

        # Too long (>120 chars)
        m2 = copy.deepcopy(self.valid_pack)
        m2["vibes"]["FLOW_STATE"]["reflections"] = ["A" * 121]
        self.assert_rejected(m2, "Reflection string too long (121 chars)")

        # Valid bounds
        m3 = copy.deepcopy(self.valid_pack)
        m3["vibes"]["FLOW_STATE"]["reflections"] = ["Zen", "B" * 120]
        self.assert_accepted(m3, "Reflection strings at exact boundary lengths 3 and 120")

    def test_22_root_unexpected_properties(self):
        """Schema must reject unexpected root properties (additionalProperties: false)."""
        m = copy.deepcopy(self.valid_pack)
        m["unauthorized_backdoor"] = "malicious_content"
        self.assert_rejected(m, "Injected top-level root property")

    def test_23_brand_track_enum_validation(self):
        """Schema must strictly enforce brand_track enum ('consumer', 'professional', 'universal', 'vihara', 'bihari')."""
        invalid_tracks = ["enterprise", "viral", "custom", "TrackA", "TrackB", ""]
        for bad_track in invalid_tracks:
            m = copy.deepcopy(self.valid_pack)
            m["brand_track"] = bad_track
            self.assert_rejected(m, f"Invalid brand_track: {bad_track}")

        for good_track in ["consumer", "professional", "universal", "vihara", "bihari"]:
            m = copy.deepcopy(self.valid_pack)
            m["brand_track"] = good_track
            self.assert_accepted(m, f"Valid brand_track: {good_track}")


if __name__ == "__main__":
    unittest.main()
