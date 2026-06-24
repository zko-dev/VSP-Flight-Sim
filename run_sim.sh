#!/bin/bash
set -e

echo "--------------"
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

if [ ! -d "venvsource" ]; then
    /opt/homebrew/bin/python3.13 -m venv venvsource
fi
source venvsource/bin/activate
python --version

echo "Sourcing OpenVSP environment..."
export OPENVSP_ROOT="/Applications/OpenVSP.app"
export OPENVSP_PY="$OPENVSP_ROOT/Contents/Resources/python"
export PYTHONPATH="$OPENVSP_PY/openvsp:$OPENVSP_PY/openvsp_config:$OPENVSP_PY/utilities:$OPENVSP_PY/degen_geom:$PYTHONPATH"
export VSPAERO="$OPENVSP_ROOT/Contents/Resources/vspaero"
echo "OpenVSP environment loaded"

echo "Generating degenGeom file..."
python python/generate_degenGeom.py

echo "Running VSPAERO analysis..."
python python/vspaero_run.py

echo "Generating results in Flight_Calc.ipynb..."
jupyter nbconvert --execute --to notebook --inplace Flight_Calc.ipynb
echo ""
echo "Please run Flight_Calc.ipynb natively to use interactive plotting tool!"
