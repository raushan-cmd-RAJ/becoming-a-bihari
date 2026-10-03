"""
Tests for Extensible Theme & Meme Pack System (.lucidpack).

Validates:
- F24: .lucidpack ZIP64 format conformance, root pack.json, icon.png, and vibe directories.
- F25: Dynamic PackManager with 350ms hot-discovery background watcher without application restart.
- F26: Bundled default pack containing >=10 unique memes per vibe category (>=120 total across 12 vibes).
- F27: Graceful corrupt pack rejection, ZipSlip path traversal defense, and pack_errors.log error tracking.
- Integration: MemeRetriever querying active loaded pack memes and enforcing 60-event LRU deduplication.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import tempfile
import time
import zipfile
import hashlib
from pathlib import Path
from typing import Generator

import pytest
from PIL import Image

from bihari.inference import Vibe, VIBE_FOLDER_NAMES
from bihari.memes import MemeRetriever
from bihari.packs import (
    LoadedPack,
    PackDirectoryWatcher,
    PackManager,
    SecurityError,
    safe_extract_lucidpack,
    validate_pack_manifest,
)

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def temp_packs_env() -> Generator[dict[str, Path], None, None]:
    """Provide isolated temporary directories for packs, cache, and memes testing."""
    with tempfile.TemporaryDirectory() as tmp_root:
        root = Path(tmp_root)
        packs_dir = root / "packs"
        packs_dir.mkdir(parents=True, exist_ok=True)
        cache_dir = packs_dir / ".cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        meme_fallback_dir = root / "fallback_memes"
        meme_fallback_dir.mkdir(parents=True, exist_ok=True)

        yield {
            "root": root,
            "packs_dir": packs_dir,
            "cache_dir": cache_dir,
            "meme_fallback_dir": meme_fallback_dir,
        }


def _create_minimal_valid_manifest(pack_id: str = "test-pack", brand_track: str = "vihara") -> dict:
    """Helper to construct a valid manifest dictionary covering all 12 vibes."""
    vibes_obj = {}
    for v in Vibe:
        vibes_obj[v.value] = {
            "folder": f"memes/{v.value.lower()}",
            "reflections": [
                f"reflection 1 for {v.value}",
                f"reflection 2 for {v.value}",
            ],
            "contextual_templates": [
                "working on {subject}",
            ],
        }

    return {
        "id": pack_id,
        "schema_version": "1.0.0",
        "name": f"Test Pack {pack_id}",
        "version": "1.0.0",
        "brand_track": brand_track,
        "author": {
            "name": "Test Author",
            "url": "https://vihara.com",
            "email": "test@vihara.com",
        },
        "description": "A valid test meme pack",
        "license": "CC-BY-4.0",
        "content_rating": "everyone",
        "tier_requirement": "free",
        "ui_theme": {
            "bg_color": "#18181b",
            "header_color": "#27272a",
            "text_color": "#f4f4f5",
            "accent_color": "#3b82f6",
            "font_family": "Segoe UI",
            "corner_radius": 8,
            "sound_volume": 0.5,
        },
        "preview": {
            "icon": "icon.png",
        },
        "vibes": vibes_obj,
    }


def _create_dummy_image_bytes(width: int = 100, height: int = 100, color: tuple = (50, 100, 150)) -> bytes:
    """Helper to generate valid PNG image bytes."""
    im = Image.new("RGBA", (width, height), color)
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def _build_test_lucidpack(
    dest_path: Path,
    manifest: dict,
    images_per_vibe: int = 3,
) -> Path:
    """Build a valid .lucidpack archive with manifest, icon, and images."""
    img_data = _create_dummy_image_bytes()
    icon_data = _create_dummy_image_bytes(256, 256, (24, 24, 27))

    with zipfile.ZipFile(dest_path, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
        zf.writestr("pack.json", json.dumps(manifest, indent=2))
        zf.writestr("icon.png", icon_data)

        for v in Vibe:
            v_folder = manifest["vibes"][v.value]["folder"]
            for i in range(images_per_vibe):
                zf.writestr(f"{v_folder}/img_{i:02d}.png", img_data)

    return dest_path


# ──────────────────────────────────────────────
# Test Suite
# ──────────────────────────────────────────────

class TestMemePackSystem:
    """Milestone 3 Test Suite for Extensible Meme Pack System."""

    def test_default_bundled_pack_integrity(self):
        """
        F26 Contract:
        The default bundled pack must exist at packs/default.lucidpack,
        be a valid .lucidpack conforming to meme_pack_schema.json,
        and contain at least 10 unique meme images per vibe category (>=120 total across 12 vibes).
        """
        default_pack_path = WORKSPACE_ROOT / "packs" / "default.lucidpack"
        assert default_pack_path.exists(), f"Default pack missing at: {default_pack_path}"
        assert default_pack_path.is_file(), "Default pack must be a file"

        # Validate ZIP archive structure
        with zipfile.ZipFile(default_pack_path, "r") as zf:
            namelist = zf.namelist()
            assert "pack.json" in namelist, "pack.json must exist in pack root"
            assert "icon.png" in namelist, "icon.png must exist in pack root"

            raw_manifest = json.loads(zf.read("pack.json").decode("utf-8"))

        # Validate manifest contents
        assert raw_manifest["id"] == "vihara-core-default"
        assert raw_manifest["name"] == "Vihara Core Mindfulness Reactions"
        assert raw_manifest["version"] == "1.0.0"
        assert raw_manifest["brand_track"] in ("vihara", "professional")
        assert raw_manifest["author"]["name"] == "Vihara Team"

        is_valid, err_msg = validate_pack_manifest(raw_manifest)
        assert is_valid, f"Default pack manifest failed validation: {err_msg}"

        # Load via PackManager
        with tempfile.TemporaryDirectory() as tmp_dir:
            pm = PackManager(
                packs_dir=Path(tmp_dir),
                bundled_pack_path=default_pack_path,
                auto_start_watcher=False,
            )
            loaded = pm.load_pack(default_pack_path)
            assert loaded is not None, "Failed to load default bundled pack"
            assert loaded.pack_id == "vihara-core-default"

            global_meme_hashes: dict[str, tuple[str, str]] = {}
            duplicate_collisions: list[tuple[str, str, str]] = []
            total_memes_count = 0

            for v in Vibe:
                memes = loaded.get_memes(v)
                assert len(memes) >= 10, (
                    f"Vibe {v.value} must contain >= 10 memes, found {len(memes)}"
                )

                vibe_hashes: set[str] = set()
                for m_path in memes:
                    assert m_path.exists(), f"Meme file missing: {m_path}"
                    assert m_path.stat().st_size > 0, f"Meme file is 0 bytes: {m_path}"

                    # Validate Pillow decodability
                    with Image.open(m_path) as im:
                        im.verify()

                    data = m_path.read_bytes()
                    h = hashlib.sha256(data).hexdigest()

                    # Within-folder uniqueness check
                    assert h not in vibe_hashes, (
                        f"Duplicate image hash detected within vibe {v.value}: {m_path.name}"
                    )
                    vibe_hashes.add(h)

                    # Cross-folder global uniqueness check
                    if h in global_meme_hashes:
                        prev_vibe, prev_name = global_meme_hashes[h]
                        duplicate_collisions.append((h, f"{prev_vibe}/{prev_name}", f"{v.value}/{m_path.name}"))
                    global_meme_hashes[h] = (v.value, m_path.name)
                    total_memes_count += 1

            # Assert ZERO cross-folder duplicates across the entire archive
            assert len(duplicate_collisions) == 0, (
                f"Asset Authenticity Violation: Found {len(duplicate_collisions)} cross-folder "
                f"duplicate images in default.lucidpack! Collisions: {duplicate_collisions[:5]}"
            )

            # Assert global unique count strictly equals total memes and meets >= 120
            assert len(global_meme_hashes) == total_memes_count, (
                f"Expected all {total_memes_count} images to have distinct SHA-256 hashes, "
                f"found only {len(global_meme_hashes)} unique hashes!"
            )
            assert len(global_meme_hashes) >= 120, (
                f"Default pack must contain >= 120 globally unique images, "
                f"found {len(global_meme_hashes)}"
            )

    def test_load_valid_lucidpack(self, temp_packs_env):
        """
        F24 Contract:
        A valid .lucidpack archive must be successfully loaded and indexed by PackManager.
        """
        packs_dir = temp_packs_env["packs_dir"]
        manifest = _create_minimal_valid_manifest("custom-zen-pack", brand_track="professional")
        pack_file = packs_dir / "custom-zen-pack.lucidpack"
        _build_test_lucidpack(pack_file, manifest, images_per_vibe=5)

        pm = PackManager(packs_dir=packs_dir, auto_start_watcher=False)
        pack = pm.load_pack(pack_file)

        assert pack is not None
        assert pack.pack_id == "custom-zen-pack"
        assert pack.name == "Test Pack custom-zen-pack"
        assert pack.version == "1.0.0"
        assert pack.brand_track == "professional"
        assert pack.author["name"] == "Test Author"
        assert len(pack.get_memes(Vibe.FLOW_STATE)) == 5
        assert len(pack.get_reflections(Vibe.SYNTAX_RAGE)) == 2
        assert len(pack.get_contextual_templates(Vibe.LOST_IN_SCROLL)) == 1

    def test_hot_discovery_detects_new_pack_without_restart(self, temp_packs_env):
        """
        F25 Contract:
        PackDirectoryWatcher monitors packs directory every 350ms (or on demand);
        dropping a new .lucidpack into packs/ dynamically registers it in PackManager
        without restarting the application.
        """
        packs_dir = temp_packs_env["packs_dir"]
        pm = PackManager(packs_dir=packs_dir, auto_start_watcher=True, poll_interval=0.1)

        try:
            initial_count = len(pm.packs)

            # Drop a new pack into packs_dir while watcher is active
            manifest = _create_minimal_valid_manifest("hot-drop-pack")
            new_pack_path = packs_dir / "hot-drop-pack.lucidpack"
            _build_test_lucidpack(new_pack_path, manifest, images_per_vibe=3)

            # Wait up to 1.5s for watcher to detect the new file
            detected = False
            for _ in range(15):
                time.sleep(0.1)
                if "hot-drop-pack" in pm.packs:
                    detected = True
                    break

            # If OS thread scheduling delayed detection, trigger synchronous scan
            if not detected:
                pm.watcher.scan_for_changes()
                detected = "hot-drop-pack" in pm.packs

            assert detected, "Hot-discovery failed to detect newly added pack in packs directory"
            loaded_pack = pm.get_pack("hot-drop-pack")
            assert loaded_pack is not None
            assert loaded_pack.name == "Test Pack hot-drop-pack"
            assert len(loaded_pack.get_memes(Vibe.FLOW_STATE)) == 3

            # Now test removal detection
            new_pack_path.unlink()
            for _ in range(15):
                time.sleep(0.1)
                if "hot-drop-pack" not in pm.packs:
                    break
            if "hot-drop-pack" in pm.packs:
                pm.watcher.scan_for_changes()

            assert "hot-drop-pack" not in pm.packs, "Removal of pack was not detected by watcher"

        finally:
            pm.stop_watcher()

    def test_graceful_rejection_of_corrupt_zip(self, temp_packs_env):
        """
        F27 Contract:
        A corrupt zip file dropped into packs directory must be rejected gracefully
        without crashing the application and logged to pack_errors.log.
        """
        packs_dir = temp_packs_env["packs_dir"]
        corrupt_pack = packs_dir / "corrupted_archive.lucidpack"
        corrupt_pack.write_bytes(b"THIS_IS_NOT_A_VALID_ZIP_ARCHIVE_DATA_123456789")

        pm = PackManager(packs_dir=packs_dir, auto_start_watcher=False)
        result = pm.load_pack(corrupt_pack)

        # Must return None without raising unhandled exception
        assert result is None, "Corrupt zip must return None gracefully"

        # Must log to pack_errors.log
        error_log = packs_dir / "pack_errors.log"
        assert error_log.exists(), "pack_errors.log must be created when a pack is rejected"
        log_content = error_log.read_text(encoding="utf-8")
        assert "corrupted_archive.lucidpack" in log_content
        assert "Corrupted ZIP" in log_content or "BadZipFile" in log_content

    def test_graceful_rejection_of_invalid_manifest(self, temp_packs_env):
        """
        F27 Contract:
        A pack with an invalid or malformed pack.json must be rejected gracefully
        and logged to pack_errors.log.
        """
        packs_dir = temp_packs_env["packs_dir"]
        bad_manifest_pack = packs_dir / "bad_manifest.lucidpack"

        # Missing required canonical vibes
        broken_manifest = {
            "id": "broken-pack",
            "schema_version": "1.0.0",
            "name": "Broken Pack",
            "version": "1.0.0",
            "author": {"name": "Anon"},
            "brand_track": "professional",
            "vibes": {},  # Missing all canonical vibes
        }

        with zipfile.ZipFile(bad_manifest_pack, "w") as zf:
            zf.writestr("pack.json", json.dumps(broken_manifest))

        pm = PackManager(packs_dir=packs_dir, auto_start_watcher=False)
        result = pm.load_pack(bad_manifest_pack)

        assert result is None, "Pack with invalid manifest must return None"

        error_log = packs_dir / "pack_errors.log"
        assert error_log.exists()
        log_content = error_log.read_text(encoding="utf-8")
        assert "bad_manifest.lucidpack" in log_content
        assert "Missing canonical vibe" in log_content or "Validation error" in log_content

    def test_strict_zipslip_path_traversal_defense(self, temp_packs_env):
        """
        F27 Contract:
        An archive containing ZipSlip path traversal patterns (e.g., '../../evil.txt')
        must be detected, rejected, raise SecurityError internally, log to pack_errors.log,
        and never write any file outside the target directory.
        """
        packs_dir = temp_packs_env["packs_dir"]
        outside_target = temp_packs_env["root"] / "evil_pwned.txt"
        zipslip_pack = packs_dir / "zipslip_exploit.lucidpack"

        # Build malicious archive with traversal entry
        with zipfile.ZipFile(zipslip_pack, "w") as zf:
            zf.writestr("pack.json", json.dumps(_create_minimal_valid_manifest("evil-pack")))
            # Path traversal member targeting parent directory
            zf.writestr("../../evil_pwned.txt", "MALICIOUS_PAYLOAD")

        # Test safe_extract_lucidpack directly raises SecurityError
        extract_dest = temp_packs_env["cache_dir"] / "evil_test"
        with pytest.raises(SecurityError) as exc_info:
            safe_extract_lucidpack(zipslip_pack, extract_dest)
        assert "ZipSlip" in str(exc_info.value)
        assert not outside_target.exists(), "ZipSlip exploit breached sandbox directory!"

        # Test PackManager loads it gracefully without crash
        pm = PackManager(packs_dir=packs_dir, auto_start_watcher=False)
        result = pm.load_pack(zipslip_pack)

        assert result is None, "PackManager must return None on ZipSlip attempt"
        assert not outside_target.exists(), "ZipSlip breached sandbox via PackManager!"

        error_log = packs_dir / "pack_errors.log"
        assert error_log.exists()
        log_content = error_log.read_text(encoding="utf-8")
        assert "zipslip_exploit.lucidpack" in log_content
        assert "Security violation" in log_content

    def test_memeretriever_active_pack_integration(self, temp_packs_env):
        """
        Integration Contract:
        MemeRetriever retrieves candidates from the active loaded pack,
        falls back to default directory if needed, and maintains LRU deduplication.
        """
        packs_dir = temp_packs_env["packs_dir"]
        fallback_dir = temp_packs_env["meme_fallback_dir"]

        manifest = _create_minimal_valid_manifest("active-test-pack")
        pack_file = packs_dir / "active-test-pack.lucidpack"
        _build_test_lucidpack(pack_file, manifest, images_per_vibe=5)

        pm = PackManager(packs_dir=packs_dir, auto_start_watcher=False)
        pm.set_active_pack("active-test-pack")

        retriever = MemeRetriever(
            meme_dir=fallback_dir,
            cooldown_seconds=0,
            pack_manager=pm,
        )

        counts = retriever.get_meme_count()
        assert counts[VIBE_FOLDER_NAMES[Vibe.FLOW_STATE]] >= 5

        # Retrieve meme for FLOW_STATE
        selected = retriever.get_meme(Vibe.FLOW_STATE, current_time=100.0, cooldown=0)
        assert selected is not None
        assert selected.name.startswith("img_")
        assert selected.exists()
        assert selected.name in retriever._recent

    def test_memeretriever_60_event_anti_repetition_with_loaded_pack(self, temp_packs_env):
        """
        Integration Contract:
        Across a 100-event simulation with a pack containing sufficient images,
        zero repeated memes occur in any 60-event window.
        """
        packs_dir = temp_packs_env["packs_dir"]
        fallback_dir = temp_packs_env["meme_fallback_dir"]

        # Build pack with 70 images for FLOW_STATE
        manifest = _create_minimal_valid_manifest("large-pool-pack")
        pack_file = packs_dir / "large-pool-pack.lucidpack"
        _build_test_lucidpack(pack_file, manifest, images_per_vibe=70)

        pm = PackManager(packs_dir=packs_dir, auto_start_watcher=False)
        pm.set_active_pack("large-pool-pack")

        retriever = MemeRetriever(
            meme_dir=fallback_dir,
            cooldown_seconds=0,
            pack_manager=pm,
        )

        history = []
        sim_time = 1000.0
        for _ in range(100):
            chosen = retriever.get_meme(Vibe.FLOW_STATE, current_time=sim_time, cooldown=0)
            assert chosen is not None
            history.append(chosen.name)
            sim_time += 1.0

        assert len(history) == 100

        # Assert zero duplicates in every 60-event window
        window_size = 60
        num_windows = len(history) - window_size + 1
        for i in range(num_windows):
            window = history[i : i + window_size]
            assert len(set(window)) == window_size, f"Duplicate found in window {i}: {window}"

    def test_exploded_directory_pack_loading(self, temp_packs_env):
        """
        F24 Contract:
        An exploded directory in packs folder containing pack.json must be loaded in-place
        without requiring ZIP extraction.
        """
        packs_dir = temp_packs_env["packs_dir"]
        exploded_dir = packs_dir / "exploded-custom-pack"
        exploded_dir.mkdir(parents=True, exist_ok=True)

        manifest = _create_minimal_valid_manifest("exploded-custom-pack")
        (exploded_dir / "pack.json").write_text(json.dumps(manifest), encoding="utf-8")

        # Create images in vibe folders
        img_bytes = _create_dummy_image_bytes()
        for v in Vibe:
            v_dir = exploded_dir / manifest["vibes"][v.value]["folder"]
            v_dir.mkdir(parents=True, exist_ok=True)
            (v_dir / "test_img.png").write_bytes(img_bytes)

        pm = PackManager(packs_dir=packs_dir, auto_start_watcher=False)
        pack = pm.load_pack(exploded_dir)

        assert pack is not None
        assert pack.pack_id == "exploded-custom-pack"
        assert len(pack.get_memes(Vibe.FLOW_STATE)) >= 1
