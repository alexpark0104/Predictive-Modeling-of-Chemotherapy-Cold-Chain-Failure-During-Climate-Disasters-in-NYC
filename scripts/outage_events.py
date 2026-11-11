"""Look closer at NYC outage events in the extracted EAGLE-I files (data/interim/nyc_outages_YEAR.csv).

    python scripts/outage_events.py around 2020 "2020-08-07 10:15:00"
    python scripts/outage_events.py decay  2020 "2020-08-04 22:45:00"

around : borough counts for the intervals around a timestamp (UTC). Use it to tell a sustained event from a
         one-interval spike that may be a data artifact.
decay  : for each borough, finds its peak within [anchor-6h, anchor+24h], then reports how much of that peak is
         still out after fixed lags and the first time the count stays below 50/10/1% of the peak for an hour.

Caveats (printed with every decay report):
* 'remaining fraction' approximates P(outage lasts longer than t) only if few NEW outages arrive after the peak.
* Restoration is not random: crews prioritize large groups, so this is not a clean survival curve.
* Absent rows mean zero outage OR a collection gap (shown as 0*); blank values are unknown (shown as blank).
* Timestamps are UTC (New York is UTC-4 in summer, UTC-5 in winter).
"""
import csv
import sys
from datetime import datetime, timedelta
from pathlib import Path

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


def decay_metrics(series_k: dict, anchor: datetime, horizon_h: int = 168):
    t_peak, peak = peak_in_window(series_k, anchor - timedelta(hours=6), anchor + timedelta(hours=24))
    if t_peak is None or peak == 0:
        return None
    remaining = {}
    for lag in LAGS_H:
        v, kind = get(series_k, t_peak + timedelta(hours=lag))
        remaining[lag] = (None if v is None else v / peak, kind)
    crossings = {}
    end = t_peak + timedelta(hours=horizon_h)
    for thr in THRESHOLDS:
        t = sustained_below(series_k, t_peak, end, thr * peak)
        if t is None:
            crossings[thr] = None
        else:
            hours = (t - t_peak).total_seconds() / 3600.0
            crossings[thr] = (hours, get(series_k, t)[1] == "absent")  # True: set by a missing row, not a number
    return {"peak_time": t_peak, "peak": peak, "remaining": remaining, "crossings": crossings}


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


def cmd_decay(series: dict, anchor: datetime):
    for k, name in NYC.items():
        m = decay_metrics(series[k], anchor)
        print(f"\n{name}")
        if m is None:
            print("  no outages found in the window")
            continue
        print(f"  peak {m['peak']} customers at {m['peak_time']} UTC")
        row = "  remaining fraction after lag (h): "
        for lag in LAGS_H:
            frac, kind = m["remaining"][lag]
            cell = "blank" if frac is None else f"{frac:.3f}" + ("*" if kind == "absent" else "")
            row += f"{lag}h={cell}  "
        print(row)
        for thr in THRESHOLDS:
            c = m["crossings"][thr]
            label = f"stays below {int(thr * 100)}% of peak after"
            if c is None:
                text = "> 168 h (not reached)"
            else:
                text = f"{c[0]:6.2f} h" + ("*" if c[1] else "")
            print(f"  {label:36s} {text}")
    print("\nCaveats: approximates a survival curve only if few new outages arrive after the peak; crews")
    print("prioritize large groups; * = no row (zero outage OR collection gap); blank = value missing.")
    print("A crossing marked * was set by a missing row, so it may reflect a gap, not a real restoration.")


def main(argv):
    if len(argv) < 3 or argv[0] not in ("around", "decay"):
        print(__doc__)
        return 1
    cmd, year, ts = argv[0], argv[1], argv[2]
    root = Path(__file__).resolve().parent.parent
    series = load_series(root / "data" / "interim" / f"nyc_outages_{year}.csv")
    (cmd_around if cmd == "around" else cmd_decay)(series, parse_ts(ts))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
