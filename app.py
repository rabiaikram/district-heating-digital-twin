"""
app.py
Heat Twin: district heating digital shadow dashboard (SYNTHETIC DEMO).

Run:  streamlit run app.py
Needs: model_engine.py and data_generator.py in the same folder.

The data is simulated. Faults, sensor problems and data gaps are injected on
purpose so that detection can be demonstrated. Gaps and spikes are flagged and
excluded from statistics, never filled in.
"""

import re
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data_generator import generate_telemetry
from model_engine import (
    CRIT_K,
    DWELLINGS,
    FROZEN_HOURS,
    MIN_HOURS,
    WARN_K,
    find_events,
    summarise,
)

st.set_page_config(page_title="Heat Twin · North Quay", page_icon="🔥", layout="wide")

# --------------------------------------------------------------------------
# Palette
# --------------------------------------------------------------------------
BG = "#0a1020"
PANEL = "#0f1a2e"
EDGE = "#1c2a44"
TEXT = "#e6edf7"
MUTED = "#8da2c0"
CYAN = "#22d3ee"
BLUE = "#3b82f6"
RED = "#f43f5e"
AMBER = "#f59e0b"
GREEN = "#10b981"
GREY = "#94a3b8"

CSS = f"""
<style>
.stApp {{ background: {BG}; color: {TEXT}; }}
.block-container {{ max-width: 1400px; padding-top: 1.6rem; padding-bottom: 3rem; }}
#MainMenu, footer {{ visibility: hidden; }}
h1, h2, h3, h4, p, label, span, div {{ font-family: "Segoe UI", system-ui, -apple-system, sans-serif; }}

.brand {{ display:flex; align-items:center; gap:14px; }}
.brand-mark {{ width:44px; height:44px; border-radius:10px; background:{PANEL};
  border:1px solid {EDGE}; display:flex; align-items:center; justify-content:center; font-size:22px; }}
.brand-name {{ font-size:20px; font-weight:700; letter-spacing:0.02em; color:{TEXT}; }}
.brand-name b {{ color:{CYAN}; }}
.brand-sub {{ font-size:13px; color:{MUTED}; }}

.pill {{ display:inline-block; padding:5px 12px; border-radius:999px; font-size:12px;
  border:1px solid {EDGE}; color:{MUTED}; margin-left:8px; }}
.pill.amber {{ color:{AMBER}; border-color:{AMBER}55; background:{AMBER}12; }}
.pill.green {{ color:{GREEN}; border-color:{GREEN}55; background:{GREEN}12; }}

.banner {{ margin:18px 0 6px 0; padding:12px 16px; border-radius:10px; font-size:14px;
  background:{AMBER}12; border:1px solid {AMBER}55; color:{TEXT}; }}
.banner b {{ color:{AMBER}; }}

.status {{ margin:6px 0 18px 0; font-size:14px; color:{MUTED}; }}
.status b {{ color:{TEXT}; }}

.kpi {{ background:{PANEL}; border:1px solid {EDGE}; border-left:3px solid {CYAN};
  border-radius:10px; padding:16px 18px; min-height:122px; box-sizing:border-box; }}
.kpi.red {{ border-left-color:{RED}; }}
.kpi.amber {{ border-left-color:{AMBER}; }}
.kpi.green {{ border-left-color:{GREEN}; }}
.kpi.blue {{ border-left-color:{BLUE}; }}
.kpi-label {{ font-size:13px; color:{MUTED}; margin-bottom:6px; }}
.kpi-value {{ font-family: ui-monospace, "SF Mono", Consolas, monospace; font-size:34px;
  font-weight:600; color:{TEXT}; line-height:1.1; }}
.kpi-unit {{ font-size:15px; color:{MUTED}; margin-left:6px; font-weight:400; }}
.kpi-note {{ font-size:12.5px; color:{MUTED}; margin-top:8px; }}

.section {{ font-size:18px; font-weight:600; margin:26px 0 8px 0; color:{TEXT}; }}
.hint {{ font-size:13px; color:{MUTED}; margin-bottom:10px; }}

.tele-wrap {{ max-height:440px; overflow:auto; border:1px solid {EDGE}; border-radius:10px; }}
table.tele {{ width:100%; border-collapse:collapse; font-size:13px; }}
table.tele th {{ position:sticky; top:0; background:{PANEL}; color:{MUTED}; text-align:left;
  font-weight:500; padding:10px 12px; border-bottom:1px solid {EDGE}; white-space:nowrap; }}
table.tele td {{ padding:9px 12px; border-bottom:1px solid {EDGE}55; white-space:nowrap;
  font-family: ui-monospace, "SF Mono", Consolas, monospace; color:{TEXT}; }}
table.tele td.crit {{ color:{RED}; }}
table.tele td.warn {{ color:{AMBER}; }}
table.tele td.dim {{ color:{MUTED}; }}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def current_end() -> datetime:
    now = datetime.now()
    end = now.replace(minute=5, second=0, microsecond=0)
    if end > now:
        end -= timedelta(hours=1)
    return end


@st.cache_data(show_spinner=False)
def load_data(days: int, seed: int, end_iso: str):
    end = pd.Timestamp(end_iso).to_pydatetime()
    df = generate_telemetry(days=days, seed=seed, end=end)
    return df, find_events(df), summarise(df)


def plain(label: str) -> str:
    """Strip the HTML span from a CONDITION label."""
    return re.sub(r"<[^>]+>", "", str(label)).replace("●", "").strip()


def fmt(v, dec=1) -> str:
    return "—" if pd.isna(v) else f"{v:.{dec}f}"


def card(label, value, unit="", note="", tone="cyan") -> str:
    return (
        f'<div class="kpi {tone}"><div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}<span class="kpi-unit">{unit}</span></div>'
        f'<div class="kpi-note">{note}</div></div>'
    )


def show_plot(fig):
    """Works across Streamlit versions (width argument changed in newer releases)."""
    try:
        st.plotly_chart(fig, width="stretch")
    except Exception:
        st.plotly_chart(fig, use_container_width=True)


def show_table(frame):
    try:
        st.dataframe(frame, width="stretch", hide_index=True)
    except Exception:
        st.dataframe(frame, use_container_width=True, hide_index=True)


def style_fig(fig, height=360):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=height,
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hovermode="x unified",
    )
    fig.update_xaxes(gridcolor="rgba(148,163,184,0.12)")
    fig.update_yaxes(gridcolor="rgba(148,163,184,0.12)")
    return fig


def shade(fig, events, kinds, color, opacity):
    """Shade event periods on a chart (no annotations, so it is version-safe)."""
    for _, e in events[events["EVENT"].isin(kinds)].iterrows():
        fig.add_vrect(
            x0=e["START"].isoformat(),
            x1=e["END"].isoformat(),
            fillcolor=color,
            opacity=opacity,
            line_width=0,
            layer="below",
        )


def masked(series, mask):
    return series.where(mask)


# --------------------------------------------------------------------------
# Charts
# --------------------------------------------------------------------------
def thermal_fig(df, events):
    x = df["TIMESTAMP"]
    spike = df["DQ FLAG"] == "spike"
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=masked(df["SUPPLY °C"], ~spike), name="Supply",
                             mode="lines", line=dict(color=CYAN, width=1.6), connectgaps=False))
    fig.add_trace(go.Scatter(x=x, y=df["RETURN °C"], name="Return (measured)",
                             mode="lines", line=dict(color=BLUE, width=1.6), connectgaps=False))
    fig.add_trace(go.Scatter(x=x, y=df["EXPECTED RETURN °C"], name="Return (healthy expectation)",
                             mode="lines", line=dict(color=GREY, width=1.2, dash="dash"),
                             connectgaps=False))
    if spike.any():
        fig.add_trace(go.Scatter(x=x[spike], y=df.loc[spike, "SUPPLY °C"], name="Spike (excluded)",
                                 mode="markers", marker=dict(color=AMBER, size=9, symbol="x")))
    shade(fig, events, ["High return temperature"], RED, 0.16)
    shade(fig, events, ["Data gap"], GREY, 0.18)
    fig.update_yaxes(title_text="°C")
    return style_fig(fig)


def residual_fig(df):
    res = df["RESIDUAL K"]
    colours = np.where(res > CRIT_K, RED, np.where(res > WARN_K, AMBER, CYAN)).tolist()
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["TIMESTAMP"], y=res, name="Measured minus expected return",
                         marker=dict(color=colours)))
    fig.add_hline(y=WARN_K, line_dash="dot", line_color=AMBER)
    fig.add_hline(y=CRIT_K, line_dash="dot", line_color=RED)
    fig.update_yaxes(title_text="K above healthy expectation")
    return style_fig(fig)


def heat_fig(df, events):
    x = df["TIMESTAMP"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=df["HEAT KW"], name="Delivered to buildings", mode="lines",
                             line=dict(color=CYAN, width=1.5), fill="tozeroy",
                             fillcolor="rgba(34,211,238,0.10)", connectgaps=False))
    fig.add_trace(go.Scatter(x=x, y=df["PLANT HEAT KW"], name="Produced at plant", mode="lines",
                             line=dict(color=GREY, width=1.2, dash="dash"), connectgaps=False))
    shade(fig, events, ["Excess heat loss"], AMBER, 0.07)
    shade(fig, events, ["Data gap"], GREY, 0.18)
    fig.update_yaxes(title_text="kW", rangemode="tozero")
    return style_fig(fig)


def flow_fig(df, events):
    x = df["TIMESTAMP"]
    frozen = df["DQ FLAG"] == "frozen"
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=df["FLOW KG/S"], name="Flow", mode="lines",
                             line=dict(color=BLUE, width=1.5), connectgaps=False))
    if frozen.any():
        fig.add_trace(go.Scatter(x=x[frozen], y=df.loc[frozen, "FLOW KG/S"], name="Frozen reading",
                                 mode="markers", marker=dict(color=AMBER, size=6)))
    shade(fig, events, ["Frozen flow sensor"], AMBER, 0.12)
    shade(fig, events, ["Data gap"], GREY, 0.18)
    fig.update_yaxes(title_text="kg/s", rangemode="tozero")
    return style_fig(fig)


def telemetry_html(df, limit=300) -> str:
    d = df.iloc[::-1].head(limit)
    head = ["Time", "Supply °C", "Return °C", "Expected °C", "Residual K", "ΔT K", "Heat kW",
            "Plant kW", "Flow kg/s", "Ambient °C", "Data", "Condition"]
    rows = ["<tr>" + "".join(f"<th>{h}</th>" for h in head) + "</tr>"]
    for _, r in d.iterrows():
        res = r["RESIDUAL K"]
        res_cls = "crit" if (not pd.isna(res) and res > CRIT_K) else ("warn" if (not pd.isna(res) and res > WARN_K) else "")
        ret_cls = "crit" if r["HIGH RETURN FLAG"] else ""
        dq = r["DQ FLAG"]
        dq_cls = "dim" if dq == "ok" else ("warn" if dq in ("spike", "frozen") else "crit")
        cells = [
            f'<td>{r["TIMESTAMP"].strftime("%d %b, %H:%M")}</td>',
            f'<td>{fmt(r["SUPPLY °C"])}</td>',
            f'<td class="{ret_cls}">{fmt(r["RETURN °C"])}</td>',
            f'<td class="dim">{fmt(r["EXPECTED RETURN °C"])}</td>',
            f'<td class="{res_cls}">{fmt(res)}</td>',
            f'<td>{fmt(r["DELTA T K"])}</td>',
            f'<td>{fmt(r["HEAT KW"], 0)}</td>',
            f'<td>{fmt(r["PLANT HEAT KW"], 0)}</td>',
            f'<td>{fmt(r["FLOW KG/S"], 2)}</td>',
            f'<td>{fmt(r["AMBIENT °C"])}</td>',
            f'<td class="{dq_cls}">{dq}</td>',
            f'<td>{r["CONDITION"]}</td>',
        ]
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return '<div class="tele-wrap"><table class="tele">' + "".join(rows) + "</table></div>"


# --------------------------------------------------------------------------
# Page
# --------------------------------------------------------------------------
if "seed" not in st.session_state:
    st.session_state["seed"] = 42

top_l, top_r = st.columns([5, 1.4])
with top_l:
    st.markdown(
        '<div class="brand"><div class="brand-mark">🔥</div><div>'
        '<div class="brand-name">HEAT / <b>TWIN</b></div>'
        '<div class="brand-sub">North Quay District, Loop 01'
        '<span class="pill amber">Simulated</span><span class="pill green">Model active</span>'
        "</div></div></div>",
        unsafe_allow_html=True,
    )
with top_r:
    if st.button("Regenerate telemetry"):
        st.session_state["seed"] += 1

st.markdown(
    '<div class="banner"><b>Synthetic demonstration data.</b> This is a simulated network with '
    "faults and data problems injected on purpose. It is not measured data from a real site, and "
    "the model has not been validated on a real network.</div>",
    unsafe_allow_html=True,
)

ctl_l, ctl_r = st.columns([5, 1.4])
with ctl_l:
    days = st.slider("Window (days)", min_value=7, max_value=40, value=27, step=1)

df, events, stats = load_data(int(days), int(st.session_state["seed"]), current_end().isoformat())

with ctl_r:
    export = df.copy()
    export["CONDITION"] = export["CONDITION"].map(plain)
    st.download_button(
        "Export CSV",
        data=export.to_csv(index=False).encode("utf-8"),
        file_name="north_quay_loop01_telemetry.csv",
        mime="text/csv",
    )

last = df.iloc[-1]
st.markdown(
    f'<div class="status">Latest simulated reading <b>{last["TIMESTAMP"].strftime("%d %b, %H:%M")}</b>'
    f' &nbsp;·&nbsp; Status <b>{plain(last["CONDITION"])}</b></div>',
    unsafe_allow_html=True,
)

alerts = events[events["SEVERITY"].isin(["warning", "critical"])]
n_crit = int((alerts["SEVERITY"] == "critical").sum())
n_warn = int((alerts["SEVERITY"] == "warning").sum())
gap_hours = int((df["DQ FLAG"] == "missing").sum())

row1 = st.columns(4)
usable = df["DQ FLAG"].isin(["ok", "frozen"])
row1[0].markdown(card("Average supply temperature", fmt(df.loc[usable, "SUPPLY °C"].mean()), "°C",
                      "Measured at the energy centre, spikes excluded"), unsafe_allow_html=True)
row1[1].markdown(card("Average return temperature", fmt(stats["mean_return_c"]), "°C",
                      "Measured, unflagged hours", "blue"), unsafe_allow_html=True)
row1[2].markdown(card("Average temperature difference", fmt(stats["mean_delta_t_k"]), "K",
                      "Supply minus return"), unsafe_allow_html=True)
row1[3].markdown(card("Peak heat delivered", fmt(df["HEAT KW"].max(), 0), "kW",
                      "Building heat meters, hourly"), unsafe_allow_html=True)

st.write("")
row2 = st.columns(4)
tone = "red" if n_crit else ("amber" if n_warn else "green")
row2[0].markdown(card("Alerts in window", f"{len(alerts)}", "",
                      f"{n_crit} critical · {n_warn} warning (each event counted once)", tone),
                 unsafe_allow_html=True)
row2[1].markdown(card("Data completeness", fmt(stats["data_completeness_pct"]), "%",
                      f"{gap_hours} gap hours · {stats['spikes_excluded']} spikes excluded · "
                      f"{stats['frozen_hours']} frozen hours", "amber"), unsafe_allow_html=True)
row2[2].markdown(card("Network efficiency", fmt(stats["network_efficiency_pct"]), "%",
                      "Heat delivered ÷ heat produced", "blue"), unsafe_allow_html=True)
row2[3].markdown(card("Heat loss", fmt(stats["heat_loss_w_per_dwelling"], 0), "W/dwelling",
                      f"Illustrative, assumes {DWELLINGS} dwellings", "blue"), unsafe_allow_html=True)

st.markdown('<div class="section">Network behaviour</div>', unsafe_allow_html=True)
st.markdown('<div class="hint">Shaded bands mark detected events. Grey bands are data gaps. '
            "Gaps are shown as gaps and are never filled in.</div>", unsafe_allow_html=True)

tab_t, tab_r, tab_h, tab_f = st.tabs(["Temperatures", "Detection", "Heat", "Flow"])
with tab_t:
    show_plot(thermal_fig(df, events))
    st.caption("Return is compared with what a healthy network would show at the same supply "
               "temperature, weather and delivered heat.")
with tab_r:
    show_plot(residual_fig(df))
    st.caption(f"An event needs the return to stay above {WARN_K:.0f} K over expectation for at least "
               f"{MIN_HOURS} hours. Above {CRIT_K:.0f} K is critical.")
with tab_h:
    show_plot(heat_fig(df, events))
    st.caption("The gap between produced and delivered heat is pipe loss. A wider gap than expected "
               "over many hours is flagged as excess heat loss.")
with tab_f:
    show_plot(flow_fig(df, events))
    st.caption(f"A flow reading that does not change for {FROZEN_HOURS} hours or more is flagged as a "
               "frozen sensor. It looks calm, which is why it is easy to miss in period averages.")

st.markdown('<div class="section">Detected events</div>', unsafe_allow_html=True)
if events.empty:
    st.info("No events in this window.")
else:
    shown = events.copy()
    shown["START"] = shown["START"].dt.strftime("%d %b, %H:%M")
    shown["END"] = shown["END"].dt.strftime("%d %b, %H:%M")
    show_table(shown.rename(columns=str.title))

with st.expander("Raw telemetry · hourly readings · newest first"):
    st.markdown(telemetry_html(df), unsafe_allow_html=True)
    st.caption("Showing the latest 300 hours. Export CSV contains all rows and the data-quality flags.")

with st.expander("How this works, and its limits"):
    st.markdown(
        "- **Model.** One loop: supply pipe, customers, return pipe. Pipe heat loss uses the standard "
        "buried-pipe relation, and customers return water at about 40 °C when healthy.\n"
        "- **Detection.** Measured return is compared with the healthy expectation. Sustained "
        "differences become events. Frozen flow readings and unusually high heat loss are checked "
        "separately.\n"
        "- **Data quality.** Missing hours and single-hour spikes are flagged and excluded from the "
        "statistics. Nothing is interpolated.\n"
        "- **Limits.** The data is synthetic and the parameters are illustrative, not calibrated to a "
        "real network. The same physics creates the data and checks it, so this shows the logic works, "
        "not that it would work on a real network."
    )
