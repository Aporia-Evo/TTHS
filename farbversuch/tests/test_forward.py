import numpy as np

from farbversuch.forward import (
    ForwardModel,
    fit_logreg,
    freq_surprise,
    fwd_design,
    log_softmax,
    logreg_obj,
    mean_loglik,
)


def synth(n=600, d=4, K=9, seed=0):
    rng = np.random.default_rng(seed)
    X = np.hstack([rng.normal(size=(n, d)), np.ones((n, 1))]); P = np.exp(log_softmax(X @ rng.normal(size=(d + 1, K))))
    return X, np.array([rng.choice(K, p=p) for p in P])


def test_logreg_grad_matches_finite_differences():
    X, y = synth(n=50); W = np.random.default_rng(1).normal(size=(5, 9)); _, g = logreg_obj(W, X, y, 1e-3)
    for idx in [(0, 0), (2, 5), (4, 8)]:
        Wp, Wm = W.copy(), W.copy(); Wp[idx] += 1e-6; Wm[idx] -= 1e-6
        assert abs((logreg_obj(Wp, X, y, 1e-3)[0] - logreg_obj(Wm, X, y, 1e-3)[0]) / 2e-6 - g[idx]) < 1e-6


def test_fit_converges():
    X, y = synth(); W, _ = fit_logreg(X, y, 9, 1e-3)
    assert np.abs(logreg_obj(W, X, y, 1e-3)[1]).max() < 1e-6


def test_warm_start_reaches_same_optimum():
    X, y = synth(); col = (np.random.default_rng(1).random(len(y)) < 0.3).astype(float)[:, None]
    Wb, _ = fit_logreg(X, y, 9, 1e-3, tol=1e-8); Xe = np.hstack([X, col])
    Wc, _ = fit_logreg(Xe, y, 9, 1e-3, tol=1e-8)
    Ww, _ = fit_logreg(Xe, y, 9, 1e-3, tol=1e-8, W0=np.vstack([Wb, np.zeros((1, 9))]))
    assert np.abs(Wc - Ww).max() < 1e-4 and abs(mean_loglik(Xe, y, Wc) - mean_loglik(Xe, y, Ww)) < 1e-7


def test_zero_column_returns_base_exactly():
    X, y = synth(); Wb, _ = fit_logreg(X, y, 9, 1e-3)
    We, it = fit_logreg(np.hstack([X, np.zeros((len(y), 1))]), y, 9, 1e-3, W0=np.vstack([Wb, np.zeros((1, 9))]))
    assert it == 0 and np.array_equal(We[:-1], Wb) and (We[-1] == 0).all()


def test_unseen_class_finite_surprise():        # Review Focus 1
    rng = np.random.default_rng(0); Z, A = rng.normal(size=(500, 3)), rng.integers(4, size=500)
    s = ForwardModel.fit(Z, A, 1 + A).surprise(Z[:4], A[:4], np.full(4, 8))
    assert np.isfinite(s).all() and (s > 3).all()


def test_surprise_is_neg_log_prob():
    rng = np.random.default_rng(0); Z, A = rng.normal(size=(300, 3)), rng.integers(4, size=300); D = rng.integers(9, size=300)
    fm = ForwardModel.fit(Z, A, D)
    assert np.allclose(fm.surprise(Z, A, D), -log_softmax(fwd_design(Z, A) @ fm.W)[np.arange(300), D])


def test_log_softmax_stable():
    assert np.allclose(log_softmax(np.array([[1000., 0.]])), [[0., -1000.]])


def test_fwd_design_layout():
    X = fwd_design(np.zeros((2, 3)), np.array([1, 3]), np.array([[1], [0]]))
    assert X.shape == (2, 9) and list(X[0, 3:]) == [0, 1, 0, 0, 1, 1]


def test_freq_surprise():
    assert np.isclose(freq_surprise(np.array([2, 1] + [0] * 7), np.array([0, 1])), -(np.log(3 / 12) + np.log(2 / 12)) / 2)
