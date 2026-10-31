# Computational Epidemiology of Trastuzumab Cold-Chain Exposure During NYC Climate Disasters

## Research Question

**Within the tested parameter ranges, which uncertainties—flood-zone outage duration, inland outage duration, backup power, temperature, or treatment-fraction assumptions—contribute most to estimated trastuzumab cold-chain exposure risk in New York City?**

## Novelty and Contribution

This study develops and evaluates a drug-specific, time-to-failure framework for estimating chemotherapy cold-chain exposure during climate disasters. Unlike a binary flood overlay, the framework incorporates refrigerator thermal delay, trastuzumab stability, outage-duration uncertainty, and backup-power duration. It then translates those assumptions into scenario-specific exposure estimates and model-derived backup-power thresholds for emergency planning.

The individual methods used in this study—geographic information systems, thermal modeling, Monte Carlo simulation, and sensitivity analysis—are established techniques. The contribution is their integration into a focused framework for trastuzumab cold-chain exposure in New York City and the comparison of binary, thermal-only, and full time-to-failure assumptions.

This project estimates scenario-based exposure. It does not predict observed spoiled doses, document treatment interruptions, or validate physical failure counts.

## Methodology and Independence

- **Data engineering and pipeline:** I independently cleaned and merged CDC Social Vulnerability Index, CDC PLACES, American Community Survey, and NYC Open Data datasets using Python, GeoPandas, and Pandas.
- **Thermal and biological modeling:** I wrote the unified failure function combining a refrigerator thermal model with the selected trastuzumab stability assumption.
- **Monte Carlo simulation:** I designed a 1,000-iteration simulation using a fixed random seed of 42. The simulation varies refrigerator time constant, outdoor temperature, treatment fraction, and inland backup-power duration.
- **Sensitivity analysis:** I designed a one-way, or OAT, sensitivity analysis to evaluate how individual assumptions affect estimated citywide exposure within the tested parameter ranges.

## Model Structure

The model estimates exposure using:

```text
Estimated exposure = probability of product failure × estimated patient-equivalents
```

The full time-to-failure model estimates the failure threshold as:

```text
Total failure time = refrigerator time to exceed 8°C + trastuzumab stability window
```

For the primary scenario, the model uses a 3-hour trastuzumab stability window after the refrigerator exceeds 8°C. This is a modeling assumption based on the selected stability source and should not be interpreted as a universal handling rule for every formulation, concentration, or storage condition.

## Limitations

### Proxy denominator

The output is an estimated cancer-survivor-equivalent, not the number of active infusion patients, chemotherapy doses, vials, or documented treatment interruptions. The denominator is estimated from cancer prevalence and a treatment-fraction assumption.

### Facility versus census-tract exposure

Flood exposure is assigned at the census-tract level. This can conflate patient residence, pharmacy location, hospital location, inventory location, and generator elevation. The model assumes that all flood-zone facilities experience the flood scenario and that all non-flooded facilities share the inland outage distribution.

### Spatial plausibility check, not validation

The Sandy comparison is a retrospective spatial plausibility check. It shows that the model is consistent with higher modeled hazard in coastal flood-zone infrastructure, but it does not validate physical failure counts, spoiled doses, temperature trajectories, or predictive accuracy.

### Outage distributions

The model uses assumed lognormal outage-duration distributions with a 6.2-hour inland mean and a 72-hour flood-zone mean. These assumptions strongly influence the results and should be interpreted as scenario parameters rather than universal outage forecasts.

### Thermal model

The refrigerator model is a simplified lumped-capacitance model. It assumes a closed door and does not fully represent thermal ballast, inventory loading, door openings, refrigerator design differences, or facility-specific indoor conditions.

### Winter conditions

The winter scenario does not model vial freezing or damage caused by indoor temperatures falling below freezing. The near-zero winter failure result therefore depends on the assumption that indoor temperatures remain above the relevant cold-chain threshold.

### No observed-dose validation

Historical spoiled-dose records and facility-level temperature logs were not available for this study. The results should therefore be used for scenario comparison and screening, not operational pharmacy control.

## Key Findings

### 1. Three-model comparison

I compared three citywide frameworks to evaluate the contribution of refrigerator thermal delay and drug stability.

- **Naive immediate-failure upper bound:** Assumes every estimated patient-equivalent in the city is immediately exposed. Estimate: **57,999 patient-equivalents**.
- **Thermal-only model:** Accounts for refrigerator warming but assumes trastuzumab becomes unusable immediately after the refrigerator exceeds 8°C. Estimate: **44,306 patient-equivalents**.
- **Full time-to-failure model:** Accounts for both refrigerator thermal delay and the additional 3-hour trastuzumab stability window. Estimate: **31,325 patient-equivalents**.

Compared with the intentionally conservative citywide immediate-failure upper bound, the full model estimates **26,674 fewer patient-equivalents of exposure**, or a **46.0% lower estimate**. The thermal component accounts for approximately **13,694** of that difference, while adding the trastuzumab stability window accounts for an additional approximately **12,981**.

These are differences between modeled scenarios. They do not represent patients saved, observed false alarms, or documented treatment interruptions.

### 2. Flood-zone comparison

For flood-zone tracts only, the results are:

- **Naive flood-zone GIS baseline:** 17,121 patient-equivalents.
- **Thermal-only model:** 17,087 patient-equivalents.
- **Full time-to-failure model:** 16,801 patient-equivalents.

The full model is approximately **1.9% lower** than the naive flood-zone baseline. This small difference occurs because the assumed 72-hour flood outage is much longer than the approximately 5.5-hour modeled trastuzumab failure threshold. Under this severe scenario, outage duration dominates the refrigerator and drug-stability buffers.

### 3. Inland backup-power thresholds

Under the modeled 6.2-hour inland outage distribution, 30°C outdoor temperature, refrigerator parameters, and trastuzumab stability assumption:

- **2 hours** of backup power achieves at least a **25% reduction** in estimated inland exposure, with an observed modeled reduction of approximately 30.5%.
- **5 hours** achieves at least a **50% reduction**, with an observed modeled reduction of approximately 56.8%.
- **10 hours** achieves at least a **75% reduction**, with an observed modeled reduction of approximately 77.8%.

These are **model-derived planning thresholds**, not universal hospital requirements and not a formal cost-effectiveness analysis. They depend on the selected outage distribution, thermal parameters, outdoor temperature, treatment fraction, and drug-stability assumption.

### 4. One-way sensitivity analysis

The one-way sensitivity analysis evaluates each parameter individually while holding the other parameters at baseline values. It cannot prove global dominance or causal importance.

Within the tested parameter ranges, treatment fraction is the largest overall driver because it scales the estimated denominator. Among operational hazard variables, inland outage duration and inland backup power have the largest effects on citywide estimated exposure.

The sensitivity results are available in:

```text
figures/sensitivity_results.csv
```

## Expected Outputs

- `figures/final_risk_map.png` — Spatial distribution of scenario-based exposure.
- `figures/sensitivity_tornado.png` — One-way/OAT sensitivity-analysis plot.
- `figures/sensitivity_results.csv` — Numerical sensitivity results containing low, baseline, high, and range values.
- `figures/monte_carlo_results.csv` — Auditable 1,000-iteration simulation data, including sampled inputs and calculated risks.
- `figures/svi_map_clean.png` — SVI visualization with data-quality annotations.
- `figures/cancer_map.png` — Census-tract cancer-prevalence visualization.

## Data and Reproducibility

Large input files are excluded from Git. To reproduce the pipeline from a fresh clone, download the following datasets into the `raw_data/` directory using the expected filenames:

| Dataset | Source / Version | Expected filename |
|---|---|---|
| NYC Census Tracts | NYC Open Data, 2020 | `2020_Census_Tracts_20261016.geojson` |
| CDC Social Vulnerability Index | CDC SVI 2022, New York census tracts | `svi_ny_tract_2022.csv` |
| CDC PLACES | CDC PLACES 2024, crude cancer prevalence | `places_nyc_full.csv` |
| ACS Population | U.S. Census ACS 2024, Table B01001 | `acs_b01001_ny_tracts.csv` |
| Sandy Flood Zones | NYC Open Data | `flood.geojson` |

### Execution steps

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python notebooks/explore.py
python notebooks/coldchain.py
```

The preprocessing script creates:

```text
raw_data/tracts_full.geojson
```

The modeling script then loads that file, applies the flood-zone layer, runs the thermal and risk calculations, performs the hospital plausibility check, runs the Monte Carlo simulation, and produces the figures and CSV outputs.

## References

1. Agency for Toxic Substances and Disease Registry. (2022). *Social Vulnerability Index.* https://www.atsdr.cdc.gov/place-health/php/svi/svi-data-documentation-download.html
2. Centers for Disease Control and Prevention. (2024). *PLACES: Local Data for Better Health, Census Tract Data.* https://chronicdata.cdc.gov/500-Cities-Places/PLACES-Local-Data-for-Better-Health-Census-Tract-D/ai6z-tcin
3. U.S. Census Bureau. (2024). *American Community Survey 5-Year Estimates, Table B01001.* https://data.census.gov
4. National Institute of Standards and Technology. (2009). *Thermal Analysis of Refrigeration Systems Used for Vaccine Storage* (NISTIR 7656). Chojnacky, M., Miller, W., Ripple, D., & Strouse, G. U.S. Department of Commerce. https://doi.org/10.6028/NIST.IR.7656
5. French Society of Oncology Pharmacy. *STABILIS Drug Stability Database.* https://www.stabilis.org
6. NYC Open Data. *Sandy Inundation Zones.* https://data.cityofnewyork.us/Environment/Sandy-Inundation-Zone/uyj8-7rv5
7. New York State Department of Public Service. (2023). *2022 Electric Service Reliability Report* (Case 23-E-0225). Con Edison Network System CAIDI: 6.23 hours. https://pl.dps.ny.gov/system/files/documents/2023/08/electric-service-reliability-report-2022.pdf