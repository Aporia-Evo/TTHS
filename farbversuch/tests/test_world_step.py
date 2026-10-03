import numpy as np

from farbversuch.tests.helpers import open_map
from farbversuch.world import C_SPECIAL, DISP, make_map, observe, rollout, step


def run_steps(m, pos, a, n, **kw):
    rng = np.random.default_rng(0)
    return [step(m, pos, a, rng, **kw) for _ in range(n)]


def test_slip_rate():
    out = run_steps(open_map(), (4, 4), 0, 20000, p_slip=0.10, red_active=False)
    assert abs(np.mean([c != 1 for _, c in out]) - 0.075) < 0.006


def test_wall_blocks():
    assert all(r == ((1, 4), 0) for r in run_steps(open_map(), (1, 4), 0, 50, p_slip=0.0, red_active=False))


def test_red_effect_only_when_active():
    m = open_map(colour=C_SPECIAL)
    assert all(c == 1 for _, c in run_steps(m, (6, 4), 0, 4000, p_slip=0.0, red_active=False))
    on = run_steps(m, (6, 4), 0, 4000, p_slip=0.0, red_active=True)
    assert abs(np.mean([c == 5 for _, c in on]) - 0.5) < 0.03


def test_red_needs_special_colour():
    assert all(c == 1 for _, c in run_steps(open_map(colour=1), (6, 4), 0, 500, p_slip=0.0, red_active=True))


def test_double_step_only_if_next_free():
    out = run_steps(open_map(colour=C_SPECIAL), (2, 4), 0, 500, p_slip=0.0, red_active=True)
    assert all(r == ((1, 4), 1) for r in out)


def test_disp_class_matches_movement():
    m, rng = make_map(np.random.default_rng(4), 0.15), np.random.default_rng(5)
    pos = m.start
    for _ in range(2000):
        new, c = step(m, pos, int(rng.integers(4)), rng, p_slip=0.3, red_active=True)
        assert (new[0] - pos[0], new[1] - pos[1]) == DISP[c]
        pos = m.start if new == m.goal else new


def test_step_draws_exactly_three_numbers():
    r1, r2 = np.random.default_rng(8), np.random.default_rng(8)
    step(open_map(), (4, 4), 0, r1, p_slip=0.1, red_active=True)
    r2.random(); r2.integers(4); r2.random()
    assert r1.random() == r2.random()


def test_red_slide_onto_and_past_goal():        # Review Focus 3
    t = rollout(open_map(colour=C_SPECIAL, goal=(2, 4)), lambda o, p: 0, np.random.default_rng(0), 0.0, True, red_p=1.0)
    assert t.reached and len(t.actions) == 1 and t.disps[0] == 5
    m2 = open_map(colour=C_SPECIAL, goal=(3, 4))
    assert step(m2, (4, 4), 0, np.random.default_rng(0), 0.0, True, red_p=1.0) == ((2, 4), 5)


def test_rollout_caps_at_max_steps():
    t = rollout(open_map(start=(1, 4), goal=(7, 7)), lambda o, p: 0, np.random.default_rng(0), 0.0, False)
    assert len(t.actions) == 40 and not t.reached


def test_rollout_records_pre_step_obs():
    m = make_map(np.random.default_rng(6), 0.15)
    t = rollout(m, lambda o, p: 1, np.random.default_rng(0), 0.1, False)
    assert (t.obs[0] == observe(m, m.start)).all() and tuple(t.positions[0]) == m.start


def test_rollout_records_the_chosen_action_not_the_executed_one():
    runs = [rollout(make_map(np.random.default_rng(e), 0.15), lambda o, p: 1, np.random.default_rng(100 + e),
                    0.5, False) for e in range(5)]
    actions, disps = (np.concatenate([getattr(t, k) for t in runs]) for k in ("actions", "disps"))
    assert (actions == 1).all()                      # Aktion 1 = unten, immer gewählt und gespeichert
    assert (disps != 2).any() and {1, 3, 4} & set(disps.tolist())    # ausgeführt wurde teils eine andere Richtung
