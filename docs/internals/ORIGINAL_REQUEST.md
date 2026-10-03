# Original User Request

## 2026-10-01T05:30:54Z

Develop a comprehensive, execution-ready Productisation and Go-To-Market (GTM) Package for the desktop mindfulness mirror ("Becoming a Bihari" / Lucid Noether), transforming it from a local developer prototype into a universally accessible, commercially viable, and virally marketed desktop application that anyone with a computer can easily use.

Working directory: C:\Users\Raushan\Documents\antigravity\lucid-noether\product_strategy
Integrity mode: development

## Requirements

### R1. Universal Product Architecture & Zero-Friction Distribution
Specify a zero-friction distribution and packaging model so anyone with a computer (non-technical users across Windows, macOS, and Linux) can install and run the app with a single click. No terminal, Python, or dependency configuration required. Must support seamless background tray operation and an extensible theme/meme pack format.

### R2. Brand Positioning & Universal Accessibility
Establish the core positioning ("a mirror, not a judge"), dual-track branding strategy (balancing edgy viral consumer appeal with a clean professional brand), target user personas across both non-technical casual users and professionals, and tailored messaging frameworks.

### R3. Commercial Model & Monetization Architecture
Define the pricing tiers (Free, Pro, Creator Packs, and Team/B2B), feature gating rules, pack marketplace mechanics, and unit economics.

### R4. Viral Go-To-Market & Launch Playbook
Deliver a tactical launch campaign roadmap covering Product Hunt, Hacker News, short-form viral video scripts (TikTok/Reels/Shorts), creator affiliate mechanics, and broad consumer/community distribution.

## Acceptance Criteria

### Technical & Packaging Deliverables
- [ ] Standalone installer and auto-update architecture document specifies build tooling, updater mechanisms, and pack distribution format for Windows, macOS, and Linux without requiring a local Python runtime.
- [ ] Meme pack specification details schema, asset folder structure, and dynamic/local manifest loading.

### Brand & Commercial Deliverables
- [ ] Positioning matrix document defines at least 3 distinct target personas (including non-technical everyday computer users) with pains, triggers, and tailored value propositions.
- [ ] Dual-track branding guide provides distinct name, tagline, and tone guidelines for viral consumer vs. professional tiers.
- [ ] Commercial strategy document details tier matrix (Free vs. Pro vs. Team), pricing points, and feature gating boundaries.

### Go-To-Market & Launch Deliverables
- [ ] Product Hunt and Show HN launch kits include titles, taglines, first-comment copy, maker story, and FAQ.
- [ ] Viral video playbook contains at least 5 complete short-form video storyboards/scripts with exact visual cues and hook lines.
- [ ] 30-day post-launch execution checklist with day-by-day milestone tracking.

## 2026-10-02T06:23:46Z

Transform the existing "Becoming a Bihari" desktop mindfulness mirror prototype (a working Python application with 12 modules for behavioral detection, meme-based reflection, and privacy-first operation) into a polished, installer-ready MVP that anyone with a Windows computer can install and use with a single click — no terminal, no Python, no configuration. The professional product track is named **"Vihara"** (not "Lucid Noether"). The consumer/viral track remains "Becoming a Bihari".

The soul of this product is one thing: **the precision of the meme reflection**. When the meme perfectly mirrors the user's current emotional and behavioral state, that moment of startled self-recognition ("wait, that's literally me right now") is itself the mechanism that invokes self-awareness and bliss. Every engineering decision should serve making that reflection as uncannily accurate, timely, and emotionally resonant as possible.

Working directory: c:\Users\Raushan\Documents\antigravity\lucid-noether
Integrity mode: development

Reference material:
- Existing codebase in `bihari/` (12 working modules: spy, inference, context, ocr, memes, fetcher, display, tray, logger, privacy, config)
- Product strategy documents in `product_strategy/` (technical packaging architecture, meme pack spec, brand positioning, commercial strategy, GTM playbook)

## Requirements

### R1. Meme Reflection Precision Overhaul
The core value proposition is that every surfaced meme must feel like an uncannily accurate mirror of the user's current state. The detection-to-meme pipeline must be overhauled so that the behavioral classification (typing velocity, window context, OCR screen content, time-of-day, session duration) maps to the most emotionally precise visual reaction possible. This includes improving the granularity of vibe sub-states, enriching the contextual subject extraction (what specifically the user is looking at or doing), and ensuring the meme selection algorithm prioritizes emotional resonance over randomness. The reflection text (the short punchy caption like "🪞 Essential research, obviously.") must feel genuinely witty and self-aware, not generic.

### R2. Vihara Rebrand & Dual-Track Identity
Rename all references from "Lucid Noether" to "Vihara" throughout the codebase, configuration files, installer metadata, tray icon tooltip, and user-facing strings. The consumer track ("Becoming a Bihari") keeps its identity. Ensure both brand tracks are cleanly separated in user-facing surfaces (installer name, tray label, window titles) while sharing the same codebase.

### R3. Zero-Friction Windows Installer & Standalone Packaging
Package the application as a standalone Windows installer that requires no Python runtime, no terminal interaction, and no dependency management. A non-technical user should be able to download a single file, double-click it, and have the app running in their system tray within 60 seconds. The application must start automatically on login (optional, user-configurable), run silently in the background, and provide a clean uninstaller. Architecture the build system so that macOS and Linux packaging can be added later without restructuring.

### R4. Bug Fixes & Production Hardening
Fix all known bugs in the existing codebase (including the NameError in `context.py` line 381 where `extract_clean_search_query` is called but never defined, and the missing `winocr`/`tomli` dependencies in `setup.py`). Harden error handling throughout — the app must never crash or show a traceback to the user. All failure modes (network unavailable, meme folders empty, OCR unavailable, Laya model not installed) must degrade gracefully with sensible fallbacks.

### R5. Extensible Meme Pack System
Implement the `.lucidpack` meme pack format (as specified in `product_strategy/01_technical_packaging/meme_pack_specification.md`) so users and creators can install, swap, and create custom reaction packs. The app must ship with a high-quality default pack that covers all 12 vibes with enough variety to avoid repetition for at least the first 2 weeks of daily use.

## Acceptance Criteria

### Meme Precision & Emotional Resonance
- [ ] Given a simulated user session where the user types code at >50 chars/min with <8% backspace rate for 10+ minutes, the system classifies FLOW_STATE and suppresses all meme popups (zero interruptions during genuine flow).
- [ ] Given a simulated user session browsing YouTube for >3 minutes with zero typing, the system classifies LOST_IN_SCROLL and surfaces a meme whose visual content (reaction image) and reflection caption both reference the specific content category being consumed (e.g., video binge, social scroll).
- [ ] Given a simulated user session with >35% backspace rate while in a code editor, the system classifies SYNTAX_RAGE and the reflection text references coding frustration specifically, not generic frustration.
- [ ] The meme selection system never repeats the same image within a 60-event window, verified by running a 100-event simulation and asserting zero duplicates.
- [ ] Reflection captions are under 40 characters and contain a context-specific subject reference (not a generic placeholder) in at least 80% of events where a subject is extractable.

### Rebrand & Identity
- [ ] Zero occurrences of the string "Lucid Noether" (case-insensitive) anywhere in the codebase, configuration files, installer scripts, or user-facing strings.
- [ ] The system tray tooltip, installer metadata, and About/version info display "Vihara" as the product name.
- [ ] The tray icon and installer branding reflect the Vihara identity.

### Installer & Packaging
- [ ] A single `.exe` installer file exists that, when double-clicked on a clean Windows 10/11 machine without Python installed, installs and launches the application into the system tray within 60 seconds.
- [ ] The installed application runs without requiring administrator/UAC elevation.
- [ ] The application can be cleanly uninstalled via Windows Settings > Apps.
- [ ] The build system produces the installer via a single documented command (e.g., `build.bat` or equivalent).

### Production Stability
- [ ] The application runs for 8+ simulated hours of mixed activity (cycling through all 12 vibe states) without crashing, hanging, or displaying an unhandled exception.
- [ ] When launched with no internet connection and empty meme folders, the application starts successfully and displays a graceful fallback (text-only reflection or bundled default memes) instead of crashing.
- [ ] All Python files pass `python -m py_compile` with zero errors.
- [ ] A test suite exists with at least 30 tests covering the detection pipeline, meme selection, privacy filter, and reflection generation, all passing.

### Meme Pack System
- [ ] A valid `.lucidpack` file can be placed in the designated packs directory and is automatically discovered and loaded by the application without restart.
- [ ] The default bundled pack contains at least 10 unique meme images per vibe category (120+ total across 12 vibes).
- [ ] An invalid or corrupted `.lucidpack` file is rejected gracefully with a log warning, without affecting the rest of the application.
