@echo off
cd /d "%~dp0"
py -3 bench.py
if errorlevel 1 pause
