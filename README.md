# Vihara 🪞 (Becoming a Bihari)

> *"The tool is a mirror, not a judge."*

**Vihara** is an open-source, privacy-first desktop mirror for people who do lonely computer work.

When you spend hours alone in front of a screen, two things consistently happen:
1. You hit friction (syntax errors, writer's block, fatigue) and unconsciously slide into rabbit holes or doomscrolling.
2. Nobody is around to notice, so minutes turn into hours.

Traditional productivity apps try to solve this with coercion: blocking websites, locking your screen, or logging your hours with judgmental productivity scores. But when software tries to parent you, you rebel—you open incognito, switch to your phone, or uninstall the blocker.

**Vihara takes the opposite approach: compassionate metacognition through humor.**

It runs quietly in your Windows system tray. It watches typing dynamics and active window context locally. When you're in genuine flow, it stays 100% silent. But when you've been slamming backspace for 20 minutes or falling down a 3 AM rabbit hole about ancient metallurgy, an unobtrusive corner toast slides in with a visual reaction meme and a punchy observation.

You laugh. The hypnotic trance snaps. You close the tab on your own terms.

---

## 🎭 Two Personalities, One Engine

People need different mirrors on different days. You can hot-swap between two brand tracks at any time with a single click in the system tray:

| Track | Name | Persona | What It Feels Like |
| :--- | :--- | :--- | :--- |
| **Track A** | **Becoming a Bihari** | *The Savage Mirror* | Unfiltered, witty, affectionate roasts that pierce straight through procrastination. |
| **Track B** | **Vihara** | *The Mindful Catalyst* | Stoic, dignified, calm observations designed for deep knowledge work and quiet presence. |

---

## 🔒 How It Actually Works (Pragmatic & Transparent)

We believe desktop utilities that monitor focus must be radically honest about what they do and don't touch.

- **Zero Keylogging**: The keyboard listener (`bihari/spy.py`) records **only timestamps** (`time.monotonic()`) in rolling buffers to calculate typing velocity (characters per minute) and backspace error spikes. No characters, strings, or virtual keys are ever inspected, saved, or logged.
- **Active Flow State Protection**: When you are in genuine flow (typing velocity >40 CPM with low error rates), all notifications and toasts are **completely suppressed**. Focus is sacred.
- **Volatile Screen Context (<30ms)**: When window titles are ambiguous during video or social browsing, native Windows Media OCR (`Windows.Media.Ocr`) reads the active window header in volatile system RAM to extract the topic. Zero disk writes, zero screenshots saved, zero cloud calls.
- **Zero Cloud / Fully Offline**: No telemetry servers, no analytics beacons, no tracking. Operates 100% in Airplane Mode.
- **Deterministic & Lightweight**: Powered by deterministic rule matching cached by window context. Consumes **0.0% CPU** during steady-state work and ~45MB RAM.
- **No Repeated Jokes**: A local SQLite LRU window (`vibe_history.db`) prevents meme fatigue so you don't see the same reaction twice in a row.

---

## 4 Categories × 12 Behavioral Vibes

| Category | State | What Triggered It | What the Mirror Does |
| :--- | :--- | :--- | :--- |
| 🔥 **Intensity** | `FLOW_STATE` | Sustained typing, low errors | **Muted.** Deep work is never interrupted. |
| | `GRINDING` | Hours of continuous keystrokes | Acknowledges the sustained grit. |
| | `BURNOUT_APPROACHING` | Erratic cadence, long sessions | Suggests water, breathing, or stepping away. |
| 😤 **Frustration** | `SYNTAX_RAGE` | Rapid backspace bursts, rewriting lines | Catches the fight before you break the keyboard. |
| | `HELP_SEEKING` | Stack Overflow tab #12, docs hopping | Gently observes the pilgrimage for answers. |
| | `MOUNTING_FRICTION` | 20 window switches in 60 seconds | Points out the restlessness with warmth. |
| 😴 **Avoidance** | `WANDERING` | Detour from editor to Wikipedia/articles | Mirrors the scenic route you took. |
| | `LOST_IN_SCROLL` | Long dwell on Reddit, YouTube, feeds | Surfaces the topic: *"Invested in: {subject}"*. |
| | `TAB_BUTTERFLY` | 40+ browser tabs cycling frantically | *"Can't decide where to be? Same."* |
| ☕ **Downtime** | `STILLNESS` | Hands off keyboard, desktop idle | Respects the pause—epiphany or rest. |
| | `MEETING_RECOVERY` | Post-Zoom/Teams blank stare | Gives executive faculties space to decompress. |
| | `AFTERNOON_DRIFT` | 2:30 PM post-lunch slump | Normalizes the biological circadian dip. |

---

## 🚀 Quick Start

### Option 1: Standalone Installer (Recommended)

1. Grab the latest installer (`.exe`) from the [Releases](https://github.com/raushan-cmd-RAJ/becoming-a-bihari/releases) page.
2. Run the installer and launch the app.
3. Look for the **🪞** (or **V** / **B**) icon in your Windows system tray.

> [!NOTE]
> **Windows SmartScreen Note**: Because this is an independent open-source project without an expensive corporate EV certificate, Windows SmartScreen may show an "Unrecognized app" prompt on first launch. Click **More info → Run anyway**. You can inspect every single line of source code right here in the repository.

### Option 2: Run from Source (Developers)

Requires Python 3.10+ on Windows 10/11:

```bash
# Clone the repository
git clone https://github.com/raushan-cmd-RAJ/becoming-a-bihari.git
cd becoming-a-bihari

# Install dependencies
pip install -r requirements.txt

# Run the app
python -m bihari
```

Right-click the tray icon to:
- **Toggle Brand Track** (Becoming a Bihari ↔ Vihara)
- **Show Test Reflection** (verify toast styling)
- **Open Meme Pack Folder** (add your own images)
- **Pause / Resume**

---

## 📦 Custom Meme & Theme Packs

Vihara uses the `.lucidpack` specification. You can customize the entire meme catalog:

1. Right-click the tray icon → **Open Meme Folder**.
2. Drop `.jpg`, `.png`, `.webp`, or animated `.gif` files into any vibe folder (`in-the-zone/`, `fighting-the-code/`, `lost-in-the-scroll/`, etc.).
3. The app hot-reloads them automatically.

---

## ⚠️ Current Status & Honest Limitations

- **Windows 11 Native Only (For Now)**: Uses native Win32 hooks and `Windows.Media.Ocr`. macOS and Linux support are planned, but not built yet.
- **Python Runtime Overhead**: The desktop daemon runs on Python + Tkinter (~45MB RAM). A future Rust port is on the roadmap to bring memory below 10MB.
- **Desktop Focus**: This is a standalone desktop app, not a mobile blocker or browser extension. It's built specifically for desk knowledge work.

---

## 🧪 Tests

The project includes an automated test suite verifying detection heuristics, context parsing, zero-repeat mechanics, and privacy filters:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

---

## 📄 License

MIT License — free and open source. Built with care for anyone working long hours at a screen.
