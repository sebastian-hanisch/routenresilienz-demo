"""Abnahmekriterien der Presets (Detailplan plan_resilienz.html, Abschnitt 7): welche Geschichte
erzaehlt jedes Beispielszenario, und woran erkennt man, dass sie traegt?

Einzige Quelle fuer `tools/tune_presets.py` (Abstimmung) und `tests/test_preset_stories.py` (Abnahme).
Anders als bei den simulationsbasierten Wellen der Seefracht-Linie ist hier ALLES exakt (keine
Stichprobe, kein Populations-/Sequenz-Split noetig) - eine einzige Kriterien-Funktion je Preset,
ausgewertet auf rrs_evaluation.Result der Presteinstellung selbst."""


def _pct(v):
    return f"{v:+.1f} %"


def criteria(name, result):
    """result: rrs_evaluation.Result. Rueckgabe: Liste (erfuellt, Text)."""
    sd, st_, gh = result.savings_vs_detour_pct, result.savings_vs_threshold_pct, result.gap_to_hindsight_pct
    if name == "Ruhige Lage":
        return [(sd >= 15.0, f"Ersparnis vs. immer Ausweichen >= 15 %: {_pct(sd)}")]
    if name == "Hormus-artige Dauerspannung":
        return [(sd <= 2.0, f"Ersparnis vs. immer Ausweichen <= 2 %: {_pct(sd)}"),
                (st_ >= 5.0, f"Ersparnis vs. Schwellwert >= 5 %: {_pct(st_)}")]
    if name == "Teure Ausweichroute":
        return [(sd >= 20.0, f"Ersparnis vs. immer Ausweichen >= 20 %: {_pct(sd)}")]
    if name == "Hohe Wartekosten":
        return [(st_ >= 25.0, f"Ersparnis vs. Schwellwert >= 25 %: {_pct(st_)}")]
    if name == "Volatile Lage":
        return [(gh >= 20.0, f"Abstand zu Hindsight >= 20 %: {_pct(gh)}")]
    raise KeyError(name)
