from pathlib import Path
import time
start_time = time.perf_counter()

import openvsp_config 
openvsp_config.LOAD_GRAPHICS = False
openvsp_config.LOAD_FACADE = False

import openvsp as vsp
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

vsp_file = ROOT / "OpenVSP" / "Aircraft.vsp3"
out_file = ROOT / "output" / "Aircraft.csv"
out_file.parent.mkdir(exist_ok=True)

print("OpenVSP version:", vsp.GetVSPVersion())
print("Reading:", vsp_file)

vsp.ClearVSPModel()
if not vsp_file.exists():
    raise FileNotFoundError(vsp_file)
vsp.ReadVSPFile(str(vsp_file))
vsp.Update()

res_id = vsp.ComputeDegenGeom(
    vsp.SET_ALL,
    vsp.DEGEN_GEOM_CSV_TYPE
)
print("DegenGeom Generated")
print("DegenGeom Result ID: ", out_file)

finish_time = time.perf_counter()
elapsed_time = finish_time - start_time
print(f"generate_degenGeom.py completed in {elapsed_time:.2f} seconds")