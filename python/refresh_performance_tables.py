# refresh_performance_tables.py

from pathlib import Path
import numpy as np

import pandas as pd
import yaml

import trim
from trim import build_trim_table


ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"

print("Using trim.py from:", trim.__file__)
print("ROOT:", ROOT)
print("OUTPUT_DIR:", OUTPUT_DIR)

with open(ROOT / "configs" / "kestrel.yaml", "r") as f:
    aircraft = yaml.safe_load(f)

vspaero_csvs = sorted(OUTPUT_DIR.glob("vsp_aero_results_alpha_elevator_*.csv"))

performance_cols = [
    "drag_N",
    "shaft_power_W",
    "electrical_power_W",
    "aux_power_W",
    "total_power_W",
    "endurance_min",
    "range_km",
]
def add_performance_columns(trim_df, aircraft):
    df = trim_df.copy()

    eta_prop = aircraft["eta_prop"]
    eta_motor = aircraft["eta_motor"]
    eta_esc = aircraft["eta_esc"]

    voltage = aircraft["battery"]["voltage_V"]
    capacity_Ah = aircraft["battery"]["capacity_Ah"]
    usable_fraction = aircraft["battery"]["usable_fraction"]

    aux_power_W = aircraft["aux_power_W"]

    battery_energy_Wh = voltage * capacity_Ah * usable_fraction

    q = 0.5 * df["rho"] * df["V_ms"]**2
    df["drag_N"] = q * df["sref_m2"] * df["CD_trim"]

    df["shaft_power_W"] = df["drag_N"] * df["V_ms"] / eta_prop
    df["electrical_power_W"] = df["shaft_power_W"] / (eta_motor * eta_esc)
    df["aux_power_W"] = aux_power_W
    df["total_power_W"] = df["electrical_power_W"] + df["aux_power_W"]

    df["endurance_min"] = battery_energy_Wh / df["total_power_W"] * 60
    df["range_km"] = df["V_ms"] * df["endurance_min"] * 60 / 1000

    invalid = df["trim_valid"].astype(str).str.lower() != "true"

    cols = [
        "drag_N",
        "shaft_power_W",
        "electrical_power_W",
        "total_power_W",
        "endurance_min",
        "range_km",
    ]

    df.loc[invalid, cols] = np.nan

    return df

for aero_csv in vspaero_csvs:
    case_name = aero_csv.stem.replace("vsp_aero_results_alpha_elevator_", "")
    perf_csv = OUTPUT_DIR / f"performance_table_{case_name}.csv"

    print(f"Refreshing {perf_csv.name}")

    old_perf_df = pd.read_csv(perf_csv) if perf_csv.exists() else None
    trim_df = build_trim_table(aircraft, aero_csv)
    trim_df = add_performance_columns(trim_df, aircraft)

    if old_perf_df is not None:
        cols_to_merge = [
            c for c in performance_cols
            if c in old_perf_df.columns and c not in trim_df.columns
        ]

        if cols_to_merge:
            trim_df = trim_df.merge(
                old_perf_df[["V_kmh"] + cols_to_merge],
                on="V_kmh",
                how="left",
            )

    print("aero_csv:", aero_csv)
    print("perf_csv:", perf_csv)
    print("columns:", trim_df.columns.tolist())

    trim_df.to_csv(perf_csv, index=False)

