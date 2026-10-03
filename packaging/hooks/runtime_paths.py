"""
Vihara - PyInstaller Runtime Path Initialization Hook.

Ensures bundled static data, packs, and assets are discoverable relative to
sys._MEIPASS when executing in a frozen environment.
"""

import os
import sys
from pathlib import Path

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    bundle_dir = Path(sys._MEIPASS)
    os.environ["VIHARA_BUNDLE_DIR"] = str(bundle_dir)
    # Ensure bundle root is in sys.path
    if str(bundle_dir) not in sys.path:
        sys.path.insert(0, str(bundle_dir))
