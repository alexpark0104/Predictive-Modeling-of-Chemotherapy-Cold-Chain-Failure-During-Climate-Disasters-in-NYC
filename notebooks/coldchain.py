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
# Load data

tracts = gpd.read_file(DATA / "tracts_full.geojson")
print("tracts loaded:", len(tracts))


# %%
# Load flood zones

flood_geojson = DATA / "flood.geojson"
flood_shp = glob.glob(str(DATA / "flood_shp" / "*.shp"))

if flood_geojson.exists():
    flood = gpd.read_file(flood_geojson)
elif flood_shp:
    flood = gpd.read_file(flood_shp[0])
else:
    raise FileNotFoundError("CRITICAL ERROR: No flood.geojson or flood_shp/*.shp found in raw_data/. Cannot compute risk without flood hazard layer.")

if flood.crs != tracts.crs:
    flood = flood.to_crs(tracts.crs)

flood_join = gpd.sjoin(tracts, flood, how="inner", predicate="intersects")
flooded_geoids = set(flood_join["geoid"])
tracts["in_flood_zone"] = tracts["geoid"].isin(flooded_geoids)
print(f"Tracts in flood zone: {tracts['in_flood_zone'].sum()} / {len(tracts)}")


# %%
# Unified Failure Function

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
# 1. Baseline Scenario

print("\n=== BASELINE SCENARIO (Trastuzumab - 3hr stability) ===")
tracts["chemo_survivor_equivalents"] = tracts["est_cancer_patients"] * 0.15

prob_baseline, tb_base = calculate_product_failure_prob(mean_outage_hrs=6.2, drug_stability_hrs=3.0)
tracts["baseline_risk"] = prob_baseline * tracts["chemo_survivor_equivalents"]

print(f"Baseline probability: {prob_baseline:.3f}")
print(f"Baseline patient-equivalents at risk: {int(tracts['baseline_risk'].sum())}")


# %%
# 2. Flood Zone Calculation

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
# 3. Sandy Plausability Check

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
# Monte Carlo Simulation

print("\n=== MONTE CARLO SIMULATION (1,000 runs) ===")
np.random.seed(42)
mc_results = [] # Store full iterations here

for _ in range(1000):
    # Sample parameters
    sim_tau = np.random.uniform(10, 14)
    sim_temp = np.random.uniform(25, 35)
    sim_frac = np.random.uniform(0.10, 0.25)
    sim_backup = np.random.uniform(0, 24)
    
    # Calculate probabilities
    pf_in, _ = calculate_product_failure_prob(6.2, sim_tau, sim_temp, sim_backup, 3.0)
    pf_fl, _ = calculate_product_failure_prob(72.0, sim_tau, sim_temp, 0.0, 3.0)
    
    sim_patients = tracts["est_cancer_patients"] * sim_frac
    
    total_risk = (pf_in * sim_patients[~tracts["in_flood_zone"]].sum()) + (pf_fl * sim_patients[tracts["in_flood_zone"]].sum())
    flood_risk = pf_fl * sim_patients[tracts["in_flood_zone"]].sum()
    
    # Save everything for auditing
    mc_results.append({
        "Simulation": _ + 1,
        "Sampled_Tau_Fridge_hr": round(sim_tau, 2),
        "Sampled_Temp_C": round(sim_temp, 2),
        "Sampled_Treatment_Fraction": round(sim_frac, 3),
        "Sampled_Backup_hr": round(sim_backup, 2),
        "Prob_Failure_Inland": round(pf_in, 3),
        "Prob_Failure_Flood": round(pf_fl, 3),
        "Total_Risk": round(total_risk, 0),
        "Flood_Risk": round(flood_risk, 0)
    })

# Save MC results to CSV
mc_df = pd.DataFrame(mc_results)
mc_df.to_csv(FIGURES / "monte_carlo_results.csv", index=False)

print(f"Monte Carlo 95% CI (Total Risk): [{np.percentile(mc_df['Total_Risk'], 2.5):.0f}, {np.percentile(mc_df['Total_Risk'], 97.5):.0f}]")
print("Saved figures/monte_carlo_results.csv")


# %%
# Visualization

fig, ax = plt.subplots(figsize=(10, 10))
tracts.plot(column="climate_risk", cmap="Reds", legend=True, ax=ax, edgecolor="black", linewidth=0.2)
if 'flood' in locals():
    flood.plot(ax=ax, color="none", edgecolor="blue", linewidth=1, alpha=0.5)
ax.set_title("Scenario-Based Cold-Chain Exposure (Patient-Equivalents)")
ax.set_axis_off()
plt.savefig(FIGURES / "final_risk_map.png", dpi=150, bbox_inches="tight")
plt.close()
print("saved figures/final_risk_map.png")

# %%
# Tornado Plot
# Baseline values
# 1. Dynamic Baseline Calculation
base_pf_in, _ = calculate_product_failure_prob(6.2, 12.0, 30.0, 0.0, 3.0)
base_pf_fl, _ = calculate_product_failure_prob(72.0, 12.0, 30.0, 0.0, 3.0)
base_pats = tracts["est_cancer_patients"] * 0.15
base_risk = (base_pf_in * base_pats[~tracts["in_flood_zone"]].sum()) + (base_pf_fl * base_pats[tracts["in_flood_zone"]].sum())

print(f"Calculated Dynamic Baseline Risk: {int(base_risk)}")

# Define the ranges for each variable
variables = {
    "Flood Outage Mean (24h to 120h)": {"mean_flood": [24, 72, 120], "param": "mean_flood"},
    "Inland Outage Mean (2h to 12h)": {"mean_inland": [2, 6.2, 12], "param": "mean_inland"},
    "Inland Backup Power (0h to 24h)": {"backup": [0, 12, 24], "param": "backup"},
    "Fridge Insulation Tau (10h to 14h)": {"tau": [10, 12, 14], "param": "tau"},
    "Treatment Fraction (10% to 25%)": {"frac": [0.10, 0.175, 0.25], "param": "frac"},
    "Outdoor Temp (25C to 35C)": {"temp": [25, 30, 35], "param": "temp"}
}

results = []

for name, vals in variables.items():
    low_val, mid_val, high_val = vals[list(vals.keys())[0]]
    
    # Defaults
    m_flood, m_inland, bck, tau, frac, temp = 72.0, 6.2, 0.0, 12.0, 0.15, 30.0
    
    # Low Scenario
    if "mean_flood" in vals: m_flood = low_val
    if "mean_inland" in vals: m_inland = low_val
    if "backup" in vals: bck = low_val
    if "tau" in vals: tau = low_val
    if "frac" in vals: frac = low_val
    if "temp" in vals: temp = low_val
    
    pf_in, _ = calculate_product_failure_prob(m_inland, tau, temp, bck, 3.0)
    pf_fl, _ = calculate_product_failure_prob(m_flood, tau, temp, 0.0, 3.0)
    pats = tracts["est_cancer_patients"] * frac
    risk_low = (pf_in * pats[~tracts["in_flood_zone"]].sum()) + (pf_fl * pats[tracts["in_flood_zone"]].sum())

    # High Scenario
    m_flood, m_inland, bck, tau, frac, temp = 72.0, 6.2, 0.0, 12.0, 0.15, 30.0
    if "mean_flood" in vals: m_flood = high_val
    if "mean_inland" in vals: m_inland = high_val
    if "backup" in vals: bck = high_val
    if "tau" in vals: tau = high_val
    if "frac" in vals: frac = high_val
    if "temp" in vals: temp = high_val
    
    pf_in, _ = calculate_product_failure_prob(m_inland, tau, temp, bck, 3.0)
    pf_fl, _ = calculate_product_failure_prob(m_flood, tau, temp, 0.0, 3.0)
    pats = tracts["est_cancer_patients"] * frac
    risk_high = (pf_in * pats[~tracts["in_flood_zone"]].sum()) + (pf_fl * pats[tracts["in_flood_zone"]].sum())

    results.append({
        "Variable": name,
        "Low_Value": low_val,
        "Baseline_Value": mid_val,
        "High_Value": high_val,
        "Low_Risk": int(risk_low),
        "High_Risk": int(risk_high),
        "Range": int(abs(risk_high - risk_low))
    })

# Save results to CSV for auditability
results_df = pd.DataFrame(results).sort_values("Range", ascending=True)
results_df.to_csv(FIGURES / "sensitivity_results.csv", index=False)
print("Saved figures/sensitivity_results.csv")

# Plot Tornado
fig, ax = plt.subplots(figsize=(10, 6))
for i, row in results_df.iterrows():
    ax.barh(row["Variable"], row["Low_Risk"] - base_risk, left=base_risk, color="blue", alpha=0.6, label="Low Bound" if i == 0 else "")
    ax.barh(row["Variable"], row["High_Risk"] - base_risk, left=base_risk, color="red", alpha=0.6, label="High Bound" if i == 0 else "")

ax.axvline(base_risk, color="black", linestyle="--", label=f"Baseline Risk ({int(base_risk)})")
ax.set_xlabel("Estimated Patient-Equivalents at Risk")
ax.set_title("One-Way (OAT) Sensitivity Analysis")
ax.legend()
plt.tight_layout()
plt.savefig(FIGURES / "sensitivity_tornado.png", dpi=150)
print("saved figures/sensitivity_tornado.png")

# %%
patient_equivalents = (
    tracts["chemo_survivor_equivalents"]
    .fillna(0)
    .astype(float)
)

flood_mask = (
    tracts["in_flood_zone"]
    .fillna(False)
    .astype(bool)
)

# 1. Naive GIS flood baseline:
# Every patient-equivalent in a flood-zone tract is assumed exposed.
# Non-flooded tracts are excluded from this flood-only comparison.
naive_flood_risk = np.where(
    flood_mask,
    patient_equivalents,
    0.0
)

# 2. Physics-based flood model:
# Uses the modeled flood-zone probability, including refrigerator
# breach time and the 3-hour trastuzumab stability window.
physics_flood_risk = np.where(
    flood_mask,
    prob_flood * patient_equivalents,
    0.0
)

naive_flood_total = naive_flood_risk.sum()
physics_flood_total = physics_flood_risk.sum()

difference = naive_flood_total - physics_flood_total
percent_reduction = (
    difference / naive_flood_total * 100
    if naive_flood_total > 0
    else np.nan
)

print("\n=== BASELINE COMPARISON: FLOOD-ZONE TRACTS ONLY ===")
print(
    f"Naive GIS baseline: "
    f"{naive_flood_total:,.0f} patient-equivalents"
)
print(
    f"Physics-based model: "
    f"{physics_flood_total:,.0f} patient-equivalents"
)
print(
    f"Difference: "
    f"{difference:,.0f} patient-equivalents"
)
print(
    f"Relative reduction in modeled exposure: "
    f"{percent_reduction:.1f}%"
)

print(
    "\nInterpretation: The naive GIS baseline assumes immediate "
    "failure for every patient-equivalent in a flood-zone tract. "
    "The physics-based estimate incorporates the modeled outage "
    "distribution, refrigerator thermal delay, and trastuzumab "
    "stability window."
)
# &&
#Citywide Comparison 
# Naive assumption: immediate failure everywhere in NYC.
naive_citywide_risk = patient_equivalents.sum()
physics_citywide_risk = tracts["climate_risk"].fillna(0).sum()

citywide_difference = naive_citywide_risk - physics_citywide_risk
citywide_reduction = (
    citywide_difference / naive_citywide_risk * 100
    if naive_citywide_risk > 0
    else np.nan
)

print("\n=== BASELINE COMPARISON: CITYWIDE ===")
print(f"Naive immediate-failure baseline: {naive_citywide_risk:,.0f}")
print(f"Physics-based scenario estimate: {physics_citywide_risk:,.0f}")
print(f"Difference: {citywide_difference:,.0f}")
print(f"Relative reduction: {citywide_reduction:.1f}%")

# %%
# Decision Rule
# Calculate baseline inland risk (0 hours backup)
pf_in_base, _ = calculate_product_failure_prob(6.2, 12.0, 30.0, 0.0, 3.0)
inland_patients = tracts.loc[~tracts["in_flood_zone"], "chemo_survivor_equivalents"].sum()
base_inland_risk = pf_in_base * inland_patients

targets = [0.25, 0.50, 0.75]
thresholds = {}

print(f"Baseline Inland Risk (0h backup): {int(base_inland_risk):,} patients\n")

for backup_hrs in range(1, 25): # Test 1 to 24 hours of backup
    # Calculate new probability with this backup
    pf_in_new, _ = calculate_product_failure_prob(6.2, 12.0, 30.0, backup_hrs, 3.0)
    new_risk = pf_in_new * inland_patients
    
    # Calculate reduction
    reduction = (base_inland_risk - new_risk) / base_inland_risk
    
    for target in targets:
        if reduction >= target and target not in thresholds:
            thresholds[target] = backup_hrs

for target in targets:
    backup_hrs = thresholds.get(target)

    if backup_hrs is None:
        print(
            f"  -> {target:.0%} reduction requires "
            "more than 24 hours of backup power"
        )
        continue

    # Recalculate the actual result for the selected threshold
    pf_at_threshold, _ = calculate_product_failure_prob(
        mean_outage_hrs=6.2,
        tau_fridge_hr=12.0,
        T_outdoor=30.0,
        backup_hrs=backup_hrs,
        drug_stability_hrs=3.0
    )

    risk_at_threshold = pf_at_threshold * inland_patients

    achieved_reduction = (
        (base_inland_risk - risk_at_threshold)
        / base_inland_risk
        if base_inland_risk > 0
        else 0.0
    )

    print(
        f"  -> {target:.0%} reduction requires "
        f"{backup_hrs} hours of backup power "
        f"(achieved: {achieved_reduction:.1%}; "
        f"estimated risk: {risk_at_threshold:,.0f})"
    )
# %%
# Three Model Comparison 
patient_equivalents = (
    tracts["chemo_survivor_equivalents"]
    .fillna(0)
    .astype(float)
)

flood_mask = (
    tracts["in_flood_zone"]
    .fillna(False)
    .astype(bool)
)

# 1. Native GIS Flooding Only Baseline
# Assumes every patient-equivalent in a flood-zone tract is immediately exposed.

naive_flood_risk = np.where(
    flood_mask,
    patient_equivalents,
    0.0
)

naive_flood_total = naive_flood_risk.sum()

# 2. Thermal Only Model
# Includes refrigerator thermal delay but excludes the
# additional 3-hour trastuzumab stability window.

pf_thermal_in, _ = calculate_product_failure_prob(
    mean_outage_hrs=6.2,
    tau_fridge_hr=12.0,
    T_outdoor=30.0,
    backup_hrs=0.0,
    drug_stability_hrs=0.0
)

pf_thermal_flood, _ = calculate_product_failure_prob(
    mean_outage_hrs=72.0,
    tau_fridge_hr=12.0,
    T_outdoor=30.0,
    backup_hrs=0.0,
    drug_stability_hrs=0.0
)

thermal_only_risk = np.where(
    flood_mask,
    pf_thermal_flood * patient_equivalents,
    pf_thermal_in * patient_equivalents
)

thermal_only_total = thermal_only_risk.sum()
thermal_only_flood_total = thermal_only_risk[flood_mask].sum()

# 3. Full time to failure model
# Includes refrigerator thermal delay plus the 3-hour
# trastuzumab stability window.

tto_risk = tracts["climate_risk"].fillna(0)
tto_total = tto_risk.sum()
tto_flood_total = tto_risk[flood_mask].sum()

# Flood only comparison

print("\n=== FLOOD-ZONE COMPARISON ===")
print(
    f"1. Naive GIS immediate-failure baseline: "
    f"{naive_flood_total:,.0f}"
)
print(
    f"2. Thermal-only model: "
    f"{thermal_only_flood_total:,.0f}"
)
print(
    f"3. Full time-to-failure model: "
    f"{tto_flood_total:,.0f}"
)

# Citywide Comparison

# For a citywide immediate-failure upper bound, every
# patient-equivalent is assumed immediately exposed.
naive_citywide_total = patient_equivalents.sum()

print("\n=== CITYWIDE COMPARISON ===")
print(
    f"1. Naive citywide immediate-failure upper bound: "
    f"{naive_citywide_total:,.0f}"
)
print(
    f"2. Thermal-only model: "
    f"{thermal_only_total:,.0f}"
)
print(
    f"3. Full time-to-failure model: "
    f"{tto_total:,.0f}"
)

print("\n=== MODEL DIFFERENCES ===")
print(
    "Thermal-only reduction versus naive citywide baseline: "
    f"{naive_citywide_total - thermal_only_total:,.0f}"
)
print(
    "Full time-to-failure reduction versus thermal-only model: "
    f"{thermal_only_total - tto_total:,.0f}"
)
print(
    "Full time-to-failure reduction versus naive citywide baseline: "
    f"{naive_citywide_total - tto_total:,.0f}"
)