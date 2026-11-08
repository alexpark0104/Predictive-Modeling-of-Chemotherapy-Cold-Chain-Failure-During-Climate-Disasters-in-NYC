"""Extract the five NYC counties from EAGLE-I yearly files and print a sanity summary.

Usage (from the repo root):
    python scripts/extract_nyc_outages.py            # defaults to 2021
    python scripts/extract_nyc_outages.py 2019 2020 2021
    python scripts/extract_nyc_outages.py 2021 --skip-extract   # reuse an existing data/interim file

Reads  raw_data/eaglei/eaglei_outages_YEAR.csv and raw_data/eaglei/MCC.csv
Writes data/interim/nyc_outages_YEAR.csv  (gitignored; regenerate from the raw files)

Notes on the data (EAGLE-I, ORNL):
* Rows with zero customers out are NOT in the file; a missing row can mean zero outage OR a gap.
* Timestamps are UTC. Customers are utility meters, not people.
* Outages under 15 minutes are not reliably captured.
* Some rows have a BLANK customers_out. They are counted as 'missing' and excluded from sums; they are
  never treated as zero, because a blank may be a collection gap.
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path

NYC = {
    "36005": "Bronx",
    "36047": "Kings (Brooklyn)",
    "36061": "New York (Manhattan)",
    "36081": "Queens",
    "36085": "Richmond (Staten Island)",
}


def extract(src: Path, dst: Path) -> int:
    """Copy only NYC rows (fips_code, customers_out, run_start_time) from src to dst. Returns row count."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with src.open(newline="") as f, dst.open("w", newline="") as g:
        reader = csv.reader(f)
        header = next(reader)
        idx = {name.strip(): i for i, name in enumerate(header)}
        fi, ci, ti = idx["fips_code"], idx["customers_out"], idx["run_start_time"]
        writer = csv.writer(g)
        writer.writerow(["fips_code", "customers_out", "run_start_time"])
        for row in reader:
            fips = row[fi].strip().zfill(5)
            if fips in NYC:
                writer.writerow([fips, row[ci], row[ti]])
                n += 1
    return n


def load_customers(mcc_path: Path) -> dict:
    """Modeled customers per county from MCC.csv (first two columns; header skipped)."""
    out = {}
    with mcc_path.open(newline="") as f:
        for row in csv.reader(f):
            if len(row) >= 2 and row[1].strip().isdigit():
                out[row[0].strip().zfill(5)] = int(row[1])
    return out


def summarize(dst: Path, customers: dict) -> dict:
    """Rows per county, each county's peak, and the citywide top intervals (UTC)."""
    rows = defaultdict(int)
    missing = defaultdict(int)
    peak = {}
    city = defaultdict(int)
    with dst.open(newline="") as f:
        reader = csv.reader(f)
        next(reader)
        for fips, out, ts in reader:
            try:
                out = int(float(out))
            except ValueError:
                missing[fips] += 1
                continue
            rows[fips] += 1
            if fips not in peak or out > peak[fips][0]:
                peak[fips] = (out, ts)
            city[ts] += out
    total = sum(customers.get(k, 0) for k in NYC)
    top = sorted(city.items(), key=lambda kv: kv[1], reverse=True)[:5]
    return {"rows": dict(rows), "missing": dict(missing), "peak": peak, "city_top": top,
            "total_customers": total}


def main(years, skip_extract=False):
    root = Path(__file__).resolve().parent.parent
    raw = root / "raw_data" / "eaglei"
    customers = load_customers(raw / "MCC.csv")
    for year in years:
        src = raw / f"eaglei_outages_{year}.csv"
        dst = root / "data" / "interim" / f"nyc_outages_{year}.csv"
        if skip_extract and dst.exists():
            print(f"\n=== {year}: reusing {dst.relative_to(root)} ===")
        else:
            print(f"\n=== {year}: reading {src.name} (large files take a minute or two) ===")
            n = extract(src, dst)
            print(f"wrote {dst.relative_to(root)} ({n} rows)")
        s = summarize(dst, customers)
        for fips, name in NYC.items():
            out, ts = s["peak"].get(fips, (0, "-"))
            cust = customers.get(fips, 0)
            pct = 100.0 * out / cust if cust else float("nan")
            print(f"  {name:26s} rows={s['rows'].get(fips, 0):6d} blank={s['missing'].get(fips, 0):5d}  peak={out:7d} ({pct:5.2f}% of {cust}) at {ts} UTC")
        print("  citywide top 5 intervals (customers out):")
        for ts, out in s["city_top"]:
            print(f"    {ts} UTC  {out:8d}  ({100.0 * out / s['total_customers']:.2f}% of {s['total_customers']})")


if __name__ == "__main__":
    args = sys.argv[1:]
    skip = "--skip-extract" in args
    years = [a for a in args if not a.startswith("--")] or ["2021"]
    main(years, skip_extract=skip)
