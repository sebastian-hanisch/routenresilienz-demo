"""Loeser: Rueckwaerts-Induktion (Bellman-Gleichung, exaktes optimales Stoppen), Vorwaerts-Erwartungswert
unter einer beliebigen Politik, feste Schwellwert-Baseline, Hindsight-Orakel.

Unveraendert aus messreihe_resilienz/resilienz.py uebernommen - bereits gegen 6 unabhaengige Checks
verifiziert (siehe messreihe_resilienz/check.py, hier als tests/test_solve.py portiert). Reine
Standardbibliothek, alles exakt ueber Zustandsverteilungen (keine Simulation, keine Zufallszahlen)."""

from __future__ import annotations

from rrs_scenario import Params, build_transition, closure_prob, direct_cost_closed, direct_cost_open, expected_direct_cost

Policy = list  # policy[n][k] in {"detour", "direct", "wait"}


def dp_optimal(p: Params) -> tuple[list[list[float]], Policy, list[list[float]]]:
    """Rueckwaertsinduktion. Gibt (V, policy, Uebergangsmatrix) zurueck; V[n][k] = optimaler
    Erwartungswert der Restkosten ab Periode n bei Risikostufe k."""
    K, N = p.n_risk_levels, p.n_periods
    T = build_transition(p)
    V: list[list[float]] = [[0.0] * K for _ in range(N + 1)]
    policy: Policy = [[""] * K for _ in range(N + 1)]

    for k in range(K):
        vd, vD = p.c_detour, expected_direct_cost(k, p)
        action, val = min((("detour", vd), ("direct", vD)), key=lambda x: x[1])
        V[N][k], policy[N][k] = val, action

    for n in range(N - 1, -1, -1):
        for k in range(K):
            vd = p.c_detour
            vD = expected_direct_cost(k, p)
            vW = p.c_wait + sum(T[k][kp] * V[n + 1][kp] for kp in range(K))
            action, val = min((("detour", vd), ("direct", vD), ("wait", vW)), key=lambda x: x[1])
            V[n][k], policy[n][k] = val, action
    return V, policy, T


def expected_cost_under_policy(policy_fn, p: Params) -> float:
    """Exakter Erwartungswert der Gesamtkosten unter einer beliebigen (n, k) -> Aktion Politik,
    per Vorwaertspropagation der Zustandsverteilung (keine Simulation, keine Zufallszahlen)."""
    K, N = p.n_risk_levels, p.n_periods
    T = build_transition(p)
    dist: dict[int, float] = {p.k0: 1.0}
    total = 0.0
    for n in range(N + 1):
        new_dist: dict[int, float] = {}
        for k, prob in dist.items():
            action = policy_fn(n, k)
            if action == "detour":
                total += prob * p.c_detour
            elif action == "direct":
                total += prob * expected_direct_cost(k, p)
            elif action == "wait":
                if n == N:
                    raise ValueError("Politik muss spaetestens in Periode N entscheiden")
                total += prob * p.c_wait
                for kp in range(K):
                    tp = T[k][kp]
                    if tp:
                        new_dist[kp] = new_dist.get(kp, 0.0) + prob * tp
            else:
                raise ValueError(f"unbekannte Aktion {action!r}")
        dist = new_dist
    remaining = sum(dist.values())
    if remaining > 1e-9:
        raise ValueError(f"Politik laesst {remaining:.2%} Masse unentschieden am Ende")
    return total


def policy_always_detour(n: int, k: int) -> str:
    return "detour"


def policy_wait_then_threshold(k_star: int):
    """Wartet bis zur letzten Periode, entscheidet dann anhand eines festen Schwellwerts - naive,
    aber informierte Heuristik ("Kapitaen beobachtet die Lage, entscheidet erst im letzten Moment
    nach Gefuehl")."""

    def fn(n: int, k: int, N: int) -> str:
        if n < N:
            return "wait"
        return "direct" if k <= k_star else "detour"

    return fn


def hindsight_oracle(p: Params) -> float:
    """Erwartungswert der Kosten bei vollstaendigem Vorwissen ueber den ganzen Risikopfad UND die
    Sperr-Realisierung an jedem Zeitpunkt: das Orakel darf zu jedem Zeitpunkt n=0..N aufhoeren und
    rueckblickend die bis dahin beste verfuegbare Option nehmen (inklusive sofortiger
    Ausweichroute ab n=0). Keine online umsetzbare Politik, nur eine obere Schranke fuer den Wert
    der Information. Exakt ueber die gemeinsame Verteilung von (Risikostufe, bisher bester Wert)
    berechnet, keine Simulation."""
    T = build_transition(p)
    K, N = p.n_risk_levels, p.n_periods
    dist: dict[tuple[int, float], float] = {(p.k0, p.c_detour): 1.0}
    for n in range(N + 1):
        new_dist: dict[tuple[int, float], float] = {}
        for (k, best), prob in dist.items():
            q = closure_prob(k, p)
            cost_open = n * p.c_wait + direct_cost_open(k, p)
            cost_closed = n * p.c_wait + direct_cost_closed(k, p)
            best_if_open = min(best, cost_open)
            best_if_closed = min(best, cost_closed)
            if n == N:
                new_dist[(k, best_if_open)] = new_dist.get((k, best_if_open), 0.0) + prob * (1 - q)
                new_dist[(k, best_if_closed)] = new_dist.get((k, best_if_closed), 0.0) + prob * q
            else:
                for kp in range(K):
                    tp = T[k][kp]
                    if not tp:
                        continue
                    new_dist[(kp, best_if_open)] = new_dist.get((kp, best_if_open), 0.0) + prob * (1 - q) * tp
                    new_dist[(kp, best_if_closed)] = new_dist.get((kp, best_if_closed), 0.0) + prob * q * tp
        dist = new_dist
    return sum(best * prob for (_, best), prob in dist.items())
