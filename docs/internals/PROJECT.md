# Project: Vihara ("Becoming a Bihari") Productisation & GTM Package

## Architecture
The Productisation and Go-To-Market (GTM) Package transforms the Vihara / "Becoming a Bihari" prototype into a commercially viable, universally accessible, and virally marketed desktop application.

```
                              CORE APPLICATION ENGINE (Local-First)
                ┌─────────────────────────────────────────────────────────────┐
                │ • Telemetry Harvester: Monotonic velocity, zero keylogging │
                │ • Window Context & Native OCR: RAM-only, <30ms execution    │
                │ • Privacy Sanitizer: Blocklist, password/credential masking │
                │ • Inference Engine: 12 vibes, dual-cooldown, flow-state gate│
                └──────────────────────────────┬──────────────────────────────┘
                                               │
               ┌───────────────────────────────┴───────────────────────────────┐
               ▼                                                               ▼
    TRACK A: CONSUMER / VIRAL                                      TRACK B: ENTERPRISE / PRO
       "Becoming a Bihari"                                              "Vihara"
  "The Savage Mindfulness Mirror"                                "The Mindful Focus Catalyst"
  • Electric Amber / Obsidian theme                             • Prussian Blue / Frosted Glass
  • Raw humor, roast reflections                                • Stoic clarity, gentle reflections
  • Social viral loops & meme drops                             • Deep work protection & team health
               │                                                               │
               └───────────────────────────────┬───────────────────────────────┘
                                               ▼
                         DISTRIBUTION & COMMERCIAL PLATFORM
  • Standalone Installers: Windows (Inno Setup .exe), macOS (.dmg), Linux (AppImage)
  • Micro-Updater: Atomic background download, SHA-256 verification, PID swap
  • Pack Ecosystem: .lucidpack JSON Schema, dynamic manifest loader, Creator Marketplace (70/30 split)
  • Monetization Matrix: Free Community ($0) | Pro ($9/mo, $79/yr, $149 lifetime) | Team ($15/seat/mo)
  • Launch Engine: Product Hunt Kit, Show HN Kit, 5-Video Viral Playbook, 30-Day Execution Matrix
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F1 | Standalone Installer Architecture | Multi-platform packaging specification for Windows (Inno Setup), macOS (.dmg/notarytool), Linux (AppImage) requiring zero Python/terminal dependencies | M1 | ORIGINAL_REQUEST §R1 |
| F2 | Atomic Auto-Update System | Version manifest schema, CDN/GitHub release integration, background check/download, detached process directory swap | M1 | ORIGINAL_REQUEST §R1 |
| F3 | Background Tray & OS Integration | Multi-state tray icon, context menu actions, low-footprint event hooks, sleep/wake resilience | M1 | ORIGINAL_REQUEST §R1 |
| F4 | Extensible Theme & Meme Pack Spec | Formal JSON Schema, asset directory structure, local & remote manifest loading, hot-reloading file watcher, sample pack | M1 | ORIGINAL_REQUEST §R1 |
| F5 | Core Positioning: "Mirror, Not a Judge" | Cognitive drift & defusion psychology, <150ms visual reaction mechanics, zero-surveillance local guarantees | M2 | ORIGINAL_REQUEST §R2 |
| F6 | Dual-Track Branding Architecture | Distinct brand guides for Track A (Becoming a Bihari) vs Track B (Vihara): naming, taglines, visual palette, voice, copy | M2 | ORIGINAL_REQUEST §R2 |
| F7 | Deep Persona Matrix | 4 fully articulated personas (including everyday non-technical users and corporate knowledge workers) with pains, triggers, and value props | M2 | ORIGINAL_REQUEST §R2 |
| F8 | Commercial Strategy & Tier Matrix | 4-tier matrix (Free Community, Pro Individual, Creator Packs, Enterprise Team), exact pricing points ($/mo, $/yr, lifetime), feature gating rules | M3 | ORIGINAL_REQUEST §R3 |
| F9 | Pack Marketplace Mechanics | Creator pack submission, curation pipeline, 70/30 revenue share, cryptographic licensing/DRM, distribution protocol | M3 | ORIGINAL_REQUEST §R3 |
| F10 | Unit Economics & Breakeven Model | COGS, hosting costs, CAC by channel, LTV, gross margin (>90%), and cashflow breakeven analysis | M3 | ORIGINAL_REQUEST §R3 |
| F11 | Product Hunt Launch Kit | Launch titles, taglines (<60 chars), maker first-comment copy, authentic founder story, 8-slide gallery specification, comprehensive FAQ | M4 | ORIGINAL_REQUEST §R4 |
| F12 | Show HN Launch Kit | Hacker News culture framing, Show HN title conventions, engineering deep dive, architecture highlights, privacy battlecard | M4 | ORIGINAL_REQUEST §R4 |
| F13 | Viral Short-Form Video Playbook | 5 complete, distinct concept storyboards/scripts with exact visual cues, audio design, hook lines, turn/climax, CTAs | M4 | ORIGINAL_REQUEST §R4 |
| F14 | 30-Day Post-Launch Execution Checklist | Day-by-day milestone tracking from Day 1 to Day 30 across launch spikes, community retention, affiliate seeding, pack drops | M4 | ORIGINAL_REQUEST §R4 |
| F15 | E2E Opaque-Box Quality & Integrity Suite | Comprehensive automated validation harness verifying all schemas, JSON structures, tier gating boundaries, and acceptance criteria | M5 | ORIGINAL_REQUEST §Acceptance Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Technical Architecture & Packaging | Standalone installer & auto-update spec, system tray spec, extensible meme pack specification + JSON schema + sample pack | None | **DONE** (Verified, schema tests pass) |
| M2 | Brand Positioning & Universal Accessibility | Positioning matrix (4 personas), dual-track branding guide (Consumer vs Professional) | None | **DONE** (Verified, 4 personas, copy matrix) |
| M3 | Commercial Strategy & Monetization | Tier matrix (Free vs Pro vs Team), pricing, feature gating boundaries, marketplace mechanics, unit economics | M2 | **DONE** (Verified, pricing, 70/30 split, economics) |
| M4 | Viral GTM & Launch Playbook | Product Hunt launch kit, Show HN launch kit, 5 viral video storyboards/scripts, 30-day post-launch execution checklist | M2, M3 | **DONE** (Verified, 5 scripts, 30-day checklist) |
| M5 | E2E Verification & Audit Gate | Automated validation harness, JSON schema verification, cross-deliverable consistency checks, E2E acceptance test suite | M1, M2, M3, M4 | **DONE** (Audit CLEAN, 58 tests pass) |

## Interface Contracts
### M1 (Packaging & Packs) ↔ M2 (Brand) & M3 (Commercial)
- **Pack Manifest Contract**: Meme and theme packs must support a `brand_track` property (`"consumer"`, `"professional"`, or `"universal"`) in `pack.json` matching the dual-track brand definition in M2.
- **Tier Gating Contract**: Feature flags defined in M1 (`custom_packs`, `cloud_sync`, `analytics_export`, `team_index`) map 1:1 to tier definitions in M3.

### M2 (Brand) ↔ M4 (GTM & Launch)
- **Messaging Alignment Contract**: Product Hunt and video copy in M4 must strictly conform to Track A ("The Savage Mindfulness Mirror") and Track B ("The Mindful Focus Catalyst") tone and nomenclature defined in M2.
- **Persona Target Contract**: Show HN launch kit targets Persona 2 (Software Dev), Product Hunt targets Persona 1 & 4 (Gen-Z & Creative Nomad), and enterprise copy targets Persona 3 (Corporate Manager).

### M3 (Commercial) ↔ M4 (GTM & Launch)
- **Offer Consistency Contract**: Pricing cited across Product Hunt FAQ, launch comments, and 30-day post-launch promotional milestones ($9/mo, $79/yr, $149 lifetime) must exactly match M3 commercial strategy.

## Code Layout
All deliverables are authored as production-grade markdown, JSON schemas, and runnable test harnesses in `product_strategy/`:

```
c:\Users\Raushan\Documents\antigravity\vihara\product_strategy\
├── 01_technical_packaging\
│   ├── standalone_installer_and_autoupdate_architecture.md
│   ├── meme_pack_specification.md
│   ├── meme_pack_schema.json
│   └── sample_pack\
│       ├── pack.json
│       ├── memes\
│       │   ├── lost_in_scroll.png.meta.json
│       │   └── syntax_rage.png.meta.json
│       └── audio\
│           └── soft_chime.wav.meta.json
├── 02_brand_positioning\
│   ├── positioning_matrix.md
│   └── dual_track_branding_guide.md
├── 03_commercial_strategy\
│   └── commercial_strategy.md
├── 04_gtm_launch_playbook\
│   ├── product_hunt_launch_kit.md
│   ├── show_hn_launch_kit.md
│   ├── viral_video_playbook.md
│   └── post_launch_30day_checklist.md
├── tests\
│   ├── test_e2e_strategy_package.py
│   └── validate_schemas.py
├── SUMMARY.md
└── TEST_READY.md
```
