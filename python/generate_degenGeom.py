# generate_degenGeom.py
from openvsp_path import get_vsp

vsp = get_vsp()

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OPENVSP_DIR = PROJECT_ROOT / "OpenVSP"

CASE_NAME = "Aircraft"
VSP_FILE = OPENVSP_DIR / f"{CASE_NAME}.vsp3"


def clean_old_solver_files():
    extensions = [
        ".vspaero",
        ".vspgeom",
        ".csv",
        ".adb",
        ".history",
        ".polar",
        ".lod",
        ".tri",
    ]

    for ext in extensions:
        path = OPENVSP_DIR / f"{CASE_NAME}{ext}"
        if path.exists():
            print(f"Deleting old {path.name}")
            path.unlink()


def generate_solver_geometry():
    print(f"Loading {VSP_FILE}")

    vsp.ClearVSPModel()
    vsp.ReadVSPFile(str(VSP_FILE))
    vsp.Update()

    # This is the closest Python equivalent to preparing VSPAERO solver geometry.
    analysis_name = "VSPAEROComputeGeometry"
    vsp.SetAnalysisInputDefaults(analysis_name)

    # Usually -1 means use the current/default VSPAERO geometry set.
    # If your VSPAERO set is specifically Set 3, change this to [3].
    vsp.SetIntAnalysisInput(analysis_name, "GeomSet", [-1])

    print("Generating VSPAERO solver geometry...")
    vsp.ExecAnalysis(analysis_name)

    expected = [
        OPENVSP_DIR / f"{CASE_NAME}.vspaero",
        OPENVSP_DIR / f"{CASE_NAME}.vspgeom",
        OPENVSP_DIR / f"{CASE_NAME}.csv",
    ]

    for path in expected:
        if path.exists():
            print(f"Created: {path}")
        else:
            print(f"Missing: {path}")


def main():
    clean_old_solver_files()
    generate_solver_geometry()


if __name__ == "__main__":
    main()