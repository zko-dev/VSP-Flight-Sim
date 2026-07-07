@echo off
setlocal

echo Creating virtual environment...
py -3.13 -m venv venvsource

echo Activating virtual environment...
call venvsource\Scripts\activate.bat

python --version

echo Upgrading pip...
python -m ensurepip --upgrade
python -m pip install --upgrade pip

echo Installing required packages...
python -m pip install -r requirements.txt

REM echo Launching Flight_Calc Setup GUI...
REM jupyter nbconvert --to html --execute Flight_Calc.ipynb
REM start Flight_Calc.html

echo Setup complete.
pause