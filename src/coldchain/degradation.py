"""Temperature-time degradation accounting and discard rules.

Two competing definitions of 'loss' are compared throughout the project:

* POLICY loss: a label-style rule (default: any time above 8 C means discard).
* PHYSICS loss: accumulated thermal-equivalent hours (relative to a reference temperature,
  via an Arrhenius factor) exceed a degradation budget.

The Arrhenius form is an approximation; protein aggregation is often non-Arrhenius, so Ea and
the budget must be treated as uncertain inputs (see params.py).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

R_KJ = 8.314462618e-3  # kJ mol^-1 K^-1


def arrhenius_factor(T_c, ea_kj_mol: float, t_ref_c: float):
    """Rate relative to the rate at t_ref_c (=1 at the reference temperature)."""
    T = np.asarray(T_c, dtype=float) + 273.15
    Tr = t_ref_c + 273.15
    return np.exp(-(ea_kj_mol / R_KJ) * (1.0 / T - 1.0 / Tr))


def excess_weight(T_c, T_set_c, ea_kj_mol: float, t_ref_c: float):
    """Degradation rate above what normal storage at the setpoint would accrue (never negative)."""
    return np.maximum(arrhenius_factor(T_c, ea_kj_mol, t_ref_c) - arrhenius_factor(T_set_c, ea_kj_mol, t_ref_c), 0.0)


def equivalent_hours(t_hr, T_c, ea_kj_mol: float, t_ref_c: float) -> float:
    """Thermal-equivalent hours at t_ref_c for one temperature trajectory (trapezoid rule)."""
    t = np.asarray(t_hr, dtype=float)
    y = arrhenius_factor(T_c, ea_kj_mol, t_ref_c)
    return float(np.sum((y[1:] + y[:-1]) * np.diff(t)) / 2.0)


def mean_kinetic_temperature(T_c, delta_h_kj_mol: float = 83.144) -> float:
    """Mean kinetic temperature (C) of equally spaced readings. 83.144 kJ/mol is the conventional
    default; verify against the current USP general chapter before citing."""
    T = np.asarray(T_c, dtype=float) + 273.15
    a = delta_h_kj_mol / R_KJ
    return float(a / (-np.log(np.mean(np.exp(-a / T)))) - 273.15)


@dataclass(frozen=True)
class PolicyRule:
    """Discard if time above `threshold_c` exceeds `allowed_hours_above_threshold`."""
    allowed_hours_above_threshold: float = 0.0
    threshold_c: float = 8.0


def policy_loss(hours_above, rule: PolicyRule):
    return np.asarray(hours_above) > rule.allowed_hours_above_threshold


def physics_loss(dose_equiv_hr, budget_equiv_hr):
    return np.asarray(dose_equiv_hr) > np.asarray(budget_equiv_hr)
