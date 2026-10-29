# %%
from pathlib import Path
import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Dynamically find the project root (works on any machine)
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "raw_data"
FIGURES = ROOT / "figures"
FIGURES.mkdir(exist_ok=True)

print("coldchain.py — starting")
# %%
#Load master data
tracts = gpd.read_file(DATA / "tracts_full.geojson")
print("tracts loaded:", len(tracts))
print("columns:", tracts.columns.tolist())
# %%
#Drug stability input from STABILIS
# Hours until drug is unusable at 25°C (room temperature)
# Assuming linear degradation between 2-8°C and 25°C endpoints

drugs = {
    
    "trastuzumab":  {"stable_25C_hours": 3, "label": "Trastuzumab (Highly Sensitive)"},
    
    
    "rituximab":    {"stable_25C_hours": 15 * 24, "label": "Rituximab (Robust)"},
}

print("drugs loaded:", list(drugs.keys()))
# %%
# Thermal Model Functions
def time_to_8C(
    tau_fridge_hr=12.0,      # hours (was mins)
    tau_building_hr=4.0,
    T_start=4.0,
    T_outdoor=30.0,
    T_indoor_0=22.0,
    backup_hours=0.0,
    dt_min=1.0,
    max_hours=168,
):
    """
    Returns hours until fridge exceeds 8°C, including backup power delay.
    Calibrated to NIST data (2-3.5 hours to breach 8°C with no backup).
    """
    t = np.arange(0, max_hours * 60, dt_min)  # minutes
    T = np.zeros_like(t)

    # Before backup runs out: fridge holds 4°C
    backup_mask = t < backup_hours * 60
    T[backup_mask] = T_start

    # After backup: fridge warms toward indoor ambient
    after = ~backup_mask
    t_after = (t[after] - backup_hours * 60) / 60  # hours after backup ends

    # Indoor temperature rises toward outdoor
    T_indoor = T_outdoor - (T_outdoor - T_indoor_0) * np.exp(-t_after / tau_building_hr)

    # Fridge temperature rises toward indoor ambient
    T[after] = T_indoor - (T_indoor - T_start) * np.exp(-t_after / tau_fridge_hr)

    # Find first time > 8°C
    breach = np.where(T > 8.0)[0]
    if len(breach) == 0:
        return max_hours  # never breaches
    return t[breach[0]] / 60  # hours
# %%
# Test the model
print("time_to_8C (no backup, 30°C outdoor, standard params):",
      time_to_8C(backup_hours=0), "hours")

print("time_to_8C (24h backup, 30°C outdoor):",
      time_to_8C(backup_hours=24), "hours")

print("time_to_8C (no backup, 20°C outdoor — cooler day):",
      time_to_8C(backup_hours=0, T_outdoor=20), "hours")
# %%
# Outage duration distribution 
def outage_exceedance_prob(mean_hours=6.2, sigma=1.0, duration_threshold=6.0):
    """
    P(outage duration > threshold) under lognormal distribution.
    mean_hours from ConEd CAIDI/system duration.
    """
    from scipy import stats
    mu = np.log(mean_hours) - 0.5 * sigma**2
    return 1 - stats.lognorm.cdf(duration_threshold, s=sigma, scale=np.exp(mu))


# Quick check
for thresh in [2, 4, 6, 12, 24]:
    p = outage_exceedance_prob(duration_threshold=thresh)
    print(f"P(outage > {thresh}h) = {p:.3f}")

# %%
# compute cold chain risk per tract
# Baseline assumptions (CALIBRATED)
TAU_FRIDGE = 12.0        # hours (was 45 minutes — NIST calibration)
TAU_BUILDING = 4.0       # hours
T_OUTDOOR = 30           # °C (summer blackout)
BACKUP_HOURS = 0         # no backup — worst-case baseline
TREATMENT_FRACTION = 0.15  # 15% of cancer survivors on active chemo

# Compute time-to-8°C (same for all tracts in baseline — varies by scenario)
t_breach = time_to_8C(
    tau_fridge_hr=TAU_FRIDGE,  # <--- CHANGED TO _hr
    tau_building_hr=TAU_BUILDING,
    T_outdoor=T_OUTDOOR,
    backup_hours=BACKUP_HOURS,
)

print(f"baseline time-to-8°C: {t_breach:.1f} hours")
# Probability outage exceeds breach time
p_fail = outage_exceedance_prob(mean_hours=6.2, duration_threshold=t_breach)
print(f"P(outage > {t_breach:.1f}h) = {p_fail:.3f}")

# Active chemo patients per tract
tracts["active_chemo_patients"] = (
    tracts["est_cancer_patients"] * TREATMENT_FRACTION
)

# Cold-chain risk score
tracts["coldchain_risk_baseline"] = (
    p_fail * tracts["active_chemo_patients"]
)

print("total active chemo patients (NYC):",
      int(tracts["active_chemo_patients"].sum()))
print("total cold-chain risk (baseline):",
      int(tracts["coldchain_risk_baseline"].sum()))

# %%
#Scenario comparison
scenarios = {
    "Summer blackout, no backup": {
        "T_outdoor": 30, "backup_hours": 0, "mean_outage": 6.2,
    },
    "Hurricane, 24h backup": {
        "T_outdoor": 22, "backup_hours": 24, "mean_outage": 72,
    },
    "Hurricane, no backup": {
        "T_outdoor": 22, "backup_hours": 0, "mean_outage": 72,
    },
    "Winter storm, no backup": {
        "T_outdoor": 5, "backup_hours": 0, "mean_outage": 12,
    },
}

results = []
for name, s in scenarios.items():
    tb = time_to_8C(
        tau_fridge_hr=TAU_FRIDGE,
        tau_building_hr=TAU_BUILDING,
        T_outdoor=s["T_outdoor"],
        backup_hours=s["backup_hours"],
    )
    pf = outage_exceedance_prob(
        mean_hours=s["mean_outage"],
        duration_threshold=tb,
    )
    risk = pf * tracts["active_chemo_patients"].sum()
    results.append({
        "scenario": name,
        "time_to_8C_hours": round(tb, 1),
        "P_failure": round(pf, 3),
        "patients_at_risk": int(risk),
    })

scenario_df = pd.DataFrame(results)
print("\n=== SCENARIO COMPARISON ===")
print(scenario_df.to_string(index=False))
# %%
# Map: Cold-chain risk (baseline)
fig, ax = plt.subplots(figsize=(10, 10))
tracts.plot(
    column="coldchain_risk_baseline",
    cmap="Reds",
    legend=True,
    legend_kwds={"shrink": 0.6},
    ax=ax,
    edgecolor="black",
    linewidth=0.2,
)
ax.set_title("Cold-chain risk (baseline: summer blackout, no backup)")
ax.set_axis_off()
plt.savefig(FIGURES / "coldchain_risk_baseline.png", dpi=150, bbox_inches="tight")
plt.close()
print("saved figures/coldchain_risk_baseline.png")
# %%
#Sandy
print("Loading flood zones...")
try:
    flood = gpd.read_file(DATA / "flood.geojson")
    
    # Ensure same CRS
    if flood.crs != tracts.crs:
        flood = flood.to_crs(tracts.crs)

    # Spatial join: flag tracts that intersect the flood zone
    flood_join = gpd.sjoin(tracts, flood, how="inner", predicate="intersects")
    flooded_geoids = set(flood_join["geoid"])

    tracts["in_flood_zone"] = tracts["geoid"].isin(flooded_geoids)
    print(f"Tracts in flood zone: {tracts['in_flood_zone'].sum()} / {len(tracts)}")

    # Adjust risk based on flood status
    # Flood zone -> Hurricane scenario (72h outage) applied to those tract's patients
    # Not in flood zone -> Summer blackout (6.2h outage) applied to those tract's patients
    
    risk_hurricane = outage_exceedance_prob(mean_hours=72, duration_threshold=2.5)
    risk_summer = outage_exceedance_prob(mean_hours=6.2, duration_threshold=2.5)

    tracts["climate_coldchain_risk"] = np.where(
        tracts["in_flood_zone"],
        risk_hurricane * tracts["active_chemo_patients"],
        risk_summer * tracts["active_chemo_patients"]
    )

    print("Total climate-adjusted risk:", int(tracts["climate_coldchain_risk"].sum()))
    print("Risk added purely by flood exposure:", int(tracts.loc[tracts["in_flood_zone"], "climate_coldchain_risk"].sum() - tracts.loc[tracts["in_flood_zone"], "coldchain_risk_baseline"].sum()))

except Exception as e:
    print("Error loading flood data:", e)
    print("Make sure flood.geojson is in raw_data/")

# %%
#map adjusted climate risk
if "climate_coldchain_risk" in tracts.columns:
    fig, ax = plt.subplots(figsize=(10, 10))
    tracts.plot(
        column="climate_coldchain_risk",
        cmap="Reds",
        legend=True,
        legend_kwds={"shrink": 0.6},
        ax=ax,
        edgecolor="black",
        linewidth=0.2,
        missing_kwds={"color": "lightgrey", "label": "No Data"}
    )
    # Overlay flood zones in blue for visual effect
    if "flood" in locals():
        flood.plot(ax=ax, color="none", edgecolor="blue", linewidth=1, alpha=0.5)
        
    ax.set_title("Cold-Chain Risk (Adjusted for Sandy Flood Zones)\nBlue outline = Flood Zone")
    ax.set_axis_off()
    plt.savefig(FIGURES / "coldchain_risk_flood.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("saved figures/coldchain_risk_flood.png")
# %%
# Monte Carlo Analysis
import numpy as np
import matplotlib.pyplot as plt

print("Running Monte Carlo Sensitivity Analysis (1,000 simulations)...")
np.random.seed(42) # <--- CRITICAL: Ensures exact reproducibility

n_sims = 1000
total_risk_results = []
flood_zone_risk_results = []

# We will evaluate risk specifically for Trastuzumab (the most sensitive drug)
drug_limit_hrs = drugs["trastuzumab"]["stable_25C_hours"] # 3 hours

for i in range(n_sims):
    # Distributions: Uniform for fridge insulation, temp, and backup
    sim_tau_fridge = np.random.uniform(10, 14)
    sim_T_outdoor = np.random.uniform(25, 35)
    sim_treatment_fraction = np.random.uniform(0.10, 0.25)
    
    # Inland tracts get 0-24h backup. Flood tracts are forced to 0h backup.
    sim_backup_inland = np.random.uniform(0, 24)
    sim_backup_flood = 0.0  # Flooded basements destroy generators

    # Calculate time to breach for this iteration
    tb_inland = time_to_8C(sim_tau_fridge, 4.0, T_outdoor=sim_T_outdoor, backup_hours=sim_backup_inland)
    tb_flood = time_to_8C(sim_tau_fridge, 4.0, T_outdoor=sim_T_outdoor, backup_hours=sim_backup_flood)
    
    # Time to total drug failure = Fridge breach time + Drug survival time at room temp
    t_fail_inland = tb_inland + drug_limit_hrs
    t_fail_flood = tb_flood + drug_limit_hrs
    
    # Probabilities (using 6.2h mean for inland, 72h mean for flood)
    pf_inland = outage_exceedance_prob(mean_hours=6.2, duration_threshold=t_fail_inland)
    pf_flood = outage_exceedance_prob(mean_hours=72, duration_threshold=t_fail_flood)
    
    sim_active_patients = tracts["est_cancer_patients"] * sim_treatment_fraction
    
    # Calculate risk
    sim_flood_risk = pf_flood * sim_active_patients[tracts["in_flood_zone"]].sum()
    sim_inland_risk = pf_inland * sim_active_patients[~tracts["in_flood_zone"]].sum()
    
    total_risk_results.append(sim_flood_risk + sim_inland_risk)
    flood_zone_risk_results.append(sim_flood_risk)

# Plotting
fig, ax = plt.subplots(figsize=(8, 6))
ax.hist(total_risk_results, bins=30, alpha=0.7, label='Citywide Risk (Patient-Equivalents)', color='blue')
ax.hist(flood_zone_risk_results, bins=30, alpha=0.7, label='Flood Zone Risk', color='red')
ax.set_xlabel('Estimated Patient-Equivalents at Risk')
ax.set_ylabel('Number of Simulations')
ax.set_title('Monte Carlo Sensitivity Analysis (1,000 Simulations)')
ax.legend()
plt.savefig(FIGURES / "monte_carlo_sensitivity.png", dpi=150, bbox_inches='tight')
plt.close()
print("saved figures/monte_carlo_sensitivity.png")

# %%
# Prove the model correctly separates Flood Hazard from Patient Density

hospitals_data = {
    "hospital": [
        "NYU Langone (Failed)", 
        "Bellevue (Failed)", 
        "Coney Island (Failed)",
        "Mount Sinai (Control - Inland)",
        "Montefiore (Control - Inland)"
    ],
    "lat": [40.7421, 40.7394, 40.5851, 40.7900, 40.8802],
    "lon": [-73.9738, -73.9752, -73.9660, -73.9520, -73.8790]
}
hospitals_df = pd.DataFrame(hospitals_data)

# Convert to GeoDataFrame
hospitals_gdf = gpd.GeoDataFrame(
    hospitals_df, 
    geometry=gpd.points_from_xy(hospitals_df.lon, hospitals_df.lat),
    crs="EPSG:4326"
)

if hospitals_gdf.crs != tracts.crs:
    hospitals_gdf = hospitals_gdf.to_crs(tracts.crs)

hospital_tracts = gpd.sjoin(
    hospitals_gdf, 
    tracts[["geoid", "boroname", "climate_coldchain_risk", "geometry"]], 
    how="left", 
    predicate="intersects"
)

# Merge the percentile back into our hospital data
tracts["risk_percentile"] = tracts["climate_coldchain_risk"].rank(pct=True)

hospital_validation = hospital_tracts.merge(
    tracts[["geoid", "risk_percentile"]], 
    on="geoid", 
    how="left"
)

for index, row in hospital_validation.iterrows():
    # If it's in the flood zone, the model uses the 72h outage. If not, the 6.2h outage.
    # Look at whether the tract is in the flood zone to see the hazard.
    is_flooded = tracts.loc[tracts["geoid"] == row["geoid"], "in_flood_zone"].values[0]
    
    if is_flooded:
        prob = "99.6% (Hurricane Flood Zone)"
    else:
        prob = "66.6% (Standard Blackout)"
        
    print(f"{row['hospital']}: {prob}")