@echo off
setlocal
cd /d "%~dp0"

echo [INFO] Launching VALORANT Crosshair Fade...
if exist "dist\ValorantCrosshairFade.exe" (
    start "" "dist\ValorantCrosshairFade.exe"
) else (
    python main.py
)
