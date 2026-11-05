import numpy as np

from coldchain.outage import LognormalOutage, OutageMixture, fit_lognormal


def test_sample_mean_matches_requested_mean():
    d = LognormalOutage(6.2, 1.0).sample(300_000, np.random.default_rng(1))
    assert abs(d.mean() / 6.2 - 1) < 0.03


def test_survival_at_median_is_half_and_decreasing():
    o = LognormalOutage(10.0, 0.8)
    assert abs(float(o.survival(o.median_hr)) - 0.5) < 1e-9
    s = o.survival(np.array([1.0, 5.0, 20.0, 100.0]))
    assert np.all(np.diff(s) < 0)


def test_fit_recovers_parameters():
    true = LognormalOutage(24.0, 0.7)
    fit = fit_lognormal(true.sample(300_000, np.random.default_rng(2)))
    assert abs(fit.sigma - 0.7) < 0.02 and abs(fit.mean_hr / 24.0 - 1) < 0.03


def test_mixture_mean_is_weighted_mean():
    a, b = LognormalOutage(2.0, 0.5), LognormalOutage(50.0, 0.5)
    m = OutageMixture((0.8, 0.2), (a, b)).sample(300_000, np.random.default_rng(3))
    assert abs(m.mean() / (0.8 * 2.0 + 0.2 * 50.0) - 1) < 0.03
