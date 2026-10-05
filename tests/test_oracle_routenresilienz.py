"""Orakel-Tests mit anderem Rechenweg: Pfadaufzählung (alle Risikopfade mit Wahrscheinlichkeit, alle Sperr-Realisierungen) statt Zustandsverteilung.
Prüft das Hindsight-Orakel exakt, den Schwellwert-Erwartungswert samt bestem Schwellwert und die Kostenaufschlüsselung."""
import itertools
import random

import pytest

import rrs_evaluation as EV
import rrs_solve as SV
from rrs_scenario import Params


def _trans(K, e, d):
    T = [[0.0] * K for _ in range(K)]
    for k in range(K):
        if k < K - 1:
            T[k][k + 1] = e
        if k > 0:
            T[k][k - 1] = d
        T[k][k] = 1 - (e if k < K - 1 else 0) - (d if k > 0 else 0)
    return T


def _paths(p):
    T = _trans(p.n_risk_levels, p.escalate_prob, p.deescalate_prob)
    for tail in itertools.product(range(p.n_risk_levels), repeat=p.n_periods):
        pr, prev = 1.0, p.k0
        for k in tail:
            pr *= T[prev][k]
            prev = k
        if pr > 0:
            yield (p.k0,) + tail, pr


def _q(k, p):
    return p.p_closure_max * k / (p.n_risk_levels - 1)


def _prem(k, p):
    return p.premium_max * p.c_direct_base * k / (p.n_risk_levels - 1)


def _hindsight(p):
    tot = 0.0
    for path, pr in _paths(p):
        for closed in itertools.product((0, 1), repeat=p.n_periods + 1):
            pc, best = 1.0, p.c_detour
            for n, k in enumerate(path):
                pc *= _q(k, p) if closed[n] else 1 - _q(k, p)
                best = min(best, n * p.c_wait + p.c_direct_base + _prem(k, p) + (p.closure_penalty if closed[n] else 0.0))
            tot += pr * pc * best
    return tot


def _policy_cost(policy, p):
    cost, waits = 0.0, 0.0
    for path, pr in _paths(p):
        c, w = 0.0, 0
        for n, k in enumerate(path):
            a = policy(n, k)
            if a == "wait":
                c, w = c + p.c_wait, w + 1
                continue
            c += p.c_detour if a == "detour" else p.c_direct_base + _prem(k, p) + _q(k, p) * p.closure_penalty
            break
        cost, waits = cost + pr * c, waits + pr * w
    return cost, waits


def _instances(count=25, seed=3):
    rng = random.Random(seed)
    for _ in range(count):
        K, N = rng.choice([2, 3, 4]), rng.choice([1, 2, 3])
        e = rng.choice([0.0, 0.15, rng.random() * 0.5])
        yield Params(n_periods=N, n_risk_levels=K, escalate_prob=e, deescalate_prob=rng.choice([0.0, 0.15, rng.random() * (1 - e)]), k0=rng.randrange(K),
                     p_closure_max=rng.choice([0.0, 0.5, rng.random()]), premium_max=rng.choice([0.0, 0.15, rng.random() * 0.4]),
                     c_detour=rng.choice([0.9, 1.4, 1.0 + rng.random()]), closure_penalty=rng.choice([0.0, 1.2, rng.random() * 2]),
                     c_wait=rng.choice([0.0, 0.02, rng.random() * 0.2]))


@pytest.mark.parametrize("p", list(_instances()))
def test_hindsight_threshold_and_breakdown_match_path_enumeration(p):
    N = p.n_periods
    assert SV.hindsight_oracle(p) == pytest.approx(_hindsight(p), abs=1e-9)
    V, pol, _ = SV.dp_optimal(p)
    cost, waits = _policy_cost(lambda n, k: pol[n][k], p)
    assert cost == pytest.approx(V[0][p.k0], abs=1e-9)                                       # DP-Wert = Pfadaufzählung der DP-Politik
    bd = EV.cost_breakdown(lambda n, k: pol[n][k], p)
    assert bd.expected_wait_periods == pytest.approx(waits, abs=1e-9) and bd.total == pytest.approx(cost, abs=1e-9)
    costs = []
    for ks in range(p.n_risk_levels):
        fn = SV.policy_wait_then_threshold(ks)
        costs.append(_policy_cost(lambda n, k, fn=fn: fn(n, k, N), p)[0])
    assert EV.best_fixed_threshold(p)[1] == pytest.approx(min(costs), abs=1e-9)
    assert min(costs) >= V[0][p.k0] - 1e-9                                                   # keine Baseline schlägt das Optimum
