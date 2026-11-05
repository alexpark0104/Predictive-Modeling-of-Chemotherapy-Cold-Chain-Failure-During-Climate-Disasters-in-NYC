# coldchain-nyc

Scenario-based model of oncology-biologic cold-chain loss during urban power outages, using trastuzumab in
New York City as the case. **Status: v0.2 rewrite in progress. No results are reported yet.**

## Question
How much refrigerated-biologic loss in blackouts reflects real degradation, and how much reflects discard policy?

## What this is not
Not a prediction, not an operational tool, and not annual risk. Outputs are conditional on an outage occurring.

## Layout
```
src/coldchain/   thermal.py (fridge ODE), degradation.py (policy vs physics rules), outage.py,
                 failure.py (facility Monte Carlo), params.py (parameter registry with provenance)
tests/           unit tests (analytic checks, monotonicity, reproducibility)
scripts/         demo.py (ILLUSTRATIVE), make_manifest.py (data checksums)
docs/            ANALYSIS_PLAN.md
data/README.md   dataset provenance registry (raw data are not committed)
legacy/          v0.1 prototype scripts, unchanged
```

## Quickstart
```
pip install -e ".[dev]"
pytest -q
python scripts/demo.py     # illustrative only; uses placeholder parameters
```

## Principles
1. Every input has a provenance status; placeholders block reporting (`assert_publishable()`).
2. Policy loss and physics loss are computed side by side; the gap between them is the object of study.
3. Anything not validated is labeled as an assumption.
