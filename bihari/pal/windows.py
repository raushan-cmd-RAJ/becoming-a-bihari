"""
Platform Abstraction Layer (PAL) — Windows Win32 Driver Implementations.

Implements native Windows integration for:
- Win32WindowObserver: Active window monitoring via win32gui and SetWinEventHook
- Win32ScreenSensor: Windows Media OCR context extraction via winocr and GDI capture
- Win32TrayDriver: Native Windows system tray integration
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import logging
import sys
import threading
import time
from typing import Any, Callable, Optional, Tuple

from .base import ActiveWindowInfo, BaseScreenSensor, BaseTrayDriver, BaseWindowObserver

logger = logging.getLogger(__name__)

EVENT_SYSTEM_FOREGROUND = 0x0003
WINEVENT_OUTOFCONTEXT = 0x0000

# Function pointer type for SetWinEventHook
WinEventProcType = ctypes.WINFUNCTYPE(
    None,
    ctypes.wintypes.HANDLE,
    ctypes.wintypes.DWORD,
    ctypes.wintypes.HWND,
    ctypes.wintypes.LONG,
    ctypes.wintypes.LONG,
    ctypes.wintypes.DWORD,
    ctypes.wintypes.DWORD,
)


class Win32WindowObserver(BaseWindowObserver):
    """
    Windows implementation of BaseWindowObserver.
    Extracts foreground window metadata and registers OS foreground event hooks.
    """

    def __init__(self, poll_interval_seconds: float = 0.5):
        self.poll_interval = poll_interval_seconds
        self._callback: Optional[Callable[[ActiveWindowInfo], None]] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._hook_handle: Any = None
        self._hook_proc_ref: Any = None
        self._last_hwnd = 0

    def is_supported(self) -> bool:
        """Check if Win32 API is supported on the host platform."""
        return sys.platform == "win32"

    def get_active_window(self) -> Optional[ActiveWindowInfo]:
        """
        Query foreground window info synchronously via Win32 API.
        Handles window race conditions, destroyed windows, and elevated processes safely.
        """
        if not self.is_supported():
            return None

        try:
            import win32gui
            import win32process
            import psutil

            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return None

            title = win32gui.GetWindowText(hwnd) or ""
            _, pid = win32process.GetWindowThreadProcessId(hwnd)

            app_name = ""
            if pid:
                try:
                    proc = psutil.Process(pid)
                    app_name = proc.name()
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    app_name = "Unknown"

            bounds: Tuple[int, int, int, int] = (0, 0, 0, 0)
            try:
                rect = win32gui.GetWindowRect(hwnd)
                bounds = (rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1])
            except Exception:
                bounds = (0, 0, 0, 0)

            return ActiveWindowInfo(
                hwnd=hwnd,
                title=title,
                app_name=app_name,
                pid=pid,
                bounds=bounds,
                is_valid=True,
            )
        except Exception as e:
            logger.debug(f"Win32WindowObserver.get_active_window failed: {e}")
            return None

    def register_switch_hook(self, callback: Callable[[ActiveWindowInfo], None]) -> bool:
        """Set the callback to be triggered when foreground window changes."""
        self._callback = callback
        return True

    def unregister_switch_hook(self) -> None:
        """Unset the callback."""
        self._callback = None

    def _event_hook_worker(self):
        """Worker thread that runs the Windows message loop with SetWinEventHook."""
        try:
            user32 = ctypes.windll.user32

            def _on_win_event(hHook, event, hwnd, idObject, idChild, dwEventThread, dwmsEventTime):
                if event == EVENT_SYSTEM_FOREGROUND and hwnd:
                    if hwnd != self._last_hwnd:
                        self._last_hwnd = hwnd
                        info = self.get_active_window()
                        if info and self._callback:
                            try:
                                self._callback(info)
                            except Exception as cb_err:
                                logger.error(f"Error in window switch callback: {cb_err}")

            self._hook_proc_ref = WinEventProcType(_on_win_event)
            self._hook_handle = user32.SetWinEventHook(
                EVENT_SYSTEM_FOREGROUND,
                EVENT_SYSTEM_FOREGROUND,
                0,
                self._hook_proc_ref,
                0,
                0,
                WINEVENT_OUTOFCONTEXT,
            )

            if not self._hook_handle:
                logger.warning("SetWinEventHook failed; falling back to event polling.")
                self._polling_loop()
                return

            msg = ctypes.wintypes.MSG()
            while self._running:
                # Use MsgWaitForMultipleObjectsEx or PeekMessage to allow non-blocking stop
                has_msg = user32.PeekMessageW(ctypes.byref(msg), 0, 0, 0, 1)  # PM_REMOVE = 1
                if has_msg:
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
                else:
                    time.sleep(0.05)

            if self._hook_handle:
                user32.UnhookWinEvent(self._hook_handle)
                self._hook_handle = None

        except Exception as e:
            logger.warning(f"WinEventHook exception ({e}); running polling fallback.")
            self._polling_loop()

    def _polling_loop(self):
        """Fallback polling loop in case WinEventHook cannot be established."""
        while self._running:
            info = self.get_active_window()
            if info and info.hwnd and info.hwnd != self._last_hwnd:
                self._last_hwnd = info.hwnd
                if self._callback:
                    try:
                        self._callback(info)
                    except Exception as err:
                        logger.error(f"Error in window switch polling callback: {err}")
            time.sleep(self.poll_interval)

    def start(self) -> None:
        """Start listening for window switches in a daemon background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._event_hook_worker,
            name="Win32WindowObserverThread",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop listening and release handles."""
        self._running = False
        if self._hook_handle:
            try:
                ctypes.windll.user32.UnhookWinEvent(self._hook_handle)
            except Exception:
                pass
            self._hook_handle = None
        self._thread = None


class Win32ScreenSensor(BaseScreenSensor):
    """
    Windows Media OCR context extractor using winocr and Win32 GDI screen grab.
    """

    def __init__(self):
        self._available: Optional[bool] = None

    def is_supported(self) -> bool:
        """Check if Windows Media OCR (winocr) is functional in current environment."""
        if sys.platform != "win32":
            return False
        if self._available is not None:
            return self._available
        try:
            import winocr  # noqa: F401
            self._available = True
        except Exception:
            self._available = False
        return self._available

    def extract_context_text(
        self, window_info: Optional[ActiveWindowInfo] = None
    ) -> Optional[str]:
        """
        Capture the bounding rect of the target window and extract visible text using winocr.
        Never throws exceptions — degrades gracefully to None.
        """
        if not self.is_supported():
            return None

        try:
            import asyncio
            import winocr
            from PIL import ImageGrab

            # Determine bounds
            bbox = None
            if window_info and window_info.bounds and window_info.bounds[2] > 0 and window_info.bounds[3] > 0:
                l, t, w, h = window_info.bounds
                # Clamp minimum size to prevent 0-pixel capture error
                if w >= 50 and h >= 50:
                    bbox = (max(0, l), max(0, t), max(0, l + w), max(0, t + h))

            # Capture screen area
            if bbox:
                screenshot = ImageGrab.grab(bbox=bbox)
            else:
                screenshot = ImageGrab.grab()

            if screenshot is None:
                return None

            # Run winocr recognize_pil
            loop = None
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            if loop.is_running():
                # Running inside existing loop
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    result = pool.submit(lambda: asyncio.run(winocr.recognize_pil(screenshot, "en"))).result(timeout=5)
            else:
                result = loop.run_until_complete(winocr.recognize_pil(screenshot, "en"))

            if not result or not hasattr(result, "text"):
                return None

            text = result.text.strip()
            return text if text else None

        except Exception as e:
            logger.debug(f"Win32ScreenSensor.extract_context_text encountered error: {e}")
            return None


class Win32TrayDriver(BaseTrayDriver):
    """
    Windows implementation of BaseTrayDriver delegating to native bihari.tray.SystemTray.
    """

    def __init__(self):
        self._tray: Any = None
        self._icon: Any = None
        self._title = "Vihara"
        self._tooltip = "Vihara — Mindful Focus Catalyst"
        self._on_quit: Optional[Callable[[], None]] = None
        self._on_click: Optional[Callable[[], None]] = None

    def is_supported(self) -> bool:
        """Check if system tray is supported on Windows."""
        return sys.platform == "win32"

    def create_tray(
        self,
        title: str,
        tooltip: str,
        on_quit: Optional[Callable[[], None]] = None,
        on_click: Optional[Callable[[], None]] = None,
    ) -> Any:
        """Initialize and wire native system tray driver."""
        self._title = title
        self._tooltip = tooltip
        self._on_quit = on_quit
        self._on_click = on_click

        from bihari.tray import SystemTray

        brand_track = (
            "bihari"
            if "bihari" in title.lower() or "bihari" in tooltip.lower()
            else "vihara"
        )
        self._tray = SystemTray(
            on_pause=lambda: None,
            on_resume=lambda: None,
            on_quit=on_quit or (lambda: None),
            on_open_memes=lambda: None,
            brand_track=brand_track,
        )
        if tooltip:
            self._tray.custom_tooltip = tooltip
        self._icon = self._tray
        return self

    def update_tooltip(self, tooltip: str) -> None:
        """Update system tray tooltip string."""
        self._tooltip = tooltip
        if self._tray and hasattr(self._tray, "update_tooltip"):
            try:
                self._tray.update_tooltip(tooltip)
            except Exception as e:
                logger.debug(f"Win32TrayDriver failed to update tooltip: {e}")

    def update_icon(self, icon_data: Any) -> None:
        """Update system tray icon image."""
        if self._tray and hasattr(self._tray, "update_icon"):
            try:
                self._tray.update_icon(icon_data)
            except Exception as e:
                logger.debug(f"Win32TrayDriver failed to update icon: {e}")

    def show_notification(self, title: str, message: str) -> None:
        """Display Windows notification."""
        if self._tray and hasattr(self._tray, "show_notification"):
            try:
                self._tray.show_notification(title, message)
            except Exception as e:
                logger.debug(f"Win32TrayDriver failed to show notification: {e}")

    def stop(self) -> None:
        """Stop and remove tray icon."""
        if self._tray and hasattr(self._tray, "stop"):
            try:
                self._tray.stop()
            except Exception as e:
                logger.debug(f"Win32TrayDriver stop error: {e}")
        self._tray = None
        self._icon = None
