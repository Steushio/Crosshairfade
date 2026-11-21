"""
High-precision background mouse and hotkey monitor.
Detects mouse clicks, hold duration, spray fade trigger, and global hotkeys.
Ensures crosshair remains hidden during hold until release.
"""

import ctypes
import threading
import time
from typing import Callable, Optional
from crosshair_config import CrosshairConfig

VK_LBUTTON = 0x01
VK_RBUTTON = 0x02
VK_MBUTTON = 0x04
VK_F1 = 0x70
VK_F2 = 0x71
VK_F3 = 0x72
VK_F4 = 0x73
VK_F5 = 0x74
VK_F6 = 0x75
VK_F7 = 0x76
VK_F8 = 0x77
VK_F9 = 0x78
VK_F10 = 0x79
VK_F11 = 0x7A
VK_F12 = 0x7B
VK_INSERT = 0x2D
VK_HOME = 0x24
VK_END = 0x23

HOTKEY_MAP = {
    "F1": VK_F1,
    "F2": VK_F2,
    "F3": VK_F3,
    "F4": VK_F4,
    "F5": VK_F5,
    "F6": VK_F6,
    "F7": VK_F7,
    "F8": VK_F8,
    "F9": VK_F9,
    "F10": VK_F10,
    "F11": VK_F11,
    "F12": VK_F12,
    "Insert": VK_INSERT,
    "Home": VK_HOME,
    "End": VK_END,
}


class MouseFadeMonitor:
    def __init__(
        self,
        config: CrosshairConfig,
        on_fade_state_change: Optional[Callable[[bool], None]] = None,
        on_hotkey_toggle: Optional[Callable[[], None]] = None,
        on_status_update: Optional[Callable[[str, int], None]] = None,
    ):
        self.config = config
        self.on_fade_state_change = on_fade_state_change
        self.on_hotkey_toggle = on_hotkey_toggle
        self.on_status_update = on_status_update

        self.running = False
        self.thread: Optional[threading.Thread] = None

        self.is_button_down = False
        self.press_start_time = 0.0
        self.faded_start_time = 0.0
        self.is_currently_faded = False
        self.hotkey_was_down = False

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.thread.start()

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=0.5)

    def _get_target_vk(self) -> int:
        btn_name = self.config.fade_mouse_button.lower()
        if "right" in btn_name:
            return VK_RBUTTON
        elif "middle" in btn_name:
            return VK_MBUTTON
        return VK_LBUTTON

    def _get_hotkey_vk(self) -> int:
        return HOTKEY_MAP.get(self.config.toggle_hotkey, VK_F10)

    def _is_key_down(self, vk: int) -> bool:
        state = ctypes.windll.user32.GetAsyncKeyState(vk)
        return bool(state & 0x8000)

    def _monitor_loop(self):
        while self.running:
            now = time.perf_counter()

            # 1. Global Hotkey Check
            hotkey_vk = self._get_hotkey_vk()
            hotkey_down = self._is_key_down(hotkey_vk)
            if hotkey_down and not self.hotkey_was_down:
                if self.on_hotkey_toggle:
                    self.on_hotkey_toggle()
            self.hotkey_was_down = hotkey_down

            # 2. Mouse Hold / Spray Lock Check
            if not self.config.fade_enabled or not self.config.overlay_enabled:
                if self.is_currently_faded:
                    self.is_currently_faded = False
                    if self.on_fade_state_change:
                        self.on_fade_state_change(False)
                time.sleep(0.01)
                continue

            btn_vk = self._get_target_vk()
            btn_down = self._is_key_down(btn_vk)

            if btn_down:
                if not self.is_button_down:
                    self.is_button_down = True
                    self.press_start_time = now
                    self.is_currently_faded = False

                hold_ms = int((now - self.press_start_time) * 1000)

                if not self.is_currently_faded:
                    if hold_ms >= self.config.fade_hold_threshold_ms:
                        self.is_currently_faded = True
                        self.faded_start_time = now
                        if self.on_fade_state_change:
                            self.on_fade_state_change(True)

                        if self.on_status_update:
                            self.on_status_update(f"FADED (Holding {hold_ms} ms)", hold_ms)
                    else:
                        if self.on_status_update:
                            self.on_status_update(f"Bursting ({hold_ms} ms)", hold_ms)

                else:
                    # CROSSHAIR REMAINS HIDDEN THE ENTIRE TIME MOUSE IS HELD!
                    if self.config.fade_mode == "Disappear for Duration":
                        fade_elapsed_ms = int((now - self.faded_start_time) * 1000)
                        if fade_elapsed_ms >= self.config.fade_disappear_duration_ms:
                            self.is_currently_faded = False
                            if self.on_fade_state_change:
                                self.on_fade_state_change(False)
                            if self.on_status_update:
                                self.on_status_update(f"Restored ({hold_ms} ms)", hold_ms)
                    else:
                        # "Hidden Until Released" (Default spray lock)
                        if self.on_status_update:
                            self.on_status_update(f"FADED - Holding Spray ({hold_ms} ms)", hold_ms)

            else:
                # Button is released
                if self.is_button_down:
                    self.is_button_down = False

                    # Restore crosshair now that hold is released!
                    if self.is_currently_faded:
                        self.is_currently_faded = False
                        if self.on_fade_state_change:
                            self.on_fade_state_change(False)

                    if self.on_status_update:
                        self.on_status_update("Ready", 0)

            time.sleep(0.003)
