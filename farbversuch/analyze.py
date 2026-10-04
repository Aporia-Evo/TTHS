"""Auswertung: Kennzahlen je Strom, Vorhersagen P1-P5, Abbruchkriterium, Bestätigung (Spec v2 §8) und Markdown-Zahlen
für BERICHT.md. Der Auswerter darf C_SPECIAL kennen; er gehört nicht zu den Systemen."""
import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from farbversuch.monitor import SYSTEMS
from farbversuch.run import CONDITIONS, duplicates, parse_seeds
from farbversuch.world import CH_COLOR, C_SPECIAL, DELTAS, HALF, OBS_DIM, obs_index

# Eingefrorene Schwellen der Spec §7 (Hauptlauf mit 10 Seeds)
P2_MIN, P3_MIN = 9, 9
ABORT_RED_MIN, ABORT_GLOBAL_MAX = 5, 3
MAIN_SEEDS = tuple(range(400, 410))      # nur für diese Seeds gelten die vorregistrierten Schwellen und Urteile
M3_SYSTEMS = tuple(n for n in SYSTEMS if n.startswith("M3"))


def is_correct(arm: str, cand: int) -> bool:
    """Richtige Zuschreibung in `red`: Farbe 0 in der Zielzelle (B) bzw. ihr Bit in Richtung der kombinierten Aktion (A)."""
    if arm == "B":
        return cand == C_SPECIAL
    return cand % OBS_DIM == obs_index(CH_COLOR[C_SPECIAL], *DELTAS[cand // OBS_DIM])


def is_colour(arm: str, cand: int) -> bool:
    if arm == "B":
        return cand < len(CH_COLOR)
    return obs_index(CH_COLOR[0], -HALF, -HALF) <= cand % OBS_DIM <= obs_index(CH_COLOR[-1], HALF, HALF)


def stream_metrics(res: dict, condition: str, arm: str, switch: int, horizon: int) -> dict:
    """Kennzahlen eines Stroms. Zeit = abgeschlossene Episoden E; Latenz = E - switch, zensiert bei `horizon`."""
    noticed = res["noticed"]
    if noticed is None:
        false_alarm, notice_latency = False, horizon
    elif condition == "none" or noticed <= switch:
        false_alarm, notice_latency = True, None
    else:
        false_alarm, notice_latency = False, noticed - switch
    opened = res["opened"]
    usability = None
    if condition == "red":
        # richtig nur nach dem Wechsel (E > switch): davor sind alle Ströme gleich, eine Öffnung ist keine Erkennung
        hits = [o for o in opened if o["episode"] > switch and is_correct(arm, o["cand"])]
        first = min(hits, key=lambda o: o["episode"], default=None)
        correct = first is not None
        attr_latency = first["episode"] - switch if correct else horizon
        usability = first.get("gain") if correct else None      # Nutzbarkeit (Spec §6); alte Ergebnisse haben kein "gain"
        misattr = len(opened) - len(hits)
    else:
        correct, attr_latency = None, None
        misattr = sum(is_colour(arm, o["cand"]) for o in opened)
    return {"false_alarm": false_alarm, "notice_latency": notice_latency, "correct": correct,
            "attr_latency": attr_latency, "misattr": misattr, "n_opened": len(opened), "usability": usability}


def _mean(xs: Sequence[float]) -> float | None:
    return float(sum(xs) / len(xs)) if xs else None


def _aggregate(condition: str, pairs: list[tuple[dict, dict]]) -> dict:
    """pairs: (Rohergebnis, Kennzahlen) je Seed mit erfüllter Prämisse."""
    raws, ms = [p[0] for p in pairs], [p[1] for p in pairs]
    lat = [m["notice_latency"] for m in ms if m["notice_latency"] is not None]
    checks = [t for r in raws for t in r["check_sec"]]
    red = condition == "red"
    return {
        "n_seeds": len(pairs),
        "n_false_alarm": sum(m["false_alarm"] for m in ms),
        "n_noticed": sum(1 for r, m in pairs if r["noticed"] is not None and not m["false_alarm"]),
        "notice_latency_mean": None if condition == "none" else _mean(lat),
        "n_correct": sum(m["correct"] for m in ms) if red else None,
        "attr_latency_mean": _mean([m["attr_latency"] for m in ms]) if red else None,
        "misattr": sum(m["misattr"] for m in ms),
        "n_opened": sum(m["n_opened"] for m in ms),
        "buffer_bytes": max((r["buffer_bytes"] for r in raws), default=0),
        "n_fits": sum(r["n_fits"] for r in raws),
        "fit_size": sum(r["fit_size"] for r in raws),
        "check_sec_mean": _mean(checks) or 0.,
        "check_sec_max": max(checks, default=0.),
        "total_sec": float(sum(r["total_sec"] for r in raws)),
    }


def _require_identical(rs: Sequence[dict], key: str, label: str) -> None:
    """Ergebnisse verschiedener Konfigurationen oder Umgebungen (BLAS-Threads!) sind nicht vergleichbar.
    Ein fehlender Schlüssel zählt als None."""
    if len(rs) < 2:
        return
    first = rs[0].get(key)
    differing = [r["seed"] for r in rs if r.get(key) != first]
    if differing:
        raise ValueError(f"{label} weicht von Seed {rs[0]['seed']} ab bei Seeds {differing}")


def _select(results: Sequence[dict], seeds: Sequence[int]) -> list[dict]:
    """Die Ergebnisse der angeforderten Seeds in deren Reihenfolge. Doppelte, fehlende oder nicht vergleichbare
    Ergebnisse sind ein Fehler."""
    if dup := duplicates(seeds):
        raise ValueError(f"doppelte Seeds in der Seed-Liste: {dup}")
    if dup := duplicates([r["seed"] for r in results]):
        raise ValueError(f"mehr als ein Ergebnis für Seeds {dup}")
    by_seed = {r["seed"]: r for r in results}
    missing = [s for s in seeds if s not in by_seed]
    if missing:
        raise ValueError(f"kein Ergebnis für Seeds {missing}")
    rs = [by_seed[s] for s in seeds]
    _require_identical(rs, "config", "Konfiguration")
    _require_identical(rs, "env", "Umgebung (env)")
    _require_identical(rs, "fingerprint", "Fingerabdruck von Code und Umgebung")
    return rs


def _m3_red(r: dict, name: str = "M3-B") -> dict | None:
    """Kennzahlen eines M3-Systems unter `red`; None bei gescheiterter Prämisse (dann gibt es keine Bedingungen)."""
    if not r.get("conditions"):
        return None
    cfg = r["config"]
    switch = cfg["switch_episode"]
    return stream_metrics(r["conditions"]["red"][name], "red", name[-1], switch, cfg["n_deploy_episodes"] - switch)


def _seed_row(r: dict) -> dict:
    """Werte je Seed für den Bericht (Spec §6). Was ein altes Ergebnis nicht enthält, ist None."""
    premise = r["premise"]
    practice = r.get("practice")
    return {"seed": r["seed"], "premise_ok": bool(premise["ok"]),
            "color_invariance": premise.get("color_invariance"), "restanteil": premise.get("restanteil"),
            "shift": premise.get("shift"),
            "practice": None if practice is None else {n: [e["name"] for e in es] for n, es in practice.items()},
            "delta": r.get("delta"),
            # Nutzbarkeit je M3-System (Spec §6); None ohne Bedingungen
            "usability": None if not r.get("conditions") else {n: _m3_red(r, n)["usability"] for n in M3_SYSTEMS}}


def evaluate(results: Sequence[dict], seeds: Sequence[int]) -> dict:
    """Zählt und misst immer; Urteile (`fulfilled`, `triggered`) gibt es nur für die vorregistrierten MAIN_SEEDS, sonst None."""
    rs = _select(results, seeds)
    cfg0 = (rs[0].get("config") or {}) if rs else {}               # die Konfigurationen sind identisch (_select)
    ok = [r for r in rs if r["premise"]["ok"]]
    failed = [r["seed"] for r in rs if not r["premise"]["ok"]]

    pairs: dict[str, dict[str, list]] = {n: {c: [] for c in CONDITIONS} for n in SYSTEMS}
    for r in ok:
        cfg = r["config"]
        switch, horizon = cfg["switch_episode"], cfg["n_deploy_episodes"] - cfg["switch_episode"]
        for n in SYSTEMS:
            for c in CONDITIONS:
                raw = r["conditions"][c][n]
                pairs[n][c].append((raw, stream_metrics(raw, c, n[-1], switch, horizon)))
    systems = {n: {c: _aggregate(c, pairs[n][c]) for c in CONDITIONS} for n in SYSTEMS}

    red_correct = systems["M3-B"]["red"]["n_correct"]
    # gescheiterte Prämisse zählt gegen M3-B: nicht richtig in red, geöffnet in global
    global_open = len(failed) + sum(m["n_opened"] > 0 for _, m in pairs["M3-B"]["global"])
    n_all = len(rs)
    prereg = set(seeds) == set(MAIN_SEEDS)                 # Duplikate sind oben ausgeschlossen

    def verdict(x: bool) -> bool | None:
        return x if prereg else None

    latency_A, latency_B = (systems[n]["red"]["attr_latency_mean"] for n in ("M3-A", "M3-B"))
    misattr_A, misattr_B = (sum(systems[n][c]["misattr"] for c in CONDITIONS) for n in ("M3-A", "M3-B"))
    hits_B, hits_S1 = (systems[n]["red"]["n_correct"] for n in ("M3-B", "S1-B"))
    return {
        "preregistered": prereg,
        "P1": {"ok_seeds": [r["seed"] for r in ok], "failed_seeds": failed},
        "P2": {"count": red_correct, "fulfilled": verdict(red_correct >= P2_MIN)},
        "P3": {"count": n_all - global_open, "fulfilled": verdict(n_all - global_open >= P3_MIN)},
        "P4": {"latency_A": latency_A, "latency_B": latency_B, "misattr_A": misattr_A, "misattr_B": misattr_B,
               "fulfilled": verdict(bool(ok) and (latency_A > latency_B or misattr_A > misattr_B))},
        "P5": {"M3-B": hits_B, "S1-B": hits_S1, "fulfilled": verdict(bool(ok) and hits_B >= hits_S1)},
        "abort": {"red_correct": red_correct, "global_open": global_open,
                  "triggered": verdict(red_correct < ABORT_RED_MIN or global_open > ABORT_GLOBAL_MAX)},
        "systems": systems,
        "seeds": [_seed_row(r) for r in rs],
        "n_null_streams": cfg0.get("n_null_streams"), "max_null_alarms": cfg0.get("max_null_alarms", 0),
    }


CONFIRM_MIN_SEED, CONFIRM_MIN_N = 500, 5      # Spec v2 §8: Bestätigungsrunden auf 500–504, 505–509, 510–514 …


def _check_confirmation_seeds(seeds: Sequence[int]) -> None:
    if not seeds:
        raise ValueError("keine Seeds für die Bestätigung")
    if used := sorted(set(seeds) & set(MAIN_SEEDS)):
        raise ValueError(f"Die Bestätigung darf nicht auf Hauptlauf-Seeds ({MAIN_SEEDS[0]}–{MAIN_SEEDS[-1]}) laufen; "
                         f"verwendet: {used}")
    if dup := duplicates(seeds):
        raise ValueError(f"doppelte Seeds in der Seed-Liste: {dup}")
    if low := sorted(s for s in seeds if s < CONFIRM_MIN_SEED):
        raise ValueError(f"Die Bestätigung läuft nur auf Seeds ab {CONFIRM_MIN_SEED} (Spec v2 §8); zu klein: {low}")
    if len(seeds) < CONFIRM_MIN_N:
        raise ValueError(f"Die Bestätigung braucht mindestens {CONFIRM_MIN_N} Seeds (Spec v2 §8), angegeben: "
                         f"{len(seeds)}")


CONFIRMATION_CRITERIA = ("premise", "no_false_open", "red_correct")


def evaluate_confirmation(results: Sequence[dict], seeds: Sequence[int]) -> dict:
    """Bestätigung (Spec v2 §8, Präzisierung des Nutzers vom 04.10.2026): ein Seed zählt nur, wenn alle drei Kriterien
    zugleich gelten; bestätigt, wenn das in mindestens ⌈0,8·n⌉ Seeds so ist ("joint"). Die Zählungen je Kriterium
    stehen zur Information daneben und entscheiden nichts. Ein Seed mit gescheiterter Prämisse erfüllt auch Kriterium 2
    und 3 nicht. Seeds des Hauptlaufs sind ein Fehler."""
    _check_confirmation_seeds(seeds)
    rs = _select(results, seeds)
    n = len(rs)
    need = -(-4 * n // 5)                                      # ⌈0,8·n⌉ ohne Gleitkomma
    per_seed = {}
    for r in rs:
        ok = bool(r["premise"]["ok"])
        # geöffnet = nur Wiederöffnungen; die Übungs-Ontologie steht nicht in "opened"
        quiet = ok and all(not r["conditions"][c]["M3-B"]["opened"] for c in ("none", "global"))
        row = {"premise": ok, "no_false_open": quiet, "red_correct": ok and bool(_m3_red(r)["correct"])}
        per_seed[r["seed"]] = {**row, "all": all(row.values())}

    def criterion(key: str) -> dict:
        count = sum(row[key] for row in per_seed.values())
        return {"count": count, "fulfilled": count >= need}

    crit = {key: criterion(key) for key in CONFIRMATION_CRITERIA}
    joint_count = sum(row["all"] for row in per_seed.values())
    joint = {"count": joint_count, "need": need, "fulfilled": joint_count >= need}
    return {"n": n, "need": need, **crit, "joint": joint, "confirmed": joint["fulfilled"], "per_seed": per_seed}


def _f(x, nd: int = 1) -> str:
    if x is None:
        return "–"
    return str(x) if isinstance(x, int) else f"{x:.{nd}f}"


def _verdict(fulfilled: bool | None) -> str:
    if fulfilled is None:
        return "–"
    return "erfüllt" if fulfilled else "nicht erfüllt"


def _percent_de(x: float) -> str:
    return f"{100 * x:.1f}".replace(".", ",") + " %"


def _table(header: Sequence[str], rows: Sequence[Sequence[str]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return lines + [""]


def _seed_values_table(ev: dict) -> list[str]:
    header = (["Seed", "Prämisse", "Farbinvarianz", "Restanteil", "Verschiebung"]
              + [f"Übungs-Ontologie {n}" for n in SYSTEMS] + [f"δ {n}" for n in M3_SYSTEMS]
              + [f"Nutzbarkeit {n}" for n in M3_SYSTEMS])
    rows = []
    for row in ev["seeds"]:
        practice, delta, usability = row["practice"] or {}, row["delta"] or {}, row["usability"] or {}
        rows.append([str(row["seed"]), _verdict(row["premise_ok"]), _f(row["color_invariance"], 3),
                     _f(row["restanteil"], 3), _f(row["shift"], 3)]
                    + ["–" if n not in practice else ", ".join(practice[n]) or "keine" for n in SYSTEMS]
                    + [_f(delta.get(n), 4) for n in M3_SYSTEMS] + [_f(usability.get(n), 4) for n in M3_SYSTEMS])
    return _table(header, rows)


def report_markdown(ev: dict) -> str:
    p1 = ev["P1"]
    n_ok, n = len(p1["ok_seeds"]), len(p1["ok_seeds"]) + len(p1["failed_seeds"])
    p4, p5, ab, systems = ev["P4"], ev["P5"], ev["abort"], ev["systems"]
    failed = ", ".join(str(s) for s in p1["failed_seeds"]) or "keine"
    gap_lat = None if p4["latency_A"] is None else p4["latency_A"] - p4["latency_B"]
    out = ["## Auswertung", ""]
    if not ev["preregistered"]:
        seeds = ", ".join(str(x) for x in sorted(p1["ok_seeds"] + p1["failed_seeds"]))
        out += [f"> **Explorative Auswertung (Seeds {seeds}) – keine Prüfung der vorregistrierten Vorhersagen; "
                f"diese gilt nur für die Seeds {MAIN_SEEDS[0]}–{MAIN_SEEDS[-1]}.**", ""]
    out += ["### Vorhersagen", ""]
    out += _table(["Vorhersage", "Ergebnis", "Zahlen"], [
        ["P1 Prämissen", _verdict(not p1["failed_seeds"]), f"{n_ok}/{n} Seeds erfüllen die Prämissen; gescheitert: {failed}"],
        ["P2 M3-B schreibt `red` richtig zu", _verdict(ev["P2"]["fulfilled"]),
         f"{ev['P2']['count']}/{n} Seeds (Schwelle ≥ {P2_MIN})"],
        ["P3 M3-B öffnet bei `global` nichts", _verdict(ev["P3"]["fulfilled"]),
         f"{ev['P3']['count']}/{n} Seeds ohne Öffnung (Schwelle ≥ {P3_MIN})"],
        ["P4 M3-A langsamer oder mehr Fehlzuschreibungen als M3-B", _verdict(p4["fulfilled"]),
         f"Zuschreibungslatenz `red` (Mittel, zensiert am Horizont): M3-A {_f(p4['latency_A'])}, "
         f"M3-B {_f(p4['latency_B'])}, Abstand A − B {_f(gap_lat)} Episoden; "
         f"Fehlzuschreibungen insgesamt: M3-A {p4['misattr_A']}, M3-B {p4['misattr_B']}, "
         f"Abstand A − B {p4['misattr_A'] - p4['misattr_B']}"],
        ["P5 M3-B mindestens so treffsicher wie S1-B", _verdict(p5["fulfilled"]),
         f"Treffer bei `red`: M3-B {p5['M3-B']}, S1-B {p5['S1-B']} (von {n_ok} Seeds mit erfüllter Prämisse)"],
    ])
    out += ["Seeds mit gescheiterter Prämisse zählen bei P2, P3 und beim Abbruchkriterium gegen M3-B "
            "und fehlen in P4 und P5.", "", "### Abbruchkriterium", ""]
    out += _table(["Größe", "Wert", "Abbruch bei"], [
        ["Richtige Zuschreibung M3-B bei `red`", f"{ab['red_correct']}/{n} Seeds", f"< {ABORT_RED_MIN}"],
        ["M3-B öffnet bei `global` ein Merkmal", f"{ab['global_open']}/{n} Seeds", f"> {ABORT_GLOBAL_MAX}"],
    ])
    if ab["triggered"] is not None:
        out.append("Abbruchkriterium ausgelöst: das Wiederöffnen per Modellvergleich funktioniert in diesem Aufbau nicht."
                   if ab["triggered"] else "Abbruchkriterium nicht ausgelöst.")
    out += ["", "### Werte je Seed", ""]
    out += _seed_values_table(ev)
    out += ["Prämisse umfasst P1 und P1b. Restanteil und Verschiebung gehören zu P1b. Übungs-Ontologie: vor dem Einsatz "
            "geöffnete Merkmale des jeweiligen Systems; sie zählen nie als geöffnet. δ: Mindestverbesserung aus den "
            "Null-Strömen. Nutzbarkeit: mittlere Verbesserung (nats pro Schritt) des richtigen Merkmals (Arm B: „Farbe 0“, "
            "Arm A: Farbe-0-Bit in Richtung der Aktion) bei der ersten richtigen Öffnung durch das jeweilige M3-System "
            "unter `red`. „–“: im Ergebnis nicht enthalten oder keine richtige Öffnung.", ""]
    out += [f"### Kennzahlen je System und Bedingung ({n_ok} Seeds mit erfüllter Prämisse)", ""]
    rows = []
    for name in SYSTEMS:
        for cond in CONDITIONS:
            m = systems[name][cond]
            rows.append([name, cond, str(m["n_seeds"]), str(m["n_false_alarm"]), str(m["n_noticed"]),
                         _f(m["notice_latency_mean"]), _f(m["n_correct"]), _f(m["attr_latency_mean"]),
                         str(m["misattr"]), str(m["n_opened"])])
    out += _table(["System", "Bedingung", "Seeds", "Fehlalarme", "Bemerkt", "Latenz Bemerken (Mittel)",
                   "Richtig zugeschrieben", "Latenz Zuschreibung (Mittel)", "Fehlzuschreibungen", "Geöffnet"], rows)
    n_null, k = ev["n_null_streams"], ev["max_null_alarms"]       # k = 0 in v2: 1/(n + 1)
    rate = ("–" if n_null is None else
            f"≈ {k + 1}/{n_null + 1} = {_percent_de((k + 1) / (n_null + 1))} "
            f"({n_null} Null-Ströme, höchstens {k} Alarme bei der Kalibrierung)")
    out += ["Latenzen in Episoden ab dem Wechsel; nicht bemerkt oder nicht zugeschrieben zählt als Horizont. "
            "Die Latenz des Bemerkens mittelt über Seeds ohne Fehlalarm und gilt nicht für `none`.", "",
            f"Erwartete Fehlalarmrate pro Strom: {rate}.", "", "### Kosten", ""]
    rows = []
    for name in SYSTEMS:
        for cond in CONDITIONS:
            m = systems[name][cond]
            rows.append([name, cond, str(m["buffer_bytes"]), str(m["n_fits"]), str(m["fit_size"]),
                         _f(m["check_sec_mean"], 3), _f(m["check_sec_max"], 3), _f(m["total_sec"], 2)])
    out += _table(["System", "Bedingung", "Puffer (Byte)", "Anpassungen", "Größe der Anpassungen",
                   "Prüfung Mittel (s)", "Prüfung Max (s)", "Gesamt (s)"], rows)
    return "\n".join(out)


def confirmation_markdown(ev: dict) -> str:
    """Abschnitt „Bestätigung“ aus dem Ergebnis von evaluate_confirmation."""
    n, need, joint = ev["n"], ev["need"], ev["joint"]
    seeds = ", ".join(str(s) for s in ev["per_seed"])
    out = ["## Bestätigung (Spec v2 §8)", "",
           f"Seeds {seeds} (n = {n}), explorativ ausgewertet. Die Methode gilt als bestätigt, wenn in mindestens "
           f"{need} von {n} Seeds alle drei Kriterien gleichzeitig gelten (Präzisierung, Entscheidung des Nutzers vom "
           f"04.10.2026). Ein Seed mit gescheiterter Prämisse zählt bei den Kriterien 2 und 3 als nicht erfüllt. "
           f"Die Zählungen je Kriterium stehen nur zur Information da.", ""]
    labels = [("premise", "1 Prämissen P1 und P1b erfüllt"),
              ("no_false_open", "2 M3-B öffnet bei `none` und `global` nichts über die Übungs-Ontologie hinaus"),
              ("red_correct", "3 M3-B öffnet bei `red` „Farbe 0“ nach dem Wechsel")]
    out += _table(["Kriterium", "Seeds", "Benötigt", "Ergebnis"],
                  [["**Alle drei Kriterien gleichzeitig (entscheidend)**", f"{joint['count']}/{n}", f"≥ {need}",
                    _verdict(joint["fulfilled"])]]
                  + [[f"{label} (zur Information)", f"{ev[key]['count']}/{n}", "–", "–"] for key, label in labels])
    out += _table(["Seed", "Kriterium 1", "Kriterium 2", "Kriterium 3", "Alle drei"],
                  [[str(seed)] + ["ja" if row[key] else "nein" for key in (*CONFIRMATION_CRITERIA, "all")]
                   for seed, row in ev["per_seed"].items()])
    out.append("Bestätigt." if ev["confirmed"] else
               "Nicht bestätigt: Ergebnis zurück an den Nutzer; eine weitere Runde läuft nur auf neuen Seeds.")
    return "\n".join(out)


def load_results(results_dir: str | Path, seeds: Sequence[int]) -> list[dict]:
    out = []
    for s in seeds:
        path = Path(results_dir) / f"seed_{s}.json"
        if not path.exists():
            raise FileNotFoundError(f"seed_{s}.json fehlt in {results_dir}")
        out.append(json.loads(path.read_text()))
    return out


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="python -m farbversuch.analyze", description="Farbversuch: Ergebnisse auswerten")
    ap.add_argument("--results", required=True, help="Ordner mit seed_<n>.json")
    ap.add_argument("--seeds", required=True, help='z. B. "400-409"')
    ap.add_argument("--confirm", action="store_true",
                    help="Bestätigungsabschnitt (Spec v2 §8) anhängen; mindestens 5 Seeds, alle ab 500")
    args = ap.parse_args(argv)
    seeds = parse_seeds(args.seeds)
    if args.confirm:
        _check_confirmation_seeds(seeds)                       # vor dem Laden: der Seed-Fehler soll nicht untergehen
    results = load_results(args.results, seeds)
    out = report_markdown(evaluate(results, seeds))
    if args.confirm:
        out += "\n" + confirmation_markdown(evaluate_confirmation(results, seeds))
    print(out)


if __name__ == "__main__":
    main()
