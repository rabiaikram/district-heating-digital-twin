"""Generate mock hourly telemetry for the district heating PoC."""

import numpy as np
import pandas as pd


def generate_telemetry(days: int = 30) -> pd.DataFrame:
    """Return hourly telemetry for the requested number of recent days."""
    if days < 1:
        raise ValueError("days must be at least 1")

    periods = days * 24
    timestamps = pd.date_range(
        end=pd.Timestamp.now().floor("h"),
        periods=periods,
        freq="h",
    )
    rng = np.random.default_rng()

    return pd.DataFrame(
        {
            "Timestamp": timestamps,
            "Supply_Temp_C": rng.normal(80.0, 2.5, periods),
            "Ambient_Temp_C": rng.normal(10.0, 5.0, periods),
            "Flow_Rate_kg_s": rng.normal(5.0, 0.5, periods),
        }
    )
