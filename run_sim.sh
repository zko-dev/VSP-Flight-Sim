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

echo "Running aircraft study..."
python3 python/run_study.py