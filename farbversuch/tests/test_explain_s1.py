import numpy as np

import pytest

from farbversuch.monitor import holm_select, perm_pvalues, pre_open_s1, s1_explain


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
    assert s1_explain(S, F, [0, 1], np.random.default_rng(1), max_new=1) == [2]


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


def test_perm_chunked_equals_unchunked():
    rng = np.random.default_rng(0); F = (rng.random((300, 7)) < .3).astype(np.uint8)
    S = 1. + 2. * F[:, 2] + rng.normal(0, 1, 300)
    a = perm_pvalues(S, F, np.random.default_rng(3), n_perm=2500, chunk=1000)
    b = perm_pvalues(S, F, np.random.default_rng(3), n_perm=2500, chunk=2500)
    assert np.array_equal(a[0], b[0]) and np.array_equal(a[1], b[1])


@pytest.mark.parametrize("n_perm, chunk", [(200, 1000), (400, 1000), (200, 1), (200, 7), (200, 199), (200, 200)])
def test_perm_result_independent_of_chunk(n_perm, chunk):
    rng = np.random.default_rng(5); F = (rng.random((120, 9)) < .4).astype(np.uint8); F[:, 8] = 1
    S = np.round(rng.normal(size=120) + F[:, 1], 1)                  # gerundet: viele Gleichstände
    a = perm_pvalues(S, F, np.random.default_rng(6), n_perm=n_perm, chunk=chunk)
    b = perm_pvalues(S, F, np.random.default_rng(6), n_perm=n_perm, chunk=n_perm)
    assert np.array_equal(a[0], b[0]) and np.array_equal(a[1], b[1])


def test_perm_draws_exactly_n_perm_permutations_whatever_chunk():
    F = (np.random.default_rng(0).random((50, 3)) < 0.5).astype(np.uint8); S = np.arange(50.)
    a, b, ref = np.random.default_rng(1), np.random.default_rng(1), np.random.default_rng(1)
    perm_pvalues(S, F, a, n_perm=23, chunk=5); perm_pvalues(S, F, b, n_perm=23, chunk=1000)
    for _ in range(23):
        ref.permutation(S)
    assert a.random() == b.random() == ref.random()


def test_perm_all_columns_constant_still_draws_all_permutations():
    S = np.arange(20.); a, ref = np.random.default_rng(1), np.random.default_rng(1)
    diff, p = perm_pvalues(S, np.zeros((20, 3), np.uint8), a, n_perm=11, chunk=4)
    for _ in range(11):
        ref.permutation(S)
    assert (diff == 0).all() and (p == 1).all() and a.random() == ref.random()


def test_s1_arm_a_can_reject_with_25000_perms():
    rng = np.random.default_rng(0); F = (rng.random((300, 1192)) < .3).astype(np.uint8)
    S = 1. + 3. * F[:, 5] + rng.normal(0, .1, 300)
    assert s1_explain(S, F, [], np.random.default_rng(1), n_perm=25000) == [5]


def test_s1_max_new_counts_only_new():
    rng = np.random.default_rng(0); F = (rng.random((400, 5)) < .3).astype(np.uint8)
    S = 1. + F[:, :4] @ np.array([3., 3., 5., 3.]) + rng.normal(0, .1, 400)
    assert s1_explain(S, F, [0, 1], np.random.default_rng(1), max_new=1) == [2]
    assert set(s1_explain(S, F, [0, 1], np.random.default_rng(1), max_new=3)) >= {2, 3}


def test_pre_open_s1_caps_at_max_open():
    rng = np.random.default_rng(0); F = (rng.random((400, 12)) < .3).astype(np.uint8)
    S = 1. + F.sum(1) * 3. + rng.normal(0, .1, 400)
    assert len(pre_open_s1(S, F, np.random.default_rng(1), n_perm=1000, max_open=8)) == 8
