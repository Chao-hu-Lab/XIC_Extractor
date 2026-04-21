from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve


def asls_baseline(
    y: np.ndarray, lam: float = 1e5, p: float = 0.01, n_iter: int = 10
) -> np.ndarray:
    """Asymmetric Least Squares baseline (Eilers & Boelens 2005)."""
    values = np.asarray(y, dtype=float)
    if values.ndim != 1:
        raise ValueError("asls_baseline expects a 1-D trace")
    if not np.all(np.isfinite(values)):
        raise ValueError("asls_baseline input must contain only finite values")
    if lam <= 0:
        raise ValueError("lam must be > 0")
    if not 0 < p < 1:
        raise ValueError("p must be > 0 and < 1")
    if n_iter < 1:
        raise ValueError("n_iter must be >= 1")
    n = len(values)
    if n < 3:
        return values.copy()

    differences = sparse.diags(
        [1, -2, 1], [0, 1, 2], shape=(n - 2, n), dtype=float, format="csc"
    )
    penalty = lam * (differences.T @ differences)
    weights = np.ones(n)
    baseline = values.copy()
    for _ in range(n_iter):
        weight_matrix = sparse.diags(weights, 0, format="csc")
        baseline = spsolve((weight_matrix + penalty).tocsc(), weights * values)
        weights = p * (values > baseline) + (1 - p) * (values < baseline)
    return baseline
