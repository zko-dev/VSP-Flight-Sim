import openvsp_config
openvsp_config.LOAD_GRAPHICS = False
openvsp_config.LOAD_FACADE = False

import openvsp as vsp
from pathlib import Path
import subprocess
import pandas as pd
import numpy as np
import time
start_time = time.perf_counter()

import shutil

ROOT = Path(__file__).resolve().parent.parent / "OpenVSP"
vsp_file = ROOT / "Aircraft.vsp3"

vsp.ClearVSPModel()
vsp.ReadVSPFile(str(vsp_file))
vsp.Update()

analysis_name = "VSPAEROSweep"
vsp.SetAnalysisInputDefaults(analysis_name)
vsp.PrintAnalysisInputs(analysis_name)

#Run sim
print("Running vspaero_run.py...")
CASE_Name = "Aircraft"
VSPAERO_EXE = "/Applications/OpenVSP.app/Contents/Resources/vspaero"
OMP_THREADS = 8 #Bump this up if computer is good
NUM_WAKE_NODES = 16
NUM_WAKE_ITERS = 8

ALPHA_SWEEP = [-8,-6,-4,-2,0,2,4,6,8]
BETA_SWEEP = [0]
ELEVATOR_SWEEP = [0,20,40] #positive is nose up
#ELEVATOR_SWEEP = [20]
AILERON_SWEEP = [0] #positive is nose up

#V_flight = np.array([30,60,90]) #kmh
#MACH_SWEEP = (V_flight/(3.6*340)).astype(int)
#MACH_SWEEP = [0.03,0.05,0.07]
MACH_SWEEP = [0.05]
#XCG_SWEEP = [0.032, 0.036, 0.045, 0.05]
XCG_SWEEP = [0.036]
YCG = 0.0
ZCG = 0.007

CONVERGENCE_TARGET = 1e+3 #L2 Residual

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

def regenerate_degen_geom():
    vsp.ClearVSPModel()
    vsp.ReadVSPFile(str(vsp_file))
    vsp.Update()
    analysis_name = "Aircraft"
    vsp.SetAnalysisInputDefaults(analysis_name)
    vsp.SetComputationFileName(
        vsp.DEGEN_GEOM_CSV_TYPE, 
        str(ROOT / f"{CASE_Name}.csv")
    )
    print("Regenerating DegenGeom...")
    vsp.ExecAnalysis(analysis_name)

def setup_vspaero(alpha_deg, beta_deg, xcg, mach, delta_e_deg=0.0, aileron_e_deg=0.0):
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
    vsp.SetDoubleAnalysisInput(analysis_name, "Ycg", [YCG])
    vsp.SetDoubleAnalysisInput(analysis_name, "Zcg", [ZCG])

    print(f"Running alpha = {alpha_deg} deg, beta = {beta_deg}, elevator = {delta_e_deg}, Aileron={aileron_e_deg}")
    vsp.ExecAnalysis(analysis_name)

#L2 Residual convergence target
def check_l2_residual():
    history_path = ROOT / f"{CASE_Name}.history"
    if not history_path.exists():
        raise FileNotFoundError(f"Missing history file: {history_path}")
    residuals = []
    for line in history_path.read_text().splitlines():
        parts = line.split()
        for p in parts:
            try:
                val = float(p)
                residuals.append(val)
            except ValueError:
                pass

    if not residuals:
        raise RuntimeError(f"No numeric residual data")
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
def main():
    case_num = 1
    regenerate_degen_geom()
    results = []
    for delta_e in ELEVATOR_SWEEP:
        for delta_a in AILERON_SWEEP:
            for alpha in ALPHA_SWEEP:
                for beta in BETA_SWEEP:
                    for xcg in XCG_SWEEP:
                        for mach in MACH_SWEEP:
                            """
                            src = ROOT / "Aircraft.case.1.quad.1.dat"
                            dst = ROOT / f"Aircraft.case.{case_num}.quad.1.dat"
                            if src.exists():
                                shutil.copy2(src,dst)
                            case_num += 1
                            SAFE_DIR = ROOT.parent / "quad_backup"
                            SAFE_DIR.mkdir(exist_ok=True)
                            for f in ROOT.glob("Aircraft.case.*.quad.*.dat"):
                                shutil.copy2(f,SAFE_DIR/f.name)
                            """
                            
                            setup_vspaero(alpha, beta, xcg, mach)
                            patch_control_angles(delta_e,delta_a) #Overwrites stock .vspaero
                            run_vspaero()
                            residual = check_l2_residual()

                            #save additional data to .csv
                            data = read_latest_polar_row()
                            data["delta_e_deg"] = delta_e
                            data["aileron_e_deg"] = delta_a
                            data["alpha_commanded"] = alpha
                            data["beta_commanded"] = beta
                            data["xcg"] = xcg
                            results.append(data)
    """
    for f in SAFE_DIR.glob("Aircraft.case.*.quad.*.dat"):
        shutil.copy2(f,ROOT / f.name)
    """

    df = pd.DataFrame(results)
    output_dir = ROOT.parent / "output"
    output_dir.mkdir(exist_ok=True)

    df.to_csv(output_dir / "vsp_aero_results.csv", index=False)

#guards against accidental run during import
if __name__ == "__main__":
    main()

finish_time = time.perf_counter()
elapsed_time = finish_time - start_time
print(f"vspaero_run.py completed in {elapsed_time:.2f} seconds")