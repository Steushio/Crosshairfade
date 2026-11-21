"""
Crosshair Configuration and Preset Management for Valorant Crosshair App.
Features custom user profile saving, persistent memory, and Valorant code import/export.
"""

import json
import os
from dataclasses import dataclass, asdict, field
from typing import Dict, Any, List

PROFILE_KEYS = [
    "outlines_enabled", "outline_opacity", "outline_thickness", "outline_color",
    "center_dot_enabled", "center_dot_opacity", "center_dot_thickness", "center_dot_color",
    "inner_lines_enabled", "inner_line_opacity", "inner_line_length", "inner_line_thickness", "inner_line_offset", "inner_line_color",
    "outer_lines_enabled", "outer_line_opacity", "outer_line_length", "outer_line_thickness", "outer_line_offset", "outer_line_color",
    "fade_enabled", "fade_hold_threshold_ms", "fade_disappear_duration_ms", "fade_mouse_button", "fade_mode",
]


@dataclass
class CrosshairConfig:
    # Overlay & Display
    overlay_enabled: bool = True
    monitor_index: int = 0
    offset_x: int = 0
    offset_y: int = 0
    toggle_hotkey: str = "F10"
    fullscreen_aggressive_mode: bool = True

    # Active Profile Name & Custom User Profiles
    current_profile_name: str = "Classic Valorant Cross (Green)"
    custom_profiles: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Outlines
    outlines_enabled: bool = True
    outline_opacity: float = 1.0
    outline_thickness: int = 1
    outline_color: str = "#000000"

    # Center Dot
    center_dot_enabled: bool = False
    center_dot_opacity: float = 1.0
    center_dot_thickness: int = 2
    center_dot_color: str = "#00FF00"

    # Inner Lines
    inner_lines_enabled: bool = True
    inner_line_opacity: float = 1.0
    inner_line_length: int = 4
    inner_line_thickness: int = 2
    inner_line_offset: int = 2
    inner_line_color: str = "#00FFFF"  # Cyan

    # Outer Lines (Separate color selection!)
    outer_lines_enabled: bool = True
    outer_line_opacity: float = 0.8
    outer_line_length: int = 2
    outer_line_thickness: int = 2
    outer_line_offset: int = 8
    outer_line_color: str = "#FFFF00"  # Yellow

    # Mouse Hold Fade / Recoil Control
    fade_enabled: bool = True
    fade_hold_threshold_ms: int = 220         # Milliseconds holding mouse before crosshair fades
    fade_disappear_duration_ms: int = 350     # Recovery duration (ms)
    fade_mouse_button: str = "Left Click"     # "Left Click" or "Right Click"
    fade_mode: str = "Hidden Until Released"  # Default: Stays hidden until hold is released!

    # System Tray & Behavior
    minimize_to_tray_on_close: bool = True
    start_minimized: bool = True              # Default: Start minimized to system tray!
    run_on_startup: bool = False              # Launch automatically on Windows startup

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CrosshairConfig":
        valid_keys = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    def extract_profile_data(self) -> Dict[str, Any]:
        """Extract visual crosshair geometry and color settings for saving."""
        data = {}
        for k in PROFILE_KEYS:
            data[k] = getattr(self, k)
        return data

    def apply_profile_data(self, data: Dict[str, Any]) -> None:
        """Apply a crosshair dictionary to current config."""
        for k, v in data.items():
            if hasattr(self, k):
                setattr(self, k, v)

    def save_custom_profile(self, name: str) -> None:
        """Saves current crosshair settings under the given profile name."""
        self.custom_profiles[name] = self.extract_profile_data()
        self.current_profile_name = name
        self.save_to_file()

    def delete_custom_profile(self, name: str) -> bool:
        """Deletes a saved custom profile."""
        if name in self.custom_profiles:
            del self.custom_profiles[name]
            if self.current_profile_name == name:
                self.current_profile_name = "Classic Valorant Cross (Green)"
            self.save_to_file()
            return True
        return False

    def load_profile_by_name(self, name: str) -> bool:
        """Loads a profile from custom_profiles or built-in PRESETS."""
        if name in self.custom_profiles:
            self.apply_profile_data(self.custom_profiles[name])
            self.current_profile_name = name
            self.save_to_file()
            return True
        elif name in PRESETS:
            self.apply_profile_data(PRESETS[name])
            self.current_profile_name = name
            self.save_to_file()
            return True
        return False

    def get_all_profile_names(self) -> List[str]:
        """Returns list of custom profiles first, then built-in presets."""
        custom = [f"⭐ {k}" for k in sorted(self.custom_profiles.keys())]
        builtin = list(PRESETS.keys())
        return custom + builtin

    def export_to_json_file(self, file_path: str) -> bool:
        """Export full configuration or custom profiles to a user-chosen JSON file."""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=4)
            return True
        except Exception as e:
            print(f"Error exporting JSON settings: {e}")
            return False

    def import_from_json_file(self, file_path: str) -> bool:
        """Import configuration and custom profiles from a user-chosen JSON file."""
        try:
            if not os.path.exists(file_path):
                return False
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # If the JSON is a full config dict
            valid_keys = self.__dataclass_fields__.keys()
            for k, v in data.items():
                if k in valid_keys:
                    setattr(self, k, v)

            # If current profile exists, apply it
            if self.current_profile_name in self.custom_profiles:
                self.apply_profile_data(self.custom_profiles[self.current_profile_name])
            elif self.current_profile_name in PRESETS:
                self.apply_profile_data(PRESETS[self.current_profile_name])

            self.save_to_file()
            return True
        except Exception as e:
            print(f"Error importing JSON settings: {e}")
            return False

    def save_to_file(self, file_path: str = "crosshair_settings.json") -> None:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")

    @classmethod
    def load_from_file(cls, file_path: str = "crosshair_settings.json") -> "CrosshairConfig":
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    cfg = cls.from_dict(data)
                    if cfg.current_profile_name in cfg.custom_profiles:
                        cfg.apply_profile_data(cfg.custom_profiles[cfg.current_profile_name])
                    elif cfg.current_profile_name in PRESETS:
                        cfg.apply_profile_data(PRESETS[cfg.current_profile_name])
                    return cfg
            except Exception as e:
                print(f"Error loading config from {file_path}: {e}")
        return cls()


# Built-in Valorant Presets
PRESETS: Dict[str, Dict[str, Any]] = {
    "Classic Valorant Cross (Green)": {
        "outlines_enabled": True,
        "outline_opacity": 1.0,
        "outline_thickness": 1,
        "outline_color": "#000000",
        "center_dot_enabled": False,
        "center_dot_opacity": 1.0,
        "center_dot_thickness": 2,
        "center_dot_color": "#00FF00",
        "inner_lines_enabled": True,
        "inner_line_opacity": 1.0,
        "inner_line_length": 6,
        "inner_line_thickness": 2,
        "inner_line_offset": 3,
        "inner_line_color": "#00FF00",
        "outer_lines_enabled": False,
        "outer_line_opacity": 0.0,
        "outer_line_length": 0,
        "outer_line_thickness": 2,
        "outer_line_offset": 10,
        "outer_line_color": "#00FF00",
        "fade_enabled": True,
        "fade_hold_threshold_ms": 220,
        "fade_disappear_duration_ms": 350,
        "fade_mouse_button": "Left Click",
        "fade_mode": "Hidden Until Released",
    },
    "TenZ (Pro)": {
        "outlines_enabled": False,
        "outline_opacity": 1.0,
        "outline_thickness": 1,
        "outline_color": "#000000",
        "center_dot_enabled": False,
        "center_dot_opacity": 1.0,
        "center_dot_thickness": 2,
        "center_dot_color": "#00FFFF",
        "inner_lines_enabled": True,
        "inner_line_opacity": 1.0,
        "inner_line_length": 4,
        "inner_line_thickness": 2,
        "inner_line_offset": 2,
        "inner_line_color": "#00FFFF",
        "outer_lines_enabled": False,
        "outer_line_opacity": 0.0,
        "outer_line_length": 0,
        "outer_line_thickness": 2,
        "outer_line_offset": 10,
        "outer_line_color": "#00FFFF",
        "fade_enabled": True,
        "fade_hold_threshold_ms": 220,
        "fade_disappear_duration_ms": 350,
        "fade_mouse_button": "Left Click",
        "fade_mode": "Hidden Until Released",
    },
    "ScreaM (Clean Dot)": {
        "outlines_enabled": True,
        "outline_opacity": 1.0,
        "outline_thickness": 1,
        "outline_color": "#000000",
        "center_dot_enabled": True,
        "center_dot_opacity": 1.0,
        "center_dot_thickness": 3,
        "center_dot_color": "#00FFFF",
        "inner_lines_enabled": False,
        "inner_line_opacity": 0.0,
        "inner_line_length": 0,
        "inner_line_thickness": 2,
        "inner_line_offset": 0,
        "inner_line_color": "#00FFFF",
        "outer_lines_enabled": False,
        "outer_line_opacity": 0.0,
        "outer_line_length": 0,
        "outer_line_thickness": 2,
        "outer_line_offset": 0,
        "outer_line_color": "#00FFFF",
        "fade_enabled": True,
        "fade_hold_threshold_ms": 250,
        "fade_disappear_duration_ms": 350,
        "fade_mouse_button": "Left Click",
        "fade_mode": "Hidden Until Released",
    },
    "Boaster (Mini Dot)": {
        "outlines_enabled": True,
        "outline_opacity": 1.0,
        "outline_thickness": 1,
        "outline_color": "#000000",
        "center_dot_enabled": True,
        "center_dot_opacity": 1.0,
        "center_dot_thickness": 2,
        "center_dot_color": "#00FF00",
        "inner_lines_enabled": False,
        "inner_line_opacity": 0.0,
        "inner_line_length": 0,
        "inner_line_thickness": 1,
        "inner_line_offset": 0,
        "inner_line_color": "#00FF00",
        "outer_lines_enabled": False,
        "outer_line_opacity": 0.0,
        "outer_line_length": 0,
        "outer_line_thickness": 1,
        "outer_line_offset": 0,
        "outer_line_color": "#00FF00",
        "fade_enabled": True,
        "fade_hold_threshold_ms": 250,
        "fade_disappear_duration_ms": 350,
        "fade_mouse_button": "Left Click",
        "fade_mode": "Hidden Until Released",
    },
    "Chronicle Dual-Tone (Cyan/Yellow)": {
        "outlines_enabled": True,
        "outline_opacity": 1.0,
        "outline_thickness": 1,
        "outline_color": "#000000",
        "center_dot_enabled": False,
        "center_dot_opacity": 1.0,
        "center_dot_thickness": 2,
        "center_dot_color": "#00FFFF",
        "inner_lines_enabled": True,
        "inner_line_opacity": 1.0,
        "inner_line_length": 4,
        "inner_line_thickness": 2,
        "inner_line_offset": 2,
        "inner_line_color": "#00FFFF",  # Cyan Inner
        "outer_lines_enabled": True,
        "outer_line_opacity": 0.9,
        "outer_line_length": 2,
        "outer_line_thickness": 2,
        "outer_line_offset": 8,
        "outer_line_color": "#FFFF00",  # Yellow Outer
        "fade_enabled": True,
        "fade_hold_threshold_ms": 220,
        "fade_disappear_duration_ms": 350,
        "fade_mouse_button": "Left Click",
        "fade_mode": "Hidden Until Released",
    },
    "Neon Split (Magenta/Cyan)": {
        "outlines_enabled": True,
        "outline_opacity": 1.0,
        "outline_thickness": 1,
        "outline_color": "#000000",
        "center_dot_enabled": True,
        "center_dot_opacity": 1.0,
        "center_dot_thickness": 2,
        "center_dot_color": "#FFFFFF",
        "inner_lines_enabled": True,
        "inner_line_opacity": 1.0,
        "inner_line_length": 5,
        "inner_line_thickness": 2,
        "inner_line_offset": 3,
        "inner_line_color": "#FF007F",  # Hot Pink Inner
        "outer_lines_enabled": True,
        "outer_line_opacity": 0.85,
        "outer_line_length": 3,
        "outer_line_thickness": 2,
        "outer_line_offset": 10,
        "outer_line_color": "#00F0FF",  # Neon Cyan Outer
        "fade_enabled": True,
        "fade_hold_threshold_ms": 220,
        "fade_disappear_duration_ms": 350,
        "fade_mouse_button": "Left Click",
        "fade_mode": "Hidden Until Released",
    },
    "Box / Square Crosshair": {
        "outlines_enabled": True,
        "outline_opacity": 1.0,
        "outline_thickness": 1,
        "outline_color": "#000000",
        "center_dot_enabled": False,
        "center_dot_opacity": 1.0,
        "center_dot_thickness": 2,
        "center_dot_color": "#FFFFFF",
        "inner_lines_enabled": True,
        "inner_line_opacity": 1.0,
        "inner_line_length": 1,
        "inner_line_thickness": 4,
        "inner_line_offset": 1,
        "inner_line_color": "#FFFFFF",
        "outer_lines_enabled": False,
        "outer_line_opacity": 0.0,
        "outer_line_length": 0,
        "outer_line_thickness": 2,
        "outer_line_offset": 5,
        "outer_line_color": "#FFFFFF",
        "fade_enabled": True,
        "fade_hold_threshold_ms": 200,
        "fade_disappear_duration_ms": 300,
        "fade_mouse_button": "Left Click",
        "fade_mode": "Hidden Until Released",
    }
}


def parse_valorant_code(code: str, config: CrosshairConfig) -> bool:
    try:
        parts = code.strip().split(";")
        if not parts:
            return False

        color_palette = [
            "#FFFFFF",  # 0 White
            "#00FF00",  # 1 Green
            "#70FF00",  # 2 Yellow Green
            "#B6FF00",  # 3 Green Yellow
            "#FFFF00",  # 4 Yellow
            "#00FFFF",  # 5 Cyan
            "#FF007F",  # 6 Pink
            "#FF0000",  # 7 Red
        ]

        i = 0
        while i < len(parts) - 1:
            key = parts[i]
            val = parts[i + 1]
            i += 2

            if key == "c":
                try:
                    c_idx = int(val)
                    if 0 <= c_idx < len(color_palette):
                        config.inner_line_color = color_palette[c_idx]
                        config.outer_line_color = color_palette[c_idx]
                        config.center_dot_color = color_palette[c_idx]
                except ValueError:
                    pass
            elif key == "u":
                hex_col = val if val.startswith("#") else f"#{val}"
                config.inner_line_color = hex_col
                config.outer_line_color = hex_col
                config.center_dot_color = hex_col
            elif key == "h":
                config.outlines_enabled = (val == "1")
            elif key == "t":
                config.outline_thickness = max(1, min(6, int(val)))
            elif key == "o":
                config.outline_opacity = max(0.0, min(1.0, float(val)))
            elif key == "d":
                config.center_dot_enabled = (val == "1")
            elif key == "z":
                config.center_dot_thickness = max(1, min(6, int(val)))
            elif key == "a":
                config.center_dot_opacity = max(0.0, min(1.0, float(val)))
            elif key == "0b":
                config.inner_lines_enabled = (val == "1")
            elif key == "0t":
                config.inner_line_thickness = max(1, min(10, int(val)))
            elif key == "0l":
                config.inner_line_length = max(0, min(20, int(val)))
            elif key == "0o":
                config.inner_line_offset = max(0, min(30, int(val)))
            elif key == "0a":
                config.inner_line_opacity = max(0.0, min(1.0, float(val)))
            elif key == "1b":
                config.outer_lines_enabled = (val == "1")
            elif key == "1t":
                config.outer_line_thickness = max(1, min(10, int(val)))
            elif key == "1l":
                config.outer_line_length = max(0, min(20, int(val)))
            elif key == "1o":
                config.outer_line_offset = max(0, min(40, int(val)))
            elif key == "1a":
                config.outer_line_opacity = max(0.0, min(1.0, float(val)))

        return True
    except Exception as e:
        print(f"Error parsing Valorant code: {e}")
        return False


def export_valorant_code(config: CrosshairConfig) -> str:
    code_parts = ["0", "P"]
    hex_col = config.inner_line_color.lstrip("#").upper()
    code_parts.extend(["u", hex_col])

    code_parts.extend(["h", "1" if config.outlines_enabled else "0"])
    if config.outlines_enabled:
        code_parts.extend(["t", str(config.outline_thickness)])
        code_parts.extend(["o", f"{config.outline_opacity:.2f}".rstrip("0").rstrip(".")])

    code_parts.extend(["d", "1" if config.center_dot_enabled else "0"])
    if config.center_dot_enabled:
        code_parts.extend(["z", str(config.center_dot_thickness)])
        code_parts.extend(["a", f"{config.center_dot_opacity:.2f}".rstrip("0").rstrip(".")])

    code_parts.extend(["0b", "1" if config.inner_lines_enabled else "0"])
    if config.inner_lines_enabled:
        code_parts.extend(["0t", str(config.inner_line_thickness)])
        code_parts.extend(["0l", str(config.inner_line_length)])
        code_parts.extend(["0o", str(config.inner_line_offset)])
        code_parts.extend(["0a", f"{config.inner_line_opacity:.2f}".rstrip("0").rstrip(".")])

    code_parts.extend(["1b", "1" if config.outer_lines_enabled else "0"])
    if config.outer_lines_enabled:
        code_parts.extend(["1t", str(config.outer_line_thickness)])
        code_parts.extend(["1l", str(config.outer_line_length)])
        code_parts.extend(["1o", str(config.outer_line_offset)])
        code_parts.extend(["1a", f"{config.outer_line_opacity:.2f}".rstrip("0").rstrip(".")])

    return ";".join(code_parts)
