@echo off
rem Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
rem SPDX-License-Identifier: GPL-3.0-only
setlocal EnableExtensions
title Sword Coach server
cd /d "%~dp0server"

rem Sword Coach server: reads your fights from the mod and serves the review page.
rem First run: finds or installs Python 3.12, makes a private environment in server\.venv and
rem installs numpy and onnxruntime into it. Later runs just start the server.

set "PY="
if exist ".venv\Scripts\python.exe" goto run
py -3.12 -c "import sys" >nul 2>&1 && set "PY=py -3.12"
if not defined PY py -3 -c "import sys; assert sys.version_info >= (3, 10)" >nul 2>&1 && set "PY=py -3"
if not defined PY python -c "import sys; assert sys.version_info >= (3, 10)" >nul 2>&1 && set "PY=python"
if defined PY goto venv

echo Python 3.10+ was not found. Installing Python 3.12 with winget (Windows's package manager)...
winget install -e --id Python.Python.3.12 --scope user --accept-source-agreements --accept-package-agreements
if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PY="%LocalAppData%\Programs\Python\Python312\python.exe""
if not defined PY py -3.12 -c "import sys" >nul 2>&1 && set "PY=py -3.12"
if not defined PY (
  echo Could not install Python automatically. Install Python 3.12 from python.org, then run this again.
  goto fail
)

:venv
echo Setting up the Sword Coach environment (first run only)...
%PY% -m venv .venv || goto fail
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check --upgrade pip >nul
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt || goto fail

:run
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt >nul 2>&1
echo Starting Sword Coach. Leave this window open while you play; close it to stop.
".venv\Scripts\python.exe" -m swordcoach.server
goto end

:fail
echo.
echo Something went wrong (see above).
:end
pause
