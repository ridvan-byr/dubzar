@echo off
rem Dubzar installer launcher: runs kur.ps1 without needing any PowerShell settings.
title Dubzar kurulum
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0kur.ps1"
echo.
pause
