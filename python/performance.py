import pandas as pd
import numpy as np

def compute_range_table(aircraft, trim_table):
    if trim_table.empty:
        raise ValueError("trim_table is empty")

    sref_m2 = float(trim_table["sref_m2"].iloc[0])
    rho = float(trim_table["rho"].iloc[0])

    mass_kg = aircraft["mass_kg"]
    df = trim_table.copy()

    rho = trim_table["rho"].iloc[0]
    sref_m2 = trim_table["sref_m2"].iloc[0]

    eta_prop = aircraft["eta_prop"]
    eta_motor = aircraft["eta_motor"]
    eta_esc = aircraft["eta_esc"]

    aux_power_W = aircraft["aux_power_W"]

    battery = aircraft["battery"]
    battery_energy_Wh = (
        battery["voltage_V"]
        * battery["capacity_Ah"]
        * battery["usable_fraction"]
    )
    df["drag_N"] = np.nan
    df["shaft_power_W"] = np.nan
    df["electrical_power_W"] = np.nan
    df["aux_power_W"] = aux_power_W
    df["total_power_W"] = np.nan
    df["endurance_min"] = np.nan
    df["range_km"] = np.nan

    valid = df["trim_valid"] == True

    if "CD_trim" in df.columns:
        df.loc[valid, "drag_N"] = (
            0.5
            * rho
            * df.loc[valid, "V_ms"]**2
            * sref_m2
            * df.loc[valid, "CD_trim"]
        )

        df.loc[valid, "shaft_power_W"] = (
            df.loc[valid, "drag_N"]
            * df.loc[valid, "V_ms"]
        )

        df.loc[valid, "electrical_power_W"] = (
            df.loc[valid, "shaft_power_W"]
            / (eta_prop * eta_motor * eta_esc)
        )

        df.loc[valid, "total_power_W"] = (
            df.loc[valid, "electrical_power_W"]
            + aux_power_W
        )

        df.loc[valid, "endurance_min"] = (
            battery_energy_Wh
            / df.loc[valid, "total_power_W"]
            * 60
        )

        df.loc[valid, "range_km"] = (
            df.loc[valid, "V_kmh"]
            * df.loc[valid, "endurance_min"]
            / 60
        )

    return df