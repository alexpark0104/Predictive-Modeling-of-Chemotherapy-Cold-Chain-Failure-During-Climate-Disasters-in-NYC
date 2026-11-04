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

# Load data
ROOT = Path(__file__).resolve().parent
if not (ROOT / "raw_data").exists():
    ROOT = ROOT.parent
tracts = gpd.read_file(ROOT / "raw_data" / "tracts_full.geojson")

# Load Flood Zones
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
    tracts["in_flood_zone"] = tracts["geoid"].isin(set(flood_join["geoid"]))
except Exception as e:
    st.error(f"Error loading flood data: {e}")
    tracts["in_flood_zone"] = False

# Load Hospitals
try:
    hosp_raw = pd.read_csv(ROOT / "raw_data" / "ny_hospitals.csv")
    nyc_counties = ["Bronx", "Kings", "New York", "Queens", "Richmond"]
    hosp_nyc = hosp_raw[hosp_raw["Facility County"].isin(nyc_counties)].copy()
    hosp_nyc = hosp_nyc[hosp_nyc["Description"].isin(["Hospital", "Off-Campus Emergency Department"])].copy()
    hosp_nyc = hosp_nyc.dropna(subset=["Facility Latitude", "Facility Longitude"])
    
    hospitals_geo = gpd.GeoDataFrame(
        hosp_nyc,
        geometry=gpd.points_from_xy(hosp_nyc["Facility Longitude"], hosp_nyc["Facility Latitude"]),
        crs="EPSG:4326"
    )
    if hospitals_geo.crs != tracts.crs:
        hospitals_geo = hospitals_geo.to_crs(tracts.crs)
        
    # Spatial join hospitals to tracts
    hosp_joined = gpd.sjoin(hospitals_geo, tracts[["geoid", "in_flood_zone", "geometry"]], how="left", predicate="intersects")
except Exception as e:
    st.error(f"Error loading hospital data: {e}")
    hospitals_geo = None
    hosp_joined = None

# Create a static baseline risk for color scaling
tracts["baseline_patients"] = tracts["est_cancer_patients"] * 0.15
STATIC_VMAX = (tracts["baseline_patients"] * 0.6).max()

# ---------- SIDEBAR CONTROLS ----------
st.sidebar.header("Scenario Parameters")
outage_flood = st.sidebar.slider("Flood Outage Duration (hours)", 24, 120, 72)
outage_inland = st.sidebar.slider("Inland Outage Duration (hours)", 2, 24, 6)
backup_inland = st.sidebar.slider("Inland Backup Power (hours)", 0, 24, 0)
drug_stability = st.sidebar.slider("Drug Stability at Room Temp (hours)", 1, 24, 3)
treatment_frac = st.sidebar.slider("Active Treatment Fraction (%)", 5, 30, 15) / 100.0

st.sidebar.markdown("---")
st.sidebar.header("Map Layers")
show_hospitals = st.sidebar.checkbox("Show All Hospitals", value=True)
show_at_risk_only = st.sidebar.checkbox("Show ONLY Hospitals in High Risk", value=False)

# ---------- REAL PHYSICS MATH ----------
def calculate_prob(mean_outage_hrs, backup_hrs, drug_stability_hrs):
    t = np.arange(0, 168 * 60, 5.0)
    T = np.zeros_like(t)
    mask = t < backup_hrs * 60
    T[mask] = 4.0
    after = ~mask
    t_after = (t[after] - backup_hrs * 60) / 60
    T_indoor = 30.0 - (30.0 - 22.0) * np.exp(-t_after / 4.0)
    T[after] = T_indoor - (T_indoor - 4.0) * np.exp(-t_after / 12.0)
    breach = np.where(T > 8.0)[0]
    t_breach = t[breach[0]] / 60 if len(breach) > 0 else 168.0
    t_total_failure = t_breach + drug_stability_hrs
    sigma = 1.0
    mu = np.log(mean_outage_hrs) - 0.5 * sigma**2
    return 1 - stats.lognorm.cdf(t_total_failure, s=sigma, scale=np.exp(mu))

prob_flood = calculate_prob(outage_flood, 0.0, drug_stability)
prob_inland = calculate_prob(outage_inland, backup_inland, drug_stability)

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

tracts.plot(
    column="risk", cmap="Reds", legend=True, ax=ax, edgecolor="black", linewidth=0.1,
    vmin=0, vmax=STATIC_VMAX,
    legend_kwds={'label': "Estimated Patients at Risk per Tract", 'shrink': 0.6}
)

# Plot flood zones
if 'flood' in locals():
    flood.plot(ax=ax, color="none", edgecolor="blue", linewidth=0.8, alpha=0.6)

# Plot Hospitals conditionally based on checkboxes
if show_hospitals and hosp_joined is not None:
    if show_at_risk_only:
        # Filter to only high-risk hospitals (e.g., in flood zones or high tract risk)
        # Let's define "high risk" as in a flood zone
        at_risk_hosp = hosp_joined[hosp_joined["in_flood_zone"] == True]
        at_risk_hosp.plot(ax=ax, color="red", marker="X", markersize=120, label="High Risk Hospital")
    else:
        # Inland Hospitals
        hosp_joined[hosp_joined["in_flood_zone"] == False].plot(
            ax=ax, color="green", marker="+", markersize=100, label="Inland Hospital"
        )
        # Flooded Hospitals
        hosp_joined[hosp_joined["in_flood_zone"] == True].plot(
            ax=ax, color="purple", marker="X", markersize=100, label="Flood-Zone Hospital"
        )
    ax.legend(loc="lower right", fontsize=10)

ax.set_title(f"Scenario Map: Flood Outage ({outage_flood}h) vs Inland Outage ({outage_inland}h) with {backup_inland}h Backup")
ax.set_axis_off()

st.pyplot(fig)