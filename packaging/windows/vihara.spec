# -*- mode: python ; coding: utf-8 -*-
"""
Vihara - Production PyInstaller onedir Build Specification.

Compiles bihari/__main__.py into a self-contained, windowless distribution (dist/vihara/)
bundling all runtime dependencies, default pack, config, and assets.
"""

import os
import sys
from pathlib import Path

# Spec directory is packaging/windows, project root is 2 levels up
SPEC_DIR = Path(SPECPATH).resolve() if "SPECPATH" in globals() else Path(__file__).resolve().parent
PROJECT_ROOT = SPEC_DIR.parent.parent

# 1. Bundled Static Data Files
added_datas = [
    (str(PROJECT_ROOT / "config.toml"), "."),
    (str(PROJECT_ROOT / "packs" / "default.lucidpack"), "packs"),
    (str(PROJECT_ROOT / "memes"), "memes"),
    (str(PROJECT_ROOT / "bihari" / "models" / "base_brain.json"), "bihari/models"),
]

# 2. Hidden Imports for Platform and Dependencies
hidden_imports = [
    "bihari.micro_model",
    "PIL",
    "PIL.Image",
    "PIL.ImageTk",
    "PIL._tkinter_finder",
    "pystray",
    "sqlite3",
    "tomllib" if sys.version_info >= (3, 11) else "tomli",
    "tomli",
    "queue",
    "dataclasses",
    "typing_extensions",
    "psutil",
    "winocr",
    "win32gui",
    "win32con",
    "win32process",
    "win32api",
    "win32ui",
    "pynput",
    "pynput.keyboard._win32",
    "pynput.mouse._win32",
    "bihari.pal",
    "bihari.pal.base",
    "bihari.pal.windows",
]

# 3. Explicit Exclusions (Eliminating bloat from core distribution)
excluded_modules = [
    "torch",
    "torchvision",
    "torchaudio",
    "cuda",
    "scipy",
    "matplotlib",
    "pandas",
    "numpy.distutils",
    "IPython",
    "jupyter",
    "unittest",
    "test",
]

# 4. Version Resource Metadata and Icon
version_file = str(SPEC_DIR / "version_info.txt")
icon_file = str(PROJECT_ROOT / "packaging" / "icons" / "app_icon.ico")
runtime_hook_file = str(PROJECT_ROOT / "packaging" / "hooks" / "runtime_paths.py")

runtime_hooks = [runtime_hook_file] if os.path.exists(runtime_hook_file) else []

a = Analysis(
    [str(PROJECT_ROOT / "run_vihara.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=added_datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=runtime_hooks,
    excludes=excluded_modules,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="vihara",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=["vcruntime140.dll", "python*.dll"],
    console=False,  # Windowless GUI: zero console window flashes
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    icon=icon_file if os.path.exists(icon_file) else None,
    version=version_file if os.path.exists(version_file) else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name="vihara",
)
