# Predictive Modeling of Chemotherapy Cold-Chain Failure During Climate Disasters in New York City

## 📖 Overview
This repository contains a multi-hazard, physics-based computational model I built to predict census-tract-level risks of chemotherapy cold-chain failure during climate disasters in New York City. 

While traditional disaster planning maps physical hazards, my model maps **biological and infrastructural failure**. It calculates the time required for a pharmacy refrigerator to breach the 8°C safety threshold, adds the specific biological degradation time of the drug, and models the probability of power outages overwhelming hospital backup generators.

## 🔬 Core Methodology
I compute risk using the following formula:
`ColdChainRisk = P(outage > total_time_to_failure) × active_chemo_patients_proxy`

1. **Thermal Physics:** I used a lumped-capacitance thermal model calibrated to NIST data to calculate how fast a pharmacy fridge warms up during a blackout.
2. **Biological Constraints:** I integrated drug-specific stability data from the STABILIS database. Because drugs degrade at different rates, the model calculates `total_time_to_failure = time_to_8C + drug_survival_time`. (e.g., Trastuzumab survives only 3 hours at room temp, while Rituximab survives 15 days).
3. **Probabilistic Hazard:** I applied lognormal distributions of power outage durations based on ConEd CAIDI data (6.2h mean for inland blackouts, 72h mean for hurricane flood zones).
4. **Geospatial Vulnerability:** I integrated the CDC Social Vulnerability Index (SVI), PLACES cancer prevalence, Census ACS adult population, and NYC Open Data Sandy Inundation Zones.
5. **Monte Carlo Simulation:** I ran a 1,000-iteration simulation (using a fixed seed of `42` for reproducibility) drawing from uniform distributions for fridge insulation (10–14h), outdoor temperature (25–35°C), and inland backup power (0–24h). For tracts intersecting the flood zone, backup power is forced to 0h to simulate flooded generator basements.

---

## ⚠️ EXPLICIT ASSUMPTIONS & LIMITATIONS

This model is an academic screening tool, **not an operational pharmacy-control system**. 

### 1. Proxy Estimates (Patient-Equivalents)
*   **Limitation:** The output `ColdChainRisk` represents **estimated patient-equivalents**, not confirmed spoiled vials or documented treatment interruptions. I used CDC PLACES data (ever-diagnosed cancer survivors) and multiplied by a 15% treatment fraction (bounded 10–25%) to approximate active infusion patients.

### 2. No Primary Survey Data
*   **Limitation:** Because I could not obtain survey data from NYC infusion centers, I used a Monte Carlo simulation to randomly vary backup power from 0 to 24 hours for inland facilities. This provides a confidence interval, not a point estimate.

### 3. The Physics of the Fridge
*   **Limitation:** I used a first-order lumped-capacitance thermal model. It assumes the door remains closed and does not account for thermal ballast. 

### 4. Qualified Winter Conclusion
*   **Limitation:** The model shows near-zero cold-chain failure during winter storms. **This assumes building heating remains functional or ambient indoor temperatures do not drop below 8°C.** In a total heating failure during a blizzard, indoor temperatures could drop below freezing, causing physical disruption to the drug vials (cracking), which this thermal model does not capture.

### 5. Retrospective Spatial Plausibility Check (Sandy)
*   **Limitation:** I backtested the model against Hurricane Sandy (2012). Because historical data on exact spoiled chemotherapy doses is unavailable, **this is a spatial plausibility check, not an observed-count validation**. The model successfully assigned a 99.6% failure probability to the tracts containing NYU Langone, Bellevue, and Coney Island Hospital (which suffered catastrophic generator failures), compared to 66.6% for inland control hospitals (Mount Sinai, Montefiore).

---

## 📂 Expected Output Files
Running `coldchain.py` and `explore.py` will generate the following files in the `figures/` directory:
*   `svi_map_clean.png`: NYC Social Vulnerability Index with reconstructed tract hatching.
*   `cancer_map.png`: Cancer prevalence by census tract.
*   `coldchain_risk_baseline.png`: Baseline cold-chain risk during a standard summer blackout.
*   `coldchain_risk_flood.png`: Risk map overlaid with the Sandy flood inundation zones.
*   `monte_carlo_sensitivity.png`: Histogram of 1,000 simulation runs.

## 💻 Setup & Reproducibility
1. Clone the repo.
2. Ensure you have Python 3.10+ installed.
3. Create a virtual environment: `python3 -m venv .venv`
4. Activate it: `source .venv/bin/activate`
5. Install dependencies: `pip install -r requirements.txt`
6. Download the raw data into a `raw_data/` folder (See Data Sources below, as files exceed GitHub limits).
7. Run `python notebooks/explore.py`
8. Run `python notebooks/coldchain.py`

## 📚 Data Sources & Versions
*   **CDC SVI 2022:** [Download Link](https://www.atsdr.cdc.gov/place-health/php/svi/svi-data-documentation-download.html) (Census Tract level).
*   **CDC PLACES 2024:** [Download Link](https://chronicdata.cdc.gov/500-Cities-Places/PLACES-Local-Data-for-Better-Health-Census-Tract-D/ai6z-tcin) (Crude prevalence).
*   **US Census ACS 2024:** [Download Link](https://data.census.gov) (Table B01001 - Sex by Age).
*   **NYC Open Data:** [Sandy Inundation Zones](https://data.cityofnewyork.us/Environment/Sandy-Inundation-Zone/uyj8-7rv5).
*   **STABILIS Database:** [Drug Stability Data](https://www.stabilis.org).
*   **NY DPS:** [ConEd Reliability Reports](https://documents.dps.ny.gov).