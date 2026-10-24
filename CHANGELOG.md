# Changelog

All notable changes to **Vihara** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.0] - 2026-10-24

### 🧠 AI & Semantic Perception Engine
- **Option B (Primary Semantic Brain)**: Integrated quantized ONNX `all-MiniLM-L6-v2` (`bihari.onnx_brain`, 21.9 MB) with multi-prototype vibe anchors across all 12 behavioral archetypes. Computes 384-dimensional cosine similarities with zero external tokenization wheels via pure-Python fallback WordPiece tokenizer.
- **Option A (MicroBrain 2.0 Fallback)**: Upgraded pure-Python linear classifier (`bihari.micro_model`, <500 KB weights) providing an instant 0% CPU offline fallback whenever `onnxruntime` is not present.
- **Terminal & Shell Flow State**: Retrained models and fine-tuned rules for developer shells (`powershell.exe`, `windowsterminal.exe`, `cmd.exe`) and command lines to prevent premature `WANDERING` false positives.
- **Social vs Technical Filtering**: Added guardrails preventing technical learning posts on social platforms from being falsely labeled as mindless scrolling.
- **Decoupled Heavy Dependencies**: Completely removed runtime dependencies on heavy frameworks (`torch`, `torchvision`, `transformers`, `huggingface_hub`, `sklearn`), reducing system resource overhead to negligible levels.

### 🔄 Meme Management & Storage Optimization
- **Lightweight Distribution Decoupling**: Excluded the static 94 MB `default.lucidpack` from the binary payload, reducing installer size by over 75% down to ~20–25 MB.
- **Autonomous Background Seeding**: Implemented startup background seeding and on-demand inventory replenishment from curated Reddit visual reaction communities (`r/reactionpics`, `r/wholesomememes`, `r/rarepuppers`, `r/oddlysatisfying`, `r/wunkus`).
- **Rolling Ring Buffer Disk Pruner**: Added `prune_seen_memes()` to retain only the 10 most recent seen meme files on disk (`max_seen_history_files = 10`), bounding disk usage under 15–20 MB while preserving lifetime deduplication.
- **30-Day Natural Cool-Off Window**: Added configurable `repeat_cooloff_days` (default: 30 days) allowing older seen visual reactions to re-enter rotation without repetitive fatigue.

### 🎨 Product & Branding Unification
- **Unified Mindful Identity**: Unified brand architecture under **Vihara: Mindful Focus Catalyst & Digital Mirror**, removing dual personality toggles from the UI for a focused, dignified mindful experience.
- **Windowless Tray Daemon**: Configured PyInstaller build for clean windowless tray startup without console window flashes.
- **File-Backed Diagnostic Logging**: Automatically logs desktop daemon operations to `%LOCALAPPDATA%\Bihari\vihara.log`.

### 📦 Build & Packaging
- **Production PyInstaller Specification**: Updated `packaging/windows/vihara.spec` to bundle ONNX models, anchor clusters, config, and icons into `dist/vihara/vihara.exe`.
- **COM Initialization Fix**: Resolved Windows isolated subprocess access violation crash (`0xC0000005`) between `winrt` and `onnxruntime` during DLL inspection.

---

## [0.1.0] - 2026-10-23

### Initial Release
- Initial release of the desktop mindfulness mirror prototype.
- Core 12-vibe behavioral taxonomy across 4 categories (`FLOW_STATE`, `SYNTAX_RAGE`, `LOST_IN_SCROLL`, etc.).
- Monotonic timestamp velocity tracking for zero-keylogging flow state detection.
- Windows Media OCR volatile header inspection.
- SQLite history tracking for basic zero-repeat.
