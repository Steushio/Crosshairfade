"""
Valorant Crosshair Overlay with Mouse Click Spray-Lock Fade
Entry point script (Standard User Mode - No Admin Required).
"""

import sys
import os
import ctypes

def set_high_dpi_aware():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # PROCESS_SYSTEM_DPI_AWARE
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

def main():
    set_high_dpi_aware()
    
    # Check if bundled in PyInstaller
    if getattr(sys, 'frozen', False):
        os.chdir(os.path.dirname(sys.executable))
    else:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))

    from app_gui import CrosshairApp
    app = CrosshairApp()
    app.mainloop()

if __name__ == "__main__":
    main()
