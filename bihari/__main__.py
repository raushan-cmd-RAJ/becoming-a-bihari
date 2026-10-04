"""
Becoming a Bihari — Main entry point.

Usage:
    python -m bihari
    
This is the orchestrator that wires all 4 modules together:
  1. THE SPY (Telemetry Harvester) — daemon threads
  2. THE INFERENCE BRIDGE (Hybrid classifier) — inference worker thread
  3. THE MEME RETRIEVER (Local meme selector) — called from inference worker
  4. THE DISPLAY ENGINE (Tkinter overlay) — main thread

Threading model:
  - Main thread: tkinter mainloop (required by tk)
  - Thread 1: ForegroundMonitor (win32 polling)
  - Thread 2: pynput keyboard listener
  - Thread 3: Inference worker (queue consumer)
  - Thread 4: pystray system tray icon
  
All threads are daemons. Communication is via queue.Queue.
Display calls are marshalled to main thread via root.after(0, callback).
"""

import os
import sys
import time
import atexit
import logging
import threading
import subprocess
import tkinter as tk
from queue import Queue, Empty
from pathlib import Path

from .config import load_config
from .privacy import PrivacyFilter
from .spy import KeyboardTracker, ForegroundMonitor
from .inference import (
    Vibe,
    VibeResult,
    VibeClassifier,
    get_reflection,
    is_flow_gate_suppressed,
    VIBE_FOLDER_NAMES,
)
from .memes import MemeRetriever
from .packs import PackManager
from .display import MemeOverlay
from .tray import SystemTray, ensure_default_desktop
from .logger import VibeLogger
from .fetcher import seed_in_background, search_live_contextual_meme
from .context import extract_context
from .ocr import ScreenTextExtractor

# ── Logging setup ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("bihari")


def main():
    ensure_default_desktop()

    # ── Load configuration ──
    cfg = load_config()
    current_track = {"value": cfg["general"].get("brand_track", "vihara")}
    active_name = "Vihara" if current_track["value"] == "vihara" else "Becoming a Bihari"

    logger.info("=" * 50)
    logger.info(f"  {active_name} v0.1.0")
    logger.info("  Privacy-first vibe detection & mindfulness mirror")
    logger.info(f"  Brand Track: {current_track['value']}")
    logger.info("=" * 50)

    # ── Initialize Module 1: THE SPY ──
    event_queue: Queue = Queue(maxsize=100)

    privacy = PrivacyFilter(
        blocked_apps=cfg["privacy"]["blocked_apps"],
        blocked_keywords=cfg["privacy"]["blocked_title_keywords"],
    )

    kb_tracker = KeyboardTracker(window_seconds=30)

    monitor = ForegroundMonitor(
        event_queue=event_queue,
        privacy_filter=privacy,
        keyboard_tracker=kb_tracker,
        poll_interval_ms=cfg["general"]["poll_interval_ms"],
        idle_timeout_seconds=cfg["general"]["idle_timeout_seconds"],
    )

    # ── Initialize Module 2: THE INFERENCE BRIDGE ──
    classifier = VibeClassifier(use_laya=cfg["inference"]["use_laya"])

    # ── Paths & SQLite Logger ──
    meme_dir = Path(cfg["paths"]["meme_dir"])
    db_path = meme_dir.parent / "vibe_history.db"
    vibe_logger = VibeLogger(db_path)

    # ── Initialize Module 3: THE PACK MANAGER & MEME RETRIEVER ──
    local_app = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
    packs_dir = Path(local_app) / "Vihara" / "packs"
    bundled_pack = Path(__file__).resolve().parent.parent / "packs" / "default.lucidpack"
    pack_manager = PackManager(
        packs_dir=packs_dir,
        bundled_pack_path=bundled_pack,
        auto_start_watcher=True,
    )

    # Check for CLI pack installation
    if "--install-pack" in sys.argv:
        try:
            pack_idx = sys.argv.index("--install-pack") + 1
            if pack_idx < len(sys.argv):
                installed = pack_manager.install_pack(Path(sys.argv[pack_idx]))
                if installed:
                    logger.info(f"Pack successfully installed via CLI: {installed.name}")
        except Exception as e:
            logger.error(f"Error handling CLI pack installation: {e}")

    retriever = MemeRetriever(
        meme_dir=meme_dir,
        cooldown_seconds=cfg["general"]["meme_cooldown_seconds"],
        history_db=db_path,
        pack_manager=pack_manager,
        never_repeat=cfg.get("general", {}).get("never_repeat", True),
    )

    # Log meme inventory
    counts = retriever.get_meme_count()
    total_memes = sum(counts.values())
    logger.info(f"Meme inventory: {total_memes} total — {counts}")
    if total_memes == 0:
        logger.warning(
            f"No memes found! Add images to subfolders in: {meme_dir}\n"
            f"  See {meme_dir / 'README.txt'} for instructions."
        )

    # ── Online Meme Seeder (if enabled) ──
    fetcher_cfg = cfg.get("fetcher", {})
    if fetcher_cfg.get("online_fetch", False):
        logger.info("Online meme fetcher enabled — checking if seeding is needed...")
        seed_in_background(
            meme_dir=meme_dir,
            min_threshold=fetcher_cfg.get("min_threshold", 3),
            target_count=fetcher_cfg.get("target_count", 10),
            seen_ids=retriever.seen_ids,
        )

    # ── Initialize Module 4: THE DISPLAY ENGINE ──
    root = tk.Tk()
    root.withdraw()  # Hide the root window — we only use Toplevel overlays
    root.title(active_name)

    overlay = MemeOverlay(
        root=root,
        width=cfg["display"]["width"],
        height=cfg["display"]["height"],
        duration_ms=cfg["display"]["duration_ms"],
        opacity=cfg["display"]["opacity"],
        slide_animation=cfg["display"]["slide_animation"],
        brand_track=current_track["value"],
    )

    # ── Pause/resume control ──
    paused = threading.Event()  # When set, inference is paused

    # ── Start Thread 1: Keyboard Listener ──
    from pynput import keyboard as kb

    kb_listener = kb.Listener(on_press=kb_tracker.on_key_press)
    kb_listener.daemon = True
    kb_listener.start()
    logger.info("Keyboard velocity tracker started.")

    # ── Start Thread 2: Foreground Monitor ──
    monitor_thread = threading.Thread(target=monitor.run, name="ForegroundMonitor", daemon=True)
    monitor_thread.start()

    # ── Start Thread 3: System Tray ──
    def handle_pause():
        paused.set()
        logger.info("⏸️  Paused — meme delivery suspended.")

    def handle_resume():
        paused.clear()
        logger.info("▶️  Resumed — meme delivery active.")

    def handle_toggle_track(new_track: str):
        current_track["value"] = new_track
        overlay.brand_track = new_track
        name = "Vihara" if new_track == "vihara" else "Becoming a Bihari"
        root.title(name)
        logger.info(f"🔄 Switched brand track to: {new_track} ({name})")

    def handle_quit():
        logger.info("Quit requested from tray.")
        cleanup()
        os._exit(0)

    def handle_open_memes():
        try:
            os.startfile(str(meme_dir))
        except Exception as e:
            logger.error(f"Failed to open meme folder: {e}")

    def handle_refresh_memes():
        logger.info("Manual meme refresh requested from tray.")
        seed_in_background(
            meme_dir=meme_dir,
            min_threshold=0,
            target_count=fetcher_cfg.get("target_count", 10),
            force=True,
            seen_ids=retriever.seen_ids,
        )

    def handle_test_meme():
        logger.info("Test meme display triggered.")
        import random
        from .inference import Vibe, VIBE_FOLDER_NAMES, get_reflection
        
        # Try to capture active window context for the test reflection
        test_ctx = None
        try:
            info = monitor._get_foreground_info()
            if info:
                app, title = privacy.sanitize(*info)
                test_ctx = extract_context(app, title)
        except Exception:
            pass

        # If on social media with a clean search query, try live search first for the test
        if test_ctx and test_ctx.is_social and test_ctx.search_query:
            logger.info(f"📱 Testing live search for '{test_ctx.search_query}'...")
            live = search_live_contextual_meme(
                test_ctx.search_query,
                meme_dir,
                recent_memes=retriever._recent,
                seen_ids=retriever.seen_ids,
                seen_hashes=retriever.seen_hashes,
            )
            if live:
                retriever.record_shown(time.time(), live)
                label = get_reflection(Vibe.LOST_IN_SCROLL, context=test_ctx, brand_track=current_track["value"])
                root.after(0, lambda p=live, l=label: overlay.show(p, l, vibe=Vibe.LOST_IN_SCROLL, brand_track=current_track["value"]))
                logger.info(f"Showing live test meme: {live.name} for '{test_ctx.search_query}'")
                return

        vibes = list(Vibe)
        random.shuffle(vibes)
        for vibe in vibes:
            folder = meme_dir / VIBE_FOLDER_NAMES[vibe]
            if folder.exists():
                files = [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in retriever.VALID_EXTENSIONS]
                if files:
                    chosen = random.choice(files)
                    label = get_reflection(vibe, context=test_ctx, brand_track=current_track["value"])
                    root.after(0, lambda p=chosen, l=label, v=vibe: overlay.show(p, l, vibe=v, brand_track=current_track["value"]))
                    logger.info(f"Showing test meme: {chosen.name} ({VIBE_FOLDER_NAMES[vibe]})")
                    return
        logger.warning("No memes found in local folders — displaying graceful text-only reflection card fallback!")
        chosen_vibe = random.choice(list(Vibe))
        label = get_reflection(chosen_vibe, context=test_ctx, brand_track=current_track["value"])
        root.after(0, lambda l=label, v=chosen_vibe: overlay.show(None, l, vibe=v, brand_track=current_track["value"]))

    tray = SystemTray(
        on_pause=handle_pause,
        on_resume=handle_resume,
        on_quit=handle_quit,
        on_open_memes=handle_open_memes,
        on_refresh_memes=handle_refresh_memes,
        on_test_meme=handle_test_meme,
        on_toggle_track=handle_toggle_track,
        brand_track=current_track["value"],
    )
    tray_thread = threading.Thread(target=tray.run, name="SystemTray", daemon=True)
    tray_thread.start()

    if "--test" in sys.argv or "--test-meme" in sys.argv:
        logger.info("CLI --test flag detected: displaying test meme in 1.5 seconds...")
        root.after(1500, handle_test_meme)

    # ── Cleanup handler ──
    cleanup_done = False

    def cleanup():
        nonlocal cleanup_done
        if cleanup_done:
            return
        cleanup_done = True

        logger.info("Shutting down...")
        monitor.stop()

        try:
            pack_manager.stop_watcher()
        except Exception:
            pass

        try:
            kb_listener.stop()
        except Exception:
            pass

        try:
            tray.stop()
        except Exception:
            pass

        try:
            vibe_logger.close()
        except Exception:
            pass

        try:
            root.destroy()
        except Exception:
            pass

        logger.info(f"{active_name} shut down cleanly. Goodbye! 👋")

    atexit.register(cleanup)

    # ── Start Thread 4: Inference Worker ──
    confidence_threshold = cfg["inference"]["confidence_threshold"]
    work_cooldown = cfg["general"].get("meme_cooldown_seconds", 300)
    social_cooldown = cfg["general"].get("social_cooldown_seconds", 90)
    last_social_meme_time = 0.0
    ocr_extractor = ScreenTextExtractor()

    def inference_loop():
        """
        Consumer loop: reads TelemetryEvents from the queue,
        classifies them, and triggers meme display when appropriate.
        """
        nonlocal last_social_meme_time

        while True:
            try:
                event = event_queue.get(timeout=2.0)
            except Empty:
                continue

            # Skip if paused
            if paused.is_set():
                continue

            try:
                now = time.time()

                # Extract clean in-the-moment context from active window (regex/string, <0.01ms)
                ctx = extract_context(event.app_name, event.window_title, dwell_minutes=getattr(event, "dwell_minutes", 0.0))
                is_social = bool(ctx and ctx.is_social)
                eligible_cooldown = social_cooldown if is_social else work_cooldown
                last_time = last_social_meme_time if is_social else retriever._last_shown_time
                is_on_cooldown = (now - last_time < eligible_cooldown)

                # Classify the event.
                # When on cooldown or during routine dwell ticks, allow_laya=False (pure rules, 0% CPU).
                result = classifier.classify(event, allow_laya=not is_on_cooldown)

                # Fast path during cooldown: never run OCR, heavy AI, or network searches.
                # Simply log telemetry and return to idle sleep (0.0% CPU).
                if is_on_cooldown:
                    vibe_logger.log(
                        app_name=event.app_name,
                        window_title=event.window_title,
                        result=result,
                        trigger=event.trigger_reason,
                        meme_shown=None,
                    )
                    continue

                meme_shown = None

                # Check if confidence meets threshold
                if result.confidence >= confidence_threshold:
                    # Usability Guardrail: Never interrupt intense active flow state.
                    # If the user is typing rapidly with near-zero backspaces, protect their focus.
                    if is_flow_gate_suppressed(event, result):
                        logger.debug("High-velocity flow state active — suppressing meme to protect focus.")
                    else:
                        meme_path = None
                        custom_reflection = None

                        # ── 1. In-The-Moment Screen Context Extraction (Lightweight Native OCR) ──
                        # Only run OCR when on social feeds / short-form reels where the window title is generic
                        # (e.g. Instagram Reels, TikTok, YouTube Shorts feeds).
                        # Never run social OCR on productivity, email, coding, articles, or non-social web browsing.
                        hwnd = getattr(event, "hwnd", 0)
                        is_social_feed = is_social or any(
                            s in event.window_title.lower() for s in ["instagram", "tiktok", "reels", "shorts", "twitter", "x.com"]
                        )
                        should_ocr = is_social_feed and not (
                            ctx and getattr(ctx, "is_specific", False) and getattr(ctx, "category", "") in ("video", "code", "docs", "email", "reading")
                        )
                        if hwnd and should_ocr and ocr_extractor.is_available():
                            ocr_text = ocr_extractor.extract_text(hwnd, event.app_name)
                            if ocr_text:
                                mindful_data = classifier.classify_screen_content(ocr_text, event.app_name, event.window_title)
                                if mindful_data:
                                    logger.info(f"🧘 In-screen mindfulness match: theme={mindful_data['human_theme']}")
                                    result = VibeResult(mindful_data["vibe"], 0.92, "laya_ocr")
                                    custom_reflection = mindful_data["reflection"]

                                    # Try finding a meme directly for the specific topic / theme
                                    search_queries = mindful_data.get("search_queries") or [
                                        mindful_data["human_theme"].replace("_", " "),
                                        mindful_data["reaction_vibe"].replace("_", " ")
                                    ]
                                    live_meme = search_live_contextual_meme(
                                        search_queries,
                                        meme_dir,
                                        recent_memes=retriever._recent,
                                        seen_ids=retriever.seen_ids,
                                        seen_hashes=retriever.seen_hashes,
                                    )
                                    if live_meme:
                                        meme_path = live_meme
                                        if is_social:
                                            last_social_meme_time = now
                                        retriever.record_shown(now, live_meme)
                                    else:
                                        meme_path = retriever.get_meme(result.vibe, now, cooldown=eligible_cooldown)
                                        if meme_path and is_social:
                                            last_social_meme_time = now

                        # ── 2. Fallback to Title / Context Pipeline if OCR produced no meme ──
                        if not meme_path:
                            # ── Social Media Spot-On Mode ──
                            if is_social:
                                if ctx and getattr(ctx, "is_specific", False) and ctx.search_query and ctx.search_query.lower() not in ("instagram", "youtube", "tiktok", "twitter", "reddit", "facebook"):
                                    queries = [ctx.search_query]
                                else:
                                    queries = [random.choice(["side eye", "blank stare", "monkey puppet looking away", "cat staring", "distracted"])]

                                logger.info(f"📱 Social media trance detected (queries={queries}) — attempting live search...")
                                live_meme = search_live_contextual_meme(
                                    queries,
                                    meme_dir,
                                    recent_memes=retriever._recent,
                                    seen_ids=retriever.seen_ids,
                                    seen_hashes=retriever.seen_hashes,
                                )
                                if live_meme:
                                    meme_path = live_meme
                                    last_social_meme_time = now
                                    retriever.record_shown(now, live_meme)
                                else:
                                    meme_path = retriever.get_meme(result.vibe, now, cooldown=social_cooldown)
                                    if meme_path:
                                        last_social_meme_time = now
                            else:
                                # Standard work mode with standard cooldown (300s)
                                meme_path = retriever.get_meme(result.vibe, now, cooldown=work_cooldown)

                        if meme_path:
                            meme_shown = meme_path.name
                            label = custom_reflection if custom_reflection else get_reflection(result.vibe, context=ctx, brand_track=current_track["value"], dwell_minutes=getattr(event, "dwell_minutes", None))
                            logger.info(
                                f"🎯 {result} (ctx={ctx.subject if ctx else 'none'}) → showing {meme_path.name}"
                            )
                            # Marshal to main thread for tkinter safety
                            root.after(
                                0,
                                lambda p=meme_path, l=label, v=result.vibe: overlay.show(p, l, vibe=v, brand_track=current_track["value"]),
                            )
                        else:
                            # Dignified text-only reflection card fallback when no meme image exists
                            label = custom_reflection if custom_reflection else get_reflection(result.vibe, context=ctx, brand_track=current_track["value"], dwell_minutes=getattr(event, "dwell_minutes", None))
                            logger.info(
                                f"🎯 {result} (ctx={ctx.subject if ctx else 'none'}) → showing text reflection card (no meme image)"
                            )
                            retriever._last_shown_time = now
                            if is_social:
                                last_social_meme_time = now
                            root.after(
                                0,
                                lambda l=label, v=result.vibe: overlay.show(None, l, vibe=v, brand_track=current_track["value"]),
                            )
                else:
                    logger.debug(f"Low confidence: {result} — skipping meme.")

                # Always log, even if no meme shown
                vibe_logger.log(
                    app_name=event.app_name,
                    window_title=event.window_title,
                    result=result,
                    trigger=event.trigger_reason,
                    meme_shown=meme_shown,
                )

            except Exception as e:
                logger.error(f"Inference error: {e}", exc_info=True)

    inference_thread = threading.Thread(target=inference_loop, name="InferenceWorker", daemon=True)
    inference_thread.start()
    logger.info("Inference worker started.")

    # ── Main thread: tkinter event loop ──
    icon_letter = "V" if current_track["value"] == "vihara" else "B"
    logger.info("")
    logger.info(f"🚀 {active_name} is running!")
    logger.info(f"   Meme folder: {meme_dir}")
    logger.info(f"   Database: {db_path}")
    logger.info(f"   Laya model: {'enabled' if cfg['inference']['use_laya'] else 'disabled (rules only)'}")
    logger.info(f"   Look for the '{icon_letter}' icon in your system tray.")
    logger.info("")

    # ── Signal handling for clean Ctrl+C in terminal ──
    import signal

    def poll_signals():
        root.after(200, poll_signals)

    root.after(200, poll_signals)

    def sig_handler(signum, frame):
        logger.info("Signal received, stopping...")
        cleanup()
        os._exit(0)

    try:
        signal.signal(signal.SIGINT, sig_handler)
        signal.signal(signal.SIGTERM, sig_handler)
    except Exception:
        pass

    try:
        root.mainloop()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Interrupted by user.")
    finally:
        cleanup()
        os._exit(0)


if __name__ == "__main__":
    main()
