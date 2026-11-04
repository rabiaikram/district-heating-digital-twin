"""
data_generator.py
SYNTHETIC hourly telemetry for the North Quay District - Loop 01 digital shadow.

This is simulated data, not measurements from a real network. It contains:
  * a healthy baseline (weather-compensated supply, realistic load profile),
  * a few injected faults, so detection can be demonstrated:
        - two periods of bypass / stuck-open valve (high return temperature)
        - a period of degraded pipe insulation (excess heat loss)
        - a frozen flow meter
  * realistic data problems: a gateway outage, random missing hours, spikes.

Fault timing is expressed as a fraction of the window, so it scales with `days`.
"""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from model_engine import T_BASE, Q_PEAK_KW, diagnose, simulate_network

# Original columns first (so existing app code keeps working), extras after.
COLUMNS = [
    "TIMESTAMP",
    "SUPPLY °C",
    "RETURN °C",
    "HEAT KW",
    "AMBIENT °C",
    "FLOW KG/S",
    "CONDITION",
]
EXTRA_COLUMNS = [
    "PLANT HEAT KW",
    "EXPECTED RETURN °C",
    "RESIDUAL K",
    "DELTA T K",
    "DQ FLAG",
    "ALERT",
    "HIGH RETURN FLAG",
    "EXCESS LOSS FLAG",
]


def _gauss(x, mu, sigma):
    return np.exp(-0.5 * ((x - mu) / sigma) ** 2)


def _window(n, start_frac, end_frac):
    idx = np.arange(n)
    return (idx >= int(n * start_frac)) & (idx < int(n * end_frac))


def generate_telemetry(days: int = 27, seed: int = 42, end=None) -> pd.DataFrame:
    """
    Generate `days` * 24 hourly readings ending at `end` (default: current hour,
    :05 past). Rows are oldest -> newest. Returns the original columns plus
    diagnostic columns (see EXTRA_COLUMNS).
    """
    days = int(days)
    n = days * 24
    rng = np.random.default_rng(seed)

    if end is None:
        now = datetime.now()
        end = now.replace(minute=5, second=0, microsecond=0)
        if end > now:
            end -= timedelta(hours=1)
    timestamps = pd.date_range(end=end, periods=n, freq="h")
    hour = timestamps.hour.to_numpy() + timestamps.minute.to_numpy() / 60.0
    day_idx = np.arange(n) / 24.0

    # --- Weather ----------------------------------------------------------
    ambient = (
        9.0
        + 2.6 * np.sin(2 * np.pi * (hour - 9) / 24)
        + 1.3 * np.sin(2 * np.pi * day_idx / 7.0)
        + rng.normal(0, 1.1, n)
    )

    # --- Heat load: space heating (weather driven) + hot water profile -------
    k_space = 0.83 * Q_PEAK_KW / (T_BASE + 3.0)          # kW per K below balance temp
    occupancy = 0.85 + 0.15 * _gauss(hour, 19, 5)
    space = np.maximum(T_BASE - ambient, 0.0) * k_space * occupancy
    dhw = 60.0 + 70.0 * _gauss(hour, 8, 1.5) + 90.0 * _gauss(hour, 20, 2.5)
    load = (space + dhw) * (1.0 + rng.normal(0, 0.04, n))
    load = np.clip(load, 40.0, Q_PEAK_KW * 1.05)

    # --- Plant supply temperature: weather compensation + control noise ------
    supply = np.clip(68.0 + (T_BASE - ambient), 68.0, 85.0) + rng.normal(0, 0.8, n)

    # --- Injected network faults -------------------------------------------
    bypass = np.zeros(n)
    for a, b, peak in ((0.30, 0.38, 0.30), (0.68, 0.74, 0.45)):
        w = _window(n, a, b)
        ramp = np.clip((np.cumsum(w) / 6.0), 0, 1) * w          # 6 h ramp-up
        bypass = np.maximum(bypass, peak * ramp)
    u_mult = np.where(_window(n, 0.55, 1.01), 1.8, 1.0)         # insulation damage

    sim = simulate_network(supply, ambient, load, bypass=bypass, u_mult=u_mult)

    # --- Measurement layer (sensor noise) -----------------------------------
    supply_m = supply + rng.normal(0, 0.2, n)
    return_m = sim["return_plant"] + rng.normal(0, 0.3, n)
    flow_m = sim["flow"] * (1.0 + rng.normal(0, 0.01, n))
    heat_m = load * (1.0 + rng.normal(0, 0.015, n))              # building heat meters
    plant_m = sim["plant_kw"] * (1.0 + rng.normal(0, 0.01, n))   # plant heat meter
    ambient_m = ambient + rng.normal(0, 0.2, n)

    # --- Sensor / data faults ------------------------------------------------
    froz = np.where(_window(n, 0.82, 0.82 + 30.0 / n))[0]       # 30 h frozen flow meter
    if len(froz):
        flow_m[froz] = flow_m[froz[0] - 1]

    spike_idx = rng.choice(n, size=max(1, int(0.005 * n)), replace=False)
    supply_m[spike_idx] += 10.0

    # --- Data gaps: gateway outage + random missing hours ---------------------
    all_cols = [supply_m, return_m, flow_m, heat_m, plant_m, ambient_m]
    outage = _window(n, 0.22, 0.22 + 8.0 / n)                    # 8 h gateway outage
    rand_missing = rng.random(n) < 0.015
    gap = outage | rand_missing
    for arr in all_cols:
        arr[gap] = np.nan

    df = pd.DataFrame(
        {
            "TIMESTAMP": timestamps,
            "SUPPLY °C": supply_m,
            "RETURN °C": return_m,
            "HEAT KW": heat_m,
            "AMBIENT °C": ambient_m,
            "FLOW KG/S": flow_m,
            "PLANT HEAT KW": plant_m,
        }
    )
    df = diagnose(df)

    for col, dec in (("SUPPLY °C", 1), ("RETURN °C", 1), ("HEAT KW", 1), ("AMBIENT °C", 1),
                     ("FLOW KG/S", 2), ("PLANT HEAT KW", 1), ("EXPECTED RETURN °C", 1),
                     ("RESIDUAL K", 1), ("DELTA T K", 1)):
        df[col] = df[col].round(dec)

    return df[COLUMNS + EXTRA_COLUMNS]
