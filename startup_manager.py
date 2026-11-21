"""
Windows Startup Manager using the Registry Run key:
HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run
"""

import sys
import os
import winreg

APP_REG_NAME = "ValorantCrosshairFade"
RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"


def get_executable_command() -> str:
    """
    Returns the launch command string for the current app.
    Works whether running as compiled executable or python script.
    """
    if getattr(sys, "frozen", False):
        exe_path = os.path.abspath(sys.executable)
        return f'"{exe_path}"'
    else:
        python_exe = sys.executable
        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "main.py"))
        return f'"{python_exe}" "{script_path}"'


def is_run_on_startup_enabled() -> bool:
    """Check if the app is currently registered in Windows HKCU Run key."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_READ)
        try:
            value, _ = winreg.QueryValueEx(key, APP_REG_NAME)
            return bool(value)
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)
    except Exception as e:
        print(f"Error checking startup status: {e}")
        return False


def set_run_on_startup(enable: bool) -> bool:
    """Enable or disable starting the app on Windows user login."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            RUN_KEY_PATH,
            0,
            winreg.KEY_SET_VALUE | winreg.KEY_READ
        )
        try:
            if enable:
                cmd = get_executable_command()
                winreg.SetValueEx(key, APP_REG_NAME, 0, winreg.REG_SZ, cmd)
                return True
            else:
                try:
                    winreg.DeleteValue(key, APP_REG_NAME)
                except FileNotFoundError:
                    pass
                return True
        finally:
            winreg.CloseKey(key)
    except Exception as e:
        print(f"Error modifying startup registry key: {e}")
        return False
