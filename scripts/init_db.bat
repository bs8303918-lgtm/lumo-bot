@echo off
cd /d "%~dp0"
set PYTHONPATH=%CD%
.\.venv\Scripts\python scripts\init_db.py
pause
