# Vihara 🪞 (Becoming a Bihari)

> *"The tool is a mirror, not a judge. When a reaction meme perfectly captures your current state in real time, the sudden moment of recognition breaks your trance. In that microsecond of laughter, identification falls away, and you return to witnessing consciousness and bliss."*

**Vihara** (also known in its viral consumer edition as **Becoming a Bihari**) is a privacy-first, desktop mindfulness mirror for Windows 11.

Traditional productivity tools act like judgmental wardens: they block websites, log screen time, and trigger shame. **Vihara takes the opposite approach: compassionate metacognition through humor.** It detects your behavioral and emotional state from typing velocity, window context, and screen cues, surfacing wordless visual reaction memes paired with punchy, in-the-moment reflections under 40 characters.

---

## 🎭 Dual-Track Experience

Vihara ships with two interchangeable brand personalities that share the exact same privacy-first engine:

| Track | Name | Persona | Tone & Voice |
| :--- | :--- | :--- | :--- |
| **Track A (Viral / Consumer)** | **Becoming a Bihari** | *The Savage Mindfulness Mirror* | Irreverent, witty, affectionate roasts that pierce through procrastination. |
| **Track B (Professional / Mindful)** | **Vihara** | *The Mindful Focus Catalyst* | Calm, stoic, grounded observations designed for deep work and sustainable flow. |

You can switch between tracks at any time directly from the system tray menu.

---

## ✨ Key Features

- **🔒 Absolute Privacy First** — Zero keylogging. The keyboard listener only tracks numerical velocity metrics (characters per minute, backspace error spikes). Passwords, banking, checkouts, and sensitive credentials are masked in volatile RAM before classification.
- **🛡️ Active Flow State Protection** — When you are in genuine flow (typing velocity >50 chars/min with <8% error rate), all notifications and popups are **100% suppressed**. Your deep work is sacred and never interrupted.
- **🎯 Emotional Resonance & Precision** — Detects deep browsing trances (e.g. YouTube rabbit holes), syntax rage in code editors, afternoon drift, and post-meeting exhaustion to serve memes that match your exact emotional state.
- **🔄 Zero-Repetition Engine** — Reinforced by a **60-event sliding window LRU cache**. Even across long sessions, you won't see repetitive reaction memes.
- **📦 Extensible `.lucidpack` Architecture** — Ships with a default curated pack of **120 unique reaction images** (10 for each of the 12 vibes) verified with unique cryptographic SHA-256 hashes. Supports hot-reloading custom community packs by dropping `.lucidpack` files into the packs directory.
- **👁️ Lightweight Screen Context** — Native Windows Media OCR (<30ms) extracts in-the-moment video titles and feed topics without sending pixels or text to any cloud servers.
- **🧠 Hybrid Deterministic & AI Inference** — Zero-CPU deterministic rule engine paired with an optional on-device decision model for ambiguous states.

---

## 4 Categories × 12 Vibes

| Category | Canonical Vibe | Internal Name | Reflection Flavor |
| :--- | :--- | :--- | :--- |
| 🔥 **Intensity** | `FLOW_STATE` | `in-the-zone` | *Suppressed to protect deep focus* |
| | `GRINDING` | `the-long-grind` | Hour after hour, line after line |
| | `BURNOUT_APPROACHING` | `running-on-fumes` | Hydration check / take a breath |
| 😤 **Frustration** | `SYNTAX_RAGE` | `fighting-the-code` | Staring at code like it owes you an apology |
| | `HELP_SEEKING` | `asking-the-internet` | Consulting the sacred scrolls |
| | `MOUNTING_FRICTION` | `mounting-friction` | It is putting up a fight today |
| 😴 **Avoidance** | `WANDERING` | `just-wandering` | Taking a scenic detour |
| | `LOST_IN_SCROLL` | `lost-in-the-scroll` | Essential research: `{subject}` |
| | `TAB_BUTTERFLY` | `tab-butterfly` | Bouncing between 10 different tabs |
| ☕ **Downtime** | `STILLNESS` | `the-great-pause` | The screen waits. So does everything else. |
| | `MEETING_RECOVERY` | `post-meeting-recovery` | Survived another meeting |
| | `AFTERNOON_DRIFT` | `afternoon-drift` | Drifting on low battery |

---

## 🚀 Quick Start

### Option 1: Run from Source (Developers)

```bash
# Clone the repository
git clone https://github.com/your-username/vihara.git
cd vihara

# Install dependencies
pip install -r requirements.txt

# Launch the app
python -m bihari
```

Look for the **🪞** icon in your Windows system tray. Right-click for options:
- **Pause / Resume**
- **Toggle Brand Track** (Vihara ↔ Becoming a Bihari)
- **Show Test Reflection**
- **Open Meme Pack Folder**
- **Quit**

### Option 2: Build the Standalone Windows Installer

To produce a single-click installer (`.exe`) that non-technical users can install without Python or terminal setup:

```cmd
# Run the automated build script (requires Inno Setup 6)
build.bat
```

This compiles a standalone PyInstaller distribution into `dist/vihara/` and packages it with Inno Setup into a zero-UAC installer inside `dist/installer/`.

---

## 🧪 Testing

The repository includes a comprehensive automated test suite covering detection heuristics, meme deduplication, reflection clamping, schema validation, and 8-hour stability simulations:

```bash
# Run all tests (189 tests across app and strategy suites)
python -m unittest discover -s tests -p "test_*.py"
```

---

## ⚙️ Configuration

Customize behavior in `config.toml` in the project root:

```toml
[general]
brand_track = "vihara"            # "vihara" (mindful) or "bihari" (savage roasts)
poll_interval_ms = 500
meme_cooldown_seconds = 300       # Work session cooldown (5 minutes)
social_cooldown_seconds = 60      # Social/video trance cooldown (1 minute)

[privacy]
blocked_apps = ["KeePassXC.exe", "1Password.exe", "Bitwarden.exe"]
blocked_title_keywords = ["bank", "sign in", "login", "password", "checkout", "payment"]

[display]
duration_ms = 4000                # Toast duration (pauses on hover)
width = 380
height = 320
slide_animation = true

[packs]
active_pack = "default"
auto_reload = true
```

---

## 🏛️ System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│  UI Layer (Tkinter Mainloop)                                           │
│  └── MemeOverlay: Sliding corner toast + modal inspection dialog       │
├────────────────────────────────────────────────────────────────────────┤
│  Platform Abstraction Layer (bihari/pal/)                              │
│  ├── Win32HookMonitor: Low-overhead OS foreground events (<0.05% CPU)  │
│  └── KeyboardTracker: pynput keystroke velocity (Zero Keylogging)      │
├────────────────────────────────────────────────────────────────────────┤
│  Privacy & Context Filter (privacy.py, context.py)                     │
│  └── Mask sensitive credentials + extract active work/leisure topic    │
├────────────────────────────────────────────────────────────────────────┤
│  Inference & Reflection Engine (inference.py)                          │
│  ├── Flow State Shield: Suppresses alerts during high-velocity work   │
│  └── Vibe Classifier: 12 vibes + contextual captions (<40 chars)       │
├────────────────────────────────────────────────────────────────────────┤
│  Pack Engine (packs.py, memes.py)                                      │
│  └── .lucidpack loader + 60-event LRU deduplication window             │
├────────────────────────────────────────────────────────────────────────┤
│  System Tray Service (tray.py)                                         │
│  └── Background tray icon + brand toggle + hotkey controls             │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
