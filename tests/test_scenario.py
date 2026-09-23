"""Fachmodell: Params-Validierung, Uebergangsmatrix-Struktur, Kostenfunktionen, Pfad-Realisierung."""
import random

import pytest

from rrs_scenario import (Params, build_transition, closure_prob, direct_cost_closed, direct_cost_open,
                          expected_direct_cost, premium, realize_path)


# ---------------------------------------------------------------------------------------------------
# Params-Validierung
# ---------------------------------------------------------------------------------------------------
def test_params_defaults_are_valid():
    Params()


@pytest.mark.parametrize("kwargs", [
    dict(n_risk_levels=1), dict(n_periods=0), dict(k0=-1), dict(k0=5, n_risk_levels=5),
    dict(escalate_prob=0.6, deescalate_prob=0.6),
])
def test_params_rejects_invalid_combinations(kwargs):
    with pytest.raises(ValueError):
        Params(**kwargs)


def test_params_boundary_probabilities_sum_to_one_are_accepted():
    Params(escalate_prob=0.5, deescalate_prob=0.5)  # Summe genau 1.0, kein "stay"


# ---------------------------------------------------------------------------------------------------
# Uebergangsmatrix: stochastisch, reflektierende Raender
# ---------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("seed", range(10))
def test_transition_rows_sum_to_one(seed):
    rng = random.Random(seed)
    p = Params(n_risk_levels=rng.randint(2, 8), escalate_prob=rng.uniform(0.05, 0.4),
              deescalate_prob=rng.uniform(0.05, 0.4))
    T = build_transition(p)
    for row in T:
        assert abs(sum(row) - 1.0) < 1e-12
        assert all(v >= 0 for v in row)


def test_transition_reflects_at_lower_boundary():
    p = Params(n_risk_levels=5, escalate_prob=0.2, deescalate_prob=0.3)
    T = build_transition(p)
    # bei k=0 gibt es kein k=-1: die Abwaertswahrscheinlichkeit bleibt bei k=0 ("stay")
    assert T[0][0] == pytest.approx(1.0 - p.escalate_prob)
    assert T[0][1] == pytest.approx(p.escalate_prob)


def test_transition_reflects_at_upper_boundary():
    p = Params(n_risk_levels=5, escalate_prob=0.2, deescalate_prob=0.3)
    T = build_transition(p)
    K = p.n_risk_levels
    assert T[K - 1][K - 1] == pytest.approx(1.0 - p.deescalate_prob)
    assert T[K - 1][K - 2] == pytest.approx(p.deescalate_prob)


def test_transition_interior_state_has_three_nonzero_entries():
    p = Params(n_risk_levels=5, escalate_prob=0.2, deescalate_prob=0.3)
    T = build_transition(p)
    row = T[2]
    nonzero = [v for v in row if v > 0]
    assert len(nonzero) == 3


# ---------------------------------------------------------------------------------------------------
# Kostenfunktionen: monoton in der Risikostufe, geschlossen gegen Sperrfall
# ---------------------------------------------------------------------------------------------------
def test_closure_prob_is_zero_at_safest_and_max_at_riskiest():
    p = Params(n_risk_levels=5, p_closure_max=0.6)
    assert closure_prob(0, p) == 0.0
    assert closure_prob(4, p) == pytest.approx(0.6)


def test_premium_is_zero_at_safest_and_max_at_riskiest():
    p = Params(n_risk_levels=5, premium_max=0.2, c_direct_base=1.0)
    assert premium(0, p) == 0.0
    assert premium(4, p) == pytest.approx(0.2)


def test_expected_direct_cost_is_between_open_and_closed_cost():
    p = Params(n_risk_levels=5)
    for k in range(5):
        lo, hi = direct_cost_open(k, p), direct_cost_closed(k, p)
        assert lo <= expected_direct_cost(k, p) <= hi


def test_expected_direct_cost_nondecreasing_in_risk_level():
    p = Params(n_risk_levels=5)
    costs = [expected_direct_cost(k, p) for k in range(5)]
    assert costs == sorted(costs)


# ---------------------------------------------------------------------------------------------------
# Pfad-Realisierung (nur zur Illustration, seedbasiert)
# ---------------------------------------------------------------------------------------------------
def test_realize_path_is_deterministic_for_the_same_seed():
    p = Params(n_periods=10, k0=2)
    assert realize_path(p, 5) == realize_path(p, 5)


def test_realize_path_differs_for_different_seeds_typically():
    p = Params(n_periods=10, k0=2)
    paths = {tuple(realize_path(p, seed)) for seed in range(10)}
    assert len(paths) > 1


def test_realize_path_has_correct_length_and_starts_at_k0():
    p = Params(n_periods=7, k0=3, n_risk_levels=5)
    path = realize_path(p, 42)
    assert len(path) == p.n_periods + 1
    assert path[0] == p.k0


def test_realize_path_stays_within_risk_bounds():
    p = Params(n_periods=20, k0=0, n_risk_levels=5, escalate_prob=0.4, deescalate_prob=0.4)
    for seed in range(20):
        path = realize_path(p, seed)
        assert all(0 <= k < p.n_risk_levels for k in path)


def test_realize_path_moves_by_at_most_one_level_per_period():
    p = Params(n_periods=20, k0=2, n_risk_levels=5, escalate_prob=0.4, deescalate_prob=0.4)
    for seed in range(20):
        path = realize_path(p, seed)
        assert all(abs(path[i + 1] - path[i]) <= 1 for i in range(len(path) - 1))
