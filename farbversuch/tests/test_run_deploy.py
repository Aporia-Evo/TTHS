import dataclasses
import json
import os
import platform
import re
from types import SimpleNamespace

import numpy as np
import pytest

import farbversuch.run as run
from farbversuch.run import (CONDITIONS, THREAD_VARS, bisect_to_target, deploy, env_block, find_p_global, main,
                             parse_seeds, run_seed, stream_episodes)
from farbversuch.tests.helpers import TINY


def test_bisect_hits_target():
    p, ok, _ = bisect_to_target(lambda p: p * p, .25, .1, 1., .02, 30)
    assert ok and abs(p * p - .25) <= .005


def test_bisect_unbracketed():                   # Review Focus 5
    p, ok, n = bisect_to_target(lambda p: p, 5., .1, 1., .02, 30)
    assert (p, ok) == (1., False) and n <= 2


def test_bisect_target_below_range():
    p, ok, n = bisect_to_target(lambda p: p, .01, .1, 1., .02, 30)
    assert (p, ok) == (.1, False) and n == 2


def test_bisect_max_iter_reached():
    calls = []
    def f(p):
        calls.append(p)
        return p * p
    p, ok, n = bisect_to_target(f, .25, .1, 1., 1e-12, 4)
    assert not ok and n == len(calls) == 2 + 4 and .1 < p < 1.


def test_bisect_fallback_is_the_closest_evaluated_point_including_both_ends():
    # Treppenfunktionen: keine Mitte trifft, der Rand mit dem kleinsten Abstand gewinnt
    p, hit, n = bisect_to_target(lambda p: 0. if p < 1. else 1.4, 1., 0., 1., 1e-9, 3)
    assert (p, hit, n) == (1., False, 5)
    p, hit, n = bisect_to_target(lambda p: .9 if p == 0. else 5., 1., 0., 1., 1e-9, 3)
    assert (p, hit, n) == (0., False, 5)


def _fake_p1(curve, red):
    """Phase1-Attrappe: Die Überraschung hängt nur von p_slip (curve) und red_active (red) ab."""
    def surprise(Z, A, D):
        return np.where(Z[:, 1] > 0, red, curve(Z[:, 0]))
    return SimpleNamespace(routine=SimpleNamespace(encode=lambda X: X), forward=SimpleNamespace(surprise=surprise))


@pytest.mark.parametrize("curve, red, changes, expected", [
    (lambda p: p, .5, {}, dict(hit=True, bracketed=True)),                                  # Mitte getroffen
    (lambda p: p, 1., {}, dict(hit=True, bracketed=True, p_global=1.)),                     # oberer Rand getroffen
    (lambda p: p, .1, {}, dict(hit=True, bracketed=True, p_global=.1)),                     # unterer Rand getroffen
    (lambda p: p, 5., {}, dict(hit=False, bracketed=False, p_global=1., evals=1)),          # Ziel oberhalb von f(1)
    (lambda p: p, .01, {}, dict(hit=False, bracketed=False, p_global=.1, evals=2)),         # Ziel unterhalb von f(0,1)
    (lambda p: p, .3, dict(pglobal_tol=1e-9, pglobal_max_iter=3),
     dict(hit=False, bracketed=True, evals=5)),                                             # max_iter erschöpft
    (lambda p: np.where(p < 1., 0., 1.4), 1., dict(pglobal_tol=1e-9, pglobal_max_iter=3),
     dict(hit=False, bracketed=True, p_global=1.)),                                         # Rückfall: oberer Rand
])
def test_find_p_global_reports_hit_and_bracketed_separately(monkeypatch, curve, red, changes, expected):
    def fake_rollouts(routine, seed, tag, n_episodes, cfg, *, p_slip, red_active=False, stream=0):
        traj = SimpleNamespace(obs=np.array([[p_slip, float(red_active)]]), actions=np.array([0]),
                               disps=np.array([0]))
        return [(None, traj)]
    monkeypatch.setattr(run, "routine_rollouts", fake_rollouts)
    r = find_p_global(0, dataclasses.replace(TINY, **changes), _fake_p1(curve, red))
    assert set(r) == {"p_global", "red_surprise", "hit", "bracketed", "evals"}
    assert type(r["hit"]) is bool and type(r["bracketed"]) is bool and r["red_surprise"] == red
    assert {k: r[k] for k in expected} == expected
    assert json.loads(json.dumps(r)) == r


def test_parse_seeds():
    assert parse_seeds("400-402") == [400, 401, 402] and parse_seeds("0") == [0] and parse_seeds("1,5") == [1, 5]


def test_parse_seeds_mixed_and_invalid():
    assert parse_seeds("1-2,7") == [1, 2, 7]
    with pytest.raises(ValueError):
        parse_seeds("5-3")


@pytest.mark.parametrize("spec, dup", [("1,1", "[1]"), ("1-3,2", "[2]"), ("400-402,401,402", "[401, 402]"),
                                       ("7,3,7,3", "[3, 7]")])
def test_parse_seeds_rejects_duplicates_and_names_them(spec, dup):
    with pytest.raises(ValueError, match="doppelte Seeds") as exc:
        parse_seeds(spec)
    assert dup in str(exc.value)


def test_parse_seeds_unique_mixed_specs_still_work():
    assert parse_seeds("3,1-2") == [3, 1, 2] and parse_seeds("1-2,4-5") == [1, 2, 4, 5]


def test_cli_rejects_duplicate_seeds_before_running_anything(tmp_path, monkeypatch):
    monkeypatch.setattr(run.multiprocessing, "get_context", lambda *a: pytest.fail("kein Worker darf starten"))
    with pytest.raises(ValueError, match="doppelte Seeds.*1"):
        main(["--seeds", "1,1", "--out", str(tmp_path / "o")])
    assert not list((tmp_path / "o").glob("*"))


def test_worker_temp_file_name_includes_the_process_id(tmp_path, monkeypatch):
    seen = []
    real_replace = os.replace
    monkeypatch.setattr(run, "run_seed", lambda seed, cfg: {"seed": seed})
    monkeypatch.setattr(os, "replace", lambda src, dst: (seen.append(os.path.basename(src)), real_replace(src, dst)))
    for pid in (1111, 2222):                      # zwei Prozesse mit demselben Seed kollidieren nicht auf einer Datei
        monkeypatch.setattr(os, "getpid", lambda pid=pid: pid)
        assert run._run_and_write((5, TINY, str(tmp_path))) == 5
    assert seen == ["seed_5.json.1111.tmp", "seed_5.json.2222.tmp"]
    assert sorted(x.name for x in tmp_path.iterdir()) == ["seed_5.json"]          # nichts bleibt liegen
    assert json.loads((tmp_path / "seed_5.json").read_text()) == {"seed": 5}


@pytest.mark.slow
def test_streams_share_maps_before_switch(tiny_phase1):
    s = {c: list(stream_episodes(0, TINY, tiny_phase1, .4, c)) for c in ("none", "red")}
    sw = TINY.switch_episode
    assert all(np.array_equal(a.positions, b.positions) for a, b in zip(s["none"][:sw], s["red"][:sw]))
    assert any((t.disps >= 5).any() for t in s["red"][sw:]) and not any((t.disps >= 5).any() for t in s["none"])


@pytest.mark.slow
def test_find_p_global_plain_and_reproducible(tiny_phase1):
    a = find_p_global(0, TINY, tiny_phase1)
    assert a == find_p_global(0, TINY, tiny_phase1)
    assert set(a) == {"p_global", "red_surprise", "hit", "bracketed", "evals"}
    assert type(a["p_global"]) is float and type(a["red_surprise"]) is float
    assert type(a["hit"]) is bool and type(a["bracketed"]) is bool and type(a["evals"]) is int
    assert TINY.p_slip <= a["p_global"] <= 1. and 2 <= a["evals"] <= 2 + TINY.pglobal_max_iter
    assert json.loads(json.dumps(a)) == a


@pytest.mark.slow
def test_deploy_reproducible_and_complete(tiny_phase1):
    def strip(r):                                # Wandzeiten dürfen abweichen
        return {k: {kk: vv for kk, vv in v.items() if not kk.endswith("_sec")} for k, v in r.items()}
    a = deploy(0, TINY, tiny_phase1, .4, "global")
    assert set(a) == set(TINY.systems)
    assert strip(a) == strip(deploy(0, TINY, tiny_phase1, .4, "global"))


def test_env_block_is_plain_and_reflects_the_environment(monkeypatch):
    monkeypatch.setenv("OMP_NUM_THREADS", "1")
    monkeypatch.setenv("OPENBLAS_NUM_THREADS", "3")
    monkeypatch.delenv("MKL_NUM_THREADS", raising=False)
    env = env_block()
    assert set(env) == {*THREAD_VARS, "numpy", "blas", "python"}
    assert (env["OMP_NUM_THREADS"], env["OPENBLAS_NUM_THREADS"], env["MKL_NUM_THREADS"]) == ("1", "3", None)
    assert env["numpy"] == np.__version__ and env["python"] == platform.python_version()
    assert env["blas"] is None or (type(env["blas"]) is str and env["blas"])
    assert json.loads(json.dumps(env)) == env


@pytest.mark.slow
def test_run_seed_schema():
    r = run_seed(0, TINY)
    assert set(r["conditions"]) == set(CONDITIONS) and set(r["conditions"]["red"]) == set(TINY.systems)
    assert set(r["env"]) == {*THREAD_VARS, "numpy", "blas", "python"}
    assert json.loads(json.dumps(r)) == r


@pytest.mark.slow
def test_run_seed_content():
    r = run_seed(0, TINY)
    assert list(r) == ["seed", "config", "env", "premise", "calibration", "p_global", "conditions", "phase1_sec",
                       "total_sec"]
    assert r["seed"] == 0 and r["config"] == TINY.as_dict() and r["premise"]["ok"] is True
    assert set(r["calibration"]) == {"m3_threshold", "cusum_k", "cusum_h"}
    assert set(r["p_global"]) == {"p_global", "red_surprise", "hit", "bracketed", "evals"}
    assert 0 < r["phase1_sec"] <= r["total_sec"]


@pytest.mark.slow
def test_premise_failure_stops_seed(capsys):
    r = run_seed(0, dataclasses.replace(TINY, min_invariance=1.01))
    assert r["premise"]["ok"] is False and r["conditions"] is None and r["p_global"] is None
    lines = capsys.readouterr().err.splitlines()
    assert len(lines) == 2 and "Prämisse nicht erfüllt" in lines[1]          # keine Bedingungszeilen


@pytest.mark.slow
def test_run_seed_logs_progress_to_stderr(capsys):
    r = run_seed(3, TINY)
    cap = capsys.readouterr()
    lines = cap.err.splitlines()
    assert cap.out == "" and all(re.match(r"\d\d:\d\d:\d\d seed 3 ", ln) for ln in lines)
    assert len(lines) == 2 + len(CONDITIONS)
    assert "gestartet" in lines[0]
    assert "Phase 1 fertig" in lines[1] and "Prämisse ok" in lines[1]
    for cond, ln in zip(CONDITIONS, lines[2:]):
        assert re.search(rf"Bedingung {cond} fertig \(\d+ s", ln)
    assert set(r["conditions"]) == set(CONDITIONS)                            # Ergebnis unverändert


@pytest.mark.slow
def test_cli_writes_and_skips(tmp_path):
    cfg = tmp_path / "c.json"; TINY.to_json(cfg)
    args = ["--config", str(cfg), "--seeds", "0", "--out", str(tmp_path / "o")]
    main(args); f = tmp_path / "o" / "seed_0.json"; t = f.stat().st_mtime_ns
    main(args); assert f.stat().st_mtime_ns == t


def _seed_file(out, seed, config):
    out.mkdir(exist_ok=True)
    f = out / f"seed_{seed}.json"
    f.write_text(json.dumps({"seed": seed, "config": config}))
    return f, (f.read_bytes(), f.stat().st_mtime_ns)


@pytest.mark.parametrize("config", [{**TINY.as_dict(), "k": 99}, None])      # andere Konfiguration / keine
def test_resume_refuses_foreign_config_and_leaves_the_file_alone(tmp_path, config):
    f, before = _seed_file(tmp_path / "o", 0, config)
    cfg = tmp_path / "c.json"; TINY.to_json(cfg)
    with pytest.raises(SystemExit, match="seed_0.json"):
        main(["--config", str(cfg), "--seeds", "0-1", "--out", str(tmp_path / "o")])
    assert (f.read_bytes(), f.stat().st_mtime_ns) == before
    assert sorted(x.name for x in (tmp_path / "o").iterdir()) == ["seed_0.json"]     # Seed 1 wurde nicht gestartet


def test_resume_skips_matching_seed_with_a_message(tmp_path, capsys):
    f, before = _seed_file(tmp_path / "o", 0, TINY.as_dict())
    cfg = tmp_path / "c.json"; TINY.to_json(cfg)
    main(["--config", str(cfg), "--seeds", "0", "--out", str(tmp_path / "o")])
    cap = capsys.readouterr()
    assert "seed 0 übersprungen (vorhanden)" in cap.err and "seed 0" not in cap.out
    assert (f.read_bytes(), f.stat().st_mtime_ns) == before


@pytest.mark.slow
def test_cli_pins_blas_threads_even_with_one_job(tmp_path, monkeypatch):
    for k in THREAD_VARS:
        monkeypatch.setenv(k, "8")               # monkeypatch stellt nach dem Test wieder her
    cfg = tmp_path / "c.json"; TINY.to_json(cfg)
    main(["--config", str(cfg), "--seeds", "0", "--out", str(tmp_path / "o")])
    r = json.loads((tmp_path / "o" / "seed_0.json").read_text())
    assert [os.environ[k] for k in THREAD_VARS] == ["1"] * 3
    assert [r["env"][k] for k in THREAD_VARS] == ["1"] * 3          # so gesehen im Worker


@pytest.mark.slow
def test_cli_parallel_matches_serial(tmp_path, monkeypatch):
    for k in THREAD_VARS:
        monkeypatch.setenv(k, "8")
    cfg = tmp_path / "c.json"; TINY.to_json(cfg)
    base = ["--config", str(cfg)]
    main([*base, "--seeds", "0-1", "--out", str(tmp_path / "par"), "--jobs", "2"])
    assert (tmp_path / "par" / "seed_0.json").exists()
    main([*base, "--seeds", "1", "--out", str(tmp_path / "ser")])    # --jobs 1: ebenfalls im festgelegten Worker

    def strip(x):
        return {k: strip(v) for k, v in x.items() if not k.endswith("_sec")} if isinstance(x, dict) else x
    par, ser = (json.loads((tmp_path / d / "seed_1.json").read_text()) for d in ("par", "ser"))
    assert strip(par) == strip(ser)
