"""
Configuration loader for Becoming a Bihari.

Reads config.toml from the project root directory.
Falls back to sensible defaults for every key.
"""

import os
import sys
from pathlib import Path
from typing import Any

# Use stdlib tomllib on 3.11+, fall back to tomli
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None  # type: ignore


# ── Default configuration ──

DEFAULTS: dict[str, Any] = {
    "general": {
        "brand_track": "vihara",  # "vihara" (dignified stoic focus) | "bihari" (savage roast mirror)
        "poll_interval_ms": 500,
        "meme_cooldown_seconds": 300,
        "social_cooldown_seconds": 60,
        "idle_timeout_seconds": 300,
    },
    "paths": {
        "meme_dir": "",  # Empty = %LOCALAPPDATA%\Vihara\memes (with fallback to %LOCALAPPDATA%\Bihari\memes)
    },
    "privacy": {
        "blocked_apps": [
            "KeePassXC.exe",
            "1Password.exe",
            "Bitwarden.exe",
        ],
        "blocked_title_keywords": [
            "bank",
            "sign in",
            "login",
            "checkout",
            "password",
            "credit card",
            "payment",
            "connexion",
            "iniciar sesión",
        ],
        "clear_clipboard": False,
    },
    "inference": {
        "use_laya": True,
        "confidence_threshold": 0.55,
    },
    "display": {
        "duration_ms": 4000,
        "opacity": 0.95,
        "width": 350,
        "height": 300,
        "slide_animation": True,
    },
    "fetcher": {
        "online_fetch": False,
        "min_threshold": 3,
        "target_count": 10,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base, returning a new dict."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _find_config_file() -> Path | None:
    """Search for config.toml in common locations."""
    candidates = [
        Path.cwd() / "config.toml",
        Path(__file__).resolve().parent.parent / "config.toml",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    """
    Load configuration from TOML file, merged with defaults.

    Args:
        config_path: Explicit path to config.toml. If None, searches common locations.

    Returns:
        Complete configuration dict with all defaults filled in.
    """
    user_config: dict[str, Any] = {}

    if config_path is None:
        config_path = _find_config_file()

    if config_path and config_path.is_file():
        if tomllib is None:
            # No TOML parser available — use defaults only
            import logging
            logging.getLogger(__name__).warning(
                "No TOML parser available (install 'tomli' for Python <3.11). "
                "Using default configuration."
            )
        else:
            with open(config_path, "rb") as f:
                user_config = tomllib.load(f)

    config = _deep_merge(DEFAULTS, user_config)

    # Resolve meme directory
    if not config["paths"]["meme_dir"]:
        local_app_data = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
        vihara_memes = Path(local_app_data) / "Vihara" / "memes"
        bihari_memes = Path(local_app_data) / "Bihari" / "memes"
        if not vihara_memes.exists() and bihari_memes.exists():
            config["paths"]["meme_dir"] = str(bihari_memes)
        else:
            config["paths"]["meme_dir"] = str(vihara_memes)

    return config
