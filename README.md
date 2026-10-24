# Vihara 🪞

> *"The tool is a mirror, not a judge."*

**Vihara** is an open-source, privacy-first desktop mirror and mindfulness catalyst for people who do lonely computer work.

When you spend long hours alone in front of a screen:
1. You hit friction (syntax errors, writer's block, fatigue) and unconsciously slide into rabbit holes or doomscrolling.
2. Nobody is around to notice, so minutes slip into hours.

Traditional productivity tools try to solve this with coercion: blocking websites, locking your screen, or assigning judgmental productivity scores. But when software tries to parent you, you rebel—opening incognito, switching to your phone, or uninstalling the blocker.

**Vihara takes the opposite approach: compassionate metacognition through humor and quiet presence.**

Running unobtrusively in your Windows system tray, Vihara observes local typing dynamics and active window context. When you are in genuine flow, it stays 100% silent. But when you have been slamming backspace in a syntax rage or wandering into an unplanned 3 AM rabbit hole, a subtle, elegant corner toast slides in with a fitting visual reaction and an empathetic reflection.

You smile. The hypnotic trance snaps. You close the tab on your own terms.

---

## 🧠 Dual-Tier On-Device Intelligence

Vihara operates without any cloud dependencies, telemetry servers, or account logins. Its semantic perception engine runs entirely locally using a calibrated dual-tier inference architecture:

```
                  ┌───────────────────────────────────────────────┐
                  │          Active Window / Telemetry            │
                  └──────────────────────┬────────────────────────┘
                                         │
                    Is Active Work & Dwell < 5 min?
                                    /         \
                             [YES] /           \ [NO]
                                  ▼             ▼
                     Defer to ML Classifier    Deterministic Rules Engine
                                  │             (Regex, App Titles, Velocity)
                                  │                      │
                                  ├──────────────────────┘
                                  ▼
                     ┌─────────────────────────┐
                     │ Option B: ONNXBrain     │  all-MiniLM-L6-v2 (21.9 MB)
                     │ (Semantic Transformer)  │  Cosine Vibe Centroid Anchors
                     └────────────┬────────────┘
                                  │ (Fallback if onnxruntime unavailable)
                                  ▼
                     ┌─────────────────────────┐
                     │ Option A: MicroBrain    │  Linear Feature Classifier (<500 KB)
                     │ (Zero-Dep Classifier)   │  Pure Python, 0% CPU, Instant
                     └────────────┬────────────┘
                                  │
                                  ▼
                     ┌─────────────────────────┐
                     │ Final Calibrated Vibe   │  (12 Behavioral Archetypes)
                     └─────────────────────────┘
```

1. **Option B (Primary) — Quantized MiniLM-L6 ONNX Semantic Brain (`bihari.onnx_brain`)**:
   - Embeds window headers, terminal process names, and volatile screen titles into a 384-dimensional semantic manifold in ~10–15ms.
   - Computes cosine similarity against multi-prototype vibe anchors across 12 behavioral archetypes.
   - Bundles a pure-Python fallback WordPiece tokenizer for zero external wheel dependencies.
2. **Option A (Instant Fallback) — MicroBrain 2.0 (`bihari.micro_model`)**:
   - An ultra-compact (<500 KB) sparse linear classifier trained directly on workspace interactions.
   - Pure Python with 0% idle CPU and zero external library requirements.
3. **Deterministic Rules & Telemetry Fusion**:
   - Fast paths for unambiguous developer tools (PowerShell, Windows Terminal, VS Code, Git).
   - Social media guardrails that distinguish technical learning posts from mindless scrolling.

---

## 🔄 Autonomous Meme Management & Zero Fatigue

- **Lightweight Distribution (~20–25 MB)**: Heavy static packs (previously 94 MB) have been decoupled. The binary ships ultra-lean.
- **Autonomous Startup Seeding**: On first run and during low-inventory states, Vihara automatically seeds high-relevance visual reactions in the background from curated subreddits (`r/reactionpics`, `r/wholesomememes`, `r/rarepuppers`, `r/oddlysatisfying`, `r/wunkus`, etc.).
- **Rolling Ring Buffer Disk Purge**: To keep local disk usage bounded (<15–20 MB), Vihara retains only the 10 most recent seen meme files on disk (`max_seen_history_files = 10`), automatically purging older local image files while tracking their history in SQLite.
- **Lifetime Zero-Repeat with Natural Cool-Off**: Every displayed meme's SHA-256 visual hash and ID are recorded in SQLite (`vibe_history.db`). By default, a 30-day cool-off window (`repeat_cooloff_days = 30`) allows memes to naturally re-enter rotation after a month, ensuring you never see repeated jokes in the same season without infinite storage bloat.

---

## 🔒 Radical Privacy Guarantees

Desktop focus tools require absolute honesty regarding what they touch:

- **Zero Keylogging**: The keyboard velocity tracker (`bihari/spy.py`) records **only monotonic timestamps** (`time.monotonic()`) in rolling 30-second sliding windows. Key characters, text strings, and virtual keycodes are never captured, logged, or saved.
- **Active Flow State Sacredness**: When typing velocity exceeds 40 CPM with low error rates, or during deep terminal and coding sessions, all notifications are completely muted.
- **Volatile Screen Context (<30ms)**: When video or social feed titles are obscured or generic, native Windows Media OCR (`Windows.Media.Ocr`) inspects only the top header region in volatile RAM. No screenshots are saved to disk or transmitted over the wire.
- **100% Offline / Airplane Mode Ready**: No telemetry beacons, analytics trackers, or external API requirements.

---

## 4 Categories × 12 Behavioral Archetypes

| Category | Archetype | Trigger Conditions | Mirror Behavior |
| :--- | :--- | :--- | :--- |
| 🔥 **Intensity** | `FLOW_STATE` | Sustained keystrokes, terminal commands, active coding | **Muted.** Deep work is never disturbed. |
| | `GRINDING` | Continuous high-velocity typing across extended sessions | Acknowledges the sustained grit. |
| | `BURNOUT_APPROACHING` | Extended continuous hours, erratic cadence | Gently suggests water, stretching, or stepping back. |
| 😤 **Frustration** | `SYNTAX_RAGE` | Rapid backspace bursts, rewriting identical lines | Intervenes before frustration breaks the flow. |
| | `HELP_SEEKING` | Rapid browsing across Stack Overflow, documentation | Validates the search for answers. |
| | `MOUNTING_FRICTION` | Frantic app cycling (>15 window switches/min) | Highlights restlessness with warmth. |
| 😴 **Avoidance** | `WANDERING` | Drifting from developer tools to Wikipedia/articles | Mirrors the scenic route taken. |
| | `LOST_IN_SCROLL` | Sustained dwell on algorithmic feeds or video feeds | Pulls subject into context: *"Invested in: {subject}"*. |
| | `TAB_BUTTERFLY` | Rapid cycling across 30+ browser tabs | Surfaces the scatter before minutes turn to hours. |
| ☕ **Downtime** | `STILLNESS` | Idle desktop, hands off keyboard | Respects the pause—epiphany or rest. |
| | `MEETING_RECOVERY` | Post-Zoom/Teams blank stare | Gives executive faculties space to decompress. |
| | `AFTERNOON_DRIFT` | 2:30 PM circadian slump | Normalizes the natural biological dip. |

---

## 🚀 Quick Start

### Option 1: Standalone Windows App (No Python Required)

1. Download the latest standalone release archive from the [Releases](https://github.com/raushan-cmd-RAJ/becoming-a-bihari/releases) page.
2. Extract and launch `vihara.exe`.
3. Vihara will quietly appear in your Windows system tray (**🪞** / **V**).

> [!NOTE]
> **Windows SmartScreen**: Because Vihara is an independent open-source project without a paid corporate EV certificate, Windows SmartScreen may show an "Unrecognized app" prompt on initial launch. Click **More info → Run anyway**. You can inspect and build every line of source code yourself.

### Option 2: Run from Source (Developers)

Requires Python 3.10+ on Windows 10/11:

```bash
# Clone the repository
git clone https://github.com/raushan-cmd-RAJ/becoming-a-bihari.git
cd becoming-a-bihari

# Install dependencies
pip install -r requirements.txt

# Run the application
python -m bihari
```

Right-click the tray icon to:
- **Show Test Reflection**: Test the current toast overlay and vibe classification.
- **Open Meme Folder**: Access or customize the local meme cache.
- **Refresh Memes**: Trigger immediate background replenishment.
- **Pause / Resume**: Temporarily suspend or reactivate notifications.
- **Quit**: Gracefully exit the background daemon.

---

## ⚙️ Configuration (`config.toml`)

Customize Vihara's behavior via `config.toml`:

```toml
[general]
poll_interval_ms = 500
idle_timeout_seconds = 180
repeat_cooloff_days = 30        # Memes can re-enter rotation after 30 days
max_seen_history_files = 10     # Keep disk usage under ~15MB

[inference]
use_onnx = true                 # Enable Option B: MiniLM semantic brain
use_micro_model = true          # Enable Option A: MicroBrain fallback
semantic_threshold = 0.40

[privacy]
blocked_apps = ["keepass.exe", "1password.exe", "bitwarden.exe"]
blocked_title_keywords = ["bank", "password", "confidential", "inbox"]

[display]
duration_ms = 7000
width = 380
height = 340
opacity = 0.94
```

---

## 🧪 Testing

Run the full automated test suite (verifying detection heuristics, ONNX inference, MicroBrain fallback, zero-repeat mechanics, and privacy filters):

```bash
pytest tests/
```

---

## 📄 License

MIT License — free and open source. Built with care for anyone working long hours at a screen.
