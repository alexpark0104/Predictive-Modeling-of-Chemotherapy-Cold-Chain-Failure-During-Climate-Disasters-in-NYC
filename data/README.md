# Data registry

Raw data are not committed to GitHub (v0.1 tracked two small files by accident; see notes). Record provenance
here so anyone can re-obtain the exact files. After any change, run
`python scripts/make_manifest.py raw_data` and commit `raw_data/MANIFEST.csv`.
Check each portal's terms of use before redistributing anything.

| file | what | source | file date | version | notes |
|---|---|---|---|---|---|
| 2020_Census_Tracts_20261016.geojson | NYC 2020 census tract boundaries | NYC Open Data (Dept. of City Planning), "2020 Census Tracts" | 2026-10-16 | 2020 tracts | 2,325 features, EPSG:4326 |
| acs_b01001_ny_tracts.csv | Sex by age, NY tracts | U.S. Census Bureau (data.census.gov), table B01001 | 2026-02-24 | 2024 ACS 5-year | used to compute adults 18+ per tract |
| svi_ny_tract_2022.csv | Social Vulnerability Index, NY | CDC/ATSDR SVI | 2026-10-16 | 2022 release, tract level | used for the 15 indicators; only needed for the equity analysis |
| places_nyc_full.csv | Tract-level health estimates | CDC PLACES, "Local Data for Better Health" | 2026-10-17 | 2024 release, crude prevalence | CANCER / CrdPrv; ever-diagnosed cancer prevalence, NOT a treatment denominator |
| ny_hospitals.csv | Health facility general information | NYS Dept. of Health (health.data.ny.gov) | 2026-11-03 | downloaded Nov 2026 | statewide, all facility types; NYC acute-care subset is built in code; needs an infusion-capable filter |
| flood.geojson | Hurricane Sandy storm-surge extent | NYC Open Data, "Sandy Inundation Zone" | 2026-10-26 | 2012 event | single historical event; tract overlay used "intersects" (any sliver) |
| tracts_full.geojson | DERIVED, not raw | produced by legacy/explore.py | 2026-10-26 | v0.1 | regenerates when explore.py reruns; its checksum is not stable; replace in the new pipeline |

## Notes
- v0.1 tracked `raw_data/ny_hospitals.csv` and `raw_data/svi_ny_tract_2022.csv` in git by accident. Both are small
  public files; untrack them later with `git rm --cached` once the new pipeline reads them.
- The prototype's "588 tracts intersect the flood zone" counts any overlap, however small. Prefer area- or
  population-weighted exposure.

## Still to acquire (see docs/ANALYSIS_PLAN.md)
- NYS Cancer Registry: HER2-positive breast cancer incidence and treatment duration
- EAGLE-I county outage records for the five NYC counties
- Current NYC/FEMA flood and stormwater maps
- A facility list flagged for infusion/oncology pharmacy capability
