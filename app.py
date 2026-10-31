import streamlit as st
import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from scipy import stats
import glob 

# Set page layout to wide so the map is big
st.set_page_config(layout="wide", page_title="ColdChain Shield NYC")

st.title("ColdChain Shield NYC")
st.markdown("A decision-support dashboard for estimating Trastuzumab cold-chain exposure during climate disasters.")

# Load data (handles both root and notebooks/ folder)
# Load data (handles both root and notebooks/ folder)
ROOT = Path(__file__).resolve().parent
if not (ROOT / "raw_data").exists():
    ROOT = ROOT.parent

tracts = gpd.read_file(ROOT / "raw_data" / "tracts_full.geojson")

# QUICK FIX: Calculate the flood zones right here in the app
try:
    flood_geojson = ROOT / "raw_data" / "flood.geojson"
    flood_shp = glob.glob(str(ROOT / "raw_data" / "flood_shp" / "*.shp"))
    
    if flood_geojson.exists():
        flood = gpd.read_file(flood_geojson)
    elif flood_shp:
        flood = gpd.read_file(flood_shp[0])
    else:
        raise FileNotFoundError("No flood data found")
        
    if flood.crs != tracts.crs:
        flood = flood.to_crs(tracts.crs)
        
    flood_join = gpd.sjoin(tracts, flood, how="inner", predicate="intersects")
    flooded_geoids = set(flood_join["geoid"])
    tracts["in_flood_zone"] = tracts["geoid"].isin(flooded_geoids)
    
except Exception as e:
    st.error(f"Error loading flood data: {e}")
    tracts["in_flood_zone"] = False # Fallback

# Create a static baseline risk for color scaling
# This ensures the colors don't auto-rescale when you move sliders
tracts["baseline_patients"] = tracts["est_cancer_patients"] * 0.15
STATIC_VMAX = (tracts["baseline_patients"] * 0.6).max() # ~60% failure max

# ---------- SIDEBAR CONTROLS ----------
st.sidebar.header("⚙️ Scenario Parameters")
outage_flood = st.sidebar.slider("Flood Outage Duration (hours)", 24, 120, 72)
outage_inland = st.sidebar.slider("Inland Outage Duration (hours)", 2, 24, 6)
backup_inland = st.sidebar.slider("Inland Backup Power (hours)", 0, 24, 0)
drug_stability = st.sidebar.slider("Drug Stability at Room Temp (hours)", 1, 24, 3)
treatment_frac = st.sidebar.slider("Active Treatment Fraction (%)", 5, 30, 15) / 100.0

# ---------- REAL PHYSICS MATH ----------
def calculate_prob(mean_outage_hrs, backup_hrs, drug_stability_hrs):
    # 1. Fridge thermal model
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
prob_flood = calculate_prob(outage_flood, 0.0, drug_stability) # Floods assume 0 backup
prob_inland = calculate_prob(outage_inland, backup_inland, drug_stability)

# Apply to tracts
tracts["patients_at_risk"] = tracts["est_cancer_patients"] * treatment_frac
tracts["risk"] = np.where(
    tracts["in_flood_zone"],
    prob_flood * tracts["patients_at_risk"],
    prob_inland * tracts["patients_at_risk"]
)

total_risk = int(tracts["risk"].sum())
flood_risk = int(tracts[tracts["in_flood_zone"]]["risk"].sum())
inland_risk = int(tracts[~tracts["in_flood_zone"]]["risk"].sum())

# ---------- DISPLAY METRICS ----------
st.markdown("### Estimated Patient-Equivalents at Risk")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Citywide Total", f"{total_risk:,}")
col2.metric("Coastal Flood Zones", f"{flood_risk:,}")
col3.metric("Inland Neighborhoods", f"{inland_risk:,}")
col4.metric("Inland Failure Prob", f"{prob_inland*100:.1f}%")

st.markdown("---")

# ---------- PLOT MAP ----------
fig, ax = plt.subplots(1, 1, figsize=(12, 10))

# Plot the map
tracts.plot(
    column="risk", 
    cmap="Reds", 
    legend=True, 
    ax=ax, 
    edgecolor="black", 
    linewidth=0.1,
    vmin=0,
    vmax=STATIC_VMAX,  # FIXED COLOR SCALE so you can see changes
    legend_kwds={'label': "Estimated Patients at Risk per Tract", 'shrink': 0.6}
)

# Outline the flood zones
tracts[tracts["in_flood_zone"]].plot(ax=ax, color="none", edgecolor="blue", linewidth=0.8)

ax.set_title(f"Scenario Map: Flood Outage ({outage_flood}h) vs Inland Outage ({outage_inland}h) with {backup_inland}h Backup")
ax.set_axis_off()

st.pyplot(fig)

st.markdown("""
*Note: The color scale (vmax) is locked to a baseline to allow visual comparison. 
Blue outlines represent the Sandy Inundation Zones.*
""")