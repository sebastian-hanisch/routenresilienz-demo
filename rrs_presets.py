"""Regler-Spezifikation, Permalink, Presets und Seed-Knopf (Standardmuster aus dem OR-Demo-Portfolio,
siehe rvm_presets.py in revenue-management-demo). Zwei Regler sind benannte Stufen statt eines
Zahlenbereichs (Ausgangsrisikostufe, Volatilitaet) - `options` in SettingSpec deckt beide Faelle ab.
Wartekosten- und Ausweichkosten-Regler sind GANZZAHLIGE Prozentpunkte (siehe rrs_constants.py)."""
import math
import random
from dataclasses import dataclass
from typing import Callable, Optional, Tuple

import streamlit as st

import rrs_constants as C


def _int_text(value):
    return str(int(value))


@dataclass(frozen=True)
class SettingSpec:
    url_param: str
    caster: Callable
    default: object
    lo: Optional[float] = None
    hi: Optional[float] = None
    step: Optional[float] = None
    options: Optional[Tuple] = None
    encoder: Callable = _int_text


SETTING_SPECS = {
    "k0_select": SettingSpec("k0", str, C.K0_DEFAULT, options=C.RISK_LABELS, encoder=str),
    "volatilitaet_select": SettingSpec("vol", str, C.VOLATILITY_DEFAULT, options=C.VOLATILITY_OPTIONS, encoder=str),
    "c_wait_slider": SettingSpec("wait", int, C.C_WAIT_PCT_DEFAULT, *C.C_WAIT_PCT_RANGE, 1),
    "c_detour_slider": SettingSpec("detour", int, C.C_DETOUR_PCT_DEFAULT, *C.C_DETOUR_PCT_RANGE, 1),
    "n_periods_slider": SettingSpec("n", int, C.N_PERIODS_DEFAULT, *C.N_PERIODS_RANGE, 1),
    "seed_input": SettingSpec("seed", int, C.SEED_DEFAULT, *C.SEED_RANGE, 1),
}

PRESET_STATE_KEYS = {
    "k0": "k0_select", "volatilitaet": "volatilitaet_select", "c_wait_pct": "c_wait_slider",
    "c_detour_pct": "c_detour_slider", "n_periods": "n_periods_slider", "seed": "seed_input",
}


def bounds(state_key):
    spec = SETTING_SPECS[state_key]
    return spec.lo, spec.hi


def options(state_key):
    return SETTING_SPECS[state_key].options


def _nearest_option(value, opts):
    return min(opts, key=lambda o: abs(o - value))


def parse_setting(spec, raw):
    """Wert aus der Adresszeile: umwandeln, auf den Bereich begrenzen bzw. auf die naechste Stufe
    klemmen. None, wenn er sich nicht auswerten laesst oder (bei String-Stufen) keine gueltige Stufe ist."""
    try:
        value = spec.caster(raw)
    except (ValueError, TypeError):
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if spec.options is not None:
        if isinstance(value, str):
            return value if value in spec.options else None
        return _nearest_option(value, spec.options)
    if spec.lo is not None:
        value = max(spec.lo, value)
    if spec.hi is not None:
        value = min(spec.hi, value)
    if spec.step and spec.step > 1 and spec.lo is not None:
        value = spec.lo + round((value - spec.lo) / spec.step) * spec.step
        value = min(spec.hi, value)
    return value


def init_session_state_defaults():
    for state_key, spec in SETTING_SPECS.items():
        if state_key not in st.session_state:
            st.session_state[state_key] = spec.default


def load_permalink_settings():
    if "permalink_loaded" in st.session_state:
        return
    qp = st.query_params
    for state_key, spec in SETTING_SPECS.items():
        if spec.url_param in qp:
            value = parse_setting(spec, qp[spec.url_param])
            if value is not None:
                st.session_state[state_key] = value
    st.session_state["permalink_loaded"] = True


def sync_query_params(values):
    """values: dict state_key -> aktueller Wert (aus den Widgets)."""
    try:
        for state_key, value in values.items():
            st.query_params[SETTING_SPECS[state_key].url_param] = SETTING_SPECS[state_key].encoder(value)
    except Exception:
        pass


def apply_preset(name):
    for field, state_key in PRESET_STATE_KEYS.items():
        st.session_state[state_key] = C.PRESETS[name][field]


def randomize_seed():
    """Wuerfelt einen neuen Seed fuer den gezeigten Risikopfad."""
    st.session_state["seed_input"] = random.randint(*C.SEED_RANGE)
