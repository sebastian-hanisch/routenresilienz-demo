"""Wiederverwendbares Panel: Kennzahlen (2 x 2), Risikopfad-Grafik, Baustein-Tabs (Immer Ausweichroute,
Schwellwert, DP exakt, Vergleich) - Plan Abschnitt 6/8."""
import pandas as pd
import streamlit as st

import rrs_constants as C
import rrs_evaluation as E
import rrs_visualization as V


def fmt_cost(v):
    return f"{v:.3f}".replace(".", ",")


def fmt_pct(v):
    return f"{v:+.1f} %".replace(".", ",")


def render_metrics(columns, result):
    """Vier Kennzahlen (Plan Abschnitt 6): Kosten (DP), Kosten (immer Ausweichroute), Kosten
    (Abwarten + fester Schwellwert), Ersparnis DP ggue. Schwellwert - die robustere, durchgehend
    positive Zahl steht prominent."""
    m = columns
    m[0].metric("Kosten (DP)", fmt_cost(result.dp_cost),
               help="Erwartete Kosten der DP-optimalen Politik (Rückwärtsinduktion) bei der eingestellten Route.")
    m[1].metric("Kosten (immer Ausweichroute)", fmt_cost(result.detour_cost),
               delta=fmt_cost(result.detour_cost - result.dp_cost), delta_color="inverse",
               help="Kontrast-Baseline: von Anfang an die sichere Route, ohne die Lage zu beobachten. Delta = Ausweichroute minus DP.")
    m[2].metric("Kosten (Abwarten + fester Schwellwert)", fmt_cost(result.threshold_cost),
               delta=fmt_cost(result.threshold_cost - result.dp_cost), delta_color="inverse",
               help="Zweite, informierte Baseline: bis zuletzt abwarten, dann anhand eines festen Schwellwerts entscheiden. Delta = Schwellwert minus DP.")
    m[3].metric("Ersparnis ggü. Schwellwert", fmt_pct(result.savings_vs_threshold_pct),
               help="Der robuste, durchgehend positive Befund: DP gegen die Schwellwert-Baseline. Wächst mit den Wartekosten.")


def render_timeline(key, shown, n_risk_levels):
    fig = V.risk_path_figure(shown, n_risk_levels)
    st.plotly_chart(fig, width="stretch", key=key)
    st.caption("Kreis = Entscheidungspunkt der DP-Politik, Raute (gestrichelt umrandet) = Entscheidungspunkt der "
              "Schwellwert-Politik (immer am letztmöglichen Tag). Farbe = gewählte Route.")


def render_policy_panel(prefix, policy_key, result, shown, params):
    """Beschreibung, Kosten-Kennzahl und Risikopfad-Grafik einer Politik (je Tab im Vergleich-Expander)."""
    st.markdown(C.POLICY_DESCRIPTIONS[policy_key])
    cost = {C.POLICY_DETOUR: result.detour_cost, C.POLICY_THRESHOLD: result.threshold_cost,
           C.POLICY_DP: result.dp_cost}[policy_key]
    c1, c2 = st.columns(2)
    c1.metric("Kosten", fmt_cost(cost))
    c2.metric("Ersparnis ggü. DP", fmt_pct(E.savings_vs_dp_pct(cost, result.dp_cost)))
    if policy_key == C.POLICY_THRESHOLD:
        st.caption(f"Bester fester Schwellwert dieser Einstellung: Risikostufe <= "
                  f"„{C.RISK_LABELS[result.best_k_star]}“ -> Direktroute, sonst Ausweichroute - "
                  f"entschieden wird aber immer erst in Periode {params.n_periods} (letztmöglicher Tag).")
    if policy_key == C.POLICY_DP:
        bd = E.dp_breakdown(result, params)
        st.caption(f"Im Erwartungswert {bd.expected_wait_periods:.2f} von {params.n_periods} Perioden "
                  f"abgewartet - Wartekosten-Anteil {fmt_cost(bd.wait_cost)}, Kosten der letztlich "
                  f"gewählten Route {fmt_cost(bd.route_cost)}.")
    render_timeline(f"{prefix}_path_chart", shown, params.n_risk_levels)


def render_comparison_tab(result, shown, params):
    """Vergleichstabelle aller drei Politiken, das Politik-Schwellwertband und eine vierte,
    sekundaere Hindsight-Kurve als "Wert von Information"-Kontext (Plan Abschnitt 8)."""
    rows = []
    costs = {C.POLICY_DETOUR: result.detour_cost, C.POLICY_THRESHOLD: result.threshold_cost,
            C.POLICY_DP: result.dp_cost}
    breakdowns = {C.POLICY_DP: E.dp_breakdown(result, params), C.POLICY_THRESHOLD: E.threshold_breakdown(result, params)}
    for policy in C.POLICY_KEYS:
        cost = costs[policy]
        wait_days = breakdowns[policy].expected_wait_periods if policy in breakdowns else 0.0
        rows.append({
            "Politik": C.POLICY_LABELS[policy], "Kosten": fmt_cost(cost),
            "Ersparnis ggü. DP": fmt_pct(E.savings_vs_dp_pct(cost, result.dp_cost)),
            "Perioden abgewartet (im Mittel)": f"{wait_days:.2f}",
            "Route am Ende": C.ACTION_LABELS[shown.dp_action if policy == C.POLICY_DP else
                                            (shown.schwelle_action if policy == C.POLICY_THRESHOLD else C.ACTION_DETOUR)],
        })
    rows.append({
        "Politik": "🔮 Hindsight (Referenz)", "Kosten": fmt_cost(result.hindsight_cost),
        "Ersparnis ggü. DP": fmt_pct(E.savings_vs_dp_pct(result.hindsight_cost, result.dp_cost)),
        "Perioden abgewartet (im Mittel)": "–", "Route am Ende": "–",
    })
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    st.plotly_chart(V.policy_grid_figure(result.policy, params.n_periods, params.n_risk_levels), width="stretch",
                    key="comparison_tab_policy_grid")
    st.plotly_chart(V.cost_comparison_figure(result, show_hindsight=True), width="stretch",
                    key="comparison_tab_cost_chart")
    st.caption("Hindsight ist keine online umsetzbare Politik (kennt Risikopfad und Sperr-Realisierung im "
              "Voraus) - sie zeigt nur, wie viel zusätzliches Wissen über die Zukunft noch bringen würde "
              "(\"Wert von Information\"), hier deutlich größer als bei der Buchungs-/Slot-Vergabe-Demo.")
