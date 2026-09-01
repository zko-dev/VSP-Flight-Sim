from pathlib import Path
import subprocess

import pandas as pd
import matplotlib.pyplot as plt


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKDIR = PROJECT_ROOT / "OpenVSP"

XFOIL_EXE = Path("/opt/homebrew/bin/xfoil")

REYNOLDS = 200_000
MACH = 0.05

ALPHA_MIN = -12.0
ALPHA_MAX = 16.0
ALPHA_STEP = 0.5

ITERATIONS = 2000


# ---------------------------------------------------------
# Select airfoil
# ---------------------------------------------------------

def select_airfoil(workdir):
    airfoil_files = sorted(workdir.glob("*-selig.dat"))

    if not airfoil_files:
        raise FileNotFoundError(
            f"No .dat airfoil files found in:\n{workdir}"
        )

    print("\nAvailable airfoils:")

    for i, path in enumerate(airfoil_files, start=1):
        print(f"  [{i}] {path.name}")

    while True:
        choice = input("\nSelect airfoil: ").strip()

        try:
            index = int(choice) - 1

            if 0 <= index < len(airfoil_files):
                return airfoil_files[index]

        except ValueError:
            pass

        print("Invalid selection. Enter one of the numbers above.")


# ---------------------------------------------------------
# Run XFOIL
# ---------------------------------------------------------
def run_xfoil_branch(airfoil_path, polar_filename, alpha_end, alpha_step):

    polar_path = WORKDIR / polar_filename
    input_path = WORKDIR / f"{polar_path.stem}.in"

    if polar_path.exists():
        polar_path.unlink()

    commands = f"""LOAD {airfoil_path.name}
PANE
OPER
VISC {REYNOLDS}
MACH {MACH}
ITER {ITERATIONS}
PACC
{polar_filename}

ALFA 0
ASEQ 0 {alpha_end} {alpha_step}
PACC

QUIT
"""

    input_path.write_text(commands)

    with open(input_path, "r") as stdin_file:
        result = subprocess.run(
            [str(XFOIL_EXE)],
            stdin=stdin_file,
            text=True,
            capture_output=True,
            cwd=WORKDIR,
        )

    if result.returncode != 0:
        raise RuntimeError(
            f"""
XFOIL failed for {polar_filename}

--- STDOUT ---
{result.stdout}

--- STDERR ---
{result.stderr}
"""
        )

    if not polar_path.exists():
        raise RuntimeError(
            f"XFOIL did not generate:\n{polar_path}"
        )

    return polar_path


def run_xfoil(airfoil_path):

    airfoil_name = airfoil_path.stem

    print("\n--------------------------------")
    print("Running XFOIL")
    print("--------------------------------")
    print(f"Airfoil:       {airfoil_path.name}")
    print(f"Reynolds:      {REYNOLDS:,}")
    print(f"Mach:          {MACH}")
    print(f"Alpha range:   {ALPHA_MIN} -> {ALPHA_MAX} deg")

    # Positive branch
    positive_path = run_xfoil_branch(
        airfoil_path,
        "xfoil_positive.pol",
        ALPHA_MAX,
        ALPHA_STEP,
    )

    # Negative branch
    negative_path = run_xfoil_branch(
        airfoil_path,
        "xfoil_negative.pol",
        ALPHA_MIN,
        -ALPHA_STEP,
    )

    return positive_path, negative_path

# ---------------------------------------------------------
# Parse XFOIL polar
# ---------------------------------------------------------

def load_polar(polar_path):

    df = pd.read_csv(
        polar_path,
        sep=r"\s+",
        skiprows=12,
        names=[
            "alpha",
            "CL",
            "CD",
            "CDp",
            "CM",
            "Top_Xtr",
            "Bot_Xtr",
            "Top_Itr",
            "Bot_Itr",
        ],
    )

    # Make sure the important columns are numeric.
    # Any malformed XFOIL rows become NaN.
    numeric_columns = [
        "alpha",
        "CL",
        "CD",
        "CDp",
        "CM",
        "Top_Xtr",
        "Bot_Xtr",
    ]

    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Remove rows where XFOIL did not produce usable aero data
    df = df.dropna(
        subset=["alpha", "CL", "CD", "CM"]
    ).reset_index(drop=True)

    if df.empty:
        raise RuntimeError(
            f"No valid aerodynamic data found in:\n{polar_path}"
        )

    return df

def load_single_polar(polar_path):

    df = pd.read_csv(
        polar_path,
        sep=r"\s+",
        skiprows=12,
        names=[
            "alpha",
            "CL",
            "CD",
            "CDp",
            "CM",
            "Top_Xtr",
            "Bot_Xtr",
            "Top_Itr",
            "Bot_Itr",
        ],
    )

    numeric_columns = [
        "alpha",
        "CL",
        "CD",
        "CDp",
        "CM",
        "Top_Xtr",
        "Bot_Xtr",
    ]

    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(
        subset=["alpha", "CL", "CD", "CM"]
    )

    return df

def load_polar(positive_path, negative_path):

    df_positive = load_single_polar(positive_path)
    df_negative = load_single_polar(negative_path)

    df = pd.concat(
        [df_negative, df_positive],
        ignore_index=True,
    )

    # Both runs contain alpha = 0, so remove duplicate
    df = (
        df.drop_duplicates(subset="alpha", keep="first")
        .sort_values("alpha")
        .reset_index(drop=True)
    )

    if df.empty:
        raise RuntimeError("No valid XFOIL aerodynamic data.")

    return df
# ---------------------------------------------------------
# Basic airfoil characteristics
# ---------------------------------------------------------

def analyze_polar(df):

    # -----------------------------------------------------
    # Maximum lift
    # -----------------------------------------------------

    i_clmax = df["CL"].idxmax()
    cl_max = df.loc[i_clmax, "CL"]
    alpha_clmax = df.loc[i_clmax, "alpha"]

    # -----------------------------------------------------
    # Minimum lift
    # -----------------------------------------------------

    i_clmin = df["CL"].idxmin()
    cl_min = df.loc[i_clmin, "CL"]
    alpha_clmin = df.loc[i_clmin, "alpha"]

    # -----------------------------------------------------
    # Lift-to-drag
    # -----------------------------------------------------

    df["L_D"] = df["CL"] / df["CD"]

    i_ldmax = df["L_D"].idxmax()
    ld_max = df.loc[i_ldmax, "L_D"]
    alpha_ldmax = df.loc[i_ldmax, "alpha"]

    # -----------------------------------------------------
    # Check XFOIL sweep coverage
    # -----------------------------------------------------

    actual_alpha_min = df["alpha"].min()
    actual_alpha_max = df["alpha"].max()

    negative_sweep_complete = (
        actual_alpha_min <= ALPHA_MIN + ALPHA_STEP
    )

    positive_sweep_complete = (
        actual_alpha_max >= ALPHA_MAX - ALPHA_STEP
    )

    # -----------------------------------------------------
    # Check whether extrema hit sweep boundaries
    # -----------------------------------------------------

    clmax_at_boundary = (
        abs(alpha_clmax - ALPHA_MAX) < 1e-6
        or abs(alpha_clmax - ALPHA_MIN) < 1e-6
    )

    clmin_at_boundary = (
        abs(alpha_clmin - ALPHA_MAX) < 1e-6
        or abs(alpha_clmin - ALPHA_MIN) < 1e-6
    )

    # -----------------------------------------------------
    # Print sweep coverage
    # -----------------------------------------------------

    print("\n--------------------------------")
    print("XFOIL Sweep Coverage")
    print("--------------------------------")

    print(
        f"Requested alpha:     "
        f"{ALPHA_MIN:.1f} -> {ALPHA_MAX:.1f} deg"
    )

    print(
        f"Converged alpha:     "
        f"{actual_alpha_min:.1f} -> {actual_alpha_max:.1f} deg"
    )

    if not negative_sweep_complete:
        print(
            f"WARNING: Negative-alpha sweep did not reach "
            f"{ALPHA_MIN:.1f} deg."
        )

    if not positive_sweep_complete:
        print(
            f"WARNING: Positive-alpha sweep did not reach "
            f"{ALPHA_MAX:.1f} deg."
        )

    # -----------------------------------------------------
    # Print airfoil characteristics
    # -----------------------------------------------------

    print("\n--------------------------------")
    print("Airfoil Characteristics")
    print("--------------------------------")

    if positive_sweep_complete:
        print(f"CLmax:              {cl_max:.4f}")
        print(f"Alpha at CLmax:     {alpha_clmax:.2f} deg")

        if clmax_at_boundary:
            print("WARNING: CLmax occurs at alpha sweep boundary.")
    else:
        print(f"Highest converged CL: {cl_max:.4f}")
        print(f"Alpha:                {alpha_clmax:.2f} deg")
        print("CLmax:                 UNRESOLVED")

    print()

    if negative_sweep_complete:
        print(f"CLmin:              {cl_min:.4f}")
        print(f"Alpha at CLmin:     {alpha_clmin:.2f} deg")

        if clmin_at_boundary:
            print("WARNING: CLmin occurs at alpha sweep boundary.")
    else:
        print(f"Lowest converged CL:  {cl_min:.4f}")
        print(f"Alpha:                {alpha_clmin:.2f} deg")
        print("CLmin:                 UNRESOLVED")

    print()

    print(f"Max L/D:            {ld_max:.2f}")
    print(f"Alpha at max L/D:   {alpha_ldmax:.2f} deg")

    # -----------------------------------------------------
    # Return results
    # -----------------------------------------------------

    return {
        "CL_max": cl_max if positive_sweep_complete else None,
        "alpha_CL_max_deg": (
            alpha_clmax if positive_sweep_complete else None
        ),

        "CL_min": cl_min if negative_sweep_complete else None,
        "alpha_CL_min_deg": (
            alpha_clmin if negative_sweep_complete else None
        ),

        "LD_max": ld_max,
        "alpha_LD_max_deg": alpha_ldmax,

        "actual_alpha_min_deg": actual_alpha_min,
        "actual_alpha_max_deg": actual_alpha_max,

        "positive_sweep_complete": positive_sweep_complete,
        "negative_sweep_complete": negative_sweep_complete,

        "CL_max_at_boundary": clmax_at_boundary,
        "CL_min_at_boundary": clmin_at_boundary,
    }


# ---------------------------------------------------------
# Plot results
# ---------------------------------------------------------

def plot_polar(df):

    # CL vs alpha
    plt.figure()
    plt.plot(df["alpha"], df["CL"], marker=".")
    plt.xlabel("Alpha [deg]")
    plt.ylabel("CL")
    plt.title("XFOIL Lift Curve")
    plt.grid(True)
    plt.show()

    # Drag polar
    plt.figure()
    plt.plot(df["CD"], df["CL"], marker=".")
    plt.xlabel("CD")
    plt.ylabel("CL")
    plt.title("XFOIL Drag Polar")
    plt.grid(True)
    plt.show()

    # L/D
    plt.figure()
    plt.plot(df["alpha"], df["L_D"], marker=".")
    plt.xlabel("Alpha [deg]")
    plt.ylabel("L/D")
    plt.title("XFOIL Lift-to-Drag Ratio")
    plt.grid(True)
    plt.show()

    # Pitching moment
    plt.figure()
    plt.plot(df["alpha"], df["CM"], marker=".")
    plt.xlabel("Alpha [deg]")
    plt.ylabel("CM")
    plt.title("XFOIL Pitching Moment")
    plt.grid(True)
    plt.show()


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

if __name__ == "__main__":

    airfoil_path = select_airfoil(WORKDIR)

    positive_path, negative_path = run_xfoil(airfoil_path)

    polar_df = load_polar(
        positive_path,
        negative_path,
    )

    print("\nPolar data:")
    print(polar_df.to_string(index=False))

    results = analyze_polar(polar_df)

    plot_polar(polar_df)