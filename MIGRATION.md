# Migration guide: keep the repo, start the rewrite

Goal: keep the GitHub repo and its history alive, freeze the prototype so nothing is lost, and do the new
work on a branch. Nothing here deletes history or requires taking the repo down.

Assumed v0.1 layout (adjust paths if yours differs):
`notebooks/explore.py`, `notebooks/coldchain.py`, `app.py`, `requirements.txt`, `figures/`, `raw_data/` (gitignored).

## 0. Before you start
```
git status                      # must be clean; commit or stash anything pending
git check-ignore -v raw_data    # confirms raw_data is ignored (it should print a .gitignore rule)
git ls-files raw_data | head    # should print nothing; if files appear, raw data were committed (see section C)
```

## A. Freeze the prototype, then branch
```
git tag -a v0.1-prototype -m "Prototype before review; numbers not citable"
git branch legacy-prototype
git push origin v0.1-prototype legacy-prototype
git switch -c rewrite
```
The tag and `legacy-prototype` branch preserve the exact prototype forever. On GitHub, turn the tag into a
Release marked "pre-release" so existing links and any citation of v0.1 still resolve.

## B. Move old code into legacy/ (keeps file history)
```
mkdir -p legacy
git mv notebooks/explore.py legacy/explore.py
git mv notebooks/coldchain.py legacy/coldchain.py
git mv app.py legacy/app.py
git mv requirements.txt legacy/requirements-v0.1.txt
git rm -r figures
```
`git rm -r figures` deletes the figures from the working tree; they remain in history. The legacy scripts find
the project root with `Path(__file__).resolve().parent.parent`, so from `legacy/` they still resolve the repo
root and `raw_data/` keeps working unchanged.

## C. The raw_data folder
- Do not delete it. It is your input data and it is not on GitHub (gitignored).
- Leave it where it is for now so the legacy scripts keep working. New code reads from it too.
- Separate raw from derived: `explore.py` writes `tracts_full.geojson` into `raw_data/`. That file is derived,
  not raw. Later, move derived files to `data/interim/` (gitignored) and keep `raw_data/` read-only in spirit.
- Record provenance in `data/README.md` (source URL, access date, version, license) for every file.
- Generate checksums: `python scripts/make_manifest.py raw_data` and commit only `raw_data/MANIFEST.csv`.
- Back it up outside the repo (cloud drive or external disk). Check each license before ever redistributing.
- If `git ls-files raw_data` printed files in step 0, data were committed at some point. Tell me and we will
  decide whether to remove them from history; do not rewrite history on your own without a backup.

## D. Add the new skeleton
Unzip the rewrite package somewhere else (not on top of the repo), then copy in:
```
cp -r /path/to/coldchain-nyc/{src,tests,scripts,docs,data,.github,pyproject.toml,MIGRATION.md} .
cp /path/to/coldchain-nyc/README.md ./README.md
cp /path/to/coldchain-nyc/legacy/README.md legacy/README.md
```
Do NOT overwrite your existing `.gitignore` blindly. Open the package's `.gitignore` and add any missing lines
to yours (it ignores `raw_data/*` except `MANIFEST.csv`, `data/raw`, `data/interim`, `outputs/`, `figures/`).
Then:
```
pip install -e ".[dev]"
pytest -q
git add -A
git commit -m "Start v0.2 rewrite: tested core model, parameter registry, legacy moved"
git push -u origin rewrite
```

## E. Keep main honest while you work
Visitors land on `main`. Open a tiny PR into main that only adds this banner at the top of the old README:

> **Status:** v0.1 prototype, under revision. Its numbers should not be cited (see `legacy/README.md`).
> Active work is on the `rewrite` branch.

## F. GitHub housekeeping
1. Repo description and topics: update to the new framing (scenario-based, policy vs physics).
2. Turn the checklist into Issues (one per P1 item) and a Project board; link them to PRs.
3. Open a **draft PR** from `rewrite` into `main` now so progress is visible and CI runs on every push.
4. Enable the Zenodo-GitHub integration, then cut a release when a version is stable to get a DOI.
5. When the framing settles, rename the repo (Settings > General). GitHub redirects old URLs and git remotes,
   so nothing breaks. Update your local remote afterward: `git remote set-url origin <new-url>`.
6. Merge `rewrite` into `main` only when: tests pass, `assert_publishable()` passes for any reported analysis,
   and the README matches what the code produces. Then tag `v0.2.0`.

## G. Suggested first commits on `rewrite`
1. Fill `data/README.md` (sources, dates) and commit `raw_data/MANIFEST.csv`.
2. Replace placeholder parameters one at a time (each in its own commit with the citation in `params.py`).
3. Write the geospatial layer (facilities, flood flags) in `src/` with tests, reusing ideas from `legacy/`.
4. Add the Sobol sensitivity script once the placeholders are gone.
