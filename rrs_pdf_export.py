"""PDF-Export des Ergebnisses (fpdf2, Helvetica-Kernschrift, nur Text und Tabellen).

Die Kernschriften kennen nur Latin-1: Umlaute sind erlaubt, aber "-" (Gedankenstrich), "-" (Minuszeichen),
"EUR"-Zeichen, Emoji usw. lassen fpdf2 abstuerzen. Deshalb laeuft jeder Text durch pdf_text()."""
import time

import rrs_constants as C
import rrs_evaluation as E

_REPLACEMENTS = {
    "–": "-", "—": "-", "‑": "-", "−": "-", "≥": ">=", "≤": "<=", "→": "->", "≈": "ca.", "€": "EUR", "±": "+-",
    "·": "-", "“": '"', "”": '"', "„": '"', "‘": "'", "’": "'", "⚠️": "(!)", "⚠": "(!)", "✅": "", "ℹ️": "",
    "🧭": "", "📐": "", "🎯": "", "📊": "", "🛟": "", "⏱️": "", "🔮": "", "🎲": "",
}


def pdf_text(text):
    """Text fuer die Helvetica-Kernschrift: bekannte Sonderzeichen ersetzen, den Rest Latin-1-sicher machen."""
    for old, new in _REPLACEMENTS.items():
        text = text.replace(old, new)
    return text.encode("latin-1", "replace").decode("latin-1")


def _cost(v):
    return f"{v:.3f}"


def _pct(v):
    return f"{v:+.1f} %"


def generate_rrs_pdf(k0_label, volatilitaet, c_wait_pct, c_detour_pct, n_periods, seed, params, result, shown,
                     compress=True):
    """Ergebnis der aktuellen Einstellung als PDF: Einstellungen, Kosten je Baustein, Vergleichstabelle,
    Kostenaufschluesselung, Hinweise zum Modell."""
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    pdf = FPDF()
    pdf.set_compression(compress)
    pdf.add_page()

    def line(text, height=7, width=0):
        pdf.cell(width, height, pdf_text(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def heading(text):
        pdf.set_font("Helvetica", "B", 12)
        line(text, 8)
        pdf.set_font("Helvetica", "", 10)

    def pairs(rows):
        for label, value in rows:
            pdf.cell(85, 6, pdf_text(label), border=0)
            line(value, 6)

    def table(headers, widths, rows):
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(230, 230, 230)
        for header, width in zip(headers, widths):
            pdf.cell(width, 7, pdf_text(header), border=1, fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.ln(7)
        pdf.set_font("Helvetica", "", 9)
        for row in rows:
            for value, width in zip(row, widths):
                pdf.cell(width, 7, pdf_text(str(value)), border=1, new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.ln(7)

    def keep_together(height):
        if pdf.get_y() + height > pdf.h - pdf.b_margin:
            pdf.add_page()

    def note(text, size=8):
        pdf.set_font("Helvetica", "I", size)
        pdf.set_text_color(110, 110, 110)
        pdf.multi_cell(0, 5, pdf_text(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(0, 0, 0)

    pdf.set_font("Helvetica", "B", 16)
    line("Routenresilienz: Nadeloehr riskieren oder ausweichen?", 10)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(120, 120, 120)
    line(f"Erstellt: {time.strftime('%d.%m.%Y %H:%M')}  -  sebastianhanisch.net", 6)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

    heading("Einstellungen")
    pairs([
        ("Ausgangsrisikostufe", k0_label), ("Volatilitaet der Lage", volatilitaet),
        ("Wartekosten je Tag", f"{c_wait_pct} %"), ("Kosten der Ausweichroute", f"+{c_detour_pct} %"),
        ("Tage bis zur Weggabelung", str(n_periods)), ("Seed", str(seed)),
    ])
    pdf.ln(3)

    heading("Kosten je Baustein (erwartete Kosten, exakt - keine Stichprobe)")
    pairs([
        ("Kosten (DP, Empfehlung)", _cost(result.dp_cost)),
        ("Kosten (immer Ausweichroute)", _cost(result.detour_cost)),
        ("Kosten (Abwarten + fester Schwellwert)", _cost(result.threshold_cost)),
        ("Kosten (Hindsight, Referenz)", _cost(result.hindsight_cost)),
        ("Ersparnis DP ggue. immer Ausweichroute", _pct(result.savings_vs_detour_pct)),
        ("Ersparnis DP ggue. Schwellwert", _pct(result.savings_vs_threshold_pct)),
    ])
    pdf.ln(3)

    keep_together(50)
    heading("Vergleichstabelle")
    bd_dp = E.dp_breakdown(result, params)
    bd_th = E.threshold_breakdown(result, params)
    rows = [
        [C.POLICY_SHORT[C.POLICY_DETOUR], _cost(result.detour_cost),
         _pct(E.savings_vs_dp_pct(result.detour_cost, result.dp_cost)), "0,00"],
        [C.POLICY_SHORT[C.POLICY_THRESHOLD], _cost(result.threshold_cost),
         _pct(E.savings_vs_dp_pct(result.threshold_cost, result.dp_cost)), f"{bd_th.expected_wait_periods:.2f}"],
        [C.POLICY_SHORT[C.POLICY_DP], _cost(result.dp_cost), _pct(0.0), f"{bd_dp.expected_wait_periods:.2f}"],
    ]
    table(["Politik", "Kosten", "Ersparnis ggue. DP", "Perioden abgewartet"], [50, 35, 40, 40], rows)
    pdf.ln(3)

    keep_together(40)
    heading("Kostenaufschluesselung DP (Wartekosten- gegen Routenkosten-Anteil)")
    pairs([
        ("Wartekosten-Anteil", _cost(bd_dp.wait_cost)), ("Kosten der gewaehlten Route", _cost(bd_dp.route_cost)),
        ("Perioden im Mittel abgewartet", f"{bd_dp.expected_wait_periods:.2f} von {n_periods}"),
    ])
    pdf.ln(3)

    keep_together(60)
    heading("Gezeigter Risikopfad (Seed " + str(seed) + ")")
    pairs([
        ("DP entscheidet in Periode", f"{shown.dp_commit_n} ({C.ACTION_LABELS[shown.dp_action]})"),
        ("Schwellwert entscheidet in Periode", f"{n_periods} ({C.ACTION_LABELS[shown.schwelle_action]})"),
        ("Bester fester Schwellwert", f"Risikostufe <= {C.RISK_LABELS[result.best_k_star]}"),
    ])
    pdf.ln(3)

    keep_together(70)
    heading("Hinweise zum Modell")
    pdf.set_font("Helvetica", "", 9)
    for text in [
        "Nadeloehr (Strasse von Hormus, Bab-el-Mandeb/Rotes Meer) gegen Ausweichroute (Kap der Guten Hoffnung): "
        "optimales Stoppen, exakt geloest per Rueckwaertsinduktion (Bellman-Gleichung) ueber (Periode, Risikostufe).",
        "Die Risikostufe ist eine stark stilisierte Ein-Parameter-Zusammenfassung, nicht an echten Ereignisdaten "
        "kalibriert. Sperrwahrscheinlichkeit und Kriegsrisikozuschlag sind linear in der Risikostufe angenommen, "
        "real duerften beide eher konvex mit der Eskalation steigen.",
        "Die Sperr-Realisierung wird je Periode unabhaengig gezogen, nicht als persistenter Zustand. Kein "
        "Flottenblick - eine einzelne Abfahrt, keine Konvoi-/Portfolio-Entscheidung.",
        "Alle Kennzahlen sind exakt ueber die Zustandsverteilung berechnet (keine Simulation, kein "
        "Standardfehler noetig) - anders als bei den simulationsbasierten Wellen der Seefracht-Linie.",
    ]:
        pdf.multi_cell(0, 5, pdf_text("- " + text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    return bytes(pdf.output())
