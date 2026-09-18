@echo off
cd /d "%~dp0"
echo ========================================================
echo   Running Everest AI Bulk CSV Importer...
echo ========================================================
.\venv\Scripts\python.exe import_csvs.py
pause
