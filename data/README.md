# Data registry

Raw data are NOT committed. Record provenance here so anyone can re-obtain the exact files.
Run `python scripts/make_manifest.py raw_data` after any change and commit `raw_data/MANIFEST.csv`.

| file | what | source URL | accessed | version/vintage | license | notes |
|---|---|---|---|---|---|---|
| 2020_Census_Tracts_*.geojson | NYC 2020 census tract boundaries | TODO | TODO | 2020 | TODO | |
| svi_ny_tract_2022.csv | CDC/ATSDR Social Vulnerability Index, NY | TODO | TODO | 2022 | public | only needed if you keep the equity analysis |
| places_nyc_full.csv | CDC PLACES tract estimates | TODO | TODO | TODO | public | ever-diagnosed cancer; NOT a treatment denominator |
| acs_b01001_ny_tracts.csv | ACS 5-year sex by age | TODO | TODO | TODO | public | |
| Sandy inundation zone | flood extent | TODO | TODO | 2012 | TODO | |
| ny_hospitals.csv | NYS DOH facility list | TODO | TODO | TODO | TODO | undocumented in v0.1 README |

## Still to acquire (see docs/ANALYSIS_PLAN.md)

- NYS Cancer Registry: HER2-positive breast cancer incidence, treatment duration
- EAGLE-I county outage records for the five NYC counties
- NYC/FEMA current flood and stormwater maps
- Facility list flagged for infusion/oncology pharmacy capability
