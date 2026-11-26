@echo off
rem Fieldnote: opens the window; it starts Claude Code hidden on your subscription login.
cd /d "%~dp0"
uv run --script fieldnote\app.py
if errorlevel 1 (
  echo.
  echo Fieldnote could not start. Check that uv and Microsoft Edge WebView2 are installed.
  pause
)
