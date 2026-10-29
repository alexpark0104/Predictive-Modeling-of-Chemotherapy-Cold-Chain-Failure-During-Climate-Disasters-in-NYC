# Predictive Modeling of Chemotherapy Cold-Chain Failure During Climate Disasters in New York City

## Overview
This repository contains a multi-hazard, physics-based computational model I built to predict census-tract-level risks of chemotherapy cold-chain failure during climate disasters (floods, hurricanes, and blackouts) in New York City. 

While traditional disaster planning maps physical hazards (e.g., flood zones), my model maps **biological and infrastructural failure**. It calculates the time required for a pharmacy refrigerator to breach the 8°C safety threshold, compares it against specific drug degradation curves, and models the probability of power outages overwhelming hospital backup generators.

## Core Methodology
I compute risk using the following formula:
`ColdChainRisk = P(outage > time_to_8C) × active_chemo_patients_proxy`

1. **Thermal Physics:** I used a lumped-capacitance thermal model calibrated to NIST data to calculate how fast a pharmacy fridge warms up during a blackout.
2. **Biological Constraints:** I integrated drug-specific stability data (from STABILIS) to determine viability (e.g., Trastuzumab degrades in 3 hours at room temp; Rituximab survives for 15 days).
3. **Probabilistic Hazard:** I applied lognormal distributions of power outage durations (based on ConEd CAIDI data).
4. **Geospatial Vulnerability:** I integrated the CDC Social Vulnerability Index (SVI), PLACES cancer prevalence, Census ACS adult population, and Sandy Inundation Zones.
5. **Statistical Robustness:** I ran a 1,000-iteration Monte Carlo simulation to handle parameter uncertainty.

---

## EXPLICIT ASSUMPTIONS & LIMITATIONS (READ CAREFULLY)

This model is an academic screening tool, **not an operational pharmacy-control system**. It contains deliberate simplifications and assumptions due to data availability constraints. 

### 1. Proxy Estimates for Active Chemotherapy Population
*   **Assumption:** I used CDC PLACES data for cancer prevalence, which estimates *ever-diagnosed* cancer survivors. To estimate the population on *active* chemotherapy, I multiplied total survivors by a **15% treatment fraction** (bounded between 10% and 25% in my sensitivity analysis).
*   **Limitation:** These patient counts are **demographic proxy estimates**. I do not have tract-level data on active infusion schedules. 

### 2. The Missing Primary Data (No Survey)
*   **Assumption:** Because I could not obtain primary survey data from NYC infusion centers regarding their exact generator capacity and fuel status due to privacy and logistical constraints, I did not guess a single value.
*   **Limitation:** Instead, I used a **1,000-run Monte Carlo simulation** that randomly varies backup power from 0 to 24 hours. This provides a confidence interval rather than a point estimate, but it does not replace actual hospital infrastructure audits.

### 3. The Physics of the Fridge
*   **Assumption:** I used a first-order lumped-capacitance thermal model (tau = 12 hours). It assumes the fridge door remains closed during the outage and does not account for thermal ballast (e.g., water bottles) or specific fridge brands.
*   **Limitation:** This is a generalized physics model. A poorly maintained fridge will fail faster; a modern, highly insulated fridge will fail slower.

### 4. Outage Duration Modeling
*   **Assumption:** For tracts inland, the model assumes a 6.2-hour outage (ConEd summer average). For tracts intersecting the Sandy Flood Zone, the model assumes a catastrophic 72-hour outage.
*   **Limitation:** This is a geographic hazard trigger. In reality, a coastal hospital with a 14th-floor generator (like Bellevue) might have power, but lose it anyway due to flooded basement fuel pumps. I model the *probability* of systemic failure, not specific mechanical failures.

### 5. Retrospective Spatial Backtest (Sandy)
*   **Assumption:** I backtested the model against Hurricane Sandy (2012). Because historical data on the exact number of spoiled chemotherapy doses is unavailable, **this is a spatial backtest, not an observed-count validation**. 
*   **Limitation:** I validated the model's spatial prediction of hospital infrastructure failure, not the physical count of ruined vials. The model successfully assigned a 99.6% cold-chain failure probability to the tracts containing NYU Langone, Bellevue, and Coney Island Hospital (which evacuated), and a 66.6% probability to inland control hospitals (Mount Sinai, Montefiore).

---

## Key Findings
1. **Winter blackouts are safe:** At 5°C outdoor, the ambient temperature acts as a natural refrigerator; the fridge never breaches 8°C.
2. **24-hour backup power is insufficient:** During a 72-hour hurricane outage, a 24-hour generator still results in a ~68% cold-chain failure rate.
3. **Infrastructure inequality drives risk:** The Monte Carlo 95% Confidence Interval for citywide risk is vast (1,491 to 39,290 patients). The presence or absence of a functioning generator is the dominant variable, not the weather.

## Setup & Reproducibility
1. Clone the repo.
2. Ensure you have Python 3.10+ installed.
3. Create a virtual environment: `python3 -m venv .venv`
4. Activate it: `source .venv/bin/activate`
5. Install dependencies: `pip install -r requirements.txt`
6. Download the raw data into `raw_data/` (See the "Data Sources" section below for links, as files exceed GitHub limits).
7. Run `python notebooks/explore.py` to build the demographic baseline.
8. Run `python notebooks/coldchain.py` to execute the thermal model, flood overlay, Monte Carlo, and Sandy validation.

## Data Sources
*   **CDC SVI 2022** (Social Vulnerability Index)
*   **CDC PLACES 2024** (Cancer Prevalence)
*   **US Census ACS 2024** (Table B01001 - Sex by Age)
*   **NYC Open Data** (Sandy Inundation Zones)
*   **NIST** (Refrigerator Thermal Dynamics)
*   **STABILIS Database** (Drug Stability / Degradation Data)
*   **NY DPS** (ConEd Outage Reliability / CAIDI)