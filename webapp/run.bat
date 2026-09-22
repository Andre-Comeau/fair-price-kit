@echo off
rem Double-click launcher for the fair-price-kit webapp. Same as running
rem "python webapp/server.py" from the repo root -- this just does that for you and keeps the
rem window open afterward so an error is readable instead of flashing shut.
cd /d "%~dp0.."
if not "%ANTHROPIC_API_KEY%"=="" goto run
echo NOTE: ANTHROPIC_API_KEY is not set in this window -- drafting will be disabled.
echo Every other feature (scan, register lookup, award search) still works.
echo See webapp\README.md if you want drafting enabled.
echo.
:run
python webapp\server.py
echo.
echo (server stopped -- close this window, or press Ctrl+C above to stop it while it's running)
pause >nul
