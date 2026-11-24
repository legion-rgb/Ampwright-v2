@echo off
cd /d "%~dp0"
uv run --script desktop_app.py
if errorlevel 1 (
  echo.
  echo Fieldnote could not start. Check that uv and Microsoft Edge WebView2 are installed.
  pause
)
