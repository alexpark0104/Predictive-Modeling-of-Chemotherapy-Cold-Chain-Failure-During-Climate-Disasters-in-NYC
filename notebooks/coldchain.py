# %%
from pathlib import Path
import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
import os
import glob

# Dynamically find the project root (works on any machine)
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "raw_data"
FIGURES = ROOT / "figures"
FIGURES.mkdir(exist_ok=True)

print("coldchain.py — starting")


# %%
# ---------- LOAD MASTER DATA ----------

tracts = gpd.read_file(DATA / "tracts_full.geojson")
print("tracts loaded:", len(tracts))


# %%
# ---------- LOAD FLOOD ZONES ----------

print("Loading flood zones...")
try:
    # Check for GeoJSON first, then Shapefile
    flood_geojson = DATA / "flood.geojson"
    flood_shp = glob.glob(str(DATA / "flood_shp" / "*.shp"))
    
    if flood_geojson.exists():
        flood = gpd.read_file(flood_geojson)
    elif flood_shp:
        flood = gpd.read_file(flood_shp[0])
    else:
        raise FileNotFoundError("No flood.geojson or flood_shp/*.shp found in raw_data/")
    
    if flood.crs != tracts.crs:
        flood = flood.to_crs(tracts.crs)

    # Spatial join to flag tracts
    flood_join = gpd.sjoin(tracts, flood, how="inner", predicate="intersects")
    flooded_geoids = set(flood_join["geoid"])
    tracts["in_flood_zone"] = tracts["geoid"].isin(flooded_geoids)
    print(f"Tracts in flood zone: {tracts['in_flood_zone'].sum()} / {len(tracts)}")

except Exception as e:
    print("Error loading flood data:", e)
    tracts["in_flood_zone"] = False # Fallback so code doesn't crash


# %%
# ---------- UNIFIED FAILURE FUNCTION ----------

def calculate_product_failure_prob(mean_outage_hrs, tau_fridge_hr=12.0, T_outdoor=30.0, backup_hrs=0.0, drug_stability_hrs=3.0):
    """Calculates probability that outage exceeds both fridge breach AND drug survival time."""
    t = np.arange(0, 168 * 60, 1.0)
    T = np.zeros_like(t)
    
    # Fridge stays cold during backup
    mask = t < backup_hrs * 60
    T[mask] = 4.0
    
    # Fridge warms up after backup
    after = ~mask
    t_after = (t[after] - backup_hrs * 60) / 60
    T_indoor = T_outdoor - (T_outdoor - 22.0) * np.exp(-t_after / 4.0)
    T[after] = T_indoor - (T_indoor - 4.0) * np.exp(-t_after / tau_fridge_hr)
    
    breach = np.where(T > 8.0)[0]
    t_breach = t[breach[0]] / 60 if len(breach) > 0 else 168.0
    
    # Total time to failure = Fridge breach + Drug survival time
    t_total_failure = t_breach + drug_stability_hrs
    
    # Probability outage exceeds total failure
    sigma = 1.0
    mu = np.log(mean_outage_hrs) - 0.5 * sigma**2
    return 1 - stats.lognorm.cdf(t_total_failure, s=sigma, scale=np.exp(mu)), t_breach


# %%
# ---------- 1. BASELINE SCENARIO ----------

print("\n=== BASELINE SCENARIO (Trastuzumab - 3hr stability) ===")
tracts["chemo_survivor_equivalents"] = tracts["est_cancer_patients"] * 0.15

prob_baseline, tb_base = calculate_product_failure_prob(mean_outage_hrs=6.2, drug_stability_hrs=3.0)
tracts["baseline_risk"] = prob_baseline * tracts["chemo_survivor_equivalents"]

print(f"Baseline probability: {prob_baseline:.3f}")
print(f"Baseline patient-equivalents at risk: {int(tracts['baseline_risk'].sum())}")


# %%
# ---------- 2. FLOOD ZONE CALCULATION ----------

print("\n=== FLOOD ZONE CALCULATION ===")
prob_flood, _ = calculate_product_failure_prob(mean_outage_hrs=72.0, backup_hrs=0.0, drug_stability_hrs=3.0)
prob_inland, _ = calculate_product_failure_prob(mean_outage_hrs=6.2, backup_hrs=0.0, drug_stability_hrs=3.0)

tracts["climate_risk"] = np.where(
    tracts["in_flood_zone"],
    prob_flood * tracts["chemo_survivor_equivalents"],
    prob_inland * tracts["chemo_survivor_equivalents"]
)
print(f"Flood Zone failure prob: {prob_flood*100:.1f}%")
print(f"Inland failure prob: {prob_inland*100:.1f}%")
print(f"Total climate-adjusted patient-equivalents at risk: {int(tracts['climate_risk'].sum())}")


# %%
# ---------- 3. SANDY PLAUSIBILITY CHECK ----------

print("\n=== SANDY SPATIAL PLAUSIBILITY CHECK ===")
hospitals = {
    "NYU Langone": (40.7421, -73.9738),
    "Bellevue": (40.7394, -73.9752),
    "Coney Island Hospital": (40.5851, -73.9660),
    "Mount Sinai (Control)": (40.7900, -73.9520),
    "Montefiore (Control)": (40.8802, -73.8790)
}

# Build GeoDataFrame for hospitals
hosp_df = pd.DataFrame(hospitals).T
hosp_df.columns = ["lat", "lon"]
hosp_df["lat"] = pd.to_numeric(hosp_df["lat"])
hosp_df["lon"] = pd.to_numeric(hosp_df["lon"])
hosp_gdf = gpd.GeoDataFrame(hosp_df, geometry=gpd.points_from_xy(hosp_df.lon, hosp_df.lat), crs="EPSG:4326")
hosp_gdf = hosp_gdf.to_crs(tracts.crs)

for name, row in hosp_gdf.iterrows():
    # Find the tract containing this hospital
    tract_match = gpd.sjoin(tracts, gpd.GeoDataFrame([row], crs=tracts.crs), predicate="contains")
    tract_geoid = tract_match.index[0] if not tract_match.empty else None
    
    if tract_geoid is not None:
        is_flooded = tracts.loc[tract_geoid, "in_flood_zone"]
        if is_flooded:
            p, _ = calculate_product_failure_prob(mean_outage_hrs=72.0, backup_hrs=0.0, drug_stability_hrs=3.0)
            status = "Flood Zone (72h outage, 0h backup)"
        else:
            p, _ = calculate_product_failure_prob(mean_outage_hrs=6.2, backup_hrs=0.0, drug_stability_hrs=3.0)
            status = "Inland (6.2h outage, 0h backup)"
        print(f"{name}: {p*100:.1f}% failure probability | {status}")
    else:
        print(f"{name}: Not found inside NYC tracts.")


# %%
# ---------- 4. MONTE CARLO SIMULATION ----------

print("\n=== MONTE CARLO SIMULATION (1,000 runs) ===")
np.random.seed(42)
total_risks, flood_risks = [], []

for _ in range(1000):
    sim_tau = np.random.uniform(10, 14)
    sim_temp = np.random.uniform(25, 35)
    sim_frac = np.random.uniform(0.10, 0.25)
    sim_backup = np.random.uniform(0, 24)
    
    pf_in, _ = calculate_product_failure_prob(6.2, sim_tau, sim_temp, sim_backup, 3.0)
    pf_fl, _ = calculate_product_failure_prob(72.0, sim_tau, sim_temp, 0.0, 3.0) # Flood forced 0h backup
    
    sim_patients = tracts["est_cancer_patients"] * sim_frac
    
    total_risks.append((pf_in * sim_patients[~tracts["in_flood_zone"]].sum()) + (pf_fl * sim_patients[tracts["in_flood_zone"]].sum()))
    flood_risks.append(pf_fl * sim_patients[tracts["in_flood_zone"]].sum())

# Save MC results to CSV as requested by reviewer
mc_df = pd.DataFrame({"Total_Risk": total_risks, "Flood_Risk": flood_risks})
mc_df.to_csv(FIGURES / "monte_carlo_results.csv", index=False)

print(f"Monte Carlo 95% CI: [{np.percentile(total_risks, 2.5):.0f}, {np.percentile(total_risks, 97.5):.0f}]")
print("Saved figures/monte_carlo_results.csv")


# %%
# ---------- 5. VISUALIZATION ----------

fig, ax = plt.subplots(figsize=(10, 10))
tracts.plot(column="climate_risk", cmap="Reds", legend=True, ax=ax, edgecolor="black", linewidth=0.2)
if 'flood' in locals():
    flood.plot(ax=ax, color="none", edgecolor="blue", linewidth=1, alpha=0.5)
ax.set_title("Scenario-Based Cold-Chain Exposure (Patient-Equivalents)")
ax.set_axis_off()
plt.savefig(FIGURES / "final_risk_map.png", dpi=150, bbox_inches="tight")
plt.close()
print("saved figures/final_risk_map.png")