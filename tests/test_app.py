"""AppTest: Skelett und Footer, jedes Preset, Permalink, alle Regler an Min und Max, die bedingte
Meldung in beiden Zustaenden, PDF, Texte."""
import pathlib

import pytest
from streamlit.testing.v1 import AppTest

import rrs_constants as C
from rrs_presets import SETTING_SPECS

APP = str(pathlib.Path(__file__).resolve().parent.parent / "app.py")
FOOTER = ("Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
          "Operations Research und Machine Learning. Interesse an einer maßgeschneiderten Lösung für "
          "Ihr Unternehmen? [Kontakt aufnehmen](https://sebastianhanisch.net/kontakt.html)")


@pytest.fixture(autouse=True)
def clean_cache():
    """st.cache_data ist prozessweit: Tests, die Einstellungen aendern, duerfen keine zwischen-
    gespeicherten Ergebnisse anderer Tests sehen."""
    import streamlit as st
    st.cache_data.clear()
    yield


def fresh(**query):
    at = AppTest.from_file(APP, default_timeout=180)
    for k, v in query.items():
        at.query_params[k] = v
    at.run()
    assert not at.exception, at.exception
    return at


def set_and_run(at, **values):
    for key, value in values.items():
        if key == "seed_input":
            at.number_input(key=key).set_value(value)
        elif key in ("k0_select", "volatilitaet_select"):
            at.select_slider(key=key).set_value(value)
        else:
            at.slider(key=key).set_value(value)
    at.run()
    assert not at.exception, at.exception
    return at


def main_metrics(at):
    return [(m.label, m.value) for m in at.metric[:4]]


def click(at, label):
    next(b for b in at.button if b.label == label).click().run()
    assert not at.exception, at.exception
    return at


def message(at, needle):
    for group in (at.success, at.warning, at.info, at.error):
        for x in group:
            if needle in x.value:
                return x.value
    return None


# ---------------------------------------------------------------------------------------------------
# Skelett
# ---------------------------------------------------------------------------------------------------
def test_skeleton_and_footer():
    at = fresh()
    assert [h.value for h in at.sidebar.header] == ["⚙️ Einstellungen"]                # genau EIN Header
    assert len(at.title) == 1 and "Routenresilienz" in at.title[0].value
    assert any(v.value.startswith("## 🧭") for v in at.markdown)
    assert any(v.value.startswith("### 📐") for v in at.markdown)
    assert [e.label for e in at.expander] == ["🔧 Wie wir das erreichen – Politiken im Vergleich",
                                              "Wie funktioniert diese Demo?", "📐 Mathematische Formulierung"]
    assert any(c.value == FOOTER for c in at.caption)
    presets = [b.label for b in at.button if b.label in C.PRESETS]
    assert presets == list(C.PRESETS) and len(presets) == 5 and all(len(n) <= 32 for n in presets)
    assert [s.label for s in at.sidebar.select_slider] == ["Ausgangsrisikostufe", "Volatilität der Lage"]
    assert [s.label for s in at.sidebar.slider] == ["Wartekosten je Tag", "Kosten der Ausweichroute",
                                                    "Tage bis zur Weggabelung"]
    assert [n.label for n in at.sidebar.number_input] == ["Seed"]
    assert any(b.label == "🎲 Neuer Risikopfad" for b in at.sidebar.button)


def test_main_metrics_are_2x2_with_the_right_labels():
    at = fresh()
    labels = [m[0] for m in main_metrics(at)]
    assert labels == ["Kosten (DP)", "Kosten (immer Ausweichroute)", "Kosten (Abwarten + fester Schwellwert)",
                      "Ersparnis ggü. Schwellwert"]


def test_charts_are_present_with_unique_keys():
    at = fresh()
    charts = at.get("plotly_chart")
    keys = [c.key for c in charts]
    assert len(set(keys)) == len(keys) and all(keys)
    # Risikopfad + Politikgitter (Hauptansicht/Kernabschnitt) + 3 Baustein-Tabs (je Risikopfad) +
    # Vergleichs-Tab (Politikgitter + Kostenvergleich) = 7
    assert len(keys) == 7


# ---------------------------------------------------------------------------------------------------
# Presets, Permalink
# ---------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("name", list(C.PRESETS))
def test_every_preset_loads_within_widget_bounds_and_shows_its_story(name):
    at = fresh()
    click(at, name)
    preset = C.PRESETS[name]
    assert at.select_slider(key="k0_select").value == preset["k0"]
    assert at.select_slider(key="volatilitaet_select").value == preset["volatilitaet"]
    assert at.slider(key="c_wait_slider").value == preset["c_wait_pct"]
    assert at.slider(key="c_detour_slider").value == preset["c_detour_pct"]
    assert at.slider(key="n_periods_slider").value == preset["n_periods"]
    assert at.number_input(key="seed_input").value == preset["seed"]

    labels = [m[0] for m in main_metrics(at)]
    assert labels[0] == "Kosten (DP)"


def test_permalink_is_clamped_snapped_and_ignores_garbage():
    at = fresh(wait="999", detour="abc", k0="unsinn", vol="Normal", junk="ignored")
    assert at.slider(key="c_wait_slider").value == C.C_WAIT_PCT_RANGE[1]          # geklemmt
    assert at.slider(key="c_detour_slider").value == C.C_DETOUR_PCT_DEFAULT        # Muell ignoriert
    assert at.select_slider(key="k0_select").value == C.K0_DEFAULT                  # ungueltige Stufe ignoriert
    assert at.select_slider(key="volatilitaet_select").value == C.VOLATILITY_DEFAULT  # Grossschreibung nicht gueltig


def test_permalink_roundtrip_reflects_settings():
    at = fresh(k0="hoch", vol="angespannt", wait="6", detour="70", n="14", seed="11")
    values = {k: at.session_state[k] for k in SETTING_SPECS}
    assert values == {"k0_select": "hoch", "volatilitaet_select": "angespannt", "c_wait_slider": 6,
                      "c_detour_slider": 70, "n_periods_slider": 14, "seed_input": 11}
    for key, spec in SETTING_SPECS.items():
        got = at.query_params[spec.url_param]
        got = got[0] if isinstance(got, list) else got
        assert got == spec.encoder(at.session_state[key]), key


def test_new_path_button_changes_only_the_seed():
    at = fresh()
    before = {k: at.session_state[k] for k in SETTING_SPECS if k != "seed_input"}
    click(at, "🎲 Neuer Risikopfad")
    assert {k: at.session_state[k] for k in SETTING_SPECS if k != "seed_input"} == before
    assert C.SEED_RANGE[0] <= at.session_state["seed_input"] <= C.SEED_RANGE[1]


def test_new_path_button_actually_randomizes_not_just_stays_in_range():
    at = fresh()
    seeds = set()
    for _ in range(8):
        click(at, "🎲 Neuer Risikopfad")
        seeds.add(at.session_state["seed_input"])
    assert len(seeds) > 1


# ---------------------------------------------------------------------------------------------------
# Regler an den Grenzen
# ---------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("key,value", [
    ("c_wait_slider", C.C_WAIT_PCT_RANGE[0]), ("c_wait_slider", C.C_WAIT_PCT_RANGE[1]),
    ("c_detour_slider", C.C_DETOUR_PCT_RANGE[0]), ("c_detour_slider", C.C_DETOUR_PCT_RANGE[1]),
    ("n_periods_slider", C.N_PERIODS_RANGE[0]), ("n_periods_slider", C.N_PERIODS_RANGE[1]),
])
def test_every_slider_works_at_its_minimum_and_maximum(key, value):
    at = set_and_run(fresh(), **{key: value})
    assert at.session_state[key] == value and len(at.metric) >= 4


@pytest.mark.parametrize("value", list(C.RISK_LABELS))
def test_risk_level_select_works_at_every_step(value):
    at = set_and_run(fresh(), k0_select=value)
    assert at.session_state["k0_select"] == value


@pytest.mark.parametrize("value", list(C.VOLATILITY_OPTIONS))
def test_volatility_select_works_at_every_step(value):
    at = set_and_run(fresh(), volatilitaet_select=value)
    assert at.session_state["volatilitaet_select"] == value


def test_seed_input_works_at_its_minimum_and_maximum():
    at = set_and_run(fresh(), seed_input=C.SEED_RANGE[0])
    assert at.session_state["seed_input"] == C.SEED_RANGE[0]
    at = set_and_run(fresh(), seed_input=C.SEED_RANGE[1])
    assert at.session_state["seed_input"] == C.SEED_RANGE[1]


def test_extreme_combination_runs_without_exception():
    at = fresh(k0="sehr gering", vol="ruhig", wait="0", detour="10", n="5", seed="0")
    assert not at.exception
    at = fresh(k0="sehr hoch", vol="angespannt", wait="10", detour="150", n="20", seed="9999")
    assert not at.exception


# ---------------------------------------------------------------------------------------------------
# Bedingte Meldung
# ---------------------------------------------------------------------------------------------------
def test_message_detour_is_almost_optimal_for_the_hormus_preset():
    at = fresh()
    click(at, "Hormus-artige Dauerspannung")
    msg = message(at, "Ausweichen fast immer richtig")
    assert msg is not None


def test_message_waiting_pays_off_for_the_calm_preset():
    at = fresh()
    click(at, "Ruhige Lage")
    msg = message(at, "lohnt sich Abwarten")
    assert msg is not None


# ---------------------------------------------------------------------------------------------------
# Bausteine im Vergleich, PDF, Texte
# ---------------------------------------------------------------------------------------------------
def test_comparison_table_has_one_row_per_policy_plus_hindsight():
    at = fresh()
    dfs = at.dataframe
    comparison_df = dfs[-1].value
    assert list(comparison_df["Politik"])[:3] == [C.POLICY_LABELS[p] for p in C.POLICY_KEYS]
    assert "Hindsight" in comparison_df["Politik"].iloc[-1]
    assert "Ersparnis ggü. DP" in comparison_df.columns


def test_each_policy_tab_shows_a_risk_path_chart():
    at = fresh()
    charts = at.get("plotly_chart")
    assert sum(1 for c in charts if c.key.startswith("tab_detour_") or c.key.startswith("tab_threshold_")
              or c.key.startswith("tab_dp_")) == 3


def test_pdf_download_button_is_offered():
    at = fresh()
    buttons = at.get("download_button")
    assert len(buttons) == 1 and buttons[0].proto.label == "📄 Ergebnis als PDF herunterladen"


def test_texts_state_the_model_and_the_dp_recommendation():
    at = fresh()
    text = "\n".join(m.value for m in at.expander[1].markdown)
    for needle in ("Rückwärtsinduktion", "Nadelöhr", "Ausweichroute", "Schwellwertband", "Flottenblick"):
        assert needle in text, needle
    math_text = "\n".join(m.value for m in at.expander[2].markdown)
    for needle in ("Bellman", "Hindsight-Orakel", "V(n, k)"):
        assert needle in math_text, needle


def test_policy_grid_and_risk_path_are_both_in_the_main_view():
    at = fresh()
    charts = at.get("plotly_chart")
    assert any(c.key == "main_path_chart" for c in charts)
    assert any(c.key == "main_policy_grid" for c in charts)
