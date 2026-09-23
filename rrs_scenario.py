"""Routenresilienz bei Nadeloehr-Sperrung: Fachmodell (Params, Uebergangsmatrix, Kostenfunktionen)
und die seedbasierte Pfad-Realisierung fuer die Illustrationsgrafik.

Modell und Kernlogik unveraendert aus messreihe_resilienz/resilienz.py uebernommen - bereits gegen
6 unabhaengige Checks verifiziert (siehe check.py dort, in tests/test_solve.py als Pflichttests
portiert). Reine Standardbibliothek, keine Zufallszahlen in den gemessenen Kennzahlen - nur
`realize_path()` unten zieht Zufallszahlen, und nur fuer die illustrative Grafik, nicht fuer
die exakt berechneten Kennzahlen."""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Params:
    n_periods: int = 10          # N: Perioden bis zum letztmoeglichen Entscheidungszeitpunkt
    n_risk_levels: int = 5       # K: diskrete Risikostufen 0..K-1
    escalate_prob: float = 0.15  # Wahrscheinlichkeit fuer Risikostufe +1 pro Periode
    deescalate_prob: float = 0.15  # Wahrscheinlichkeit fuer Risikostufe -1 pro Periode
    k0: int = 1                  # Startrisikostufe
    p_closure_max: float = 0.5   # Sperrwahrscheinlichkeit bei hoechster Risikostufe (linear in k)
    premium_max: float = 0.15    # Kriegsrisikozuschlag bei hoechster Stufe, Anteil von c_direct_base
    c_direct_base: float = 1.0   # Basiskosten Direktroute (normiert)
    c_detour: float = 1.4        # Kosten Ausweichroute (normiert, fix, sicher)
    closure_penalty: float = 1.2  # Zusatzkosten bei Sperrung waehrend Direktfahrt (normiert)
    c_wait: float = 0.02         # Kosten je Periode Abwarten (Liegezeit/verlorene Charterzeit)

    def __post_init__(self) -> None:
        if self.n_risk_levels < 2:
            raise ValueError("n_risk_levels muss >= 2 sein")
        if self.n_periods < 1:
            raise ValueError("n_periods muss >= 1 sein")
        if not (0 <= self.k0 < self.n_risk_levels):
            raise ValueError("k0 ausserhalb 0..n_risk_levels-1")
        if self.escalate_prob + self.deescalate_prob > 1.0 + 1e-9:
            raise ValueError("escalate_prob + deescalate_prob > 1")


def build_transition(p: Params) -> list[list[float]]:
    """KxK-Uebergangsmatrix: Random Walk auf den Risikostufen mit reflektierenden Raendern."""
    K = p.n_risk_levels
    T = [[0.0] * K for _ in range(K)]
    for k in range(K):
        up = p.escalate_prob
        down = p.deescalate_prob
        stay = 1.0 - up - down
        if k == 0:
            stay += down
            down = 0.0
        if k == K - 1:
            stay += up
            up = 0.0
        if down:
            T[k][k - 1] += down
        T[k][k] += stay
        if up:
            T[k][k + 1] += up
    return T


def closure_prob(k: int, p: Params) -> float:
    return p.p_closure_max * k / (p.n_risk_levels - 1)


def premium(k: int, p: Params) -> float:
    return p.premium_max * p.c_direct_base * k / (p.n_risk_levels - 1)


def direct_cost_open(k: int, p: Params) -> float:
    return p.c_direct_base + premium(k, p)


def direct_cost_closed(k: int, p: Params) -> float:
    return p.c_direct_base + premium(k, p) + p.closure_penalty


def expected_direct_cost(k: int, p: Params) -> float:
    q = closure_prob(k, p)
    return (1 - q) * direct_cost_open(k, p) + q * direct_cost_closed(k, p)


def realize_path(p: Params, seed: int) -> list[int]:
    """Zieht EINEN Risikopfad ab k0 ueber n_periods Schritte der Markov-Kette, nur zur Illustration
    (Musterentnahme wie messreihe_resilienz/dump_sweep.py). Rueckgabe: Liste der Laenge
    n_periods+1 (Risikostufe je Periode 0..N)."""
    rng = random.Random(seed)
    T = build_transition(p)
    path = [p.k0]
    k = p.k0
    for _ in range(p.n_periods):
        probs = T[k]
        r = rng.random()
        acc = 0.0
        for kp, prob in enumerate(probs):
            acc += prob
            if r <= acc:
                k = kp
                break
        path.append(k)
    return path
