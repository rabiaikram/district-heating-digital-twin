import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np

# 1. Page Configuration
st.set_page_config(
    page_title="HEAT / TWIN — District Heating Digital Twin",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. Inject Replit Custom Dark CSS
st.markdown("""
<style>
    /* Dark Theme Core */
    .stApp {
        background-color: #0b0e14 !important;
        color: #e2e8f0 !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Hide Default Headers & Footers */
    header, footer, #MainMenu {visibility: hidden;}
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
        max-width: 95% !important;
    }
    
    /* Top Header Bar */
    .top-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: #111622;
        padding: 12px 20px;
        border-radius: 10px;
        border: 1px solid #1e2638;
        margin-bottom: 20px;
    }
    .brand-title {
        font-size: 14px;
        font-weight: 700;
        letter-spacing: 1.5px;
        color: #00f2fe;
    }
    .brand-subtitle {
        font-size: 11px;
        color: #64748b;
        margin-left: 10px;
    }
    .status-pill {
        background: rgba(16, 185, 129, 0.15);
        color: #10b981;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
    }
    
    /* KPI Card Containers */
    .kpi-card {
        background: #111622;
        border: 1px solid #1e2638;
        border-radius: 12px;
        padding: 18px 20px;
        height: 100%;
        box-shadow: 0 4px 20px rgba(0,0,0,0.2);
    }
    .kpi-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 1px;
        color: #64748b;
        text-transform: uppercase;
    }
    .kpi-value {
        font-size: 32px;
        font-weight: 700;
        color: #f8fafc;
        margin: 10px 0 4px 0;
    }
    .kpi-unit {
        font-size: 16px;
        color: #94a3b8;
        font-weight: 400;
    }
    .kpi-subtext {
        font-size: 11px;
        color: #64748b;
    }
    .kpi-subtext-alert {
        font-size: 11px;
        color: #f43f5e;
    }
    
    /* Section Headers */
    .section-tag {
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 1.5px;
        color: #00f2fe;
        text-transform: uppercase;
        margin-bottom: 2px;
    }
    .section-title {
        font-size: 26px;
        font-weight: 700;
        color: #f8fafc;
        margin-bottom: 4px;
    }
    .section-desc {
        font-size: 13px;
        color: #64748b;
        margin-bottom: 20px;
    }
    
    /* Slider Widget Container */
    .slider-box {
        background: #111622;
        border: 1px solid #1e2638;
        border-radius: 10px;
        padding: 12px 20px;
        margin-bottom: 25px;
    }
</style>
""", unsafe_allow_html=True)

# 3. Data Engine
@st.cache_data
def get_data(days=30):
    dates = pd.date_range(end=pd.Timestamp.now(), periods=days*24, freq='h')
    np.random.seed(42)
    
    supply = np.random.normal(80.0, 1.8, len(dates))
    flow = np.random.normal(5.0, 0.4, len(dates))
    ambient = np.random.normal(10.0, 4.0, len(dates))
    
    # Thermodynamic Calculation (Kusuda / Cengel model)
    L, Cp, U = 1000, 4184, 0.5
    exp_factor = np.exp(-(U * L) / (flow * Cp))
    predicted_return = ambient + (supply - ambient) * exp_factor
    
    heat_kw = flow * Cp * (supply - predicted_return) / 1000
    anomalies = predicted_return > 65.0
    
    return pd.DataFrame({
        'Timestamp': dates,
        'Supply_Temp_C': supply,
        'Predicted_Return_Temp_C': predicted_return,
        'Flow_Rate_kg_s': flow,
        'Ambient_Temp_C': ambient,
        'Heat_Delivered_kW': heat_kw,
        'Anomaly_Flag': anomalies
    })

# 4. Top Navigation Bar
st.markdown("""
<div class="top-bar">
    <div>
        <span class="brand-title">HEAT / TWIN</span>
        <span class="brand-subtitle">NETWORK OPERATIONS — North Quay District · Loop 01</span>
    </div>
    <div>
        <span class="status-pill">● Model active</span>
    </div>
</div>
""", unsafe_allow_html=True)

# 5. Header Section
st.markdown('<div class="section-tag">OPERATIONS INTELLIGENCE</div>', unsafe_allow_html=True)
st.markdown('<div class="section-title">Network overview</div>', unsafe_allow_html=True)
st.markdown('<div class="section-desc">Live thermal performance and modelled return conditions.</div>', unsafe_allow_html=True)

# 6. Interactive Window Control
with st.container():
    st.markdown('<div class="slider-box">', unsafe_allow_html=True)
    c_sl, c_txt = st.columns([4, 1])
    with c_sl:
        days_sim = st.slider("Historical window (Hourly modelled telemetry)", 7, 60, 30)
    with c_txt:
        st.markdown(f"<p style='color:#00f2fe; font-size:18px; font-weight:700; margin-top:20px;'>{days_sim} days</p>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

df = get_data(days_sim)

# 7. KPI Metrics Row
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-header">AVERAGE SUPPLY TEMPERATURE <span>🌡️</span></div>
        <div class="kpi-value">{df['Supply_Temp_C'].mean():.1f} <span class="kpi-unit">°C</span></div>
        <div class="kpi-subtext">⚡ Across selected window</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-header">AVERAGE RETURN TEMPERATURE <span>🌊</span></div>
        <div class="kpi-value">{df['Predicted_Return_Temp_C'].mean():.1f} <span class="kpi-unit">°C</span></div>
        <div class="kpi-subtext">⚡ Predicted from flow and ambient</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-header">PEAK HEAT DELIVERED <span>⚡</span></div>
        <div class="kpi-value">{df['Heat_Delivered_kW'].max():.0f} <span class="kpi-unit">kW</span></div>
        <div class="kpi-subtext">⚡ Maximum hourly delivery</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    anom_count = df['Anomaly_Flag'].sum()
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-header">ANOMALY COUNT <span>⚠️</span></div>
        <div class="kpi-value" style="color:#f43f5e;">{anom_count} <span class="kpi-unit" style="color:#f43f5e;">events</span></div>
        <div class="kpi-subtext-alert">⚠️ Return temperature above 65 °C</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# 8. Charts Row
ch_col1, ch_col2 = st.columns(2)

# Thermal Profile Chart
with ch_col1:
    st.markdown('<div class="section-tag">THERMAL PROFILE</div>', unsafe_allow_html=True)
    st.markdown('<div style="color:#f8fafc; font-size:16px; font-weight:700; margin-bottom:10px;">Supply & predicted return</div>', unsafe_allow_html=True)
    
    fig_thermal = go.Figure()
    fig_thermal.add_trace(go.Scatter(
        x=df['Timestamp'], y=df['Supply_Temp_C'],
        name='Supply', line=dict(color='#00f2fe', width=1.5)
    ))
    fig_thermal.add_trace(go.Scatter(
        x=df['Timestamp'], y=df['Predicted_Return_Temp_C'],
        name='Predicted return', line=dict(color='#3b82f6', width=1.5)
    ))
    fig_thermal.update_layout(
        template="plotly_dark",
        paper_bgcolor='#111622',
        plot_bgcolor='#111622',
        margin=dict(l=10, r=10, t=10, b=10),
        height=280,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(showgrid=False, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor='#1e2638', zeroline=False)
    )
    st.plotly_chart(fig_thermal, use_container_width=True)

# Load Profile Chart
with ch_col2:
    st.markdown('<div class="section-tag">LOAD PROFILE</div>', unsafe_allow_html=True)
    st.markdown('<div style="color:#f8fafc; font-size:16px; font-weight:700; margin-bottom:10px;">Delivered heat</div>', unsafe_allow_html=True)
    
    fig_load = go.Figure()
    fig_load.add_trace(go.Scatter(
        x=df['Timestamp'], y=df['Heat_Delivered_kW'],
        name='Delivered heat', fill='tozeroy',
        line=dict(color='#00e5ff', width=1.5),
        fillcolor='rgba(0, 229, 255, 0.1)'
    ))
    fig_load.update_layout(
        template="plotly_dark",
        paper_bgcolor='#111622',
        plot_bgcolor='#111622',
        margin=dict(l=10, r=10, t=10, b=10),
        height=280,
        showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor='#1e2638', zeroline=False)
    )
    st.plotly_chart(fig_load, use_container_width=True)

# 9. Raw Data Table
with st.expander("Raw telemetry — Hourly readings"):
    st.dataframe(df, use_container_width=True)
