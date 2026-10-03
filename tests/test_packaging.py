"""
Automated Test Suite for Milestone 4: Windows Installer & Standalone Packaging.

Validates:
- F11: Standalone PyInstaller onedir build spec (packaging/windows/vihara.spec)
- F12: Lowest-privilege Inno Setup installer (packaging/windows/installer.iss)
- F13: Clean Windows Settings > Apps uninstaller
- F14: Configurable login auto-start registry integration
- F15: Single build command pipeline (build.bat)
- F16: Platform Abstraction Layer (bihari/pal/) and cross-platform extensibility
- Integrity: Zero occurrences of legacy name in all packaging files
"""

from __future__ import annotations

import ast
import configparser
import inspect
import os
import re
import sys
from pathlib import Path
from typing import Generator

import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
PACKAGING_DIR = WORKSPACE_ROOT / "packaging"
PAL_DIR = WORKSPACE_ROOT / "bihari" / "pal"


class TestPyInstallerSpec:
    """F11: Validates PyInstaller onedir build specification (vihara.spec)."""

    @pytest.fixture(autouse=True)
    def spec_path_and_content(self):
        self.spec_path = PACKAGING_DIR / "windows" / "vihara.spec"
        assert self.spec_path.exists(), f"Spec file not found: {self.spec_path}"
        self.content = self.spec_path.read_text(encoding="utf-8")
        return self.spec_path, self.content

    def test_spec_parses_as_valid_python(self):
        """vihara.spec must be valid Python syntax."""
        try:
            parsed = ast.parse(self.content, filename=str(self.spec_path))
            assert parsed is not None
        except SyntaxError as e:
            pytest.fail(f"vihara.spec contains syntax errors: {e}")

    def test_spec_configures_windowless_gui(self):
        """vihara.spec must enforce console=False for silent windowless GUI."""
        assert "console=False" in self.content or "console = False" in self.content, (
            "vihara.spec must specify console=False to prevent console window flashes"
        )

    def test_spec_onedir_mode_with_collect(self):
        """vihara.spec must define COLLECT for onedir compilation into dist/vihara/."""
        assert "COLLECT(" in self.content or "coll = COLLECT" in self.content
        assert 'name="vihara"' in self.content or "name='vihara'" in self.content

    def test_spec_bundles_required_data_files(self):
        """vihara.spec must bundle config.toml, default pack (.lucidpack), and meme assets."""
        assert "config.toml" in self.content, "vihara.spec must bundle config.toml"
        assert "default.lucidpack" in self.content, (
            "vihara.spec must bundle default.lucidpack"
        )
        assert "memes" in self.content, "vihara.spec must bundle memes/ assets"

    def test_spec_includes_all_runtime_dependencies(self):
        """vihara.spec must include pywin32, pynput, pystray, Pillow, psutil, winocr, tomli."""
        required_imports = [
            "PIL",
            "pystray",
            "win32gui",
            "pynput",
            "psutil",
            "winocr",
            "tomli",
            "bihari.pal",
        ]
        for imp in required_imports:
            assert imp in self.content, f"vihara.spec missing hidden import: {imp}"

    def test_spec_excludes_heavy_machine_learning_libraries(self):
        """vihara.spec must explicitly exclude torch, cuda, scipy, matplotlib, pandas."""
        required_excludes = ["torch", "cuda", "scipy", "matplotlib", "pandas"]
        for exc in required_excludes:
            assert exc in self.content, f"vihara.spec missing exclusion: {exc}"

    def test_spec_embeds_windows_version_resource_metadata(self):
        """vihara.spec must embed Windows version resource metadata (Name, Version, Publisher, Description)."""
        version_info_path = PACKAGING_DIR / "windows" / "version_info.txt"
        assert version_info_path.exists(), f"Version info file missing: {version_info_path}"

        v_content = version_info_path.read_text(encoding="utf-8")
        assert "Vihara" in v_content, "Version resource must contain ProductName 'Vihara'"
        assert "1.0.0" in v_content, "Version resource must contain ProductVersion '1.0.0'"
        assert "Vihara Team" in v_content, "Version resource must contain CompanyName 'Vihara Team'"
        assert "Vihara Desktop Mindfulness Mirror" in v_content, (
            "Version resource must contain FileDescription 'Vihara Desktop Mindfulness Mirror'"
        )


class TestInnoSetupScript:
    """F12, F13, F14: Validates Inno Setup 6 installer script (installer.iss)."""

    @pytest.fixture(autouse=True)
    def iss_path_and_content(self):
        self.iss_path = PACKAGING_DIR / "windows" / "installer.iss"
        assert self.iss_path.exists(), f"installer.iss not found: {self.iss_path}"
        self.content = self.iss_path.read_text(encoding="utf-8")
        return self.iss_path, self.content

    def test_privileges_required_lowest_zero_uac(self):
        """F12: installer.iss must specify PrivilegesRequired=lowest for zero UAC elevation."""
        pattern = re.compile(r"^\s*PrivilegesRequired\s*=\s*lowest\s*$", re.IGNORECASE | re.MULTILINE)
        assert pattern.search(self.content), (
            "installer.iss must define PrivilegesRequired=lowest to avoid UAC prompt"
        )

    def test_targets_per_user_localappdata_directory(self):
        """F12: installer.iss must install to {localappdata}\\Programs\\Vihara."""
        pattern = re.compile(
            r"^\s*DefaultDirName\s*=\s*\{localappdata\}\\Programs\\Vihara\s*$",
            re.IGNORECASE | re.MULTILINE,
        )
        assert pattern.search(self.content), (
            "installer.iss must target {localappdata}\\Programs\\Vihara"
        )

    def test_packages_pyinstaller_payload_into_installer(self):
        """F12: installer.iss must package dist/vihara/ into Vihara-Setup-x64.exe."""
        assert "OutputBaseFilename=Vihara-Setup-x64" in self.content
        assert "OutputDir=..\\..\\dist\\installers" in self.content
        assert r"dist\vihara\*" in self.content

    def test_creates_start_menu_and_desktop_shortcuts(self):
        """F12: installer.iss must create Start Menu shortcut and optional Desktop shortcut."""
        assert "{autoprograms}" in self.content, "Must create Start Menu shortcut in {autoprograms}"
        assert "{autodesktop}" in self.content, "Must create optional Desktop shortcut in {autodesktop}"
        assert "Name: \"desktopicon\"" in self.content or "Name: 'desktopicon'" in self.content

    def test_registers_configurable_login_startup_in_hkcu(self):
        """F14: installer.iss must register HKCU Run key for login auto-start with task toggle."""
        assert "Root: HKCU" in self.content
        assert r"Software\Microsoft\Windows\CurrentVersion\Run" in self.content
        assert "ValueName: \"Vihara\"" in self.content or "ValueName: 'Vihara'" in self.content
        assert "startupentry" in self.content, "Must bind auto-start to installer task checkbox"

    def test_registers_clean_uninstaller_in_windows_settings_apps(self):
        """F13: installer.iss must register clean uninstaller in Windows Settings > Apps."""
        assert "UninstallDisplayName=" in self.content
        assert "Vihara" in self.content
        assert "UninstallDisplayIcon=" in self.content

    def test_launches_application_post_install_silently_without_admin(self):
        """F12: installer.iss must launch application post-install in user session."""
        assert "[Run]" in self.content
        assert "postinstall" in self.content
        assert "nowait" in self.content


class TestBuildBatPipeline:
    """F15: Validates single build command pipeline (build.bat)."""

    @pytest.fixture(autouse=True)
    def bat_path_and_content(self):
        self.bat_path = WORKSPACE_ROOT / "build.bat"
        assert self.bat_path.exists(), f"build.bat not found at root: {self.bat_path}"
        self.content = self.bat_path.read_text(encoding="utf-8")
        return self.bat_path, self.content

    def test_build_bat_checks_python_environment(self):
        """build.bat must verify Python is on PATH."""
        assert "python --version" in self.content

    def test_build_bat_checks_and_runs_pyinstaller(self):
        """build.bat must invoke PyInstaller with vihara.spec."""
        assert "vihara.spec" in self.content
        assert "PyInstaller" in self.content

    def test_build_bat_handles_inno_setup_compiler(self):
        """build.bat must look for ISCC.exe and compile installer.iss."""
        assert "ISCC" in self.content
        assert "installer.iss" in self.content

    def test_build_bat_reports_clean_output_paths_and_exit_codes(self):
        """build.bat must handle ERRORLEVEL and exit codes cleanly."""
        assert "ERRORLEVEL" in self.content
        assert "exit /b" in self.content
        assert "dist\\vihara" in self.content


class TestPlatformAbstractionLayer:
    """F16: Validates Platform Abstraction Layer (bihari/pal/) architecture and interfaces."""

    def test_pal_package_structure(self):
        """bihari/pal/ must contain __init__.py, base.py, and windows.py."""
        assert (PAL_DIR / "__init__.py").exists()
        assert (PAL_DIR / "base.py").exists()
        assert (PAL_DIR / "windows.py").exists()

    def test_base_interfaces_are_abstract(self):
        """base.py must define abstract interfaces for window, OCR sensor, and tray driver."""
        from bihari.pal.base import (
            ActiveWindowInfo,
            BaseScreenSensor,
            BaseTrayDriver,
            BaseWindowObserver,
        )

        assert inspect.isabstract(BaseWindowObserver)
        assert inspect.isabstract(BaseScreenSensor)
        assert inspect.isabstract(BaseTrayDriver)

        # Verify abstract methods
        assert "get_active_window" in BaseWindowObserver.__abstractmethods__
        assert "register_switch_hook" in BaseWindowObserver.__abstractmethods__
        assert "extract_context_text" in BaseScreenSensor.__abstractmethods__
        assert "create_tray" in BaseTrayDriver.__abstractmethods__

    def test_active_window_info_dataclass(self):
        """ActiveWindowInfo must be immutable and provide empty checks."""
        from bihari.pal.base import ActiveWindowInfo

        empty_info = ActiveWindowInfo()
        assert empty_info.is_empty
        assert empty_info.hwnd == 0

        valid_info = ActiveWindowInfo(hwnd=12345, title="Vihara Workspace", app_name="code.exe", pid=999)
        assert not valid_info.is_empty
        assert valid_info.title == "Vihara Workspace"
        assert valid_info.app_name == "code.exe"

    def test_windows_driver_implements_interfaces(self):
        """windows.py must implement all abstract methods of the PAL base interfaces."""
        from bihari.pal.base import (
            BaseScreenSensor,
            BaseTrayDriver,
            BaseWindowObserver,
        )
        from bihari.pal.windows import (
            Win32ScreenSensor,
            Win32TrayDriver,
            Win32WindowObserver,
        )

        assert issubclass(Win32WindowObserver, BaseWindowObserver)
        assert issubclass(Win32ScreenSensor, BaseScreenSensor)
        assert issubclass(Win32TrayDriver, BaseTrayDriver)

        # Concrete classes must not be abstract
        assert not inspect.isabstract(Win32WindowObserver)
        assert not inspect.isabstract(Win32ScreenSensor)
        assert not inspect.isabstract(Win32TrayDriver)

    def test_pal_factory_functions(self):
        """bihari.pal factory functions must return valid driver instances."""
        import bihari.pal as pal

        observer = pal.get_window_observer()
        sensor = pal.get_screen_sensor()
        tray = pal.get_tray_driver()

        assert isinstance(observer, pal.BaseWindowObserver)
        assert isinstance(sensor, pal.BaseScreenSensor)
        assert isinstance(tray, pal.BaseTrayDriver)

        # Query helper should not raise exceptions
        info = pal.get_active_window_info()
        assert info is None or isinstance(info, pal.ActiveWindowInfo)

    def test_pal_windows_driver_graceful_execution(self):
        """Win32 drivers must run without raising unhandled exceptions."""
        from bihari.pal.windows import Win32ScreenSensor, Win32WindowObserver

        if sys.platform == "win32":
            obs = Win32WindowObserver()
            info = obs.get_active_window()
            # On Windows, info can be ActiveWindowInfo or None, but must not throw
            assert info is None or info.is_valid

            sensor = Win32ScreenSensor()
            # Should safely degrade if winocr or permission not present
            text = sensor.extract_context_text(info)
            assert text is None or isinstance(text, str)

    def test_win32_tray_driver_lifecycle_and_delegation(self):
        """Win32TrayDriver must initialize genuine tray instance and support methods."""
        from bihari.pal.windows import Win32TrayDriver
        from bihari.tray import SystemTray

        driver = Win32TrayDriver()
        assert driver.is_supported() == (sys.platform == "win32")

        ret = driver.create_tray("Vihara Test", "Vihara — Test Tooltip")
        assert ret is driver
        assert driver._icon is not None
        assert isinstance(driver._icon, SystemTray)
        assert driver._tray is driver._icon

        driver.update_tooltip("Updated Tooltip")
        assert driver._tooltip == "Updated Tooltip"

        driver.show_notification("Title", "Message")
        driver.stop()
        assert driver._icon is None
        assert driver._tray is None



class TestCrossPlatformPackaging:
    """F16: Validates cross-platform packaging scripts for macOS and Linux."""

    def test_macos_packaging_pipeline_specification(self):
        """packaging/mac/build_dmg.sh and entitlements.plist must exist and specify pipeline."""
        build_dmg = PACKAGING_DIR / "mac" / "build_dmg.sh"
        entitlements = PACKAGING_DIR / "mac" / "entitlements.plist"

        assert build_dmg.exists(), f"macOS build script missing: {build_dmg}"
        assert entitlements.exists(), f"macOS entitlements missing: {entitlements}"

        dmg_content = build_dmg.read_text(encoding="utf-8")
        assert "pyinstaller" in dmg_content.lower()
        assert "codesign" in dmg_content
        assert "notarytool" in dmg_content
        assert "Vihara" in dmg_content

        ent_content = entitlements.read_text(encoding="utf-8")
        assert "com.apple.security.cs.allow-jit" in ent_content

    def test_linux_packaging_pipeline_specification(self):
        """packaging/linux/build_appimage.sh and vihara.desktop must exist and specify pipeline."""
        build_appimage = PACKAGING_DIR / "linux" / "build_appimage.sh"
        desktop = PACKAGING_DIR / "linux" / "vihara.desktop"

        assert build_appimage.exists(), f"Linux build script missing: {build_appimage}"
        assert desktop.exists(), f"Linux desktop file missing: {desktop}"

        appimage_content = build_appimage.read_text(encoding="utf-8")
        assert "pyinstaller" in appimage_content.lower()
        assert "AppDir" in appimage_content
        assert "appimagetool" in appimage_content
        assert "Vihara" in appimage_content

        desktop_content = desktop.read_text(encoding="utf-8")
        assert "[Desktop Entry]" in desktop_content
        assert "Name=Vihara" in desktop_content


class TestZeroLegacyBrandingInPackaging:
    """Acceptance Criteria: Zero occurrences of legacy name in packaging, build, PAL, and tests."""

    def test_zero_legacy_branding_in_all_packaging_files(self):
        """Assert zero occurrences of the legacy brand string (case-insensitive) across packaging and PAL."""
        forbidden = "lucid" + " " + "noether"
        targets = [
            PACKAGING_DIR,
            PAL_DIR,
            WORKSPACE_ROOT / "build.bat",
            WORKSPACE_ROOT / "tests" / "test_packaging.py",
        ]

        occurrences = []
        for target in targets:
            if target.is_file():
                content = target.read_text(encoding="utf-8", errors="ignore")
                if target.name == "test_packaging.py":
                    # Check for literal occurrences outside the dynamic checker
                    lines = [line for line in content.splitlines() if 'forbidden = "lucid"' not in line]
                    sanitized_content = "\n".join(lines)
                    if forbidden in sanitized_content.lower():
                        occurrences.append(str(target.relative_to(WORKSPACE_ROOT)))
                elif forbidden in content.lower():
                    occurrences.append(str(target.relative_to(WORKSPACE_ROOT)))
            elif target.is_dir():
                for root, _, files in os.walk(target):
                    for file in files:
                        p = Path(root) / file
                        try:
                            content = p.read_text(encoding="utf-8", errors="ignore")
                            if forbidden in content.lower():
                                occurrences.append(str(p.relative_to(WORKSPACE_ROOT)))
                        except Exception:
                            pass

        assert not occurrences, (
            f"Found legacy brand string in packaging/PAL files: {occurrences}"
        )
