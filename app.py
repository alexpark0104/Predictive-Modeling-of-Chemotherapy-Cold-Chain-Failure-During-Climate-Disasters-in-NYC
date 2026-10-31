import streamlit as st
import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Load data
ROOT = Path(__file__).parent
tracts = gpd.read_file(ROOT / "raw_data" / "tracts_full.geojson")

st.title("ColdChain Shield NYC")
st.markdown("A decision-support tool to estimate Trastuzumab cold-chain exposure during disasters.")

# Sidebar controls
st.sidebar.header("Scenario Parameters")
outage = st.sidebar.slider("Outage Duration (hours)", 6, 120, 72)
backup = st.sidebar.slider("Backup Power (hours)", 0, 48, 0)
drug_stability = st.sidebar.slider("Drug Stability at Room Temp (hours)", 1, 24, 3)

# Simplified probability calculation for the dashboard
def get_prob(mean_outage, backup, drug_limit):
    # Fake math for the demo, replace with your actual lognormal function if you want
    time_to_fail = 2.5 + drug_limit
    effective_outage = max(0, mean_outage - backup)
    if effective_outage > time_to_fail:
        return 0.95
    elif effective_outage == 0:
        return 0.05
    return 0.5 # Placeholder

prob = get_prob(outage, backup, drug_stability)
tracts["risk"] = prob * (tracts["est_cancer_patients"] * 0.15)

# Plot map
fig, ax = plt.subplots(1, 1, figsize=(10, 10))
tracts.plot(column="risk", cmap="Reds", legend=True, ax=ax, edgecolor="black", linewidth=0.1)
ax.set_axis_off()
ax.set_title(f"Estimated Exposure: {int(tracts['risk'].sum())} patients")

st.pyplot(fig)