from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def load_performance_table(csv_path):
    df = pd.read_csv(csv_path)
    if "trim_valid" in df.columns:
        df["trim_valid"] = df["trim_valid"].astype(bool)
    return df


def filter_valid_trim(df):
    return df[df["trim_valid"] == True].copy()


def plot_range(df):
    valid = filter_valid_trim(df)

    fig = px.line(
        valid,
        x="V_kmh",
        y="range_km",
        markers=True,
        title="Predicted range vs cruise speed",
    )
    fig.update_layout(
        xaxis_title="Velocity [km/h]",
        yaxis_title="Range [km]",
        template="plotly_white",
    )
    return fig


def plot_endurance(df):
    valid = filter_valid_trim(df)

    fig = px.line(
        valid,
        x="V_kmh",
        y="endurance_min",
        markers=True,
        title="Predicted endurance vs cruise speed",
    )
    fig.update_layout(
        xaxis_title="Velocity [km/h]",
        yaxis_title="Endurance [min]",
        template="plotly_white",
    )
    return fig


def plot_trim_elevator(df):
    valid = filter_valid_trim(df)

    fig = px.line(
        valid,
        x="V_kmh",
        y="delta_e_trim_deg",
        markers=True,
        title="Trim elevator deflection vs cruise speed",
    )
    fig.update_layout(
        xaxis_title="Velocity [km/h]",
        yaxis_title="Elevator trim [deg]",
        template="plotly_white",
    )
    return fig


def plot_ld(df):
    valid = filter_valid_trim(df)

    fig = px.line(
        valid,
        x="V_kmh",
        y="L_D_trim",
        markers=True,
        title="Trimmed L/D vs cruise speed",
    )
    fig.update_layout(
        xaxis_title="Velocity [km/h]",
        yaxis_title="Trimmed L/D",
        template="plotly_white",
    )
    return fig


def plot_power(df):
    valid = filter_valid_trim(df)

    fig = px.line(
        valid,
        x="V_kmh",
        y=["shaft_power_W", "electrical_power_W", "total_power_W"],
        markers=True,
        title="Power required vs cruise speed",
    )
    fig.update_layout(
        xaxis_title="Velocity [km/h]",
        yaxis_title="Power [W]",
        template="plotly_white",
    )
    return fig


def plot_all(csv_path="output/performance_table.csv"):
    df = load_performance_table(csv_path)

    plot_range(df).show()
    plot_endurance(df).show()
    plot_trim_elevator(df).show()
    plot_ld(df).show()
    plot_power(df).show()