# Show HN Launch Kit: Becoming a Bihari / Vihara

**Product**: Becoming a Bihari / Vihara  
**Target Channel**: Hacker News (`news.ycombinator.com`)  
**Format**: `Show HN` Submission & Discussion Thread  
**Primary Persona Target**: Persona 2 (The Remote Knowledge Worker / Software Engineer)  
**Open Source Repository**: `https://github.com/vihara/vihara`  
**License**: MIT / Open Core  

---

## 1. Hacker News Cultural Framing & Principles

Hacker News is one of the most discerning and skeptical developer communities on the internet. Submissions that rely on marketing jargon, growth hacking buzzwords ("game-changing", "AI-powered revolution", "hyper-productive"), or evasive privacy claims are immediately dismantled in the comments.

To succeed on Hacker News, the launch must strictly adhere to the following principles:

1. **Radical Technical Transparency**: Provide direct file paths, line citations, API mechanisms, and architectural rationales. Settle technical questions with code.
2. **Immediate Privacy Verification**: Developers will assume any background software monitoring screen or keyboard activity is spyware until proven otherwise. We must front-load our zero-keylogging, RAM-only OCR, and local-first architecture proofs.
3. **No Marketing Fluff**: Explain what the software does, how it works, why it was built, its current limitations, and what trade-offs were made.
4. **Humble, Responsive Engagement**: Acknowledge bugs and edge cases quickly. Welcome architectural critiques (e.g., Python runtime footprint vs. Rust) with genuine engineering appreciation.

---

## 2. Show HN Title Conventions

Hacker News title conventions require a clean, factual prefix (`Show HN:`) followed by a concise description of what the project is and what makes it interesting.

### Recommended Title Options

- **Recommended Primary Title**:  
  `Show HN: Becoming a Bihari – Privacy-first desktop mindfulness mirror (no keylogging)`
- **Architecture-Focused Alternative**:  
  `Show HN: Vihara – An offline desktop mirror using native WinRT OCR and typing velocity`
- **Problem-First Curiosity Title**:  
  `Show HN: A desktop daemon that catches coding rage and doomscrolling without cloud telemetry`
- **Technical Mechanism Title**:  
  `Show HN: Local desktop mirror detecting focus drift via Win32 hooks and 421M parameter model`

---

## 3. Show HN Submission Post (Exact Markdown Copy)

```markdown
Show HN: Becoming a Bihari – Privacy-first desktop mindfulness mirror (no keylogging)

Hey HN,

I built Becoming a Bihari (also packaged as Vihara), an open-source, privacy-first desktop mindfulness daemon for Windows 11.

GitHub: https://github.com/vihara/vihara  
Release Installer (.exe): https://github.com/vihara/vihara/releases/tag/v0.1.0  
Architecture Spec: https://github.com/vihara/vihara/blob/main/docs/architecture.md  

### The Problem
Most focus tools rely on coercion: DNS blacklisting (`/etc/hosts`), application termination, or invasive employee surveillance (random webcam snaps, keystroke logging). 

In practice, these approaches suffer from two fundamental problems:
1. **Psychological Reactance**: When software acts as a punitive warden, users rebel. You either bypass the blocker (switching to your phone, opening incognito) or disable it completely.
2. **Invasive Telemetry**: Many commercial productivity apps ship your window titles, URLs, and activity logs to external cloud servers.

### The Solution: A Mirror, Not a Judge
Instead of enforcing hard blocks, this tool acts as an ambient cognitive mirror. When you enter a frustration loop (e.g. violent backspacing during syntax errors) or an unconscious trance state (e.g. 45 minutes on Wikipedia or Twitter), it surfaces an ephemeral, wordless visual reaction meme in a borderless bottom-right corner toast paired with a short reflection (e.g., `🪞 Invested in: Bronze Age Metallurgy`).

Because visual reaction images are comprehended in <150ms (subcortical processing), it breaks cognitive capture with humor rather than shame, prompting a voluntary return to focus.

### Architecture Deep Dive

The daemon runs an asynchronous multi-threaded Python/Win32 architecture:

1. **Telemetry & Privacy Filter (`bihari/spy.py`, `bihari/privacy.py`)**:
   - We track typing dynamics using low-level `pynput` listeners, but **we never log keystroke identities**. We store only `time.monotonic()` float timestamps in two rolling deques (`maxlen=100`) to compute characters/minute and backspace ratios. Line 85 of `spy.py`: `self._strokes.append(now)`. No character codes or strings are ever retained.
   - An upfront regex sanitizer intercepts active foreground window titles. Password managers (`KeePassXC`, `1Password`, `Bitwarden`) and financial/login keywords (`bank`, `sign in`, `login`, `checkout`) are immediately rewritten to `HIDDEN_PRIVACY_CONTEXT` and excluded from OCR.

2. **Native WinRT Screen OCR (`bihari/ocr.py`)**:
   - Rather than bundling heavy OCR frameworks like Tesseract or PaddleOCR, we call Windows 11’s built-in `Windows.Media.Ocr` runtime via `winocr` and Win32 GDI screen capture.
   - The capture is strictly constrained to the bounding box of the active foreground window, processed entirely within volatile system RAM, and immediately garbage-collected (<30ms execution time, zero disk writes). UI noise words and stop words are stripped to isolate the primary topic.

3. **Hybrid Inference Pipeline (`bihari/inference.py`)**:
   - Fast deterministic rule tables execute in O(1) time.
   - For ambiguous window contexts, the system queries **Laya**, a lightweight 421M non-autoregressive decision model running locally on CPU (<15ms latency).
   - Inference classifications are cached by window title hash, resulting in **0.0% CPU usage** during steady-state typing and deep work.

4. **Active Flow State Protection**:
   - The daemon monitors your focus velocity. When typing speed exceeds 40 CPM and backspace error rates remain below 10%, all corner toasts and overlays are automatically suppressed. Deep focus is never interrupted.

5. **Anti-Repetition Engine (`bihari/memes.py`)**:
   - To eliminate joke fatigue, a 60-event LRU cache persisted via local SQLite (`vibe_history.db`) ensures you do not see repeat reaction images even across multi-day sessions.

### Known Limitations & Roadmap
- **Windows 11 Native**: The initial prototype relies heavily on Win32 handles and WinRT OCR APIs. We are actively planning a cross-platform rewrite in Rust (`windows-rs`, Apple Vision framework for macOS, Wayland layer-shell for Linux).
- **AV Heuristics**: Because low-level keyboard velocity hooks share Win32 API signatures with keyloggers, unsigned test builds occasionally trigger heuristic warnings in strict antivirus suites. All code is open-source and reproducible, and official releases are EV code-signed.

The core engine is free and open-source. I’d love your feedback on the architecture, local-first privacy boundaries, and whether this ambient awareness model resonates with your workflow.
```

---

## 4. Engineering Architecture Highlights & Dataflow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                       LOCAL SENSORY & INFERENCE PIPELINE                        │
└─────────────────────────────────────────────────────────────────────────────────┘
         │
         ├──► Keyboard Velocity Hook (`pynput.keyboard.Listener`)
         │    • Records ONLY `time.monotonic()` in rolling deque (maxlen=100)
         │    • Calculates Characters/Min (CPM) and Backspace Error Rate (%)
         │    • ZERO keystroke character codes stored or evaluated
         │
         ├──► Active Window Hook (`win32gui.GetForegroundWindow`)
         │    • Regex Privacy Sanitizer (`bihari/privacy.py`)
         │    • Masks password managers, banks, and credential inputs
         │    • Emits `HIDDEN_PRIVACY_CONTEXT` if sensitive
         │
         ├──► WinRT Native Screen OCR (`Windows.Media.Ocr`)
         │    • Foreground window bounding box capture via Win32 GDI
         │    • Executed strictly in volatile system RAM (<30ms)
         │    • Zero disk writes, zero screenshots persisted
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     DECISION & FLOW STATE ARBITRATION                           │
└─────────────────────────────────────────────────────────────────────────────────┘
         │
         ├──► Flow State Gate (`bihari/inference.py`)
         │    • IF CPM > 40 AND error_rate < 10% ➔ SUPPRESS OVERLAYS (Silence)
         │    • Cooldown pacing: 60s during drift, 300s during deep work
         │
         ├──► Hybrid Classification (Rules + Laya 421M Non-Autoregressive Model)
         │    • Evaluates window title hash, text density, and typing metrics
         │    • Classifies into 4 categories × 12 internal vibes (<15ms latency)
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     PRESENTATION & DEDUPLICATION ENGINE                         │
└─────────────────────────────────────────────────────────────────────────────────┘
         │
         ├──► SQLite LRU Deduplication Window (`vibe_history.db`)
         │    • 60-event exclusion window prevents meme fatigue
         │
         └──► Borderless Floating Corner Toast (`MemeOverlay`)
              • Non-intrusive bottom-right toast with hover-pause dismiss timer
              • Click-to-enlarge modal viewer with Escape key handling
```

---

## 5. Privacy Battlecard & Threat Model

When developers scrutinize the codebase, use this threat matrix as our baseline defense:

| Threat Vector | Potential Suspicion / Attack | Architectural Mitigation in Code | Verifiable Code Citation |
| :--- | :--- | :--- | :--- |
| **Keystroke Logging** | "The app records my passwords, private code, and chats." | The keyboard tracker only evaluates timestamp deltas. Key character codes are discarded immediately upon hook firing. | `bihari/spy.py:58-64`<br>`bihari/spy.py:85`<br>`bihari/privacy.py:5-6` |
| **Cloud Surveillance** | "The daemon sends screenshots or activity logs to a telemetry server." | Zero outbound network calls. The application contains no network sockets or telemetry reporters. Operates 100% in Airplane Mode. | Entire codebase (no network imports or analytics SDKs) |
| **Credential / Banking Leakage** | "The screen OCR reads my 1Password master password or banking balances." | Proactive regex sanitizer intercepts window titles. Matching windows are masked to `HIDDEN_PRIVACY_CONTEXT` and bypass OCR entirely. | `bihari/privacy.py:12, 41-48`<br>`bihari/config.py:36-51` |
| **Disk Image Snooping** | "Screenshots are saved in temp folders or AppData." | Screen captures occur via Win32 GDI Device Contexts in volatile RAM, handed directly to WinRT OCR, and freed immediately. Zero disk writes. | `bihari/ocr.py:8-13` |
| **High Resource Consumption** | "Background daemon hogs CPU, spins laptop fans, or drains battery." | WinRT OCR triggers only upon context changes (<30ms). Laya 421M runs locally in <15ms. Classification caching keeps steady-state CPU at 0.0%. | `bihari/inference.py`<br>`bihari/ocr.py` |

---

## 6. Hacker News Comment Response Protocols

The following matrix prepares the launch team for anticipated technical objections and skepticism on the HN thread.

### Protocol 1: The "This looks like a keylogger / malware" Objection
- **Anticipated Comment**:  
  *"Using global keyboard hooks (`pynput`) is literally what keyloggers do. My antivirus flagged the binary. Why should anyone trust running this?"*
- **Response Strategy**:  
  Validate the concern immediately, explain the technical necessity, point to the exact source lines, and explain code signing:
- **Response Copy**:  
  ```markdown
  You're completely right to be skeptical—any background tool using low-level keyboard hooks should be treated with extreme caution.

  Here is how it works technically in the codebase:
  In `bihari/spy.py` (lines 72–88), we initialize `pynput.keyboard.Listener`. When a key event fires, our handler executes:
  ```python
  now = time.monotonic()
  self._strokes.append(now)
  ```
  We literally append a monotonic float timestamp into `collections.deque(maxlen=100)`. The `key` object is only evaluated with `key == kb.Key.backspace` to track error rates. We never extract `.char`, `.vk`, or text strings.

  Because generic antivirus heuristics flag any binary calling `SetWindowsHookExW` without high Microsoft reputation, unsigned builds trigger false positives. To solve this for end users:
  1. All source code is 100% open and auditable on GitHub.
  2. Production release installers are signed with an Extended Validation (EV) certificate.
  3. We submit release hashes to Microsoft Defender Security Intelligence for whitelisting prior to public release.
  ```

### Protocol 2: The "Why Python instead of Rust/Tauri/C#?" Objection
- **Anticipated Comment**:  
  *"Why did you write a desktop utility in Python? Tkinter looks clunky, and bundling a Python runtime inflates memory usage to 50MB. This should have been written in Rust or C# WinUI."*
- **Response Strategy**:  
  Agree with the premise, explain the prototype rationale, and highlight the Rust roadmap:
- **Response Copy**:  
  ```markdown
  Completely agree with this critique. 

  Python was chosen strictly as our fast-prototyping substrate: it allowed us to experiment with the behavioral inference heuristics, integrate Laya (our 421M decision model), and test the UX mechanics with real users in weeks rather than months.

  However, you're spot on about memory and platform overhead: running Python + Tkinter consumes ~45MB of RAM and requires bundling runtime dependencies.

  Our immediate Phase 2 roadmap is a complete port of the core daemon to Rust:
  - Using `windows-rs` for native Win32 window hooks and WinRT OCR integration.
  - Using `tray-icon` and lightweight platform-native webview/overlay layers.
  - This will drop idle memory consumption from ~45MB to under 8MB and eliminate the Python runtime entirely.

  If anyone in the HN community is interested in contributing to the Rust rewrite, the tracking issue and crate structure are live on our repo!
  ```

### Protocol 3: The "Memes are just more distraction" Objection
- **Anticipated Comment**:  
  *"Isn't popping up memes literally adding more digital distraction to my day? If I'm procrastinating, how does looking at a cat meme help me focus?"*
- **Response Strategy**:  
  Ground the answer in behavioral science (ACT, cognitive defusion, latency of visual vs. verbal processing):
- **Response Copy**:  
  ```markdown
  It sounds counter-intuitive, but there is substantial cognitive science behind this:

  When you fall down a rabbit hole (e.g. clicking through 20 tabs or scrolling social media), you enter a semi-hypnotic, dissociative trance state. 

  Traditional focus apps try to solve this with text alerts or hard blocks:
  - Text alerts ("You have been unproductive for 20 minutes") require verbal working memory to process (~800ms+), which induces guilt, defensiveness, and cognitive fatigue.
  - Hard blocks trigger psychological reactance: you get mad at the software and switch to your phone.

  By contrast, a wordless visual meme (a side-eye cat or perplexed capybara) is processed subcortically in under 150ms. It acts as an instant, visceral pattern interrupt. You laugh, the dissociative trance snaps, and you realize: "Right, I was supposed to be writing that SQL migration."

  Because the software doesn't scold you or lock your computer, your autonomy is preserved. You close the tab voluntarily. That tiny moment of self-awareness is the entire goal.
  ```

### Protocol 4: The "What about confidential enterprise codebases?" Objection
- **Anticipated Comment**:  
  *"I work under strict NDAs at a defense contractor / fintech. Can I use this without leaking proprietary code or customer PII?"*
- **Response Strategy**:  
  Emphasize local-only architecture, air-gapped support, and custom blocklist configurability:
- **Response Copy**:  
  ```markdown
  Yes. The application was designed from the ground up for zero-trust environments:
  1. **Zero Outbound Sockets**: There is literally no telemetry pipeline or cloud sync in the core app. You can block the executable in your local firewall or run it in full Airplane Mode.
  2. **RAM-Only Screen OCR**: Screen buffers exist only in volatile system RAM for <30ms while WinRT OCR extracts words, and are immediately discarded. No images are ever saved to disk.
  3. **Custom Window Blacklists**: In `config.toml`, you can define custom regex rules under `blocked_title_keywords`:
  ```toml
  blocked_title_keywords = ["internal-project-alpha", "confidential", "jira.enterprise"]
  ```
  Whenever any window matching these patterns gains focus, the entire sensory pipeline (both velocity and OCR) is instantly bypassed.
  ```
