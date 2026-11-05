# Legacy (v0.1 prototype)

`explore.py` and `coldchain.py` are the original prototype scripts, kept unchanged for history and for
reproducing v0.1 outputs. Do NOT cite v0.1 numbers: the patient denominator is implausibly large (it applies
a treatment fraction to all ever-diagnosed adults), the 3-hour stability window is an unsourced constant, and
the Monte Carlo and tornado analyses have known inconsistencies. See the review notes and docs/ANALYSIS_PLAN.md.

These scripts locate the project root with `Path(__file__).resolve().parent.parent`, so they keep working from
this folder as long as `raw_data/` sits at the repository root. `app.py` (Streamlit) also belongs here; it
contains placeholder math and is not the model.

Some of the preprocessing logic (tract/ACS/PLACES joins) may be reused in the geospatial layer later; copy
pieces into `src/` with tests rather than editing these files.
