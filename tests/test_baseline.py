import numpy as np

from xic_extractor.baseline import asls_baseline


def test_baseline_on_flat_trace_returns_constant() -> None:
    y = np.full(200, 5.0)
    bl = asls_baseline(y, lam=1e5, p=0.01)
    assert np.allclose(bl, 5.0, atol=0.1)


def test_baseline_tracks_slow_hump_but_not_sharp_peak() -> None:
    n = 400
    x = np.arange(n)
    hump = 3.0 * np.exp(-((x - n / 2) ** 2) / (2 * 80**2))
    peak = 20.0 * np.exp(-((x - n / 2) ** 2) / (2 * 5**2))
    y = hump + peak + 0.1 * np.sin(x / 5)
    bl = asls_baseline(y, lam=1e5, p=0.01)
    apex = n // 2
    assert bl[apex] < peak[apex] * 0.3
    side = n // 4
    assert abs(bl[side] - hump[side]) < 0.5


def test_baseline_shape_matches_input() -> None:
    y = np.random.RandomState(0).normal(0, 1, 128) + 10
    bl = asls_baseline(y, lam=1e4, p=0.01)
    assert bl.shape == y.shape
