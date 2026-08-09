from pathlib import Path
from aircraft import load_aircraft_config
from vspaero_run import run_vspaero_analysis
from trim import build_trim_table
from performance import compute_range_table

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "configs" / "kestrel.yaml"

def get_run_name():
    print()
    run_name = input(
        "Study name (leave blank for 'test'): "
    ).strip()

    if run_name == "":
        run_name = "test"

    # make filename safe
    run_name = (
        run_name.replace(" ", "_")
                .replace("/", "_")
                .replace("\\", "_")
    )
    return run_name

def main():
    run_name = get_run_name()
    aircraft = load_aircraft_config(CONFIG_PATH)

    output_dir = ROOT / "output"
    output_dir.mkdir(exist_ok=True)

    latest_aero_csv = (
        output_dir
        / "vsp_aero_results_alpha_elevator_latest.csv"
    )

    reuse = input(
        "Reuse existing latest VSPAERO CSV? [Y/n]: "
    ).strip().lower()

    if reuse in ("", "y", "yes"):
        if not latest_aero_csv.exists():
            raise FileNotFoundError(
                f"No existing aerodynamic CSV found: {latest_aero_csv}"
            )

        aero_csv = latest_aero_csv
        print(f"Reusing {aero_csv}")

    else:
        aero_csv = run_vspaero_analysis(
            aircraft=aircraft,
            mode="alpha_elevator",
            run_name=run_name,
        )

    trim_table = build_trim_table(
        aircraft=aircraft,
        aero_csv=aero_csv,
    )

    range_table = compute_range_table(
        aircraft=aircraft,
        trim_table=trim_table,
    )

    performance_named = (
        output_dir / f"performance_table_{run_name}.csv"
    )
    performance_latest = (
        output_dir / "performance_table_latest.csv"
    )

    range_table.to_csv(performance_named, index=False)
    range_table.to_csv(performance_latest, index=False)

    print(f"Saved {performance_named}")
    print(f"Saved {performance_latest}")
    
if __name__ == "__main__":
    main()
