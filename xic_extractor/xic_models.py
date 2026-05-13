from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class XICRequest:
    mz: float
    rt_min: float
    rt_max: float
    ppm_tol: float

    def __post_init__(self) -> None:
        if self.rt_min > self.rt_max:
            raise ValueError("rt_min must be <= rt_max")
        if self.ppm_tol <= 0:
            raise ValueError("ppm_tol must be > 0")


@dataclass(frozen=True)
class XICTrace:
    rt: NDArray[np.float64]
    intensity: NDArray[np.float64]

    @classmethod
    def empty(cls) -> "XICTrace":
        return cls(np.array([], dtype=float), np.array([], dtype=float))

    @classmethod
    def from_arrays(cls, rt: object, intensity: object) -> "XICTrace":
        rt_array = np.asarray(rt, dtype=float)
        intensity_array = np.asarray(intensity, dtype=float)
        if (
            rt_array.ndim != 1
            or intensity_array.ndim != 1
            or rt_array.shape != intensity_array.shape
        ):
            raise ValueError("XIC trace arrays must be matching 1D arrays")
        return cls(rt_array, intensity_array)
