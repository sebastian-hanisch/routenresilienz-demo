"""Erfuellen die echten Presets ihre eigenen Abnahmekriterien? Alles exakt (keine Stichprobe), daher
reicht ein einziger Lauf je Preset - siehe tools/tune_presets.py fuer die Abstimmung."""
import pytest

import rrs_constants as C
import rrs_evaluation as E
import rrs_stories as ST


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_preset_satisfies_its_own_acceptance_criteria(name):
    cfg = C.PRESETS[name]
    params = E.params_from_controls(cfg["k0"], cfg["volatilitaet"], cfg["c_wait_pct"], cfg["c_detour_pct"],
                                    cfg["n_periods"])
    result = E.evaluate(params)
    for ok, text in ST.criteria(name, result):
        assert ok, f"{name}: {text}"


def test_ruhige_lage_and_hormus_are_at_opposite_ends_of_the_detour_savings_spectrum():
    """Kernaussage der Demo (Plan Abschnitt 1): der Vorsprung gegen "immer Ausweichen" ist
    regimeabhaengig - ruhige Lage deutlich positiv, Hormus nahe 0."""
    def savings(name):
        cfg = C.PRESETS[name]
        params = E.params_from_controls(cfg["k0"], cfg["volatilitaet"], cfg["c_wait_pct"], cfg["c_detour_pct"],
                                        cfg["n_periods"])
        return E.evaluate(params).savings_vs_detour_pct

    assert savings("Ruhige Lage") > savings("Hormus-artige Dauerspannung") + 10.0


def test_hohe_wartekosten_beats_the_reference_wave_baseline_advantage():
    """Der robusteste Hook der Welle (Plan Abschnitt 7): Ersparnis vs. Schwelle waechst deutlich mit
    den Wartekosten, staerker als bei den anderen Presets."""
    cfg = C.PRESETS["Hohe Wartekosten"]
    params = E.params_from_controls(cfg["k0"], cfg["volatilitaet"], cfg["c_wait_pct"], cfg["c_detour_pct"],
                                    cfg["n_periods"])
    result = E.evaluate(params)
    for other in C.PRESETS:
        if other == "Hohe Wartekosten":
            continue
        ocfg = C.PRESETS[other]
        oparams = E.params_from_controls(ocfg["k0"], ocfg["volatilitaet"], ocfg["c_wait_pct"], ocfg["c_detour_pct"],
                                         ocfg["n_periods"])
        oresult = E.evaluate(oparams)
        assert result.savings_vs_threshold_pct >= oresult.savings_vs_threshold_pct
