"""Loeser: die 6 Pflichtchecks aus messreihe_resilienz/check.py (unabhaengig verifiziert, hier
portiert) plus die Randfaelle aus dem Detailplan Abschnitt 11 (Wartekosten 0, Ausweichroute so teuer
wie die Direktroute im sichersten Fall, 1 Periode, hoechste Risikostufe von Anfang an)."""
import itertools
import random

import pytest

from rrs_scenario import Params, expected_direct_cost
from rrs_solve import dp_optimal, expected_cost_under_policy, hindsight_oracle, policy_wait_then_threshold

TOL = 1e-6


def _random_params(rng: random.Random) -> Params:
    return Params(
        n_periods=rng.randint(3, 14), n_risk_levels=rng.randint(2, 7), escalate_prob=rng.uniform(0.03, 0.35),
        deescalate_prob=rng.uniform(0.03, 0.35), k0=rng.randint(0, 1), p_closure_max=rng.uniform(0.1, 0.9),
        premium_max=rng.uniform(0.0, 0.3), c_direct_base=1.0, c_detour=rng.uniform(1.05, 2.2),
        closure_penalty=rng.uniform(0.1, 2.5), c_wait=rng.uniform(0.0, 0.05),
    )


# ---------------------------------------------------------------------------------------------------
# 1) Vorwaerts- = Rueckwaertsrechnung
# ---------------------------------------------------------------------------------------------------
def test_forward_matches_backward():
    rng = random.Random(1)
    for _ in range(30):
        params = _random_params(rng)
        V, policy, _ = dp_optimal(params)

        def policy_fn(n, k, policy=policy):
            return policy[n][k]

        forward = expected_cost_under_policy(policy_fn, params)
        backward = V[0][params.k0]
        assert abs(forward - backward) < TOL, (forward, backward, params)


# ---------------------------------------------------------------------------------------------------
# 2) Erschoepfende Politiksuche auf Mini-Instanzen: keine durchprobierte Politik schlaegt die DP
# ---------------------------------------------------------------------------------------------------
def test_exhaustive_tiny_instances():
    rng = random.Random(2)
    for _ in range(8):
        params = Params(
            n_periods=rng.choice([1, 2]), n_risk_levels=rng.choice([2, 3]), escalate_prob=rng.uniform(0.05, 0.4),
            deescalate_prob=rng.uniform(0.05, 0.4), k0=0, p_closure_max=rng.uniform(0.1, 0.9),
            premium_max=rng.uniform(0.0, 0.3), c_direct_base=1.0, c_detour=rng.uniform(1.0, 2.0),
            closure_penalty=rng.uniform(0.2, 2.0), c_wait=rng.uniform(0.0, 0.05),
        )
        V, policy, _ = dp_optimal(params)
        dp_value = V[0][params.k0]

        N, K = params.n_periods, params.n_risk_levels
        states = [(n, k) for n in range(N) for k in range(K)]
        best_over_all = float("inf")
        for combo in itertools.product(["detour", "direct", "wait"], repeat=len(states)):
            assignment = dict(zip(states, combo))

            def policy_fn(n, k, assignment=assignment, N=N, params=params):
                if n == N:
                    vd, vD = params.c_detour, expected_direct_cost(k, params)
                    return "detour" if vd <= vD else "direct"
                return assignment[(n, k)]

            try:
                cost = expected_cost_under_policy(policy_fn, params)
            except ValueError:
                continue
            best_over_all = min(best_over_all, cost)
        assert abs(best_over_all - dp_value) < TOL, ("DP sollte optimal sein", best_over_all, dp_value)


# ---------------------------------------------------------------------------------------------------
# 3) V(n,k) faellt nicht in k
# ---------------------------------------------------------------------------------------------------
def test_monotonic_in_risk():
    rng = random.Random(3)
    for _ in range(30):
        params = _random_params(rng)
        V, _, _ = dp_optimal(params)
        for n in range(params.n_periods + 1):
            row = V[n]
            for k in range(len(row) - 1):
                assert row[k] <= row[k + 1] + 1e-9, (n, k, row, params)


# ---------------------------------------------------------------------------------------------------
# 4) Hindsight schlaegt nie das DP-Optimum
# ---------------------------------------------------------------------------------------------------
def test_hindsight_never_worse_than_dp():
    rng = random.Random(4)
    for _ in range(30):
        params = _random_params(rng)
        V, _, _ = dp_optimal(params)
        dp_value = V[0][params.k0]
        hindsight = hindsight_oracle(params)
        assert hindsight <= dp_value + 1e-9, (hindsight, dp_value, params)


# ---------------------------------------------------------------------------------------------------
# 5) V(n,k) steigt nie mit weniger verbleibender Zeit
# ---------------------------------------------------------------------------------------------------
def test_value_nonincreasing_in_remaining_time():
    rng = random.Random(6)
    for _ in range(30):
        params = _random_params(rng)
        V, _, _ = dp_optimal(params)
        for n in range(params.n_periods):
            for k in range(params.n_risk_levels):
                assert V[n][k] <= V[n + 1][k] + 1e-9, (n, k, V[n][k], V[n + 1][k], params)


# ---------------------------------------------------------------------------------------------------
# 6) DP schlaegt beide naiven Baselines
# ---------------------------------------------------------------------------------------------------
def test_dp_beats_both_naive_baselines():
    rng = random.Random(5)
    for _ in range(20):
        params = _random_params(rng)
        V, _, _ = dp_optimal(params)
        dp_value = V[0][params.k0]

        always_detour = expected_cost_under_policy(lambda n, k: "detour", params)
        assert dp_value <= always_detour + 1e-9

        for k_star in range(params.n_risk_levels):
            fn = policy_wait_then_threshold(k_star)
            cost = expected_cost_under_policy(lambda n, k, fn=fn, N=params.n_periods: fn(n, k, N), params)
            assert dp_value <= cost + 1e-9, (dp_value, cost, k_star, params)


# ---------------------------------------------------------------------------------------------------
# Randfaelle (Detailplan Abschnitt 11)
# ---------------------------------------------------------------------------------------------------
def test_zero_wait_cost_does_not_crash_and_stays_optimal():
    """Wartekosten 0: die DP bleibt wohldefiniert und weiterhin mindestens so gut wie beide
    Baselines - aber NICHT "an der sichersten Risikostufe wird immer gewartet" (das ist falsch,
    siehe die allgemeinere, bewiesene Eigenschaft oben)."""
    params = Params(c_wait=0.0, n_periods=10, n_risk_levels=5, k0=1)
    V, policy, _ = dp_optimal(params)
    always_detour = expected_cost_under_policy(lambda n, k: "detour", params)
    assert V[0][params.k0] <= always_detour + 1e-9
    # an der sichersten Risikostufe (k=0) muss "wait" NICHT ueberall optimal sein
    assert not all(policy[n][0] == "wait" for n in range(params.n_periods))


def test_detour_cost_equal_to_direct_cost_at_safest_level():
    """Ausweichroute genauso teuer wie die Direktroute im sichersten Fall (k=0, keine Sperrung/
    Praemie dort): DP muss weiterhin eine wohldefinierte, konsistente Politik liefern."""
    params = Params(n_risk_levels=5, c_direct_base=1.0, c_detour=1.0, k0=0, premium_max=0.2, p_closure_max=0.5)
    V, policy, _ = dp_optimal(params)

    def policy_fn(n, k, policy=policy):
        return policy[n][k]

    forward = expected_cost_under_policy(policy_fn, params)
    assert abs(forward - V[0][params.k0]) < TOL
    # bei k=0 ist expected_direct_cost == c_detour == 1.0: "direct" und "detour" gleichwertig
    assert expected_direct_cost(0, params) == pytest.approx(params.c_detour)


def test_single_period_forces_immediate_decision():
    """1 Periode (n_periods=1): keine Wartemoeglichkeit ausser in Periode 0, in Periode 1 wird
    immer erzwungen entschieden."""
    params = Params(n_periods=1, n_risk_levels=5, k0=2)
    V, policy, _ = dp_optimal(params)
    assert policy[1][2] in ("direct", "detour")
    assert all(policy[1][k] in ("direct", "detour") for k in range(params.n_risk_levels))


def test_starting_at_highest_risk_level():
    """Hoechste Risikostufe von Anfang an (k0 = K-1): DP bleibt wohldefiniert, und Ausweichen ist
    typischerweise (aber nicht per Definition) die dominante fruehe Wahl."""
    params = Params(n_periods=10, n_risk_levels=5, k0=4, c_detour=1.4)
    V, policy, T = dp_optimal(params)

    def policy_fn(n, k, policy=policy):
        return policy[n][k]

    forward = expected_cost_under_policy(policy_fn, params)
    assert abs(forward - V[0][params.k0]) < TOL
    always_detour = expected_cost_under_policy(lambda n, k: "detour", params)
    assert V[0][params.k0] <= always_detour + 1e-9


def test_terminal_period_picks_the_cheaper_of_direct_and_detour_explicitly():
    """V[N][k]/policy[N][k] muss explizit das GUENSTIGERE von Direktroute und Ausweichroute sein -
    nicht nur "irgendeine" Wahl, die zufaellig durch die uebrigen Perioden ausgeglichen wird (die
    min(vd,vD,wait)-Rueckfallmoeglichkeit an jeder frueheren Periode kann eine falsche Terminal-
    entscheidung sonst verschleiern, siehe tools/mutation_check.py)."""
    rng = random.Random(8)
    for _ in range(15):
        params = _random_params(rng)
        V, policy, _ = dp_optimal(params)
        for k in range(params.n_risk_levels):
            expected_cost = min(params.c_detour, expected_direct_cost(k, params))
            expected_action = "detour" if params.c_detour <= expected_direct_cost(k, params) else "direct"
            assert V[params.n_periods][k] == pytest.approx(expected_cost), (k, params)
            assert policy[params.n_periods][k] == expected_action, (k, params)


def test_threshold_policy_chooses_direct_exactly_at_the_threshold_level():
    """policy_wait_then_threshold(k_star) muss bei GENAU k=k_star die Direktroute waehlen (<=, nicht
    <) - sonst verschiebt sich die Politik unbemerkt, weil min(vd,vD,wait) an frueheren Perioden den
    Unterschied sonst kaschiert."""
    for k_star in range(5):
        fn = policy_wait_then_threshold(k_star)
        assert fn(10, k_star, 10) == "direct"
        if k_star + 1 < 5:
            assert fn(10, k_star + 1, 10) == "detour"


def test_hindsight_oracle_never_exceeds_immediate_detour_cost():
    """Das Hindsight-Orakel darf ab n=0 sofort ausweichen - es kann also nie schlechter sein als
    c_detour selbst."""
    rng = random.Random(7)
    for _ in range(10):
        params = _random_params(rng)
        assert hindsight_oracle(params) <= params.c_detour + 1e-9


def test_expected_cost_under_policy_rejects_wait_in_final_period():
    params = Params(n_periods=3)
    with pytest.raises(ValueError, match="spätestens in Periode N"):
        expected_cost_under_policy(lambda n, k: "wait", params)


def test_expected_cost_under_policy_rejects_unknown_action():
    params = Params(n_periods=3)
    with pytest.raises(ValueError):
        expected_cost_under_policy(lambda n, k: "fly", params)
