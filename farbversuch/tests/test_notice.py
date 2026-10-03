import numpy as np

from farbversuch.monitor import (
    calibrate_cusum,
    calibrate_m3,
    cusum_trace,
    m3_trace,
    null_threshold,
)


def test_null_threshold_is_second_largest():
    v = [1., 5., 3., 4.]
    assert null_threshold(v) == 4. and sum(x > null_threshold(v) for x in v) == 1


def test_calibrations_allow_at_most_one_null_alarm():
    rng = np.random.default_rng(0)
    nulls = [[rng.exponential(1., rng.integers(5, 15)) for _ in range(300)] for _ in range(20)]
    t = calibrate_m3(nulls)
    assert sum(max(v for _, v in m3_trace(s)) > t for s in nulls) <= 1
    k, h = calibrate_cusum(nulls)
    assert sum(cusum_trace(np.concatenate(s), k).max() > h for s in nulls) <= 1


def test_m3_trace_needs_window_and_uses_last_steps():
    tr = m3_trace([np.full(10, float(i)) for i in range(60)], window=500, interval=10)
    assert tr[0][0] == 50 and np.isclose(tr[0][1], np.arange(50.).mean())
    assert tr[1][0] == 60 and np.isclose(tr[1][1], np.arange(10., 60.).mean())


def test_cusum_trace_values():
    assert cusum_trace(np.array([1., 3., 0., 2.]), 1.).tolist() == [0., 2., 1., 2.]


def test_calibrate_cusum_k():
    k, _ = calibrate_cusum([[np.array([1., 2.]), np.array([3.])], [np.array([4.])]])
    assert np.isclose(k, 2.5 + 0.5 * np.std([1., 2., 3., 4.]))


def test_calibrate_m3_stream_without_checkpoint_counts_as_minus_inf():
    short = [np.full(10, 9.) for _ in range(10)]            # 100 Schritte < Fenster: kein Prüfpunkt
    long_ = [[np.full(10, float(v)) for _ in range(60)] for v in (1, 2)]
    assert m3_trace(short, window=500) == []
    assert calibrate_m3([short, *long_]) == 1.               # -inf, 1, 2 -> zweitgrößtes ist 1
