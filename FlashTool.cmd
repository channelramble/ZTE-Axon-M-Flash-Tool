@echo off
rem ZTE AXON M FLASH TOOL launcher
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0FlashTool.ps1"
if errorlevel 1 pause
