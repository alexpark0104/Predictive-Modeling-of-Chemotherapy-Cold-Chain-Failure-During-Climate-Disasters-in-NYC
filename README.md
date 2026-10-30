# Computational Epidemiology of Trastuzumab Cold-Chain Exposure During NYC Climate Disasters

## Research Question
**Within the tested parameter ranges, which uncertainties—flood-zone outage duration, inland outage duration, backup power, temperature, or treatment-fraction assumptions—contribute most to estimated trastuzumab cold-chain exposure risk in NYC?**

## 🔬 Overview
This repository contains a scenario-based computational epidemiology model. It estimates patient-equivalent exposure to trastuzumab cold-chain failure during climate disasters in NYC. 

*Note: This model estimates scenario-based exposure under explicitly stated assumptions. It does not predict observed spoiled doses or validate physical failure counts.*

## Methodology & Independence
*   **Data Engineering & Pipeline:** I independently cleaned and merged CDC SVI, PLACES, ACS, and NYC Open Data using Python (GeoPandas, Pandas). 
*   **Thermal/Biological Modeling:** I wrote the unified failure function combining a NIST-calibrated thermal model with STABILIS drug degradation data. 
*   **Monte Carlo & Sensitivity:** I designed the 1,000-iteration Monte Carlo (seed=42) and the One-Way (OAT) Sensitivity Analysis to rank assumption influence. 
*   **AI Disclosure:** AI tools were used to assist with code syntax, debugging, and formatting. The epidemiological framing, parameter selection, and validation design were independently conceived by me. A dated research log is maintained externally.

## LIMITATIONS
*   **Proxy Denominators:** The output is an estimated cancer-survivor-equivalent, not active infusion volume.
*   **Facility vs. Tract:** Flood exposure is applied at the census-tract level, conflating patient residence and pharmacy location.
*   **Plausibility, Not Validation:** The Sandy check shows the model is *consistent* with high-hazard coastal infrastructure but does not validate physical failure counts or predictive accuracy.
*   **OAT Sensitivity Limitations:** The one-way sensitivity analysis tests parameters individually and cannot prove global dominance or causal importance.

## Key Findings
1.  **The Dominant Variables:** Within the tested parameter ranges, the One-Way Sensitivity Analysis identifies **Inland Backup Power** and **Inland Outage Duration** as the largest drivers of citywide estimated exposure. 
2.  **Coastal vs. Inland:** The model assigns a 98.1% failure probability to coastal flood-zone tracts and a 35.5% failure probability to inland tracts.
3.  **The 24-Hour Illusion:** A 24-hour backup generator during a 72-hour hurricane outage still results in significant cold-chain exposure.

## Expected Outputs
*   `figures/final_risk_map.png`: Spatial distribution of risk.
*   `figures/sensitivity_tornado.png`: One-Way (OAT) Sensitivity Analysis plot.
*   `figures/sensitivity_results.csv`: Numerical data for the Tornado plot.
*   `figures/monte_carlo_results.csv`: Auditable 1,000-run simulation data.

## Data and Reproducibility
To reproduce this pipeline from a fresh clone, download the following datasets into a `raw_data/` folder (large files are excluded from Git):

| Dataset | Source / Version | Expected Filename |
| :--- | :--- | :--- |
| NYC Census Tracts | NYC Open Data (2020) | `2020_Census_Tracts_20261016.geojson` |
| CDC SVI | CDC 2022 (NY, Tract) | `svi_ny_tract_2022.csv` |
| CDC PLACES | CDC 2024 (Crude Prev) | `places_nyc_full.csv` |
| ACS Population | Census 2024 (B01001) | `acs_b01001_ny_tracts.csv` |
| Sandy Flood Zones | NYC Open Data | `flood.geojson` |

**Execution Steps:**
1. `python3 -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. `python notebooks/explore.py`
4. `python notebooks/coldchain.py`

## References
*   **CDC SVI:** Agency for Toxic Substances and Disease Registry (2022). Social Vulnerability Index.
*   **CDC PLACES:** Centers for Disease Control and Prevention (2024). Local Data for Better Health.
*   **US Census ACS:** United States Census Bureau (2024). American Community Survey 5-Year Estimates.
*   **NIST:** National Institute of Standards and Technology. Refrigerator Thermal Dynamics.
*   **STABILIS:** French Society of Oncology Pharmacy. Drug Stability Database.
*   **NY DPS:** New York Department of Public Service. ConEd Outage Reliability Reports (CAIDI).