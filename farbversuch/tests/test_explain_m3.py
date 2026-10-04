import numpy as np

from farbversuch import monitor
from farbversuch.forward import fit_logreg, fwd_design, mean_loglik
from farbversuch.monitor import FitStats, cv_folds, m3_explain, m3_improvements, m3_null_gain, pre_open_m3, select_m3
from farbversuch.world import N_DISP


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


def test_select_m3_requires_mean_above_delta():
    assert select_m3(np.array([[.004] * 5, [.02] * 5]), [0, 1], delta=.01) == 1
    assert select_m3(np.array([[.004] * 5]), [0], delta=.01) is None


def test_duplicates_and_base_copies_give_exact_zero_without_fit():
    Z, A, D, F = slide_data(); st = FitStats()
    Fx = np.stack([F[:, 0], F[:, 0], 1 - F[:, 0], (A == 0).astype(np.uint8)], 1)   # Signal, Duplikat, Komplement, Basisspalte
    imp, cands = m3_improvements(Z, A, D, Fx, [0], np.random.default_rng(1), stats=st)
    assert list(cands) == [1, 2, 3] and (imp == 0).all() and st.n_fits == 5          # nur die Basismodelle


def test_three_identical_copies_open_at_most_once():
    Z, A, D, F = slide_data()
    F4 = np.stack([F[:, 0]] * 3 + [F[:, 1]], 1)
    assert pre_open_m3(Z, A, D, F4, lambda r: np.random.default_rng(r), delta=0.0) == [0]


def test_m3_null_gain_zero_without_eligible():                 # Review Focus 2
    Z, A, D, F = slide_data()
    assert m3_null_gain(Z, A, D, F, [], np.random.default_rng(1)) > 0.05
    assert m3_null_gain(Z, A, D, F, [0], np.random.default_rng(1)) < 0.005
    assert m3_null_gain(Z, A, D, np.zeros((len(A), 1), np.uint8), [], np.random.default_rng(1)) == 0.0


def test_m3_explain_reports_gain():
    Z, A, D, F = slide_data(); info = {}
    assert m3_explain(Z, A, D, F, [], np.random.default_rng(1), info=info) == 0 and info["gain"] > 0.05


def test_pre_open_m3_cap_and_determinism(monkeypatch):         # Review Focus 1
    calls = iter(range(100))
    monkeypatch.setattr(monitor, "m3_explain", lambda *a, **k: next(calls))
    assert pre_open_m3(None, None, None, None, lambda r: None, delta=.01) == list(range(8))
    monkeypatch.undo()
    Z, A, D, F = slide_data()
    r1 = pre_open_m3(Z, A, D, F, lambda r: np.random.default_rng(r), delta=.01)
    assert r1 == pre_open_m3(Z, A, D, F, lambda r: np.random.default_rng(r), delta=.01) == [0]


def _naive_improvements(Z, A, D, F, rng, test_fold_coefs=False, l2=1e-3, n_folds=5):
    """Referenz zu Plan v2, Festlegung 3, Kandidat für Kandidat: Rest der Testzeilen mit den Koeffizienten der
    Trainingsteilung (test_fold_coefs=True: die falsche Variante mit eigener Regression auf der Testteilung)."""
    folds = cv_folds(len(A), rng, n_folds)
    Xb = fwd_design(Z, A)
    imp = np.zeros((F.shape[1], n_folds))
    for f, test in enumerate(folds):
        train = np.setdiff1d(np.arange(len(A)), test)
        Wb, _ = fit_logreg(Xb[train], D[train], N_DISP, l2)
        llb = mean_loglik(Xb[test], D[test], Wb)
        for j in range(F.shape[1]):
            f_tr, f_te = F[train, j].astype(float), F[test, j].astype(float)
            coef = np.linalg.lstsq(Xb[train], f_tr, rcond=None)[0]
            coef_te = np.linalg.lstsq(Xb[test], f_te, rcond=None)[0] if test_fold_coefs else coef
            r_tr, r_te = f_tr - Xb[train] @ coef, f_te - Xb[test] @ coef_te
            We, _ = fit_logreg(np.column_stack([Xb[train], r_tr]), D[train], N_DISP, l2,
                               W0=np.vstack([Wb, np.zeros((1, N_DISP))]))
            imp[j, f] = mean_loglik(np.column_stack([Xb[test], r_te]), D[test], We) - llb
    return imp


def test_test_rows_are_residualised_with_the_train_fold_coefficients():
    # Kandidaten hängen mit z und der Aktion zusammen: die Koeffizienten von Trainings- und Testteilung unterscheiden
    # sich, also auch der Rest der Testzeilen je nach Variante
    rng = np.random.default_rng(3); n = 600
    Z, A = rng.normal(size=(n, 3)), rng.integers(4, size=n)
    sig = (Z[:, 0] + rng.normal(size=n) > .5).astype(np.uint8)
    act = ((A == 1) | (rng.random(n) < .2)).astype(np.uint8)
    D = 1 + A; slide = (sig == 1) & (rng.random(n) < .5); D[slide] = 5 + A[slide]
    F = np.stack([sig, act], 1)
    imp, cands = m3_improvements(Z, A, D, F, [], np.random.default_rng(7))
    reference = _naive_improvements(Z, A, D, F, np.random.default_rng(7))
    leaky = _naive_improvements(Z, A, D, F, np.random.default_rng(7), test_fold_coefs=True)
    assert list(cands) == [0, 1] and np.abs(leaky - reference).max() > 1e-4      # der Fall trennt die Varianten
    assert np.allclose(imp, reference, rtol=0, atol=1e-10)
