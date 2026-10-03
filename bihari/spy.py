"""
Module 1: THE SPY — Telemetry Harvester.

Captures foreground window info (app name, window title) via win32 APIs
and tracks keyboard velocity metrics (typing speed, backspace rate) via pynput.

Privacy guarantees:
  - Never logs individual keystrokes — only increments numerical counters.
  - All data passes through PrivacyFilter before entering the event pipeline.
"""

import time
import datetime
import threading
import collections
from queue import Queue
from typing import Optional

import logging

logger = logging.getLogger(__name__)


class TelemetryEvent:
    """Immutable snapshot of the user's current state at a point in time."""

    __slots__ = (
        "app_name",
        "window_title",
        "typing_speed",
        "backspace_count",
        "backspace_rate",
        "window_switches_3min",
        "timestamp",
        "trigger_reason",
        "hour_of_day",
        "session_minutes",
        "dwell_minutes",
        "hwnd",
    )

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            object.__setattr__(self, k, v)
        if not hasattr(self, "hwnd"):
            object.__setattr__(self, "hwnd", 0)

    def __repr__(self):
        return (
            f"TelemetryEvent(app={self.app_name!r}, title={self.window_title!r}, "
            f"speed={self.typing_speed}, bs_rate={self.backspace_rate:.2f}, "
            f"switches={self.window_switches_3min}, trigger={self.trigger_reason!r}, "
            f"hour={self.hour_of_day}, session={self.session_minutes}, dwell={self.dwell_minutes})"
        )


class KeyboardTracker:
    """
    Tracks typing velocity without ever logging individual keys.

    Maintains two rolling deques of timestamps:
      - Total keystroke timestamps (for chars/min calculation)
      - Backspace key timestamps (for frustration/rage detection)
    """

    def __init__(self, window_seconds: int = 30):
        self.window_seconds = window_seconds
        self._strokes: collections.deque = collections.deque()
        self._backspaces: collections.deque = collections.deque()
        self._lock = threading.Lock()

    def on_key_press(self, key):
        """
        Callback for pynput Listener.
        Only records the *timestamp* of the event — never the key identity.
        Exception: we check if the key IS backspace to increment that counter,
        but we never store which non-backspace key was pressed.
        """
        from pynput import keyboard as kb

        now = time.monotonic()
        cutoff = now - self.window_seconds

        with self._lock:
            self._strokes.append(now)
            if key == kb.Key.backspace:
                self._backspaces.append(now)

            # Prune old entries
            while self._strokes and self._strokes[0] < cutoff:
                self._strokes.popleft()
            while self._backspaces and self._backspaces[0] < cutoff:
                self._backspaces.popleft()

    def get_metrics(self) -> dict:
        """Get current typing metrics for the sliding window."""
        now = time.monotonic()
        cutoff = now - self.window_seconds

        with self._lock:
            # Prune stale entries
            while self._strokes and self._strokes[0] < cutoff:
                self._strokes.popleft()
            while self._backspaces and self._backspaces[0] < cutoff:
                self._backspaces.popleft()

            total = len(self._strokes)
            backspaces = len(self._backspaces)

        return {
            "typing_speed": round(total / self.window_seconds * 60),  # chars per minute
            "backspace_count": backspaces,
            "backspace_rate": round(backspaces / total, 2) if total > 0 else 0.0,
        }

    def get_backspace_velocity(self, window_seconds: int = 10) -> int:
        """Get backspace count in a shorter recent window (for spike detection)."""
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            return sum(1 for t in self._backspaces if t >= cutoff)


class ForegroundMonitor:
    """
    Monitors the foreground window for changes and backspace spikes.

    Emits TelemetryEvent objects into the event queue when:
      1. The foreground window changes (app or title)
      2. Backspace velocity spikes by >50% in a 10-second window

    Uses a settling debounce (poll_interval) to avoid flooding on rapid alt-tabs.
    """

    def __init__(
        self,
        event_queue: Queue,
        privacy_filter,
        keyboard_tracker: KeyboardTracker,
        poll_interval_ms: int = 500,
        idle_timeout_seconds: int = 300,
    ):
        self.queue = event_queue
        self.privacy = privacy_filter
        self.keyboard = keyboard_tracker
        self.poll_interval = poll_interval_ms / 1000.0
        self.idle_timeout = idle_timeout_seconds
        self._running = False

        # Window switch history: deque of (monotonic_timestamp, app_name)
        self._switch_history: collections.deque = collections.deque(maxlen=50)
        self._last_app = ""
        self._last_title = ""
        self._last_event_time = time.monotonic()
        
        self._session_start = time.monotonic()
        self._current_app_start = time.monotonic()

        # Backspace spike detection
        self._last_backspace_velocity = 0

    def _get_foreground_info(self) -> Optional[tuple[str, str, int]]:
        """
        Get (exe_name, window_title, hwnd) of the foreground window.

        Returns None on failure — handles the race condition where a window
        is destroyed between GetForegroundWindow() and GetWindowText(),
        as well as UAC-elevated processes that block title reading.
        """
        try:
            import win32gui
            import win32process
            import psutil

            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return None

            title = win32gui.GetWindowText(hwnd)
            _, pid = win32process.GetWindowThreadProcessId(hwnd)

            if pid <= 0:
                return None

            try:
                proc = psutil.Process(pid)
                exe = proc.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                # Elevated process or gone — return with empty name
                exe = "unknown.exe"

            return exe, title, hwnd

        except Exception as e:
            # win32gui can throw pywintypes.error on window destruction race
            logger.debug(f"Foreground info failed: {e}")
            return None

    def _count_switches_in_window(self, seconds: int = 180) -> int:
        """Count window switches in the last N seconds."""
        cutoff = time.monotonic() - seconds
        return sum(1 for ts, _ in self._switch_history if ts >= cutoff)

    def _emit_event(self, app: str, title: str, trigger: str, hwnd: int = 0):
        """Build and enqueue a TelemetryEvent."""
        metrics = self.keyboard.get_metrics()
        hour_of_day = datetime.datetime.now().hour
        session_minutes = round((time.monotonic() - self._session_start) / 60.0, 1)
        dwell_minutes = round((time.monotonic() - self._current_app_start) / 60.0, 1)
        event = TelemetryEvent(
            app_name=app,
            window_title=title,
            typing_speed=metrics["typing_speed"],
            backspace_count=metrics["backspace_count"],
            backspace_rate=metrics["backspace_rate"],
            window_switches_3min=self._count_switches_in_window(180),
            timestamp=time.time(),
            trigger_reason=trigger,
            hour_of_day=hour_of_day,
            session_minutes=session_minutes,
            dwell_minutes=dwell_minutes,
            hwnd=hwnd,
        )
        # Non-blocking put — drop if queue is full rather than blocking the monitor
        if not self.queue.full():
            self.queue.put(event)
            logger.debug(f"Emitted: {event}")
        self._last_event_time = time.monotonic()

    def run(self):
        """
        Main polling loop. Runs as a daemon thread.

        Fires events on:
          - Window change (app or title changed)
          - Backspace spike (>50% increase in 10s window)
        """
        try:
            from .tray import ensure_default_desktop
            ensure_default_desktop()
        except Exception:
            pass

        self._running = True
        logger.info("Foreground monitor started.")

        while self._running:
            info = self._get_foreground_info()
            if info is None:
                time.sleep(self.poll_interval)
                continue

            app_raw, title_raw, hwnd = info
            app, title = self.privacy.sanitize(app_raw, title_raw)
            trigger = None

            # Trigger 1: Window changed
            if app != self._last_app or title != self._last_title:
                self._switch_history.append((time.monotonic(), app))
                if app != self._last_app:
                    self._current_app_start = time.monotonic()
                self._last_app = app
                self._last_title = title
                trigger = "window_change"

            # Trigger 2: Backspace spike (>50% increase in 10s window)
            current_bv = self.keyboard.get_backspace_velocity(window_seconds=10)
            if self._last_backspace_velocity > 2 and current_bv > self._last_backspace_velocity * 1.5:
                trigger = "backspace_spike"
            self._last_backspace_velocity = current_bv

            # Trigger 3: Active dwell tick (emit every 15s while user remains in window)
            if trigger is None:
                elapsed = time.monotonic() - self._last_event_time
                if elapsed >= 15.0:
                    trigger = "dwell_tick"

            if trigger:
                self._emit_event(app, title, trigger, hwnd=hwnd)

            time.sleep(self.poll_interval)

        logger.info("Foreground monitor stopped.")

    def stop(self):
        """Signal the monitor loop to exit."""
        self._running = False
