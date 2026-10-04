"""
Routenresilienz bei Nadeloehr-Sperrung - interaktive Fall-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Zusatz zur Geschwindigkeitsoptimierung (Seefracht-Linie): eine Reederei entscheidet vor jeder Abfahrt,
ob sie ein Nadeloehr (Bab-el-Mandeb/Rotes Meer; als Spannungsbild auch die Strasse von Hormus) anfaehrt - kuerzer, aber mit
Kriegsrisikozuschlag und Sperrrisiko - oder die deutlich laengere Ausweichroute (Kap der Guten
Hoffnung) nimmt, oder eine weitere Periode auf mehr Information wartet. Klassisches optimales
Stoppen, exakt geloest per Rueckwaertsinduktion (Bellman-Gleichung) ueber (Periode, Risikostufe).

Lauffaehig mit: streamlit run app.py
"""
import streamlit as st

import rrs_constants as C
import rrs_evaluation as E
import rrs_visualization as VZ
from rrs_pdf_export import generate_rrs_pdf
from rrs_presets import (apply_preset, bounds, init_session_state_defaults, load_permalink_settings,
                         options, randomize_seed, SETTING_SPECS, sync_query_params)
from rrs_ui_panel import fmt_cost, fmt_pct, render_comparison_tab, render_metrics, render_policy_panel, render_timeline

st.set_page_config(page_title="Routenresilienz – Sebastian Hanisch", layout="wide")

SCENARIO_KEYS = list(SETTING_SPECS)


@st.cache_data(show_spinner=False, max_entries=64)
def _scenario(k0_label, volatilitaet, c_wait_pct, c_detour_pct, n_periods):
    params = E.params_from_controls(k0_label, volatilitaet, c_wait_pct, c_detour_pct, n_periods)
    result = E.evaluate(params)
    return params, result


@st.cache_data(show_spinner=False, max_entries=64)
def _shown(k0_label, volatilitaet, c_wait_pct, c_detour_pct, n_periods, seed):
    params, result = _scenario(k0_label, volatilitaet, c_wait_pct, c_detour_pct, n_periods)
    return E.evaluate_shown_path(params, seed, result)


st.title("🧭 Routenresilienz: Nadelöhr riskieren oder ausweichen?")
st.markdown(
    """
Eine Reederei entscheidet vor jeder Abfahrt, ob sie ein **Nadelöhr** (Bab-el-Mandeb/Rotes Meer; als Spannungsbild auch die Straße von Hormus, die für Golfhäfen allerdings keine Kap-Alternative hat) anfährt – kürzer, aber mit **Kriegsrisikozuschlag** und Sperrrisiko – oder die deutlich
längere **Ausweichroute** (Kap der Guten Hoffnung) nimmt, motiviert durch die reale Umleitung der Weltcontainerschifffahrt seit den Angriffen der Houthi-Miliz auf Handelsschiffe im Roten Meer (ab November 2023; große Reedereien leiten seit Dezember 2023/Januar 2024 ums Kap um; die Risikostufe hier ist
illustrativ, nicht an echten Ereignissen kalibriert). Ein **Zusatz zur Geschwindigkeitsoptimierung** (Seefracht-Linie): hebt deren Annahme auf, dass die Route von vornherein feststeht. Wie das Modell
funktioniert, steht im Expander „Wie funktioniert diese Demo?" weiter unten, die formale Beschreibung im Expander „📐 Mathematische Formulierung".
"""
)

st.caption("🎯 Schnellstart – ein Beispielszenario laden:")
PRESET_HELP = {
    "Ruhige Lage": "Der entspannte Grundfall: Abwarten und die Direktroute lohnen sich klar.",
    "Hormus-artige Dauerspannung": "Akute Dauerkrise: Ausweichen ist schon fast optimal, der Gewinn der DP liegt allein im WANN.",
    "Teure Ausweichroute": "Wenn Ausweichen selbst richtig teuer wird, lohnt sich die genaue Abwägung besonders.",
    "Hohe Wartekosten": "Der robusteste Hook dieser Demo: starres Abwarten wird teuer, wenn Liegezeit selbst viel kostet.",
    "Volatile Lage": "Die Lage schlägt schnell in beide Richtungen um – zeigt einen hohen Wert von Information.",
}
preset_names = list(C.PRESETS.keys())
for row in (preset_names[:3], preset_names[3:]):
    cols = st.columns(3)
    for col, name in zip(cols, row):
        with col:
            st.button(name, width="stretch", on_click=apply_preset, args=(name,), help=PRESET_HELP[name])

st.caption("🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, um ein Szenario zu teilen.")

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    k0_label = st.select_slider("Ausgangsrisikostufe", options("k0_select"), key="k0_select",
                                help="Startzustand der Markov-Kette über die Risikostufe.")
    volatilitaet = st.select_slider("Volatilität der Lage", options("volatilitaet_select"), key="volatilitaet_select",
                                    help="Steuert Eskalations- und Deeskalationswahrscheinlichkeit gemeinsam "
                                         "(Ausmaß der Bewegung, nicht Richtung).")
    c_wait_pct = st.slider("Wartekosten je Tag", *bounds("c_wait_slider"), key="c_wait_slider", format="%d%%",
                           help="Kosten je Periode Abwarten, in % der Direktroute-Basiskosten (verlorene Charterzeit).")
    c_detour_pct = st.slider("Kosten der Ausweichroute", *bounds("c_detour_slider"), key="c_detour_slider", format="%d%%",
                             help="Fixer Aufschlag der Ausweichroute über die Direktroute-Basiskosten (Kap/Suez-Verhältnis).")
    n_periods = st.slider("Tage bis zur Weggabelung", *bounds("n_periods_slider"), key="n_periods_slider",
                          help="Länge des Entscheidungsfensters.")
    seed = st.number_input("Seed", *bounds("seed_input"), key="seed_input", step=1,
                           help="Bestimmt den gezeigten Risikopfad.")
    st.button("🎲 Neuer Risikopfad", width="stretch", on_click=randomize_seed, help="Würfelt einen neuen Seed.")

sync_query_params({key: st.session_state[key] for key in SCENARIO_KEYS})

c_wait_pct, c_detour_pct, n_periods, seed = int(c_wait_pct), int(c_detour_pct), int(n_periods), int(seed)

params, result = _scenario(k0_label, volatilitaet, c_wait_pct, c_detour_pct, n_periods)
shown = _shown(k0_label, volatilitaet, c_wait_pct, c_detour_pct, n_periods, seed)

# ---------------------------------------------------------------------------------------------------
# Hauptansicht
# ---------------------------------------------------------------------------------------------------
st.markdown("## 🧭 Wann lohnt sich Abwarten, wann sofort entscheiden?")
st.caption(f"Ausgangsrisiko {k0_label}, Volatilität {volatilitaet}, Wartekosten {c_wait_pct} %, "
          f"Ausweichroute +{c_detour_pct} %, {n_periods} Perioden, Seed {seed}.")

metric_rows = [st.columns(2), st.columns(2)]
render_metrics(metric_rows[0] + metric_rows[1], result)
st.caption(f"Zum Vergleich (regimeabhängig, siehe Warnhinweis unten): Ersparnis DP ggü. immer Ausweichroute "
          f"{fmt_pct(result.savings_vs_detour_pct)}.")

if result.savings_vs_detour_pct <= C.DETOUR_SAVINGS_LOW_THRESHOLD:
    st.info(f"ℹ️ Bei dieser Einstellung ist Ausweichen fast immer richtig (Ersparnis DP ggü. immer Ausweichroute "
           f"nur {fmt_pct(result.savings_vs_detour_pct)}) – der Gewinn der DP liegt im WANN, nicht im OB.")
else:
    st.success(f"✅ Bei dieser Einstellung lohnt sich Abwarten und die Direktroute deutlich (Ersparnis DP ggü. "
              f"immer Ausweichroute {fmt_pct(result.savings_vs_detour_pct)}).")

st.markdown("#### 🧭 Realisierter Risikopfad mit Entscheidungspunkt")
render_timeline("main_path_chart", shown, params.n_risk_levels)

st.info(f"🔮 Hindsight (volles Vorwissen über Risikopfad und Sperr-Realisierung) läge bei "
       f"{fmt_cost(result.hindsight_cost)} – das DP-Optimum ist **{fmt_pct(result.gap_to_hindsight_pct)}** teurer: so "
       f"groß ist hier der Wert von Information (deutlich größer als bei der Buchungs-/Slot-Vergabe-Demo).")

pdf_slot = st.container()

st.markdown("---")

# ---------------------------------------------------------------------------------------------------
# Kernabschnitt
# ---------------------------------------------------------------------------------------------------
st.markdown("### 📐 Wie sieht die optimale Schwellwertpolitik aus?")
st.markdown(
    """
Kernfrage dieser Demo: wie sieht die optimale Politik über Periode und Risikostufe aus – ein stabiles Schwellwertband oder eine einzelne Zahl? Direktroute bei niedriger Risikostufe, Abwarten in einem
mittleren Band, Ausweichroute bei hoher Risikostufe – über fast den ganzen Zeithorizont stabil, kollabiert erst in der letzten Periode auf eine Zweierwahl.
"""
)
st.plotly_chart(VZ.policy_grid_figure(result.policy, params.n_periods, params.n_risk_levels), width="stretch",
                key="main_policy_grid")

bd_dp = E.dp_breakdown(result, params)
bd_th = E.threshold_breakdown(result, params)
c1, c2 = st.columns(2)
c1.metric("DP: Wartekosten-Anteil", fmt_cost(bd_dp.wait_cost),
         help=f"Im Mittel {bd_dp.expected_wait_periods:.2f} von {params.n_periods} Perioden abgewartet; "
              f"Kosten der letztlich gewählten Route: {fmt_cost(bd_dp.route_cost)}.")
c2.metric("Schwellwert: Wartekosten-Anteil", fmt_cost(bd_th.wait_cost),
         help=f"Wartet immer alle {params.n_periods} Perioden; Kosten der letztlich gewählten Route: "
              f"{fmt_cost(bd_th.route_cost)}.")
st.caption("Der Vorsprung der DP gegenüber dem festen Schwellwert kommt aus weniger unnötigem Warten, nicht aus "
          "einer anderen Endentscheidung – die Kosten der letztlich gewählten Route unterscheiden sich weit "
          "weniger als die Wartekosten-Anteile.")
st.caption(f"Basis: alle Zahlen exakt über die Zustandsverteilung berechnet (keine Stichprobe, kein "
          f"Standardfehler nötig). Rechenzeit gemessen: DP über (Periode × Risikostufe) braucht selbst beim "
          f"größten Reglerstand ({C.N_PERIODS_RANGE[1]} Perioden, {C.N_RISK_LEVELS} Stufen) unter 1 ms – ohne "
          f"Knopf möglich, live bei jedem Reglerzug.")

with pdf_slot:
    st.download_button(
        "📄 Ergebnis als PDF herunterladen",
        data=generate_rrs_pdf(k0_label, volatilitaet, c_wait_pct, c_detour_pct, n_periods, seed, params, result, shown),
        file_name="routenresilienz_ergebnis.pdf", mime="application/pdf", key="primary_pdf_download",
        help="Einstellungen, Kosten je Baustein, Vergleichstabelle, Kostenaufschlüsselung.")

st.markdown("---")

# ---------------------------------------------------------------------------------------------------
# Bausteine im Vergleich
# ---------------------------------------------------------------------------------------------------
with st.expander("🔧 Wie wir das erreichen – Politiken im Vergleich"):
    tabs = st.tabs([C.POLICY_LABELS[C.POLICY_DETOUR], C.POLICY_LABELS[C.POLICY_THRESHOLD], C.POLICY_LABELS[C.POLICY_DP],
                   C.COMPARISON_TAB_LABEL])
    with tabs[0]:
        render_policy_panel("tab_detour", C.POLICY_DETOUR, result, shown, params)
    with tabs[1]:
        render_policy_panel("tab_threshold", C.POLICY_THRESHOLD, result, shown, params)
    with tabs[2]:
        render_policy_panel("tab_dp", C.POLICY_DP, result, shown, params)
    with tabs[3]:
        render_comparison_tab(result, shown, params)

with st.expander("Wie funktioniert diese Demo?"):
    st.markdown(
        """
**Nadelöhr gegen Ausweichroute.** Die aktuelle Risikolage folgt einer diskreten Markov-Kette über 5 Risikostufen (sehr gering … sehr hoch, Random Walk mit reflektierenden Rändern). In jeder Periode bis
zur letztmöglichen Weggabelung kann die Reederei sofort die **Direktroute** durchs Nadelöhr wählen (Erwartungswert aus Kriegsrisikozuschlag und Sperrwahrscheinlichkeit, beide steigend in der
Risikostufe), die **Ausweichroute** (fix, sicher, aber länger), oder eine weitere Periode **abwarten** (kleine Kosten je Periode, verlorene Charterzeit) – klassisches optimales Stoppen, exakt gelöst
per Rückwärtsinduktion (Bellman-Gleichung).

**Warum der Vorsprung gegen "immer Ausweichen" von der Ausgangslage abhängt, gegen "Abwarten + fester Schwellwert" aber robust ist.** Bei bereits hoher Ausgangsrisikostufe ist Ausweichen selbst schon
fast optimal – der Gewinn der DP liegt dann allein im WANN, nicht im OB (siehe die bedingte Meldung oben). Gegen die feste Schwellwert-Baseline dagegen wächst der Vorsprung robust mit den
Wartekosten: die naive Regel zahlt immer die vollen Wartekosten bis zur letzten Periode, während die DP adaptiv früh abbricht, sobald sich die Lage klärt.

**Warum die optimale Politik ein stabiles Schwellwertband ist, keine einzelne Zahl.** Das Politik-Schwellwertband oben zeigt: Direktroute bei niedriger Risikostufe, Abwarten in einem mittleren Band,
Ausweichroute bei hoher Risikostufe – über fast den ganzen Zeithorizont stabil, kollabiert erst in der letzten Periode (keine weitere Wartemöglichkeit) auf eine reine Zweierwahl.

**Grenzen dieses Modells** (bewusst so gewählt, damit die Aussage ehrlich bleibt):

- **Risikostufe stark stilisiert** – eine Ein-Parameter-Zusammenfassung einer politisch/militärisch komplexen Lage, nicht an echten Ereignisdaten (z. B. Lloyd's-Kriegsrisiko-Notierungen) kalibriert.
- **Linear statt konvex** – Sperrwahrscheinlichkeit und Kriegsrisikozuschlag sind linear in der Risikostufe angenommen, real dürften beide eher konvex mit der Eskalation steigen.
- **Sperrung je Periode unabhängig**, nicht als persistenter Zustand ("gesperrt bleibt gesperrt" würde einen zusätzlichen Absorptionszustand brauchen).
- **Kein Flottenblick** – eine einzelne Abfahrt, keine Konvoi-/Portfolio-Entscheidung über mehrere Schiffe.
        """
    )

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Zustandsraum.** Periode $n \in \{0, \dots, N\}$, Risikostufe $k \in \{0, \dots, K-1\}$; Übergang per Random Walk mit reflektierenden Rändern (Eskalationswahrscheinlichkeit $p_{up}$,
Deeskalationswahrscheinlichkeit $p_{down}$, an den Rändern reflektiert).

**Bellman-Gleichung.** $V(N, k) = \min\big(c_{Ausweichen},\ \mathbb{E}[\text{Kosten Direktroute} \mid k]\big)$; für $n < N$:
$$V(n, k) = \min\Big(c_{Ausweichen},\ \mathbb{E}[\text{Kosten Direktroute} \mid k],\ c_{Warten} + \sum_{k'} T(k, k') \cdot V(n+1, k')\Big)$$
$V(0, k_0)$ ist der optimale erwartete Gesamtkostenwert; die Politik $\pi(n,k) \in \{\text{direkt}, \text{ausweichen}, \text{warten}\}$ ergibt sich aus dem jeweiligen Minimierer.

**Bewiesene Struktureigenschaft.** $V(n, k) \leq V(n+1, k)$ für alle $n < N, k$ – mehr verbleibende Zeit kann die Erwartungskosten nur senken, nie erhöhen (Induktion über $n$: die Optionsmenge bei $n$
enthält die Optionsmenge bei $n+1$ als Teilmenge über die Warten-Option). **Nicht** dasselbe wie "bei kostenlosem Abwarten wird immer gewartet" – an der sichersten Risikostufe droht durch die
Zufallsbewegung nur eine Verschlechterung, keine Verbesserung, daher kann Abwarten dort selbst ohne Wartekosten ungünstig sein.

**Hindsight-Orakel.** Gemeinsame Verteilung von (Risikostufe, bisher bester erreichbarer Wert) exakt vorwärts propagiert, keine Simulation: zu jedem Zeitpunkt darf rückblickend die bis dahin beste
verfügbare Option genommen werden (inklusive sofortiger Ausweichroute ab $n=0$) – keine online umsetzbare Politik, nur eine obere Schranke für den Wert der Information.

Implementiert in `rrs_scenario.py` (Params, Übergangsmatrix, Kostenfunktionen, Pfad-Realisierung), `rrs_solve.py` (DP, Hindsight-Orakel, Schwellwert-Baseline) und `rrs_evaluation.py` (Kennzahlen,
Kostenaufschlüsselung, gezeigter Pfad).
        """
    )

st.markdown("---")

st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zum Thema: [Seefracht optimieren](https://sebastianhanisch.net/seefracht-optimierung.html)."
)
