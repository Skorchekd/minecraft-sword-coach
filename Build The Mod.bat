@echo off
rem Copyright (C) 2026 Skorchekd, ApocalypseGamer1, Crazyon and centerx (MCA - Minecraft Combat AI, https://minecraftcombatai.com/)
rem SPDX-License-Identifier: GPL-3.0-only
setlocal EnableExtensions
title Build Sword Coach mod
cd /d "%~dp0mod"

rem Builds the Fabric mod (needs a Java 25 JDK; installs Eclipse Temurin 25 with winget if none is found).
rem The jar is copied next to this file; put it in your Minecraft mods folder with Fabric API.

call :findjava
if defined JAVA_HOME goto build
echo A Java 25 JDK was not found. Installing Eclipse Temurin 25 with winget...
winget install -e --id EclipseAdoptium.Temurin.25.JDK --accept-source-agreements --accept-package-agreements
call :findjava
if not defined JAVA_HOME (
  echo Could not find a Java 25 JDK. Install one from adoptium.net, then run this again.
  goto fail
)

:build
echo Using Java at %JAVA_HOME%
rem clean first, so only this version's jar is left to copy
call gradlew.bat clean build || goto fail
for %%f in (build\libs\swordcoach-*.jar) do copy /y "%%f" "%~dp0" >nul && set "JAR=%%~nxf"
echo.
echo Built %JAR% (next to this file). Put it in your mods folder together with Fabric API,
echo and take any older swordcoach jar out of the mods folder (two copies stop the game from starting).
explorer /select,"%~dp0%JAR%"
goto end

:findjava
rem An existing JAVA_HOME is kept when it is a JDK 25 (its folder name says 25), else look in the usual places.
if defined JAVA_HOME if exist "%JAVA_HOME%\bin\javac.exe" echo %JAVA_HOME%| findstr /c:"25" >nul && exit /b 0
set "JAVA_HOME="
for /d %%d in ("%ProgramFiles%\Eclipse Adoptium\jdk-25*" "%ProgramFiles%\Java\jdk-25*" "%ProgramFiles%\Microsoft\jdk-25*") do if exist "%%~d\bin\javac.exe" set "JAVA_HOME=%%~d"
exit /b 0

:fail
echo.
echo The build failed (see above).
:end
pause
