"""
Vihara - Standalone desktop application entry point.
Used by PyInstaller and direct launcher.
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path
root = Path(__file__).resolve().parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from bihari.__main__ import main

if __name__ == "__main__":
    main()
