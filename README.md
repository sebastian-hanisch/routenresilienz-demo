# Routenresilienz: Nadelöhr riskieren oder ausweichen? – Streamlit-Demo

**[→ Demo live ausprobieren](https://sebastianhanisch-routenresilienz-demo.streamlit.app/)**

Interaktive Fall-Demo zu **optimalem Stoppen**: eine Reederei entscheidet vor jeder Abfahrt, ob sie ein **Nadelöhr** (Straße von Hormus, Bab-el-Mandeb/Rotes Meer) anfährt – kürzer, aber mit
**Kriegsrisikozuschlag** und Sperrrisiko – oder die deutlich längere **Ausweichroute** (Kap der Guten Hoffnung) nimmt, motiviert durch die reale Umleitung der Weltcontainerschifffahrt seit den
Houthi-Angriffen im Roten Meer 2024. Die Demo beantwortet: **Wann lohnt es sich, auf mehr Information über die Sperrlage zu warten, und wie teuer ist es, diese Frage mit einer festen Faustregel statt
adaptiv zu beantworten?**

Teil des Portfolios für die Website „Sebastian Hanisch – Operations Research und Machine Learning", **Zusatz zur Geschwindigkeitsoptimierung** (`slow-steaming-demo`, Seefracht-Linie): eine „baut
aus"-Kante wie „Robuste Kaiplatzplanung" in der Hafen-Linie – hebt deren stillschweigende Annahme auf, dass die Route von vornherein feststeht. Anders als die simulationsbasierten Wellen der
Seefracht-Linie sind hier **alle Kennzahlen exakt** (Zustandsverteilungen statt Stichprobe) – keine Stichprobenschwankung, kein Standardfehler nötig.

## Warum dieses Problem

Klassisches **optimales Stoppen**, exakt lösbar per Rückwärtsinduktion (Bellman-Gleichung) über den kleinen Zustandsraum (Periode, Risikostufe). Der Befund ist differenzierter als bei den bisherigen
Wellen: gegen „immer Ausweichroute" ist der Vorsprung der DP-Politik **regimeabhängig** – bei bereits hoher Ausgangsrisikostufe fast 0 % (Ausweichen ist dort schon fast optimal), bei ruhiger Lage
dagegen deutlich zweistellig. Der robuste, durchgehend starke Hebel liegt gegen „abwarten und dann nach Gefühl entscheiden" (fester Schwellwert am letztmöglichen Tag): dort wächst der Vorsprung mit
den Wartekosten, weil die naive Regel immer die vollen Wartekosten zahlt, während die DP adaptiv früh abbricht.

## Modell

Diskrete Markov-Kette über 5 Risikostufen (sehr gering … sehr hoch, Random Walk mit reflektierenden Rändern, kalibrierbare Eskalations-/Deeskalationswahrscheinlichkeit). In jeder von N Perioden bis
zum letztmöglichen Entscheidungszeitpunkt: **Direktroute** (Erwartungswert aus laufzeitabhängigem Kriegsrisikozuschlag plus Sperrwahrscheinlichkeit, beide linear steigend in der Risikostufe; bei
Sperrung zusätzliche Umleitungs-Strafkosten), **Ausweichroute** (fix, sicher, unabhängig von Risikostufe und Zeitpunkt), oder **eine weitere Periode abwarten** (kleine Kosten je Periode, verlorene
Charterzeit). Am letzten Zeitpunkt muss entschieden werden. Formal im Expander „📐 Mathematische Formulierung" der App.

## Methodik – drei Bausteine statt einer Reglerfamilie

Wie bei den vorherigen Wellen drei Bausteine, kein stetiger Regler – aber anders als dort **zwei** naive Baselines statt einer, weil die Kernfrage selbst zweidimensional ist (OB ausweichen, UND WANN
entscheiden):

- **🛟 Immer Ausweichroute**: von Anfang an die sichere, längere Route, ohne die Lage zu beobachten – die **Kontrast-Baseline**.
- **⏱️ Abwarten + fester Schwellwert**: bis zum letztmöglichen Tag abwarten, dann anhand eines festen Schwellwerts entscheiden – die **zweite, informierte Baseline**.
- **🎯 DP (exakt)**: Rückwärtsinduktion über (Periode, Risikostufe) – das echte Optimum, entscheidet adaptiv wann und wie. Die **operative Empfehlung der Hauptansicht**.

Zusätzlich ein **Hindsight-Orakel** (kennt Risikopfad und Sperr-Realisierung im Voraus, keine online umsetzbare Politik) als vierte, prominente Kurve – der Wert von Information ist hier deutlich
größer als bei der Buchungs-/Slot-Vergabe-Demo.

**Kernlogik unverändert übernommen**: `rrs_scenario.py` (Params, Übergangsmatrix, Kostenfunktionen) und `rrs_solve.py` (`dp_optimal`, `expected_cost_under_policy`, `policy_wait_then_threshold`,
`hindsight_oracle`) sind direkt aus `seefracht-planung/messreihe_resilienz/resilienz.py` übernommen – bereits gegen 6 unabhängige Checks verifiziert (`messreihe_resilienz/check.py`: 0 Verletzungen).
Reine Standardbibliothek, kein scipy nötig.

## Befunde (gemessen, keine Behauptungen)

Alle Zahlen mit `python -m pytest tests/` nachvollziehbar (`test_preset_stories.py`); **exakt** über die Zustandsverteilung berechnet, keine Stichprobe, kein Standardfehler nötig.

| Frage | Befund | Test |
|---|---|---|
| Ist die DP besser als „immer Ausweichen"? | Regimeabhängig: ruhige Lage +20,5 %, teure Ausweichroute +23,6 %, Hormus-artige Dauerspannung nur +0,0 % – bei akutem Risiko ist Ausweichen schon fast optimal, kein Fehler des Modells | `test_preset_stories.py` |
| Ist die DP besser als „Abwarten + fester Schwellwert"? | Ja, robust und wachsend mit den Wartekosten: vernachlässigbare Wartekosten +10,0 % bis +12,7 %, hohe Wartekosten **+34,0 %** – der robusteste Hook dieser Demo | `test_preset_stories.py` |
| Kommt der Vorsprung aus weniger Warten oder einer anderen Route? | Aus weniger unnötigem Warten: die DP wartet im Mittel klar weniger Perioden als der feste Schwellwert bei jedem Preset | `test_evaluation.py::test_dp_waits_no_more_than_the_threshold_baseline_on_average` |
| Wird bei kostenlosem Abwarten immer gewartet? | Nein – an der sichersten Risikostufe droht nur eine Verschlechterung, keine Verbesserung; die DP wählt dort auch bei `c_wait=0` nicht immer „warten" | `test_solve.py::test_zero_wait_cost_does_not_crash_and_stays_optimal` |
| Stimmt Vorwärts- mit Rückwärtsrechnung überein? | Ja, exakt (30 Zufallsinstanzen) – zwei unabhängige Rechenwege für dieselbe Zahl | `test_solve.py::test_forward_matches_backward` |
| Schlägt eine erschöpfende Politiksuche auf Mini-Instanzen die DP? | Nein, 0 Verletzungen über 8 Instanzen (bis zu 3^6 durchprobierte Politiken) | `test_solve.py::test_exhaustive_tiny_instances` |
| Dominiert Hindsight immer das DP-Optimum? | Ja, harte Invariante: 0 Verletzungen über 30 Zufallsinstanzen | `test_solve.py::test_hindsight_never_worse_than_dp` |
| Hilft mehr verbleibende Zeit nie? | Bewiesene Struktureigenschaft (nicht nur getestet): V(n,k) ≤ V(n+1,k) für alle n, k, unabhängig von den Wartekosten | `test_solve.py::test_value_nonincreasing_in_remaining_time` |
| Schlägt die DP beide naiven Baselines immer? | Ja, 0 Verletzungen über 20 Zufallsinstanzen × 5 Schwellwerte | `test_solve.py::test_dp_beats_both_naive_baselines` |

## Ehrliche Grenzen

- **Risikostufe stark stilisiert** – eine Ein-Parameter-Zusammenfassung einer politisch/militärisch komplexen Lage, nicht an echten Ereignisdaten (z. B. Lloyd's-Kriegsrisiko-Notierungen) kalibriert.
- **Linear statt konvex** – Sperrwahrscheinlichkeit und Kriegsrisikozuschlag sind linear in der Risikostufe angenommen, real dürften beide eher konvex mit der Eskalation steigen.
- **Sperrung je Periode unabhängig**, nicht als persistenter Zustand („gesperrt bleibt gesperrt" würde einen zusätzlichen Absorptionszustand brauchen).
- **Kein Flottenblick** – eine einzelne Abfahrt, keine Konvoi-/Portfolio-Entscheidung über mehrere Schiffe.
- **Fachmodell-Konstanten fest** – `n_risk_levels`, Sperrwahrscheinlichkeit/Prämie bei höchster Stufe, Basiskosten und Sperr-Strafkosten sind in `rrs_constants.py` fixiert, nicht über Regler
  einstellbar (nur Ausgangsrisikostufe, Volatilität, Wartekosten, Ausweichkosten und Perioden sind es, siehe Detailplan Abschnitt 5).

## Tests

`python -m pytest tests/ -v` – 133 Tests, rund 13 Sekunden. Zusammensetzung:

- **Fachmodell** (`test_scenario.py`): Params-Validierung, Übergangsmatrix-Struktur (stochastisch, reflektierende Ränder), Kostenfunktionen monoton in der Risikostufe, Pfad-Realisierung
  (Determinismus, Struktur, Randbeachtung).
- **Löser** (`test_solve.py`): alle 6 Pflichtchecks aus `messreihe_resilienz/check.py` (Vorwärts=Rückwärts, erschöpfende Politiksuche, Monotonie in Risiko, Hindsight ≤ DP, V nicht steigend mit
  weniger Zeit, DP schlägt beide Baselines) plus Randfälle (Wartekosten 0, Ausweichroute so teuer wie die Direktroute im sichersten Fall, 1 Periode, höchste Risikostufe von Anfang an) plus gezielte
  Grenzwert-Tests der Terminalperiode und der Schwellwert-Politik (beim Bau per Mutationstest als Testlücke gefunden, siehe unten).
- **Auswertung** (`test_evaluation.py`): `params_from_controls` gegen die Regler-Zuordnung, Kennzahlen gegen Direktrechnung, Kostenaufschlüsselung summiert exakt zu den Gesamtkosten, DP wartet nie
  mehr als die Schwellwert-Baseline, gezeigter Pfad konsistent mit der Politik.
- **Regler** (`test_presets.py`): Permalink-Parsing/-Klemmen/-Runden (inkl. Stufen-Regler), Presets innerhalb ihrer eigenen Grenzen.
- **Presets** (`test_stories.py`, `test_preset_stories.py`): jedes Kriterium an künstlichen Werten, die genau an seiner Schwelle kippen; echte Presets erfüllen ihre Kriterien (exakt, keine Toleranz
  nötig).
- **Figuren** (`test_visualization.py`): Risikopfad, Politik-Schwellwertband, Kostenvergleich – alle Achsen fest (`fixedrange`).
- **PDF** (`test_pdf_export.py`): Sonderzeichen-Bereinigung (fpdf2 stürzt bei „–", „€", Unicode-Minus, Emoji ab – mit den genauen Zeichen getestet), Randfälle (Wartekosten 0, jedes Preset, kleinste
  Periodenzahl, höchste Ausgangsrisikostufe).
- **End-to-End** (`test_app.py`, AppTest): Skelett und Footer, jedes Preset, Permalink, alle Regler an Min und Max, die bedingte Meldung in beiden Zuständen, Vergleichstabelle, PDF, Texte.

Zusätzlich ein Fehler-Einbau-Test (`tools/mutation_check.py`, 27 Mutanten über `rrs_scenario`, `rrs_solve`, `rrs_evaluation`, `rrs_presets`, `rrs_stories`): **26 gefunden, 1 überlebt, 0 Fehler in der
Mutantenliste.** Der eine Überlebende ist gleichwertig (kein sichtbarer Unterschied im Verhalten): `realize_path`s Ziehungs-Vergleich (`<=` → `<`) trifft nur den exakten Gleichheitspunkt
`r == acc` einer stetigen Zufallszahl – ein Ereignis mit Wahrscheinlichkeit praktisch 0.

**Beim Bau gefundene Testlücken (per Mutationstest, dann geschlossen):** drei Mutanten überlebten zunächst, weil `min(vd, vD, wait)` an jeder Periode außer der Terminalperiode einen Rückfall auf die
korrekt berechnete Direkt-/Ausweichroute bietet und dadurch einen kaputten Terminal-Grenzfall verschleiert. Behoben durch drei gezielte Tests: `test_terminal_period_picks_the_cheaper_of_direct_and_detour_explicitly`
(V[N]/policy[N] explizit gegen die direkte Formel), `test_threshold_policy_chooses_direct_exactly_at_the_threshold_level` (Grenzfall `k == k_star`), und ein präzises `pytest.raises(..., match=...)`
statt eines unspezifischen `pytest.raises(ValueError)` in `test_expected_cost_under_policy_rejects_wait_in_final_period`.

## Dateistruktur

| Datei | Inhalt | Herkunft |
|---|---|---|
| `app.py` | Streamlit-Hauptablauf: Presets, Sidebar, Hauptansicht, Kernabschnitt, Bausteine im Vergleich, Texte | neu |
| `rrs_constants.py` | Fachmodell-Konstanten, Regler-Grenzen, `PRESETS`, Bausteine, Farben | neu |
| `rrs_presets.py` | `SETTING_SPECS`, Permalink, Presets, Seed-Knopf | Muster `rvm_presets.py` |
| `rrs_scenario.py` | Params, Übergangsmatrix, Kostenfunktionen, Pfad-Realisierung | `messreihe_resilienz/resilienz.py`, unverändert (+ neue `realize_path`) |
| `rrs_solve.py` | DP, Vorwärts-Erwartungswert, Schwellwert-Baseline, Hindsight-Orakel | `messreihe_resilienz/resilienz.py`, unverändert |
| `rrs_evaluation.py` | Params aus Reglern, Kennzahlen je Einstellung, Kostenaufschlüsselung, gezeigter Pfad | Muster `rvm_evaluation.py` |
| `rrs_visualization.py` | Risikopfad, Politik-Schwellwertband, Kostenvergleich (alle Achsen fest) | Muster `rvm_visualization.py` |
| `rrs_ui_panel.py` | Kennzahlen (2×2), Risikopfad-Grafik, Baustein-Tabs | Muster `rvm_ui_panel.py` |
| `rrs_pdf_export.py` | PDF-Export (`fpdf2`, Sonderzeichen-Bereinigung) | Muster `rvm_pdf_export.py` |
| `rrs_stories.py` | Abnahmekriterien der Presets | Muster `rvm_stories.py` |
| `tools/tune_presets.py` | Preset-Abstimmung/-Bericht | neu |
| `tools/mutation_check.py` | Fehler-Einbau-Test | neu |
| `tests/` | siehe oben | neu |

## Bewusst nicht umgesetzt (mögliche Erweiterungen)

- **Kalibrierung an echten Ereignisdaten** (z. B. Lloyd's-Kriegsrisiko-Notierungen) statt der stark stilisierten Ein-Parameter-Risikostufe.
- **Konvexe Risikofunktionen** statt linear in der Risikostufe (reale Eskalation dürfte überproportional teuer werden).
- **Persistenter Sperrzustand** ("gesperrt bleibt gesperrt") statt je Periode unabhängiger Sperr-Realisierung – ein zusätzlicher Absorptionszustand in der Markov-Kette.
- **Flottenblick/Konvoi-Entscheidung** über mehrere Schiffe mit korrelierten Risikorealisierungen statt einer einzelnen Abfahrt.
- **Kopplung der Sperr-Realisierung mit der tatsächlichen Routenlänge** (aktuell wird die Risikostufe am Entscheidungszeitpunkt verwendet, nicht am Ankunftszeitpunkt).

## Lokal ausführen

```bash
pip install -r requirements-dev.txt
streamlit run app.py
```

Tests: `python -m pytest tests/ -v`. Preset-Abstimmung: `python tools/tune_presets.py`. Fehler-Einbau: `python tools/mutation_check.py`.

---

Gebaut mit Streamlit, Plotly und fpdf2.

Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). Mehr zum Thema: [Seefracht optimieren](https://sebastianhanisch.net/seefracht-optimierung.html).
