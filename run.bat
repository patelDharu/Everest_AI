@echo off
title Everest AI Assistant - 7Span
echo ============================================================
echo Starting Everest AI Streamlit Application (Virtual Env)...
echo ============================================================
cd /d " \%~dp0\\
call venv\Scripts\activate.bat
python -m streamlit run app.py
pause
