"""Steady-state thermo-hydraulic calculations for buried insulated pipes."""

import numpy as np
import pandas as pd

PIPE_LENGTH_M = 1000.0
SPECIFIC_HEAT_J_KG_C = 4184.0
THERMAL_TRANSMITTANCE_W_M_K = 0.5
ANOMALY_RETURN_TEMP_C = 65.0


def calculate_thermodynamics(df: pd.DataFrame) -> pd.DataFrame:
    """Add predicted return temperature, delivered heat, and anomaly flag."""
    required_columns = {
        "Supply_Temp_C",
        "Ambient_Temp_C",
        "Flow_Rate_kg_s",
    }
    missing_columns = required_columns.difference(df.columns)
    if missing_columns:
        raise ValueError(
            "Missing required telemetry columns: "
            + ", ".join(sorted(missing_columns))
        )
    if (df["Flow_Rate_kg_s"] <= 0).any():
        raise ValueError("Flow_Rate_kg_s must be greater than zero")

    result = df.copy()
    attenuation = np.exp(
        -(THERMAL_TRANSMITTANCE_W_M_K * PIPE_LENGTH_M)
        / (result["Flow_Rate_kg_s"] * SPECIFIC_HEAT_J_KG_C)
    )
    result["Predicted_Return_Temp_C"] = result["Ambient_Temp_C"] + (
        result["Supply_Temp_C"] - result["Ambient_Temp_C"]
    ) * attenuation
    result["Heat_Delivered_kW"] = (
        result["Flow_Rate_kg_s"]
        * SPECIFIC_HEAT_J_KG_C
        * (
            result["Supply_Temp_C"]
            - result["Predicted_Return_Temp_C"]
        )
        / 1000.0
    )
    result["Anomaly_Flag"] = (
        result["Predicted_Return_Temp_C"] > ANOMALY_RETURN_TEMP_C
    )
    return result
