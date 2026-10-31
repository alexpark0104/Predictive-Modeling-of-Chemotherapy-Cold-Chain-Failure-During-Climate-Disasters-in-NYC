import streamlit as st
import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from scipy import stats

st.set_page_config(layout="wide")
st.title("ColdChain Shield NYC")
st.markdown("A decision-support tool to estimate Trastuzumab cold-chain exposure during disasters.")

# Load data (handles both root and notebooks/ folder)
ROOT = Path(__file__).resolve().parent
if not (ROOT / "raw_data").exists():
    ROOT = ROOT.parent
tracts = gpd.read_file(ROOT / "raw_data" / "tracts_full.geojson")

# ---------- SIDEBAR CONTROLS ----------
st.sidebar.header("Scenario Parameters")
outage = st.sidebar.slider("Outage Duration (hours)", 2, 120, 72)
backup = st.sidebar.slider("Backup Power (hours)", 0, 48, 0)
drug_stability = st.sidebar.slider("Drug Stability at Room Temp (hours)", 1, 24, 3)
treatment_frac = st.sidebar.slider("Active Treatment Fraction (%)", 5, 30, 15) / 100.0

# ---------- REAL MATH ----------
def calculate_prob(mean_outage_hrs, backup_hrs, drug_stability_hrs):
    # 1. Fridge thermal model (simplified for speed)
    t = np.arange(0, 168 * 60, 5.0) # 5-min steps
    T = np.zeros_like(t)
    mask = t < backup_hrs * 60
    T[mask] = 4.0
    after = ~mask
    t_after = (t[after] - backup_hrs * 60) / 60
    T_indoor = 30.0 - (30.0 - 22.0) * np.exp(-t_after / 4.0)
    T[after] = T_indoor - (T_indoor - 4.0) * np.exp(-t_after / 12.0)
    
    breach = np.where(T > 8.0)[0]
    t_breach = t[breach[0]] / 60 if len(breach) > 0 else 168.0
    
    # 2. Total time to failure
    t_total_failure = t_breach + drug_stability_hrs
    
    # 3. Probability
    sigma = 1.0
    mu = np.log(mean_outage_hrs) - 0.5 * sigma**2
    return 1 - stats.lognorm.cdf(t_total_failure, s=sigma, scale=np.exp(mu))

# Calculate probabilities dynamically based on sliders
prob_flood = calculate_prob(outage, 0.0, drug_stability) # Flood = 0 backup
prob_inland = calculate_prob(outage, backup, drug_stability)

# Apply to tracts
tracts["chemo_survivor_equivalents"] = tracts["est_cancer_patients"] * treatment_frac
tracts["risk"] = np.where(
    tracts["in_flood_zone"],
    prob_flood * tracts["chemo_survivor_equivalents"],
    prob_inland * tracts["chemo_survivor_equivalents"]
)

total_risk = int(tracts["risk"].sum())

# ---------- DISPLAY METRICS ----------
col1, col2, col3 = st.columns(3)
col1.metric("Citywide Exposure (Patients)", f"{total_risk:,}")
col2.metric("Coastal Failure Prob", f"{prob_flood*100:.1f}%")
col3.metric("Inland Failure Prob", f"{prob_inland*100:.1f}%")

# ---------- PLOT MAP ----------
fig, ax = plt.subplots(1, 1, figsize=(10, 10))

# Set a fixed maximum for the color scale so we can see the map change!
# 1000 is a good number so the map isn't always maxed out in red.
FIXED_VMAX = 1000 

tracts.plot(
    column="risk", 
    cmap="Reds", 
    legend=True, 
    ax=ax, 
    edgecolor="black", 
    linewidth=0.1,
    vmin=0,
    vmax=FIXED_VMAX  # <--- LOCKING THE COLOR SCALE
)

# Overlay the flood zones so you can see where the blue outline is
# (If your tracts dataframe has the flood data, this draws it)
if "in_flood_zone" in tracts.columns:
    tracts[tracts["in_flood_zone"]].plot(ax=ax, color="none", edgecolor="blue", linewidth=0.5)

ax.set_title(f"Estimated Patient-Equivalent Risk (Max Scale = {FIXED_VMAX})")
ax.set_axis_off()
st.pyplot(fig)