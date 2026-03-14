@echo off
echo ============================================================
echo   ATEM Mini Controller - Build EXE
echo ============================================================

:: Use pyinstaller from PATH, or find it in common user Scripts location
where pyinstaller > nul 2>&1
if errorlevel 1 (
    echo pyinstaller not found in PATH, trying pip install...
    pip install pyinstaller
)

:: Locate pyinstaller executable
set "PYINST=pyinstaller"
where pyinstaller > nul 2>&1
if errorlevel 1 (
    :: Fallback: user Scripts directory
    for /f "delims=" %%i in ('python -c "import sysconfig; print(sysconfig.get_path(\"scripts\", \"nt_user\"))"') do set "PYINST=%%i\pyinstaller.exe"
)

:: Build (-y: overwrite output dir without confirmation)
"%PYINST%" -y ^
    --onefile ^
    --name atem ^
    --console ^
    --add-data "static;static" ^
    --add-data "presets.json;." ^
    --hidden-import uvicorn.logging ^
    --hidden-import uvicorn.loops ^
    --hidden-import uvicorn.loops.auto ^
    --hidden-import uvicorn.protocols ^
    --hidden-import uvicorn.protocols.http ^
    --hidden-import uvicorn.protocols.http.auto ^
    --hidden-import uvicorn.protocols.websockets ^
    --hidden-import uvicorn.protocols.websockets.auto ^
    --hidden-import uvicorn.lifespan ^
    --hidden-import uvicorn.lifespan.on ^
    --hidden-import anyio ^
    --hidden-import anyio._backends._asyncio ^
    main.py

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Build complete: dist\atem.exe
echo ============================================================
echo.
echo   How to deploy:
echo   1. Copy dist\atem.exe to the target PC
echo   2. Run atem.exe
echo   3. Open http://localhost:8000/config to configure
echo      (ATEM IP, simulator mode, source names, etc.)
echo   4. Save and restart atem.exe to apply settings
echo.
echo   Files created next to atem.exe:
echo   - atem.conf    : user settings (overrides defaults)
echo   - presets.json : preset data
echo ============================================================
pause
