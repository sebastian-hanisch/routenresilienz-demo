"""Regler: Permalink-Parsing/-Klemmen/-Runden (inkl. Stufen-Regler auf die naechste Stufe), Presets
innerhalb ihrer eigenen Grenzen."""
import rrs_constants as C
from rrs_presets import SETTING_SPECS, parse_setting


def test_numeric_setting_is_clamped_to_its_range():
    spec = SETTING_SPECS["c_wait_slider"]
    assert parse_setting(spec, "999") == spec.hi
    assert parse_setting(spec, "-5") == spec.lo


def test_numeric_setting_rounds_to_the_nearest_step():
    spec = SETTING_SPECS["n_periods_slider"]
    # step=1, kein spezielles Runden noetig (int-Caster rundet implizit via int())
    assert parse_setting(spec, "12") == 12


def test_garbage_input_returns_none():
    spec = SETTING_SPECS["c_wait_slider"]
    assert parse_setting(spec, "abc") is None
    assert parse_setting(spec, "") is None


def test_non_finite_float_is_rejected():
    spec = SETTING_SPECS["c_detour_slider"]
    assert parse_setting(spec, "inf") is None
    assert parse_setting(spec, "nan") is None


def test_string_option_setting_accepts_only_exact_matches():
    spec = SETTING_SPECS["k0_select"]
    assert parse_setting(spec, "hoch") == "hoch"
    assert parse_setting(spec, "nonsense") is None


def test_string_option_setting_is_case_sensitive_and_rejects_close_misses():
    spec = SETTING_SPECS["volatilitaet_select"]
    assert parse_setting(spec, "Normal") is None  # Grossschreibung nicht in den Optionen
    assert parse_setting(spec, "normal") == "normal"


def test_numeric_option_setting_snaps_to_the_nearest_option():
    # keine numerischen Options-Regler in dieser Demo (nur String-Stufen) - trotzdem die Logik pruefen
    from rrs_presets import SettingSpec
    spec = SettingSpec("x", float, 1.0, options=(1.0, 2.0, 5.0))
    assert parse_setting(spec, "1.4") == 1.0
    assert parse_setting(spec, "3.6") == 5.0


# ---------------------------------------------------------------------------------------------------
# Presets: liegen innerhalb der eigenen Reglergrenzen
# ---------------------------------------------------------------------------------------------------
def test_every_preset_is_within_its_own_widget_bounds():
    for name, cfg in C.PRESETS.items():
        assert cfg["k0"] in C.RISK_LABELS, name
        assert cfg["volatilitaet"] in C.VOLATILITY_OPTIONS, name
        lo, hi = C.C_WAIT_PCT_RANGE
        assert lo <= cfg["c_wait_pct"] <= hi, name
        lo, hi = C.C_DETOUR_PCT_RANGE
        assert lo <= cfg["c_detour_pct"] <= hi, name
        lo, hi = C.N_PERIODS_RANGE
        assert lo <= cfg["n_periods"] <= hi, name
        lo, hi = C.SEED_RANGE
        assert lo <= cfg["seed"] <= hi, name


def test_preset_names_are_short_enough_for_a_button_label():
    assert all(len(name) <= 32 for name in C.PRESETS)


def test_there_are_exactly_five_presets_arranged_three_plus_two():
    assert len(C.PRESETS) == 5
