"""ILLUSTRATIVE demo of the policy-vs-physics comparison.

Every number printed here depends on PLACEHOLDER inputs (see src/coldchain/params.py) and must
not be cited. The point is to show how the pieces fit together.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from coldchain import params as P
from coldchain.failure import RunConfig, Scenario, run_scenario
from coldchain.outage import LognormalOutage

print("=" * 78)
print("ILLUSTRATIVE ONLY - placeholder parameters in use:", ", ".join(P.placeholders()))
print("=" * 78)

sig = P.value("outage_sigma")
scenarios = [
    Scenario("ordinary outage, no backup", LognormalOutage(6.0, sig)),
    Scenario("storm outage, no backup", LognormalOutage(48.0, sig)),
    Scenario("storm, generator 24h, dry", LognormalOutage(48.0, sig), backup_hr_if_ok=24.0,
             p_backup_ok_nonflood=0.95, p_backup_ok_flood=0.4),
    Scenario("storm, generator 24h, flooded", LognormalOutage(48.0, sig), flooded=True, backup_hr_if_ok=24.0,
             p_backup_ok_nonflood=0.95, p_backup_ok_flood=0.4),
]
cfg = RunConfig(n=20000, seed=0, allow_placeholders=True)

print(f"{'scenario':34s} {'policy':>8s} {'physics':>8s} {'avoidable':>10s}   (conditional on an outage)")
for s in scenarios:
    r = run_scenario(s, cfg)
    print(f"{s.name:34s} {r['p_policy']:8.3f} {r['p_physics']:8.3f} {r['p_avoidable']:10.3f}")
