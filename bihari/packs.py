"""
Extensible Theme and Meme Pack System (.lucidpack).

Provides:
- PackManager: Discovers, validates, caches, and serves meme packs.
- PackDirectoryWatcher: Hot-discovery background file watcher (350ms polling).
- Safe extraction with strict ZipSlip path traversal defense.
- Schema validation against Draft-07 meme pack specification.
- Graceful error logging to pack_errors.log without crashing.
"""

from __future__ import annotations

import copy
import datetime
import json
import logging
import os
import shutil
import sys
import threading
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from .inference import Vibe, VIBE_FOLDER_NAMES

logger = logging.getLogger(__name__)

VALID_IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".gif", ".webp"})

# Canonical vibe enum name to standard pack folder mapping
VIBE_TO_PACK_FOLDER: dict[Vibe, str] = {
    Vibe.FLOW_STATE: "memes/flow_state",
    Vibe.GRINDING: "memes/grinding",
    Vibe.BURNOUT_APPROACHING: "memes/burnout_approaching",
    Vibe.SYNTAX_RAGE: "memes/syntax_rage",
    Vibe.HELP_SEEKING: "memes/help_seeking",
    Vibe.MOUNTING_FRICTION: "memes/mounting_friction",
    Vibe.WANDERING: "memes/wandering",
    Vibe.LOST_IN_SCROLL: "memes/lost_in_scroll",
    Vibe.TAB_BUTTERFLY: "memes/tab_butterfly",
    Vibe.STILLNESS: "memes/stillness",
    Vibe.MEETING_RECOVERY: "memes/meeting_recovery",
    Vibe.AFTERNOON_DRIFT: "memes/afternoon_drift",
}


# ──────────────────────────────────────────────
# Pack Exceptions
# ──────────────────────────────────────────────

class PackError(Exception):
    """Base exception for meme pack operations."""
    pass


class SecurityError(PackError):
    """Raised when an archive violates security policies (e.g., ZipSlip path traversal)."""
    pass


class ManifestValidationError(PackError):
    """Raised when pack.json fails validation."""
    pass


class CorruptPackError(PackError):
    """Raised when a pack archive or folder is corrupted."""
    pass


# ──────────────────────────────────────────────
# Safe Extraction & ZipSlip Defense
# ──────────────────────────────────────────────

def safe_extract_lucidpack(zip_path: Path, target_dir: Path) -> Path:
    """
    Safely extract a .lucidpack ZIP archive into target_dir with strict ZipSlip defense.

    Rejects any zip entry with '..' components, absolute paths, or paths that
    resolve outside of target_dir.

    Raises:
        SecurityError: If any path traversal attempt is detected.
        zipfile.BadZipFile: If the archive is corrupt or invalid.
    """
    target_resolved = target_dir.resolve()
    target_resolved.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
        # Pre-validate all members before writing anything to disk
        for member in zf.infolist():
            filename = member.filename

            # Check for path traversal elements
            parts = Path(filename).parts
            if ".." in parts:
                raise SecurityError(
                    f"ZipSlip traversal attempt detected: entry '{filename}' contains '..'"
                )

            # Check for absolute paths
            if filename.startswith(("/", "\\")) or (len(filename) > 1 and filename[1] == ":"):
                raise SecurityError(
                    f"ZipSlip traversal attempt detected: absolute path '{filename}'"
                )

            # Check resolved destination path
            dest_file = (target_resolved / filename).resolve()
            try:
                common = os.path.commonpath([str(target_resolved), str(dest_file)])
            except ValueError:
                raise SecurityError(
                    f"ZipSlip traversal attempt detected: cross-drive path for '{filename}'"
                )

            if common != str(target_resolved):
                raise SecurityError(
                    f"ZipSlip traversal attempt detected: target '{dest_file}' outside '{target_resolved}'"
                )

        # Extract verified archive
        zf.extractall(target_resolved)

    return target_resolved


# ──────────────────────────────────────────────
# Manifest Validation
# ──────────────────────────────────────────────

def validate_pack_manifest(
    manifest: dict[str, Any],
    schema_path: Optional[Path] = None,
) -> tuple[bool, str]:
    """
    Validate pack.json manifest against required fields and Draft-07 schema.

    Returns:
        (is_valid: bool, error_message: str)
    """
    if not isinstance(manifest, dict):
        return False, "Manifest must be a JSON object"

    # Required root keys per Draft-07 specification
    required_keys = ["id", "schema_version", "name", "version", "author", "brand_track", "vibes"]
    for key in required_keys:
        if key not in manifest:
            return False, f"Missing required root key: '{key}'"

    if manifest.get("schema_version") != "1.0.0":
        return False, f"Invalid schema_version: '{manifest.get('schema_version')}' (must be '1.0.0')"

    author = manifest.get("author")
    if not isinstance(author, dict) or not author.get("name"):
        return False, "Author must be an object with a non-empty 'name' field"

    brand_track = str(manifest.get("brand_track", "")).lower()
    valid_tracks = {"consumer", "professional", "universal", "vihara", "bihari"}
    if brand_track not in valid_tracks:
        return False, f"Invalid brand_track '{brand_track}'. Must be one of {valid_tracks}"

    vibes_obj = manifest.get("vibes")
    if not isinstance(vibes_obj, dict):
        return False, "'vibes' must be an object mapping canonical vibes"

    # All 12 canonical vibes must be present
    for vibe in Vibe:
        vibe_key = vibe.value
        if vibe_key not in vibes_obj:
            return False, f"Missing canonical vibe in manifest: '{vibe_key}'"
        v_entry = vibes_obj[vibe_key]
        if not isinstance(v_entry, dict):
            return False, f"Vibe entry for '{vibe_key}' must be an object"
        if not v_entry.get("folder") or not isinstance(v_entry.get("folder"), str):
            return False, f"Vibe entry for '{vibe_key}' must declare a string 'folder'"
        reflections = v_entry.get("reflections")
        if not isinstance(reflections, list) or len(reflections) == 0:
            return False, f"Vibe entry for '{vibe_key}' must declare at least one reflection"

    # Optional jsonschema library validation
    try:
        import jsonschema

        schema = None
        if schema_path and Path(schema_path).exists():
            with open(schema_path, "r", encoding="utf-8") as f:
                schema = json.load(f)
        else:
            # Default schema path in packs/ or product_strategy
            default_schema = Path(__file__).resolve().parent.parent / "packs" / "meme_pack_schema.json"
            if not default_schema.exists():
                default_schema = (
                    Path(__file__).resolve().parent.parent
                    / "product_strategy"
                    / "01_technical_packaging"
                    / "meme_pack_schema.json"
                )
            if default_schema.exists():
                with open(default_schema, "r", encoding="utf-8") as f:
                    schema = json.load(f)

        if schema:
            jsonschema.validate(instance=manifest, schema=schema)
    except Exception as exc:
        if "jsonschema" in str(type(exc)):
            return False, f"JSON Schema validation failed: {exc}"
        pass

    return True, ""


def log_pack_error(error_log_path: Path, pack_name: str, error_msg: str) -> None:
    """Log pack rejection warning to error_log_path and standard logging."""
    logger.warning(f"Pack rejected [{pack_name}]: {error_msg}")
    try:
        error_log_path.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with open(error_log_path, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] [WARNING] Rejected pack '{pack_name}': {error_msg}\n")
    except Exception as exc:
        logger.error(f"Could not write to pack error log {error_log_path}: {exc}")


# ──────────────────────────────────────────────
# Loaded Pack Representation
# ──────────────────────────────────────────────

@dataclass
class LoadedPack:
    """Represents an active, validated theme & meme pack."""
    pack_id: str
    name: str
    version: str
    brand_track: str
    author: dict[str, Any]
    description: str
    root_path: Path
    manifest: dict[str, Any]
    ui_theme: dict[str, Any] = field(default_factory=dict)
    icon_path: Optional[Path] = None

    def get_memes(self, vibe: Vibe) -> list[Path]:
        """Return list of valid candidate image files on disk for the given vibe."""
        vibes_obj = self.manifest.get("vibes", {})
        vibe_key = vibe.value
        entry = vibes_obj.get(vibe_key, {})
        folder_rel = entry.get("folder")

        search_dirs: list[Path] = []
        if folder_rel:
            search_dirs.append(self.root_path / folder_rel)

        # Fallback to standard pack folder names
        if vibe in VIBE_TO_PACK_FOLDER:
            search_dirs.append(self.root_path / VIBE_TO_PACK_FOLDER[vibe])
        if vibe in VIBE_FOLDER_NAMES:
            search_dirs.append(self.root_path / "memes" / VIBE_FOLDER_NAMES[vibe])

        for target_dir in search_dirs:
            if target_dir.exists() and target_dir.is_dir():
                found = [
                    f for f in target_dir.iterdir()
                    if f.is_file() and f.suffix.lower() in VALID_IMAGE_EXTENSIONS
                ]
                if found:
                    return sorted(found, key=lambda p: p.name)

        return []

    def get_reflections(self, vibe: Vibe) -> list[str]:
        """Return declared reflections for the vibe."""
        entry = self.manifest.get("vibes", {}).get(vibe.value, {})
        return entry.get("reflections", [])

    def get_contextual_templates(self, vibe: Vibe) -> list[str]:
        """Return contextual templates containing {subject} token for the vibe."""
        entry = self.manifest.get("vibes", {}).get(vibe.value, {})
        return entry.get("contextual_templates", [])


# ──────────────────────────────────────────────
# Hot-Discovery Watcher
# ──────────────────────────────────────────────

class PackDirectoryWatcher:
    """
    Watches the packs directory for new, modified, or removed .lucidpack archives
    or exploded directories, polling every 350ms (or on demand).
    """

    def __init__(
        self,
        packs_dir: Path,
        on_change: Optional[Callable[[list[str]], None]] = None,
        poll_interval: float = 0.35,
    ):
        self.packs_dir = Path(packs_dir)
        self.on_change = on_change
        self.poll_interval = poll_interval
        self._last_snapshot: dict[str, tuple[float, int]] = {}
        self._running = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def scan_for_changes(self) -> list[str]:
        """
        Perform an immediate synchronous scan of the packs directory.

        Returns list of pack paths (or names) that were added, modified, or removed.
        """
        if not self.packs_dir.exists():
            return []

        current_snapshot: dict[str, tuple[float, int]] = {}
        changes: list[str] = []

        try:
            for item in self.packs_dir.iterdir():
                if item.name.startswith((".", "_")) or item.name == "pack_errors.log":
                    continue

                if item.is_file() and item.suffix.lower() == ".lucidpack":
                    stat = item.stat()
                    current_snapshot[item.name] = (stat.st_mtime, stat.st_size)
                elif item.is_dir() and (item / "pack.json").is_file():
                    stat = (item / "pack.json").stat()
                    current_snapshot[item.name] = (stat.st_mtime, stat.st_size)
        except OSError as exc:
            logger.debug(f"Error scanning packs directory: {exc}")
            return []

        # Check for additions and modifications
        for name, sig in current_snapshot.items():
            if name not in self._last_snapshot:
                changes.append(name)
            elif self._last_snapshot[name] != sig:
                changes.append(name)

        # Check for removals
        for name in self._last_snapshot:
            if name not in current_snapshot:
                changes.append(name)

        self._last_snapshot = current_snapshot

        if changes and self.on_change:
            try:
                self.on_change(changes)
            except Exception as exc:
                logger.error(f"Error in PackDirectoryWatcher change callback: {exc}")

        return changes

    def _watch_loop(self):
        """Background thread loop polling every poll_interval seconds."""
        # Initial snapshot without firing callback
        if self.packs_dir.exists():
            try:
                for item in self.packs_dir.iterdir():
                    if item.is_file() and item.suffix.lower() == ".lucidpack":
                        stat = item.stat()
                        self._last_snapshot[item.name] = (stat.st_mtime, stat.st_size)
                    elif item.is_dir() and (item / "pack.json").is_file():
                        stat = (item / "pack.json").stat()
                        self._last_snapshot[item.name] = (stat.st_mtime, stat.st_size)
            except Exception:
                pass

        while not self._stop_event.is_set():
            self.scan_for_changes()
            self._stop_event.wait(self.poll_interval)

    def start(self):
        """Start the background monitoring thread."""
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._watch_loop,
            name="PackDirectoryWatcher",
            daemon=True,
        )
        self._thread.start()
        logger.info(f"PackDirectoryWatcher started on {self.packs_dir} (interval {self.poll_interval}s)")

    def stop(self, timeout: float = 2.0):
        """Stop the background monitoring thread."""
        if not self._running:
            return
        self._running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        logger.info("PackDirectoryWatcher stopped.")


# ──────────────────────────────────────────────
# Pack Manager Service
# ──────────────────────────────────────────────

class PackManager:
    """
    Central manager for discovery, safe extraction, validation,
    and runtime serving of theme and meme packs.
    """

    def __init__(
        self,
        packs_dir: Optional[Path] = None,
        bundled_pack_path: Optional[Path] = None,
        auto_start_watcher: bool = False,
        poll_interval: float = 0.35,
        cache_dir: Optional[Path] = None,
    ):
        if packs_dir is None:
            local_app = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
            self.packs_dir = Path(local_app) / "Vihara" / "packs"
        else:
            self.packs_dir = Path(packs_dir)

        if bundled_pack_path is None:
            # Default location: packs/default.lucidpack in repository root
            workspace_root = Path(__file__).resolve().parent.parent
            self.bundled_pack_path = workspace_root / "packs" / "default.lucidpack"
        else:
            self.bundled_pack_path = Path(bundled_pack_path)

        if cache_dir is None:
            self.cache_dir = self.packs_dir / ".cache"
        else:
            self.cache_dir = Path(cache_dir)

        self.error_log_path = self.packs_dir / "pack_errors.log"
        self.packs: dict[str, LoadedPack] = {}
        self.active_pack_id: str = "vihara-core-default"
        self._lock = threading.RLock()

        # Ensure directories exist
        self.packs_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Initial discovery
        self.discover_and_load_all()

        # Watcher initialization
        self.watcher = PackDirectoryWatcher(
            packs_dir=self.packs_dir,
            on_change=self._on_packs_directory_changed,
            poll_interval=poll_interval,
        )
        if auto_start_watcher:
            self.start_watcher()

    def _on_packs_directory_changed(self, changed_items: list[str]):
        """Callback invoked when watcher detects changes in the packs folder."""
        logger.info(f"Pack directory changes detected: {changed_items}. Updating pack registry...")
        self.discover_and_load_all()

    def discover_and_load_all(self) -> dict[str, LoadedPack]:
        """
        Scan packs_dir and bundled pack path, extract archives safely,
        validate manifests, and update active pack registry.
        """
        with self._lock:
            # 1. Load bundled default pack if available
            bundled_id = "vihara-core-default"
            if self.bundled_pack_path and self.bundled_pack_path.exists():
                bundled_pack = self.load_pack(self.bundled_pack_path)
                if bundled_pack:
                    bundled_id = bundled_pack.pack_id
                    self.packs[bundled_pack.pack_id] = bundled_pack

            # 2. Scan packs directory for .lucidpack archives and exploded folders
            current_found_ids: set[str] = set()
            if self.packs_dir.exists():
                for item in sorted(self.packs_dir.iterdir()):
                    if item.name.startswith((".", "_")) or item.name == "pack_errors.log":
                        continue

                    if (item.is_file() and item.suffix.lower() == ".lucidpack") or (
                        item.is_dir() and (item / "pack.json").is_file()
                    ):
                        pack = self.load_pack(item)
                        if pack:
                            self.packs[pack.pack_id] = pack
                            current_found_ids.add(pack.pack_id)

            # 3. Clean up uninstalled packs (excluding bundled default pack)
            for pid in list(self.packs.keys()):
                if pid != bundled_id and pid not in current_found_ids:
                    logger.info(f"Pack '{pid}' was removed from disk. Unregistering.")
                    del self.packs[pid]

            # 4. Set fallback active pack if current active_pack_id is not present
            if self.active_pack_id not in self.packs:
                if bundled_id in self.packs:
                    self.active_pack_id = bundled_id
                elif self.packs:
                    self.active_pack_id = next(iter(self.packs.keys()))

            logger.info(
                f"PackManager loaded {len(self.packs)} pack(s). Active pack: '{self.active_pack_id}'"
            )
            return dict(self.packs)

    def load_pack(self, pack_path: Path) -> Optional[LoadedPack]:
        """
        Safely load, validate, and return a LoadedPack from an archive or folder.

        If the pack is corrupt, invalid, or violates security (ZipSlip),
        logs the error to pack_errors.log and returns None without crashing.
        """
        pack_path = Path(pack_path)
        pack_name = pack_path.name

        try:
            root_dir: Path

            if pack_path.is_file():
                if pack_path.suffix.lower() != ".lucidpack":
                    log_pack_error(self.error_log_path, pack_name, "File extension must be .lucidpack")
                    return None

                target_cache = self.cache_dir / pack_path.stem
                # Check if cached extraction is already up to date
                pack_mtime = pack_path.stat().st_mtime
                cache_manifest = target_cache / "pack.json"
                if (
                    target_cache.is_dir()
                    and cache_manifest.is_file()
                    and cache_manifest.stat().st_mtime >= pack_mtime
                ):
                    root_dir = target_cache
                else:
                    # Clean previous cache directory if it existed
                    if target_cache.exists():
                        shutil.rmtree(target_cache, ignore_errors=True)
                    # Safe extraction with ZipSlip defense
                    safe_extract_lucidpack(pack_path, target_cache)
                    root_dir = target_cache

            elif pack_path.is_dir():
                root_dir = pack_path
            else:
                log_pack_error(self.error_log_path, pack_name, "Pack path does not exist")
                return None

            # Load pack.json
            manifest_path = root_dir / "pack.json"
            if not manifest_path.is_file():
                log_pack_error(self.error_log_path, pack_name, "pack.json not found in pack root")
                return None

            try:
                manifest_content = manifest_path.read_text(encoding="utf-8")
                manifest = json.loads(manifest_content)
            except Exception as json_err:
                log_pack_error(self.error_log_path, pack_name, f"Invalid JSON manifest: {json_err}")
                return None

            # Validate manifest
            is_valid, err_msg = validate_pack_manifest(manifest)
            if not is_valid:
                log_pack_error(self.error_log_path, pack_name, f"Validation error: {err_msg}")
                return None

            icon_path = root_dir / "icon.png"
            if not icon_path.is_file():
                icon_path = None

            loaded = LoadedPack(
                pack_id=manifest["id"],
                name=manifest["name"],
                version=manifest["version"],
                brand_track=manifest["brand_track"],
                author=manifest["author"],
                description=manifest.get("description", ""),
                root_path=root_dir,
                manifest=manifest,
                ui_theme=manifest.get("ui_theme", {}),
                icon_path=icon_path,
            )
            return loaded

        except SecurityError as sec_err:
            log_pack_error(self.error_log_path, pack_name, f"Security violation: {sec_err}")
            return None
        except zipfile.BadZipFile as zip_err:
            log_pack_error(self.error_log_path, pack_name, f"Corrupted ZIP archive: {zip_err}")
            return None
        except Exception as exc:
            log_pack_error(self.error_log_path, pack_name, f"Unexpected error loading pack: {exc}")
            return None

    def install_pack(self, archive_path: Path) -> Optional[LoadedPack]:
        """
        Install a .lucidpack into packs_dir, load it, and activate it.
        """
        archive_path = Path(archive_path)
        if not archive_path.is_file():
            log_pack_error(self.error_log_path, archive_path.name, "File does not exist")
            return None

        dest = self.packs_dir / archive_path.name
        try:
            shutil.copy2(archive_path, dest)
            pack = self.load_pack(dest)
            if pack:
                with self._lock:
                    self.packs[pack.pack_id] = pack
                    self.active_pack_id = pack.pack_id
                logger.info(f"Installed and activated pack: '{pack.name}' ({pack.pack_id})")
                return pack
            else:
                # If invalid, remove the copied bad archive
                if dest.exists():
                    dest.unlink(missing_ok=True)
                return None
        except Exception as exc:
            log_pack_error(self.error_log_path, archive_path.name, f"Installation failure: {exc}")
            return None

    def get_pack(self, pack_id: str) -> Optional[LoadedPack]:
        """Retrieve loaded pack by ID."""
        with self._lock:
            return self.packs.get(pack_id)

    def get_active_pack(self) -> Optional[LoadedPack]:
        """Retrieve currently active LoadedPack."""
        with self._lock:
            if self.active_pack_id in self.packs:
                return self.packs[self.active_pack_id]
            if self.packs:
                return next(iter(self.packs.values()))
            return None

    def set_active_pack(self, pack_id: str) -> bool:
        """Set the active pack by ID."""
        with self._lock:
            if pack_id in self.packs:
                self.active_pack_id = pack_id
                logger.info(f"Active pack switched to: '{pack_id}'")
                return True
            logger.warning(f"Cannot set active pack: '{pack_id}' is not loaded")
            return False

    def get_all_packs(self) -> list[LoadedPack]:
        """Return list of all loaded packs."""
        with self._lock:
            return list(self.packs.values())

    def get_memes_for_vibe(self, vibe: Vibe) -> list[Path]:
        """Retrieve meme candidates for the given vibe from the active pack."""
        active = self.get_active_pack()
        if active:
            return active.get_memes(vibe)
        return []

    def get_ui_theme(self) -> dict[str, Any]:
        """Return UI theme design tokens for the active pack."""
        active = self.get_active_pack()
        if active and active.ui_theme:
            return dict(active.ui_theme)
        return {
            "bg_color": "#18181b",
            "header_color": "#27272a",
            "text_color": "#f4f4f5",
            "accent_color": "#3b82f6",
            "font_family": "Segoe UI",
            "corner_radius": 8,
            "sound_volume": 0.5,
        }

    def watch_directory(self, dir_path: Path, callback: Callable[[list[str]], None]):
        """Configure directory watcher with custom callback."""
        self.watcher.packs_dir = Path(dir_path)
        self.watcher.on_change = callback

    def start_watcher(self):
        """Start the directory watcher background thread."""
        self.watcher.start()

    def stop_watcher(self):
        """Stop the directory watcher background thread."""
        self.watcher.stop()
