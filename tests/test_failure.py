import warnings

from coldchain.degradation import PolicyRule
from coldchain.failure import RunConfig, Scenario, run_scenario, wilson_ci
from coldchain.outage import LognormalOutage

warnings.simplefilter("ignore")
CFG = RunConfig(n=4000, seed=7, allow_placeholders=True)


def _s(mean, sigma=0.3, **kw):
    return Scenario("t", LognormalOutage(mean, sigma), **kw)


def test_negligible_outages_cause_no_loss():
    r = run_scenario(_s(0.05, 0.2), CFG)
    assert r["p_policy"] == 0.0 and r["p_physics"] == 0.0


def test_very_long_outage_causes_policy_loss_and_physics_loss_with_small_budget():
    cfg = RunConfig(n=2000, seed=1, allow_placeholders=True, budget_range_equiv_hr=(5.0, 10.0))
    r = run_scenario(_s(200.0), cfg)
    assert r["p_policy"] > 0.99 and r["p_physics"] > 0.99


def test_strict_policy_exceeds_physics_when_budget_is_large():
    cfg = RunConfig(n=3000, seed=2, allow_placeholders=True, budget_range_equiv_hr=(500.0, 600.0))
    r = run_scenario(_s(8.0, 0.5), cfg)
    assert r["p_policy"] > 0.3 and r["p_physics"] == 0.0
    assert abs(r["p_avoidable"] - r["p_policy"]) < 1e-12


def test_longer_backup_reduces_loss():
    base = dict(p_backup_ok_nonflood=1.0)
    lo = run_scenario(_s(10.0, 0.5, backup_hr_if_ok=1.0, **base), CFG)["p_policy"]
    hi = run_scenario(_s(10.0, 0.5, backup_hr_if_ok=12.0, **base), CFG)["p_policy"]
    assert hi < lo


def test_flood_correlated_backup_failure_raises_loss():
    kw = dict(backup_hr_if_ok=24.0, p_backup_ok_nonflood=0.95, p_backup_ok_flood=0.4)
    dry = run_scenario(_s(20.0, 0.5, flooded=False, **kw), CFG)["p_policy"]
    wet = run_scenario(_s(20.0, 0.5, flooded=True, **kw), CFG)["p_policy"]
    assert wet > dry


def test_pharmaceutical_fridges_fail_sooner_than_freezerless():
    a = run_scenario(_s(2.0, 0.4, fridge_type="pharmaceutical"), CFG)["p_policy"]
    b = run_scenario(_s(2.0, 0.4, fridge_type="freezerless"), CFG)["p_policy"]
    assert a > b


def test_same_seed_reproducible_and_different_seed_differs():
    s = _s(6.0, 0.8)
    a, b = run_scenario(s, CFG), run_scenario(s, CFG)
    c = run_scenario(s, RunConfig(n=4000, seed=8, allow_placeholders=True))
    assert a == b and a["p_policy"] != c["p_policy"]


def test_wilson_interval_contains_estimate():
    lo, hi = wilson_ci(30, 100)
    assert lo < 0.3 < hi and 0.0 <= lo and hi <= 1.0
