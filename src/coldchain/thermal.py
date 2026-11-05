"""Lumped-capacitance refrigerator model during power loss.

The fridge relaxes toward room temperature with time constant tau_fridge; the room
warms toward outdoor temperature with tau_room (HVAC off). Each step uses an exact
exponential update with the room held at its mid-step value, so a constant room is
integrated exactly.

Known simplifications (document these in any paper):
* Only the outage window is simulated; post-restoration pull-down is ignored, which
  biases exposure LOW.
* A single time constant per fridge; no door openings, defrost cycles, or thermal ballast.
* Product temperature is taken equal to fridge air temperature; real packaged product lags
  the air (conservative).
"""
from __future__ import annotations

from typing import Callable, Optional

import numpy as np


def tau_from_breach_time(t_breach_hr, T0_c, T_room_c, threshold_c: float = 8.0):
    """Fridge time constant that crosses `threshold_c` at `t_breach_hr` in a CONSTANT-temperature room."""
    t_breach_hr = np.asarray(t_breach_hr, dtype=float)
    T0_c = np.asarray(T0_c, dtype=float)
    T_room_c = np.asarray(T_room_c, dtype=float)
    if not (np.all(T0_c < threshold_c) and np.all(threshold_c < T_room_c)):
        raise ValueError("Need T0 < threshold < T_room.")
    ratio = (T_room_c - threshold_c) / (T_room_c - T0_c)
    return t_breach_hr / (-np.log(ratio))


def simulate_batch(
    outage_hr,
    tau_fridge_hr,
    T_fridge0_c,
    T_room0_c,
    T_outdoor_c,
    tau_room_hr,
    backup_hr=0.0,
    *,
    dt_hr: float = 0.1,
    horizon_hr: float = 336.0,
    threshold_c: float = 8.0,
    weight_fn: Optional[Callable[[np.ndarray, np.ndarray], np.ndarray]] = None,
    hvac_on_backup: bool = False,
):
    """Vectorised simulation of many outages at once.

    All array-like inputs broadcast against each other. While t < backup_hr the fridge is
    powered and held at its initial temperature. If `hvac_on_backup` is False the room starts
    warming at t = 0 regardless of backup (backup powers the fridge only).

    Outages longer than `horizon_hr` are truncated at the horizon.

    Returns dict of arrays: hours_above (time above threshold during the outage), peak_c, and
    dose (integral of weight_fn(T, T0) dt, if weight_fn is given).
    """
    arrs = np.broadcast_arrays(*[np.atleast_1d(np.asarray(a, dtype=float)) for a in
                                 (outage_hr, tau_fridge_hr, T_fridge0_c, T_room0_c, T_outdoor_c, tau_room_hr, backup_hr)])
    outage, tau, T0, Tr0, Tout, tau_r, backup = [np.array(a, dtype=float).ravel() for a in arrs]

    n = outage.size
    T = T0.copy()
    peak = T0.copy()
    hours_above = np.zeros(n)
    dose = np.zeros(n)
    outage_eff = np.minimum(outage, horizon_hr)
    decay = np.exp(-dt_hr / tau)

    for k in range(int(np.ceil(horizon_hr / dt_hr))):
        t0 = k * dt_hr
        frac = np.clip((outage_eff - t0) / dt_hr, 0.0, 1.0)
        if not frac.any():
            break
        tm = t0 + 0.5 * dt_hr
        t_room = np.maximum(tm - (backup if hvac_on_backup else 0.0), 0.0)
        T_room = Tout - (Tout - Tr0) * np.exp(-t_room / tau_r)
        T_new = T_room + (T - T_room) * decay
        T_new = np.where(tm < backup, T0, T_new)  # powered: held at setpoint
        active = frac > 0
        T = np.where(active, T_new, T)
        peak = np.where(active, np.maximum(peak, T), peak)
        hours_above += frac * dt_hr * (T > threshold_c)
        if weight_fn is not None:
            dose += frac * dt_hr * weight_fn(T, T0)

    return {"hours_above": hours_above, "peak_c": peak, "dose": dose}
