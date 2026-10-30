# Computational Epidemiology of Trastuzumab Cold-Chain Exposure During NYC Climate Disasters

## Research Question
**Which uncertainties—flood exposure, outage duration, backup power, temperature, or treatment-fraction assumptions—contribute most to estimated trastuzumab cold-chain exposure risk in NYC?**

## Overview
This repository contains a scenario-based computational epidemiology model. It estimates patient-equivalent exposure to trastuzumab cold-chain failure during climate disasters in NYC. 

*Note: This model estimates scenario-based exposure under explicitly stated assumptions. It does not predict observed spoiled doses or validate physical failure counts.*

## Methodology & Independence
*   **Data Engineering & Pipeline:** I independently cleaned and merged CDC SVI, PLACES, ACS, and NYC Open Data using Python (GeoPandas, Pandas). 
*   **Thermal/Biological Modeling:** I wrote the unified failure function combining a NIST-calibrated thermal model with STABILIS drug degradation data. 
*   **Monte Carlo & Sensitivity:** I designed the 1,000-iteration Monte Carlo (seed=42) and the Global Sensitivity Analysis (Tornado Plot) to rank assumption influence. AI tools were used to assist with code syntax and debugging, but the epidemiological framing, parameter selection, and validation design were my own.

## LIMITATIONS
*   **Proxy Denominators:** The output is an estimated cancer-survivor-equivalent, not active infusion volume.
*   **Facility vs. Tract:** Flood exposure is applied at the census-tract level, conflating patient residence and pharmacy location.
*   **Plausibility, Not Validation:** The Sandy check shows the model is *consistent* with high-hazard coastal infrastructure but does not validate physical failure counts.

## Key Findings
1.  **The Dominant Variable:** The Global Sensitivity Analysis proves that **Inland Backup Power** and **Inland Outage Duration** drive the vast majority of citywide risk. Flood zones are catastrophic but geographically contained.
2.  **Coastal vs. Inland:** The model assigns a 98.1% failure probability to coastal flood-zone tracts and a 35.5% failure probability to inland tracts.
3.  **The 24-Hour Illusion:** A 24-hour backup generator during a 72-hour hurricane outage still results in significant cold-chain exposure.

## Expected Outputs
*   `figures/final_risk_map.png`: Spatial distribution of risk.
*   `figures/sensitivity_tornado.png`: Global Sensitivity Analysis.
*   `figures/monte_carlo_results.csv`: Auditable 1,000-run simulation data.