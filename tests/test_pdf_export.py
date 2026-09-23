"""PDF-Export: Sonderzeichen-Bereinigung (fpdf2 stuerzt bei "-" [Gedankenstrich], "EUR"-Zeichen,
Emoji, Minuszeichen U+2212 ab - mit den GENAUEN Zeichen testen), Randfaelle."""
import pytest

import rrs_evaluation as E
from rrs_pdf_export import generate_rrs_pdf, pdf_text


def test_pdf_text_replaces_en_dash_and_em_dash():
    assert "–" not in pdf_text("Kosten – Ausweichroute")
    assert "—" not in pdf_text("Kosten — Ausweichroute")


def test_pdf_text_replaces_euro_sign_with_eur():
    assert "EUR" in pdf_text("100 €")
    assert "€" not in pdf_text("100 €")


def test_pdf_text_replaces_unicode_minus_sign():
    assert "−" not in pdf_text("−5 %")


def test_pdf_text_strips_or_replaces_emoji():
    cleaned = pdf_text("🧭 📐 🎯 🛟 ⏱️ 🔮 🎲 ✅ ℹ️ ⚠️")
    cleaned.encode("latin-1")  # darf nicht crashen


def test_pdf_text_keeps_german_umlauts():
    text = pdf_text("Prämie für Nadelöhr, Ausweichroute, Wartekosten – Größe")
    assert "Prämie" in text and "Nadelöhr" in text and "Größe" in text


def test_pdf_text_result_is_always_latin1_encodable():
    tricky = "Nadelöhr–Route € ≥ ≤ → ≈ ± · „" '""' "‘’ ⚠️ ✅ ℹ️ 🧭📐🎯🛟⏱️🔮🎲 − Ω λ"
    pdf_text(tricky).encode("latin-1")


# ---------------------------------------------------------------------------------------------------
# PDF-Generierung: darf nicht abstuerzen, auch nicht an Randfaellen
# ---------------------------------------------------------------------------------------------------
def _pdf_for(k0="mittel", volatilitaet="normal", c_wait_pct=2, c_detour_pct=40, n_periods=10, seed=5):
    params = E.params_from_controls(k0, volatilitaet, c_wait_pct, c_detour_pct, n_periods)
    result = E.evaluate(params)
    shown = E.evaluate_shown_path(params, seed, result)
    return generate_rrs_pdf(k0, volatilitaet, c_wait_pct, c_detour_pct, n_periods, seed, params, result, shown)


def test_pdf_generation_does_not_crash_for_the_default_scenario():
    data = _pdf_for()
    assert data[:4] == b"%PDF"
    assert len(data) > 500


def test_pdf_generation_does_not_crash_at_zero_wait_cost():
    data = _pdf_for(c_wait_pct=0)
    assert data[:4] == b"%PDF"


def test_pdf_generation_does_not_crash_for_every_preset():
    import rrs_constants as C
    for name, cfg in C.PRESETS.items():
        data = _pdf_for(cfg["k0"], cfg["volatilitaet"], cfg["c_wait_pct"], cfg["c_detour_pct"], cfg["n_periods"],
                        cfg["seed"])
        assert data[:4] == b"%PDF", name


def test_pdf_generation_does_not_crash_at_the_smallest_period_count():
    data = _pdf_for(n_periods=5)
    assert data[:4] == b"%PDF"


def test_pdf_generation_does_not_crash_at_highest_starting_risk_level():
    data = _pdf_for(k0="sehr hoch")
    assert data[:4] == b"%PDF"
