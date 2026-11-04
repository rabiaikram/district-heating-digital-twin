"""
data_generator.py
Synthetic hourly telemetry for the North Quay District - Loop 01 digital twin.
"""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from model_engine import run_model

COLUMNS = [
    "TIMESTAMP",
    "SUPPLY °C",
    "RETURN °C",
    "HEAT KW",
    "AMBIENT °C",
    "FLOW KG/S",
    "CONDITION",
]


def generate_telemetry(days: int = 27, seed: int = 42) -> pd.DataFrame:
    """
    Generate `days` * 24 hourly readings ending at the latest reading
    (current hour, :05 past). Rows are returned oldest -> newest;
    TIMESTAMP is a real datetime so charts can use it directly.
    """
    days = int(days)
    n = days * 24
    rng = np.random.default_rng(seed)

    now = datetime.now()
    end = now.replace(minute=5, second=0, microsecond=0)
    if end > now:
        end -= timedelta(hours=1)
    timestamps = pd.date_range(end=end, periods=n, freq="h")

    hour = timestamps.hour.to_numpy() + timestamps.minute.to_numpy() / 60.0
    day_idx = np.arange(n) / 24.0

    # Ambient: daily cycle + slow weekly drift + noise
    ambient = (
        9.0
        + 2.6 * np.sin(2 * np.pi * (hour - 9) / 24)
        + 1.3 * np.sin(2 * np.pi * day_idx / 7.0)
        + rng.normal(0, 1.1, n)
    )

    # Supply temperature: set-point around 80 °C with control noise
    supply = (
        80.0
        + 1.2 * np.sin(2 * np.pi * (hour - 6) / 24)
        + rng.normal(0, 2.0, n)
    )

    # Mass flow (kg/s): morning / evening demand shape
    flow = (
        5.2
        + 0.35 * np.sin(2 * np.pi * (hour - 7) / 24)
        + rng.normal(0, 0.35, n)
    )
    flow = np.clip(flow, 3.8, 6.5)

    predicted_return, heat_kw, condition = run_model(supply, ambient, flow)

    df = pd.DataFrame(
        {
            "TIMESTAMP": timestamps,
            "SUPPLY °C": np.round(supply, 1),
            "RETURN °C": np.round(predicted_return, 1),
            "HEAT KW": np.round(heat_kw, 1),
            "AMBIENT °C": np.round(ambient, 1),
            "FLOW KG/S": np.round(flow, 2),
            "CONDITION": condition,
        }
    )
    return df[COLUMNS]
