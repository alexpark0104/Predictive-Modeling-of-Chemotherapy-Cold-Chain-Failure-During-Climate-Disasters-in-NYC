# Predictive Modeling of Chemotherapy Cold-Chain Failure During Climate Disasters in New York City

## Overview
This repository contains a multi-hazard, physics-based computational model I built to generate **scenario-based patient-equivalent exposure estimates** for chemotherapy cold-chain failure during climate disasters in New York City. 

*Note: This repository does not predict observed spoiled doses. It estimates the scale of potential exposure using demographic proxies.*

## Core Methodology
I compute risk using the following formula:
`ColdChainRisk = P(outage > total_time_to_failure) × chemo_survivor_equivalents`

1. **Unified Failure Function:** `total_time_to_failure` is calculated by combining the time for a pharmacy fridge to breach 8°C (lumped-capacitance thermal model) with the specific biological degradation time of the drug (e.g., Trastuzumab degrades in 3 hours at room temp).
2. **Probabilistic Hazard:** I applied lognormal distributions of power outage durations (6.2h mean inland, 72h mean for flood zones).
3. **Geospatial Vulnerability:** I integrated the CDC Social Vulnerability Index (SVI), PLACES cancer prevalence, Census ACS adult population, and NYC Open Data Sandy Inundation Zones.
4. **Monte Carlo Simulation:** I ran a 1,000-iteration simulation (seed = `42`) drawing from uniform distributions for fridge insulation (10–14h), outdoor temperature (25–35°C), and inland backup power (0–24h). Flood-zone tracts are forced to 0h backup (simulating flooded basements).

## EXPLICIT ASSUMPTIONS & LIMITATIONS

### 1. Patient-Equivalent Proxies
*   **Limitation:** The output represents **estimated cancer-survivor-equivalents**, not active infusion patients. I multiplied CDC PLACES prevalence (ever-diagnosed) by a 15% treatment fraction to approximate the denominator.

### 2. Facility vs. Tract Exposure (Ecological Fallacy)
*   **Limitation:** Flood exposure is assigned at the census-tract level. This conflates patient residence, pharmacy location, and generator elevation. The model assumes all flooded generators fail and all non-flooded facilities share one inland outage distribution.

### 3. Spatial Plausibility Check (Not Validation)
*   **Limitation:** I performed a **retrospective spatial plausibility check** against Hurricane Sandy, not a full validation. Because observed temperature logs and spoiled-dose records are unavailable, I did not report predictive accuracy. The model dynamically calculates a ~99.6% failure probability for the tracts containing NYU Langone, Bellevue, and Coney Island Hospital, compared to ~66.6% for inland control hospitals. This confirms the model correctly identifies high-hazard coastal infrastructure, but does not confirm exact physical failure counts.

### 4. Qualified Winter Conclusion
*   **Limitation:** The model shows near-zero cold-chain failure during winter storms. This assumes indoor ambient temperatures do not drop below 8°C. A total heating failure during a blizzard could freeze and crack vials, which this thermal model does not capture.

## Expected Output Files
*   `figures/final_risk_map.png`: Risk map overlaid with the Sandy flood inundation zones.
*   `figures/monte_carlo_results.csv`: Machine-readable 1,000-iteration simulation output (Total_Risk and Flood_Risk columns).
*   `figures/svi_map_clean.png`: NYC Social Vulnerability Index.

## Reproducibility & Data Provenance
To reproduce this pipeline from a fresh clone, download the following datasets into a `raw_data/` folder:

| Dataset | Source / Version | Expected Filename | Rows | CRS |
| :--- | :--- | :--- | :--- | :--- |
| NYC Census Tracts | NYC Open Data (2020) | `2020_Census_Tracts.geojson` | 2,325 | EPSG:4326 |
| CDC SVI | CDC 2022 (NY, Tract) | `svi_ny_tract_2022.csv` | 5,394 | N/A |
| CDC PLACES | CDC 2024 (Crude Prev) | `places_nyc_full.csv` | ~3.1M | N/A |
| ACS Population | Census 2024 (B01001) | `acs_b01001_ny_tracts.csv` | 5,397 | N/A |
| Sandy Flood Zones | NYC Open Data | `flood.geojson` | 588 tracts | EPSG:4326 |

1. `python3 -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. `python notebooks/explore.py` (Builds `raw_data/tracts_full.geojson`)
4. `python notebooks/coldchain.py` (Runs thermal model, Monte Carlo, and plausibility check)