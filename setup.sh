#!/bin/bash

/opt/homebrew/bin/python3.13 -m venv venvsource venv/bin/activate
python --version

echo "upgrading pip..."
python -m ensurepip --upgrade
python -m pip install --upgrade pip

echo "Installing required packages..."
python -m pip install -r requirements.txt

#echo "Launching Flight_Calc Setup GUI..."
#jupyter nbconvert --to html --execute Flight_Calc.ipynb && open Flight_Calc.html
