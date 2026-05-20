from dataclasses import dataclass


@dataclass(frozen=True)
class InstrumentQCTarget:
    compound: str
    precursor_mz: float
    reference_mz: float
    reference_rt_min: float
    reference_base_width_min: float
    rt_min: float = 0.0
    rt_max: float = 12.0
    ppm_tol: float = 10.0


SDOLEK_TARGETS: tuple[InstrumentQCTarget, ...] = (
    InstrumentQCTarget(
        compound="SDO",
        precursor_mz=311.0814,
        reference_mz=311.0814,
        reference_rt_min=6.26,
        reference_base_width_min=0.83,
    ),
    InstrumentQCTarget(
        compound="LEK",
        precursor_mz=556.2771,
        reference_mz=556.2772,
        reference_rt_min=6.40,
        reference_base_width_min=0.85,
    ),
)
