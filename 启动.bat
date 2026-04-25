@echo off
:: Duplicate File Finder Launcher
python duplicate_finder_ctk.py
if %errorlevel% neq 0 (
    py duplicate_finder_ctk.py
)
pause
