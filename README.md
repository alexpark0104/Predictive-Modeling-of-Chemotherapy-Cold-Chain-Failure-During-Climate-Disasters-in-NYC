# Predictive Modeling of Trastuzumab Cold-Chain Failure During Climate Disasters in New York City

## Overview
This repository contains a multi-hazard, physics-based computational model I built to generate **scenario-based patient-equivalent exposure estimates** for Trastuzumab (a temperature-sensitive chemotherapy drug) during climate disasters in New York City. 

*Note: This repository does not predict observed spoiled doses. It estimates the scale of potential exposure using demographic proxies.*

## Core Methodology
I compute risk using the following formula:
`ColdChainRisk = P(outage > total_time_to_failure) × chemo_survivor_equivalents`

1. **Unified Failure Function:** `total_time_to_failure` is calculated by combining the time for a pharmacy fridge to breach 8°C (lumped-capacitance thermal model) with the specific biological degradation time of Trastuzumab (3 hours at room temp).
2. **Probabilistic Hazard:** I applied lognormal distributions of power outage durations (6.2h mean inland, 72h mean for flood zones).
3. **Geospatial Vulnerability:** I integrated the CDC Social Vulnerability Index (SVI), PLACES cancer prevalence, Census ACS adult population, and NYC Open Data Sandy Inundation Zones.
4. **Monte Carlo Simulation:** I ran a 1,000-iteration simulation (seed = `42`) drawing from uniform distributions for fridge insulation (10–14h), outdoor temperature (25–35°C), and inland backup power (0–24h). Flood-zone tracts are forced to 0h backup. All sampled parameters are exported to `monte_carlo_results.csv` for auditability.

## EXPLICIT ASSUMPTIONS & LIMITATIONS

### 1. Patient-Equivalent Proxies
*   **Limitation:** The output represents **estimated cancer-survivor-equivalents**, not active infusion patients. I multiplied CDC PLACES prevalence (ever-diagnosed) by a 15% treatment fraction to approximate the denominator.

### 2. Facility vs. Tract Exposure (Ecological Fallacy)
*   **Limitation:** Flood exposure is assigned at the census-tract level. This conflates patient residence, pharmacy location, and generator elevation. The model assumes all flooded generators fail and all non-flooded facilities share one inland outage distribution.

### 3. Spatial Plausibility Check (Not Validation)
*   **Limitation:** I performed a **retrospective spatial plausibility check** against Hurricane Sandy, not a full validation. Because observed temperature logs and spoiled-dose records are unavailable, I did not report predictive accuracy. The model dynamically calculates an **~98.1% failure probability** for the tracts containing NYU Langone, Bellevue, and Coney Island Hospital, compared to **~35.5%** for inland control hospitals (Mount Sinai, Montefiore). This confirms the model correctly identifies high-hazard coastal infrastructure.

### 4. Qualified Winter Conclusion
*   **Limitation:** The model shows near-zero cold-chain failure during winter storms, assuming indoor temperatures do not drop below 8°C. Total heating failure could freeze and crack vials, which this thermal model does not capture.

## Expected Output Files
*   `figures/final_risk_map.png`: Risk map overlaid with the Sandy flood inundation zones.
*   `figures/monte_carlo_results.csv`: Machine-readable 1,000-iteration simulation output (includes sampled inputs and risks).
*   `figures/svi_map_clean.png`: NYC Social Vulnerability Index.

## Reproducibility & Data Provenance
To reproduce this pipeline from a fresh clone, download the following datasets into a `raw_data/` folder:

| Dataset | Direct Source URL | Expected Filename | Rows | CRS |
| :--- | :--- | :--- | :--- | :--- |
| NYC Census Tracts | [NYC Open Data](https://data.cityofnewyork.us/City-Government/2020-Census-Tracts/63ge-mke6) | `2020_Census_Tracts_20261016.geojson` | 2,325 | EPSG:4326 |
| CDC SVI (NY) | [CDC SVI Download](https://www.atsdr.cdc.gov/place-health/php/svi/svi-data-documentation-download.html) | `svi_ny_tract_2022.csv` | 5,394 | N/A |
| CDC PLACES | [CDC PLACES 2024](https://chronicdata.cdc.gov/500-Cities-Places/PLACES-Local-Data-for-Better-Health-Census-Tract-D/ai6z-tcin) | `places_nyc_full.csv` | ~3.1M | N/A |
| ACS Population | [Census Data](https://data.census.gov) (Table B01001) | `acs_b01001_ny_tracts.csv` | 5,397 | N/A |
| Sandy Flood Zones | [NYC Open Data](https://data.cityofnewyork.us/Environment/Sandy-Inundation-Zone/uyj8-7rv5) | `flood.geojson` | 588 tracts | EPSG:4326 |

1. `python3 -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. `python notebooks/explore.py` (Builds `raw_data/tracts_full.geojson`)
4. `python notebooks/coldchain.py` (Runs thermal model, Monte Carlo, and plausibility check)