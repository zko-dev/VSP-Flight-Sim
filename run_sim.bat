@echo off
setlocal

echo --------------
cd /d "%~dp0"

REM Create virtual environment if it doesn't exist
if not exist "venvsource\" (
    echo Creating virtual environment...
    py -3.13 -m venv venvsource
)

REM Activate virtual environment
call venvsource\Scripts\activate.bat

python --version

echo Running aircraft study...
python python\run_study.py

pause