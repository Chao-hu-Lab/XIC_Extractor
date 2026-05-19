from __future__ import annotations

from xic_extractor.peak_detection.traces import (
    Trace,
    TraceGroup,
    untargeted_trace_group,
)


def alignment_trace_group(
    *,
    sample_stem: str,
    family_id: str,
    mz: float,
    rt_values: object,
    intensity_values: object,
    rt_min: float,
    rt_max: float,
    ppm_tol: float,
    expected_rt_min: float | None = None,
    neutral_loss_tag: str = "",
    product_mz: float | None = None,
    observed_neutral_loss_da: float | None = None,
    source: str = "",
) -> TraceGroup:
    trace = Trace.from_arrays(
        sample_name=sample_stem,
        mz=mz,
        rt=rt_values,
        intensity=intensity_values,
        rt_min=rt_min,
        rt_max=rt_max,
        ppm_tol=ppm_tol,
        source=source,
    )
    return untargeted_trace_group(
        trace,
        family_id=family_id,
        expected_rt_min=expected_rt_min,
        neutral_loss_tag=neutral_loss_tag,
        precursor_mz=mz,
        product_mz=product_mz,
        observed_neutral_loss_da=observed_neutral_loss_da,
    )
