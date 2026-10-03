"""
Native Windows 11 system tray integration using win32gui.

Provides a robust, native system tray icon and popup context menu
(Pause, Resume, Open Meme Folder, Fetch / Refresh Memes, Quit)
using pure Win32 APIs without relying on fragile ctypes wrapper libraries.
Automatically attaches to the interactive 'Default' desktop station.
"""

import os
import time
import ctypes
import logging
import tempfile
from typing import Any, Callable, Optional

import win32gui
import win32con
import win32api
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

IDM_PAUSE = 1001
IDM_RESUME = 1002
IDM_OPEN_MEMES = 1003
IDM_TEST_MEME = 1004
IDM_REFRESH_MEMES = 1005
IDM_QUIT = 1006
IDM_TRACK_VIHARA = 1007
IDM_TRACK_BIHARI = 1008


def ensure_default_desktop():
    """Ensure the calling thread is attached to the interactive Default desktop."""
    try:
        user32 = ctypes.windll.user32
        hdesk = user32.OpenDesktopW("Default", 0, False, 0x01FF)  # GENERIC_ALL
        if hdesk:
            user32.SetThreadDesktop(hdesk)
    except Exception as e:
        logger.debug(f"Could not switch to Default desktop: {e}")


def _create_default_icon(letter: str = "V", is_vihara: bool = True) -> Image.Image:
    """Create a high-contrast tray icon programmatically matching the active brand track."""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if is_vihara:
        # Vihara Track B: Crisp platinum ring, Prussian Slate center
        draw.ellipse([2, 2, size - 3, size - 3], fill=(240, 245, 255, 255))
        draw.ellipse([5, 5, size - 6, size - 6], fill=(11, 27, 43, 255))
    else:
        # Bihari Track A: Crisp white ring, vibrant cobalt blue center
        draw.ellipse([2, 2, size - 3, size - 3], fill=(240, 240, 255, 255))
        draw.ellipse([5, 5, size - 6, size - 6], fill=(30, 110, 235, 255))

    # Center letter
    try:
        font = ImageFont.truetype("segoeuib.ttf", 36)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("segoeui.ttf", 34)
        except (OSError, IOError):
            font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), letter, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (size - text_w) // 2
    y = (size - text_h) // 2 - 3
    draw.text((x, y), letter, fill=(255, 255, 255, 255), font=font)

    return img


class SystemTray:
    """
    Native Win32 system tray icon with context menu.

    Menu items:
      - Pause: Pause vibe detection and meme delivery
      - Resume: Resume detection
      - Open Meme Folder: Opens the meme directory in Explorer
      - Fetch / Refresh Memes: Seeds memes from Reddit
      - Quit: Clean shutdown
    """

    WM_TRAY = win32con.WM_USER + 20

    def __init__(
        self,
        on_pause: Callable,
        on_resume: Callable,
        on_quit: Callable,
        on_open_memes: Callable,
        on_refresh_memes: Optional[Callable] = None,
        on_test_meme: Optional[Callable] = None,
        on_toggle_track: Optional[Callable[[str], None]] = None,
        brand_track: str = "vihara",
    ):
        self.on_pause = on_pause
        self.on_resume = on_resume
        self.on_quit = on_quit
        self.on_open_memes = on_open_memes
        self.on_refresh_memes = on_refresh_memes
        self.on_test_meme = on_test_meme
        self.on_toggle_track = on_toggle_track
        self.brand_track = brand_track

        self.hwnd = None
        self.hicon = None
        self.ico_path = None
        self._running = False
        self._class_atom = None
        self._hinstance = None
        self.custom_tooltip: Optional[str] = None

    def get_tooltip(self) -> str:
        """Return dynamic tray tooltip according to custom override or brand track."""
        if hasattr(self, "custom_tooltip") and self.custom_tooltip:
            return self.custom_tooltip
        if str(self.brand_track).lower() in ("bihari", "consumer", "savage"):
            return "Becoming a Bihari — Savage Mindfulness Mirror"
        return "Vihara — Mindful Focus Catalyst"

    def update_tooltip(self, tooltip: str) -> None:
        """Update system tray hover tooltip dynamically."""
        self.custom_tooltip = tooltip
        if self.hwnd:
            try:
                nid = (
                    self.hwnd,
                    1,
                    win32gui.NIF_TIP,
                    self.WM_TRAY,
                    self.hicon,
                    tooltip,
                )
                win32gui.Shell_NotifyIcon(win32gui.NIM_MODIFY, nid)
            except Exception as e:
                logger.debug(f"Failed to update tray tooltip: {e}")

    def update_icon(self, icon_data: Any = None) -> None:
        """Update system tray icon handle dynamically."""
        pass

    def show_notification(self, title: str, message: str) -> None:
        """Display native Win32 balloon notification via Shell_NotifyIcon."""
        if not self.hwnd:
            return
        try:
            nid = (
                self.hwnd,
                1,
                win32gui.NIF_INFO,
                self.WM_TRAY,
                self.hicon,
                self.get_tooltip(),
                message,
                200,
                title,
                win32gui.NIIF_INFO,
            )
            win32gui.Shell_NotifyIcon(win32gui.NIM_MODIFY, nid)
        except Exception as e:
            logger.debug(f"Failed to display tray notification: {e}")

    def _create_icon_handle(self):
        """Generate a multi-resolution .ico from the default image and load it."""
        is_vihara = str(self.brand_track).lower() not in ("bihari", "consumer", "savage")
        letter = "V" if is_vihara else "B"
        img = _create_default_icon(letter=letter, is_vihara=is_vihara)
        with tempfile.NamedTemporaryFile(suffix=".ico", delete=False) as f:
            self.ico_path = f.name
            img.save(
                self.ico_path,
                format="ICO",
                sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64)],
            )

        self.hicon = win32gui.LoadImage(
            0,
            self.ico_path,
            win32con.IMAGE_ICON,
            0,
            0,
            win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE,
        )

    def set_brand_track(self, track: str):
        """Dynamically update brand track, icon, and tooltip while tray is running."""
        self.brand_track = track
        if self.hwnd:
            old_hicon = self.hicon
            old_ico_path = self.ico_path
            try:
                self._create_icon_handle()
                nid = (
                    self.hwnd,
                    1,
                    win32gui.NIF_ICON | win32gui.NIF_TIP,
                    self.WM_TRAY,
                    self.hicon,
                    self.get_tooltip(),
                )
                win32gui.Shell_NotifyIcon(win32gui.NIM_MODIFY, nid)
            except Exception as e:
                logger.debug(f"Failed to update tray icon: {e}")
            finally:
                if old_hicon:
                    try:
                        win32gui.DestroyIcon(old_hicon)
                    except Exception:
                        pass
                if old_ico_path and os.path.exists(old_ico_path):
                    try:
                        os.remove(old_ico_path)
                    except OSError:
                        pass

    def _show_menu(self):
        """Pop up the context menu at the current cursor position."""
        menu = win32gui.CreatePopupMenu()
        win32gui.AppendMenu(menu, win32con.MF_STRING, IDM_PAUSE, "Pause")
        win32gui.AppendMenu(menu, win32con.MF_STRING, IDM_RESUME, "Resume")
        win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 0, "")

        # Reflection Mode toggle submenu
        mode_menu = win32gui.CreatePopupMenu()
        is_bihari = str(self.brand_track).lower() in ("bihari", "consumer", "savage")
        vihara_flags = win32con.MF_STRING | (win32con.MF_UNCHECKED if is_bihari else win32con.MF_CHECKED)
        bihari_flags = win32con.MF_STRING | (win32con.MF_CHECKED if is_bihari else win32con.MF_UNCHECKED)
        win32gui.AppendMenu(mode_menu, vihara_flags, IDM_TRACK_VIHARA, "Dignified (Vihara)")
        win32gui.AppendMenu(mode_menu, bihari_flags, IDM_TRACK_BIHARI, "Savage (Bihari)")
        win32gui.AppendMenu(menu, win32con.MF_POPUP, mode_menu, "Reflection Mode")

        win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 0, "")
        win32gui.AppendMenu(menu, win32con.MF_STRING, IDM_OPEN_MEMES, "Open Meme Folder")

        if self.on_test_meme:
            win32gui.AppendMenu(
                menu, win32con.MF_STRING, IDM_TEST_MEME, "Show Test Reflection Now"
            )

        if self.on_refresh_memes:
            win32gui.AppendMenu(
                menu, win32con.MF_STRING, IDM_REFRESH_MEMES, "Fetch / Refresh Memes"
            )

        win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 0, "")
        win32gui.AppendMenu(menu, win32con.MF_STRING, IDM_QUIT, "Quit")

        pos = win32gui.GetCursorPos()
        win32gui.SetForegroundWindow(self.hwnd)
        cmd = win32gui.TrackPopupMenu(
            menu,
            win32con.TPM_LEFTALIGN | win32con.TPM_RIGHTBUTTON | win32con.TPM_RETURNCMD,
            pos[0],
            pos[1],
            0,
            self.hwnd,
            None,
        )
        win32gui.PostMessage(self.hwnd, win32con.WM_NULL, 0, 0)
        win32gui.DestroyMenu(menu)

        if cmd == IDM_TRACK_VIHARA:
            self.set_brand_track("vihara")
            if self.on_toggle_track:
                self.on_toggle_track("vihara")
        elif cmd == IDM_TRACK_BIHARI:
            self.set_brand_track("bihari")
            if self.on_toggle_track:
                self.on_toggle_track("bihari")
        elif cmd == IDM_PAUSE:
            self.on_pause()
        elif cmd == IDM_RESUME:
            self.on_resume()
        elif cmd == IDM_OPEN_MEMES:
            self.on_open_memes()
        elif cmd == IDM_TEST_MEME and self.on_test_meme:
            self.on_test_meme()
        elif cmd == IDM_REFRESH_MEMES and self.on_refresh_memes:
            self.on_refresh_memes()
        elif cmd == IDM_QUIT:
            self.on_quit()

    def _wnd_proc(self, hwnd, msg, wp, lp):
        if msg == self.WM_TRAY:
            if lp == win32con.WM_RBUTTONUP:
                self._show_menu()
            elif lp == win32con.WM_LBUTTONUP:
                self._show_menu()
        elif msg == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0)

        return win32gui.DefWindowProc(hwnd, msg, wp, lp)

    def run(self):
        """Start the native tray icon and pump messages."""
        ensure_default_desktop()
        self._running = True

        self._create_icon_handle()

        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = self._wnd_proc
        wc.lpszClassName = "ViharaNativeTrayWindow"
        self._hinstance = wc.hInstance = win32gui.GetModuleHandle(None)
        self._class_atom = win32gui.RegisterClass(wc)

        self.hwnd = win32gui.CreateWindow(
            self._class_atom,
            "ViharaTrayWindow",
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            self._hinstance,
            None,
        )

        nid = (
            self.hwnd,
            1,
            win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP,
            self.WM_TRAY,
            self.hicon,
            self.get_tooltip(),
        )
        win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)
        logger.info(f"System tray icon added successfully ({self.get_tooltip()}).")

        # Pump message loop
        while self._running:
            win32gui.PumpWaitingMessages()
            time.sleep(0.05)

        # Cleanup
        try:
            win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, (self.hwnd, 1))
        except Exception:
            pass

        if self.hicon:
            try:
                win32gui.DestroyIcon(self.hicon)
            except Exception:
                pass

        if self.hwnd:
            try:
                win32gui.DestroyWindow(self.hwnd)
            except Exception:
                pass

        if self._class_atom and self._hinstance:
            try:
                win32gui.UnregisterClass(self._class_atom, self._hinstance)
            except Exception:
                pass

        if self.ico_path and os.path.exists(self.ico_path):
            try:
                os.remove(self.ico_path)
            except OSError:
                pass

        logger.info("System tray icon removed.")

    def stop(self):
        """Signal the message loop to stop."""
        self._running = False
