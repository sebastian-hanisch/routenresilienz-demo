"""Auswertung: Params aus Reglern, Kennzahlen gegen Direktrechnung, Kostenaufschluesselung, gezeigter
Pfad. Alles exakt - kein Stichprobenvergleich noetig (Detailplan Abschnitt 11)."""
import pytest

import rrs_constants as C
import rrs_evaluation as E
from rrs_solve import dp_optimal, expected_cost_under_policy, hindsight_oracle, policy_wait_then_threshold


def test_params_from_controls_maps_k0_label_and_volatility():
    p = E.params_from_controls("sehr hoch", "angespannt", 5, 60, 12)
    assert p.k0 == 4
    assert p.escalate_prob == C.VOLATILITY_PARAMS["angespannt"][0]
    assert p.deescalate_prob == C.VOLATILITY_PARAMS["angespannt"][1]
    assert p.n_periods == 12
    assert p.c_wait == pytest.approx(0.05)
    assert p.c_detour == pytest.approx(1.60)
    assert p.n_risk_levels == C.N_RISK_LEVELS
    assert p.p_closure_max == C.P_CLOSURE_MAX
    assert p.premium_max == C.PREMIUM_MAX
    assert p.closure_penalty == C.CLOSURE_PENALTY


def test_evaluate_matches_direct_dp_and_baseline_computation():
    params = E.params_from_controls("mittel", "normal", 2, 40, 10)
    result = E.evaluate(params)
    V, policy, _ = dp_optimal(params)
    assert result.dp_cost == pytest.approx(V[0][params.k0])
    assert result.detour_cost == pytest.approx(params.c_detour)
    assert result.hindsight_cost == pytest.approx(hindsight_oracle(params))

    best_k, best_cost = None, float("inf")
    for k_star in range(params.n_risk_levels):
        fn = policy_wait_then_threshold(k_star)
        cost = expected_cost_under_policy(lambda n, k, fn=fn, N=params.n_periods: fn(n, k, N), params)
        if cost < best_cost:
            best_k, best_cost = k_star, cost
    assert result.best_k_star == best_k
    assert result.threshold_cost == pytest.approx(best_cost)


def test_savings_percentages_are_internally_consistent():
    params = E.params_from_controls("gering", "ruhig", 2, 40, 10)
    result = E.evaluate(params)
    expected_sd = (result.detour_cost - result.dp_cost) / result.detour_cost * 100
    expected_st = (result.threshold_cost - result.dp_cost) / result.threshold_cost * 100
    expected_gh = (result.dp_cost - result.hindsight_cost) / result.hindsight_cost * 100
    assert result.savings_vs_detour_pct == pytest.approx(expected_sd)
    assert result.savings_vs_threshold_pct == pytest.approx(expected_st)
    assert result.gap_to_hindsight_pct == pytest.approx(expected_gh)


def test_savings_vs_dp_pct_is_zero_for_dp_itself():
    assert E.savings_vs_dp_pct(1.234, 1.234) == pytest.approx(0.0)


def test_savings_vs_dp_pct_handles_zero_cost():
    assert E.savings_vs_dp_pct(0.0, 0.0) == 0.0


def test_savings_vs_dp_pct_uses_cost_not_dp_cost_as_denominator():
    # (200 - 100) / 200 * 100 = 50 % - nicht 100 % (das waere der Fall bei dp_cost als Nenner)
    assert E.savings_vs_dp_pct(200.0, 100.0) == pytest.approx(50.0)


# ---------------------------------------------------------------------------------------------------
# Kostenaufschluesselung: Wartekosten- + Routenkosten-Anteil summieren exakt zu den Gesamtkosten
# ---------------------------------------------------------------------------------------------------
def test_cost_breakdown_sums_to_total_cost_for_dp():
    params = E.params_from_controls("hoch", "normal", 8, 42, 10)
    result = E.evaluate(params)
    bd = E.dp_breakdown(result, params)
    assert bd.total == pytest.approx(result.dp_cost)
    assert 0.0 <= bd.expected_wait_periods <= params.n_periods


def test_cost_breakdown_sums_to_total_cost_for_threshold():
    params = E.params_from_controls("hoch", "normal", 8, 42, 10)
    result = E.evaluate(params)
    bd = E.threshold_breakdown(result, params)
    assert bd.total == pytest.approx(result.threshold_cost)
    # die Schwellwert-Politik wartet immer bis zur letzten Periode
    assert bd.expected_wait_periods == pytest.approx(params.n_periods)


def test_dp_waits_no_more_than_the_threshold_baseline_on_average():
    """Kernbotschaft der Demo: der Vorsprung kommt aus WENIGER unnoetigem Warten."""
    for name, cfg in C.PRESETS.items():
        params = E.params_from_controls(cfg["k0"], cfg["volatilitaet"], cfg["c_wait_pct"], cfg["c_detour_pct"],
                                        cfg["n_periods"])
        result = E.evaluate(params)
        bd_dp = E.dp_breakdown(result, params)
        bd_th = E.threshold_breakdown(result, params)
        assert bd_dp.expected_wait_periods <= bd_th.expected_wait_periods + 1e-9, name


# ---------------------------------------------------------------------------------------------------
# Die gezeigte Pfad-Realisierung
# ---------------------------------------------------------------------------------------------------
def test_shown_path_commit_point_matches_the_policy():
    params = E.params_from_controls("mittel", "angespannt", 2, 40, 10)
    result = E.evaluate(params)
    shown = E.evaluate_shown_path(params, 5, result)
    assert len(shown.path) == params.n_periods + 1
    # vor dem Commit-Punkt muss die Politik entlang des Pfads "wait" gewesen sein
    for n in range(shown.dp_commit_n):
        assert result.policy[n][shown.path[n]] == "wait"
    if shown.dp_commit_n < params.n_periods:
        assert result.policy[shown.dp_commit_n][shown.k_at_commit] == shown.dp_action


def test_shown_path_threshold_action_matches_best_k_star():
    params = E.params_from_controls("mittel", "angespannt", 2, 40, 10)
    result = E.evaluate(params)
    shown = E.evaluate_shown_path(params, 5, result)
    expected = "direct" if shown.k_at_n <= result.best_k_star else "detour"
    assert shown.schwelle_action == expected


def test_shown_path_is_reproducible_for_the_same_seed():
    params = E.params_from_controls("mittel", "normal", 2, 40, 10)
    result = E.evaluate(params)
    a = E.evaluate_shown_path(params, 123, result)
    b = E.evaluate_shown_path(params, 123, result)
    assert a == b


def test_shown_path_commit_defaults_to_forced_decision_when_policy_never_commits_early():
    """Randfall: 1 Periode - policy[0] entscheidet in Periode 0 selbst schon (kein "wait" moeglich,
    ausser der einzigen Wartemoeglichkeit vor der Zwangsentscheidung bei n=1)."""
    params = E.params_from_controls("mittel", "normal", 2, 40, 1)
    result = E.evaluate(params)
    shown = E.evaluate_shown_path(params, 5, result)
    assert shown.dp_commit_n <= params.n_periods
