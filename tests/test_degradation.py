import numpy as np

from coldchain.degradation import (PolicyRule, arrhenius_factor, equivalent_hours, excess_weight,
                                   mean_kinetic_temperature, physics_loss, policy_loss)


def test_factor_is_one_at_reference_and_increases_with_temperature():
    assert abs(float(arrhenius_factor(25.0, 100.0, 25.0)) - 1.0) < 1e-12
    f = arrhenius_factor(np.array([5.0, 15.0, 25.0, 35.0]), 100.0, 25.0)
    assert np.all(np.diff(f) > 0)


def test_higher_activation_energy_amplifies_deviation_from_reference():
    assert arrhenius_factor(35.0, 120.0, 25.0) > arrhenius_factor(35.0, 60.0, 25.0)
    assert arrhenius_factor(5.0, 120.0, 25.0) < arrhenius_factor(5.0, 60.0, 25.0)


def test_equivalent_hours_at_reference_equals_elapsed_time():
    t = np.linspace(0, 10, 101)
    assert abs(equivalent_hours(t, np.full_like(t, 25.0), 100.0, 25.0) - 10.0) < 1e-9


def test_mkt_of_constant_temperature_is_that_temperature():
    assert abs(mean_kinetic_temperature(np.full(50, 7.3)) - 7.3) < 1e-9


def test_mkt_between_mean_and_max_for_variable_temperature():
    T = np.array([2.0, 5.0, 8.0, 20.0, 30.0])
    m = mean_kinetic_temperature(T)
    assert T.mean() <= m <= T.max()


def test_excess_weight_zero_at_or_below_setpoint():
    assert float(excess_weight(5.0, 5.0, 100.0, 25.0)) == 0.0
    assert float(excess_weight(3.0, 5.0, 100.0, 25.0)) == 0.0
    assert float(excess_weight(30.0, 5.0, 100.0, 25.0)) > 0.0


def test_policy_and_physics_rules():
    strict = PolicyRule(0.0)
    assert policy_loss([0.0, 0.1], strict).tolist() == [False, True]
    assert policy_loss([1.5], PolicyRule(2.0)).tolist() == [False]
    assert physics_loss([10.0, 100.0], 72.0).tolist() == [False, True]
