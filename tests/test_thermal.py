import numpy as np

from coldchain.thermal import simulate_batch, tau_from_breach_time


def _run(outage, tau, backup=0.0, room=25.0, dt=0.02):
    return simulate_batch(outage, tau, 5.0, room, room, 4.0, backup, dt_hr=dt, horizon_hr=40.0)


def test_tau_roundtrip_crosses_threshold_at_breach_time():
    tau = tau_from_breach_time(3.0, 5.0, 25.0)
    T = 25.0 + (5.0 - 25.0) * np.exp(-3.0 / tau)
    assert abs(T - 8.0) < 1e-9


def test_hours_above_matches_analytic_constant_room():
    tau = float(tau_from_breach_time(3.0, 5.0, 25.0))
    r = _run(20.0, tau)
    assert abs(r["hours_above"][0] - 17.0) < 0.06


def test_backup_delays_breach_by_backup_duration():
    tau = float(tau_from_breach_time(3.0, 5.0, 25.0))
    r0, r5 = _run(20.0, tau), _run(20.0, tau, backup=5.0)
    assert abs((r0["hours_above"][0] - r5["hours_above"][0]) - 5.0) < 0.06


def test_short_outage_never_exceeds_threshold():
    tau = float(tau_from_breach_time(3.0, 5.0, 25.0))
    r = _run(1.0, tau)
    assert r["hours_above"][0] == 0.0 and r["peak_c"][0] < 8.0


def test_batch_matches_individual_runs():
    tau = float(tau_from_breach_time(3.0, 5.0, 25.0))
    durations = np.array([2.0, 6.0, 12.0])
    batch = _run(durations, tau)["hours_above"]
    single = np.array([_run(d, tau)["hours_above"][0] for d in durations])
    assert np.allclose(batch, single)


def test_temperature_never_exceeds_room_and_peak_monotone_in_outage():
    tau = float(tau_from_breach_time(3.0, 5.0, 25.0))
    peaks = [_run(d, tau)["peak_c"][0] for d in (1.0, 4.0, 10.0, 30.0)]
    assert all(b >= a for a, b in zip(peaks, peaks[1:])) and peaks[-1] <= 25.0 + 1e-9
