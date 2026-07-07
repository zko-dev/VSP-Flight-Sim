import pandas as pd
import numpy as np

from scipy.interpolate import RegularGridInterpolator
from scipy.optimize import least_squares

def get_aircraft_value(aircraft, key, default = None):
    #Parse yaml later
    return aircraft.get(key, default)

def velocity_grid_kmh(v_min=30, v_max=120, step = 1):
    return np.arange(v_min, v_max + step, step)

def kmh_to_ms(V_kmh):
    return np.asarray(V_kmh) / 3.6

def compute_cl_required(mass_kg, sref_m2, velocity_kmh, rho=1.225):
    W = mass_kg * 9.81
    V_ms = kmh_to_ms(velocity_kmh)
    CL_required = 2*W/(rho*(V_ms**2)*sref_m2)
    return pd.DataFrame({
        "V_kmh": velocity_kmh,
        "V_ms": V_ms,
        "CL_required": CL_required,
    })

def build_trim_table(aircraft, aero_csv):
    aero_df = pd.read_csv(aero_csv)

    mass_kg = aircraft["mass_kg"]
    sref_m2 = aircraft["sref_m2"]
    rho = aircraft["rho"]

    velocity_kmh = velocity_grid_kmh(30, 120, 1)

    trim_df = compute_cl_required(
        mass_kg=mass_kg,
        sref_m2=sref_m2,
        velocity_kmh=velocity_kmh,
        rho=rho,
    )

    trim_df["alpha_trim_deg"] = np.nan
    trim_df["delta_e_trim_deg"] = np.nan
    trim_df["CL_trim"] = np.nan
    trim_df["CD_trim"] = np.nan
    trim_df["CM_trim"] = np.nan
    trim_df["L_D_trim"] = np.nan
    trim_df["trim_valid"] = False

    previous_solution = None
    for i, row in trim_df.iterrows():
        result = interp_trim_at_cl(
            aero_df,
            row["CL_required"],
            previous_solution=previous_solution,
        )

        if result is None:
            continue

        for key, value in result.items():
            trim_df.loc[i, key] = value

        previous_solution = [
            result["alpha_trim_deg"],
            result["delta_e_trim_deg"],
        ]
    return trim_df

def make_surface_interpolator(aero_df, value_col):
    table = aero_df.pivot_table(
        index="alpha",
        columns="delta_e_deg",
        values=value_col,
        aggfunc="mean",
    ).sort_index().sort_index(axis=1)

    alpha_grid = table.index.to_numpy()
    de_grid = table.columns.to_numpy()
    values = table.to_numpy()

    interp = RegularGridInterpolator(
        (alpha_grid, de_grid),
        values,
        bounds_error=False,
        fill_value=np.nan,
    )

    return interp, alpha_grid, de_grid

def interp_trim_at_cl(aero_df, cl_req, previous_solution=None):
    cl_interp, alpha_grid, de_grid = make_surface_interpolator(aero_df, "CLtot")
    cm_interp, _, _ = make_surface_interpolator(aero_df, "CMytot")
    cd_interp, _, _ = make_surface_interpolator(aero_df, "CDtot")

    alpha_min, alpha_max = alpha_grid.min(), alpha_grid.max()
    de_min, de_max = de_grid.min(), de_grid.max()

    def residual(x):
        alpha, de = x
        pt = np.array([[alpha, de]])

        cl = cl_interp(pt)[0]
        cm = cm_interp(pt)[0]

        if np.isnan(cl) or np.isnan(cm):
            return [1e3, 1e3]

        return [
            cl - cl_req,
            cm,
        ]

    if previous_solution is None:
        # Start from closest raw CL point
        idx = (aero_df["CLtot"] - cl_req).abs().idxmin()
        x0 = np.array([
            aero_df.loc[idx, "alpha"],
            aero_df.loc[idx, "delta_e_deg"],
        ])
    else:
        x0 = np.array(previous_solution)

    sol = least_squares(
        residual,
        x0=x0,
        bounds=([alpha_min, de_min], [alpha_max, de_max]),
        xtol=1e-10,
        ftol=1e-10,
        gtol=1e-10,
        max_nfev=200,
    )

    if not sol.success:
        return None

    alpha_trim, de_trim = sol.x
    cl_trim = cl_interp([[alpha_trim, de_trim]])[0]
    cm_trim = cm_interp([[alpha_trim, de_trim]])[0]
    cd_trim = cd_interp([[alpha_trim, de_trim]])[0]

    if np.isnan(cl_trim) or np.isnan(cm_trim) or np.isnan(cd_trim):
        return None

    if abs(cl_trim - cl_req) > 0.02 or abs(cm_trim) > 0.01:
        return None

    return {
        "alpha_trim_deg": alpha_trim,
        "delta_e_trim_deg": de_trim,
        "CL_trim": cl_trim,
        "CD_trim": cd_trim,
        "CM_trim": cm_trim,
        "L_D_trim": cl_trim / cd_trim if cd_trim > 0 else np.nan,
        "trim_valid": True,
    }