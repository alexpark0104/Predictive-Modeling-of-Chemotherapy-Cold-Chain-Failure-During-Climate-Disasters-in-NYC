"""Facility-level Monte Carlo: policy loss vs physics loss under outage scenarios.

Outputs are CONDITIONAL on an outage occurring at the facility (not annual risk) and are
exposure-style probabilities for unopened refrigerated inventory, not patient-level outcomes.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Dict, Tuple

import numpy as np

from . import params as P
from .degradation import PolicyRule, excess_weight, physics_loss, policy_loss
from .outage import LognormalOutage
from .thermal import simulate_batch, tau_from_breach_time

FRIDGE_TYPES = ("pharmaceutical", "freezerless", "dual_zone", "dorm")


@dataclass(frozen=True)
class Scenario:
    name: str
    outage: LognormalOutage
    fridge_type: str = "pharmaceutical"
    flooded: bool = False
    backup_hr_if_ok: float = 0.0          # hours backup keeps the fridge cold if it works
    p_backup_ok_nonflood: float = 0.0
    p_backup_ok_flood: float = 0.0        # < nonflood encodes flood-correlated backup failure
    T_room0_c: float = P.value("room_initial_c")
    T_outdoor_c: float = P.value("outdoor_c")
    tau_room_hr: float = P.value("tau_room_hr")


@dataclass(frozen=True)
class RunConfig:
    n: int = 20000
    seed: int = 0
    dt_hr: float = 0.1
    horizon_hr: float = 336.0
    ea_kj_mol: float = P.value("ea_kj_mol")
    t_ref_c: float = P.value("t_ref_c")
    budget_range_equiv_hr: Tuple[float, float] = P.value("budget_equiv_hr_range")
    policy: PolicyRule = field(default_factory=lambda: PolicyRule(P.value("policy_allowed_hr_above_8c")))
    T_fridge0_range_c: Tuple[float, float] = P.value("fridge_setpoint_range_c")
    nist_test_room_c: float = P.value("nist_test_room_c")
    hvac_on_backup: bool = False
    allow_placeholders: bool = False


def wilson_ci(k: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1 + z ** 2 / n
    centre = (p + z ** 2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / denom
    return (float(max(0.0, centre - half)), float(min(1.0, centre + half)))


def run_scenario(s: Scenario, cfg: RunConfig = RunConfig()) -> Dict[str, float]:
    bad = P.placeholders()
    if bad and not cfg.allow_placeholders:
        warnings.warn("Registry still has PLACEHOLDER parameters (" + ", ".join(bad) +
                      "): results are illustrative only.", stacklevel=2)
    if s.fridge_type not in FRIDGE_TYPES:
        raise ValueError(f"fridge_type must be one of {FRIDGE_TYPES}")

    rng = np.random.default_rng(cfg.seed)
    n = cfg.n
    outage = s.outage.sample(n, rng)

    p_ok = s.p_backup_ok_flood if s.flooded else s.p_backup_ok_nonflood
    backup_hr = np.where(rng.random(n) < p_ok, s.backup_hr_if_ok, 0.0)

    lo, hi = P.value(f"breach_hr_{s.fridge_type}")
    t_breach = rng.uniform(lo, hi, n)
    T0 = rng.uniform(*cfg.T_fridge0_range_c, n)
    tau = tau_from_breach_time(t_breach, T0, cfg.nist_test_room_c)

    b0, b1 = cfg.budget_range_equiv_hr
    budget = np.exp(rng.uniform(np.log(b0), np.log(b1), n))

    sim = simulate_batch(
        outage, tau, T0, s.T_room0_c, s.T_outdoor_c, s.tau_room_hr, backup_hr,
        dt_hr=cfg.dt_hr, horizon_hr=cfg.horizon_hr, threshold_c=cfg.policy.threshold_c,
        weight_fn=lambda T, T0_: excess_weight(T, T0_, cfg.ea_kj_mol, cfg.t_ref_c),
        hvac_on_backup=cfg.hvac_on_backup,
    )
    pol = policy_loss(sim["hours_above"], cfg.policy)
    phy = physics_loss(sim["dose"], budget)

    def rate(mask):
        k = int(mask.sum())
        lo_, hi_ = wilson_ci(k, n)
        return k / n, lo_, hi_

    out = {"scenario": s.name, "n": n}
    for key, mask in (("policy", pol), ("physics", phy), ("avoidable", pol & ~phy), ("physics_only", phy & ~pol)):
        p, l, h = rate(mask)
        out[f"p_{key}"], out[f"p_{key}_lo"], out[f"p_{key}_hi"] = p, l, h
    return out
