import dataclasses
import json
import os
import platform

import numpy as np
import pytest

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


def test_parse_seeds():
    assert parse_seeds("400-402") == [400, 401, 402] and parse_seeds("0") == [0] and parse_seeds("1,5") == [1, 5]


def test_parse_seeds_mixed_and_invalid():
    assert parse_seeds("1-2,7") == [1, 2, 7]
    with pytest.raises(ValueError):
        parse_seeds("5-3")


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
    assert set(a) == {"p_global", "red_surprise", "bracketed", "evals"}
    assert type(a["p_global"]) is float and type(a["red_surprise"]) is float
    assert type(a["bracketed"]) is bool and type(a["evals"]) is int
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
    assert set(r["p_global"]) == {"p_global", "red_surprise", "bracketed", "evals"}
    assert 0 < r["phase1_sec"] <= r["total_sec"]


@pytest.mark.slow
def test_premise_failure_stops_seed():
    r = run_seed(0, dataclasses.replace(TINY, min_invariance=1.01))
    assert r["premise"]["ok"] is False and r["conditions"] is None and r["p_global"] is None


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
