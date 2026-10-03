"""
Module 4: THE DISPLAY ENGINE — Meme overlay and modal viewer.

Features:
  1. Corner Toast Notification:
     - Borderless, topmost card sliding in at bottom-right corner.
     - Top-right '✕' button for instant dismiss.
     - Hovering pauses the auto-dismiss timer.
     - Clicking the meme opens the enlarged modal view.
  2. Enlarged Modal Viewer:
     - Expands the meme to a high-resolution, centered modal on screen.
     - Displays vibe tag, full image, and action buttons ('Close (Esc)', 'Open Folder').
     - Closes via '✕' button, Escape key, or Close button.

Threading safety:
  All display methods must be called on the main (tkinter) thread.
"""

import os
import tkinter as tk
from pathlib import Path
from typing import Optional
import logging

from PIL import Image, ImageTk

logger = logging.getLogger(__name__)

# ── Fix DPI scaling on Windows 11 ──
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
except Exception:
    pass


class MemeOverlay:
    """
    Manages meme toast notifications and enlarged modal viewing.
    """

    def __init__(
        self,
        root: tk.Tk,
        width: int = 340,
        height: int = 290,
        duration_ms: int = 4000,
        opacity: float = 0.96,
        slide_animation: bool = True,
        brand_track: str = "vihara",
    ):
        self.root = root
        self.width = width
        self.height = height
        self.duration_ms = duration_ms
        self.opacity = opacity
        self.slide_animation = slide_animation
        self.brand_track = brand_track

        self._toast_window: Optional[tk.Toplevel] = None
        self._modal_window: Optional[tk.Toplevel] = None
        self._toast_photo = None
        self._modal_photo = None
        self._dismiss_job = None
        self._current_image_path: Optional[Path] = None
        self._current_label: str = ""

        # GIF animation state
        self._toast_gif_frames: list = []
        self._toast_gif_idx: int = 0
        self._toast_gif_job = None
        self._modal_gif_frames: list = []
        self._modal_gif_idx: int = 0
        self._modal_gif_job = None

    def set_brand_track(self, brand_track: str):
        """Update active brand track styling."""
        self.brand_track = brand_track

    def show(
        self,
        image_path: Optional[Path] = None,
        label: str = "",
        vibe = None,
        brand_track: Optional[str] = None,
    ):
        """
        Show a reflection toast in the bottom-right corner.
        Supports both image memes and elegant text-only fallback cards (when image is None/missing).
        Must be called from the main thread.
        """
        active_track = brand_track or self.brand_track
        is_bihari = str(active_track).lower() in ("bihari", "consumer", "track_a", "savage")

        # Visual design system per dual_track_branding_guide.md §4.1
        if is_bihari:
            bg_color = "#121212"
            header_bg = "#1e1e1e"
            text_color = "#ffffff"
            border_color = "#ff8c00"
            track_prefix = "🪞"
            default_title = "Becoming a Bihari"
        else:
            bg_color = "#0B1B2B"
            header_bg = "#162638"
            text_color = "#E2E8F0"
            border_color = "#2a4365"
            track_prefix = "⚖️"
            default_title = "Vihara • Cognitive Reset"

        # Destroy any existing toast
        self._destroy_toast()

        # Check if valid image exists
        has_image = False
        photo = None
        self._toast_gif_frames = []
        self._toast_gif_idx = 0

        if image_path:
            p = Path(image_path)
            if p.is_file() and p.exists():
                try:
                    from PIL import ImageSequence
                    img = Image.open(p)
                    is_gif = getattr(img, "is_animated", False) and img.n_frames > 1
                    if is_gif:
                        for frame in ImageSequence.Iterator(img):
                            f = frame.copy().convert("RGBA")
                            f.thumbnail((self.width - 20, self.height - 70), Image.Resampling.LANCZOS)
                            self._toast_gif_frames.append(ImageTk.PhotoImage(f))
                        photo = self._toast_gif_frames[0] if self._toast_gif_frames else ImageTk.PhotoImage(img)
                    else:
                        img.thumbnail((self.width - 20, self.height - 70), Image.Resampling.LANCZOS)
                        photo = ImageTk.PhotoImage(img)
                    has_image = True
                    self._current_image_path = p
                except Exception as e:
                    logger.warning(f"Failed to load image {image_path}, using text reflection: {e}")
                    has_image = False

        if not has_image:
            self._current_image_path = None

        self._current_label = label

        # Dimensions: text-only card is shorter and sleeker
        toast_w = max(self.width, 360)
        toast_h = self.height if has_image else 125

        try:
            # ── Create Toast Window ──
            win = tk.Toplevel(self.root)
            win.overrideredirect(True)          # Borderless
            win.attributes("-topmost", True)    # Always on top
            win.configure(bg=bg_color)

            try:
                win.attributes("-alpha", self.opacity)
            except tk.TclError:
                pass

            # ── Screen geometry ──
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            x = screen_w - toast_w - 20
            y_final = screen_h - toast_h - 60  # Above taskbar

            # Outer framed card
            card_frame = tk.Frame(win, bg=bg_color, highlightbackground=border_color, highlightthickness=1)
            card_frame.pack(fill="both", expand=True)

            # ── Header bar (vibe title + close button) ──
            header = tk.Frame(card_frame, bg=header_bg)
            header.pack(fill="x", side="top")

            btn_close = tk.Label(
                header,
                text="✕",
                fg="#a1a1aa",
                bg=header_bg,
                font=("Segoe UI", 10, "bold"),
                cursor="hand2",
                padx=8,
                pady=4,
            )
            btn_close.pack(side="right", anchor="ne", padx=4)
            btn_close.bind("<Button-1>", lambda e: self._destroy_toast())
            btn_close.bind("<Enter>", lambda e: btn_close.configure(fg="#ffffff", bg="#dc2626"))
            btn_close.bind("<Leave>", lambda e: btn_close.configure(fg="#a1a1aa", bg=header_bg))

            # Header title text
            if has_image:
                title_text = f"{track_prefix} {label}" if label else f"{track_prefix} {default_title}"
            else:
                title_text = f"{track_prefix} {default_title}"

            lbl_vibe = tk.Label(
                header,
                text=title_text,
                fg=text_color,
                bg=header_bg,
                font=("Segoe UI", 9, "bold"),
                wraplength=toast_w - 45,
                justify="left",
                anchor="w",
            )
            lbl_vibe.pack(side="left", fill="both", expand=True, padx=8, pady=4)

            if has_image and photo:
                # ── Image panel ──
                self._toast_photo = photo
                img_label = tk.Label(card_frame, image=photo, bg=bg_color, cursor="hand2")
                img_label.pack(padx=8, pady=(4, 2))

                # Start animated GIF loop if multi-frame
                if len(self._toast_gif_frames) > 1:
                    def _play_toast_gif():
                        if not self._toast_window or not img_label.winfo_exists():
                            return
                        self._toast_gif_idx = (self._toast_gif_idx + 1) % len(self._toast_gif_frames)
                        img_label.configure(image=self._toast_gif_frames[self._toast_gif_idx])
                        self._toast_gif_job = self.root.after(100, _play_toast_gif)

                    self._toast_gif_job = self.root.after(100, _play_toast_gif)

                # Footer hint
                hint_label = tk.Label(
                    card_frame,
                    text="click to enlarge • ✕ to close",
                    fg="#829ab1" if not is_bihari else "#71717a",
                    bg=bg_color,
                    font=("Segoe UI", 8),
                    cursor="hand2",
                )
                hint_label.pack(side="bottom", pady=(0, 4))

                for widget in (img_label, hint_label):
                    widget.bind("<Button-1>", lambda e: self._show_expanded())
            else:
                # ── Text-Only Reflection Card Fallback ──
                reflection_display = label if label else "Take a quiet breath and ground your focus."
                body_frame = tk.Frame(card_frame, bg=bg_color)
                body_frame.pack(fill="both", expand=True, padx=12, pady=(6, 4))

                lbl_reflection = tk.Label(
                    body_frame,
                    text=f'"{reflection_display}"',
                    fg=text_color,
                    bg=bg_color,
                    font=("Segoe UI", 10, "italic"),
                    wraplength=toast_w - 30,
                    justify="center",
                )
                lbl_reflection.pack(fill="both", expand=True, pady=4)

                hint_text = "🌿 Mindful Reflection • Esc to close" if not is_bihari else "⚡ Savage Mirror • Esc to close"
                hint_label = tk.Label(
                    card_frame,
                    text=hint_text,
                    fg="#829ab1" if not is_bihari else "#9E9E9E",
                    bg=bg_color,
                    font=("Segoe UI", 8),
                    cursor="hand2",
                )
                hint_label.pack(side="bottom", pady=(0, 4))

                for widget in (card_frame, body_frame, lbl_reflection, hint_label):
                    widget.bind("<Button-1>", lambda e: self._destroy_toast())

            # ── Hovering pauses auto-dismiss ──
            win.bind("<Enter>", lambda e: self._pause_dismiss())
            win.bind("<Leave>", lambda e: self._resume_dismiss())
            win.bind("<Escape>", lambda e: self._destroy_toast())

            self._toast_window = win

            # ── Position and animate ──
            if self.slide_animation:
                y_start = screen_h
                win.geometry(f"{toast_w}x{toast_h}+{x}+{y_start}")
                self._animate_slide(win, x, y_start, y_final, steps=12)
            else:
                win.geometry(f"{toast_w}x{toast_h}+{x}+{y_final}")

            # ── Auto-dismiss timer ──
            self._resume_dismiss()
        except Exception as e:
            logger.error(f"Error displaying reflection card: {e}", exc_info=True)

    def _animate_slide(self, win: tk.Toplevel, x: int, y_current: float, y_target: int, steps: int):
        """Smooth slide-up animation."""
        if steps <= 0 or not win.winfo_exists():
            return

        dy = (y_target - y_current) / steps
        new_y = int(y_current + dy)

        try:
            win.geometry(f"{self.width}x{self.height}+{x}+{new_y}")
        except tk.TclError:
            return

        win.after(16, lambda: self._animate_slide(win, x, new_y, y_target, steps - 1))

    def _pause_dismiss(self):
        """Pause auto-dismiss timer on mouse hover."""
        if self._dismiss_job:
            self.root.after_cancel(self._dismiss_job)
            self._dismiss_job = None

    def _resume_dismiss(self):
        """Resume auto-dismiss timer."""
        self._pause_dismiss()
        self._dismiss_job = self.root.after(self.duration_ms, self._destroy_toast)

    def _destroy_toast(self):
        """Safely destroy the corner toast."""
        self._pause_dismiss()
        if self._toast_gif_job:
            try:
                self.root.after_cancel(self._toast_gif_job)
            except Exception:
                pass
            self._toast_gif_job = None

        if self._toast_window is not None:
            try:
                if self._toast_window.winfo_exists():
                    self._toast_window.destroy()
            except tk.TclError:
                pass
            self._toast_window = None
            self._toast_photo = None
            self._toast_gif_frames = []

    def _destroy_modal(self):
        """Safely destroy the enlarged modal window."""
        if self._modal_gif_job:
            try:
                self.root.after_cancel(self._modal_gif_job)
            except Exception:
                pass
            self._modal_gif_job = None

        if self._modal_window is not None:
            try:
                if self._modal_window.winfo_exists():
                    self._modal_window.destroy()
            except tk.TclError:
                pass
            self._modal_window = None
            self._modal_photo = None
            self._modal_gif_frames = []

    def _show_expanded(self):
        """
        Open the meme in an enlarged, centered modal viewer.
        """
        if not self._current_image_path or not self._current_image_path.exists():
            return

        # Dismiss toast and cancel timers
        self._destroy_toast()
        self._destroy_modal()

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        # Calculate maximum viewing area (up to 80% screen width and 78% screen height)
        max_view_w = int(screen_w * 0.80)
        max_view_h = int(screen_h * 0.78)

        try:
            from PIL import ImageSequence
            full_img = Image.open(self._current_image_path)
            is_gif = getattr(full_img, "is_animated", False) and full_img.n_frames > 1
            if is_gif:
                self._modal_gif_frames = []
                self._modal_gif_idx = 0
                for frame in ImageSequence.Iterator(full_img):
                    f = frame.copy().convert("RGBA")
                    f.thumbnail((max_view_w, max_view_h - 90), Image.Resampling.LANCZOS)
                    self._modal_gif_frames.append(ImageTk.PhotoImage(f))
                modal_photo = self._modal_gif_frames[0] if self._modal_gif_frames else None
                img_w = self._modal_gif_frames[0].width() if self._modal_gif_frames else 360
                img_h = self._modal_gif_frames[0].height() if self._modal_gif_frames else 260
            else:
                display_img = full_img.copy()
                display_img.thumbnail((max_view_w, max_view_h - 90), Image.Resampling.LANCZOS)
                img_w, img_h = display_img.size
                modal_photo = ImageTk.PhotoImage(display_img)
        except Exception as e:
            logger.error(f"Failed to enlarge image {self._current_image_path}: {e}")
            return

        modal_w = max(img_w + 24, 380)
        modal_h = img_h + 96

        x = (screen_w - modal_w) // 2
        y = (screen_h - modal_h) // 2

        modal = tk.Toplevel(self.root)
        modal.overrideredirect(True)          # Borderless clean frame
        modal.attributes("-topmost", True)    # Above other windows
        modal.configure(bg="#18181b")
        modal.geometry(f"{modal_w}x{modal_h}+{x}+{y}")

        # ── Header bar ──
        header = tk.Frame(modal, bg="#27272a", height=34)
        header.pack(fill="x", side="top")

        tag_label = self._current_label if self._current_label else "a moment"
        lbl_title = tk.Label(
            header,
            text=f"🪞 {tag_label}",
            fg="#f4f4f5",
            bg="#27272a",
            font=("Segoe UI", 10, "bold"),
        )
        lbl_title.pack(side="left", padx=12, pady=6)

        btn_modal_x = tk.Label(
            header,
            text="✕",
            fg="#a1a1aa",
            bg="#27272a",
            font=("Segoe UI", 11, "bold"),
            cursor="hand2",
            padx=8,
        )
        btn_modal_x.pack(side="right", padx=6)
        btn_modal_x.bind("<Button-1>", lambda e: self._destroy_modal())
        btn_modal_x.bind("<Enter>", lambda e: btn_modal_x.configure(fg="#ffffff", bg="#dc2626"))
        btn_modal_x.bind("<Leave>", lambda e: btn_modal_x.configure(fg="#a1a1aa", bg="#27272a"))

        # ── Large Image panel ──
        self._modal_photo = modal_photo
        panel = tk.Label(modal, image=modal_photo, bg="#18181b")
        panel.pack(padx=10, pady=8)

        # Loop modal GIF animation if multi-frame
        if len(self._modal_gif_frames) > 1:
            def _play_modal_gif():
                if not self._modal_window or not panel.winfo_exists():
                    return
                self._modal_gif_idx = (self._modal_gif_idx + 1) % len(self._modal_gif_frames)
                panel.configure(image=self._modal_gif_frames[self._modal_gif_idx])
                self._modal_gif_job = self.root.after(100, _play_modal_gif)

            self._modal_gif_job = self.root.after(100, _play_modal_gif)

        # ── Footer Toolbar ──
        footer = tk.Frame(modal, bg="#18181b")
        footer.pack(fill="x", side="bottom", pady=(0, 10))

        # Close button
        btn_close = tk.Button(
            footer,
            text="close (esc)",
            command=self._destroy_modal,
            bg="#27272a",
            fg="#f4f4f5",
            activebackground="#3f3f46",
            activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=14,
            pady=4,
            cursor="hand2",
        )
        btn_close.pack(side="right", padx=(6, 14))

        # Open folder button
        curr_folder = self._current_image_path.parent

        def open_folder():
            try:
                os.startfile(str(curr_folder))
            except Exception as e:
                logger.error(f"Failed to open folder: {e}")

        btn_folder = tk.Button(
            footer,
            text="📂 Open Folder",
            command=open_folder,
            bg="#27272a",
            fg="#d4d4d8",
            activebackground="#3f3f46",
            activeforeground="#ffffff",
            font=("Segoe UI", 9),
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2",
        )
        btn_folder.pack(side="right", padx=4)

        # File name display
        lbl_filename = tk.Label(
            footer,
            text=self._current_image_path.name[:35],
            fg="#71717a",
            bg="#18181b",
            font=("Segoe UI", 8),
        )
        lbl_filename.pack(side="left", padx=14)

        # ── Bind Escape key & focus ──
        modal.bind("<Escape>", lambda e: self._destroy_modal())
        modal.focus_force()

        self._modal_window = modal
        logger.info(f"Opened enlarged view for {self._current_image_path.name}")
