from openvsp_path import get_vsp, get_vspaero_exe
vsp = get_vsp()
VSPAERO_EXE = get_vspaero_exe()
from pathlib import Path
import subprocess
import pandas as pd
import numpy as np
import time
start_time = time.perf_counter()

import yaml
from trim import parse_vspaero_header
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "configs" / "kestrel.yaml"
with open(CONFIG_PATH, "r") as f:
    AIRCRAFT = yaml.safe_load(f)
VSPAERO_CONFIG = AIRCRAFT["vspaero"]

import shutil

from itertools import product

def initialize_vsp_model(vsp_file):
    vsp.ClearVSPModel()
    vsp.ReadVSPFile(str(vsp_file))
    vsp.Update()
    analysis_name = "VSPAEROSweep"
    vsp.SetAnalysisInputDefaults(analysis_name)
    vsp.PrintAnalysisInputs(analysis_name)

#Run sim
print("Running vspaero_run.py...")
ROOT = PROJECT_ROOT / "OpenVSP"
CASE_Name = AIRCRAFT["vsp"]["case_name"]
vsp_file = PROJECT_ROOT / AIRCRAFT["vsp"]["file"]

ANALYSIS_MODE = VSPAERO_CONFIG["analysis_mode"]
OMP_THREADS = VSPAERO_CONFIG["omp_threads"]
NUM_WAKE_NODES = VSPAERO_CONFIG["num_wake_nodes"]
NUM_WAKE_ITERS = VSPAERO_CONFIG["num_wake_iters"]
CONVERGENCE_TARGET = VSPAERO_CONFIG["convergence_target"]
BATCH_PRESETS = VSPAERO_CONFIG["batch_presets"]
FULL_ANALYSIS_SEQUENCE = VSPAERO_CONFIG["full_analysis_sequence"]

def patch_control_angles(delta_e_deg, aileron_e_deg):
    vspaero_path = ROOT / f"{CASE_Name}.vspaero"
    lines = vspaero_path.read_text().splitlines()
    for i,line in enumerate(lines):
        parts = line.split()
        if line.strip() == "Ruddervon":
            lines[i+3] = f"{delta_e_deg:.3f}"
        elif line.strip() == "Aileron":
            lines[i+3] = f"{aileron_e_deg:.3f}"
    vspaero_path.write_text("\n".join(lines)+"\n")

def regenerate_solver_geometry():
    vsp.ClearVSPModel()
    vsp.ReadVSPFile(str(vsp_file))
    vsp.Update()

    analysis_name = "VSPAEROComputeGeometry"
    vsp.SetAnalysisInputDefaults(analysis_name)

    print("Regenerating VSPAERO solver geometry...")
    vsp.ExecAnalysis(analysis_name)

def setup_vspaero(alpha_deg, beta_deg, xcg, ycg, zcg, mach, delta_e_deg=0.0, aileron_e_deg=0.0):
    vsp.ClearVSPModel()
    vsp.ReadVSPFile(str(vsp_file))
    vsp.Update()
    
    analysis_name = "VSPAEROSweep"
    vsp.SetAnalysisInputDefaults(analysis_name)
    vsp.PrintAnalysisInputs(analysis_name)

    #CFD config declaration
    vsp.SetIntAnalysisInput(analysis_name, "NumWakeNodes", [NUM_WAKE_NODES])
    vsp.SetIntAnalysisInput(analysis_name, "WakeNumIter", [NUM_WAKE_ITERS])
    #vsp.SetIntAnalysisInput(analysis_name, "FixedWakeFlag", [1])

    #Alpha sweep
    vsp.SetDoubleAnalysisInput(analysis_name, "AlphaStart", [alpha_deg])
    vsp.SetIntAnalysisInput(analysis_name, "AlphaNpts", [1])

    #Beta sweep
    vsp.SetDoubleAnalysisInput(analysis_name, "BetaStart", [beta_deg])
    vsp.SetIntAnalysisInput(analysis_name, "BetaNpts", [1])

    #Mach sweep
    vsp.SetDoubleAnalysisInput(analysis_name, "MachStart", [mach])
    vsp.SetIntAnalysisInput(analysis_name, "MachNpts", [1])

    #CG location
    vsp.SetDoubleAnalysisInput(analysis_name, "Xcg", [xcg])
    vsp.SetDoubleAnalysisInput(analysis_name, "Ycg", [ycg])
    vsp.SetDoubleAnalysisInput(analysis_name, "Zcg", [zcg])

    print(f"Running alpha = {alpha_deg} deg, beta = {beta_deg}, elevator = {delta_e_deg}, Aileron={aileron_e_deg}")
    vsp.ExecAnalysis(analysis_name)

#L2 Residual convergence target
def check_l2_residual():
    history_files = list(ROOT.glob(f"{CASE_Name}.history"))
    if not history_files:
        print(f"History file not found: {CASE_Name}.history")
        return np.nan
    history_path = max(history_files, key=lambda p: p.stat().st_mtime)

    residuals = []
    for line in history_path.read_text().splitlines():
        parts = line.split()
        for p in parts:
            try:
                residuals.append(float(p))
            except ValueError:
                pass

    if not residuals:
        raise RuntimeError(f"No numeric residual data in {history_path}")
    final_residual = abs(residuals[-1])
    print(f"L2 residual: {final_residual:.3e}")
    if final_residual > CONVERGENCE_TARGET:
        raise RuntimeError(
            f"VSPAERO failed convergence: residual {final_residual:.3e} > {CONVERGENCE_TARGET:.1e}"
        )
    return final_residual

#Configure solver
def run_vspaero():
    print("cwd =", ROOT)
    print("vspaero =", ROOT / CASE_Name)
    print("csv =", ROOT / f"{CASE_Name}.csv")
    print("vspgeom =", ROOT / f"{CASE_Name}.vspgeom")
    subprocess.run(
        [VSPAERO_EXE, "-omp", str(OMP_THREADS), CASE_Name], 
        cwd=ROOT,
        check=True,
    )

#Read .polar
def read_latest_polar_row():
    polar_path = ROOT / f"{CASE_Name}.polar"
    rows = []
    for line in polar_path.read_text().splitlines():
        parts = line.split()

        try:
            nums = [float(x) for x in parts]
        except ValueError:
            continue
        if len(nums)>= 16:
            rows.append(nums)
    if not rows:
        raise RuntimeError(f"No numeric rows found in {polar_path}")
    
    row = rows[-1]

    #Output map: 
    return {
        "beta": row[0],
        "Mach": row[1],
        "alpha": row[2],
        "Re_1e6": row[3],

        "CLo": row[4],
        "CLi": row[5],
        "CLtot": row[6],

        "CDo": row[7],
        "CDi": row[8],
        "CDtot": row[9],

        "CSo": row[10],
        "CSi": row[11],
        "CStot": row[12],

        "L/D": row[13],
        "E": row[14],

        "CMox": row[15],
        "CMoy": row[16],
        "CMoz": row[17],

        "CMix": row[18],
        "CMiy": row[19],
        "CMiz": row[20],

        "CMxtot": row[21],
        "CMytot": row[22],
        "CMztot": row[23],

        "CFox": row[24],
        "CFoy": row[25],
        "CFoz": row[26],

        "CFix": row[27],
        "CFiy": row[28],
        "CFiz": row[29],

        "CFxtot": row[30],
        "CFytot": row[31],
        "CFztot": row[32],

        "CLwtot": row[33],
        "CDwtot": row[34],
        "CSwtot": row[35],

        "CLiw": row[36],
        "CDiw": row[37],
        "CSiw": row[38],

        "CFwxtot": row[39],
        "CFwytot": row[40],
        "CFwztot": row[41],

        "CFiwx": row[42],
        "CFiwy": row[43],
        "CFiwz": row[44],

        "LoDw": row[45],
        "Ew": row[46],
        "StallFactor": row[47],
    }

#setup batch run:
def run_batch(batch):
    results = []

    for delta_e, delta_a, alpha, beta, xcg, ycg, zcg, mach in product(
        batch["elevator"],
        batch["aileron"],
        batch["alpha"],
        batch["beta"],
        batch["xcg"],
        batch["ycg"],
        batch["zcg"],
        batch["mach"],
    ):
        setup_vspaero(alpha, beta, xcg, ycg, zcg, mach)
        patch_control_angles(delta_e, delta_a)
        run_vspaero()
        residual = check_l2_residual()

        data = read_latest_polar_row()

        vsp_info = parse_vspaero_header(ROOT / f"{CASE_Name}.vspaero")
        data.update(vsp_info)

        data["analysis_tag"] = batch["tag"]
        data["delta_e_deg"] = delta_e
        data["aileron_e_deg"] = delta_a
        data["alpha_commanded"] = alpha
        data["beta_commanded"] = beta
        data["xcg"] = xcg
        data["ycg"] = ycg
        data["zcg"] = zcg
        data["mach_commanded"] = mach
        data["l2_residual"] = residual

        results.append(data)

    return pd.DataFrame(results)


def main(run_name="test"):
    print("Running vspaero_run.py...")
    output_dir = ROOT.parent / "output"
    output_dir.mkdir(exist_ok=True)
    initialize_vsp_model(vsp_file)
    initialize_vsp_model(vsp_file)

    regenerate_solver_geometry()

    if ANALYSIS_MODE == "full":
        all_dfs = []

        for mode in FULL_ANALYSIS_SEQUENCE:
            print(f"\n=== Running batch: {mode} ===")
            batch = BATCH_PRESETS[mode]
            df = run_batch(batch)

            batch_output = output_dir / f"vsp_aero_results_{mode}_{run_name}.csv"
            df.to_csv(batch_output, index=False)
            all_dfs.append(df)

        df_all = pd.concat(all_dfs, ignore_index=True)
        df_all.to_csv(output_dir / "vsp_aero_results_full.csv", index=False)

    else:
        batch = BATCH_PRESETS[ANALYSIS_MODE]
        df = run_batch(batch)
        df.to_csv(output_dir / f"vsp_aero_results_{ANALYSIS_MODE}.csv", index=False)

def run_vspaero_analysis(aircraft=None, mode="full", run_name="test"):
    global ANALYSIS_MODE

    ANALYSIS_MODE = mode

    start_time = time.perf_counter()
    main(run_name=run_name)
    elapsed_time = time.perf_counter() - start_time

    print(f"vspaero_run.py completed in {elapsed_time:.2f} seconds")

    output_dir = ROOT.parent / "output"

    if mode == "full":
        return output_dir / "vsp_aero_results_full.csv"

    source_output = output_dir / f"vsp_aero_results_{mode}.csv"
    named_output = output_dir / f"vsp_aero_results_{mode}_{run_name}.csv"
    latest_output = output_dir / f"vsp_aero_results_{mode}_latest.csv"

    if not source_output.exists():
        raise FileNotFoundError(f"Expected output not found: {source_output}")

    shutil.copy2(source_output, named_output)
    shutil.copy2(source_output, latest_output)

    return latest_output

print("VSP exe path:     ", vsp.GetVSPExePath())
print("VSPAERO path:     ", vsp.GetVSPAEROPath())
print("VSPAERO found:    ", vsp.CheckForVSPAERO(vsp.GetVSPAEROPath()))

#guards against accidental run during import
if __name__ == "__main__":
    run_vspaero_analysis(mode=ANALYSIS_MODE)
