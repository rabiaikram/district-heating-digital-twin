"""Streamlit version of the District Heating Digital Twin PoC dashboard."""

import plotly.express as px
import streamlit as st

from data_generator import generate_telemetry
from model_engine import calculate_thermodynamics

st.set_page_config(
    page_title="District Heating Digital Twin",
    layout="wide",
)

st.markdown(
    """
    <style>
      .stApp { background: #0e1117; color: #e6edf5; }
      [data-testid="stSidebar"] { background: #111923; border-right: 1px solid #233242; }
      [data-testid="stMetric"] {
        background: linear-gradient(145deg, #151f2a, #111923);
        border: 1px solid #263646; border-radius: 12px; padding: 18px 20px;
      }
      [data-testid="stMetricLabel"] { color: #9aabba; }
      [data-testid="stMetricValue"] { color: #e8f2f8; }
      h1, h2, h3 { color: #e8f2f8; }
      .block-container { padding-top: 2rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_dashboard_data(days: int):
    telemetry = generate_telemetry(days=days)
    return calculate_thermodynamics(telemetry)


with st.sidebar:
    st.markdown("### Network controls")
    historical_days = st.slider(
        "Historical data range",
        min_value=7,
        max_value=60,
        value=30,
        step=1,
        format="%d days",
    )
    st.caption("Hourly simulated telemetry · steady-state model")

df = load_dashboard_data(historical_days)
anomalies = int(df["Anomaly_Flag"].sum())

st.title("District Heating Digital Twin")
st.caption(
    f"Thermo-hydraulic network performance · last {historical_days} days"
)

metric_columns = st.columns(4)
metric_columns[0].metric(
    "Avg Supply Temp",
    f"{df['Supply_Temp_C'].mean():.1f} °C",
)
metric_columns[1].metric(
    "Avg Return Temp",
    f"{df['Predicted_Return_Temp_C'].mean():.1f} °C",
)
metric_columns[2].metric(
    "Peak Heat Delivered",
    f"{df['Heat_Delivered_kW'].max():,.0f} kW",
)
metric_columns[3].metric(
    "Anomalies Detected",
    f"{anomalies:,}",
    delta=f"{anomalies:,} flagged",
    delta_color="inverse" if anomalies > 0 else "normal",
)

temperature_chart = px.line(
    df,
    x="Timestamp",
    y=["Supply_Temp_C", "Predicted_Return_Temp_C"],
    color_discrete_sequence=["#2dd4bf", "#60a5fa"],
    labels={
        "value": "Temperature (°C)",
        "Timestamp": "Time",
        "variable": "Series",
    },
    template="plotly_dark",
)
temperature_chart.update_layout(
    title="Supply & return temperature",
    paper_bgcolor="#0e1117",
    plot_bgcolor="#0e1117",
    legend_title_text="",
    margin=dict(l=12, r=12, t=48, b=12),
)
temperature_chart.update_traces(line=dict(width=2))

heat_chart = px.area(
    df,
    x="Timestamp",
    y="Heat_Delivered_kW",
    color_discrete_sequence=["#38bdf8"],
    labels={
        "Heat_Delivered_kW": "Heat delivered (kW)",
        "Timestamp": "Time",
    },
    template="plotly_dark",
)
heat_chart.update_layout(
    title="Heat delivered over time",
    paper_bgcolor="#0e1117",
    plot_bgcolor="#0e1117",
    margin=dict(l=12, r=12, t=48, b=12),
)
heat_chart.update_traces(line=dict(width=2), fillcolor="rgba(56, 189, 248, 0.22)")

left_chart, right_chart = st.columns(2)
with left_chart:
    st.plotly_chart(temperature_chart, use_container_width=True)
with right_chart:
    st.plotly_chart(heat_chart, use_container_width=True)

with st.expander("View raw telemetry and model output"):
    st.dataframe(df, use_container_width=True, hide_index=True)
