"""
Main GUI Application for Valorant Crosshair Fade.
Features Valorant-style dark theme, live crosshair preview, dedicated color pickers,
custom user profile saving/loading with persistent memory, Valorant code import/export,
mouse hold spray fade (hidden until released), continuous topmost Fullscreen mode,
and Windows System Tray integration with auto-start minimized.
"""

import os
import sys
import tkinter as tk
from tkinter import colorchooser, messagebox, simpledialog, filedialog
import customtkinter as ctk
from PIL import Image, ImageTk
from typing import Dict, Any, Callable, Optional, List

from crosshair_config import CrosshairConfig, PRESETS, parse_valorant_code, export_valorant_code
import renderer
from overlay_window import OverlayWindow, get_system_monitors
from mouse_monitor import MouseFadeMonitor, HOTKEY_MAP
from tray_manager import SystemTrayManager
from startup_manager import is_run_on_startup_enabled, set_run_on_startup


def resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and for PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


PALETTE = [
    ("#00FFFF", "Cyan"),
    ("#00FF00", "Green"),
    ("#FFFF00", "Yellow"),
    ("#FFFFFF", "White"),
    ("#FF007F", "Pink"),
    ("#FF0000", "Red"),
    ("#000000", "Black"),
    ("#FF8C00", "Orange"),
]


class CrosshairApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("dark-blue")

        self.title("VALORANT Crosshair Fade - Trigger Discipline Overlay")
        self.geometry("980x750")
        self.minsize(920, 700)

        self.icon_path = resource_path("assets/app_icon.ico")
        self.icon_png_path = resource_path("assets/app_icon.png")
        if os.path.exists(self.icon_path):
            try:
                self.iconbitmap(self.icon_path)
            except Exception:
                pass

        self.config_data = CrosshairConfig.load_from_file()
        self.preview_zoom = 4
        self.preview_bg = "Valorant Slate"
        self.show_grid = True
        self.preview_photo: Any = None

        self._build_header()
        self._build_body()

        self.overlay = OverlayWindow(self, self.config_data)

        self.monitor = MouseFadeMonitor(
            config=self.config_data,
            on_fade_state_change=self._on_fade_state_change,
            on_hotkey_toggle=self._on_hotkey_toggle,
            on_status_update=self._on_monitor_status_update
        )
        self.monitor.start()

        tray_img_path = self.icon_png_path if os.path.exists(self.icon_png_path) else self.icon_path
        self.tray_manager = SystemTrayManager(
            icon_path=tray_img_path,
            on_show_settings=lambda: self.after(0, self.restore_from_tray),
            on_toggle_overlay=lambda: self.after(0, self.toggle_overlay_state),
            on_select_preset=lambda p: self.after(0, lambda: self._on_profile_selected_from_name(p)),
            on_exit=lambda: self.after(0, self.quit_app),
            is_overlay_active_fn=lambda: self.config_data.overlay_enabled,
            get_profiles_fn=self.config_data.get_all_profile_names,
            on_toggle_startup=lambda: self.after(0, self._toggle_startup_from_tray),
            is_startup_enabled_fn=is_run_on_startup_enabled
        )
        self.tray_manager.start()

        self.update_all()

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        if self.config_data.start_minimized:
            self.withdraw()
            self.after(500, lambda: self.tray_manager.notify(
                "VALORANT Crosshair Fade",
                f"Active in background! Profile: [{self.config_data.current_profile_name}]\nPress [{self.config_data.toggle_hotkey}] in-game to toggle, or click tray icon to open settings."
            ))

    def _build_header(self):
        header_frame = ctk.CTkFrame(self, fg_color="#0F1923", corner_radius=0, height=65)
        header_frame.pack(fill="x", side="top", padx=0, pady=0)
        header_frame.pack_propagate(False)

        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(side="left", padx=20, pady=10)

        title_lbl = ctk.CTkLabel(
            title_box,
            text="VALORANT CROSSHAIR FADE",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color="#FD4556"
        )
        title_lbl.pack(anchor="w")

        sub_lbl = ctk.CTkLabel(
            title_box,
            text="Independent Colors • Profile Saver • Hold-to-Fade Spray Lock • Fullscreen Mode",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#8B978F"
        )
        sub_lbl.pack(anchor="w")

        actions_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        actions_box.pack(side="right", padx=15, pady=10)

        tray_btn = ctk.CTkButton(
            actions_box,
            text="📥 Minimize to Tray",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#203040",
            hover_color="#2C4156",
            width=130,
            command=self.minimize_to_tray
        )
        tray_btn.pack(side="left", padx=(0, 10))

        self.hotkey_badge = ctk.CTkLabel(
            actions_box,
            text=f"Hotkey: [{self.config_data.toggle_hotkey}]",
            font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
            fg_color="#1F2326",
            corner_radius=6,
            text_color="#ECE8E1",
            padx=10,
            pady=4
        )
        self.hotkey_badge.pack(side="left", padx=(0, 10))

        self.toggle_btn = ctk.CTkButton(
            actions_box,
            text="OVERLAY: ACTIVE",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#2ECC71",
            hover_color="#27AE60",
            width=135,
            command=self.toggle_overlay_state
        )
        self.toggle_btn.pack(side="left")

    def _build_body(self):
        body_container = ctk.CTkFrame(self, fg_color="transparent")
        body_container.pack(fill="both", expand=True, padx=15, pady=12)

        left_panel = ctk.CTkFrame(body_container, width=320, fg_color="#181E24", corner_radius=10)
        left_panel.pack(side="left", fill="y", padx=(0, 10), pady=0)
        left_panel.pack_propagate(False)

        self._build_left_panel(left_panel)

        right_panel = ctk.CTkFrame(body_container, fg_color="#181E24", corner_radius=10)
        right_panel.pack(side="right", fill="both", expand=True, padx=0, pady=0)

        self._build_tabs(right_panel)

    def _build_left_panel(self, parent: ctk.CTkFrame):
        lbl = ctk.CTkLabel(
            parent,
            text="LIVE PREVIEW",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#ECE8E1"
        )
        lbl.pack(anchor="w", padx=15, pady=(10, 4))

        canvas_border = ctk.CTkFrame(parent, fg_color="#0F1923", corner_radius=8, width=240, height=240)
        canvas_border.pack(padx=15, pady=4)
        canvas_border.pack_propagate(False)

        self.preview_canvas = tk.Canvas(
            canvas_border,
            width=230,
            height=230,
            bg="#0F1923",
            highlightthickness=0
        )
        self.preview_canvas.place(relx=0.5, rely=0.5, anchor="center")

        ctrl_frame = ctk.CTkFrame(parent, fg_color="transparent")
        ctrl_frame.pack(fill="x", padx=15, pady=2)

        ctk.CTkLabel(ctrl_frame, text="Zoom:", font=ctk.CTkFont(size=11), text_color="#A0A0A0").pack(side="left")
        self.zoom_menu = ctk.CTkOptionMenu(
            ctrl_frame,
            values=["2x", "4x", "8x"],
            width=65,
            height=24,
            command=self._on_zoom_changed
        )
        self.zoom_menu.set(f"{self.preview_zoom}x")
        self.zoom_menu.pack(side="left", padx=5)

        self.grid_switch = ctk.CTkSwitch(
            ctrl_frame,
            text="Grid",
            font=ctk.CTkFont(size=11),
            width=40,
            command=self._on_grid_toggled
        )
        if self.show_grid:
            self.grid_switch.select()
        self.grid_switch.pack(side="right")

        bg_frame = ctk.CTkFrame(parent, fg_color="transparent")
        bg_frame.pack(fill="x", padx=15, pady=2)
        ctk.CTkLabel(bg_frame, text="Backdrop:", font=ctk.CTkFont(size=11), text_color="#A0A0A0").pack(side="left")
        self.bg_menu = ctk.CTkOptionMenu(
            bg_frame,
            values=["Valorant Slate", "Combat Tan (Bind)", "Ice Blue (Icebox)", "Dark Gray", "Pitch Black", "Green Screen"],
            height=24,
            width=150,
            command=self._on_bg_changed
        )
        self.bg_menu.set(self.preview_bg)
        self.bg_menu.pack(side="right")

        practice_box = ctk.CTkFrame(parent, fg_color="#0F1923", corner_radius=8)
        practice_box.pack(fill="x", padx=15, pady=(8, 4))

        p_lbl = ctk.CTkLabel(
            practice_box,
            text="TRIGGER DISCIPLINE TESTER",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#FD4556"
        )
        p_lbl.pack(anchor="w", padx=10, pady=(4, 2))

        self.status_pill = ctk.CTkLabel(
            practice_box,
            text="🟢 STATUS: READY",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color="#2ECC71",
            fg_color="#18222A",
            corner_radius=5,
            padx=8,
            pady=2
        )
        self.status_pill.pack(fill="x", padx=10, pady=2)

        self.test_pad = ctk.CTkButton(
            practice_box,
            text="Click & Hold Here to Test Fade",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#2A3540",
            hover_color="#374553",
            height=28
        )
        self.test_pad.pack(fill="x", padx=10, pady=(2, 6))
        self.test_pad.bind("<ButtonPress-1>", self._on_test_pad_down)
        self.test_pad.bind("<ButtonRelease-1>", self._on_test_pad_up)

        preset_box = ctk.CTkFrame(parent, fg_color="#0F1923", corner_radius=8)
        preset_box.pack(fill="x", padx=15, pady=(6, 0))

        p_head_row = ctk.CTkFrame(preset_box, fg_color="transparent")
        p_head_row.pack(fill="x", padx=10, pady=(6, 2))

        ctk.CTkLabel(
            p_head_row,
            text="PROFILES & SAVED CROSSHAIRS",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#00FFFF"
        ).pack(side="left")

        self.profile_menu = ctk.CTkOptionMenu(
            preset_box,
            values=self._get_profile_menu_values(),
            height=28,
            command=self._on_profile_dropdown_selected
        )
        self._sync_profile_dropdown_label()
        self.profile_menu.pack(fill="x", padx=10, pady=3)

        p_btn_row1 = ctk.CTkFrame(preset_box, fg_color="transparent")
        p_btn_row1.pack(fill="x", padx=10, pady=2)

        save_as_btn = ctk.CTkButton(
            p_btn_row1,
            text="💾 Save New",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#204030",
            hover_color="#2C5640",
            width=110,
            command=self._on_save_new_profile
        )
        save_as_btn.pack(side="left", padx=(0, 3), expand=True, fill="x")

        update_btn = ctk.CTkButton(
            p_btn_row1,
            text="🔄 Overwrite",
            font=ctk.CTkFont(size=11),
            fg_color="#2A3540",
            hover_color="#374553",
            width=80,
            command=self._on_overwrite_profile
        )
        update_btn.pack(side="left", padx=2, expand=True, fill="x")

        delete_btn = ctk.CTkButton(
            p_btn_row1,
            text="🗑️",
            font=ctk.CTkFont(size=12),
            fg_color="#402020",
            hover_color="#562C2C",
            width=36,
            command=self._on_delete_profile
        )
        delete_btn.pack(side="right", padx=(3, 0))

        code_btn_row = ctk.CTkFrame(preset_box, fg_color="transparent")
        code_btn_row.pack(fill="x", padx=10, pady=(2, 2))

        import_btn = ctk.CTkButton(
            code_btn_row,
            text="Import Code",
            font=ctk.CTkFont(size=11),
            fg_color="#1F2833",
            hover_color="#2C3847",
            command=self._on_import_code
        )
        import_btn.pack(side="left", padx=(0, 3), expand=True, fill="x")

        export_btn = ctk.CTkButton(
            code_btn_row,
            text="Copy Code",
            font=ctk.CTkFont(size=11),
            fg_color="#1F2833",
            hover_color="#2C3847",
            command=self._on_export_code
        )
        export_btn.pack(side="right", padx=(3, 0), expand=True, fill="x")

        json_btn_row = ctk.CTkFrame(preset_box, fg_color="transparent")
        json_btn_row.pack(fill="x", padx=10, pady=(2, 6))

        import_json_btn = ctk.CTkButton(
            json_btn_row,
            text="📥 Import JSON",
            font=ctk.CTkFont(size=11),
            fg_color="#1B2B38",
            hover_color="#273C4E",
            command=self._on_import_json
        )
        import_json_btn.pack(side="left", padx=(0, 3), expand=True, fill="x")

        export_json_btn = ctk.CTkButton(
            json_btn_row,
            text="📤 Export JSON",
            font=ctk.CTkFont(size=11),
            fg_color="#1B2B38",
            hover_color="#273C4E",
            command=self._on_export_json
        )
        export_json_btn.pack(side="right", padx=(3, 0), expand=True, fill="x")

    def _build_tabs(self, parent: ctk.CTkFrame):
        self.tabs = ctk.CTkTabview(parent, fg_color="#181E24", segmented_button_selected_color="#FD4556")
        self.tabs.pack(fill="both", expand=True, padx=10, pady=8)

        tab_inner = self.tabs.add("Inner Lines")
        tab_outer = self.tabs.add("Outer Lines")
        tab_outlines = self.tabs.add("Outlines & Dot")
        tab_fade = self.tabs.add("Mouse Hold Fade")
        tab_display = self.tabs.add("Display & Fullscreen")

        self._build_inner_tab(tab_inner)
        self._build_outer_tab(tab_outer)
        self._build_outlines_tab(tab_outlines)
        self._build_fade_tab(tab_fade)
        self._build_display_tab(tab_display)

    def _build_inner_tab(self, tab):
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=5, pady=5)

        self.inner_switch = ctk.CTkSwitch(
            scroll,
            text="Show Inner Lines",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._on_inner_switch
        )
        if self.config_data.inner_lines_enabled:
            self.inner_switch.select()
        self.inner_switch.pack(anchor="w", pady=(5, 15))

        self._build_color_picker_row(
            scroll,
            title="Inner Lines Color",
            current_hex=self.config_data.inner_line_color,
            on_color_picked=self._on_inner_color_picked,
            attr_name="inner_line_color"
        )

        self.inner_opacity_slider = self._create_slider_row(
            scroll, "Inner Line Opacity", 0.0, 1.0, self.config_data.inner_line_opacity,
            lambda v: self._update_attr("inner_line_opacity", float(v)), is_float=True
        )

        self.inner_length_slider = self._create_slider_row(
            scroll, "Inner Line Length", 0, 20, self.config_data.inner_line_length,
            lambda v: self._update_attr("inner_line_length", int(round(v)))
        )

        self.inner_thickness_slider = self._create_slider_row(
            scroll, "Inner Line Thickness", 1, 10, self.config_data.inner_line_thickness,
            lambda v: self._update_attr("inner_line_thickness", int(round(v)))
        )

        self.inner_offset_slider = self._create_slider_row(
            scroll, "Inner Line Offset", 0, 20, self.config_data.inner_line_offset,
            lambda v: self._update_attr("inner_line_offset", int(round(v)))
        )

    def _build_outer_tab(self, tab):
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=5, pady=5)

        self.outer_switch = ctk.CTkSwitch(
            scroll,
            text="Show Outer Lines",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._on_outer_switch
        )
        if self.config_data.outer_lines_enabled:
            self.outer_switch.select()
        self.outer_switch.pack(anchor="w", pady=(5, 15))

        self._build_color_picker_row(
            scroll,
            title="Outer Lines Color (Separate Selection)",
            current_hex=self.config_data.outer_line_color,
            on_color_picked=self._on_outer_color_picked,
            attr_name="outer_line_color"
        )

        self.outer_opacity_slider = self._create_slider_row(
            scroll, "Outer Line Opacity", 0.0, 1.0, self.config_data.outer_line_opacity,
            lambda v: self._update_attr("outer_line_opacity", float(v)), is_float=True
        )

        self.outer_length_slider = self._create_slider_row(
            scroll, "Outer Line Length", 0, 20, self.config_data.outer_line_length,
            lambda v: self._update_attr("outer_line_length", int(round(v)))
        )

        self.outer_thickness_slider = self._create_slider_row(
            scroll, "Outer Line Thickness", 1, 10, self.config_data.outer_line_thickness,
            lambda v: self._update_attr("outer_line_thickness", int(round(v)))
        )

        self.outer_offset_slider = self._create_slider_row(
            scroll, "Outer Line Offset", 0, 40, self.config_data.outer_line_offset,
            lambda v: self._update_attr("outer_line_offset", int(round(v)))
        )

    def _build_outlines_tab(self, tab):
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=5, pady=5)

        outlines_header = ctk.CTkLabel(
            scroll,
            text="OUTLINES",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#FD4556"
        )
        outlines_header.pack(anchor="w", pady=(5, 4))

        self.outline_switch = ctk.CTkSwitch(
            scroll,
            text="Enable Outlines",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._on_outline_switch
        )
        if self.config_data.outlines_enabled:
            self.outline_switch.select()
        self.outline_switch.pack(anchor="w", pady=(0, 10))

        self._build_color_picker_row(
            scroll,
            title="Outline Color Selection",
            current_hex=self.config_data.outline_color,
            on_color_picked=self._on_outline_color_picked,
            attr_name="outline_color"
        )

        self.outline_opacity_slider = self._create_slider_row(
            scroll, "Outline Opacity", 0.0, 1.0, self.config_data.outline_opacity,
            lambda v: self._update_attr("outline_opacity", float(v)), is_float=True
        )

        self.outline_thickness_slider = self._create_slider_row(
            scroll, "Outline Thickness", 1, 6, self.config_data.outline_thickness,
            lambda v: self._update_attr("outline_thickness", int(round(v)))
        )

        ctk.CTkLabel(scroll, text="").pack(pady=4)
        dot_header = ctk.CTkLabel(
            scroll,
            text="CENTER DOT",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#FD4556"
        )
        dot_header.pack(anchor="w", pady=(10, 4))

        self.dot_switch = ctk.CTkSwitch(
            scroll,
            text="Enable Center Dot",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._on_dot_switch
        )
        if self.config_data.center_dot_enabled:
            self.dot_switch.select()
        self.dot_switch.pack(anchor="w", pady=(0, 10))

        self._build_color_picker_row(
            scroll,
            title="Center Dot Color",
            current_hex=self.config_data.center_dot_color,
            on_color_picked=self._on_dot_color_picked,
            attr_name="center_dot_color"
        )

        self.dot_opacity_slider = self._create_slider_row(
            scroll, "Center Dot Opacity", 0.0, 1.0, self.config_data.center_dot_opacity,
            lambda v: self._update_attr("center_dot_opacity", float(v)), is_float=True
        )

        self.dot_thickness_slider = self._create_slider_row(
            scroll, "Center Dot Size (Thickness)", 1, 6, self.config_data.center_dot_thickness,
            lambda v: self._update_attr("center_dot_thickness", int(round(v)))
        )

    def _build_fade_tab(self, tab):
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=5, pady=5)

        desc = (
            "🎯 Trigger Discipline & Spray Lock:\n"
            "If you hold your mouse click longer than your configured hold limit (e.g. 200ms),\n"
            "the crosshair will immediately disappear.\n\n"
            "⚠️ SPRAY LOCK RULE (Enabled by default):\n"
            "The crosshair will NOT show as long as you continue holding the mouse click!\n"
            "It reappears only after the hold is released, training recoil reset and counter-strafing."
        )
        desc_lbl = ctk.CTkLabel(
            scroll,
            text=desc,
            font=ctk.CTkFont(size=12),
            text_color="#A4B3C6",
            justify="left"
        )
        desc_lbl.pack(anchor="w", pady=(5, 12))

        self.fade_switch = ctk.CTkSwitch(
            scroll,
            text="Enable Mouse Hold Fade Feature",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._on_fade_switch
        )
        if self.config_data.fade_enabled:
            self.fade_switch.select()
        self.fade_switch.pack(anchor="w", pady=(0, 15))

        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(fill="x", pady=6)
        ctk.CTkLabel(
            btn_frame,
            text="Monitored Mouse Button:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#ECE8E1"
        ).pack(side="left")

        self.mouse_btn_menu = ctk.CTkOptionMenu(
            btn_frame,
            values=["Left Click", "Right Click"],
            command=self._on_fade_btn_changed
        )
        self.mouse_btn_menu.set(self.config_data.fade_mouse_button)
        self.mouse_btn_menu.pack(side="right")

        mode_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        mode_frame.pack(fill="x", pady=6)
        ctk.CTkLabel(
            mode_frame,
            text="Fade Behavior Mode:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#ECE8E1"
        ).pack(side="left")

        self.fade_mode_menu = ctk.CTkOptionMenu(
            mode_frame,
            values=["Hidden Until Released", "Disappear for Duration"],
            command=self._on_fade_mode_changed
        )
        self.fade_mode_menu.set(self.config_data.fade_mode)
        self.fade_mode_menu.pack(side="right")

        self.hold_threshold_slider = self._create_slider_row(
            scroll,
            "Hold Duration Limit (ms before disappearing)",
            50, 1000, self.config_data.fade_hold_threshold_ms,
            lambda v: self._update_attr("fade_hold_threshold_ms", int(round(v))),
            unit=" ms"
        )

        self.disappear_duration_slider = self._create_slider_row(
            scroll,
            "Optional Duration Limit (if duration mode is selected)",
            50, 2000, self.config_data.fade_disappear_duration_ms,
            lambda v: self._update_attr("fade_disappear_duration_ms", int(round(v))),
            unit=" ms"
        )

        guide_box = ctk.CTkFrame(scroll, fg_color="#0F1923", corner_radius=8)
        guide_box.pack(fill="x", pady=(15, 5), padx=5)

        ctk.CTkLabel(
            guide_box,
            text="💡 Pro Tip for Vandal & Phantom:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#00FFFF"
        ).pack(anchor="w", padx=10, pady=(8, 2))

        weapons_info = (
            "• Vandal / Phantom first 2-3 bullets take ~180ms - 220ms.\n"
            "• Keeping 'Hidden Until Released' on forces you to release LMB\n"
            "  and counter-strafe instead of committing to an inaccurate spray!"
        )
        ctk.CTkLabel(
            guide_box,
            text=weapons_info,
            font=ctk.CTkFont(size=11),
            text_color="#8B978F",
            justify="left"
        ).pack(anchor="w", padx=10, pady=(0, 8))

    def _build_display_tab(self, tab):
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=5, pady=5)

        fs_header = ctk.CTkLabel(
            scroll,
            text="FULLSCREEN MODE OPTIMIZATIONS",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#FD4556"
        )
        fs_header.pack(anchor="w", pady=(5, 4))

        self.fs_lock_switch = ctk.CTkSwitch(
            scroll,
            text="Aggressive Fullscreen Z-Order Lock (Continuous Topmost)",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._on_fs_lock_switch
        )
        if self.config_data.fullscreen_aggressive_mode:
            self.fs_lock_switch.select()
        self.fs_lock_switch.pack(anchor="w", pady=(2, 6))

        fs_tip_box = ctk.CTkFrame(scroll, fg_color="#0F1923", corner_radius=8)
        fs_tip_box.pack(fill="x", pady=(2, 12))

        fs_tip_text = (
            "🎮 Valorant Fullscreen Support:\n"
            "• The Aggressive Z-Order Lock continuously keeps the crosshair above Fullscreen games.\n"
            "• Make sure Windows 'Fullscreen Optimizations' is NOT disabled on your Valorant executable\n"
            "  (default Windows 10/11 setting) so DWM can render external overlays over Fullscreen."
        )
        ctk.CTkLabel(
            fs_tip_box,
            text=fs_tip_text,
            font=ctk.CTkFont(size=11),
            text_color="#A4B3C6",
            justify="left"
        ).pack(anchor="w", padx=10, pady=8)

        tray_header = ctk.CTkLabel(
            scroll,
            text="SYSTEM TRAY & STARTUP",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#FD4556"
        )
        tray_header.pack(anchor="w", pady=(5, 4))

        self.start_min_switch = ctk.CTkSwitch(
            scroll,
            text="Start App Minimized in System Tray (Enabled)",
            font=ctk.CTkFont(size=13),
            command=self._on_start_min_switch
        )
        if self.config_data.start_minimized:
            self.start_min_switch.select()
        self.start_min_switch.pack(anchor="w", pady=(2, 6))

        self.startup_switch = ctk.CTkSwitch(
            scroll,
            text="Launch on Windows Startup (Run with Windows)",
            font=ctk.CTkFont(size=13),
            command=self._on_startup_switch
        )
        # Check actual Windows registry state or config
        if is_run_on_startup_enabled() or self.config_data.run_on_startup:
            self.startup_switch.select()
        self.startup_switch.pack(anchor="w", pady=(2, 6))

        self.tray_close_switch = ctk.CTkSwitch(
            scroll,
            text="Minimize to System Tray on Window Close (X)",
            font=ctk.CTkFont(size=13),
            command=self._on_tray_close_switch
        )
        if self.config_data.minimize_to_tray_on_close:
            self.tray_close_switch.select()
        self.tray_close_switch.pack(anchor="w", pady=(2, 12))

        mon_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        mon_frame.pack(fill="x", pady=8)
        ctk.CTkLabel(
            mon_frame,
            text="Target Display Monitor:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#ECE8E1"
        ).pack(side="left")

        monitors = get_system_monitors()
        mon_labels = [f"Display {i+1} ({m[3]}x{m[4]}){' [Primary]' if m[5] else ''}" for i, m in enumerate(monitors)]
        self.mon_menu = ctk.CTkOptionMenu(
            mon_frame,
            values=mon_labels,
            command=self._on_monitor_changed
        )
        if 0 <= self.config_data.monitor_index < len(mon_labels):
            self.mon_menu.set(mon_labels[self.config_data.monitor_index])
        self.mon_menu.pack(side="right")

        hotkey_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        hotkey_frame.pack(fill="x", pady=8)
        ctk.CTkLabel(
            hotkey_frame,
            text="Global Toggle Hotkey (Works In-Game):",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#ECE8E1"
        ).pack(side="left")

        self.hotkey_menu = ctk.CTkOptionMenu(
            hotkey_frame,
            values=list(HOTKEY_MAP.keys()),
            command=self._on_hotkey_changed
        )
        self.hotkey_menu.set(self.config_data.toggle_hotkey)
        self.hotkey_menu.pack(side="right")

        ctk.CTkLabel(scroll, text="").pack(pady=2)
        ctk.CTkLabel(
            scroll,
            text="CENTER ALIGNMENT FINE-TUNING",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#FD4556"
        ).pack(anchor="w", pady=(8, 4))

        self.offset_x_slider = self._create_slider_row(
            scroll, "Screen Offset X (pixels)", -50, 50, self.config_data.offset_x,
            lambda v: self._update_offset_x(int(round(v))), unit=" px"
        )

        self.offset_y_slider = self._create_slider_row(
            scroll, "Screen Offset Y (pixels)", -50, 50, self.config_data.offset_y,
            lambda v: self._update_offset_y(int(round(v))), unit=" px"
        )

        reset_btn = ctk.CTkButton(
            scroll,
            text="Reset Offsets to Exact Screen Center (0, 0)",
            fg_color="#203040",
            hover_color="#2C4156",
            command=self._reset_offsets
        )
        reset_btn.pack(anchor="w", pady=10)

    def _build_color_picker_row(
        self,
        parent: ctk.CTkFrame,
        title: str,
        current_hex: str,
        on_color_picked: Callable[[str], None],
        attr_name: str
    ):
        frame = ctk.CTkFrame(parent, fg_color="#131920", corner_radius=8)
        frame.pack(fill="x", pady=(2, 10), padx=0)

        top_row = ctk.CTkFrame(frame, fg_color="transparent")
        top_row.pack(fill="x", padx=10, pady=(8, 6))

        ctk.CTkLabel(
            top_row,
            text=title,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#ECE8E1"
        ).pack(side="left")

        swatch = tk.Label(
            top_row,
            text=f"  {current_hex.upper()}  ",
            bg=current_hex,
            fg="#000000" if self._is_light_color(current_hex) else "#FFFFFF",
            font=("Consolas", 10, "bold"),
            relief="solid",
            bd=1
        )
        swatch.pack(side="right", padx=(10, 0))
        setattr(self, f"{attr_name}_swatch", swatch)

        pick_btn = ctk.CTkButton(
            top_row,
            text="Custom Color...",
            font=ctk.CTkFont(size=11),
            width=100,
            height=26,
            fg_color="#2A3540",
            hover_color="#374553",
            command=lambda: self._open_color_dialog(attr_name, on_color_picked)
        )
        pick_btn.pack(side="right")

        palette_row = ctk.CTkFrame(frame, fg_color="transparent")
        palette_row.pack(fill="x", padx=10, pady=(0, 8))

        ctk.CTkLabel(palette_row, text="Quick Palette:", font=ctk.CTkFont(size=10), text_color="#7A8795").pack(side="left", padx=(0, 6))

        for hex_code, name in PALETTE:
            p_btn = tk.Button(
                palette_row,
                bg=hex_code,
                activebackground=hex_code,
                width=2,
                height=1,
                relief="flat",
                command=lambda h=hex_code: on_color_picked(h)
            )
            p_btn.pack(side="left", padx=2)

    def _create_slider_row(
        self,
        parent: ctk.CTkFrame,
        title: str,
        min_val: float,
        max_val: float,
        init_val: float,
        on_change: Callable[[float], None],
        is_float: bool = False,
        unit: str = ""
    ) -> ctk.CTkSlider:
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.pack(fill="x", pady=4)

        header = ctk.CTkFrame(container, fg_color="transparent")
        header.pack(fill="x")

        ctk.CTkLabel(header, text=title, font=ctk.CTkFont(size=12), text_color="#CAD1D8").pack(side="left")

        val_text = f"{init_val:.2f}{unit}" if is_float else f"{int(init_val)}{unit}"
        val_lbl = ctk.CTkLabel(
            header,
            text=val_text,
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color="#00FFFF"
        )
        val_lbl.pack(side="right")

        def _slider_callback(value):
            if is_float:
                val_lbl.configure(text=f"{value:.2f}{unit}")
            else:
                val_lbl.configure(text=f"{int(round(value))}{unit}")
            on_change(value)

        slider = ctk.CTkSlider(
            container,
            from_=min_val,
            to=max_val,
            number_of_steps=int(max_val - min_val) if not is_float else 100,
            command=_slider_callback
        )
        slider.set(init_val)
        slider.pack(fill="x", pady=(2, 0))

        slider.val_lbl = val_lbl
        slider.unit = unit
        slider.is_float = is_float
        return slider

    def _is_light_color(self, hex_color: str) -> bool:
        r, g, b, _ = renderer.hex_to_rgba(hex_color)
        luminance = (0.299 * r + 0.587 * g + 0.114 * b)
        return luminance > 160

    def _open_color_dialog(self, attr_name: str, callback: Callable[[str], None]):
        current = getattr(self.config_data, attr_name)
        color = colorchooser.askcolor(color=current, title=f"Choose {attr_name.replace('_', ' ').title()}")
        if color and color[1]:
            callback(color[1].upper())

    def _get_profile_menu_values(self) -> List[str]:
        return self.config_data.get_all_profile_names()

    def _sync_profile_dropdown_label(self):
        curr = self.config_data.current_profile_name
        if curr in self.config_data.custom_profiles:
            self.profile_menu.set(f"⭐ {curr}")
        else:
            self.profile_menu.set(curr)

    def _on_profile_dropdown_selected(self, choice: str):
        clean_name = choice.replace("⭐ ", "").strip()
        self.config_data.load_profile_by_name(clean_name)
        self._sync_all_controls_from_config()
        self.update_all()
        if hasattr(self, "tray_manager"):
            self.tray_manager.update_menu()

    def _on_profile_selected_from_name(self, name: str):
        clean_name = name.replace("⭐ ", "").strip()
        self.config_data.load_profile_by_name(clean_name)
        self._sync_all_controls_from_config()
        self._sync_profile_dropdown_label()
        self.update_all()

    def _on_save_new_profile(self):
        name = simpledialog.askstring("Save Crosshair Profile", "Enter a name for this custom crosshair:")
        if name and name.strip():
            clean_name = name.strip()
            self.config_data.save_custom_profile(clean_name)
            self.profile_menu.configure(values=self._get_profile_menu_values())
            self._sync_profile_dropdown_label()
            if hasattr(self, "tray_manager"):
                self.tray_manager.update_menu()
            messagebox.showinfo("Profile Saved", f"Crosshair profile '{clean_name}' saved successfully!")

    def _on_overwrite_profile(self):
        curr = self.config_data.current_profile_name
        if curr in self.config_data.custom_profiles:
            self.config_data.save_custom_profile(curr)
            messagebox.showinfo("Profile Updated", f"Custom profile '{curr}' has been updated with your current changes!")
        else:
            self._on_save_new_profile()

    def _on_delete_profile(self):
        curr = self.config_data.current_profile_name
        if curr in self.config_data.custom_profiles:
            if messagebox.askyesno("Delete Profile", f"Are you sure you want to delete profile '{curr}'?"):
                self.config_data.delete_custom_profile(curr)
                self.profile_menu.configure(values=self._get_profile_menu_values())
                self._sync_profile_dropdown_label()
                self._sync_all_controls_from_config()
                self.update_all()
                if hasattr(self, "tray_manager"):
                    self.tray_manager.update_menu()
        else:
            messagebox.showwarning("Cannot Delete Preset", f"'{curr}' is a built-in preset and cannot be deleted.")

    def _update_attr(self, attr_name: str, value: Any):
        setattr(self.config_data, attr_name, value)
        self.config_data.save_to_file()
        self.update_all()

    def _on_inner_switch(self):
        self.config_data.inner_lines_enabled = bool(self.inner_switch.get())
        self.config_data.save_to_file()
        self.update_all()

    def _on_outer_switch(self):
        self.config_data.outer_lines_enabled = bool(self.outer_switch.get())
        self.config_data.save_to_file()
        self.update_all()

    def _on_outline_switch(self):
        self.config_data.outlines_enabled = bool(self.outline_switch.get())
        self.config_data.save_to_file()
        self.update_all()

    def _on_dot_switch(self):
        self.config_data.center_dot_enabled = bool(self.dot_switch.get())
        self.config_data.save_to_file()
        self.update_all()

    def _on_fade_switch(self):
        self.config_data.fade_enabled = bool(self.fade_switch.get())
        self.config_data.save_to_file()

    def _on_fade_btn_changed(self, choice: str):
        self.config_data.fade_mouse_button = choice
        self.config_data.save_to_file()

    def _on_fade_mode_changed(self, choice: str):
        self.config_data.fade_mode = choice
        self.config_data.save_to_file()

    def _on_fs_lock_switch(self):
        self.config_data.fullscreen_aggressive_mode = bool(self.fs_lock_switch.get())
        self.config_data.save_to_file()

    def _on_tray_close_switch(self):
        self.config_data.minimize_to_tray_on_close = bool(self.tray_close_switch.get())
        self.config_data.save_to_file()

    def _on_start_min_switch(self):
        self.config_data.start_minimized = bool(self.start_min_switch.get())
        self.config_data.save_to_file()

    def _on_startup_switch(self):
        enabled = bool(self.startup_switch.get())
        success = set_run_on_startup(enabled)
        if success:
            self.config_data.run_on_startup = enabled
            self.config_data.save_to_file()
            if hasattr(self, "tray_manager"):
                self.tray_manager.update_menu()
        else:
            # Revert switch if registry update failed
            if not enabled:
                self.startup_switch.select()
            else:
                self.startup_switch.deselect()

    def _toggle_startup_from_tray(self):
        currently_enabled = is_run_on_startup_enabled()
        new_state = not currently_enabled
        success = set_run_on_startup(new_state)
        if success:
            self.config_data.run_on_startup = new_state
            self.config_data.save_to_file()
            if hasattr(self, "startup_switch"):
                if new_state:
                    self.startup_switch.select()
                else:
                    self.startup_switch.deselect()
            if hasattr(self, "tray_manager"):
                self.tray_manager.update_menu()
                status = "ENABLED" if new_state else "DISABLED"
                self.tray_manager.notify("Run on Startup", f"Launch on Windows Startup is now {status}.")

    def _on_monitor_changed(self, choice: str):
        monitors = get_system_monitors()
        for idx in range(len(monitors)):
            if f"Display {idx+1}" in choice:
                self.config_data.monitor_index = idx
                break
        self.config_data.save_to_file()
        self.overlay.reposition()

    def _on_hotkey_changed(self, choice: str):
        self.config_data.toggle_hotkey = choice
        self.hotkey_badge.configure(text=f"Hotkey: [{choice}]")
        self.config_data.save_to_file()

    def _update_offset_x(self, val: int):
        self.config_data.offset_x = val
        self.config_data.save_to_file()
        self.overlay.reposition()

    def _update_offset_y(self, val: int):
        self.config_data.offset_y = val
        self.config_data.save_to_file()
        self.overlay.reposition()

    def _reset_offsets(self):
        self.config_data.offset_x = 0
        self.config_data.offset_y = 0
        self.offset_x_slider.set(0)
        self.offset_x_slider.val_lbl.configure(text="0 px")
        self.offset_y_slider.set(0)
        self.offset_y_slider.val_lbl.configure(text="0 px")
        self.config_data.save_to_file()
        self.overlay.reposition()

    def _on_inner_color_picked(self, hex_col: str):
        self.config_data.inner_line_color = hex_col
        self._update_swatch("inner_line_color", hex_col)
        self.config_data.save_to_file()
        self.update_all()

    def _on_outer_color_picked(self, hex_col: str):
        self.config_data.outer_line_color = hex_col
        self._update_swatch("outer_line_color", hex_col)
        self.config_data.save_to_file()
        self.update_all()

    def _on_outline_color_picked(self, hex_col: str):
        self.config_data.outline_color = hex_col
        self._update_swatch("outline_color", hex_col)
        self.config_data.save_to_file()
        self.update_all()

    def _on_dot_color_picked(self, hex_col: str):
        self.config_data.center_dot_color = hex_col
        self._update_swatch("center_dot_color", hex_col)
        self.config_data.save_to_file()
        self.update_all()

    def _update_swatch(self, attr_name: str, hex_col: str):
        swatch = getattr(self, f"{attr_name}_swatch", None)
        if swatch:
            swatch.config(
                bg=hex_col,
                fg="#000000" if self._is_light_color(hex_col) else "#FFFFFF",
                text=f"  {hex_col.upper()}  "
            )

    def _on_import_code(self):
        code = simpledialog.askstring("Import Valorant Crosshair Code", "Paste your Valorant crosshair share code:")
        if code:
            if parse_valorant_code(code, self.config_data):
                self.config_data.save_to_file()
                self._sync_all_controls_from_config()
                self.update_all()
                messagebox.showinfo("Success", "Valorant crosshair imported successfully!")
            else:
                messagebox.showerror("Error", "Invalid or unsupported Valorant crosshair code format.")

    def _on_export_code(self):
        code = export_valorant_code(self.config_data)
        self.clipboard_clear()
        self.clipboard_append(code)
        messagebox.showinfo("Copied to Clipboard", f"Valorant Crosshair Profile Code copied!\n\n{code}")

    def _on_import_json(self):
        file_path = filedialog.askopenfilename(
            title="Import Crosshairs & Settings from JSON",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if file_path:
            if self.config_data.import_from_json_file(file_path):
                self.profile_menu.configure(values=self._get_profile_menu_values())
                self._sync_profile_dropdown_label()
                self._sync_all_controls_from_config()
                self.update_all()
                if hasattr(self, "tray_manager"):
                    self.tray_manager.update_menu()
                messagebox.showinfo("Import Successful", f"Settings and profiles successfully imported from:\n{file_path}")
            else:
                messagebox.showerror("Import Failed", "Failed to import JSON file. Please ensure it is a valid crosshair settings file.")

    def _on_export_json(self):
        file_path = filedialog.asksaveasfilename(
            title="Export Crosshairs & Settings to JSON",
            defaultextension=".json",
            initialfile="my_valorant_crosshairs.json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if file_path:
            if self.config_data.export_to_json_file(file_path):
                messagebox.showinfo("Export Successful", f"Settings and profiles successfully exported to:\n{file_path}")
            else:
                messagebox.showerror("Export Failed", "Could not save the JSON settings file.")

    def _sync_all_controls_from_config(self):
        if self.config_data.inner_lines_enabled: self.inner_switch.select()
        else: self.inner_switch.deselect()

        if self.config_data.outer_lines_enabled: self.outer_switch.select()
        else: self.outer_switch.deselect()

        if self.config_data.outlines_enabled: self.outline_switch.select()
        else: self.outline_switch.deselect()

        if self.config_data.center_dot_enabled: self.dot_switch.select()
        else: self.dot_switch.deselect()

        self._update_swatch("inner_line_color", self.config_data.inner_line_color)
        self._update_swatch("outer_line_color", self.config_data.outer_line_color)
        self._update_swatch("outline_color", self.config_data.outline_color)
        self._update_swatch("center_dot_color", self.config_data.center_dot_color)

        def _set_slider(slider, val):
            slider.set(val)
            if getattr(slider, "is_float", False):
                slider.val_lbl.configure(text=f"{val:.2f}{slider.unit}")
            else:
                slider.val_lbl.configure(text=f"{int(round(val))}{slider.unit}")

        _set_slider(self.inner_opacity_slider, self.config_data.inner_line_opacity)
        _set_slider(self.inner_length_slider, self.config_data.inner_line_length)
        _set_slider(self.inner_thickness_slider, self.config_data.inner_line_thickness)
        _set_slider(self.inner_offset_slider, self.config_data.inner_line_offset)

        _set_slider(self.outer_opacity_slider, self.config_data.outer_line_opacity)
        _set_slider(self.outer_length_slider, self.config_data.outer_line_length)
        _set_slider(self.outer_thickness_slider, self.config_data.outer_line_thickness)
        _set_slider(self.outer_offset_slider, self.config_data.outer_line_offset)

        _set_slider(self.outline_opacity_slider, self.config_data.outline_opacity)
        _set_slider(self.outline_thickness_slider, self.config_data.outline_thickness)
        _set_slider(self.dot_opacity_slider, self.config_data.center_dot_opacity)
        _set_slider(self.dot_thickness_slider, self.config_data.center_dot_thickness)

        _set_slider(self.hold_threshold_slider, self.config_data.fade_hold_threshold_ms)
        _set_slider(self.disappear_duration_slider, self.config_data.fade_disappear_duration_ms)

        self.mouse_btn_menu.set(self.config_data.fade_mouse_button)
        self.fade_mode_menu.set(self.config_data.fade_mode)

    def _on_zoom_changed(self, val: str):
        self.preview_zoom = int(val.replace("x", ""))
        self.update_preview()

    def _on_bg_changed(self, val: str):
        self.preview_bg = val
        self.update_preview()

    def _on_grid_toggled(self):
        self.show_grid = bool(self.grid_switch.get())
        self.update_preview()

    def _on_test_pad_down(self, event):
        self.test_pad.configure(fg_color="#FD4556")

    def _on_test_pad_up(self, event):
        self.test_pad.configure(fg_color="#2A3540")

    def update_all(self):
        self.update_preview()
        if hasattr(self, "overlay"):
            self.overlay.update_crosshair()
        if hasattr(self, "tray_manager"):
            self.tray_manager.update_menu()

    def update_preview(self):
        img = renderer.render_preview_image(
            config=self.config_data,
            preview_size=240,
            zoom=self.preview_zoom,
            bg_mode=self.preview_bg,
            show_grid=self.show_grid
        )
        self.preview_photo = ImageTk.PhotoImage(img)
        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(115, 115, image=self.preview_photo)

    def toggle_overlay_state(self):
        self.overlay.toggle_overlay()
        if self.config_data.overlay_enabled:
            self.toggle_btn.configure(text="OVERLAY: ACTIVE", fg_color="#2ECC71", hover_color="#27AE60")
        else:
            self.toggle_btn.configure(text="OVERLAY: OFF", fg_color="#E74C3C", hover_color="#C0392B")

        if hasattr(self, "tray_manager"):
            self.tray_manager.update_menu()

    def _on_hotkey_toggle(self):
        self.after(0, self.toggle_overlay_state)

    def _on_fade_state_change(self, is_faded: bool):
        self.overlay.set_fade(is_faded)
        self.after(0, lambda: self._update_preview_fade(is_faded))

    def _update_preview_fade(self, is_faded: bool):
        if is_faded:
            self.preview_canvas.delete("all")
            self.preview_canvas.create_text(
                115, 115,
                text="FADED\n(Hold Threshold Exceeded\nRelease to Restore)",
                fill="#FD4556",
                font=("Segoe UI", 11, "bold"),
                justify="center"
            )
        else:
            self.update_preview()

    def _on_monitor_status_update(self, status_text: str, hold_ms: int):
        self.after(0, lambda: self._apply_status_pill(status_text, hold_ms))

    def _apply_status_pill(self, status_text: str, hold_ms: int):
        if "FADED" in status_text:
            self.status_pill.configure(
                text=f"🔴 {status_text}",
                text_color="#FD4556",
                fg_color="#2A1418"
            )
        elif "Bursting" in status_text or "Holding" in status_text:
            self.status_pill.configure(
                text=f"🟡 {status_text}",
                text_color="#F1C40F",
                fg_color="#2A2414"
            )
        else:
            self.status_pill.configure(
                text="🟢 STATUS: READY",
                text_color="#2ECC71",
                fg_color="#18222A"
            )

    def minimize_to_tray(self):
        self.withdraw()
        if hasattr(self, "tray_manager"):
            self.tray_manager.notify(
                "VALORANT Crosshair Fade",
                f"Running in system tray! Press [{self.config_data.toggle_hotkey}] in-game to toggle, or click tray icon to reopen settings."
            )

    def restore_from_tray(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def on_closing(self):
        if self.config_data.minimize_to_tray_on_close:
            self.minimize_to_tray()
        else:
            self.quit_app()

    def quit_app(self):
        if hasattr(self, "tray_manager"):
            self.tray_manager.stop()
        if hasattr(self, "monitor"):
            self.monitor.stop()
        if hasattr(self, "overlay"):
            self.overlay.destroy()
        self.destroy()
