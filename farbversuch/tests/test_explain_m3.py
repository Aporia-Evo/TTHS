import numpy as np

from farbversuch.monitor import FitStats, cv_folds, m3_explain, select_m3


def slide_data(n=1500, seed=0):
    rng = np.random.default_rng(seed); Z, A = rng.normal(size=(n, 3)), rng.integers(4, size=n)
    sig, noise = (rng.random((2, n)) < 0.25).astype(np.uint8)
    D = 1 + A; slide = (sig == 1) & (rng.random(n) < 0.5); D[slide] = 5 + A[slide]
    return Z, A, D, np.stack([sig, noise, np.zeros(n, np.uint8)], 1)


def test_select_m3_needs_all_folds_and_takes_largest_mean():
    assert select_m3(np.array([[.3, .3, .3, .3, -.01], [.05] * 5, [.06] * 5]), [0, 1, 2]) == 2
    assert select_m3(np.array([[.1] * 5, [.1] * 5]), [4, 7]) == 4
    assert select_m3(np.zeros((1, 5)), [0]) is None


def test_m3_opens_signal():
    Z, A, D, F = slide_data()
    assert m3_explain(Z, A, D, F, [], np.random.default_rng(1)) == 0


def test_m3_ignores_noise_once_signal_open():
    Z, A, D, F = slide_data()
    assert m3_explain(Z, A, D, F, [0], np.random.default_rng(1)) is None


def test_m3_skips_constant_column_without_fit():
    Z, A, D, F = slide_data(); st = FitStats()
    m3_explain(Z, A, D, F, [], np.random.default_rng(1), stats=st)
    assert st.n_fits == 5 * 3 and st.size > 0           # je Teilung: Basis, Signal, Rauschen


def test_m3_deterministic():
    Z, A, D, F = slide_data(); s1, s2 = FitStats(), FitStats()
    assert m3_explain(Z, A, D, F, [], np.random.default_rng(1), stats=s1) == m3_explain(Z, A, D, F, [], np.random.default_rng(1), stats=s2)
    assert s1 == s2


def test_cv_folds_partition():
    folds = cv_folds(103, np.random.default_rng(0))
    assert sorted(np.concatenate(folds).tolist()) == list(range(103)) and {len(f) for f in folds} == {20, 21}
