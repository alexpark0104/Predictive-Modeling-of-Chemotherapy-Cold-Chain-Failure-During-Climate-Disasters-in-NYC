import csv
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import extract_nyc_outages as ex  # noqa: E402


def _write(path, rows, header):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def test_extract_keeps_only_nyc_rows_and_summarizes_peaks():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        src, dst, mcc = d / "raw.csv", d / "out" / "nyc.csv", d / "MCC.csv"
        _write(src, [
            ["01003", "Baldwin", "Alabama", "6", "2021-01-01 00:00:00"],
            ["36061", "New York", "New York", "100", "2021-01-01 00:00:00"],
            ["36061", "New York", "New York", "900", "2021-01-01 00:15:00"],
            ["36047", "Kings", "New York", "50", "2021-01-01 00:15:00"],
            ["36999", "Fake", "New York", "7", "2021-01-01 00:15:00"],
        ], ["fips_code", "county", "state", "customers_out", "run_start_time"])
        _write(mcc, [["36061", "1000"], ["36047", "2000"]], ["County_FIPS", "Customers"])

        assert ex.extract(src, dst) == 3
        s = ex.summarize(dst, ex.load_customers(mcc))
        assert s["rows"] == {"36061": 2, "36047": 1}
        assert s["peak"]["36061"] == (900, "2021-01-01 00:15:00")
        assert s["city_top"][0] == ("2021-01-01 00:15:00", 950)


def test_load_customers_skips_header_and_keeps_leading_zeros():
    with tempfile.TemporaryDirectory() as d:
        mcc = Path(d) / "MCC.csv"
        _write(mcc, [["1001", "5"], ["36061", "873185"]], ["County_FIPS", "Customers"])
        got = ex.load_customers(mcc)
        assert got == {"01001": 5, "36061": 873185}


def test_blank_customers_out_is_counted_as_missing_not_zero():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        src, dst = d / "raw.csv", d / "nyc.csv"
        _write(src, [
            ["36061", "New York", "New York", "", "2021-01-01 00:00:00"],
            ["36061", "New York", "New York", "40", "2021-01-01 00:15:00"],
            ["36047", "Kings", "New York", "", "2021-01-01 00:15:00"],
        ], ["fips_code", "county", "state", "customers_out", "run_start_time"])
        assert ex.extract(src, dst) == 3
        s = ex.summarize(dst, {"36061": 1000, "36047": 2000})
        assert s["rows"] == {"36061": 1}
        assert s["missing"] == {"36061": 1, "36047": 1}
        assert s["peak"]["36061"] == (40, "2021-01-01 00:15:00")
