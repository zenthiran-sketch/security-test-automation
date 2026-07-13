@echo off
setlocal EnableExtensions
cd /d "%~dp0"

REM HexStrike single-command setup + start for Windows Command Prompt
REM Usage: start.bat
REM        start.bat --skip-tools
REM        start.bat --skip-install

title HexStrike Setup and Start
color 0A

echo.
echo  ============================================================
echo   HexStrike - install dependencies and start UI + API
echo  ============================================================
echo.

chcp 65001 >nul 2>&1
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

if exist "%USERPROFILE%\go\bin" set "PATH=%USERPROFILE%\go\bin;%PATH%"
if exist "%LOCALAPPDATA%\Programs\Go\bin" set "PATH=%LOCALAPPDATA%\Programs\Go\bin;%PATH%"

set "PY_CMD="
where python >nul 2>&1 && set "PY_CMD=python"
if not defined PY_CMD (
  where py >nul 2>&1 && set "PY_CMD=py -3"
)
if not defined PY_CMD (
  where python3 >nul 2>&1 && set "PY_CMD=python3"
)

if not defined PY_CMD (
  echo [ERROR] Python was not found on PATH.
  echo.
  echo Install Python 3.10+ from https://www.python.org/downloads/
  echo During setup, check "Add python.exe to PATH".
  echo Then open a NEW Command Prompt and run:  start.bat
  echo.
  pause
  exit /b 1
)

where node >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Node.js was not found on PATH.
  echo Install LTS from https://nodejs.org/ then open a NEW Command Prompt.
  echo.
  pause
  exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
  echo [ERROR] npm was not found on PATH. Reinstall Node.js.
  echo.
  pause
  exit /b 1
)

echo [hexstrike] Using: %PY_CMD%
%PY_CMD% --version
node --version
npm --version
echo.

if exist "%~dp0.venv\Scripts\python.exe" (
  echo [hexstrike] Existing .venv detected - will reuse / refresh it.
)

echo [hexstrike] Running setup and starting servers...
echo [hexstrike] UI will open at http://localhost:5173
echo [hexstrike] Press Ctrl+C later to stop both servers.
echo.

%PY_CMD% "%~dp0start.py" %*
set "EXITCODE=%ERRORLEVEL%"

if not "%EXITCODE%"=="0" (
  echo.
  echo [ERROR] HexStrike exited with code %EXITCODE%.
  echo Check hexstrike.log in this folder for API errors.
  echo.
  pause
  exit /b %EXITCODE%
)

endlocal
exit /b 0