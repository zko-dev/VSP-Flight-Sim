import pandas as pd
import numpy as np

from pathlib import Path

from scipy.interpolate import RegularGridInterpolator
from scipy.optimize import least_squares

def get_reference_value(yaml_value, vsp_value):
    if yaml_value is None:
        return vsp_value
    return yaml_value

def parse_vspaero_header(vspaero_file):
    values = {}

    keys = {
        "Sref": "sref_m2",
        "Cref": "cref_m",
        "Bref": "bref_m",
        "X_cg": "cg_x_m",
        "Y_cg": "cg_y_m",
        "Z_cg": "cg_z_m",
        "Mach": "mach",
        "Vinf": "vinf_mps",
        "Rho": "rho",
        "AoA": "alpha_deg",
        "Beta": "beta_deg",
        "ReCref": "re_cref",
    }

    with open(vspaero_file, "r") as f:
        for line in f:
            line = line.strip()

            if "=" not in line:
                continue

            left, right = line.split("=", 1)
            left = left.strip()
            right = right.strip()

            if left in keys:
                try:
                    values[keys[left]] = float(right)
                except ValueError:
                    pass

    return values

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

def get_elevator_limits(aircraft, de_grid):
    yaml_de_min = aircraft["control_limits"]["elevator_min_deg"]
    yaml_de_max = aircraft["control_limits"]["elevator_max_deg"]

    csv_de_min = de_grid.min()
    csv_de_max = de_grid.max()

    de_min = max(csv_de_min, yaml_de_min)
    de_max = min(csv_de_max, yaml_de_max)

    return de_min, de_max

def build_trim_table(aircraft, aero_csv):
    aero_df = pd.read_csv(aero_csv)
    
    root = Path(__file__).resolve().parent.parent

    vspaero_file = root / aircraft["vsp"]["aero_file"]
    vsp_info = parse_vspaero_header(vspaero_file)

    mass_kg = aircraft["mass_kg"]

    sref_m2 = get_reference_value(
        aircraft["reference_geometry"]["sref_m2"],
        vsp_info["sref_m2"],
    )

    rho = get_reference_value(
        aircraft["rho"],
        vsp_info["rho"],
    )

    cref_m = get_reference_value(
    aircraft["reference_geometry"]["cref_m"],
    vsp_info["cref_m"],
    )

    bref_m = get_reference_value(
        aircraft["reference_geometry"]["bref_m"],
        vsp_info["bref_m"],
    )

    cg_x_m = get_reference_value(
        aircraft["cg_m"]["x"],
        vsp_info["cg_x_m"],
    )

    cg_y_m = get_reference_value(
        aircraft["cg_m"]["y"],
        vsp_info["cg_y_m"],
    )

    cg_z_m = get_reference_value(
        aircraft["cg_m"]["z"],
        vsp_info["cg_z_m"],
    )

    velocity_kmh = velocity_grid_kmh(30, 120, 1)

    trim_df = compute_cl_required(
        mass_kg=mass_kg,
        sref_m2=sref_m2,
        velocity_kmh=velocity_kmh,
        rho=rho,
    )

    trim_df["mass_kg"] = mass_kg
    trim_df["sref_m2"] = sref_m2
    trim_df["cref_m"] = cref_m
    trim_df["bref_m"] = bref_m
    trim_df["cg_x_m"] = cg_x_m
    trim_df["cg_y_m"] = cg_y_m
    trim_df["cg_z_m"] = cg_z_m
    trim_df["rho"] = rho
    trim_df["alpha_trim_deg"] = np.nan
    trim_df["delta_e_trim_deg"] = np.nan
    trim_df["CL_trim"] = np.nan
    trim_df["CD_trim"] = np.nan
    trim_df["CM_trim"] = np.nan
    trim_df["L_D_trim"] = np.nan
    trim_df["trim_valid"] = False
    trim_df["Cma_per_deg"] = np.nan
    trim_df["Cma_per_rad"] = np.nan
    trim_df["Cmde_per_deg"] = np.nan
    trim_df["Cmde_per_rad"] = np.nan
    trim_df["elevator_margin_up_deg"] = np.nan
    trim_df["elevator_margin_down_deg"] = np.nan
    trim_df["elevator_authority_score"] = np.nan
    trim_df["Cma_fit_points"] = np.nan
    trim_df["Cmde_fit_points"] = np.nan

    previous_solution = None
    for i, row in trim_df.iterrows():
        result = interp_trim_at_cl(
            aero_df,
            row["CL_required"],
            aircraft=aircraft,
            previous_solution=previous_solution,
        )

        if result is None:
            continue

        for key, value in result.items():
            trim_df.loc[i, key] = value

        derivs = stability_derivatives_at_trim(
            aero_df,
            result["alpha_trim_deg"],
            result["delta_e_trim_deg"],
            aircraft=aircraft,
        )

        if derivs is not None:
            for key, value in derivs.items():
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

def interp_trim_at_cl(aero_df, cl_req, aircraft, previous_solution=None):
    cl_interp, alpha_grid, de_grid = make_surface_interpolator(aero_df, "CLtot")
    cm_interp, _, _ = make_surface_interpolator(aero_df, "CMytot")
    cd_interp, _, _ = make_surface_interpolator(aero_df, "CDtot")

    alpha_min, alpha_max = alpha_grid.min(), alpha_grid.max()
    de_min, de_max = get_elevator_limits(aircraft, de_grid)

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

    x0[0] = np.clip(x0[0], alpha_min, alpha_max)
    x0[1] = np.clip(x0[1], de_min, de_max)


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

def stability_derivatives_at_trim(
    aero_df,
    alpha_trim,
    de_trim,
    aircraft,
):
    cm_interp, alpha_grid, de_grid = make_surface_interpolator(
        aero_df,
        "CMytot",
    )

    de_min, de_max = get_elevator_limits(aircraft, de_grid)

    # ---------------------------------------------------------
    # Cm_alpha: fit CM versus alpha across the full alpha sweep
    # while holding elevator fixed at the trimmed deflection.
    # ---------------------------------------------------------
    alpha_points = np.column_stack(
        [
            alpha_grid,
            np.full(len(alpha_grid), de_trim),
        ]
    )

    cm_alpha_values = cm_interp(alpha_points)

    valid_alpha = np.isfinite(cm_alpha_values)

    if valid_alpha.sum() < 2:
        return None

    cma_per_deg, cma_intercept = np.polyfit(
        alpha_grid[valid_alpha],
        cm_alpha_values[valid_alpha],
        1,
    )

    # ---------------------------------------------------------
    # Cm_delta_e: fit CM versus elevator across the full usable
    # elevator sweep while holding alpha fixed at trim.
    # ---------------------------------------------------------
    usable_de_grid = de_grid[
        (de_grid >= de_min)
        & (de_grid <= de_max)
    ]

    de_points = np.column_stack(
        [
            np.full(len(usable_de_grid), alpha_trim),
            usable_de_grid,
        ]
    )

    cm_de_values = cm_interp(de_points)

    valid_de = np.isfinite(cm_de_values)

    if valid_de.sum() < 2:
        return None

    cmde_per_deg, cmde_intercept = np.polyfit(
        usable_de_grid[valid_de],
        cm_de_values[valid_de],
        1,
    )

    return {
        "Cma_per_deg": cma_per_deg,
        "Cma_per_rad": cma_per_deg * 180.0 / np.pi,

        "Cmde_per_deg": cmde_per_deg,
        "Cmde_per_rad": cmde_per_deg * 180.0 / np.pi,

        "Cma_fit_points": int(valid_alpha.sum()),
        "Cmde_fit_points": int(valid_de.sum()),

        "elevator_margin_up_deg": de_trim - de_min,
        "elevator_margin_down_deg": de_max - de_trim,
        "elevator_authority_score": min(
            de_trim - de_min,
            de_max - de_trim,
        ),
    }