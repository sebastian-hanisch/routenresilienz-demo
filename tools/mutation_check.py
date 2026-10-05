"""Fehler-Einbau-Test: baut einzelne Fehler in die Module ein und prueft, ob die Tests (ohne AppTests,
die sind zu langsam fuer viele Mutanten) sie finden.

Aufruf (im Projektordner): ./venv/Scripts/python.exe tools/mutation_check.py [Teilstring des Dateinamens]
Jeder Mutant ersetzt genau eine Stelle; Ueberlebende sind entweder gleichwertig (kein sichtbarer
Unterschied) oder eine Luecke der Tests. Die Kopie liegt in einem temporaeren Ordner;
PYTHONDONTWRITEBYTECODE=1, damit veralteter Bytecode keine Ueberlebenden vortaeuscht; Quelltexte als
LF (Windows-Python schreibt sonst CRLF und die Zeichenketten unten finden nichts)."""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
PY = sys.executable
TIMEOUT = 240

MUTANTS = [
    # rrs_scenario.py: reflektierende Raender, Kostenfunktionen, Pfad-Ziehung
    ("rrs_scenario.py", "            stay += down\n            down = 0.0", "            stay += down\n            down = down"),
    ("rrs_scenario.py", "            stay += up\n            up = 0.0", "            stay += up\n            up = up"),
    ("rrs_scenario.py", "return p.p_closure_max * k / (p.n_risk_levels - 1)", "return p.p_closure_max * k / p.n_risk_levels"),
    ("rrs_scenario.py", "return p.premium_max * p.c_direct_base * k / (p.n_risk_levels - 1)", "return p.premium_max * p.c_direct_base * k / p.n_risk_levels"),
    ("rrs_scenario.py", "if r <= acc:", "if r < acc:"),
    # rrs_solve.py: Rueckwaertsinduktion, Schwellwert, Hindsight
    ("rrs_solve.py", 'action, val = min((("detour", vd), ("direct", vD)), key=lambda x: x[1])', 'action, val = max((("detour", vd), ("direct", vD)), key=lambda x: x[1])'),
    ("rrs_solve.py", "vW = p.c_wait + sum(T[k][kp] * V[n + 1][kp] for kp in range(K))", "vW = p.c_wait * 2 + sum(T[k][kp] * V[n + 1][kp] for kp in range(K))"),
    ("rrs_solve.py", 'return "direct" if k <= k_star else "detour"', 'return "direct" if k < k_star else "detour"'),
    ("rrs_solve.py", "best_if_open = min(best, cost_open)", "best_if_open = max(best, cost_open)"),
    ("rrs_solve.py", "best_if_closed = min(best, cost_closed)", "best_if_closed = max(best, cost_closed)"),
    ("rrs_solve.py", 'if n == N:\n                    raise ValueError("Politik muss spätestens in Periode N entscheiden")',
     'if n > N:\n                    raise ValueError("Politik muss spätestens in Periode N entscheiden")'),
    # rrs_evaluation.py: Ersparnis-Formeln, Kostenaufschluesselung
    ("rrs_evaluation.py", "savings_vs_detour = (detour_cost - dp_cost) / detour_cost * 100 if detour_cost else 0.0",
     "savings_vs_detour = (dp_cost - detour_cost) / detour_cost * 100 if detour_cost else 0.0"),
    ("rrs_evaluation.py", "savings_vs_threshold = (threshold_cost - dp_cost) / threshold_cost * 100 if threshold_cost else 0.0",
     "savings_vs_threshold = (threshold_cost - dp_cost) / dp_cost * 100 if threshold_cost else 0.0"),
    ("rrs_evaluation.py", "gap_to_hindsight = (dp_cost - hindsight_cost) / hindsight_cost * 100 if hindsight_cost > 0 else 0.0",
     "gap_to_hindsight = (hindsight_cost - dp_cost) / hindsight_cost * 100 if hindsight_cost > 0 else 0.0"),
    ("rrs_evaluation.py", "return (cost - dp_cost) / cost * 100 if cost else 0.0", "return (cost - dp_cost) / dp_cost * 100 if cost else 0.0"),
    ("rrs_evaluation.py", "route_cost += prob * params.c_detour", "route_cost += params.c_detour"),
    ("rrs_evaluation.py", "wait_cost += prob * params.c_wait", "wait_cost += params.c_wait"),
    ("rrs_evaluation.py", "expected_wait_periods += prob", "expected_wait_periods += 1"),
    # rrs_presets.py
    ("rrs_presets.py", "value = max(spec.lo, value)", "value = value"),
    ("rrs_presets.py", "if spec.hi is not None:\n        value = min(spec.hi, value)", "if spec.hi is not None:\n        value = value"),
    ("rrs_presets.py", "return min(opts, key=lambda o: abs(o - value))", "return min(opts)"),
    # randomize_seed() selbst braucht AppTest (st.session_state ausserhalb eines Skript-Kontexts) - dort
    # abgedeckt (tests/test_app.py::test_new_path_button_actually_randomizes_not_just_stays_in_range),
    # nicht in diesem schnellen, AppTest-losen Lauf.
    # rrs_stories.py: Schwellen der Presets
    ("rrs_stories.py", 'return [(sd >= 15.0, f"Ersparnis vs. immer Ausweichen >= 15 %: {_pct(sd)}")]',
     'return [(sd >= 14.0, f"Ersparnis vs. immer Ausweichen >= 15 %: {_pct(sd)}")]'),
    ("rrs_stories.py", 'return [(sd <= 2.0, f"Ersparnis vs. immer Ausweichen <= 2 %: {_pct(sd)}"),',
     'return [(sd <= 3.0, f"Ersparnis vs. immer Ausweichen <= 2 %: {_pct(sd)}"),'),
    ("rrs_stories.py", '(st_ >= 5.0, f"Ersparnis vs. Schwellwert >= 5 %: {_pct(st_)}")]',
     '(st_ >= 4.0, f"Ersparnis vs. Schwellwert >= 5 %: {_pct(st_)}")]'),
    ("rrs_stories.py", 'return [(sd >= 20.0, f"Ersparnis vs. immer Ausweichen >= 20 %: {_pct(sd)}")]',
     'return [(sd >= 19.0, f"Ersparnis vs. immer Ausweichen >= 20 %: {_pct(sd)}")]'),
    ("rrs_stories.py", 'return [(st_ >= 25.0, f"Ersparnis vs. Schwellwert >= 25 %: {_pct(st_)}")]',
     'return [(st_ >= 24.0, f"Ersparnis vs. Schwellwert >= 25 %: {_pct(st_)}")]'),
    ("rrs_stories.py", 'return [(gh >= 20.0, f"Abstand zu Hindsight >= 20 %: {_pct(gh)}")]',
     'return [(gh >= 19.0, f"Abstand zu Hindsight >= 20 %: {_pct(gh)}")]'),
]


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else ""
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="rrs_mut_"))
    for f in ROOT.glob("*.py"):
        shutil.copy(f, tmp / f.name)
    shutil.copytree(ROOT / "tests", tmp / "tests", ignore=shutil.ignore_patterns("__pycache__"))
    for f in tmp.glob("*.py"):
        f.write_bytes(f.read_bytes().replace(b"\r\n", b"\n"))
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    survivors, errors, killed = [], [], 0
    for n, (name, old, new) in enumerate(MUTANTS, 1):
        if only and only not in name:
            continue
        path = tmp / name
        original = path.read_bytes().decode("utf-8")
        if original.count(old) != 1:
            errors.append((n, name, old[:60], original.count(old)))
            continue
        path.write_bytes(original.replace(old, new).encode("utf-8"))
        try:
            r = subprocess.run([PY, "-m", "pytest", "-x", "-q", "-p", "no:cacheprovider", "tests", "--ignore=tests/test_app.py"],
                              cwd=tmp, env=env, capture_output=True, text=True, timeout=TIMEOUT)
            survived = r.returncode == 0
        except subprocess.TimeoutExpired:
            survived = False                    # Endlosschleife gilt als gefunden
            print(f"[{n:3d}] Zeitueberschreitung (als gefunden gezaehlt)  {name}", flush=True)
        path.write_bytes(original.encode("utf-8"))
        if survived:
            survivors.append((n, name, old[:70], new[:70]))
            print(f"[{n:3d}] UEBERLEBT  {name}: {old[:60]!r} -> {new[:60]!r}", flush=True)
        else:
            killed += 1
            print(f"[{n:3d}] gefunden  {name}", flush=True)
    print(f"\n{killed} gefunden, {len(survivors)} ueberlebt, {len(errors)} Fehler in der Mutantenliste")
    for e in errors:
        print("  FEHLER (Stelle nicht eindeutig gefunden):", e)
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
