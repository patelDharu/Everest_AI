@echo off
cd /d "%~dp0"
echo ========================================================
echo   Syncing 160+ Real Everest CSV Files from D:\everest_data_zip...
echo ========================================================
.\venv\Scripts\python.exe sync_everest_real_data.py
pause
