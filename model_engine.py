"""
model_engine.py
Physics engine for the district heating digital twin.

Steady-state buried-pipe heat loss (Kusuda / Cengel style):

    T_return = T_ambient + (T_supply - T_ambient) * exp(-U * L / (m_dot * Cp))
    Q_kW     = m_dot * Cp * (T_supply - T_return) / 1000

Constants
    L  = 1000 m      pipe length
    Cp = 4184 J/kg.K specific heat of water
    U  = 0.5 W/m.K   overall heat-loss coefficient per metre of pipe
"""

import numpy as np

L = 1000.0
CP = 4184.0
U = 0.5

ANOMALY_THRESHOLD = 65.0

HIGH_RETURN = '<span style="color:#f43f5e">●</span> High return'
NORMAL = '<span style="color:#10b981">●</span> Normal'


def predict_return(supply, ambient, flow):
    """Predict the return temperature (°C) from supply, ambient and mass flow (kg/s)."""
    supply = np.asarray(supply, dtype=float)
    ambient = np.asarray(ambient, dtype=float)
    flow = np.maximum(np.asarray(flow, dtype=float), 0.05)  # avoid divide-by-zero

    decay = np.exp(-(U * L) / (flow * CP))
    return ambient + (supply - ambient) * decay


def heat_delivered_kw(supply, return_temp, flow):
    """Heat delivered to the network in kW."""
    supply = np.asarray(supply, dtype=float)
    return_temp = np.asarray(return_temp, dtype=float)
    flow = np.asarray(flow, dtype=float)
    return flow * CP * (supply - return_temp) / 1000.0


def classify(return_temp):
    """Return the HTML condition label for each return temperature."""
    return_temp = np.asarray(return_temp, dtype=float)
    return np.where(return_temp > ANOMALY_THRESHOLD, HIGH_RETURN, NORMAL)


def run_model(supply, ambient, flow):
    """
    Full model pass.

    Returns
    -------
    predicted_return : ndarray  (°C)
    heat_kw          : ndarray  (kW)
    anomaly          : ndarray  (HTML strings)
    """
    predicted_return = predict_return(supply, ambient, flow)
    heat_kw = heat_delivered_kw(supply, predicted_return, flow)
    anomaly = classify(predicted_return)
    return predicted_return, heat_kw, anomaly
