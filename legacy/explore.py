# %%
from pathlib import Path
import geopandas as gpd
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import folium
import os

# Dynamically find the project root (works on any machine)
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "raw_data"
FIGURES = ROOT / "figures"
FIGURES.mkdir(exist_ok=True)

print("geopandas version:", gpd.__version__)
print("looking in:", DATA)


# %%
# Helper functions

def clean_cdc_sentinels(df, cols):
    """Replace CDC's -999 sentinel (any format) with NaN, coerce to numeric."""
    df[cols] = df[cols].apply(pd.to_numeric, errors="coerce")  
    df[cols] = df[cols].replace(-999, pd.NA)                    
    df[cols] = df[cols].replace(-999.0, pd.NA)                  
    return df


def assert_unit_range(series, name):
    """Raise if a column that should be 0-1 has values outside [0, 1]."""
    bad = ((series < 0) | (series > 1)).sum()
    assert bad == 0, (
        f"{name} has {bad} values outside 0-1 "
        f"(min={series.min()}, max={series.max()})"
    )
    print(f"{name}: OK ({series.min():.3f} to {series.max():.3f})")


# %%
# Loading tracts

tracts = gpd.read_file(DATA / "2020_Census_Tracts_20261016.geojson")
tracts["geoid"] = tracts["geoid"].astype(str).str.zfill(11)

print("tracts rows:", len(tracts))
print("crs:", tracts.crs)


# %%
# Plotting boroughs

tracts.plot(column="boroname", figsize=(10, 10), legend=True, cmap="tab10")
plt.title("NYC by Borough")
plt.savefig(FIGURES / "nyc_boroughs.png", dpi=150, bbox_inches="tight")
plt.close()
print("saved figures/nyc_boroughs.png")


# %%
# Loading SVI

svi = pd.read_csv(DATA / "svi_ny_tract_2022.csv", dtype=str)
svi["FIPS"] = svi["FIPS"].str.zfill(11)
svi = svi.rename(columns={"FIPS": "geoid"})

print("svi rows:", len(svi))
print("unique geoids:", svi["geoid"].nunique())


# %%
# Clean RPL Columns

rpl_cols = ["RPL_THEMES", "RPL_THEME1", "RPL_THEME2", "RPL_THEME3", "RPL_THEME4"]
svi[rpl_cols] = svi[rpl_cols].apply(pd.to_numeric, errors="coerce")
svi[rpl_cols] = svi[rpl_cols].replace(-999, pd.NA)

print("after cleaning RPL_THEMES:")
print("  range:", svi["RPL_THEMES"].min(), "to", svi["RPL_THEMES"].max())
print("  missing:", svi["RPL_THEMES"].isna().sum())


# %%
# ---------- CLEAN EP_ (raw percentages) FOR NYC-RELATIVE RECONSTRUCTION ----------

ep_cols = [
    "EP_POV150", "EP_UNEMP", "EP_HBURD", "EP_NOHSDP",          # Theme 1: socioeconomic
    "EP_AGE65", "EP_AGE17", "EP_DISABL", "EP_SNGPNT",          # Theme 2: household
    "EP_MINRTY", "EP_LIMENG",                                  # Theme 3: minority/language
    "EP_MUNIT", "EP_MOBILE", "EP_CROWD", "EP_NOVEH", "EP_GROUPQ",  # Theme 4: housing/transport
]
svi = clean_cdc_sentinels(svi, ep_cols)

# Sanity: no negatives
assert svi[ep_cols].min().min() >= 0, "EP_ still has negatives — cleanup broken"


# %%
# ---------- COMPUTE NYC-RELATIVE PERCENTILE RANKS ----------

nyc_fips = ("36005", "36047", "36061", "36081", "36085")  # Bronx, Kings, NY, Queens, Richmond
is_nyc = svi["geoid"].str.startswith(nyc_fips)
nyc_idx = svi[is_nyc].index

for col in ep_cols:
    svi.loc[nyc_idx, f"{col}_pct"] = svi.loc[nyc_idx, col].rank(pct=True)

pct_cols = [f"{c}_pct" for c in ep_cols]
svi["custom_svi_nyc"] = svi[pct_cols].mean(axis=1)

print("NYC tracts with custom_svi_nyc:",
      svi.loc[nyc_idx, "custom_svi_nyc"].notna().sum(), "/", len(nyc_idx))
print("range:", svi.loc[nyc_idx, "custom_svi_nyc"].min(),
      "to", svi.loc[nyc_idx, "custom_svi_nyc"].max())


# %%
# ---------- FILL RPL_THEMES FOR NYC ONLY ----------

svi["RPL_THEMES_clean"] = svi["RPL_THEMES"].copy()
svi["svi_reconstructed"] = False

# NYC tracts missing CDC rank → fill with NYC-relative reconstruction
fill_mask = is_nyc & svi["RPL_THEMES"].isna() & svi["custom_svi_nyc"].notna()
svi.loc[fill_mask, "RPL_THEMES_clean"] = svi.loc[fill_mask, "custom_svi_nyc"]
svi.loc[fill_mask, "svi_reconstructed"] = True

print("reconstructed NYC tracts:", svi["svi_reconstructed"].sum())
print("still missing in NYC:",
      (is_nyc & svi["RPL_THEMES_clean"].isna()).sum())

# Assert only on NYC, since we don't care about upstate
assert_unit_range(svi.loc[is_nyc, "RPL_THEMES_clean"].dropna(), "NYC RPL_THEMES_clean")

# %%
# ---------- BOROUGH MEDIAN IMPUTATION FOR REMAINING NaN ----------

county_to_borough = {
    "36005": "Bronx", "36047": "Brooklyn", "36061": "Manhattan",
    "36081": "Queens", "36085": "Staten Island",
}
svi["borough"] = svi["geoid"].str[:5].map(county_to_borough)

# Borough medians from NYC tracts that HAVE a valid CDC RPL_THEMES
valid_nyc = svi[is_nyc & svi["RPL_THEMES"].notna()]
borough_medians = valid_nyc.groupby("borough")["RPL_THEMES"].median()
print("Borough medians (from CDC-valid tracts):")
print(borough_medians)

# Fill remaining NaN in NYC with borough median
still_missing = is_nyc & svi["RPL_THEMES_clean"].isna()
svi["svi_imputed"] = False
svi.loc[still_missing, "RPL_THEMES_clean"] = (
    svi.loc[still_missing, "borough"].map(borough_medians)
)
svi.loc[still_missing, "svi_imputed"] = True

print("imputed (borough median):", svi["svi_imputed"].sum())
print("reconstructed (NYC-rel):", svi["svi_reconstructed"].sum())
print("still missing in NYC:", (is_nyc & svi["RPL_THEMES_clean"].isna()).sum())
assert_unit_range(svi.loc[is_nyc, "RPL_THEMES_clean"].dropna(), "NYC RPL_THEMES_clean")

# %%
# ---------- MERGE ----------

tracts_svi = tracts.merge(
    svi[["geoid", "RPL_THEMES_clean", "RPL_THEME1", "RPL_THEME2",
         "RPL_THEME3", "RPL_THEME4", "svi_reconstructed", "svi_imputed"]]
        .rename(columns={"RPL_THEMES_clean": "RPL_THEMES"}),
    on="geoid",
    how="left",
)

print("joined rows:", len(tracts_svi))
print("missing SVI in NYC:", tracts_svi["RPL_THEMES"].isna().sum())
print("reconstructed (NYC-relative):", tracts_svi["svi_reconstructed"].sum())
print("imputed (borough median):", tracts_svi["svi_imputed"].sum())


# %%
fig, ax = plt.subplots(figsize=(10, 10))

# Main choropleth — no missing_kwds, no legend_kwds
tracts_svi.plot(
    column="RPL_THEMES",
    cmap="Reds",
    legend=True,
    ax=ax,
    edgecolor="black",
    linewidth=0.2,
)

# Missing (the water tract) — plot as grey separately
tracts_svi[tracts_svi["RPL_THEMES"].isna()].plot(
    ax=ax, color="lightgrey", edgecolor="black", linewidth=0.2,
)

# Reconstructed (NYC-relative) — blue hatch
tracts_svi[tracts_svi["svi_reconstructed"] == True].plot(
    ax=ax, facecolor="none", edgecolor="blue", hatch="///", linewidth=0.5,
)

# Imputed (borough median) — orange hatch
tracts_svi[tracts_svi["svi_imputed"] == True].plot(
    ax=ax, facecolor="none", edgecolor="orange", hatch="xxx", linewidth=0.5,
)

ax.set_title("NYC SVI — blue hatch = NYC-relative recon, orange hatch = borough-median imputed, grey = no data")
ax.set_axis_off()
plt.savefig(FIGURES / "svi_map_clean.png", dpi=150, bbox_inches="tight")
plt.close()
print("saved figures/svi_map_clean.png")

# %%
# Loading Places 
places_raw = pd.read_csv(
    DATA / "places_nyc_full.csv", 
    dtype = {"LocationID": str, "CountyFIPS": str},
    low_memory = False,
)
print("total rows: ", len(places_raw))
print("total columns: ", sorted(places_raw["Year"].unique()))

# %% 
# Filter to Cancer 
places_cancer = places_raw[
    (places_raw["MeasureId"] == "CANCER") &
    (places_raw["DataValueTypeID"] == "CrdPrv")
].copy()

print("cancer rows (national):", len(places_cancer))
print("sample:")
print(places_cancer[["LocationID", "LocationName", "Data_Value", "TotalPop18plus"]].head(3))

# %%
# Check TotalPop18plus Usability 
n_ok = places_cancer["TotalPop18plus"].notna().sum()
n_total = len(places_cancer)
print(f"TotalPop18plus populated: {n_ok} / {n_total} ({n_ok / n_total:.1%})")
print("sample pop values:", places_cancer["TotalPop18plus"].head(5).tolist())

# %%
# Filter to NYC 
nyc_fips = ("36005", "36047", "36061", "36081", "36085")
places_nyc = places_cancer[
    places_cancer["LocationID"].str.startswith(nyc_fips)
].copy()

print("NYC cancer rows:", len(places_nyc))
print("unique tracts:", places_nyc["LocationID"].nunique())

# %%
# Clean sentinels 
places_nyc["Data_Value"] = pd.to_numeric(places_nyc["Data_Value"], errors="coerce")
places_nyc["Low_Confidence_Limit"] = pd.to_numeric(places_nyc["Low_Confidence_Limit"], errors="coerce")
places_nyc["High_Confidence_Limit"] = pd.to_numeric(places_nyc["High_Confidence_Limit"], errors="coerce")
places_nyc["TotalPop18plus"] = pd.to_numeric(places_nyc["TotalPop18plus"], errors="coerce")

for col in ["Data_Value", "Low_Confidence_Limit", "High_Confidence_Limit", "TotalPop18plus"]:
    places_nyc[col] = places_nyc[col].replace(-999, pd.NA)

print("cancer prevalence range:", places_nyc["Data_Value"].min(), "to", places_nyc["Data_Value"].max())
print("missing prevalence:", places_nyc["Data_Value"].isna().sum())
print("adult pop range:", places_nyc["TotalPop18plus"].min(), "to", places_nyc["TotalPop18plus"].max())

# %%
# Rename + Keep
places_nyc = places_nyc.rename(columns={
    "LocationID": "geoid",
    "Data_Value": "cancer_prev_pct",
    "Low_Confidence_Limit": "cancer_ci_low",
    "High_Confidence_Limit": "cancer_ci_high",
    "TotalPop18plus": "adult_pop",
})

places_nyc = places_nyc[[
    "geoid", "cancer_prev_pct", "cancer_ci_low", "cancer_ci_high", "adult_pop"
]].copy()

# %%
# compute estimated cancer patients
places_nyc["est_cancer_patients"] = (
    places_nyc["adult_pop"] * places_nyc["cancer_prev_pct"] / 100
)

print("estimated cancer patients per tract:")
print(places_nyc["est_cancer_patients"].describe())

# %%
# ---------- JOIN TO TRACTS_SVI ----------

tracts_svi_places = tracts_svi.merge(places_nyc, on="geoid", how="left")

print("joined rows:", len(tracts_svi_places))
print("missing cancer prevalence:", tracts_svi_places["cancer_prev_pct"].isna().sum())
print("missing adult pop:", tracts_svi_places["adult_pop"].isna().sum())
print("cancer prevalence range:", tracts_svi_places["cancer_prev_pct"].min(), "to", tracts_svi_places["cancer_prev_pct"].max())
print("total estimated patients (NYC):", int(tracts_svi_places["est_cancer_patients"].sum()))


# %%
# ---------- MAP: CANCER PREVALENCE ----------

fig, ax = plt.subplots(figsize=(10, 10))
tracts_svi_places.plot(
    column="cancer_prev_pct",
    cmap="OrRd",
    legend=True,
    legend_kwds={"shrink": 0.6},
    ax=ax,
    edgecolor="black",
    linewidth=0.2,
    missing_kwds={"color": "lightgrey", "label": "No data"},
)
ax.set_title("Cancer prevalence (% adults) by NYC census tract")
ax.set_axis_off()
plt.savefig(FIGURES / "cancer_map.png", dpi=150, bbox_inches="tight")
plt.close()
print("saved figures/cancer_map.png")

# %%
# Is TotalPop18plus populated for ANY measure, or is it broken across PLACES?
sample_measure = places_raw[places_raw["MeasureId"] == "OBESITY"].head(1000)
print("TotalPop18plus populated for OBESITY:", sample_measure["TotalPop18plus"].notna().sum(), "/", len(sample_measure))

# Of the 54 tracts with adult pop, how many have cancer prevalence too?
nyc_cancer_check = places_raw[
    (places_raw["MeasureId"] == "CANCER") &
    (places_raw["DataValueTypeID"] == "CrdPrv") &
    (places_raw["LocationID"].str.startswith(("36005","36047","36061","36081","36085")))
].copy()
print("NYC cancer rows with adult_pop:", nyc_cancer_check["TotalPop18plus"].notna().sum())

# %%
# Load ACS B01001
acs_raw = pd.read_csv(
    DATA / "acs_b01001_ny_tracts.csv", 
    dtype={"GEO_ID": str},
    skiprows=[1],  
    low_memory=False,
)
print("acs rows:", len(acs_raw))
print("first GEO_ID:", acs_raw["GEO_ID"].iloc[0])

# %%
# Extra GEOID
# "1400000US36061002400" → "36061002400"
acs_raw["geoid"] = acs_raw["GEO_ID"].str.split("US").str[-1]

# Filter to NYC counties
nyc_fips = ("36005", "36047", "36061", "36081", "36085")
acs_nyc = acs_raw[acs_raw["geoid"].str.startswith(nyc_fips)].copy()

print("NYC ACS rows:", len(acs_nyc))
print("unique geoids:", acs_nyc["geoid"].nunique())

# %%
# Compute adult population 
# Male 18+:   B01001_007E through B01001_025E
# Female 18+: B01001_031E through B01001_049E
male_adult_cols = [f"B01001_{i:03d}E" for i in range(7, 26)]
female_adult_cols = [f"B01001_{i:03d}E" for i in range(31, 50)]
adult_cols = male_adult_cols + female_adult_cols

# Coerce to numeric, replace -999 sentinels
acs_nyc[adult_cols] = acs_nyc[adult_cols].apply(pd.to_numeric, errors="coerce")
acs_nyc[adult_cols] = acs_nyc[adult_cols].replace(-999, pd.NA)

# Sum adult population per tract
acs_nyc["adult_pop"] = acs_nyc[adult_cols].sum(axis=1, min_count=1)

print("adult_pop range:", acs_nyc["adult_pop"].min(), "to", acs_nyc["adult_pop"].max())
print("total adult pop (NYC):", int(acs_nyc["adult_pop"].sum()))
# %%
# MERGE ACS ont TRACTS_SVI

tracts_acs = tracts_svi.merge(
    acs_nyc[["geoid", "adult_pop"]],
    on="geoid",
    how="left",
)

print("joined rows:", len(tracts_acs))
print("missing adult_pop:", tracts_acs["adult_pop"].isna().sum())
print("total adult pop in tracts:", int(tracts_acs["adult_pop"].sum()))
# %%
# Merge PLACES Cancer Prevalence

# Reuse places_nyc from earlier (already filtered to NYC cancer)
places_for_merge = places_nyc[["geoid", "cancer_prev_pct", "cancer_ci_low", "cancer_ci_high"]].copy()

tracts_full = tracts_acs.merge(places_for_merge, on="geoid", how="left")

print("final rows:", len(tracts_full))
print("missing cancer_prev_pct:", tracts_full["cancer_prev_pct"].isna().sum())
print("missing adult_pop:", tracts_full["adult_pop"].isna().sum())

# %%
#  COMPUTE ESTIMATED CANCER PATIENTS 

tracts_full["est_cancer_patients"] = (
    tracts_full["adult_pop"] * tracts_full["cancer_prev_pct"] / 100
)

print("total estimated cancer patients (NYC):",
      int(tracts_full["est_cancer_patients"].sum()))
# EXPECTED: ~350,000 - 420,000


# %%
# SAVE INTERIM 

tracts_full.to_file(DATA / "tracts_full.geojson", driver="GeoJSON")
print("saved tracts_full.geojson")