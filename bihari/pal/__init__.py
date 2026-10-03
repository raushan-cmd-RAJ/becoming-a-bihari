"""
Platform Abstraction Layer (PAL) — Dynamic Platform Dispatcher.

Provides factory functions to obtain platform-specific drivers:
- get_window_observer() -> BaseWindowObserver
- get_screen_sensor() -> BaseScreenSensor
- get_tray_driver() -> BaseTrayDriver
- get_active_window_info() -> Optional[ActiveWindowInfo]
"""

from __future__ import annotations

import logging
import sys
from typing import Optional

from .base import (
    ActiveWindowInfo,
    BaseScreenSensor,
    BaseTrayDriver,
    BaseWindowObserver,
)
from .windows import (
    Win32ScreenSensor,
    Win32TrayDriver,
    Win32WindowObserver,
)

logger = logging.getLogger(__name__)


class FallbackWindowObserver(BaseWindowObserver):
    """Safe fallback window observer for platforms without native window hook support."""

    def is_supported(self) -> bool:
        return False

    def get_active_window(self) -> Optional[ActiveWindowInfo]:
        return None

    def register_switch_hook(self, callback) -> bool:
        return False

    def unregister_switch_hook(self) -> None:
        pass

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass


class FallbackScreenSensor(BaseScreenSensor):
    """Safe fallback screen sensor when OCR is unavailable."""

    def is_supported(self) -> bool:
        return False

    def extract_context_text(self, window_info: Optional[ActiveWindowInfo] = None) -> Optional[str]:
        return None


class FallbackTrayDriver(BaseTrayDriver):
    """Safe fallback tray driver when native tray is unsupported."""

    def is_supported(self) -> bool:
        return False

    def create_tray(self, title: str, tooltip: str, on_quit=None, on_click=None):
        return None

    def update_tooltip(self, tooltip: str) -> None:
        pass

    def update_icon(self, icon_data) -> None:
        pass

    def show_notification(self, title: str, message: str) -> None:
        pass

    def stop(self) -> None:
        pass


def get_window_observer(poll_interval_seconds: float = 0.5) -> BaseWindowObserver:
    """Return the active platform window observer instance."""
    if sys.platform == "win32":
        return Win32WindowObserver(poll_interval_seconds=poll_interval_seconds)
    # macOS or Linux would dispatch MacWindowObserver / LinuxWindowObserver
    return FallbackWindowObserver()


def get_screen_sensor() -> BaseScreenSensor:
    """Return the active platform screen OCR sensor instance."""
    if sys.platform == "win32":
        return Win32ScreenSensor()
    # macOS would dispatch MacAppleVisionSensor, Linux would dispatch LinuxOcrSensor
    return FallbackScreenSensor()


def get_tray_driver() -> BaseTrayDriver:
    """Return the active platform system tray driver instance."""
    if sys.platform == "win32":
        return Win32TrayDriver()
    return FallbackTrayDriver()


def get_active_window_info() -> Optional[ActiveWindowInfo]:
    """Convenience helper to query current foreground window info."""
    observer = get_window_observer()
    return observer.get_active_window()


__all__ = [
    "ActiveWindowInfo",
    "BaseWindowObserver",
    "BaseScreenSensor",
    "BaseTrayDriver",
    "Win32WindowObserver",
    "Win32ScreenSensor",
    "Win32TrayDriver",
    "FallbackWindowObserver",
    "FallbackScreenSensor",
    "FallbackTrayDriver",
    "get_window_observer",
    "get_screen_sensor",
    "get_tray_driver",
    "get_active_window_info",
]
