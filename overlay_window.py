"""
Transparent, Click-Through, Hardware-Accelerated Overlay Window.
Maintains continuous topmost Z-order to stay visible over games in Fullscreen mode.
"""

import ctypes
from ctypes import wintypes
import threading
import time
import tkinter as tk
from typing import List, Tuple, Optional
from PIL import ImageTk
from crosshair_config import CrosshairConfig
import renderer

GWL_EXSTYLE = -20
GWLP_HWNDPARENT = -8

WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_TOPMOST = 0x00000008

HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
SWP_ASYNCWINDOWPOS = 0x4000

CHROMA_HEX = "#000001"
CHROMA_RGB = (0, 0, 1)


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG)
    ]


class MONITORINFOEX(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", wintypes.WCHAR * 32)
    ]


def get_system_monitors() -> List[Tuple[str, int, int, int, int, bool]]:
    """Returns list of monitors: [(name, left, top, width, height, is_primary), ...]"""
    monitors = []

    def callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
        mi = MONITORINFOEX()
        mi.cbSize = ctypes.sizeof(MONITORINFOEX)
        ctypes.windll.user32.GetMonitorInfoW(hMonitor, ctypes.byref(mi))
        r = mi.rcMonitor
        monitors.append((
            mi.szDevice,
            r.left,
            r.top,
            r.right - r.left,
            r.bottom - r.top,
            bool(mi.dwFlags & 1)
        ))
        return 1

    MonitorEnumProc = ctypes.WINFUNCTYPE(
        ctypes.c_int,
        wintypes.HMONITOR,
        wintypes.HDC,
        ctypes.c_void_p,
        wintypes.LPARAM
    )
    ctypes.windll.user32.EnumDisplayMonitors(None, None, MonitorEnumProc(callback), 0)

    if not monitors:
        w = ctypes.windll.user32.GetSystemMetrics(0)
        h = ctypes.windll.user32.GetSystemMetrics(1)
        monitors.append(("Primary Display", 0, 0, w, h, True))

    return monitors


class OverlayWindow:
    def __init__(self, root: tk.Tk, config: CrosshairConfig, window_size: int = 140):
        self.root = root
        self.config = config
        self.window_size = window_size
        self.hwnd: Optional[int] = None
        self.current_photo: Optional[ImageTk.PhotoImage] = None
        self.image_id: Optional[int] = None
        self.is_faded = False

        self.topmost_running = True
        self._topmost_thread: Optional[threading.Thread] = None

        self._create_window()
        self._start_topmost_keeper()

    def _create_window(self):
        self.top = tk.Toplevel(self.root)
        self.top.overrideredirect(True)
        self.top.attributes("-topmost", True)
        self.top.attributes("-transparentcolor", CHROMA_HEX)
        self.top.config(bg=CHROMA_HEX)

        self.canvas = tk.Canvas(
            self.top,
            width=self.window_size,
            height=self.window_size,
            bg=CHROMA_HEX,
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)

        self.top.update_idletasks()

        # Get HWND
        self.hwnd = ctypes.windll.user32.GetParent(self.top.winfo_id()) or self.top.winfo_id()

        # Set extended styles: Layered, transparent click-through, topmost, no-activate, tool window
        old_style = ctypes.windll.user32.GetWindowLongW(self.hwnd, GWL_EXSTYLE)
        new_style = old_style | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_TOPMOST
        ctypes.windll.user32.SetWindowLongW(self.hwnd, GWL_EXSTYLE, new_style)

        # Unparent window so it is an independent desktop window not affected by root.withdraw()
        try:
            SetWindowLongPtr = getattr(ctypes.windll.user32, "SetWindowLongPtrW", ctypes.windll.user32.SetWindowLongW)
            SetWindowLongPtr.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.HWND]
            SetWindowLongPtr.restype = wintypes.HWND
            SetWindowLongPtr(self.hwnd, GWLP_HWNDPARENT, None)
        except Exception:
            pass

        self.reposition()
        self.update_crosshair()

    def _start_topmost_keeper(self):
        """
        Background keeper thread: Continuously asserts HWND_TOPMOST
        so the overlay stays on top even when games like Valorant enter Fullscreen.
        """
        self._topmost_thread = threading.Thread(target=self._topmost_keeper_loop, daemon=True)
        self._topmost_thread.start()

    def _topmost_keeper_loop(self):
        last_fg = 0
        while self.topmost_running:
            if self.hwnd and self.config.overlay_enabled and not self.is_faded:
                current_fg = ctypes.windll.user32.GetForegroundWindow()
                if self.config.fullscreen_aggressive_mode or current_fg != last_fg:
                    ctypes.windll.user32.BringWindowToTop(self.hwnd)
                    ctypes.windll.user32.SetWindowPos(
                        self.hwnd,
                        HWND_TOPMOST,
                        0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW | SWP_ASYNCWINDOWPOS
                    )
                last_fg = current_fg
            time.sleep(0.025)

    def reposition(self):
        """Calculate screen center coordinates on chosen monitor and move overlay."""
        monitors = get_system_monitors()
        m_idx = self.config.monitor_index
        if m_idx < 0 or m_idx >= len(monitors):
            m_idx = 0

        _, m_left, m_top, m_width, m_height, _ = monitors[m_idx]

        center_x = m_left + (m_width // 2) - (self.window_size // 2) + self.config.offset_x
        center_y = m_top + (m_height // 2) - (self.window_size // 2) + self.config.offset_y

        self.top.geometry(f"{self.window_size}x{self.window_size}+{center_x}+{center_y}")
        self._ensure_topmost()

    def _ensure_topmost(self):
        if self.hwnd:
            ctypes.windll.user32.BringWindowToTop(self.hwnd)
            ctypes.windll.user32.SetWindowPos(
                self.hwnd,
                HWND_TOPMOST,
                0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW | SWP_ASYNCWINDOWPOS
            )

    def update_crosshair(self):
        """Re-render crosshair and update on canvas."""
        if not self.config.overlay_enabled or self.is_faded:
            self.canvas.delete("all")
            self.current_photo = None
            return

        raw_img = renderer.render_crosshair_image(self.config, canvas_size=self.window_size)
        overlay_img = renderer.composite_for_overlay(raw_img, chroma_color=CHROMA_RGB)

        self.current_photo = ImageTk.PhotoImage(overlay_img)
        self.canvas.delete("all")
        cx, cy = self.window_size // 2, self.window_size // 2
        self.image_id = self.canvas.create_image(cx, cy, image=self.current_photo)
        self._ensure_topmost()

    def set_fade(self, fade: bool):
        """Called by mouse monitor to instantly hide or show crosshair."""
        self.is_faded = fade
        self.root.after(0, self._apply_fade_state)

    def _apply_fade_state(self):
        if self.is_faded or not self.config.overlay_enabled:
            self.canvas.delete("all")
            self.current_photo = None
        else:
            self.update_crosshair()

    def toggle_overlay(self):
        """Toggle overlay on/off via hotkey or UI."""
        self.config.overlay_enabled = not self.config.overlay_enabled
        self.root.after(0, self._apply_fade_state)

    def destroy(self):
        self.topmost_running = False
        try:
            self.top.destroy()
        except Exception:
            pass
