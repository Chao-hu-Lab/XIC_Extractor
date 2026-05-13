import numpy as np
import pytest

from xic_extractor.xic_models import XICRequest, XICTrace


def test_xic_request_rejects_invalid_bounds() -> None:
    with pytest.raises(ValueError, match="rt_min must be <= rt_max"):
        XICRequest(mz=258.0, rt_min=10.0, rt_max=8.0, ppm_tol=20.0)


def test_xic_request_rejects_non_positive_ppm() -> None:
    with pytest.raises(ValueError, match="ppm_tol must be > 0"):
        XICRequest(mz=258.0, rt_min=8.0, rt_max=10.0, ppm_tol=0.0)


def test_xic_trace_normalizes_arrays_to_float() -> None:
    trace = XICTrace.from_arrays([8.1, 8.2], [10, 20])

    assert isinstance(trace.rt, np.ndarray)
    assert isinstance(trace.intensity, np.ndarray)
    assert trace.rt.dtype == float
    assert trace.intensity.dtype == float
    assert trace.rt.tolist() == [8.1, 8.2]
    assert trace.intensity.tolist() == [10.0, 20.0]


def test_xic_trace_rejects_mismatched_arrays() -> None:
    with pytest.raises(ValueError, match="matching 1D arrays"):
        XICTrace.from_arrays([8.1, 8.2], [10.0])
