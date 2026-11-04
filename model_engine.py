"""
model_engine.py
Physics + diagnostics for the district heating digital shadow (SYNTHETIC DEMO).

What this model represents
--------------------------
One heat-network loop: energy centre -> supply pipe -> substations (customers)
-> return pipe -> energy centre.

    1. Supply pipe loses heat to the ground:
           T_supply_end = T_amb + (T_supply - T_amb) * exp(-U*L / (m*cp))
    2. Customers extract heat Q_load. A healthy substation returns water at
       T_return_sub (about 40 C at full load, slightly warmer at part load).
       Flow is set by the control valves so the load is met:
           m = Q_load / (cp * (1 - bypass) * (T_supply_end - T_return_sub))
    3. A bypass / stuck-open valve / fouled heat exchanger sends a fraction of the
       flow back hot, which raises the return temperature (low delta-T problem):
           T_mix = (1 - bypass) * T_return_sub + bypass * T_supply_end
    4. Return pipe loses heat to the ground:
           T_return_plant = T_amb + (T_mix - T_amb) * exp(-U*L / (m*cp))
    5. Energy balance:
           Q_plant = m * cp * (T_supply - T_return_plant)
           Q_loss  = Q_plant - Q_load      (supply + return pipe losses)

Diagnostics compare MEASURED values with what a HEALTHY network would show under
the same conditions (supply temperature, ambient, delivered heat). Deviations are
"residuals". Data problems (gaps, spikes, frozen sensors) are FLAGGED, never
silently filled.

All parameters below are ILLUSTRATIVE, not calibrated to a real network.
Check realistic ranges against CIBSE CP1 / project data before using for real.
"""

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------
# Network parameters (illustrative)
# --------------------------------------------------------------------------
L = 1000.0                 # route length of each pipe (supply and return), m
CP = 4184.0                # specific heat of water, J/(kg.K)
CP_KJ = CP / 1000.0
U = 0.20                   # heat-loss coefficient per pipe, W/(m.K)
DWELLINGS = 300            # dwellings served (for W/dwelling indicator)
T_BASE = 15.5              # balance temperature for space heating, C
Q_PEAK_KW = 700.0          # design peak heat load, kW
RETURN_DESIGN = 40.0       # healthy substation return at full load, C
RETURN_PART_LOAD_RISE = 4.0  # healthy return is warmer at part load, K

# --------------------------------------------------------------------------
# Detection settings
# --------------------------------------------------------------------------
ANOMALY_THRESHOLD = 65.0   # absolute sanity ceiling, C (kept for compatibility)
WARN_K = 3.0               # residual warning level, K
CRIT_K = 6.0               # residual critical level, K
MIN_HOURS = 3              # hours above warning level before it counts
SPIKE_K = 6.0              # single-point jump versus rolling median, K
FROZEN_HOURS = 6           # identical readings for this long = frozen sensor
LOSS_EXCESS_RATIO = 0.40   # excess heat loss versus expectation (24 h mean)
LOSS_MIN_HOURS = 12

# --------------------------------------------------------------------------
# Condition labels (HTML spans, same style as the original app)
# --------------------------------------------------------------------------
HIGH_RETURN = '<span style="color:#f43f5e">●</span> High return'
EXCESS_LOSS = '<span style="color:#f43f5e">●</span> Excess heat loss'
FROZEN = '<span style="color:#f59e0b">●</span> Frozen flow sensor'
MISSING = '<span style="color:#94a3b8">●</span> Data gap'
SPIKE = '<span style="color:#f59e0b">●</span> Spike (excluded)'
NORMAL = '<span style="color:#10b981">●</span> Normal'


# --------------------------------------------------------------------------
# Physics
# --------------------------------------------------------------------------
def _decay(flow, u_mult=1.0):
    flow = np.maximum(np.asarray(flow, dtype=float), 0.05)
    return np.exp(-(U * u_mult * L) / (flow * CP))


def healthy_substation_return(load_kw):
    """Return temperature leaving customers when everything works (C)."""
    frac = np.clip(np.asarray(load_kw, dtype=float) / Q_PEAK_KW, 0.0, 1.0)
    return RETURN_DESIGN + RETURN_PART_LOAD_RISE * (1.0 - frac)


def simulate_network(supply, ambient, load_kw, bypass=0.0, u_mult=1.0, iterations=8):
    """
    Solve the loop for given plant supply temperature, ambient temperature and
    delivered heat load.

    bypass : fraction (0-0.8) of flow that skips heat extraction (fault)
    u_mult : multiplier on pipe heat-loss coefficient (insulation damage > 1)

    Returns a dict of arrays: flow (kg/s), supply_end, return_sub, return_plant (C),
    plant_kw, load_kw, loss_kw.
    """
    supply = np.asarray(supply, dtype=float)
    ambient = np.asarray(ambient, dtype=float)
    load = np.asarray(load_kw, dtype=float)
    bypass = np.clip(np.asarray(bypass, dtype=float), 0.0, 0.8)

    t_r_sub = healthy_substation_return(load)
    m = np.maximum(load / (CP_KJ * 30.0), 0.05)           # first guess: 30 K
    for _ in range(iterations):
        t_s_end = ambient + (supply - ambient) * _decay(m, u_mult)
        d_t = np.maximum(t_s_end - t_r_sub, 5.0)
        m = np.maximum(load / (CP_KJ * (1.0 - bypass) * d_t), 0.05)
    t_s_end = ambient + (supply - ambient) * _decay(m, u_mult)

    t_mix = (1.0 - bypass) * t_r_sub + bypass * t_s_end
    t_r_plant = ambient + (t_mix - ambient) * _decay(m, u_mult)
    plant_kw = m * CP_KJ * (supply - t_r_plant)
    return {
        "flow": m,
        "supply_end": t_s_end,
        "return_sub": t_r_sub,
        "return_plant": t_r_plant,
        "plant_kw": plant_kw,
        "load_kw": load,
        "loss_kw": plant_kw - load,
    }


def expected_return(supply, ambient, load_kw):
    """Return temperature a HEALTHY network would show at the energy centre (C)."""
    return simulate_network(supply, ambient, load_kw)["return_plant"]


def heat_delivered_kw(supply, return_temp, flow):
    """Generic heat meter formula Q = m * cp * dT (kW)."""
    supply = np.asarray(supply, dtype=float)
    return_temp = np.asarray(return_temp, dtype=float)
    flow = np.asarray(flow, dtype=float)
    return flow * CP * (supply - return_temp) / 1000.0


def classify(return_temp):
    """Absolute ceiling check only (kept for compatibility). Real detection is diagnose()."""
    return_temp = np.asarray(return_temp, dtype=float)
    return np.where(return_temp > ANOMALY_THRESHOLD, HIGH_RETURN, NORMAL)


# --------------------------------------------------------------------------
# Diagnostics
# --------------------------------------------------------------------------
def _runs(mask, min_len):
    """Return (start, end) index pairs of True runs at least min_len long."""
    mask = np.asarray(mask, dtype=bool)
    out, start = [], None
    for i, v in enumerate(mask):
        if v and start is None:
            start = i
        elif not v and start is not None:
            if i - start >= min_len:
                out.append((start, i - 1))
            start = None
    if start is not None and len(mask) - start >= min_len:
        out.append((start, len(mask) - 1))
    return out


def _sustained(mask, min_len):
    keep = np.zeros(len(mask), dtype=bool)
    for a, b in _runs(mask, min_len):
        keep[a:b + 1] = True
    return keep


def diagnose(df):
    """
    Add diagnostic columns to a telemetry frame. Raw measured columns are NOT
    changed. Gaps and spikes are flagged and excluded from residual statistics;
    nothing is interpolated.

    Expects: SUPPLY °C, RETURN °C, HEAT KW (delivered), AMBIENT °C, FLOW KG/S,
             PLANT HEAT KW.
    Adds:    EXPECTED RETURN °C, RESIDUAL K, DELTA T K, DQ FLAG, ALERT, CONDITION,
             HIGH RETURN FLAG, EXCESS LOSS FLAG (independent, so events never split)
    """
    out = df.copy()
    s = out["SUPPLY °C"].to_numpy(float)
    r = out["RETURN °C"].to_numpy(float)
    q = out["HEAT KW"].to_numpy(float)
    a = out["AMBIENT °C"].to_numpy(float)
    f = out["FLOW KG/S"].to_numpy(float)
    qp = out["PLANT HEAT KW"].to_numpy(float)
    n = len(out)

    with np.errstate(invalid="ignore"):
        missing = np.isnan(np.column_stack([s, r, q, a, f, qp])).any(axis=1)

        sup_med = pd.Series(s).rolling(5, center=True, min_periods=3).median().to_numpy()
        ret_med = pd.Series(r).rolling(5, center=True, min_periods=3).median().to_numpy()
        spike = (~missing) & ((np.abs(s - sup_med) > SPIKE_K) | (np.abs(r - ret_med) > SPIKE_K))

        fs = pd.Series(f)
        zero_range = ((fs.rolling(FROZEN_HOURS).max() - fs.rolling(FROZEN_HOURS).min()) == 0).to_numpy()
        frozen = np.zeros(n, dtype=bool)
        for i in np.where(zero_range)[0]:
            frozen[max(0, i - FROZEN_HOURS + 1):i + 1] = True

        usable = ~(missing | spike)

        exp_ret = expected_return(s, a, q)
        residual = np.where(usable, r - exp_ret, np.nan)

        # Sustained high return: >= MIN_HOURS above warning level (bridge gaps <= 2 h)
        base = pd.Series(np.where(np.isnan(residual), np.nan, (residual > WARN_K).astype(float)))
        base = base.ffill(limit=2).fillna(0.0).to_numpy().astype(bool)
        high_return = _sustained(base, MIN_HOURS)

        # Excess heat loss versus healthy expectation (24 h smoothing)
        sim = simulate_network(s, a, q)
        meas_loss = qp - q
        excess = np.where(usable, (meas_loss - sim["loss_kw"]) / np.maximum(sim["loss_kw"], 1.0), np.nan)
        smooth = pd.Series(excess).rolling(24, min_periods=12).mean().to_numpy()
        excess_loss = _sustained(np.nan_to_num(smooth, nan=0.0) > LOSS_EXCESS_RATIO, LOSS_MIN_HOURS)

    dq = np.where(missing, "missing", np.where(spike, "spike", np.where(frozen, "frozen", "ok")))
    alert = np.where(high_return, "high_return", np.where(excess_loss, "excess_loss", ""))

    cond = np.full(n, NORMAL, dtype=object)
    cond[excess_loss] = EXCESS_LOSS
    cond[high_return] = HIGH_RETURN
    cond[frozen] = FROZEN
    cond[spike] = SPIKE
    cond[missing] = MISSING

    out["EXPECTED RETURN °C"] = exp_ret
    out["RESIDUAL K"] = residual
    out["HIGH RETURN FLAG"] = high_return
    out["EXCESS LOSS FLAG"] = excess_loss
    out["DELTA T K"] = s - r
    out["DQ FLAG"] = dq
    out["ALERT"] = alert
    out["CONDITION"] = cond
    return out


def find_events(df):
    """Group consecutive flagged hours into single events (not one per hour)."""
    rows = []
    ts = pd.to_datetime(df["TIMESTAMP"]).reset_index(drop=True)
    res = df["RESIDUAL K"].reset_index(drop=True)

    def add(kind, a, b, severity, note):
        rows.append({
            "EVENT": kind, "START": ts[a], "END": ts[b], "HOURS": b - a + 1,
            "SEVERITY": severity, "NOTE": note,
        })

    for a, b in _runs(df["HIGH RETURN FLAG"].to_numpy(), 1):
        peak = float(np.nanmax(res[a:b + 1])) if res[a:b + 1].notna().any() else float("nan")
        add("High return temperature", a, b, "critical" if peak > CRIT_K else "warning",
            f"Return up to {peak:.1f} K above healthy expectation. "
            "Check substation heat exchanger, control valve, bypass.")
    for a, b in _runs(df["EXCESS LOSS FLAG"].to_numpy(), 1):
        add("Excess heat loss", a, b, "warning",
            "Heat loss well above healthy expectation. Check insulation / leaks.")
    for a, b in _runs((df["DQ FLAG"] == "frozen").to_numpy(), 1):
        add("Frozen flow sensor", a, b, "warning",
            f"Flow reading identical for {b - a + 1} h. Check meter and communications.")
    for a, b in _runs((df["DQ FLAG"] == "missing").to_numpy(), 2):
        add("Data gap", a, b, "info", "No data received. Not filled or estimated.")
    cols = ["EVENT", "START", "END", "HOURS", "SEVERITY", "NOTE"]
    return pd.DataFrame(rows, columns=cols).sort_values("START").reset_index(drop=True)


def summarise(df):
    """Headline numbers for the dashboard (all from measured, unflagged data)."""
    ok = df["DQ FLAG"].isin(["ok", "frozen"])
    delivered = df.loc[ok, "HEAT KW"].sum()
    produced = df.loc[ok, "PLANT HEAT KW"].sum()
    loss_kw = (df.loc[ok, "PLANT HEAT KW"] - df.loc[ok, "HEAT KW"]).mean()
    return {
        "data_completeness_pct": 100.0 * (df["DQ FLAG"] != "missing").mean(),
        "spikes_excluded": int((df["DQ FLAG"] == "spike").sum()),
        "frozen_hours": int((df["DQ FLAG"] == "frozen").sum()),
        "events": len(find_events(df)),
        "mean_delta_t_k": float(df.loc[ok, "DELTA T K"].mean()),
        "mean_return_c": float(df.loc[ok, "RETURN °C"].mean()),
        "network_efficiency_pct": float(100.0 * delivered / produced) if produced else float("nan"),
        "heat_loss_w_per_dwelling": float(1000.0 * loss_kw / DWELLINGS),
    }


def run_model(supply, ambient, load_kw):
    """Healthy-network model pass: returns (expected_return, plant_kw, loss_kw)."""
    sim = simulate_network(supply, ambient, load_kw)
    return sim["return_plant"], sim["plant_kw"], sim["loss_kw"]
