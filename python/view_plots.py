from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

from dash import Dash, dcc, html, Input, Output


ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"

PERFORMANCE_CSV = OUTPUT_DIR / "performance_table_latest.csv"
VSPAERO_ALPHA_ELEVATOR_CSV = OUTPUT_DIR / "vsp_aero_results_alpha_elevator_latest.csv"

def list_performance_comparison_files():
    files = sorted(OUTPUT_DIR.glob("performance_table_*.csv"))
    return [f for f in files if "latest" not in f.name]


def list_vspaero_comparison_files(include_latest=False):
    files = sorted(OUTPUT_DIR.glob("vsp_aero_results_alpha_elevator_*.csv"))
    if include_latest:
        return files
    return [f for f in files if "latest" not in f.name]

def study_name_from_path(path, prefix):
    stem = Path(path).stem
    return stem.replace(prefix, "")

def load_csv(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Missing CSV file: {path}")
    return pd.read_csv(path)


def numeric_columns(df):
    return df.select_dtypes(include="number").columns.tolist()


def valid_trim_df(df):
    if "trim_valid" not in df.columns:
        return df.copy()

    # Handles True/False stored as bool or string
    return df[df["trim_valid"].astype(str).str.lower() == "true"].copy()

def all_case_options(files, latest_label, latest_value):
    return [{"label": latest_label, "value": latest_value}] + [
        {"label": study_name_from_path(f, "performance_table_")
         if "performance_table_" in f.name
         else study_name_from_path(f, "vsp_aero_results_alpha_elevator_"),
         "value": str(f)}
        for f in files
    ]

def performance_case_to_vspaero_case(case_value):
    if case_value == "latest":
        return "latest"

    path = Path(case_value)
    case_name = study_name_from_path(path, "performance_table_")
    vspaero_path = OUTPUT_DIR / f"vsp_aero_results_alpha_elevator_{case_name}.csv"

    return str(vspaero_path)

def load_case_df(case_value, latest_path, prefix):
    if case_value == "latest":
        path = latest_path
        study = "latest"
    else:
        path = Path(case_value)
        study = study_name_from_path(path, prefix)

    df = load_csv(path)
    df["study"] = study
    return df


def load_selected_cases(case_values, latest_path, prefix):
    if not case_values:
        case_values = ["latest"]

    return pd.concat(
        [load_case_df(v, latest_path, prefix) for v in case_values],
        ignore_index=True,
    )

def make_performance_line(df, y_col, valid_only=True):
    plot_df = valid_trim_df(df) if valid_only else df.copy()

    fig = px.line(
        plot_df,
        x="V_kmh",
        y=y_col,
        markers=True,
        title=f"{y_col} vs cruise speed",
    )

    fig.update_layout(
        template="plotly_white",
        xaxis_title="Velocity [km/h]",
        yaxis_title=y_col,
        height=600,
    )

    return fig


def make_vspaero_2d(df, x_col, y_col, color_col):
    fig = px.line(
        df,
        x=x_col,
        y=y_col,
        color=color_col,
        markers=True,
        title=f"{y_col} vs {x_col}",
    )

    fig.update_layout(
        template="plotly_white",
        height=600,
    )

    return fig


def make_vspaero_3d(df, x_col, y_col, z_col, mode):
    plot_df = df[[x_col, y_col, z_col]].dropna().copy()

    if mode == "surface":
        pivot = plot_df.pivot_table(
            index=y_col,
            columns=x_col,
            values=z_col,
            aggfunc="mean",
        )

        fig = go.Figure(
            data=[
                go.Surface(
                    x=pivot.columns.to_numpy(),
                    y=pivot.index.to_numpy(),
                    z=pivot.to_numpy(),
                    colorbar=dict(title=z_col),
                )
            ]
        )

        fig.update_layout(
            title=f"Surface: {z_col} over {x_col} and {y_col}",
            scene=dict(
                xaxis_title=x_col,
                yaxis_title=y_col,
                zaxis_title=z_col,
            ),
            template="plotly_white",
            height=750,
        )

    else:
        fig = px.scatter_3d(
            plot_df,
            x=x_col,
            y=y_col,
            z=z_col,
            color=z_col,
            title=f"3D scatter: {z_col} over {x_col} and {y_col}",
        )

        fig.update_layout(
            template="plotly_white",
            height=750,
        )

    return fig


def find_first_existing_column(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None


def case_summary_series(df, case_name):
    valid = valid_trim_df(df)

    # Representative trimmed point
    best_trim = None
    if not valid.empty and "L_D_trim" in valid.columns:
        best_trim = valid.loc[valid["L_D_trim"].idxmax()]

    if valid.empty:
        return pd.Series(name=case_name, dtype="object")

    cl_col = find_first_existing_column(
        valid,
        ["CL_trim", "CL", "CLtot", "CL_total", "CL_required"],
    )
    cd_col = find_first_existing_column(
        valid,
        ["CD_trim", "CD", "CDtot", "CD_total"],
    )

    def row_at_best(metric):
        if metric not in valid.columns:
            return None
        return valid.loc[valid[metric].idxmax()]

    def fmt(row, metric):
        if row is None:
            return "N/A"

        parts = [
            f"{row[metric]:.3g}",
            f"@ {row['V_kmh']:.1f} km/h" if "V_kmh" in row else "",
        ]

        if cl_col:
            parts.append(f"CL={row[cl_col]:.3f}")
        if cd_col:
            parts.append(f"CD={row[cd_col]:.4f}")

        return " | ".join(p for p in parts if p)

    best_range = row_at_best("range_km")
    best_endurance = row_at_best("endurance_min")
    best_ld = row_at_best("L_D_trim")

    return pd.Series(
        {
            "Weight [kg]": valid["mass_kg"].iloc[0] if "mass_kg" in valid else np.nan,
            "Xcg [m]": valid["cg_x_m"].iloc[0] if "cg_x_m" in valid else np.nan,
            "Sref [m²]": valid["sref_m2"].iloc[0] if "sref_m2" in valid else np.nan,

            "Cmα [1/rad]":
                best_trim["Cma_per_rad"]
                if best_trim is not None and "Cma_per_rad" in best_trim
                else np.nan,

            "Best range": fmt(best_range, "range_km"),
            "Best endurance": fmt(best_endurance, "endurance_min"),
            "Best L/D": fmt(best_ld, "L_D_trim"),
        },
        name=case_name,
    )


def make_summary_table(selected_cases):
    cases = []

    if not selected_cases:
        selected_cases = ["latest"]

    for case_value in selected_cases:
        if case_value == "latest":
            df = load_csv(PERFORMANCE_CSV)
            case_name = "latest"
        else:
            path = Path(case_value)
            df = load_csv(path)
            case_name = study_name_from_path(path, "performance_table_")

        cases.append(case_summary_series(df, case_name))

    summary_df = pd.concat(cases, axis=1)

    return html.Table(
        [
            html.Thead(
                html.Tr(
                    [html.Th("Metric")]
                    + [html.Th(col) for col in summary_df.columns]
                )
            ),
            html.Tbody(
                [
                    html.Tr(
                        [html.Td(idx)]
                        + [html.Td(summary_df.loc[idx, col]) for col in summary_df.columns]
                    )
                    for idx in summary_df.index
                ]
            ),
        ],
        style={
            "width": "100%",
            "borderCollapse": "collapse",
            "marginBottom": "24px",
        },
    )


def create_app():
    performance_files = list_performance_comparison_files()
    vspaero_files = list_vspaero_comparison_files(include_latest=False)

    performance_options = [{"label": "latest", "value": "latest"}] + [
    {"label": study_name_from_path(f, "performance_table_"), "value": str(f)}
    for f in performance_files
    ]

    perf_df = load_csv(PERFORMANCE_CSV)
    vsp_df = load_csv(VSPAERO_ALPHA_ELEVATOR_CSV)

    perf_numeric = numeric_columns(perf_df)
    vsp_numeric = numeric_columns(vsp_df)

    perf_default = "range_km" if "range_km" in perf_numeric else perf_numeric[0]

    vsp_x_default = "alpha" if "alpha" in vsp_numeric else vsp_numeric[0]
    vsp_y_default = "CMytot" if "CMytot" in vsp_numeric else vsp_numeric[1]
    vsp_z_default = "CMytot" if "CMytot" in vsp_numeric else vsp_numeric[2]
    vsp_color_default = (
        "delta_e_deg" if "delta_e_deg" in vsp_numeric else vsp_numeric[0]
    )

    app = Dash(__name__)

    app.layout = html.Div(
        [
            html.H1("VSP Batch Result Viewer"),

            html.H2("Global case selection"),
            html.Div(
                [
                    html.Label("Cases"),
                    dcc.Dropdown(
                        id="global-cases",
                        options=performance_options,
                        value=["latest"],
                        multi=True,
                        placeholder="Select cases",
                    ),
                ],
                style={
                    "maxWidth": "620px",
                    "marginBottom": "24px",
                },
            ),

            html.H2("Summary comparison"),
            html.Div(id="summary-comparison-table"),

            html.Hr(),
            html.H2("Trimmed Performance comparison"),
            html.Div(
                [
                    html.Label("Metric"),
                    dcc.Dropdown(
                        id="perf-comparison-y",
                        options=[{"label": c, "value": c} for c in perf_numeric],
                        value="range_km" if "range_km" in perf_numeric else perf_numeric[0],
                    ),
                    dcc.Checklist(
                        id="perf-comparison-valid-only",
                        options=[{"label": "Valid trim only", "value": "valid"}],
                        value=["valid"],
                    ),
                ],
                style={"maxWidth": "620px"},
            ),
            dcc.Graph(id="perf-comparison-graph"),

            html.Hr(),

            html.H2("VSPAERO 2D viewer"),
            html.Div(
                [
                    html.Label("X"),
                    dcc.Dropdown(
                        id="vsp-2d-x",
                        options=[{"label": c, "value": c} for c in vsp_numeric],
                        value=vsp_x_default,
                    ),
                    html.Label("Y"),
                    dcc.Dropdown(
                        id="vsp-2d-y",
                        options=[{"label": c, "value": c} for c in vsp_numeric],
                        value=vsp_y_default,
                    ),
                    html.Label("Color"),
                    dcc.Dropdown(
                        id="vsp-2d-color",
                        options=[{"label": c, "value": c} for c in vsp_numeric],
                        value=vsp_color_default,
                    ),
                ],
                style={
                    "display": "grid",
                    "gridTemplateColumns": "1fr 1fr 1fr",
                    "gap": "12px",
                },
            ),
            dcc.Graph(id="vsp-2d-graph"),

            html.Hr(),
            html.H2("VSPAERO 3D comparison viewer"),
            html.Div(
                [
                    html.Label("X"),
                    dcc.Dropdown(
                        id="vsp-surface-comparison-x",
                        options=[{"label": c, "value": c} for c in vsp_numeric],
                        value=vsp_x_default,
                    ),
                    html.Label("Y"),
                    dcc.Dropdown(
                        id="vsp-surface-comparison-y",
                        options=[{"label": c, "value": c} for c in vsp_numeric],
                        value="delta_e_deg"
                        if "delta_e_deg" in vsp_numeric
                        else vsp_numeric[1],
                    ),
                    html.Label("Z"),
                    dcc.Dropdown(
                        id="vsp-surface-comparison-z",
                        options=[{"label": c, "value": c} for c in vsp_numeric],
                        value=vsp_z_default,
                    ),
                    html.Label("Mode"),
                    dcc.Dropdown(
                        id="vsp-surface-comparison-mode",
                        options=[
                            {"label": "Overlay surfaces", "value": "surface"},
                            {"label": "Overlay 3D scatter", "value": "scatter"},
                        ],
                        value="surface",
                    ),
                ],
                style={
                    "display": "grid",
                    "gridTemplateColumns": "2fr 1fr 1fr 1fr 1fr",
                    "gap": "12px",
                    "alignItems": "end",
                },
            ),
            dcc.Graph(id="vsp-surface-comparison-graph"),
        ],
        style={
            "fontFamily": "Arial, sans-serif",
            "maxWidth": "1200px",
            "margin": "0 auto",
            "padding": "24px",
        },
    )

    @app.callback(
    Output("summary-comparison-table", "children"),
    Input("global-cases", "value"),
    )
    def update_summary_comparison_table(selected_cases):
        return make_summary_table(selected_cases)
    
    @app.callback(
        Output("vsp-2d-graph", "figure"),
        Input("global-cases", "value"),
        Input("vsp-2d-x", "value"),
        Input("vsp-2d-y", "value"),
        Input("vsp-2d-color", "value"),
    )
    def update_vspaero_2d(selected_cases, x_col, y_col, color_col):
        selected_cases = [
            performance_case_to_vspaero_case(case)
            for case in selected_cases
        ]
        df = load_selected_cases(
            selected_cases,
            VSPAERO_ALPHA_ELEVATOR_CSV,
            "vsp_aero_results_alpha_elevator_",
        )

        fig = px.line(
            df,
            x=x_col,
            y=y_col,
            color="study",
            line_dash=color_col if color_col in df.columns else None,
            markers=True,
            title=f"{y_col} vs {x_col}",
        )

        fig.update_layout(template="plotly_white", height=600)
        return fig
    
    @app.callback(
    Output("perf-comparison-graph", "figure"),
    Input("global-cases", "value"),
    Input("perf-comparison-y", "value"),
    Input("perf-comparison-valid-only", "value"),
    )
    def update_performance_comparison(selected_cases, y_col, valid_values):
        valid_only = "valid" in valid_values

        df = load_selected_cases(
            selected_cases,
            PERFORMANCE_CSV,
            "performance_table_",
        )

        if valid_only and "trim_valid" in df.columns:
            df = valid_trim_df(df)

        fig = px.line(
            df,
            x="V_kmh",
            y=y_col,
            color="study",
            markers=True,
            title=f"Performance comparison: {y_col} vs cruise speed",
        )

        fig.update_layout(
            template="plotly_white",
            xaxis_title="Velocity [km/h]",
            yaxis_title=y_col,
            height=650,
        )

        return fig

    @app.callback(
        Output("vsp-surface-comparison-graph", "figure"),
        Input("global-cases", "value"),
        Input("vsp-surface-comparison-x", "value"),
        Input("vsp-surface-comparison-y", "value"),
        Input("vsp-surface-comparison-z", "value"),
        Input("vsp-surface-comparison-mode", "value"),
    )
    def update_vspaero_surface_comparison(selected_cases, x_col, y_col, z_col, mode):
        selected_cases = [
            performance_case_to_vspaero_case(case)
            for case in selected_cases
        ]
        return make_vspaero_surface_comparison(
            selected_cases,
            x_col,
            y_col,
            z_col,
            mode,
        )
    return app

def load_named_csvs(files, prefix):
    dfs = []

    for path in files:
        path = Path(path)
        df = pd.read_csv(path)
        df["study"] = study_name_from_path(path, prefix)
        dfs.append(df)

    if not dfs:
        return pd.DataFrame()

    return pd.concat(dfs, ignore_index=True)


def make_performance_comparison(files, y_col, valid_only=True):
    df = load_named_csvs(files, "performance_table_")

    if df.empty:
        fig = go.Figure()
        fig.update_layout(
            title="Select performance studies to compare",
            template="plotly_white",
            height=600,
        )
        return fig

    if valid_only and "trim_valid" in df.columns:
        df = df[df["trim_valid"].astype(str).str.lower() == "true"].copy()

    fig = px.line(
        df,
        x="V_kmh",
        y=y_col,
        color="study",
        markers=True,
        title=f"Performance comparison: {y_col} vs cruise speed",
    )

    fig.update_layout(
        template="plotly_white",
        xaxis_title="Velocity [km/h]",
        yaxis_title=y_col,
        height=650,
    )

    return fig


def make_vspaero_surface_comparison(files, x_col, y_col, z_col, mode):
    fig = go.Figure()

    if not files:
        files = ["latest"]

    # A few intentionally different palettes make overlapped surfaces easier to separate.
    colorscales = [
        "Viridis",
        "Plasma",
        "Cividis",
        "Turbo",
        "Blues",
        "Reds",
        "Greens",
        "Purples",
    ]

    scatter_symbols = [
        "circle",
        "diamond",
        "square",
        "cross",
        "x",
        "triangle-up",
        "triangle-down",
        "star",
    ]

    added_any_trace = False
    skipped = []

    for i, case_value in enumerate(files):
        if case_value == "latest":
            df = load_csv(VSPAERO_ALPHA_ELEVATOR_CSV)
            study = "latest"
        else:
            path = Path(case_value)
            df = load_csv(path)
            study = study_name_from_path(
                path,
                "vsp_aero_results_alpha_elevator_",
            )

        required = {x_col, y_col, z_col}
        if not required.issubset(df.columns):
            skipped.append(study)
            continue

        plot_df = df[[x_col, y_col, z_col]].dropna().copy()
        if plot_df.empty:
            skipped.append(study)
            continue

        colorscale = colorscales[i % len(colorscales)]

        if mode == "surface":
            pivot = plot_df.pivot_table(
                index=y_col,
                columns=x_col,
                values=z_col,
                aggfunc="mean",
            ).sort_index().sort_index(axis=1)

            fig.add_trace(
                go.Surface(
                    x=pivot.columns.to_numpy(),
                    y=pivot.index.to_numpy(),
                    z=pivot.to_numpy(),
                    name=study,
                    colorscale=colorscale,
                    showscale=(i == 0),
                    colorbar=dict(title=z_col) if i == 0 else None,
                    opacity=0.58,
                    contours=dict(
                        z=dict(
                            show=True,
                            usecolormap=True,
                            project_z=True,
                            width=2,
                        )
                    ),
                    hovertemplate=(
                        f"<b>{study}</b><br>"
                        + f"{x_col}: %{{x}}<br>"
                        + f"{y_col}: %{{y}}<br>"
                        + f"{z_col}: %{{z}}<extra></extra>"
                    ),
                )
            )
        else:
            fig.add_trace(
                go.Scatter3d(
                    x=plot_df[x_col],
                    y=plot_df[y_col],
                    z=plot_df[z_col],
                    mode="markers",
                    name=study,
                    marker=dict(
                        size=5,
                        symbol=scatter_symbols[i % len(scatter_symbols)],
                        opacity=0.82,
                    ),
                    hovertemplate=(
                        f"<b>{study}</b><br>"
                        + f"{x_col}: %{{x}}<br>"
                        + f"{y_col}: %{{y}}<br>"
                        + f"{z_col}: %{{z}}<extra></extra>"
                    ),
                )
            )

        added_any_trace = True

    title = f"VSPAERO 3D comparison: {z_col} over {x_col} and {y_col}"
    if skipped:
        title += f" | skipped missing/empty: {', '.join(skipped)}"

    if not added_any_trace:
        fig.update_layout(
            title="No selected files contain the requested X/Y/Z columns",
            template="plotly_white",
            height=800,
        )
        return fig

    fig.update_layout(
        title=title,
        template="plotly_white",
        height=850,
        legend=dict(title="Study"),
        scene=dict(
            xaxis_title=x_col,
            yaxis_title=y_col,
            zaxis_title=z_col,
        ),
    )
    return fig



if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)