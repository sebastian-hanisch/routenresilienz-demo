"""Konstanten der Routenresilienz-Demo (Zusatz zur Geschwindigkeitsoptimierung, Seefracht-Linie).

Modell und Zahlen aus messreihe_resilienz/ (siehe seefracht-planung/plan_resilienz.html,
messreihe_resilienz/ERGEBNIS.md). Fachmodell-Konstanten (n_risk_levels, p_closure_max, premium_max,
c_direct_base, closure_penalty) sind FEST - Abschnitt 5 des Plans exponiert dafuer keine Regler,
nur k0, Volatilitaet, Wartekosten, Ausweichkosten, Perioden und Seed sind einstellbar. Presets werden
mit tools/tune_presets.py gegen die Abnahmekriterien in rrs_stories.py geprueft (Zahlen exakt, keine
Stichprobe noetig - siehe tools/PRESET_SWEEP.md).

Wartekosten- und Ausweichkosten-Regler liegen in GANZZAHLIGEN PROZENTPUNKTEN (nicht als Anteil 0-1) -
`format="%.0f%%"` in app.py formatiert damit direkt den Reglerwert, ohne ihn zu multiplizieren
(bekannte Falle: format="%.0f%%" formatiert den ROHEN Wert, nicht Wert*100)."""

# --- Fachmodell-Konstanten (nicht ueber Regler einstellbar, Plan Abschnitt 2/5) --------------------
N_RISK_LEVELS = 5
P_CLOSURE_MAX = 0.5     # Sperrwahrscheinlichkeit bei hoechster Risikostufe
PREMIUM_MAX = 0.15      # Kriegsrisikozuschlag bei hoechster Stufe, Anteil von c_direct_base
C_DIRECT_BASE = 1.0     # Basiskosten Direktroute (normiert)
CLOSURE_PENALTY = 1.2   # Zusatzkosten bei Sperrung waehrend Direktfahrt (normiert)

# --- Ausgangsrisikostufe (k0_select): 5 benannte Stufen statt Freitext-Wahrscheinlichkeiten -------
RISK_LABELS = ("sehr gering", "gering", "mittel", "hoch", "sehr hoch")
K0_DEFAULT = "mittel"

# --- Volatilitaet der Lage (volatilitaet_select): steuert (Eskalations-, Deeskalationswahrscheinlichkeit)
# gemeinsam. "Volatilitaet" = Ausmass der Bewegung, nicht Richtung: "angespannt" ist symmetrisch hoch
# (haeufiges Hin und Her), nicht einseitig eskalierend - das deckt sich mit dem Volatile-Lage-Preset
# (Plan Abschnitt 7: "hohe Eskalations- UND Deeskalationswahrscheinlichkeit").
VOLATILITY_OPTIONS = ("ruhig", "normal", "angespannt")
VOLATILITY_DEFAULT = "normal"
VOLATILITY_PARAMS = {
    "ruhig": (0.05, 0.25),
    "normal": (0.15, 0.15),
    "angespannt": (0.30, 0.30),
}

# --- weitere Regler (Plan Abschnitt 5); Prozent-Regler in GANZZAHLIGEN Prozentpunkten ---------------
C_WAIT_PCT_RANGE, C_WAIT_PCT_DEFAULT = (0, 10), 2          # % von c_direct_base je Periode Abwarten
C_DETOUR_PCT_RANGE, C_DETOUR_PCT_DEFAULT = (10, 150), 40    # % Aufschlag der Ausweichroute ueber c_direct_base
N_PERIODS_RANGE, N_PERIODS_DEFAULT = (5, 20), 10
SEED_RANGE, SEED_DEFAULT = (0, 9999), 5


def c_wait_from_pct(pct: int) -> float:
    return C_DIRECT_BASE * pct / 100.0


def c_detour_from_pct(pct: int) -> float:
    return C_DIRECT_BASE * (1 + pct / 100.0)


# --- Bausteine (Plan Abschnitt 3): drei Politiken, DP ist die operative Empfehlung ------------------
POLICY_DETOUR, POLICY_THRESHOLD, POLICY_DP = "detour_always", "threshold", "dp"
POLICY_KEYS = (POLICY_DETOUR, POLICY_THRESHOLD, POLICY_DP)
POLICY_LABELS = {
    POLICY_DETOUR: "🛟 Immer Ausweichroute",
    POLICY_THRESHOLD: "⏱️ Abwarten + Schwellwert",
    POLICY_DP: "🎯 DP (exakt)",
}
POLICY_SHORT = {POLICY_DETOUR: "Immer Ausweichen", POLICY_THRESHOLD: "Schwellwert", POLICY_DP: "DP (exakt)"}
POLICY_COLORS = {POLICY_DETOUR: "#9aa5b4", POLICY_THRESHOLD: "#e0a800", POLICY_DP: "#2a6fb0"}

# Schwelle der bedingten Meldung in der Hauptansicht (Plan Abschnitt 6): Ersparnis DP ggue. "immer
# Ausweichroute" in Prozent. <= Schwelle -> "Ausweichen ist hier fast immer richtig" (hohe Ausgangslage);
# > Schwelle -> "hier lohnt sich Abwarten und die Direktroute deutlich" (niedrige Ausgangslage).
DETOUR_SAVINGS_LOW_THRESHOLD = 5.0
POLICY_DESCRIPTIONS = {
    POLICY_DETOUR: "Waehlt von Anfang an die sichere, laengere Ausweichroute, ohne die Lage zu "
                   "beobachten. Die Kontrast-Baseline: zeigt, wie teuer pauschale Vorsicht wird.",
    POLICY_THRESHOLD: "Wartet bis zum letztmoeglichen Tag ab und entscheidet dann anhand eines festen "
                      "Schwellwerts ueber die Risikostufe. Die zweite, informierte Baseline: zeigt, wie "
                      "teuer starres statt adaptives Abwarten wird.",
    POLICY_DP: "Rueckwaertsinduktion ueber (Periode, Risikostufe) - das echte Optimum, entscheidet "
              "adaptiv wann und wie. Die operative Empfehlung der Hauptansicht.",
}
COMPARISON_TAB_LABEL = "📊 Vergleich"

# --- Aktionen (Zustandsraum von policy[n][k]) und Darstellung ---------------------------------------
ACTION_DIRECT, ACTION_WAIT, ACTION_DETOUR = "direct", "wait", "detour"
ACTION_LABELS = {ACTION_DIRECT: "Direktroute", ACTION_WAIT: "Abwarten", ACTION_DETOUR: "Ausweichroute"}
ACTION_COLORS = {ACTION_DIRECT: "#2a6fb0", ACTION_WAIT: "#e0a800", ACTION_DETOUR: "#2e7d4f"}  # blau/gelb/gruen wie im Plan
HINDSIGHT_COLOR = "#c0392b"
CHART_HEIGHT = 380

# --- Presets (Plan Abschnitt 7; mit tools/tune_presets.py gegen rrs_stories.criteria() abgestimmt) -
PRESETS = {
    "Ruhige Lage": dict(k0="gering", volatilitaet="ruhig", c_wait_pct=2, c_detour_pct=40,
                        n_periods=10, seed=101),
    "Hormus-artige Dauerspannung": dict(k0="sehr hoch", volatilitaet="normal", c_wait_pct=2,
                                        c_detour_pct=42, n_periods=10, seed=205),
    "Teure Ausweichroute": dict(k0="mittel", volatilitaet="normal", c_wait_pct=2, c_detour_pct=80,
                                n_periods=10, seed=309),
    "Hohe Wartekosten": dict(k0="hoch", volatilitaet="normal", c_wait_pct=8, c_detour_pct=42,
                             n_periods=10, seed=417),
    "Volatile Lage": dict(k0="mittel", volatilitaet="angespannt", c_wait_pct=2, c_detour_pct=40,
                          n_periods=10, seed=505),
}
