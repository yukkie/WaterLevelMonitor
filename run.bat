@echo off
set CMD=%1

set PYTHON=venv\Scripts\python.exe
if not exist %PYTHON% set PYTHON=python

if "%CMD%"=="streamlit" (
    echo Starting Streamlit...
    %PYTHON% -m streamlit run src/app.py
) else if "%CMD%"=="test" (
    echo Running tests...
    %PYTHON% -m pytest
) else (
    echo Starting Main...
    %PYTHON% -m src.main
)
