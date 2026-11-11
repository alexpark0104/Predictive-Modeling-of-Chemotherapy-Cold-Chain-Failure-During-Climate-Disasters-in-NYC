"""Look closer at NYC outage events in the extracted EAGLE-I files (data/interim/nyc_outages_YEAR.csv).

    python scripts/outage_events.py around 2020 "2020-08-07 10:15:00"
    python scripts/outage_events.py decay  2020 "2020-08-04 22:45:00"
    python scripts/outage_events.py decay  2020 "2020-08-04 22:45:00" --csv

around : borough counts for the intervals around a timestamp (UTC). Tells a sustained event from a one-interval
         spike. (Checked once against news reports: the 2020-08-07 Manhattan spike was a real transmission outage.)
decay  : for each borough, finds its peak within [anchor-6h, anchor+24h], estimates the ordinary baseline (median
         customers out over the 7 days ending 12h before the anchor), then reports how much of the peak, and of
         the peak EXCESS over baseline, is still out after fixed lags and when the excess stays below 50/10/1%.
         --csv also writes hourly curves to data/interim/decay_YEAR_<anchor>.csv for later modeling.

Caveats (printed with every decay report):
* 'remaining fraction' approximates P(outage lasts longer than t) only if few NEW outages arrive after the peak.
* Restoration is not random: crews prioritize large groups, so this is not a clean survival curve.
* Absent rows mean zero outage OR a collection gap (shown as 0*); blank values are unknown (shown as blank).
  The baseline treats absent rows as zero, which may understate it where gaps exist.
* 15-minute sampling understates very short peaks; timestamps are UTC (New York is UTC-4 in summer, -5 in winter).
"""
import csv
import sys
from datetime import datetime, timedelta
from pathlib import Path
from statistics import median

NYC = {
    "36005": "Bronx",
    "36047": "Brooklyn",
    "36061": "Manhattan",
    "36081": "Queens",
    "36085": "Staten Island",
}
STEP = timedelta(minutes=15)
LAGS_H = (3, 6, 12, 24, 48, 72, 96)
THRESHOLDS = (0.5, 0.1, 0.01)
MIN_RATIO = 3.0      # peak must be at least this multiple of baseline...
MIN_EXCESS = 100     # ...and exceed it by at least this many customers to count as an event


def parse_ts(s: str) -> datetime:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%m/%d/%y %H:%M"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            continue
    raise ValueError(f"Unrecognized timestamp: {s!r}")


def load_series(path: Path) -> dict:
    """{fips: {datetime: int or None}}; None marks a blank (unknown) value."""
    series = {k: {} for k in NYC}
    with Path(path).open(newline="") as f:
        reader = csv.reader(f)
        next(reader)
        for fips, out, ts in reader:
            try:
                value = int(float(out))
            except ValueError:
                value = None
            series[fips][parse_ts(ts)] = value
    return series


def get(series_k: dict, t: datetime):
    """(value, kind): kind is 'ok', 'blank' (unknown) or 'absent' (zero OR gap; value 0)."""
    if t in series_k:
        v = series_k[t]
        return (v, "ok") if v is not None else (None, "blank")
    return (0, "absent")


def peak_in_window(series_k: dict, t0: datetime, t1: datetime):
    best = (None, 0)
    for t, v in series_k.items():
        if v is not None and t0 <= t <= t1 and v > best[1]:
            best = (t, v)
    return best


def baseline_level(series_k: dict, anchor: datetime, days: int = 7, skip_hours: int = 12) -> float:
    """Median customers out over [anchor-days, anchor-skip_hours]; absent rows count as zero, blanks are skipped."""
    t, end, vals = anchor - timedelta(days=days), anchor - timedelta(hours=skip_hours), []
    while t <= end:
        v, kind = get(series_k, t)
        if kind != "blank":
            vals.append(v)
        t += STEP
    return float(median(vals)) if vals else 0.0


def sustained_below(series_k: dict, start: datetime, end: datetime, threshold: float, need: int = 4):
    """First time t >= start where `need` consecutive intervals are all below threshold (blank never counts)."""
    t = start
    while t <= end:
        ok = True
        for i in range(need):
            v, kind = get(series_k, t + i * STEP)
            if kind == "blank" or v >= threshold:
                ok = False
                break
        if ok:
            return t
        t += STEP
    return None


def _crossing(series_k, t_peak, end, threshold_count):
    t = sustained_below(series_k, t_peak, end, threshold_count)
    if t is None:
        return None
    return ((t - t_peak).total_seconds() / 3600.0, get(series_k, t)[1] == "absent")


def decay_metrics(series_k: dict, anchor: datetime, horizon_h: int = 168):
    t_peak, peak = peak_in_window(series_k, anchor - timedelta(hours=6), anchor + timedelta(hours=24))
    if t_peak is None or peak == 0:
        return None
    base = baseline_level(series_k, anchor)
    excess = peak - base
    distinguishable = peak >= MIN_RATIO * base and excess >= MIN_EXCESS
    remaining, remaining_adj = {}, {}
    for lag in LAGS_H:
        v, kind = get(series_k, t_peak + timedelta(hours=lag))
        remaining[lag] = (None if v is None else v / peak, kind)
        remaining_adj[lag] = (None if (v is None or not distinguishable) else max(v - base, 0.0) / excess, kind)
    end = t_peak + timedelta(hours=horizon_h)
    crossings = {thr: _crossing(series_k, t_peak, end, thr * peak) for thr in THRESHOLDS}
    crossings_adj = {thr: (_crossing(series_k, t_peak, end, base + thr * excess) if distinguishable else None)
                     for thr in THRESHOLDS}
    return {"peak_time": t_peak, "peak": peak, "baseline": base, "distinguishable": distinguishable,
            "remaining": remaining, "crossings": crossings,
            "remaining_adj": remaining_adj, "crossings_adj": crossings_adj}


def curve_rows(series_k: dict, m: dict, name: str, max_hours: int = 168):
    """Hourly curve rows for CSV export."""
    rows, peak, base = [], m["peak"], m["baseline"]
    excess = peak - base
    for h in range(0, max_hours + 1):
        v, kind = get(series_k, m["peak_time"] + timedelta(hours=h))
        raw = None if v is None else v / peak
        adj = None if (v is None or not m["distinguishable"]) else max(v - base, 0.0) / excess
        rows.append([name, h, v, kind, raw, adj, base, peak, m["peak_time"].strftime("%Y-%m-%d %H:%M:%S")])
    return rows


def cmd_around(series: dict, center: datetime, hours: int = 2):
    print(f"{'time (UTC)':20s}" + "".join(f"{n:>14s}" for n in NYC.values()) + f"{'citywide':>12s}")
    n = int(hours * 4)
    for i in range(-n, n + 1):
        t = center + i * STEP
        cells, total = [], 0
        for k in NYC:
            v, kind = get(series[k], t)
            cells.append("blank" if kind == "blank" else (f"{v}*" if kind == "absent" else str(v)))
            total += v or 0
        mark = "  <--" if i == 0 else ""
        print(f"{t:%Y-%m-%d %H:%M}".ljust(20) + "".join(f"{c:>14s}" for c in cells) + f"{total:12d}{mark}")
    print("\n* = no row (zero outage OR collection gap). 'blank' = row present but value missing.")


def _fmt(frac, kind):
    return "blank" if frac is None else f"{frac:.3f}" + ("*" if kind == "absent" else "")


def _fmt_cross(c):
    return "> 168 h (not reached)" if c is None else f"{c[0]:6.2f} h" + ("*" if c[1] else "")


def cmd_decay(series: dict, anchor: datetime, year: str, write_csv: bool = False):
    all_rows = []
    for k, name in NYC.items():
        m = decay_metrics(series[k], anchor)
        print(f"\n{name}")
        if m is None:
            print("  no outages found in the window")
            continue
        print(f"  peak {m['peak']} customers at {m['peak_time']} UTC; ordinary baseline ~{m['baseline']:.0f} customers")
        print("  raw fraction of peak after lag:      " + "  ".join(f"{l}h={_fmt(*m['remaining'][l])}" for l in LAGS_H))
        if not m["distinguishable"]:
            print("  NOT distinguishable from baseline in this window; baseline-adjusted results skipped.")
            continue
        print("  fraction of EXCESS after lag:        " + "  ".join(f"{l}h={_fmt(*m['remaining_adj'][l])}" for l in LAGS_H))
        for thr in THRESHOLDS:
            label = f"excess stays below {int(thr * 100)}% of peak excess after"
            print(f"  {label:48s} {_fmt_cross(m['crossings_adj'][thr])}")
        all_rows += curve_rows(series[k], m, name)
    print("\nCaveats: approximates a survival curve only if few new outages arrive after the peak; crews")
    print("prioritize large groups; * = no row (zero outage OR collection gap); blank = value missing.")
    print("A crossing marked * was set by a missing row, so it may reflect a gap, not a real restoration.")
    if write_csv and all_rows:
        slug = anchor.strftime("%Y%m%d_%H%M")
        out = Path(__file__).resolve().parent.parent / "data" / "interim" / f"decay_{year}_{slug}.csv"
        with out.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["borough", "hours_after_peak", "customers_out", "kind", "raw_fraction",
                        "excess_fraction", "baseline", "peak", "peak_time_utc"])
            w.writerows(all_rows)
        print(f"\nwrote {out.relative_to(Path(__file__).resolve().parent.parent)} ({len(all_rows)} rows)")


def main(argv):
    flags = [a for a in argv if a.startswith("--")]
    args = [a for a in argv if not a.startswith("--")]
    if len(args) < 3 or args[0] not in ("around", "decay"):
        print(__doc__)
        return 1
    cmd, year, ts = args[0], args[1], args[2]
    root = Path(__file__).resolve().parent.parent
    series = load_series(root / "data" / "interim" / f"nyc_outages_{year}.csv")
    if cmd == "around":
        cmd_around(series, parse_ts(ts))
    else:
        cmd_decay(series, parse_ts(ts), year, write_csv="--csv" in flags)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
