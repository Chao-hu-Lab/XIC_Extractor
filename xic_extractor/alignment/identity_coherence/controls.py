from __future__ import annotations

from collections.abc import Sequence

from .control_evaluation import (
    evaluate_identity_controls as _evaluate_identity_controls,
)
from .control_manifest import (
    REQUIRED_MANIFEST_FIELDS,
    read_identity_controls_manifest,
    read_identity_controls_manifest_tsv,
)
from .control_models import (
    IdentityCoherenceOutputRecordLike,
    IdentityControlEvaluationResult,
    IdentityControlManifestEntry,
    IdentityControlsConfig,
    IdentityDecoySource,
)
from .decoy_controls import evaluate_identity_decoy as _evaluate_identity_decoy
from .models import SeedGateConfig
from .positive_controls import evaluate_positive_control
from .schema import (
    ControlStatus,
    ControlType,
    DecoyGenerationMethod,
    EvidenceStage,
    FragmentObservationMode,
    PositiveControlMappingStatus,
    RequestCandidateIdentityStatus,
)
from .seed_gate import evaluate_seed_gate


def evaluate_identity_controls(
    entries: Sequence[IdentityControlManifestEntry],
    *,
    records: Sequence[IdentityCoherenceOutputRecordLike],
    decoy_sources: Sequence[IdentityDecoySource],
    config: IdentityControlsConfig,
    seed_gate_config: SeedGateConfig = SeedGateConfig(),
) -> IdentityControlEvaluationResult:
    return _evaluate_identity_controls(
        entries,
        records=records,
        decoy_sources=decoy_sources,
        config=config,
        seed_gate_config=seed_gate_config,
        positive_control_evaluator=evaluate_positive_control,
        decoy_evaluator=evaluate_identity_decoy,
    )


def evaluate_identity_decoy(
    entry: IdentityControlManifestEntry,
    source: IdentityDecoySource,
    config: IdentityControlsConfig,
    *,
    seed_gate_config: SeedGateConfig = SeedGateConfig(),
) -> dict[str, object]:
    return _evaluate_identity_decoy(
        entry,
        source,
        config,
        seed_gate_config=seed_gate_config,
        seed_gate_evaluator=evaluate_seed_gate,
    )

__all__ = [
    "ControlStatus",
    "ControlType",
    "DecoyGenerationMethod",
    "EvidenceStage",
    "FragmentObservationMode",
    "IdentityCoherenceOutputRecordLike",
    "IdentityControlEvaluationResult",
    "IdentityControlManifestEntry",
    "IdentityControlsConfig",
    "IdentityDecoySource",
    "PositiveControlMappingStatus",
    "REQUIRED_MANIFEST_FIELDS",
    "RequestCandidateIdentityStatus",
    "evaluate_identity_controls",
    "evaluate_identity_decoy",
    "evaluate_positive_control",
    "evaluate_seed_gate",
    "read_identity_controls_manifest",
    "read_identity_controls_manifest_tsv",
]
