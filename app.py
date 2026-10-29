import plotly.graph_objects as go
import streamlit as st

from data_generator import generate_telemetry

st.set_page_config(
    page_title="District Heating Digital Twin",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def html(markup: str) -> None:
    """Render HTML through st.markdown (strips indentation so Markdown never treats it as code)."""
    cleaned = "\n".join(line.strip() for line in markup.splitlines() if line.strip())
    st.markdown(cleaned, unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# GLOBAL CSS (injected first)
# ----------------------------------------------------------------------------
html(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

.stApp { background: #0b0e14; font-family: 'Inter', sans-serif; }
header, footer, #MainMenu { display: none; }
[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"] { display: none; }
.block-container, [data-testid="stMainBlockContainer"] {
    padding: 1.5rem 2rem; max-width: 100%;
}
[data-testid="stVerticalBlock"] { gap: 1rem; }

/* ---------- Top bar ---------- */
.st-key-topbar {
    background: #111622;
    border-bottom: 1px solid #1e2638;
    margin: -1.5rem -2rem 0 -2rem;
    padding: 0.85rem 2rem;
    width: calc(100% + 4rem);
}
.brand { display: flex; align-items: center; gap: 14px; }
.brand-icon {
    width: 44px; height: 44px; border-radius: 12px;
    border: 1px solid rgba(0,242,254,0.35); background: rgba(0,242,254,0.08);
    display: flex; align-items: center; justify-content: center; color: #00f2fe;
}
.brand-name { color: #00f2fe; font-weight: 700; font-size: 16px; letter-spacing: 0.2px; line-height: 1.1; }
.brand-sub { color: #64748b; font-size: 11px; letter-spacing: 2px; margin-top: 3px; }
.brand-divider { width: 1px; height: 34px; background: #1e2638; margin: 0 6px 0 10px; }
.brand-district { color: #94a3b8; font-size: 14px; }
.model-pill {
    display: inline-flex; align-items: center; gap: 8px;
    background: rgba(16,185,129,0.12); color: #10b981;
    border: 1px solid rgba(16,185,129,0.35);
    padding: 8px 16px; border-radius: 999px; font-size: 13px; font-weight: 500; white-space: nowrap;
}
.model-pill .dot { width: 8px; height: 8px; border-radius: 50%; background: #10b981; box-shadow: 0 0 8px #10b981; }

/* ---------- Buttons ---------- */
.stButton > button, .stDownloadButton > button {
    background: transparent; color: #e2e8f0;
    border: 1px solid #1e2638; border-radius: 12px;
    height: 46px; padding: 0 22px; font-weight: 500; font-size: 15px; width: 100%;
    font-family: 'Inter', sans-serif;
}
.stButton > button:hover, .stDownloadButton > button:hover {
    background: rgba(0,242,254,0.06); border-color: #00f2fe; color: #00f2fe;
}
.stButton > button:focus, .stDownloadButton > button:focus { box-shadow: none; outline: none; }

/* ---------- Section header ---------- */
.eyebrow { display: flex; align-items: center; gap: 12px; color: #00f2fe; font-size: 10px; font-weight: 700; letter-spacing: 2.2px; margin-top: 26px; }
.eyebrow .line { width: 24px; height: 1px; background: #00f2fe; }
.page-title { color: #ffffff; font-size: 24px; font-weight: 700; margin: 14px 0 4px 0; letter-spacing: -0.5px; line-height: 1.15; }
.page-sub { color: #94a3b8; font-size: 14px; }
.latest-reading { display: flex; align-items: center; justify-content: flex-end; gap: 10px; color: #94a3b8; font-size: 13px; height: 46px; white-space: nowrap; }
.latest-reading b { color: #e2e8f0; font-family: 'JetBrains Mono', monospace; font-weight: 600; }

/* ---------- Slider row ---------- */
.st-key-sliderrow {
    background: #111622; border: 1px solid #1e2638; border-radius: 14px;
    padding: 14px 24px;
}
.st-key-sliderrow [data-testid="stHorizontalBlock"] { align-items: center; }
.slider-icon {
    width: 40px; height: 40px; border-radius: 10px; background: #1a2133; border: 1px solid #1e2638;
    display: flex; align-items: center; justify-content: center; color: #94a3b8; flex: 0 0 40px;
}
.slider-left { display: flex; align-items: center; gap: 12px; }
.slider-title { color: #e2e8f0; font-size: 13px; font-weight: 600; line-height: 1.2; }
.slider-sub { color: #64748b; font-size: 11px; }
.days-text { color: #e2e8f0; font-family: 'JetBrains Mono', monospace; font-weight: 600; font-size: 15px; }
.res-text { color: #64748b; font-size: 12px; text-align: right; display: flex; align-items: center; justify-content: flex-end; gap: 8px; }
[data-testid="stSliderTickBarMin"], [data-testid="stSliderTickBarMax"],
[data-testid="stSliderThumbValue"] { display: none; }
[data-testid="stSlider"] { padding-top: 0; }
[data-testid="stSlider"] [role="slider"] { background: #00f2fe; box-shadow: 0 0 0 4px rgba(0,242,254,0.2); }

/* ---------- KPI cards ---------- */
.kpi-card {
    position: relative; background: #111622; border: 1px solid #1e2638; border-radius: 14px;
    padding: 24px 24px 20px 24px; height: 186px; overflow: hidden;
}
.kpi-card::before { content: ''; position: absolute; top: 0; left: 24px; width: 100px; height: 2px; background: #00f2fe; }
.kpi-card.alert::before { background: #f43f5e; }
.kpi-label { color: #94a3b8; font-size: 11px; font-weight: 600; letter-spacing: 1.8px; }
.kpi-icon {
    position: absolute; top: 24px; right: 22px; width: 42px; height: 42px; border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    background: rgba(0,242,254,0.10); border: 1px solid rgba(0,242,254,0.30); color: #00f2fe;
}
.kpi-card.alert .kpi-icon { background: rgba(244,63,94,0.10); border-color: rgba(244,63,94,0.35); color: #f43f5e; }
.kpi-value { margin-top: 30px; color: #e2e8f0; font-family: 'JetBrains Mono', monospace; font-size: 40px; font-weight: 500; letter-spacing: -1px; line-height: 1; }
.kpi-value .unit { font-family: 'Inter', sans-serif; font-size: 15px; color: #64748b; margin-left: 6px; letter-spacing: 0; }
.kpi-card.alert .kpi-value, .kpi-card.alert .kpi-value .unit { color: #f43f5e; }
.kpi-card.alert .kpi-value .unit { opacity: 0.8; }
.kpi-foot { margin-top: 22px; display: flex; align-items: center; gap: 8px; color: #64748b; font-size: 13px; }
.kpi-card.alert .kpi-foot { color: #f43f5e; }

/* ---------- Chart cards ---------- */
.st-key-chart1, .st-key-chart2 {
    background: #111622; border: 1px solid #1e2638; border-radius: 14px; padding: 24px 24px 18px 24px;
}
.chart-head { display: flex; justify-content: space-between; align-items: flex-start; }
.chart-eyebrow { color: #94a3b8; font-size: 11px; font-weight: 600; letter-spacing: 1.8px; }
.chart-title { color: #e2e8f0; font-size: 16px; font-weight: 600; margin-top: 8px; letter-spacing: -0.2px; }
.chart-pill {
    background: rgba(0,242,254,0.08); border: 1px solid rgba(0,242,254,0.30); color: #7dd3fc;
    font-size: 11px; padding: 6px 12px; border-radius: 999px; white-space: nowrap;
}
.chart-footer {
    background: #111622; border-top: 1px solid #1e2638; margin-top: 6px; padding-top: 14px;
    color: #64748b; font-size: 12px; display: flex; align-items: center; gap: 10px;
}
.chart-footer .ico { color: #00f2fe; font-size: 13px; }

/* ---------- Expander ---------- */
[data-testid="stExpander"] {
    background: #111622; border: 1px solid #1e2638; border-radius: 14px; overflow: hidden;
}
[data-testid="stExpander"] details { border: none; }
[data-testid="stExpander"] details summary { padding: 20px 24px; color: #e2e8f0; font-weight: 600; font-size: 15px; }
[data-testid="stExpander"] details summary:hover { color: #00f2fe; }
[data-testid="stExpander"] details[open] summary { border-bottom: 1px solid #1e2638; }

/* ---------- Custom table ---------- */
.custom-table-wrapper { max-height: 480px; overflow-y: auto; border-radius: 10px; }
.custom-table-wrapper::-webkit-scrollbar { width: 6px; }
.custom-table-wrapper::-webkit-scrollbar-thumb { background: #2a3550; border-radius: 6px; }
.custom-table { width: 100%; border-collapse: collapse; text-align: left; background: #111622; font-size: 13px; color: #e2e8f0; border: none; }
.custom-table thead tr { text-align: left !important; }
.custom-table th {
    position: sticky; top: 0; background: #111622; z-index: 2;
    color: #94a3b8; font-size: 11px; font-weight: 600; letter-spacing: 1.6px;
    text-align: left !important; padding: 16px 24px; border-bottom: 1px solid #1e2638;
}
.custom-table td {
    text-align: left; padding: 15px 24px; border-bottom: 1px solid #1e2638;
    font-family: 'JetBrains Mono', monospace; font-size: 13px; background: #111622;
}
.custom-table td:last-child { font-family: 'Inter', sans-serif; font-size: 12px; }
.custom-table tbody tr:hover td { background: #151b2b; }
.t-supply { color: #2dd4bf; font-weight: 500; }
.t-return { color: #fb7185; font-weight: 500; }

/* ---------- Footer ---------- */
.page-footer {
    display: flex; justify-content: space-between; margin-top: 18px; padding-top: 18px;
    border-top: 1px solid #1e2638; color: #475569; font-size: 12px;
}
.page-footer .sep { margin: 0 8px; color: #334155; }
</style>
"""
)

# ----------------------------------------------------------------------------
# SVG icons
# ----------------------------------------------------------------------------
def svg(path: str, size: int = 20, extra: str = "") -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" {extra}>'
        f"{path}</svg>"
    )


ICON_FLAME = svg('<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.07-2.14-.22-4.05 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.15.43-2.3 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>', 22)
ICON_THERMO = svg('<path d="M14 4v10.54a4 4 0 1 1-4 0V4a2 2 0 0 1 4 0Z"/>', 20)
ICON_WAVES = svg('<path d="M2 6c.6.5 1.2 1 2.5 1C7 7 7 5 9.5 5c2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/><path d="M2 12c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/><path d="M2 18c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/>', 20)
ICON_BOLT = svg('<path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z"/>', 20)
ICON_ALERT = svg('<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>', 20)
ICON_FILTER = svg('<path d="M4 21v-7"/><path d="M4 10V3"/><path d="M12 21v-9"/><path d="M12 8V3"/><path d="M20 21v-5"/><path d="M20 12V3"/><path d="M1 14h6"/><path d="M9 8h6"/><path d="M17 16h6"/>', 18)
ICON_PULSE = svg('<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>', 15)
ICON_WARN_SM = svg('<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>', 15)
ICON_CLOCK = svg('<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>', 16)

# ----------------------------------------------------------------------------
# State
# ----------------------------------------------------------------------------
if "seed" not in st.session_state:
    st.session_state.seed = 42


def regenerate() -> None:
    st.session_state.seed += 1


days = int(st.session_state.get("days", 27))
df = generate_telemetry(days=days, seed=st.session_state.seed)

# ----------------------------------------------------------------------------
# 1. TOP BAR
# ----------------------------------------------------------------------------
with st.container(key="topbar"):
    c_left, c_pill, c_btn = st.columns([6, 1.3, 2], vertical_alignment="center")
    with c_left:
        html(
            f"""
<div class="brand">
<div class="brand-icon">{ICON_FLAME}</div>
<div>
<div class="brand-name" style="color:#ffffff;">HEAT / <span style="color:#00f2fe;">TWIN</span></div>
<div class="brand-sub">NETWORK OPERATIONS</div>
</div>
<div class="brand-divider"></div>
<div class="brand-district">North Quay District · Loop 01</div>
</div>
"""
        )
    with c_pill:
        html('<div style="display:flex;justify-content:flex-end;"><span class="model-pill"><span class="dot"></span>Model active</span></div>')
    with c_btn:
        st.button("↻  Regenerate telemetry", on_click=regenerate, key="regen")

# ----------------------------------------------------------------------------
# 2. SECTION HEADER (+ latest reading / export)
# ----------------------------------------------------------------------------
latest_ts = df["TIMESTAMP"].iloc[-1].strftime("%d %b, %H:%M")

h_left, h_mid, h_right = st.columns([6, 2.6, 1.4], vertical_alignment="bottom")
with h_left:
    html(
        """
<div class="eyebrow"><span class="line"></span>OPERATIONS INTELLIGENCE</div>
<div class="page-title">Network overview</div>
<div class="page-sub">Live thermal performance and modelled return conditions.</div>
"""
    )
with h_mid:
    html(f'<div class="latest-reading">{ICON_CLOCK}<span>Latest reading</span><b>{latest_ts}</b></div>')
with h_right:
    export_df = df.copy()
    export_df["CONDITION"] = export_df["RETURN °C"].apply(lambda v: "High return" if v > 65.0 else "Normal")
    st.download_button(
        "↓  Export CSV",
        data=export_df.to_csv(index=False).encode("utf-8"),
        file_name="north_quay_loop01_telemetry.csv",
        mime="text/csv",
        key="export",
    )

# ----------------------------------------------------------------------------
# 3. SLIDER ROW  st.columns([1, 6, 1, 2])
# ----------------------------------------------------------------------------
with st.container(key="sliderrow"):
    s1, s2, s3, s4 = st.columns([1, 6, 1, 2], vertical_alignment="center")
    with s1:
        html(
            f"""
<div class="slider-left">
<div class="slider-icon">{ICON_FILTER}</div>
<div><div class="slider-title">Historical window</div><div class="slider-sub">Hourly modelled telemetry</div></div>
</div>
"""
        )
    with s2:
        st.slider("Historical window", min_value=7, max_value=60, value=27, key="days", label_visibility="collapsed")
    with s3:
        html(f'<div class="days-text">{days} days</div>')
    with s4:
        html('<div class="res-text"><span style="color:#00f2fe;">≡</span> Hourly resolution</div>')

# ----------------------------------------------------------------------------
# 4. KPI CARDS
# ----------------------------------------------------------------------------
avg_supply = df["SUPPLY °C"].mean()
avg_return = df["RETURN °C"].mean()
peak_heat = df["HEAT KW"].max()
anomaly_count = int((df["RETURN °C"] > 65.0).sum())


def kpi(label: str, value: str, unit: str, foot: str, icon: str, foot_icon: str, alert: bool = False) -> str:
    cls = "kpi-card alert" if alert else "kpi-card"
    return f"""
<div class="{cls}">
<div class="kpi-label">{label}</div>
<div class="kpi-icon">{icon}</div>
<div class="kpi-value">{value}<span class="unit">{unit}</span></div>
<div class="kpi-foot">{foot_icon}<span>{foot}</span></div>
</div>
"""


k1, k2, k3, k4 = st.columns(4)
with k1:
    html(kpi("AVERAGE SUPPLY TEMPERATURE", f"{avg_supply:.1f}", "°C", "Across selected window", ICON_THERMO, ICON_PULSE))
with k2:
    html(kpi("AVERAGE RETURN TEMPERATURE", f"{avg_return:.1f}", "°C", "Predicted from flow and ambient", ICON_WAVES, ICON_PULSE))
with k3:
    html(kpi("PEAK HEAT DELIVERED", f"{peak_heat:.0f}", "kW", "Maximum hourly delivery", ICON_BOLT, ICON_PULSE))
with k4:
    html(kpi("ANOMALY COUNT", f"{anomaly_count}", "events", "Return temperature above 65 °C", ICON_ALERT, ICON_WARN_SM, alert=True))

# ----------------------------------------------------------------------------
# 5. CHARTS
# ----------------------------------------------------------------------------
def style_fig(fig: go.Figure, y_range, y_ticks, y_suffix: str = "") -> go.Figure:
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#111622",
        plot_bgcolor="#111622",
        margin=dict(l=0, r=0, t=30, b=0),
        height=360,
        font=dict(family="JetBrains Mono, monospace", size=10, color="#64748b"),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1.0, font=dict(size=11, color="#94a3b8", family="Inter, sans-serif")),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, showline=False, tickformat="%d %b", nticks=13, tickfont=dict(color="#64748b"))
    fig.update_yaxes(
        showgrid=False, zeroline=False, showline=False,
        range=y_range, tickvals=y_ticks, ticksuffix=y_suffix, automargin=True, tickfont=dict(color="#64748b"),
    )
    return fig


plot_config = {"displayModeBar": False}
col_a, col_b = st.columns(2)

# ---- Chart 1: thermal profile ----
with col_a:
    with st.container(key="chart1"):
        html(
            """
<div class="chart-head"><div>
<div class="chart-eyebrow">THERMAL PROFILE</div>
<div class="chart-title">Supply &amp; predicted return</div>
</div></div>
"""
        )
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(x=df["TIMESTAMP"], y=df["SUPPLY °C"], mode="lines", name="Supply", line=dict(color="#00f2fe", width=1.6)))
        fig1.add_trace(go.Scatter(x=df["TIMESTAMP"], y=df["RETURN °C"], mode="lines", name="Predicted return", line=dict(color="#3b82f6", width=1.6)))
        fig1.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name="Above 65 °C", marker=dict(color="#f43f5e", size=8)))
        style_fig(fig1, [66, 92], [66, 73, 80, 92], "°")
        st.plotly_chart(fig1, config=plot_config)
        # 6. Footer below chart 1
        html(
            '<div class="chart-footer"><span class="ico" style="color:#00f2fe;">↘</span>'
            "<span>Return temperature is estimated from supply, ambient conditions and measured flow.</span></div>"
        )

# ---- Chart 2: load profile ----
with col_b:
    with st.container(key="chart2"):
        html(
            """
<div class="chart-head">
<div>
<div class="chart-eyebrow">LOAD PROFILE</div>
<div class="chart-title">Delivered heat</div>
</div>
<div class="chart-pill">Hourly · kW</div>
</div>
"""
        )
        fig2 = go.Figure()
        fig2.add_trace(
            go.Scatter(
                x=df["TIMESTAMP"], y=df["HEAT KW"], mode="lines", name="Delivered heat",
                line=dict(color="#00e5ff", width=1.4), fill="tozeroy", fillcolor="rgba(0,229,255,0.10)",
            )
        )
        style_fig(fig2, [0, 60], [0, 15, 30, 45, 60], " kW")
        fig2.update_layout(showlegend=False)
        st.plotly_chart(fig2, config=plot_config)
        # 7. Footer below chart 2
        html(
            '<div class="chart-footer"><span class="ico" style="color:#00f2fe;">◷</span>'
            "<span>Calculated from flow rate and supply-to-return temperature difference.</span></div>"
        )

# ----------------------------------------------------------------------------
# 8. RAW TELEMETRY (custom HTML table, no st.dataframe)
# ----------------------------------------------------------------------------
table_df = df.sort_values("TIMESTAMP", ascending=False).copy()
table_df["TIMESTAMP"] = table_df["TIMESTAMP"].dt.strftime("%d %b, %H:%M")
table_df["SUPPLY °C"] = table_df["SUPPLY °C"].map(lambda v: f'<span class="t-supply">{v:.1f}</span>')
table_df["RETURN °C"] = table_df["RETURN °C"].map(lambda v: f'<span class="{"t-return" if v > 65.0 else "t-supply"}">{v:.1f}</span>')
table_df["HEAT KW"] = table_df["HEAT KW"].map(lambda v: f"{v:.0f}")
table_df["AMBIENT °C"] = table_df["AMBIENT °C"].map(lambda v: f"{v:.1f}")
table_df["FLOW KG/S"] = table_df["FLOW KG/S"].map(lambda v: f"{v:.2f}")

table_html = table_df.to_html(escape=False, index=False, classes="custom-table", border=0)
table_html = "".join(line.strip() for line in table_html.splitlines())

with st.expander(f"Raw telemetry  ·  Hourly readings · newest first · {len(df)} records", expanded=False):
    st.markdown(f'<div class="custom-table-wrapper">{table_html}</div>', unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# 9. PAGE FOOTER
# ----------------------------------------------------------------------------
html(
    """
<div class="page-footer">
<div>District heating digital twin<span class="sep">/</span>Proof of concept</div>
<div>↗ &nbsp;Modelled hourly telemetry · all values calculated in-browser</div>
</div>
"""
)
