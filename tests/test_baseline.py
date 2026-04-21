import numpy as np
import pytest

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


@pytest.mark.parametrize("bad_value", [np.nan, np.inf, -np.inf])
def test_baseline_rejects_non_finite_values(bad_value: float) -> None:
    y = np.array([1.0, bad_value, 2.0])
    with pytest.raises(ValueError, match="finite"):
        asls_baseline(y)


def test_baseline_rejects_non_1d_input() -> None:
    y = np.ones((5, 2))
    with pytest.raises(ValueError, match="1-D"):
        asls_baseline(y)


def test_short_baseline_returns_float_copy() -> None:
    y = np.array([1, 2])
    bl = asls_baseline(y)
    assert bl.dtype.kind == "f"
    assert np.array_equal(bl, np.array([1.0, 2.0]))
    assert not np.shares_memory(y, bl)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"lam": 0}, "lam"),
        ({"p": 0}, "p"),
        ({"p": 1}, "p"),
        ({"n_iter": 0}, "n_iter"),
    ],
)
def test_baseline_rejects_invalid_parameters(
    kwargs: dict[str, float | int], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        asls_baseline(np.ones(5), **kwargs)
