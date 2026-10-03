import numpy as np

from farbversuch.monitor import holm_select, perm_pvalues, s1_explain


def test_perm_pvalue_extremes():
    rng = np.random.default_rng(0); f = (rng.random(400) < 0.3).astype(np.uint8)
    S = 1. + 3. * f + rng.normal(0, 0.1, 400)
    diff, p = perm_pvalues(S, np.stack([f, np.ones(400, np.uint8)], 1), np.random.default_rng(1))
    assert p[0] == 1 / 1001 and diff[0] > 2.5 and p[1] == 1. and diff[1] == 0.


def test_holm_stepdown():
    assert holm_select(np.array([.001, .02, .012, .5]), np.zeros(4)) == [0, 2, 1]
    assert holm_select(np.array([.03, .03]), np.zeros(2)) == []
    assert holm_select(np.array([.001, .001]), np.array([1., 2.])) == [1, 0]


def test_s1_respects_cap_and_opened():
    rng = np.random.default_rng(0); F = (rng.random((400, 5)) < 0.3).astype(np.uint8)
    S = 1. + F[:, :4] @ np.array([3., 3., 5., 3.]) + rng.normal(0, 0.1, 400)
    assert s1_explain(S, F, [0, 1], np.random.default_rng(1)) == [2]


def test_s1_arm_a_cannot_reject():              # Folge der Spec: 0,05/1192 < 1/1001
    rng = np.random.default_rng(0); F = (rng.random((300, 1192)) < 0.3).astype(np.uint8)
    S = 1. + 3. * F[:, 5] + rng.normal(0, 0.1, 300)
    assert s1_explain(S, F, [], np.random.default_rng(1)) == []


def test_perm_pvalues_match_naive_loop():
    rng = np.random.default_rng(3); F = (rng.random((60, 4)) < 0.4).astype(np.uint8); F[:, 3] = 0
    S = rng.normal(size=60) + F[:, 0]
    diff, p = perm_pvalues(S, F, np.random.default_rng(4), n_perm=50)
    ref = np.random.default_rng(4); perms = [ref.permutation(S) for _ in range(50)]
    for j in range(3):
        d = lambda s: s[F[:, j] == 1].mean() - s[F[:, j] == 0].mean()
        assert np.isclose(diff[j], d(S))
        assert p[j] == (1 + sum(d(q) >= d(S) for q in perms)) / 51
    assert diff[3] == 0. and p[3] == 1.


def test_s1_draws_same_permutations_whatever_remains():
    F = (np.random.default_rng(0).random((50, 3)) < 0.5).astype(np.uint8); S = np.arange(50.)
    a, b = np.random.default_rng(1), np.random.default_rng(1)
    s1_explain(S, F, [], a, n_perm=7); s1_explain(S, F, [0, 1, 2], b, n_perm=7)
    assert a.random() == b.random()
