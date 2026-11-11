import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import outage_events as oe  # noqa: E402

T0 = datetime(2020, 8, 4, 12, 0)


def _decaying(half_life_h=6.0, peak=1000, hours=120):
    s = {}
    for i in range(int(hours * 4)):
        t = T0 + i * oe.STEP
        s[t] = int(round(peak * 0.5 ** ((i / 4.0) / half_life_h)))
    return s


def test_decay_recovers_known_half_life_and_remaining_fraction():
    s = _decaying()
    m = oe.decay_metrics(s, T0 + timedelta(hours=1))
    assert m["peak"] == 1000 and m["peak_time"] == T0
    hours, from_absent = m["crossings"][0.5]
    assert 6.0 <= hours <= 6.5 and from_absent is False
    assert abs(m["remaining"][12][0] - 0.25) < 0.01


def test_blank_value_is_unknown_not_zero():
    s = _decaying()
    s[T0 + timedelta(hours=6)] = None
    m = oe.decay_metrics(s, T0 + timedelta(hours=1))
    assert m["remaining"][6] == (None, "blank")


def test_absent_row_is_flagged_as_zero_or_gap():
    s = _decaying(hours=10)  # nothing after 10 hours
    m = oe.decay_metrics(s, T0 + timedelta(hours=1))
    frac, kind = m["remaining"][24]
    assert frac == 0.0 and kind == "absent"


def test_timestamp_parser_accepts_both_formats():
    assert oe.parse_ts("2021-09-02 06:15:00") == datetime(2021, 9, 2, 6, 15)
    assert oe.parse_ts("9/2/21 6:15") == datetime(2021, 9, 2, 6, 15)


def test_crossing_set_by_missing_rows_is_flagged():
    s = {T0 + i * oe.STEP: 100 for i in range(40)}  # flat for 10 hours, then no rows
    m = oe.decay_metrics(s, T0 + timedelta(hours=1))
    hours, from_absent = m["crossings"][0.5]
    assert abs(hours - 10.0) < 0.3 and from_absent is True
