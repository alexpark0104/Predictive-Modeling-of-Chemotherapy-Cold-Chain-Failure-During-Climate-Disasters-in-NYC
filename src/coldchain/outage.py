"""Outage-duration distributions.

NOTE: a lognormal is a convenient starting point, not a validated model. Fit it to disaster-
conditioned data (EAGLE-I county outages, utility reports), check goodness of fit, and consider
mixtures by event type and network type (underground vs overhead). Durations here are
CONDITIONAL on an outage occurring; they say nothing about outage frequency.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np
from scipy import stats


@dataclass(frozen=True)
class LognormalOutage:
    mean_hr: float
    sigma: float

    @property
    def mu(self) -> float:
        return float(np.log(self.mean_hr) - 0.5 * self.sigma ** 2)

    @property
    def median_hr(self) -> float:
        return float(np.exp(self.mu))

    def sample(self, n: int, rng: np.random.Generator) -> np.ndarray:
        return rng.lognormal(self.mu, self.sigma, n)

    def survival(self, t_hr):
        return stats.lognorm.sf(t_hr, s=self.sigma, scale=np.exp(self.mu))


def fit_lognormal(durations_hr) -> LognormalOutage:
    """Maximum-likelihood lognormal fit to positive durations (hours)."""
    d = np.asarray(durations_hr, dtype=float)
    if np.any(d <= 0):
        raise ValueError("Durations must be positive.")
    logs = np.log(d)
    mu, sigma = float(np.mean(logs)), float(np.std(logs))
    return LognormalOutage(mean_hr=float(np.exp(mu + 0.5 * sigma ** 2)), sigma=sigma)


@dataclass(frozen=True)
class OutageMixture:
    weights: Tuple[float, ...]
    components: Tuple[LognormalOutage, ...]

    def sample(self, n: int, rng: np.random.Generator) -> np.ndarray:
        w = np.asarray(self.weights, dtype=float)
        idx = rng.choice(len(w), size=n, p=w / w.sum())
        out = np.empty(n)
        for i, comp in enumerate(self.components):
            m = idx == i
            out[m] = comp.sample(int(m.sum()), rng)
        return out
