"""Auswertung: Params aus den Reglern bauen, Kennzahlen je Einstellung (DP, Baselines, Hindsight,
Ersparnisse), Kostenaufschluesselung (Wartekosten- gegen Routenkosten-Anteil unter einer Politik) und
die EINE gezeigte Pfad-Realisierung mit DP-/Schwellwert-Entscheidungspunkten (Plan Abschnitt 6).

Alles exakt (Zustandsverteilungen statt Simulation) - nur die gezeigte Pfad-Realisierung selbst ist
seedbasiert (nur zur Illustration, siehe rrs_scenario.realize_path). Reine Rechnung ohne Streamlit."""
from __future__ import annotations

from dataclasses import dataclass

import rrs_constants as C
from rrs_scenario import Params, expected_direct_cost, realize_path
from rrs_solve import dp_optimal, expected_cost_under_policy, hindsight_oracle, policy_wait_then_threshold


def params_from_controls(k0_label, volatilitaet, c_wait_pct, c_detour_pct, n_periods):
    k0 = C.RISK_LABELS.index(k0_label)
    escalate, deescalate = C.VOLATILITY_PARAMS[volatilitaet]
    return Params(
        n_periods=n_periods, n_risk_levels=C.N_RISK_LEVELS, escalate_prob=escalate, deescalate_prob=deescalate,
        k0=k0, p_closure_max=C.P_CLOSURE_MAX, premium_max=C.PREMIUM_MAX, c_direct_base=C.C_DIRECT_BASE,
        c_detour=C.c_detour_from_pct(c_detour_pct), closure_penalty=C.CLOSURE_PENALTY,
        c_wait=C.c_wait_from_pct(c_wait_pct),
    )


# ---------------------------------------------------------------------------------------------------
# Kennzahlen der eingestellten Route: DP, beide Baselines, Hindsight (Plan Abschnitt 6)
# ---------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Result:
    V: list
    policy: list
    T: list
    dp_cost: float
    detour_cost: float
    best_k_star: int
    threshold_cost: float
    hindsight_cost: float
    savings_vs_detour_pct: float
    savings_vs_threshold_pct: float
    gap_to_hindsight_pct: float


def best_fixed_threshold(params: Params) -> tuple[int, float]:
    best_k, best_cost = None, float("inf")
    for k_star in range(params.n_risk_levels):
        fn = policy_wait_then_threshold(k_star)
        cost = expected_cost_under_policy(lambda n, k, fn=fn, N=params.n_periods: fn(n, k, N), params)
        if cost < best_cost:
            best_k, best_cost = k_star, cost
    return best_k, best_cost


def evaluate(params: Params) -> Result:
    V, policy, T = dp_optimal(params)
    dp_cost = V[0][params.k0]
    detour_cost = params.c_detour
    best_k_star, threshold_cost = best_fixed_threshold(params)
    hindsight_cost = hindsight_oracle(params)
    savings_vs_detour = (detour_cost - dp_cost) / detour_cost * 100 if detour_cost else 0.0
    savings_vs_threshold = (threshold_cost - dp_cost) / threshold_cost * 100 if threshold_cost else 0.0
    gap_to_hindsight = (dp_cost - hindsight_cost) / hindsight_cost * 100 if hindsight_cost > 0 else 0.0
    return Result(
        V=V, policy=policy, T=T, dp_cost=dp_cost, detour_cost=detour_cost, best_k_star=best_k_star,
        threshold_cost=threshold_cost, hindsight_cost=hindsight_cost,
        savings_vs_detour_pct=savings_vs_detour, savings_vs_threshold_pct=savings_vs_threshold,
        gap_to_hindsight_pct=gap_to_hindsight,
    )


# ---------------------------------------------------------------------------------------------------
# Kostenaufschluesselung: Wartekosten-Anteil gegen Kosten der letztlich gewaehlten Route (exakt ueber
# die Zustandsverteilung, Plan Abschnitt 6 Kernabschnitt)
# ---------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class CostBreakdown:
    wait_cost: float
    route_cost: float
    expected_wait_periods: float

    @property
    def total(self) -> float:
        return self.wait_cost + self.route_cost


def cost_breakdown(policy_fn, params: Params) -> CostBreakdown:
    from rrs_scenario import build_transition

    K, N = params.n_risk_levels, params.n_periods
    T = build_transition(params)
    dist: dict[int, float] = {params.k0: 1.0}
    wait_cost = 0.0
    route_cost = 0.0
    expected_wait_periods = 0.0
    for n in range(N + 1):
        new_dist: dict[int, float] = {}
        for k, prob in dist.items():
            action = policy_fn(n, k)
            if action == "detour":
                route_cost += prob * params.c_detour
            elif action == "direct":
                route_cost += prob * expected_direct_cost(k, params)
            elif action == "wait":
                wait_cost += prob * params.c_wait
                expected_wait_periods += prob
                for kp in range(K):
                    tp = T[k][kp]
                    if tp:
                        new_dist[kp] = new_dist.get(kp, 0.0) + prob * tp
            else:
                raise ValueError(action)
        dist = new_dist
    return CostBreakdown(wait_cost=wait_cost, route_cost=route_cost, expected_wait_periods=expected_wait_periods)


def savings_vs_dp_pct(cost: float, dp_cost: float) -> float:
    """Wie viel eine Politik gegenueber dem DP-Optimum teurer ist, in Prozent ihrer eigenen Kosten
    (0 % fuer DP selbst)."""
    return (cost - dp_cost) / cost * 100 if cost else 0.0


def dp_breakdown(result: Result, params: Params) -> CostBreakdown:
    policy = result.policy
    return cost_breakdown(lambda n, k: policy[n][k], params)


def threshold_breakdown(result: Result, params: Params) -> CostBreakdown:
    fn = policy_wait_then_threshold(result.best_k_star)
    return cost_breakdown(lambda n, k, fn=fn, N=params.n_periods: fn(n, k, N), params)


# ---------------------------------------------------------------------------------------------------
# Die EINE gezeigte Pfad-Realisierung mit DP-/Schwellwert-Entscheidungspunkten (Plan Abschnitt 1/6,
# Muster messreihe_resilienz/dump_sweep.py)
# ---------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class ShownPath:
    seed: int
    path: list
    dp_commit_n: int
    dp_action: str
    k_at_commit: int
    schwelle_action: str
    k_at_n: int
    best_k_star: int


def evaluate_shown_path(params: Params, seed: int, result: Result) -> ShownPath:
    path = realize_path(params, seed)
    policy = result.policy
    dp_commit_n, dp_action = None, None
    for n, k in enumerate(path[:-1]):
        a = policy[n][k]
        if a != "wait":
            dp_commit_n, dp_action = n, a
            break
    if dp_commit_n is None:
        dp_commit_n = params.n_periods
        k_final = path[params.n_periods]
        dp_action = "detour" if params.c_detour <= expected_direct_cost(k_final, params) else "direct"
    k_at_commit = path[dp_commit_n]
    k_at_n = path[params.n_periods]
    schwelle_action = "direct" if k_at_n <= result.best_k_star else "detour"
    return ShownPath(
        seed=seed, path=path, dp_commit_n=dp_commit_n, dp_action=dp_action, k_at_commit=k_at_commit,
        schwelle_action=schwelle_action, k_at_n=k_at_n, best_k_star=result.best_k_star,
    )
