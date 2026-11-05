# Analysis plan (draft - finalize BEFORE running reported analyses)

Version: 0.1 draft. Freeze a dated copy (tag or Zenodo) before generating any number you intend to report.

## Question
How much oncology-biologic loss (trastuzumab as the case) during urban power outages reflects real
degradation, and how much reflects discard policy?

## Research questions
- RQ1: Fraction of unopened inventory lost under (a) a strict label rule and (b) a kinetic degradation budget.
- RQ2: Effect of flood-correlated backup failure vs independent failure on facility-level risk.
- RQ3: Which inputs flip the conclusion (global sensitivity).
- RQ4 (pick one later): mitigation counterfactuals OR equity analysis.

## Estimand and framing
Probabilities are conditional on an outage occurring at a facility. They are exposure-style estimates for
unopened refrigerated inventory, not patient outcomes and not annual risk.

## Rules the code enforces
- Every input lives in `src/coldchain/params.py` with a status (SOURCED / ANCHORED / ASSUMED / PLACEHOLDER).
- `assert_publishable()` must pass before any reported number is generated: no placeholders.
- Seeds are fixed and recorded with every output.

## Inputs to replace (priority order)
1. Activation energy and degradation budget from trastuzumab kinetic/excursion data (read primary sources).
2. Outage-duration distribution fitted to EAGLE-I / utility data, by event and network type.
3. Backup-power probabilities by facility type, with flood-conditional failure.
4. Active-patient denominator from registry data (for the exposure-weighting step).

## Sensitivity analysis
Global variance-based (Sobol) on loss probability; report first-order and total-effect indices; run structural
choices (policy rule, budget range, Ea) as explicit scenarios.

## Validation
Component-level checks (outage durations vs Sandy/2003 records; backup failure vs documented hospital events).
State plainly where validation is qualitative.

## Stopping rules / what would change the plan
Write these down before results exist (e.g., if budget range spans orders of magnitude and drives >X% of
variance, report conclusions as conditional rather than point estimates).
