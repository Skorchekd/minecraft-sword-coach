@echo off
rem Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
rem SPDX-License-Identifier: GPL-3.0-only
setlocal EnableExtensions
title Bundle fight data
cd /d "%~dp0"

rem Packs your saved fights (data\fights) and your relabels (data\labels) into one zip next to this
rem file, for you to send, after checking every fight reads back. Nothing is uploaded: what happens to the
rem zip is up to you. Uses the server's Python (run Launch AI Server.bat once first).

if not exist "server\.venv\Scripts\python.exe" (
  echo Run Launch AI Server.bat once first: it sets up the Python this uses.
  goto end
)
pushd server
".venv\Scripts\python.exe" -m swordcoach.bundle > "%TEMP%\swordcoach-bundle.txt" || (type "%TEMP%\swordcoach-bundle.txt" & popd & goto fail)
popd
type "%TEMP%\swordcoach-bundle.txt"
for /f "usebackq delims=" %%z in ("%TEMP%\swordcoach-bundle.txt") do set "ZIP=%%z"
explorer /select,"%ZIP%"
goto end

:fail
echo Could not make the zip (see above).
:end
pause
