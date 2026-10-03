"""
Privacy filter for telemetry sanitization.

Masks window titles when sensitive apps or keywords are detected.
Does NOT log individual keystrokes — only numerical velocity metrics.
Does NOT clear the clipboard — only masks telemetry data.
"""

import re
from typing import Optional

HIDDEN = "HIDDEN_PRIVACY_CONTEXT"


class PrivacyFilter:
    """Sanitizes telemetry data before it enters the event pipeline."""

    def __init__(self, blocked_apps: list[str], blocked_keywords: list[str]):
        """
        Args:
            blocked_apps: Executable names to always mask (e.g., 'KeePassXC.exe').
            blocked_keywords: Title substrings that trigger masking (case-insensitive).
        """
        self.blocked_apps = {app.lower() for app in blocked_apps}

        # Compile a single regex for all keywords (case-insensitive)
        if blocked_keywords:
            escaped = [re.escape(kw) for kw in blocked_keywords]
            self.pattern = re.compile("|".join(escaped), re.IGNORECASE)
        else:
            self.pattern = None

    def is_sensitive(self, app_name: str, window_title: str) -> bool:
        """Check if the current context is sensitive."""
        if app_name.lower() in self.blocked_apps:
            return True
        if self.pattern and self.pattern.search(window_title):
            return True
        return False

    def sanitize(self, app_name: str, window_title: str) -> tuple[str, str]:
        """
        Returns (app_name, sanitized_title).
        Masks the title to HIDDEN_PRIVACY_CONTEXT if sensitive.
        """
        if self.is_sensitive(app_name, window_title):
            return app_name, HIDDEN
        return app_name, window_title
