# python/openvsp_setup.py

import os
import sys
from pathlib import Path

OPENVSP_ROOT = Path(os.environ.get("OPENVSP_ROOT", "/Applications/OpenVSP.app"))
OPENVSP_PY = OPENVSP_ROOT / "Contents" / "Resources" / "python"

OPENVSP_PATHS = [
    OPENVSP_PY / "openvsp",
    OPENVSP_PY / "openvsp_config",
    OPENVSP_PY / "utilities",
    OPENVSP_PY / "degen_geom",
]

for p in OPENVSP_PATHS:
    if not p.exists():
        raise FileNotFoundError(f"Missing OpenVSP Python path: {p}")
    sys.path.insert(0, str(p))

import openvsp_config

openvsp_config.LOAD_GRAPHICS = False
openvsp_config.LOAD_FACADE = False

import openvsp as vsp

VSPAERO_EXE = str(OPENVSP_ROOT / "Contents" / "Resources" / "vspaero")

def get_vsp():
    return vsp

def get_vspaero_exe():
    return VSPAERO_EXE