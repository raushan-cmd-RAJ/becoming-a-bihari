"""
Tests for Module: Privacy Filter & Telemetry Sanitization.

Validates:
- Keyword blocklist detection (bank, login, checkout, password, payment, etc.).
- App executable blocklist detection (KeePassXC.exe, 1Password.exe, Bitwarden.exe).
- Redaction of sensitive window titles to HIDDEN_PRIVACY_CONTEXT.
- Passthrough of non-sensitive everyday work contexts.
- Case-insensitivity and adversarial string safety (regex characters, accents).
- Pure velocity tracking with zero keystroke retention.
"""

import pytest
from bihari.privacy import PrivacyFilter, HIDDEN
from bihari.config import DEFAULTS
from bihari.spy import KeyboardTracker


@pytest.fixture
def default_filter():
    """Create a PrivacyFilter using default config settings."""
    blocked_apps = DEFAULTS["privacy"]["blocked_apps"]
    blocked_keywords = DEFAULTS["privacy"]["blocked_title_keywords"]
    return PrivacyFilter(blocked_apps, blocked_keywords)


class TestPrivacyFilter:
    """Tier 1 & Tier 2: Privacy Sanitizer verification."""

    def test_sensitive_app_masking(self, default_filter):
        """KeePassXC, 1Password, and Bitwarden must be unconditionally masked."""
        for app in ["KeePassXC.exe", "1Password.exe", "Bitwarden.exe"]:
            assert default_filter.is_sensitive(app, "My Passwords Database") is True
            app_out, title_out = default_filter.sanitize(app, "My Passwords Database")
            assert app_out == app
            assert title_out == HIDDEN

    def test_sensitive_app_case_insensitivity(self, default_filter):
        """App blocking must be case-insensitive."""
        assert default_filter.is_sensitive("keepassxc.exe", "Vault") is True
        assert default_filter.is_sensitive("BITWARDEN.EXE", "Vault") is True
        assert default_filter.is_sensitive("1password.exe", "Vault") is True

    @pytest.mark.parametrize("title", [
        "Chase Online Banking - Account Overview",
        "Sign in to your Google Account",
        "Secure User Login - Portal",
        "Amazon.com - Checkout & Order Summary",
        "Enter your Master Password",
        "Pay with Credit Card - Stripe",
        "Confirm Payment details",
        "Portail de connexion - Mon Compte",
        "Página de Iniciar Sesión",
    ])
    def test_sensitive_keywords_detection(self, default_filter, title):
        """All default sensitive keywords must trigger masking."""
        assert default_filter.is_sensitive("chrome.exe", title) is True
        _, sanitized = default_filter.sanitize("chrome.exe", title)
        assert sanitized == HIDDEN

    def test_keyword_case_insensitivity(self, default_filter):
        """Keyword matching must be case-insensitive across uppercase, lowercase, and mixed."""
        assert default_filter.is_sensitive("firefox.exe", "BANK STATEMENT OF ACCOUNT") is True
        assert default_filter.is_sensitive("firefox.exe", "pAsSwOrD recovery") is True
        assert default_filter.is_sensitive("firefox.exe", "CHECKOUT - SHOPPING CART") is True

    @pytest.mark.parametrize("app, title", [
        ("code.exe", "auth_service.py - vihara - Visual Studio Code"),
        ("chrome.exe", "Python 3.13.1 Documentation - Standard Library"),
        ("chrome.exe", "Lofi Hip Hop Radio - Beats to Relax/Study to - YouTube"),
        ("windowsterminal.exe", "git status - powershell"),
        ("spotify.exe", "Daft Punk - Harder, Better, Faster, Stronger"),
        ("slack.exe", "#engineering - Acme Corp"),
    ])
    def test_benign_context_passthrough(self, default_filter, app, title):
        """Benign applications and non-sensitive titles must pass through unaltered."""
        assert default_filter.is_sensitive(app, title) is False
        app_out, title_out = default_filter.sanitize(app, title)
        assert app_out == app
        assert title_out == title

    def test_regex_special_characters_in_title(self, default_filter):
        """Titles with regex meta-characters must evaluate cleanly without re.error."""
        sensitive_adversarial = [
            "Special [Offer] (USD) + Bank? * $100.00 ^",
            "regex.test(password) == True? [docs]",
            "C:\\Users\\admin\\payment\\receipt.pdf",
        ]
        for title in sensitive_adversarial:
            assert default_filter.is_sensitive("notepad.exe", title) is True
            _, sanitized = default_filter.sanitize("notepad.exe", title)
            assert sanitized == HIDDEN

        non_sensitive_adversarial = [
            "Title with unclosed (bracket [and more",
            "C:\\Development\\Projects\\my-app\\main.py",
            "Special characters: ^.*+?{}[]\\|()",
        ]
        for title in non_sensitive_adversarial:
            assert default_filter.is_sensitive("notepad.exe", title) is False
            _, sanitized = default_filter.sanitize("notepad.exe", title)
            assert sanitized == title

    def test_empty_and_minimal_inputs(self, default_filter):
        """Empty strings and boundary strings must degrade safely without exceptions."""
        assert default_filter.is_sensitive("", "") is False
        app_out, title_out = default_filter.sanitize("", "")
        assert app_out == ""
        assert title_out == ""

    def test_no_keystroke_logging_contract(self):
        """KeyboardTracker only aggregates numeric counts; it must never store raw key characters."""
        tracker = KeyboardTracker()
        assert not hasattr(tracker, "logged_keys")
        assert not hasattr(tracker, "keystroke_buffer")
        # Check metrics dictionary
        metrics = tracker.get_metrics()
        assert "typing_speed" in metrics
        assert "backspace_count" in metrics
        assert "backspace_rate" in metrics
        assert isinstance(metrics["typing_speed"], (int, float))
        assert isinstance(metrics["backspace_count"], int)
        assert isinstance(metrics["backspace_rate"], float)
        # Verify internal deques hold only timestamps
        assert len(tracker._strokes) == 0
        assert len(tracker._backspaces) == 0
