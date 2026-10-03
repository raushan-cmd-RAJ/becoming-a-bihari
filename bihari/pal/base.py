"""
Platform Abstraction Layer (PAL) — Base Interfaces and Data Contracts.

Defines polymorphic interfaces for platform-specific capabilities:
- BaseWindowObserver: Active window monitoring and foreground switch hooks
- BaseScreenSensor: Native on-screen OCR context extraction
- BaseTrayDriver: System tray icon, notifications, and menu management
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Tuple


@dataclass(frozen=True)
class ActiveWindowInfo:
    """Immutable representation of the foreground window state."""

    hwnd: int = 0
    title: str = ""
    app_name: str = ""
    pid: int = 0
    bounds: Tuple[int, int, int, int] = (0, 0, 0, 0)  # (left, top, width, height)
    is_valid: bool = True
    extra_metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        """Return True if no valid window is represented."""
        return not self.is_valid or (not self.title and not self.app_name)


class BaseWindowObserver(abc.ABC):
    """
    Abstract interface for foreground window tracking and OS event hooks.
    Implementations must handle permissions, elevation differences, and race conditions.
    """

    @abc.abstractmethod
    def get_active_window(self) -> Optional[ActiveWindowInfo]:
        """Query the current active foreground window synchronously."""
        raise NotImplementedError

    @abc.abstractmethod
    def register_switch_hook(self, callback: Callable[[ActiveWindowInfo], None]) -> bool:
        """Register a callback invoked when the active foreground window changes."""
        raise NotImplementedError

    @abc.abstractmethod
    def unregister_switch_hook(self) -> None:
        """Unregister the switch hook callback."""
        raise NotImplementedError

    @abc.abstractmethod
    def start(self) -> None:
        """Start listening for window events (may spawn background thread or loop)."""
        raise NotImplementedError

    @abc.abstractmethod
    def stop(self) -> None:
        """Stop listening and clean up all OS resources."""
        raise NotImplementedError

    @abc.abstractmethod
    def is_supported(self) -> bool:
        """Return True if this platform driver is supported in the current environment."""
        raise NotImplementedError


class BaseScreenSensor(abc.ABC):
    """
    Abstract interface for screen text / OCR context extraction.
    Must never crash if OCR libraries or permissions are missing.
    """

    @abc.abstractmethod
    def extract_context_text(
        self, window_info: Optional[ActiveWindowInfo] = None
    ) -> Optional[str]:
        """
        Extract visible text from active foreground window bounding box.
        Returns cleaned text or None if extraction fails or is unsupported.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def is_supported(self) -> bool:
        """Return True if native OCR capability is functional on this system."""
        raise NotImplementedError


class BaseTrayDriver(abc.ABC):
    """
    Abstract interface for system tray icon and status integration.
    """

    @abc.abstractmethod
    def create_tray(
        self,
        title: str,
        tooltip: str,
        on_quit: Optional[Callable[[], None]] = None,
        on_click: Optional[Callable[[], None]] = None,
    ) -> Any:
        """Create and initialize the system tray icon."""
        raise NotImplementedError

    @abc.abstractmethod
    def update_tooltip(self, tooltip: str) -> None:
        """Update the hover tooltip text."""
        raise NotImplementedError

    @abc.abstractmethod
    def update_icon(self, icon_data: Any) -> None:
        """Update the tray icon image."""
        raise NotImplementedError

    @abc.abstractmethod
    def show_notification(self, title: str, message: str) -> None:
        """Display an OS notification / balloon toast from the tray icon."""
        raise NotImplementedError

    @abc.abstractmethod
    def stop(self) -> None:
        """Remove the tray icon and clean up resources."""
        raise NotImplementedError

    @abc.abstractmethod
    def is_supported(self) -> bool:
        """Return True if system tray is supported in the current environment."""
        raise NotImplementedError
