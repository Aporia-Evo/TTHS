import json

import pytest

from farbversuch.analyze import (MAIN_SEEDS, confirmation_markdown, evaluate, evaluate_confirmation, is_colour,
                                 is_correct, load_results, main, report_markdown, stream_metrics)
from farbversuch.monitor import SYSTEMS
from farbversuch.run import CONDITIONS
from farbversuch.world import CH_COLOR, CH_GOAL, CH_WALL, C_SPECIAL, DELTAS, obs_index


def sysres(noticed=None, opened=(), gain=None):
    """opened: (cand, episode) oder (cand, episode, gain); `gain` ist der Standard für Öffnungen ohne eigenen."""
    return {"noticed": noticed,
            "practice": [], "delta": None,
            "opened": [{"cand": c, "name": "", "episode": e, "gain": (g[0] if g else gain)} for c, e, *g in opened],
            "buffer_bytes": 0, "n_fits": 0, "fit_size": 0, "check_sec": [], "total_sec": 0.}


PRACTICE = {"M3-B": [{"cand": 4, "name": "Wand"}], "M3-A": [], "S1-B": [{"cand": 5, "name": "Ziel"}],
            "S1-A": [{"cand": 3, "name": "bit3&a0"}, {"cand": 300, "name": "bit2&a1"}]}


def fake_result(seed, red_ok=True, global_open=False, ok=True, gain=0.05):
    conds = {c: {s: sysres() for s in SYSTEMS} for c in CONDITIONS}
    conds["red"]["M3-B"] = sysres(110, [(C_SPECIAL, 120)] if red_ok else [], gain=gain)
    conds["global"]["M3-B"] = sysres(110, [(4, 120)] if global_open else [])
    return {"seed": seed, "config": {"switch_episode": 100, "n_deploy_episodes": 400, "n_null_streams": 20},
            "premise": {"ok": ok, "color_invariance": 0.99, "fwd_surprise": 1.0, "freq_surprise": 1.5,
                        "restanteil": 0.05, "shift": 0.1},
            "practice": PRACTICE, "delta": {"M3-B": 0.002, "M3-A": 0.003},
            "conditions": conds if ok else None}


A_RED = 0 * 298 + obs_index(CH_COLOR[C_SPECIAL], -1, 0)       # Farbe 0 oben, Aktion oben


def test_is_correct():
    assert is_correct("B", C_SPECIAL) and not is_correct("B", 4)
    assert is_correct("A", A_RED) and not is_correct("A", 1 * 298 + obs_index(CH_COLOR[C_SPECIAL], -1, 0))


def test_latency_and_censoring():
    m = stream_metrics(sysres(130, [(C_SPECIAL, 140)]), "red", "B", 100, 300)
    assert (m["notice_latency"], m["correct"], m["attr_latency"], m["false_alarm"]) == (30, True, 40, False)
    assert stream_metrics(sysres(), "red", "B", 100, 300)["notice_latency"] == 300
    assert stream_metrics(sysres(250), "none", "B", 100, 300)["false_alarm"]


def test_prechange_alarm_in_red():               # Review Focus 4
    m = stream_metrics(sysres(90, [(C_SPECIAL, 120)]), "red", "B", 100, 300)
    assert m["false_alarm"] and m["notice_latency"] is None and m["correct"] and m["attr_latency"] == 20


def test_preswitch_opening_in_red_is_a_misattribution():
    # vor dem Wechsel sind alle vier Ströme gleich: eine frühe Öffnung kann keine Erkennung der roten Änderung sein
    m = stream_metrics(sysres(60, [(C_SPECIAL, 70)]), "red", "B", 100, 300)
    assert (m["correct"], m["attr_latency"], m["misattr"], m["n_opened"]) == (False, 300, 1, 1)
    # bei E = switch ist noch keine rote Episode abgeschlossen; E = switch + 1 ist die erste mögliche richtige
    assert not stream_metrics(sysres(80, [(C_SPECIAL, 100)]), "red", "B", 100, 300)["correct"]
    m = stream_metrics(sysres(80, [(C_SPECIAL, 101)]), "red", "B", 100, 300)
    assert m["correct"] and m["attr_latency"] == 1 and m["misattr"] == 0
    m = stream_metrics(sysres(60, [(C_SPECIAL, 70), (C_SPECIAL, 120)]), "red", "B", 100, 300)
    assert (m["correct"], m["attr_latency"], m["misattr"]) == (True, 20, 1)
    m = stream_metrics(sysres(60, [(A_RED, 70)]), "red", "A", 100, 300)
    assert (m["correct"], m["attr_latency"], m["misattr"]) == (False, 300, 1)


def test_preswitch_correct_opening_does_not_count_for_p2():
    seeds = list(range(400, 410))
    results = [fake_result(s) for s in seeds]
    sys_variant(results[0], "M3-B", "red", sysres(60, [(C_SPECIAL, 70)]))
    assert evaluate(results, seeds)["P2"]["count"] == 9


def test_misattribution_rules():
    assert stream_metrics(sysres(110, [(2, 120), (4, 130)]), "global", "B", 100, 300)["misattr"] == 1
    assert stream_metrics(sysres(110, [(4, 120), (C_SPECIAL, 130)]), "red", "B", 100, 300)["misattr"] == 1


def test_predictions_and_abort():
    seeds = list(range(400, 410))
    ev = evaluate([fake_result(s, red_ok=s != 400, global_open=s == 401) for s in seeds], seeds)
    assert ev["P2"] == {"count": 9, "fulfilled": True} and ev["P3"]["fulfilled"] and not ev["abort"]["triggered"]
    ev = evaluate([fake_result(s, red_ok=s < 404) for s in seeds], seeds)
    assert not ev["P2"]["fulfilled"] and ev["abort"]["triggered"]
    ev = evaluate([fake_result(s, global_open=s < 404) for s in seeds], seeds)
    assert not ev["P3"]["fulfilled"] and ev["abort"]["triggered"]


def test_failed_premise_counts_against_m3b():
    seeds = list(range(400, 410))
    ev = evaluate([fake_result(s, ok=s != 409) for s in seeds], seeds)
    assert ev["P1"]["failed_seeds"] == [409] and ev["P2"]["count"] == 9 and ev["abort"]["global_open"] == 1


# --- über die Vorgabe hinaus ---

def test_colour_features_and_arm_a_misattribution():
    assert [is_colour("B", c) for c in range(6)] == [True] * 4 + [False] * 2
    colour_bit = 2 * 298 + obs_index(CH_COLOR[3], 2, -3)          # irgendein Farbbit, Aktion unten
    wall_bit = obs_index(CH_WALL, -1, 0)
    goal_bit = obs_index(CH_GOAL, 0, 1)
    assert is_colour("A", colour_bit)
    assert not is_colour("A", wall_bit) and not is_colour("A", goal_bit) and not is_colour("A", 3 * 298 + 297)
    assert stream_metrics(sysres(110, [(colour_bit, 120), (wall_bit, 125)]), "walls", "A", 100, 300)["misattr"] == 1
    # red, Arm A: jede Öffnung außer der richtigen (auch Wandbit) ist Fehlzuschreibung
    m = stream_metrics(sysres(110, [(wall_bit, 120), (A_RED, 130), (colour_bit, 140)]), "red", "A", 100, 300)
    assert m["correct"] and m["attr_latency"] == 30 and m["misattr"] == 2 and m["n_opened"] == 3


def test_opening_before_switch_is_not_correct_and_none_gives_horizon():
    m = stream_metrics(sysres(80, [(C_SPECIAL, 90)]), "red", "B", 100, 300)
    assert m["attr_latency"] == 300 and not m["correct"] and m["misattr"] == 1
    m = stream_metrics(sysres(110, [(4, 120)]), "red", "B", 100, 300)
    assert not m["correct"] and m["attr_latency"] == 300
    m = stream_metrics(sysres(110, [(C_SPECIAL, 150), (C_SPECIAL, 130)]), "red", "B", 100, 300)
    assert m["attr_latency"] == 30                                # frühestes richtiges Öffnen zählt
    m = stream_metrics(sysres(110, [(C_SPECIAL, 120)]), "global", "B", 100, 300)
    assert m["correct"] is None and m["attr_latency"] is None and m["misattr"] == 1 and m["n_opened"] == 1


def test_none_condition_every_notice_is_false_alarm():
    m = stream_metrics(sysres(250), "none", "B", 100, 300)
    assert m["false_alarm"] and m["notice_latency"] is None
    assert not stream_metrics(sysres(), "none", "B", 100, 300)["false_alarm"]


def test_failed_premise_counts_as_global_open_and_misses_red():
    seeds = list(range(400, 410))
    ev = evaluate([fake_result(s, ok=s >= 406) for s in seeds], seeds)
    assert ev["P1"]["ok_seeds"] == [406, 407, 408, 409] and ev["P1"]["failed_seeds"] == [400, 401, 402, 403, 404, 405]
    assert ev["P2"]["count"] == 4 and ev["P3"]["count"] == 4 and not ev["P3"]["fulfilled"]
    assert ev["abort"] == {"red_correct": 4, "global_open": 6, "triggered": True}


def sys_variant(res, name, cond, sr):
    res["conditions"][cond][name] = sr
    return res


def test_p4_p5_compare_only_premise_ok_seeds():
    seeds = list(range(400, 410))
    results = []
    for s in seeds:
        r = fake_result(s, ok=s != 409)
        if r["conditions"]:
            # M3-A: spät (Latenz 80 statt 20) und eine Fehlzuschreibung in none
            sys_variant(r, "M3-A", "red", sysres(110, [(A_RED, 180)]))
            sys_variant(r, "M3-A", "none", sysres(110, [(2 * 298 + obs_index(CH_COLOR[1], 0, 0), 120)]))
            # S1-B trifft nur in 5 Seeds
            sys_variant(r, "S1-B", "red", sysres(105, [(C_SPECIAL, 106)] if s < 405 else []))
        results.append(r)
    ev = evaluate(results, seeds)
    assert ev["P4"] == {"latency_A": 80.0, "latency_B": 20.0, "misattr_A": 9, "misattr_B": 0, "fulfilled": True}
    assert ev["P5"] == {"M3-B": 9, "S1-B": 5, "fulfilled": True}
    # S1-B besser als M3-B: P5 nicht erfüllt
    results = [fake_result(s, red_ok=s != 400) for s in seeds]
    for r in results:
        sys_variant(r, "S1-B", "red", sysres(105, [(C_SPECIAL, 106)]))
    ev = evaluate(results, seeds)
    assert ev["P5"] == {"M3-B": 9, "S1-B": 10, "fulfilled": False}


def test_p4_fulfilled_by_either_gap_and_not_by_neither():
    seeds = list(range(400, 410))
    base = [fake_result(s) for s in seeds]                      # M3-A: nie öffnen (Horizont 300) -> langsamer
    assert evaluate(base, seeds)["P4"]["fulfilled"]
    equal = []
    for s in seeds:
        r = fake_result(s)
        sys_variant(r, "M3-A", "red", sysres(110, [(A_RED, 120)]))
        equal.append(r)
    ev = evaluate(equal, seeds)["P4"]
    assert (ev["latency_A"], ev["latency_B"], ev["misattr_A"], ev["misattr_B"]) == (20.0, 20.0, 0, 0)
    assert not ev["fulfilled"]
    more_misattr = []
    for s in seeds:
        r = fake_result(s)
        sys_variant(r, "M3-A", "red", sysres(110, [(A_RED, 120), (1 * 298 + 297, 130)]))
        more_misattr.append(r)
    ev = evaluate(more_misattr, seeds)["P4"]
    assert ev["latency_A"] == ev["latency_B"] and ev["misattr_A"] == 10 and ev["fulfilled"]


def test_system_metrics_and_costs():
    seeds = [400, 401]
    results = [fake_result(s) for s in seeds]
    for k, r in enumerate(results):
        r["conditions"]["red"]["M3-B"].update(buffer_bytes=1000, n_fits=3 + k, fit_size=100 * (k + 1),
                                              check_sec=[0.5, 1.5] if k == 0 else [2.5], total_sec=2.0 + k)
    m = evaluate(results, seeds)["systems"]["M3-B"]["red"]
    assert (m["n_seeds"], m["n_noticed"], m["n_false_alarm"], m["n_correct"]) == (2, 2, 0, 2)
    assert (m["notice_latency_mean"], m["attr_latency_mean"], m["misattr"], m["n_opened"]) == (10.0, 20.0, 0, 2)
    assert (m["n_fits"], m["fit_size"], m["buffer_bytes"], m["total_sec"]) == (7, 300, 1000, 5.0)
    assert m["check_sec_mean"] == pytest.approx(1.5) and m["check_sec_max"] == 2.5
    ev = evaluate(results, seeds)["systems"]
    assert set(ev) == set(SYSTEMS) and all(set(ev[n]) == set(CONDITIONS) for n in SYSTEMS)
    assert ev["M3-B"]["none"]["notice_latency_mean"] is None and ev["M3-B"]["global"]["n_correct"] is None


def test_report_markdown_lists_predictions_numbers_and_costs():
    seeds = list(range(400, 410))
    ev = evaluate([fake_result(s, red_ok=s != 400, global_open=s == 401, ok=s != 409) for s in seeds], seeds)
    md = report_markdown(ev)
    for label in ("P1", "P2", "P3", "P4", "P5", "Abbruchkriterium"):
        assert label in md
    assert "nicht erfüllt" in md and "erfüllt" in md
    assert "409" in md                                          # gescheiterter Seed wird genannt
    for name in SYSTEMS:
        assert name in md
    for word in ("Puffer", "Anpassungen", "Prüfung", "Gesamt"):
        assert word in md
    assert "|" in md and "---" in md


def test_missing_seed_file_names_the_seed(tmp_path):
    for s in (400, 401):
        (tmp_path / f"seed_{s}.json").write_text(json.dumps(fake_result(s)))
    with pytest.raises(FileNotFoundError, match="seed_402"):
        load_results(tmp_path, [400, 401, 402])
    assert [r["seed"] for r in load_results(tmp_path, [400, 401])] == [400, 401]


def test_evaluate_rejects_unlisted_seed():
    with pytest.raises(ValueError, match="402"):
        evaluate([fake_result(400), fake_result(401)], [400, 401, 402])


def test_main_prints_markdown(tmp_path, capsys):
    for s in range(400, 403):
        (tmp_path / f"seed_{s}.json").write_text(json.dumps(fake_result(s)))
    main(["--results", str(tmp_path), "--seeds", "400-402"])
    out = capsys.readouterr().out
    assert "P2" in out and "M3-B" in out
    with pytest.raises(FileNotFoundError, match="seed_403"):
        main(["--results", str(tmp_path), "--seeds", "400-403"])


def test_evaluate_requires_identical_config_and_env():
    seeds = [400, 401, 402]
    env = {"OMP_NUM_THREADS": "1", "numpy": "2.4.0"}

    def results(**changes):
        rs = [{**fake_result(s), "env": dict(env)} for s in seeds]
        for seed, change in changes.items():
            rs[seeds.index(int(seed[1:]))].update(change)
        return rs

    assert evaluate(results(), seeds)["P2"]["count"] == 3
    with pytest.raises(ValueError, match="Konfiguration.*401") as exc:
        evaluate(results(s401={"config": {"switch_episode": 100, "n_deploy_episodes": 300}}), seeds)
    assert "402" not in str(exc.value)
    with pytest.raises(ValueError, match="Umgebung.*402") as exc:
        evaluate(results(s402={"env": {**env, "OMP_NUM_THREADS": "3"}}), seeds)
    assert "401" not in str(exc.value)
    with pytest.raises(ValueError, match="Umgebung.*401.*402"):       # fehlendes "env" zählt als None
        evaluate(results(s401={"env": None}, s402={"env": {"numpy": "9"}}), seeds)
    plain = [fake_result(s) for s in seeds]                           # alle ohne "env": einheitlich None
    assert evaluate(plain, seeds)["P2"]["count"] == 3
    mixed = [fake_result(400), {**fake_result(401), "env": env}, fake_result(402)]
    with pytest.raises(ValueError, match="Umgebung.*401"):
        evaluate(mixed, seeds)


def test_evaluate_compares_only_the_listed_seeds():
    results = [fake_result(s) for s in (400, 401)] + [{**fake_result(999), "env": {"other": 1}}]
    assert evaluate(results, [400, 401])["P2"]["count"] == 2


# --- Review des Nutzers: doppelte Seeds (U1) ---

def test_evaluate_rejects_duplicate_requested_seeds():
    # ein erfolgreiches Ergebnis, zehnmal angefordert, darf nicht als "10/10 Treffer" zählen
    with pytest.raises(ValueError, match="400"):
        evaluate([fake_result(400)], [400] * 10)
    with pytest.raises(ValueError, match="Seeds.*401") as exc:
        evaluate([fake_result(s) for s in (400, 401, 402)], [400, 401, 401, 402])
    assert "400" not in str(exc.value) and "402" not in str(exc.value)     # nur die doppelten werden genannt


def test_evaluate_rejects_several_results_for_one_seed():
    results = [fake_result(400), fake_result(401), fake_result(401, red_ok=False)]
    with pytest.raises(ValueError, match="Ergebnis.*401") as exc:
        evaluate(results, [400, 401])
    assert "400" not in str(exc.value)
    with pytest.raises(ValueError, match="999"):                          # auch für nicht angeforderte Seeds
        evaluate([fake_result(400), fake_result(999), fake_result(999)], [400])


def test_cli_rejects_duplicate_seeds(tmp_path):
    (tmp_path / "seed_400.json").write_text(json.dumps(fake_result(400)))
    with pytest.raises(ValueError, match="400"):
        main(["--results", str(tmp_path), "--seeds", "400,400"])
    with pytest.raises(ValueError, match="400"):                          # auch ohne parse_seeds: load_results + evaluate
        evaluate(load_results(tmp_path, [400, 400]), [400, 400])


# --- Review des Nutzers: vorregistrierte Urteile nur für die Hauptseeds (U2) ---

VERDICTS = (("P2", "fulfilled"), ("P3", "fulfilled"), ("P4", "fulfilled"), ("P5", "fulfilled"), ("abort", "triggered"))


def verdicts(ev):
    return {f"{k}.{f}": ev[k][f] for k, f in VERDICTS}


def test_main_seeds_are_the_preregistered_ten():
    assert MAIN_SEEDS == tuple(range(400, 410))


@pytest.mark.parametrize("seeds", [list(MAIN_SEEDS), list(reversed(MAIN_SEEDS)), [405, 400, 409, 401, 408, 402, 407, 403, 406, 404]])
def test_preregistered_for_exactly_the_main_seeds_in_any_order(seeds):
    ev = evaluate([fake_result(s) for s in seeds], seeds)
    assert ev["preregistered"] is True
    assert all(isinstance(v, bool) for v in verdicts(ev).values())
    assert ev["P2"] == {"count": 10, "fulfilled": True} and ev["abort"]["triggered"] is False


@pytest.mark.parametrize("seeds", [[0], [400], list(range(400, 409)), list(range(401, 411)), list(range(400, 420)),
                                   list(range(399, 410))])
def test_other_seed_sets_are_explorative_with_counts_but_no_verdicts(seeds):
    ev = evaluate([fake_result(s) for s in seeds], seeds)
    assert ev["preregistered"] is False
    assert verdicts(ev) == dict.fromkeys(verdicts(ev))                   # alles None
    assert ev["P2"]["count"] == len(seeds) and ev["P3"]["count"] == len(seeds)
    assert ev["abort"]["red_correct"] == len(seeds) and ev["abort"]["global_open"] == 0
    assert ev["P1"]["ok_seeds"] == sorted(seeds) and ev["systems"]["M3-B"]["red"]["n_seeds"] == len(seeds)
    assert ev["P5"]["M3-B"] == len(seeds) and ev["P4"]["latency_B"] == 20.0


def test_nine_hits_among_twenty_seeds_is_not_a_p2_verdict():
    seeds = list(range(400, 420))
    ev = evaluate([fake_result(s, red_ok=s < 409) for s in seeds], seeds)
    assert ev["P2"] == {"count": 9, "fulfilled": None} and ev["abort"]["triggered"] is None


def test_single_pilot_seed_gets_no_abort_verdict():
    ev = evaluate([fake_result(0)], [0])                              # früher: "Aufbau funktioniert nicht"
    assert ev["abort"] == {"red_correct": 1, "global_open": 0, "triggered": None}


def row(md, label):
    return next(ln for ln in md.splitlines() if ln.startswith(f"| {label}"))


def test_report_marks_explorative_evaluation_and_prints_no_verdicts():
    seeds = [0, 1]
    md = report_markdown(evaluate([fake_result(s, red_ok=s == 0) for s in seeds], seeds))
    assert md.splitlines()[0] == "## Auswertung"
    head = "\n".join(md.splitlines()[:5])                              # gut sichtbar, vor den Tabellen
    assert ("Explorative Auswertung (Seeds 0, 1) – keine Prüfung der vorregistrierten Vorhersagen; "
            "diese gilt nur für die Seeds 400–409.") in head
    for label in ("P2", "P3", "P4", "P5"):
        cells = [c.strip() for c in row(md, label).split("|")]
        assert cells[2] == "–" and "erfüllt" not in cells[2]
    assert "ausgelöst" not in md and "funktioniert nicht" not in md
    assert "1/2 Seeds" in row(md, "P2") and "Abbruchkriterium" in md   # Zahlen bleiben


def test_report_for_main_seeds_keeps_verdicts_and_abort_sentence():
    seeds = list(MAIN_SEEDS)
    md = report_markdown(evaluate([fake_result(s) for s in seeds], seeds))
    assert "Explorative" not in md and "vorregistriert" not in md
    assert "| erfüllt |" in row(md, "P2") and "Abbruchkriterium nicht ausgelöst." in md
    md = report_markdown(evaluate([fake_result(s, red_ok=s < 404) for s in seeds], seeds))
    assert "nicht erfüllt" in row(md, "P2") and "Abbruchkriterium ausgelöst:" in md


def test_main_marks_a_partial_evaluation_as_explorative(tmp_path, capsys):
    for s in (400, 401):
        (tmp_path / f"seed_{s}.json").write_text(json.dumps(fake_result(s)))
    main(["--results", str(tmp_path), "--seeds", "400-401"])
    out = capsys.readouterr().out
    assert "Explorative Auswertung (Seeds 400, 401)" in out and "ausgelöst" not in out


# --- Task 8: Auswertung v2 und Bestätigung ---

def test_confirmation_counts_and_need():
    # Kriterien je 5/4/4, aber nur 3 Seeds erfüllen alle drei zugleich: nicht bestätigt (Entscheidung D1, 04.10.2026)
    seeds = list(range(500, 505))
    rs = [fake_result(s, red_ok=s != 500, global_open=s == 501) for s in seeds]
    ev = evaluate_confirmation(rs, seeds)
    assert ev["need"] == 4 and ev["red_correct"] == {"count": 4, "fulfilled": True}
    assert ev["no_false_open"]["count"] == 4
    assert ev["joint"] == {"count": 3, "need": 4, "fulfilled": False} and not ev["confirmed"]


def test_confirmation_rejects_main_seeds_and_duplicates():
    with pytest.raises(ValueError): evaluate_confirmation([fake_result(400)], [400])
    with pytest.raises(ValueError): evaluate_confirmation([fake_result(500)], [500, 500])


def test_failed_premise_counts_against_confirmation():
    seeds = list(range(500, 505))
    ev = evaluate_confirmation([fake_result(s, ok=s > 501) for s in seeds], seeds)
    assert ev["premise"]["count"] == 3 and not ev["confirmed"]


def test_report_shows_practice_and_p1b():
    seeds = list(range(400, 410))
    md = report_markdown(evaluate([fake_result(s) for s in seeds], seeds))
    assert "Restanteil" in md and "Übungs-Ontologie" in md and "Nutzbarkeit" in md and "4,8" in md


def test_confirmation_result_has_exactly_the_contract_keys_and_n():
    seeds = list(range(500, 505))
    ev = evaluate_confirmation([fake_result(s) for s in seeds], seeds)
    assert {"n", "need", "premise", "no_false_open", "red_correct", "confirmed"} <= set(ev)
    assert ev["n"] == 5 and ev["premise"] == {"count": 5, "fulfilled": True}
    assert ev["no_false_open"] == {"count": 5, "fulfilled": True}


@pytest.mark.parametrize("n, need", [(5, 4), (6, 5), (7, 6), (10, 8), (15, 12)])
def test_confirmation_need_is_ceil_of_four_fifths(n, need):
    seeds = list(range(500, 500 + n))
    ev = evaluate_confirmation([fake_result(s) for s in seeds], seeds)
    assert ev["n"] == n and ev["need"] == need


def test_per_criterion_four_of_five_but_joint_three_is_not_confirmed():
    # Seed 500 verfehlt nur Kriterium 2, Seed 501 nur Kriterium 3: jedes Kriterium hat 4/5, aber nur 3 Seeds erfüllen
    # alle drei zugleich; entscheidend ist die gemeinsame Zählung (Entscheidung D1 des Nutzers, 04.10.2026)
    seeds = list(range(500, 505))
    rs = [fake_result(500, global_open=True), fake_result(501, red_ok=False)] + [fake_result(s) for s in (502, 503, 504)]
    ev = evaluate_confirmation(rs, seeds)
    assert (ev["premise"]["count"], ev["no_false_open"]["count"], ev["red_correct"]["count"]) == (5, 4, 4)
    assert ev["premise"]["fulfilled"] and ev["no_false_open"]["fulfilled"] and ev["red_correct"]["fulfilled"]
    assert ev["joint"] == {"count": 3, "need": 4, "fulfilled": False} and ev["confirmed"] is False
    assert [row["all"] for row in ev["per_seed"].values()] == [False, False, True, True, True]


def test_joint_four_of_five_is_confirmed():
    # ein einziger Seed verfehlt zwei Kriterien zugleich: 4/5 gemeinsam genügt
    seeds = list(range(500, 505))
    rs = [fake_result(500, global_open=True, red_ok=False)] + [fake_result(s) for s in (501, 502, 503, 504)]
    ev = evaluate_confirmation(rs, seeds)
    assert (ev["premise"]["count"], ev["no_false_open"]["count"], ev["red_correct"]["count"]) == (5, 4, 4)
    assert ev["joint"] == {"count": 4, "need": 4, "fulfilled": True} and ev["confirmed"] is True
    assert ev["per_seed"][500] == {"premise": True, "no_false_open": False, "red_correct": False, "all": False}
    assert all(ev["per_seed"][s]["all"] for s in (501, 502, 503, 504))


def test_confirmed_depends_on_the_joint_count_alone():
    # ein Kriterium unter 4 heißt auch gemeinsam unter 4; umgekehrt entscheidet nie ein Einzelkriterium
    seeds = list(range(500, 505))
    rs = [fake_result(500, global_open=True), fake_result(501, global_open=True)] + [fake_result(s) for s in (502, 503, 504)]
    ev = evaluate_confirmation(rs, seeds)
    assert (ev["premise"]["count"], ev["no_false_open"]["count"], ev["red_correct"]["count"]) == (5, 3, 5)
    assert ev["premise"]["fulfilled"] and ev["red_correct"]["fulfilled"] and not ev["no_false_open"]["fulfilled"]
    assert ev["joint"] == {"count": 3, "need": 4, "fulfilled": False} and not ev["confirmed"]
    all_ok = evaluate_confirmation([fake_result(s) for s in seeds], seeds)
    assert all_ok["joint"] == {"count": 5, "need": 4, "fulfilled": True} and all_ok["confirmed"]


def test_confirmation_criteria_two_and_three_look_only_at_m3b():
    seeds = list(range(500, 505))
    others = [n for n in SYSTEMS if n != "M3-B"]

    def counts(rs):
        ev = evaluate_confirmation(rs, seeds)
        return ev["no_false_open"]["count"], ev["red_correct"]["count"], ev["joint"]["count"]

    base = [fake_result(s, red_ok=s != 500, global_open=s == 501) for s in seeds]
    expected = counts(base)
    assert expected == (4, 4, 3)
    noisy = [fake_result(s, red_ok=s != 500, global_open=s == 501) for s in seeds]
    for r in noisy:
        for name in others:
            arm_red = C_SPECIAL if name.endswith("B") else A_RED
            for cond in ("none", "global"):
                sys_variant(r, name, cond, sysres(110, [(4, 120), (1, 130)]))          # andere öffnen fälschlich
            sys_variant(r, name, "red", sysres(110, [(arm_red, 120)]))                 # andere treffen in red
    assert counts(noisy) == expected
    quiet = [fake_result(s, red_ok=s != 500, global_open=s == 501) for s in seeds]
    for r in quiet:
        for name in others:
            sys_variant(r, name, "red", sysres(110, [(4, 120)]))                       # andere verfehlen red
    assert counts(quiet) == expected


def test_failed_premise_seed_is_not_fulfilled_for_criteria_two_and_three():
    seeds = list(range(500, 505))
    ev = evaluate_confirmation([fake_result(s, ok=s != 500) for s in seeds], seeds)
    assert ev["premise"]["count"] == 4 and ev["no_false_open"]["count"] == 4 and ev["red_correct"]["count"] == 4
    assert ev["joint"]["count"] == 4 and ev["confirmed"]         # 4 von 5 genügt
    ev = evaluate_confirmation([fake_result(s, ok=s > 501) for s in seeds], seeds)
    assert ev["no_false_open"]["count"] == 3 and ev["red_correct"]["count"] == 3
    # die Prämisse entscheidet, nicht das Vorhandensein von Bedingungen: ok=False mit sonst makellosen Strömen
    rs = [fake_result(s) for s in seeds]
    rs[0]["premise"]["ok"] = False
    ev = evaluate_confirmation(rs, seeds)
    assert (ev["premise"]["count"], ev["no_false_open"]["count"], ev["red_correct"]["count"]) == (4, 4, 4)


def test_confirmation_false_open_in_none_counts_and_practice_is_not_an_opening():
    seeds = list(range(500, 505))
    rs = [fake_result(s) for s in seeds]
    for r in rs[:2]:
        sys_variant(r, "M3-B", "none", sysres(150, [(4, 160)]))      # offen in none
    ev = evaluate_confirmation(rs, seeds)
    assert ev["no_false_open"] == {"count": 3, "fulfilled": False} and not ev["confirmed"]
    # Übungs-Ontologie steht in "practice", nicht in "opened": sie ist kein falsches Öffnen
    assert all(r["conditions"]["none"]["M3-B"]["practice"] == [] for r in rs[2:])
    rs = [{**fake_result(s), "practice": {**PRACTICE, "M3-B": [{"cand": 0, "name": "Farbe 0"}]}} for s in seeds]
    assert evaluate_confirmation(rs, seeds)["no_false_open"]["count"] == 5


def test_confirmation_red_correct_needs_an_opening_after_the_switch():
    seeds = list(range(500, 505))
    rs = [fake_result(s) for s in seeds]
    sys_variant(rs[0], "M3-B", "red", sysres(60, [(C_SPECIAL, 70)]))     # richtige Farbe, aber vor dem Wechsel
    sys_variant(rs[1], "M3-B", "red", sysres(110, [(4, 120)]))           # falsches Merkmal
    ev = evaluate_confirmation(rs, seeds)
    assert ev["red_correct"] == {"count": 3, "fulfilled": False}


def test_confirmation_ignores_other_conditions_for_false_opens():
    # walls ist kein Teil von Kriterium 2; red-Öffnungen anderer Merkmale schaden Kriterium 3 nicht, solange Farbe 0 kommt
    seeds = list(range(500, 505))
    rs = [fake_result(s) for s in seeds]
    for r in rs:
        sys_variant(r, "M3-B", "walls", sysres(120, [(4, 130)]))
        sys_variant(r, "M3-B", "red", sysres(110, [(4, 115), (C_SPECIAL, 120)]))
    ev = evaluate_confirmation(rs, seeds)
    assert ev["no_false_open"]["count"] == 5 and ev["red_correct"]["count"] == 5 and ev["confirmed"]


def test_confirmation_error_cases():
    five = list(range(500, 505))
    with pytest.raises(ValueError, match="400.*409|Hauptlauf") as exc:
        evaluate_confirmation([fake_result(s) for s in (405, *five)], [405, *five])
    assert "405" in str(exc.value) and "500" not in str(exc.value)
    with pytest.raises(ValueError, match="409"):                       # schon die Grenze zählt
        evaluate_confirmation([fake_result(409)], [409])
    with pytest.raises(ValueError, match="doppelt.*500"):
        evaluate_confirmation([fake_result(500)], [500, 500])
    with pytest.raises(ValueError, match="504"):                       # fehlendes Ergebnis
        evaluate_confirmation([fake_result(s) for s in five[:4]], five)
    with pytest.raises(ValueError, match="Ergebnis.*500"):             # zwei Ergebnisse für einen Seed
        evaluate_confirmation([fake_result(500)] + [fake_result(s) for s in five], five)
    with pytest.raises(ValueError, match="Konfiguration.*501"):
        evaluate_confirmation([fake_result(500), {**fake_result(501), "config": {"switch_episode": 50,
                                                                                  "n_deploy_episodes": 400}}]
                              + [fake_result(s) for s in five[2:]], five)
    with pytest.raises(ValueError):                                    # ohne Seeds gäbe es "bestätigt" aus nichts
        evaluate_confirmation([], [])


@pytest.mark.parametrize("seeds, named", [([0, 500, 501, 502, 503], "[0]"), ([499, 500, 501, 502, 503], "[499]"),
                                          (list(range(410, 415)), "[410, 411, 412, 413, 414]"),
                                          ([1, 2, 500, 501, 502], "[1, 2]")])
def test_confirmation_needs_seeds_from_500_and_names_the_others(seeds, named):
    with pytest.raises(ValueError, match="500") as exc:
        evaluate_confirmation([fake_result(s) for s in seeds], seeds)
    assert named in str(exc.value)


@pytest.mark.parametrize("n", [1, 2, 4])
def test_confirmation_needs_at_least_five_seeds(n):
    seeds = list(range(500, 500 + n))
    with pytest.raises(ValueError, match="mindestens 5 Seeds") as exc:
        evaluate_confirmation([fake_result(s) for s in seeds], seeds)
    assert f"{n}" in str(exc.value)


def test_main_confirm_refuses_small_or_low_seed_sets_before_loading(tmp_path, capsys):
    for args in (["--seeds", "0"], ["--seeds", "500-503"], ["--seeds", "495-499"]):
        with pytest.raises(ValueError, match="500|mindestens 5"):         # kein FileNotFoundError: es gibt keine Dateien
            main(["--results", str(tmp_path), *args, "--confirm"])
    assert capsys.readouterr().out == ""
    for s in range(500, 504):
        (tmp_path / f"seed_{s}.json").write_text(json.dumps(fake_result(s)))
    main(["--results", str(tmp_path), "--seeds", "500-503"])          # ohne --confirm bleibt die Auswertung erlaubt
    assert "Bestätigung" not in capsys.readouterr().out


def criteria_rows(md):
    lines = md.splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith("| Kriterium |"))
    rows = []
    for ln in lines[start + 2:]:
        if not ln.startswith("|"):
            break
        rows.append([c.strip() for c in ln.strip("|").split("|")])
    return rows


def test_confirmation_markdown_leads_with_the_joint_row_and_marks_the_others_as_information():
    seeds = list(range(500, 505))
    md = confirmation_markdown(evaluate_confirmation(
        [fake_result(s, red_ok=s != 500, global_open=s == 501) for s in seeds], seeds))
    assert md.splitlines()[0] == "## Bestätigung (Spec v2 §8)"
    joint, *crit = criteria_rows(md)
    assert "alle drei" in joint[0].lower() and "entscheidend" in joint[0]
    assert joint[1:] == ["3/5", "≥ 4", "nicht erfüllt"]                  # 5/4/4 je Kriterium, gemeinsam nur 3
    assert [c[0][0] for c in crit] == ["1", "2", "3"] and all("zur Information" in c[0] for c in crit)
    assert "Prämissen" in crit[0][0] and "`none`" in crit[1][0] and "`global`" in crit[1][0] and "`red`" in crit[2][0]
    assert [c[1] for c in crit] == ["5/5", "4/5", "4/5"]
    assert all("erfüllt" not in cell for c in crit for cell in c[1:])     # kein Urteil aus einem Einzelkriterium
    assert "gleichzeitig" in md and "Nicht bestätigt" in md
    assert md.rstrip().endswith("eine weitere Runde läuft nur auf neuen Seeds.")
    assert "| 500 | ja | ja | nein | nein |" in md and "| 501 | ja | nein | ja | nein |" in md   # welche Seeds fehlen
    assert "| 502 | ja | ja | ja | ja |" in md
    md = confirmation_markdown(evaluate_confirmation([fake_result(s) for s in seeds], seeds))
    assert criteria_rows(md)[0][1:] == ["5/5", "≥ 4", "erfüllt"] and md.rstrip().endswith("Bestätigt.")
    md = confirmation_markdown(evaluate_confirmation([fake_result(s, ok=s > 501) for s in seeds], seeds))
    assert criteria_rows(md)[0][1:] == ["3/5", "≥ 4", "nicht erfüllt"]
    assert "| 500 | nein | nein | nein | nein |" in md and "Nicht bestätigt" in md


def test_main_confirm_appends_section(tmp_path, capsys):
    for s in range(500, 505):
        (tmp_path / f"seed_{s}.json").write_text(json.dumps(fake_result(s)))
    main(["--results", str(tmp_path), "--seeds", "500-504"])
    assert "Bestätigung" not in capsys.readouterr().out
    main(["--results", str(tmp_path), "--seeds", "500-504", "--confirm"])
    out = capsys.readouterr().out
    assert out.index("## Auswertung") < out.index("## Bestätigung (Spec v2 §8)")
    assert "Explorative Auswertung (Seeds 500, 501, 502, 503, 504)" in out


def test_main_confirm_refuses_main_seeds_with_clear_error(tmp_path, capsys):
    # auch ohne Ergebnisdateien: der Fehler über die Seeds kommt zuerst, nicht FileNotFoundError
    with pytest.raises(ValueError, match="Hauptlauf") as exc:
        main(["--results", str(tmp_path), "--seeds", "400-409", "--confirm"])
    assert "400" in str(exc.value) and capsys.readouterr().out == ""
    for s in (409, 500):
        (tmp_path / f"seed_{s}.json").write_text(json.dumps(fake_result(s)))
    with pytest.raises(ValueError, match="409"):
        main(["--results", str(tmp_path), "--seeds", "409,500", "--confirm"])
    main(["--results", str(tmp_path), "--seeds", "409,500"])         # ohne --confirm bleibt die Auswertung erlaubt


# --- Bericht: Seedwerte, Nutzbarkeit, Fehlalarmrate, alte Ergebnisse ---

def seed_table(md):
    lines = md.splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith("| Seed |"))
    rows = []
    for ln in lines[start + 2:]:
        if not ln.startswith("|"):
            break
        rows.append([c.strip() for c in ln.strip("|").split("|")])
    header = [c.strip() for c in lines[start].strip("|").split("|")]
    return header, rows


def test_usability_is_gain_of_first_correct_opening_under_red():
    m = stream_metrics(sysres(110, [(4, 115, 0.9), (C_SPECIAL, 130, 0.07), (C_SPECIAL, 120, 0.04)]),
                       "red", "B", 100, 300)
    assert m["usability"] == 0.04                                   # früheste richtige Öffnung, nicht die erste der Liste
    assert stream_metrics(sysres(110, [(C_SPECIAL, 90, 0.5), (C_SPECIAL, 120, 0.06)]), "red", "B", 100, 300)["usability"] == 0.06
    assert stream_metrics(sysres(110, [(4, 120, 0.3)]), "red", "B", 100, 300)["usability"] is None
    assert stream_metrics(sysres(110, [(C_SPECIAL, 90, 0.5)]), "red", "B", 100, 300)["usability"] is None
    assert stream_metrics(sysres(110, [(C_SPECIAL, 120, 0.5)]), "global", "B", 100, 300)["usability"] is None
    assert stream_metrics(sysres(110, [(C_SPECIAL, 120)]), "red", "B", 100, 300)["usability"] is None     # kein gain (S1, alt)


def test_evaluate_carries_per_seed_values():
    seeds = [500, 501, 502]
    rs = [fake_result(500, gain=0.0123), fake_result(501, red_ok=False), fake_result(502, ok=False)]
    ev = evaluate(rs, seeds)
    assert [row["seed"] for row in ev["seeds"]] == seeds
    first = ev["seeds"][0]
    assert first["premise_ok"] is True and first["color_invariance"] == 0.99 and first["restanteil"] == 0.05
    assert first["shift"] == 0.1 and first["delta"] == {"M3-B": 0.002, "M3-A": 0.003}
    assert first["practice"]["M3-B"] == ["Wand"] and first["practice"]["S1-A"] == ["bit3&a0", "bit2&a1"]
    assert [row["usability"] for row in ev["seeds"]] == [{"M3-B": 0.0123, "M3-A": None}, {"M3-B": None, "M3-A": None},
                                                        None]                      # gescheiterte Prämisse: keine Bedingungen
    assert ev["seeds"][2]["premise_ok"] is False and ev["seeds"][2]["practice"] == first["practice"]   # steht oben im Ergebnis
    assert ev["n_null_streams"] == 20


def test_report_per_seed_table_values():
    seeds = [500, 501, 502]
    rs = [fake_result(500, gain=0.0123), fake_result(501, red_ok=False), fake_result(502, ok=False)]
    header, rows = seed_table(report_markdown(evaluate(rs, seeds)))
    assert header[0] == "Seed" and "Farbinvarianz" in header and "Restanteil" in header and "Verschiebung" in header
    assert [h for h in header if h.startswith("Übungs-Ontologie")] == [f"Übungs-Ontologie {n}" for n in SYSTEMS]
    assert "δ M3-B" in header and "δ M3-A" in header
    assert [h for h in header if h.startswith("Nutzbarkeit")] == ["Nutzbarkeit M3-B", "Nutzbarkeit M3-A"]
    col = {h: i for i, h in enumerate(header)}
    assert rows[0][col["Seed"]] == "500" and rows[0][col["Prämisse"]] == "erfüllt"
    assert rows[0][col["Farbinvarianz"]] == "0.990" and rows[0][col["Restanteil"]] == "0.050"
    assert rows[0][col["Verschiebung"]] == "0.100"
    assert rows[0][col["Übungs-Ontologie M3-B"]] == "Wand" and rows[0][col["Übungs-Ontologie S1-A"]] == "bit3&a0, bit2&a1"
    assert rows[0][col["Übungs-Ontologie M3-A"]] == "keine"           # leer ist nicht "unbekannt"
    assert rows[0][col["δ M3-B"]] == "0.0020" and rows[0][col["δ M3-A"]] == "0.0030"
    assert rows[0][col["Nutzbarkeit M3-B"]] == "0.0123" and rows[0][col["Nutzbarkeit M3-A"]] == "–"
    assert rows[1][col["Nutzbarkeit M3-B"]] == "–"                  # M3-B hat in red nichts geöffnet
    assert rows[2][col["Prämisse"]] == "nicht erfüllt" and rows[2][col["Nutzbarkeit M3-B"]] == "–"


def test_usability_is_reported_for_both_m3_systems():
    # Spec §6 "je Seed und System": auch M3-A, Gewinn der ersten richtigen Öffnung (Farbe-0-Bit in Aktionsrichtung)
    seeds = [500, 501]
    rs = [fake_result(500, gain=0.0123), fake_result(501, gain=0.02)]
    a_wrong = 1 * 298 + obs_index(CH_COLOR[C_SPECIAL], -1, 0)            # Farbe-0-Bit oben, aber Aktion unten
    sys_variant(rs[0], "M3-A", "red", sysres(110, [(a_wrong, 115, 0.9), (A_RED, 140, 0.031), (A_RED, 130, 0.027)]))
    sys_variant(rs[1], "M3-A", "red", sysres(110, [(A_RED, 90, 0.5)]))        # nur vor dem Wechsel: keine Nutzbarkeit
    ev = evaluate(rs, seeds)
    assert [row["usability"] for row in ev["seeds"]] == [{"M3-B": 0.0123, "M3-A": 0.027}, {"M3-B": 0.02, "M3-A": None}]
    header, rows = seed_table(report_markdown(ev))
    col = {h: i for i, h in enumerate(header)}
    assert [rows[i][col["Nutzbarkeit M3-A"]] for i in (0, 1)] == ["0.0270", "–"]
    assert [rows[i][col["Nutzbarkeit M3-B"]] for i in (0, 1)] == ["0.0123", "0.0200"]


def legacy_result(seed, **kw):
    """Ergebnis im v1-Format: ohne practice, delta, gain, restanteil, shift und n_null_streams."""
    r = fake_result(seed, **kw)
    for key in ("practice", "delta"):
        del r[key]
    for key in ("restanteil", "shift"):
        del r["premise"][key]
    del r["config"]["n_null_streams"]
    for conds in (r["conditions"] or {}).values():
        for sr in conds.values():
            del sr["practice"], sr["delta"]
            for o in sr["opened"]:
                del o["gain"]
    return r


def test_old_results_without_v2_keys_show_dashes_and_do_not_crash():
    seeds = list(range(400, 410))
    md = report_markdown(evaluate([legacy_result(s, ok=s != 409) for s in seeds], seeds))
    header, rows = seed_table(md)
    col = {h: i for i, h in enumerate(header)}
    assert len(rows) == 10
    for k in ("Restanteil", "Verschiebung", "δ M3-B", "δ M3-A", "Nutzbarkeit M3-B", "Nutzbarkeit M3-A") + tuple(f"Übungs-Ontologie {n}" for n in SYSTEMS):
        assert {r[col[k]] for r in rows} == {"–"}, k
    assert rows[0][col["Farbinvarianz"]] == "0.990"                 # was es gab, bleibt sichtbar
    assert "Fehlalarmrate" in md and "4,8" not in md                # Anzahl der Null-Ströme unbekannt


def test_null_values_in_json_premise_show_dashes():            # nicht endlicher Restanteil steht als null im JSON
    r = fake_result(500)
    r["premise"].update(restanteil=None, shift=None, ok=False)
    r["conditions"] = None
    header, rows = seed_table(report_markdown(evaluate([r], [500])))
    col = {h: i for i, h in enumerate(header)}
    assert rows[0][col["Restanteil"]] == "–" and rows[0][col["Verschiebung"]] == "–"


def test_expected_false_alarm_rate_line():
    def line(n_null, **cfg):
        rs = [fake_result(s) for s in (500, 501)]
        for r in rs:
            r["config"].update(n_null_streams=n_null, **cfg)
        md = report_markdown(evaluate(rs, [500, 501]))
        return next(ln for ln in md.splitlines() if "Fehlalarmrate" in ln)
    assert "1/21" in line(20) and "4,8 %" in line(20)
    assert "1/10" in line(9) and "10,0 %" in line(9)
    assert "." not in line(20).split("≈")[-1].split("%")[0]            # deutsches Komma
    # v1-Ergebnisse (max_null_alarms = 1) hatten eine doppelt so hohe Rate: (k + 1)/(n + 1)
    assert "2/21" in line(20, max_null_alarms=1) and "9,5 %" in line(20, max_null_alarms=1)


def test_empty_practice_ontology_is_shown_as_none_not_as_missing():
    r = fake_result(500)
    r["practice"] = {n: [] for n in SYSTEMS}
    header, rows = seed_table(report_markdown(evaluate([r], [500])))
    assert [c for h, c in zip(header, rows[0]) if h.startswith("Übungs-Ontologie")] == ["keine"] * len(SYSTEMS)
