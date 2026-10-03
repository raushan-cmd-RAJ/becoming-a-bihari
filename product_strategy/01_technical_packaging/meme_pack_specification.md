# Extensible Theme and Meme Pack Specification (`.lucidpack`)

**Document ID**: `STRAT-TECH-02`  
**Milestone**: M1 (Technical Packaging & Architecture)  
**Target Requirement**: R1 (Universal Product Architecture & Zero-Friction Distribution)  
**Associated Schema**: `meme_pack_schema.json`  
**Reference Sample**: `sample_pack/pack.json`  
**Status**: Production Architectural Specification  

---

## 1. Overview & Architectural Vision

In the initial prototype, meme assets were hardcoded into unorganized local directories (`memes/the-long-grind`, `memes/tab-butterfly`) without structured metadata, author attribution, visual theme overrides, audio cues, or integrity checking. 

To enable a thriving **Creator Ecosystem** and support the dual-track brand strategy ("Becoming a Bihari" viral savage mirror vs. "Vihara" professional focus catalyst), Vihara establishes the **`.lucidpack` specification**.

A `.lucidpack` is an open, portable, cryptographically verifiable package format that bundles:
1. **Visual Reaction Assets**: Optimized GIFs, PNGs, and WebPs mapped to the 12 cognitive drift states.
2. **Reflections & Contextual Templates**: Authentic text reflections and dynamic window-interpolated one-liners.
3. **Audio Cues**: Gentle auditory feedback (chimes, singing bowls, sighs) synchronized to toast animations.
4. **UI Design Tokens**: Complete color palette, typography, and corner radius tokens for the corner overlay.
5. **Brand Track & Commercial Gating**: Metadata aligning the pack with consumer/professional tiers and creator licensing.

---

## 2. Package Format & Archive Structure

A theme/meme pack exists in two interchangeable states:
1. **Distribution Archive (`.lucidpack`)**: A standard, unencrypted ZIP64 archive with the `.lucidpack` file extension, compressed via Deflate (level 6 or 9).
2. **Exploded Directory**: An unpacked folder placed inside the user's local packs directory, actively monitored by the runtime hot-reloader.

### 2.1 File System Hierarchy

```
my-custom-pack.lucidpack (or directory: my-custom-pack/)
├── pack.json                        # [MANDATORY] Manifest conforming to meme_pack_schema.json
├── icon.png                         # [MANDATORY] 256x256 PNG pack icon for UI menus
├── preview.png                      # [RECOMMENDED] 1200x630 banner for Marketplace gallery
├── README.md                        # [OPTIONAL] Human-readable creator notes & credits
├── LICENSE.txt                      # [OPTIONAL] Full legal text for asset licensing
├── memes/                           # [MANDATORY] Directory containing reaction image assets
│   ├── flow_state/
│   │   ├── deep_focus_01.png
│   │   └── flow_state.gif
│   ├── syntax_rage/
│   │   ├── rage_quit.jpg
│   │   └── compiler_screaming.png
│   ├── lost_in_scroll/
│   │   ├── infinite_feed.png
│   │   └── void_stare.webp
│   └── ... (folders for remaining vibes)
├── audio/                           # [OPTIONAL] Audio cues (WAV / OGG / MP3)
│   ├── soft_chime.wav
│   └── gentle_bell.ogg
└── metadata/                        # [OPTIONAL] Asset-level provenance & alt-text
    ├── memes/
    │   ├── lost_in_scroll.png.meta.json
    │   └── syntax_rage.png.meta.json
    └── audio/
        └── soft_chime.wav.meta.json
```

---

## 3. The 12 Canonical Cognitive Drift Vibes

Every valid `.lucidpack` must support the **12 canonical cognitive drift states** defined by the core inference engine. If a creator pack omits assets for any specific vibe, the runtime automatically falls back to default system reflections:

| # | Vibe Enum Key | Cognitive State Description | Default Trigger Signature |
|---|---|---|---|
| 1 | `FLOW_STATE` | Deep productive concentration | Monotonic high typing velocity (>60 WPM), zero backspaces, sustained IDE/writing context >15 min |
| 2 | `GRINDING` | Extended effort and perseverance | Moderate continuous activity >45 min without pause |
| 3 | `BURNOUT_APPROACHING` | Exhaustion, fatigue, and cognitive depletion | Rapid error spikes, erratic mouse cursor jitter, continuous work >90 min |
| 4 | `SYNTAX_RAGE` | Frustration, compiler errors, build failures | Rapid backspace bursts (>12 presses/3s), aggressive keystroke intensity |
| 5 | `HELP_SEEKING` | Active research and problem solving | Browser transitions to Stack Overflow, GitHub Issues, documentation, LLM chats |
| 6 | `MOUNTING_FRICTION` | Stagnation, confusion, and resistance | Frequent cursor stops, long pauses (>45s) interspersed with single-line edits |
| 7 | `WANDERING` | Low-focus exploration / productive procrastination | Switching between documentation, Wikipedia, email, terminal without writing code |
| 8 | `LOST_IN_SCROLL` | Unconscious social doomscrolling | Active window in X/Twitter, Reddit, YouTube Shorts, Instagram Reels >5 min |
| 9 | `TAB_BUTTERFLY` | Frenetic multi-tasking / browser overload | Opening >10 browser tabs in <60 seconds, rapid tab flipping |
| 10 | `STILLNESS` | Intentional rest, away from keyboard | Zero keyboard/mouse input for >3 minutes while computer unlocked |
| 11 | `MEETING_RECOVERY` | Post-call cognitive decompression | Immediate window transition from Zoom, Microsoft Teams, or Google Meet |
| 12 | `AFTERNOON_DRIFT` | Post-lunch circadian energy dip | Time window 14:00–16:00 local time with low input velocity (<15 WPM) |

---

## 4. Manifest Specification (`pack.json`)

The manifest is authored in JSON and strictly validated against `meme_pack_schema.json` (Draft-07).

### 4.1 Schema Field Definitions

- **`id`** (`string`, required): Unique pack identifier. Must use reverse-DNS notation or kebab-case (e.g. `com.creator.bihari-savage`, `corporate-zen-pack`). Pattern: `^[a-z0-9][a-z0-9_.-]+$`.
- **`schema_version`** (`string`, required): Always `"1.0.0"`.
- **`name`** (`string`, required): Display name shown in tray menu and UI (3–60 characters).
- **`version`** (`string`, required): Semantic version (`MAJOR.MINOR.PATCH`, e.g. `"1.2.0"`).
- **`brand_track`** (`string`, required): Brand alignment matching M2 dual-track strategy:
  - `"consumer"`: Savage humor, edgy roasts, raw viral memes (Track A: "Becoming a Bihari").
  - `"professional"`: Stoic clarity, gentle mindfulness, clean aesthetic (Track B: "Vihara").
  - `"universal"`: Balanced tone appropriate for both casual and workplace environments.
- **`author`** (`object`, required):
  - `name` (`string`, required): Creator or organization name.
  - `url` (`string`, optional): Creator website or social link.
  - `email` (`string`, optional): Creator contact.
- **`description`** (`string`, optional): Summary of the pack's theme, inspiration, and content (up to 500 characters).
- **`license`** (`string`, optional): Legal licensing terms (e.g. `"CC-BY-4.0"`, `"MIT"`, `"Proprietary"`).
- **`content_rating`** (`string`, optional): Content maturity filter: `"everyone"` (default), `"teen"`, `"mature"`, `"edgy_humor"`.
- **`tier_requirement`** (`string`, optional): Commercial gating boundary: `"free"` (default), `"pro"`, `"team"`.
- **`ui_theme`** (`object`, optional): Design tokens overriding toast styling:
  - `bg_color`: Hex color string (`#18181b`).
  - `header_color`: Hex color string (`#27272a`).
  - `text_color`: Hex color string (`#f4f4f5`).
  - `accent_color`: Hex color string (`#3b82f6`).
  - `font_family`: Typography string (`"Segoe UI"`, `"SF Pro"`, `"Inter"`).
  - `corner_radius`: Integer (0–24 pixels).
  - `sound_volume`: Float (0.0 to 1.0).
- **`vibes`** (`object`, required): Dictionary containing all 12 canonical vibe entries.
  - `folder`: Relative path to directory containing reaction images.
  - `audio_cue`: Optional relative path to sound stinger.
  - `reflections`: Array of strings (min 1, max 120 chars each).
  - `contextual_templates`: Optional array of templates containing the `{subject}` token.
  - `assets`: Optional explicit list of assets with SHA-256 hashes and captions.
- **`asset_hashes`** (`object`, optional): Relative file path to SHA-256 string mapping for tamper verification.

---

## 5. Dynamic Manifest Loading & Lifecycle

The runtime engine handles packs through a resilient **`PackManager`** service:

```
  ┌────────────────────────────────────────────────────────┐
  │                    DISCOVERY PHASE                     │
  │  Scans OS-specific pack directories on app startup     │
  └───────────────────────────┬────────────────────────────┘
                              │ Directory list
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │                   VALIDATION PHASE                     │
  │  1. JSON Schema Draft-07 validation of pack.json       │
  │  2. Security check: ZipSlip path traversal prevention  │
  │  3. Image format & Pillow open test                    │
  │  4. Audio format test (WAV/OGG/MP3)                    │
  └───────────────────────────┬────────────────────────────┘
                              │ Validation passed
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │                  INDEXING & FALLBACK                   │
  │  - Maps 12 vibes into memory                           │
  │  - Any missing vibe defaults to system starter pack    │
  │  - Updates System Tray "Theme & Meme Packs" submenu    │
  └───────────────────────────┬────────────────────────────┘
                              │ Runtime monitoring
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │                 HOT-RELOAD FILE WATCHER                │
  │  Watches pack folders for modifications; invalidates   │
  │  in-memory cache within 300ms without restarting app   │
  └────────────────────────────────────────────────────────┘
```

### 5.1 Discovery Directories by Platform

The runtime automatically scans the following directories for unpacked folders and `.lucidpack` archives:

- **Windows**: `%LOCALAPPDATA%\Vihara\packs\`  
  *(e.g., `C:\Users\<User>\AppData\Local\Vihara\packs`)*
- **macOS**: `~/Library/Application Support/Vihara/packs/`
- **Linux**: `~/.local/share/vihara/packs/`

In addition, the built-in system pack is always bundled inside the application distribution directory (`dist/Vihara/default_memes/`) to serve as an immutable fallback.

---

### 5.2 Hot-Reloading File Watcher Architecture

When pack creators or users drop new images into a vibe folder or edit `pack.json`, the app immediately picks up changes without requiring a restart.

#### Implementation Pattern (`bihari/pack_watcher.py`)

```python
"""
Vihara - Hot-Reloading Pack Watcher
Monitors pack folders using debounced filesystem event notifications.
"""
import time
import logging
from pathlib import Path
from typing import Callable

class PackDirectoryWatcher:
    def __init__(self, packs_dir: Path, on_pack_changed: Callable[[Path], None]):
        self.packs_dir = packs_dir
        self.on_pack_changed = on_pack_changed
        self._last_modified_times = {}
        self._debounce_window_sec = 0.35

    def scan_for_changes(self):
        """
        Polls directory mtimes (or hooks into OS ReadDirectoryChangesW/inotify).
        Debounces multiple write operations from image editors.
        """
        now = time.time()
        for manifest_path in self.packs_dir.glob("*/pack.json"):
            try:
                mtime = manifest_path.stat().st_mtime
                pack_folder = manifest_path.parent
                last_seen = self._last_modified_times.get(pack_folder, 0)
                
                if mtime > last_seen and (now - mtime) >= self._debounce_window_sec:
                    self._last_modified_times[pack_folder] = mtime
                    logging.info(f"Pack change detected in {pack_folder.name}. Reloading...")
                    self.on_pack_changed(pack_folder)
            except OSError:
                continue
```

---

### 5.3 Single-Click `.lucidpack` OS Installation Protocol

To provide true zero-friction installation for non-technical users downloading packs from creators or websites:

1. **File Association**:
   - The installer associates `.lucidpack` with `vihara.exe --install-pack "%1"`.
2. **Execution Flow**:
   - When a user double-clicks `cyberpunk-focus.lucidpack` in their browser downloads:
   - The OS launches `vihara.exe --install-pack "C:\Downloads\cyberpunk-focus.lucidpack"`.
   - If Vihara is already running, the single-instance IPC channel (named pipe `\\.\pipe\ViharaIPC` on Windows, UNIX socket on macOS/Linux) forwards the file path to the background process.
3. **Safe Extraction & ZipSlip Defense**:
   - The extractor validates that all compressed archive paths resolve strictly within the destination directory, blocking path traversal attacks (`../` exploits).
4. **Instant Activation & Celebration**:
   - The newly installed pack is validated, set as the active pack in `config.toml`, and a celebratory corner toast is triggered:
   - Header: `"🪞 New Pack Installed"`
   - Text: `"Activated 'Cyberpunk Focus' by @creator"`

---

## 6. Pack Validation Rules & Security Matrix

| Component | Validation Rule | Error Treatment |
|---|---|---|
| **`pack.json`** | Must be valid JSON and pass Draft-07 Schema validation | Pack rejected; error logged to `pack_errors.log`; skipped in UI |
| **Canonical Vibes** | All 12 canonical vibe keys must be declared | If missing, automatically filled with default system reflections |
| **Image Assets** | Must decode via `PIL.Image.open()` (PNG, JPG, WebP, GIF) | Corrupt image skipped; warning logged; falls back to other images in folder |
| **Image Resolution** | Maximum dimensions: 1920x1080; Max file size: 5MB per asset | Downscaled in memory during toast rendering to prevent RAM bloat |
| **Audio Assets** | Must be valid WAV, OGG, or MP3; duration must be ≤ 4.0 seconds | Audio cue skipped; reflection displays silently |
| **SHA-256 Hashes** | When declared in `asset_hashes`, must match actual asset hash | Flagged as modified/unverified; creator signature invalidated |
| **Text Reflections** | Length between 3 and 120 characters; no raw HTML/scripts | Sanitized and stripped to plain UTF-8 text |
| **Contextual Tokens** | `{subject}` token must be present if declared in `contextual_templates` | Substituted with window title entity (or fallback generic noun) |

---

## 7. Creator Quick-Start: Creating a Pack in 5 Minutes

Creating a custom meme pack is simple enough that anyone can do it:

1. **Create a Folder**: Name it `my-favorite-memes`.
2. **Download Template**: Copy `pack.json` from the `sample_pack` reference.
3. **Customize Manifest**:
   - Set `"id": "com.myname.coolpack"`.
   - Set `"name": "My Cool Memes"`.
   - Choose `"brand_track": "consumer"` or `"professional"`.
4. **Add Images**: Drop your favorite GIFs or PNGs into `memes/flow_state`, `memes/syntax_rage`, `memes/lost_in_scroll`, etc.
5. **Write Reflections**: Add 3–5 funny or mindful one-liners to each vibe in `pack.json`.
6. **Package**: Zip the contents of the folder and rename the extension to `.lucidpack`.
7. **Test & Share**: Double-click `.lucidpack` to install and test on your machine.
