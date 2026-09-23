"""Preset-Abstimmung: traegt die Geschichte jedes Presets (Detailplan plan_resilienz.html,
Abschnitt 7) gegen die Abnahmekriterien in rrs_stories.py?

Aufruf (im Projektordner): ./venv/Scripts/python.exe tools/tune_presets.py

Anders als bei den simulationsbasierten Wellen der Seefracht-Linie ist hier ALLES exakt (keine
Stichprobe, kein Populations-/Sequenz-Split noetig, siehe rrs_stories.py) - ein einziger Lauf je
Preset reicht, das Ergebnis haengt nicht vom Zufall ab (der gezeigte Seed bestimmt nur die
illustrative Pfad-Grafik, nicht die gemessenen Kennzahlen). Fachmodell-Konstanten (n_risk_levels,
p_closure_max, premium_max, c_direct_base, closure_penalty) sind FEST (rrs_constants.py) - nur die
Regler-Dimensionen (k0, Volatilitaet, Wartekosten, Ausweichkosten, Perioden) werden je Preset
variiert."""
import sys

sys.path.insert(0, ".")
import rrs_constants as C
import rrs_evaluation as E
import rrs_stories as ST


def main():
    all_ok = True
    for name, cfg in C.PRESETS.items():
        params = E.params_from_controls(cfg["k0"], cfg["volatilitaet"], cfg["c_wait_pct"], cfg["c_detour_pct"],
                                        cfg["n_periods"])
        result = E.evaluate(params)
        print(f"\n### {name}  {cfg}")
        print(f"  dp={result.dp_cost:.4f} immer_ausweichen={result.detour_cost:.4f} "
              f"schwelle={result.threshold_cost:.4f} hindsight={result.hindsight_cost:.4f} "
              f"bester_k*={result.best_k_star}")
        print(f"  Ersparnis vs. immer Ausweichen: {result.savings_vs_detour_pct:+.2f} %  "
              f"vs. Schwelle: {result.savings_vs_threshold_pct:+.2f} %  "
              f"Abstand zu Hindsight: {result.gap_to_hindsight_pct:+.2f} %")
        for ok, text in ST.criteria(name, result):
            print(("  OK   " if ok else "  FAIL ") + text)
            all_ok = all_ok and ok
    print("\nalle Kriterien erfuellt" if all_ok else "\nMINDESTENS EIN KRITERIUM VERFEHLT - Presets nachschaerfen")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
