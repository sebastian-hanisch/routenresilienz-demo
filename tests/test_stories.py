"""Jedes Preset-Abnahmekriterium einzeln an kuenstlichen Werten pruefen, die genau an seiner Schwelle
kippen (Detailplan Abschnitt 7/12: Kriterien so testen, nicht nur am echten Preset)."""
from types import SimpleNamespace

import rrs_stories as ST


def _r(sd=0.0, st_=0.0, gh=0.0):
    return SimpleNamespace(savings_vs_detour_pct=sd, savings_vs_threshold_pct=st_, gap_to_hindsight_pct=gh)


def _ok(name, result):
    return all(ok for ok, _ in ST.criteria(name, result))


# ---------------------------------------------------------------------------------------------------
# Ruhige Lage: Ersparnis vs. immer Ausweichen >= 15 %
# ---------------------------------------------------------------------------------------------------
def test_ruhige_lage_tips_exactly_at_its_threshold():
    assert _ok("Ruhige Lage", _r(sd=15.0))
    assert _ok("Ruhige Lage", _r(sd=15.001))
    assert not _ok("Ruhige Lage", _r(sd=14.999))


# ---------------------------------------------------------------------------------------------------
# Hormus-artige Dauerspannung: Ersparnis vs. Ausweichen <= 2 % UND vs. Schwelle >= 5 %
# ---------------------------------------------------------------------------------------------------
def test_hormus_tips_exactly_at_both_thresholds():
    assert _ok("Hormus-artige Dauerspannung", _r(sd=2.0, st_=5.0))
    assert not _ok("Hormus-artige Dauerspannung", _r(sd=2.001, st_=5.0))
    assert not _ok("Hormus-artige Dauerspannung", _r(sd=2.0, st_=4.999))


def test_hormus_requires_both_criteria_not_just_one():
    # nur das erste Kriterium erfuellt (sd niedrig), das zweite (st_ hoch genug) verfehlt
    assert not _ok("Hormus-artige Dauerspannung", _r(sd=1.0, st_=0.0))
    # nur das zweite Kriterium erfuellt, das erste (sd niedrig genug) verfehlt
    assert not _ok("Hormus-artige Dauerspannung", _r(sd=50.0, st_=100.0))
    # beide erfuellt
    assert _ok("Hormus-artige Dauerspannung", _r(sd=1.0, st_=100.0))


# ---------------------------------------------------------------------------------------------------
# Teure Ausweichroute: Ersparnis vs. Ausweichen >= 20 %
# ---------------------------------------------------------------------------------------------------
def test_teure_ausweichroute_tips_exactly_at_its_threshold():
    assert _ok("Teure Ausweichroute", _r(sd=20.0))
    assert not _ok("Teure Ausweichroute", _r(sd=19.999))


# ---------------------------------------------------------------------------------------------------
# Hohe Wartekosten: Ersparnis vs. Schwelle >= 25 %
# ---------------------------------------------------------------------------------------------------
def test_hohe_wartekosten_tips_exactly_at_its_threshold():
    assert _ok("Hohe Wartekosten", _r(st_=25.0))
    assert not _ok("Hohe Wartekosten", _r(st_=24.999))


# ---------------------------------------------------------------------------------------------------
# Volatile Lage: Abstand zu Hindsight >= 20 %
# ---------------------------------------------------------------------------------------------------
def test_volatile_lage_tips_exactly_at_its_threshold():
    assert _ok("Volatile Lage", _r(gh=20.0))
    assert not _ok("Volatile Lage", _r(gh=19.999))


def test_unknown_preset_name_raises():
    import pytest
    with pytest.raises(KeyError):
        ST.criteria("Nicht vorhanden", _r())
