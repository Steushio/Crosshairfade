"""
System Tray Manager for Valorant Crosshair Fade using pystray.
Allows background execution, quick preset/custom profile switching, and toggling.
"""

import threading
from typing import Callable, List, Optional
from PIL import Image
import pystray
from pystray import MenuItem as item, Menu


class SystemTrayManager:
    def __init__(
        self,
        icon_path: str,
        on_show_settings: Callable[[], None],
        on_toggle_overlay: Callable[[], None],
        on_select_preset: Callable[[str], None],
        on_exit: Callable[[], None],
        is_overlay_active_fn: Callable[[], bool],
        get_profiles_fn: Optional[Callable[[], List[str]]] = None,
        on_toggle_startup: Optional[Callable[[], None]] = None,
        is_startup_enabled_fn: Optional[Callable[[], bool]] = None,
    ):
        self.icon_path = icon_path
        self.on_show_settings = on_show_settings
        self.on_toggle_overlay = on_toggle_overlay
        self.on_select_preset = on_select_preset
        self.on_exit = on_exit
        self.is_overlay_active_fn = is_overlay_active_fn
        self.get_profiles_fn = get_profiles_fn
        self.on_toggle_startup = on_toggle_startup
        self.is_startup_enabled_fn = is_startup_enabled_fn

        self.icon_image = Image.open(icon_path)
        self.icon: Optional[pystray.Icon] = None
        self._thread: Optional[threading.Thread] = None

    def _build_menu(self) -> Menu:
        def toggle_text(item_obj):
            active = self.is_overlay_active_fn()
            return f"Toggle Overlay: {'[ACTIVE]' if active else '[HIDDEN]'}"

        profiles = self.get_profiles_fn() if self.get_profiles_fn else []
        if not profiles:
            from crosshair_config import PRESETS
            profiles = list(PRESETS.keys())

        preset_items = [
            item(p_name, lambda _, name=p_name: self.on_select_preset(name))
            for p_name in profiles
        ]

        menu_items = [
            item("Open Settings", lambda _: self.on_show_settings(), default=True),
            item(toggle_text, lambda _: self.on_toggle_overlay()),
            Menu.SEPARATOR,
            item("Profiles & Presets", Menu(*preset_items)),
            Menu.SEPARATOR,
        ]

        if self.on_toggle_startup and self.is_startup_enabled_fn:
            def startup_text(item_obj):
                enabled = self.is_startup_enabled_fn()
                return f"Run on Windows Startup: {'[ON]' if enabled else '[OFF]'}"

            menu_items.append(item(startup_text, lambda _: self.on_toggle_startup()))
            menu_items.append(Menu.SEPARATOR)

        menu_items.append(item("Exit App", lambda _: self.on_exit()))
        return Menu(*menu_items)

    def start(self):
        if self.icon is None:
            self.icon = pystray.Icon(
                name="ValorantCrosshairFade",
                icon=self.icon_image,
                title="VALORANT Crosshair Fade",
                menu=self._build_menu()
            )
            self._thread = threading.Thread(target=self.icon.run, daemon=True)
            self._thread.start()

    def update_menu(self):
        if self.icon:
            self.icon.menu = self._build_menu()
            status = "ACTIVE" if self.is_overlay_active_fn() else "HIDDEN"
            self.icon.title = f"VALORANT Crosshair Fade ({status})"

    def notify(self, title: str, message: str):
        if self.icon:
            try:
                self.icon.notify(title=title, message=message)
            except Exception:
                pass

    def stop(self):
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass
            self.icon = None
