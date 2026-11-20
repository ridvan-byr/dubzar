@echo off
rem Dubzar uninstaller launcher.
title Dubzar kaldir
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0kaldir.ps1"
echo.
pause
