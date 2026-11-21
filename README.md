# Valorant Custom Crosshair Overlay with Mouse Click Spray-Lock Fade

A high-performance standalone Windows desktop overlay designed specifically for **VALORANT** players.

---

## ✨ Features

1. **Valorant Geometry & Independent Colors**:
   - Outlines (Opacity, Thickness, Custom Color)
   - Center Dot (Opacity, Thickness, Custom Color)
   - **Inner Lines** (Opacity, Length, Thickness, Offset, **Independent Color**)
   - **Outer Lines** (Opacity, Length, Thickness, Offset, **Independent Color**)
   - Full live preview canvas with pixel-grid and map background choices (Dark, Valorant Slate, Icebox, Bind, Green Screen).

2. **Mouse Click Spray-Lock Fade (Trigger Discipline / Recoil Control)**:
   - When firing (Left Click held down), the crosshair disappears after a customizable threshold (e.g., 200ms).
   - **Stays hidden for the entire duration of the spray/burst until the mouse click is released**, instantly reappearing when ready for the next tap.
   - Built-in interactive "Click & Hold Test Pad" in the GUI to dial in timings.

3. **Persistent Profile Manager & JSON Import/Export**:
   - Save custom crosshairs under custom names (e.g. `⭐ TenZ Cyan`, `⭐ Yellow Dot`).
   - Overwrite, update, and delete profiles anytime.
   - **Persistent Memory**: The app automatically saves and restores the last selected profile and settings across reboots in `crosshair_settings.json`.
   - **JSON Import / Export**:
     - `📥 Import JSON`: Load external backup files containing all your profiles and customizations.
     - `📤 Export JSON`: Save a portable `.json` backup file of your entire crosshair library.
   - Included built-in pro presets (Dot, Tenz, Shroud, Boaster, Box, Shotgun, Plus, Circle, etc.).
   - Valorant Official Share Code Import & Export.

4. **System Tray Integration & Windows Startup**:
   - **Starts Minimized by Default**: Seamlessly sits in the Windows System Tray with a custom crosshair icon.
   - **Launch on Windows Startup**: Toggle switch in Settings and right-click System Tray menu (`Run on Windows Startup: [ON/OFF]`) to automatically start the app minimized when Windows boots.
   - Right-click tray menu to quickly switch profiles, toggle overlay on/off, open GUI, or exit.
   - Global toggle hotkey (`F10`) to hide/show the crosshair anytime in-game.

5. **Direct Fullscreen Compatibility**:
   - Click-through transparent layered Win32 window (`WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE | WS_EX_TOPMOST`).
   - Unparented tool window isolated from task switches (`GWLP_HWNDPARENT`).
   - Continuous 40 Hz topmost Z-order keeper loop.
   - Built with `--uac-admin` privilege elevation to stay on top of games.

---

## 🚀 How to Run

### Option 1: Standalone Executable (Standard User - No Admin Required)
You can directly run the compiled standalone `.exe`:
```
dist\ValorantCrosshairFade.exe
```
*(No administrative prompt or UAC elevation required)*

### Option 2: Run via Batch Script
Double-click `run.bat` in the root folder.

### Option 3: Run via Python
```powershell
python main.py
```

---

## 🎮 Fullscreen Configuration for Valorant

Modern games run best using Windows 10/11's **Fullscreen Optimizations (Independent Flip)**:

1. **Fullscreen Optimizations**: Make sure "Disable fullscreen optimizations" is **unchecked** on `VALORANT-Win64-Shipping.exe`.
2. **In-Game Display Mode**: Set Valorant to **Fullscreen**.
3. **Run as Administrator**: The app automatically prompts for Administrator privilege to ensure it stays in front of game frames.

---

## 📁 Project Structure

- `main.py`: Entry point with DPI awareness and UAC elevation handling.
- `app_gui.py`: CustomTkinter dark-themed interface, sliders, color pickers, and tester pad.
- `crosshair_config.py`: Profile manager, presets, and JSON persistence.
- `renderer.py`: Precision pixel renderer calculating spoke boxes, offsets, and outlines.
- `overlay_window.py`: Zero-input-lag transparent click-through Win32 overlay window.
- `mouse_monitor.py`: High-frequency asynchronous mouse click monitor for spray-lock fade.
- `tray_manager.py`: Windows System Tray integration with quick profile switcher.
- `run.bat`: Quick admin launcher batch script.
- `dist/ValorantCrosshairFade.exe`: Single-file standalone executable.
