# Identity Coherence Controls And Decoy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the V0.4 identity-control validation slice: TSV control manifest parsing, positive-control evaluation, identity-decoy seed-gate evaluation, evaluated `controls.tsv` rows, and control-aware summary counts.

**Architecture:** This is a validation layer around the already-implemented identity coherence domain pipeline. It consumes pre-Backfill seed-gate inputs plus already-evaluated `IdentityCoherenceOutputRecord` objects, emits machine-readable control audit rows, and must never mutate identity decisions or final matrices. Decoys are identity-layer specificity tests; blank/QC/background filtering remains downstream and out of scope.

**Tech Stack:** Python 3.11+, dataclasses, `csv.DictReader`, existing `identity_coherence` domain models and schema constants, `pytest`, `ruff`.

---

## Required Working Directory

Run every command from this worktree:

```powershell
Set-Location "C:\Users\user\Desktop\XIC_Extractor\.worktrees\untargeted-backfill-logic-reset"
```

Do not run this plan from `C:\Users\user\Desktop\XIC_Extractor` or another sibling worktree.

Before starting Task 1, record the base commit:

```powershell
$env:GIT_CONFIG_COUNT = "1"
$env:GIT_CONFIG_KEY_0 = "safe.directory"
$env:GIT_CONFIG_VALUE_0 = (Get-Location).Path
git status --short
git rev-parse HEAD
```

Use that exact hash as `<base_commit_before_task1>` in the final scope guard.
Keep the three `GIT_CONFIG_*` environment variables set for every later
`git status`, `git diff`, `git add`, and `git commit` command in this plan.

If this plan file is still untracked when implementation starts, do not include
it in `<base_commit_before_task1>` or task commits. Scope guard is measured from
the latest committed implementation baseline before Task 1 begins.

## Current State

Already implemented:

- normalized fragment identity request builder;
- request-vs-candidate identity matcher;
- seed gate;
- RT center estimation;
- tier 1 / tier 2 / tier 3 cell evidence;
- row evaluator and decision summary;
- frozen TSV schema constants;
- output writer for requests, decisions, cell evidence, pass-through controls, and summary.

This plan starts after the output writer slice. It must not repeat output writer implementation, row evaluation, shape/width scoring, Backfill, or RAW/XIC retrieval.

## Scope Boundary

In scope:

- TSV manifest reader for identity controls.
- `positive_targeted_istd` and `identity_decoy` control types only.
- Positive-control evaluation against already-evaluated identity output records.
- Positive-control mapping validation against declared target mz/RT error fields
  and manifest tolerances; a matching `decision_id` alone is not sufficient.
- Decoy generation/evaluation against the seed gate using explicit pre-Backfill seed evidence and owner geometry.
- Evaluated control rows that match `IDENTITY_COHERENCE_CONTROL_COLUMNS`.
- Control-aware summary counters rendered from supplied control rows.
- Facade exports and contract tests.

Out of scope:

- YAML manifest parsing. The spec allows `.yml`, but this slice intentionally implements TSV first to avoid a new parser/dependency. `.yml/.yaml` inputs must raise a clear error.
- RAW/XIC retrieval, XIC request planning, vendor APIs, `ms1_index_source`, or process worker payload changes.
- Alignment pipeline orchestration, `owner_backfill`, workbook/HTML report rendering, or CLI wiring.
- Controls that represent blank/QC/background/downstream filtering.
- Final-matrix filtering, contaminant filtering, area correction, normalization, statistics, or production inclusion decisions.
- Full decoy row promotion through shape/width retrieval. In this slice, V0.4 decoys must fail before cross-sample promotion; if a decoy reaches `coherent_seed`, it is reported as a control failure and does not continue into tier 2/3.
- Real 8RAW controls interpretation. This slice validates the unit-level
  manifest/evaluator/writer surface only; no 8RAW claim is valid until a later
  diagnostic harness supplies real pre-Backfill decoy sources and writes
  `controls.tsv` from actual run artifacts.

## File Structure

- Create `xic_extractor/alignment/identity_coherence/controls.py`
  - Own identity-control manifest dataclasses.
  - Own TSV manifest parsing.
  - Own positive-control and decoy evaluation.
  - Produce frozen-schema control-row mappings, but do not write files.
- Modify `xic_extractor/alignment/identity_coherence/schema.py`
  - Add stable StrEnums for control type, control status, decoy method, and positive-control mapping status.
- Modify `xic_extractor/alignment/identity_coherence/output.py`
  - Keep `controls.tsv` writer generic.
  - Upgrade summary controls section from pass-through-only counters to evaluated-control counters, still derived only from supplied rows.
- Modify `xic_extractor/alignment/identity_coherence/__init__.py`
  - Re-export the control validation surface.
- Create `tests/alignment/identity_coherence/test_controls_manifest.py`
  - Test TSV manifest parsing and rejection of downstream control types.
- Create `tests/alignment/identity_coherence/test_controls_evaluation.py`
  - Test positive controls and identity decoys.
- Modify `tests/alignment/identity_coherence/test_output_writer.py`
  - Test control-aware summary counters.
- Modify `tests/alignment/identity_coherence/test_output_projection.py`
  - Keep existing pass-through projection tests aligned with the controls spec
    enum values.
- Modify `tests/alignment/identity_coherence/test_schema_contract.py`
  - Test facade exports and dependency boundary.

## Design Rules

- Controls validate identity diagnostics. They never promote identities and never change `IdentityDecisionSummary`.
- Positive-control labels are validation-only evidence. They must not affect `decision`, coherent counts, tier assignment, or promotion gates.
- Positive controls require a strict row mapping and tolerance-backed targeted
  mapping evidence. Stale `decision_id` matches must fail if `expected_mapping_status`,
  mz error, or RT delta do not validate against the manifest.
- Identity decoys are in scope because they test false identity promotion. They must use pre-Backfill request/candidate/owner inputs.
- Decoy sources must be pre-Backfill, primary, and non-duplicate before seed-gate
  evaluation. Invalid decoy provenance is a failed control setup, not an expected
  seed-gate failure.
- Background, blank, QC, contaminant, and downstream negative controls are rejected by the identity-controls manifest reader.
- `rt_shift` decoy uses `owner_peak_end_rt + decoy_rt_owner_boundary_margin_sec / 60.0`; owner RT fields are minutes, margin config is seconds.
- `mz_shift` decoy modifies request identity constraints, not the joined candidate evidence.
- `fragment_tag_shuffle` decoy modifies request fragment tags, not the joined candidate evidence.
- A decoy that reaches `coherent_seed` is a failed identity control in this
  slice. Any valid decoy source that fails before `coherent_seed` is correctly
  rejected, even if it fails at an earlier seed-gate reason than
  `required_failure_reason_when_missed`; the manifest's required reason remains
  audit context, not the binary pass/fail rule.
- Control rows are dictionaries projected to `IDENTITY_COHERENCE_CONTROL_COLUMNS`; output writing stays in `output.py`.
- `IdentityControlEvaluationResult` threshold fields are audit-only run-status
  signals. They never mutate identity decisions and should not be described as
  final matrix gating.
- Domain modules (`candidate_matcher.py`, `cell_evidence.py`, `decision.py`, `request_builder.py`, `row_evaluator.py`, `rt_center.py`, `seed_gate.py`, `shape.py`, `tags.py`, `width.py`, `models.py`, `schema.py`) must not import `controls.py` or `output.py`.
- `controls.py` may import seed-gate/domain helpers. No existing domain module may import `controls.py`.

---

## Task 1: Control Schema Enums And TSV Manifest Parser

**Files:**

- Modify: `xic_extractor/alignment/identity_coherence/schema.py`
- Create: `xic_extractor/alignment/identity_coherence/controls.py`
- Create: `tests/alignment/identity_coherence/test_controls_manifest.py`

- [ ] **Step 1: Write failing manifest parser tests**

Create `tests/alignment/identity_coherence/test_controls_manifest.py`:

```python
import pytest

from xic_extractor.alignment.identity_coherence.controls import (
    IdentityControlManifestEntry,
    read_identity_controls_manifest,
)
from xic_extractor.alignment.identity_coherence.schema import (
    ControlType,
    DecoyGenerationMethod,
    FragmentObservationMode,
    PositiveControlMappingStatus,
)


def test_read_identity_controls_manifest_tsv_accepts_positive_and_decoy(tmp_path):
    path = tmp_path / "identity_coherence_controls_manifest.tsv"
    path.write_text(
        "\t".join(
            (
                "control_id",
                "control_type",
                "control_name",
                "expected_mapping_status",
                "control_expected_behavior",
                "fragment_observation_mode",
                "precursor_tolerance_ppm",
                "product_tolerance_ppm",
                "cid_observed_loss_tolerance_ppm",
                "rt_tolerance_sec",
                "required_failure_reason_when_missed",
                "decision_id",
                "decoy_generation_method",
            )
        )
        + "\n"
        + "\t".join(
            (
                "CTRL-ISTD-1",
                "positive_targeted_istd",
                "ISTD 5mdC",
                "mapped",
                "would_primary",
                "cid_neutral_loss",
                "10",
                "10",
                "10",
                "60",
                "review_only_insufficient_support",
                "DEC-1",
                "",
            )
        )
        + "\n"
        + "\t".join(
            (
                "CTRL-DECOY-1",
                "identity_decoy",
                "RT shifted decoy",
                "mapped",
                "not_would_primary",
                "cid_neutral_loss",
                "10",
                "10",
                "10",
                "60",
                "seed_rt_outside_owner_peak",
                "DEC-1",
                "rt_shift",
            )
        )
        + "\n",
        encoding="utf-8",
    )

    entries = read_identity_controls_manifest(path)

    assert len(entries) == 2
    assert entries[0].control_type is ControlType.POSITIVE_TARGETED_ISTD
    assert entries[0].expected_mapping_status is PositiveControlMappingStatus.MAPPED
    assert entries[0].fragment_observation_mode is (
        FragmentObservationMode.CID_NEUTRAL_LOSS
    )
    assert entries[0].decision_id == "DEC-1"
    assert entries[1].control_type is ControlType.IDENTITY_DECOY
    assert entries[1].decoy_generation_method is DecoyGenerationMethod.RT_SHIFT


def test_manifest_rejects_downstream_control_types(tmp_path):
    path = tmp_path / "identity_coherence_controls_manifest.tsv"
    path.write_text(
        "control_id\tcontrol_type\tcontrol_name\texpected_mapping_status\t"
        "control_expected_behavior\tfragment_observation_mode\t"
        "precursor_tolerance_ppm\tproduct_tolerance_ppm\t"
        "cid_observed_loss_tolerance_ppm\trt_tolerance_sec\t"
        "required_failure_reason_when_missed\n"
        "CTRL-BLANK\tblank\tBlank\tmapped\tnot_would_primary\t"
        "cid_neutral_loss\t10\t10\t10\t60\tbackground\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unsupported identity control_type"):
        read_identity_controls_manifest(path)


def test_manifest_requires_decoy_generation_method_for_decoys(tmp_path):
    path = tmp_path / "identity_coherence_controls_manifest.tsv"
    path.write_text(
        "control_id\tcontrol_type\tcontrol_name\texpected_mapping_status\t"
        "control_expected_behavior\tfragment_observation_mode\t"
        "precursor_tolerance_ppm\tproduct_tolerance_ppm\t"
        "cid_observed_loss_tolerance_ppm\trt_tolerance_sec\t"
        "required_failure_reason_when_missed\tdecision_id\n"
        "CTRL-DECOY\tidentity_decoy\tMissing method\tmapped\tnot_would_primary\t"
        "cid_neutral_loss\t10\t10\t10\t60\tseed_rt_outside_owner_peak\tDEC-1\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="decoy_generation_method is required"):
        read_identity_controls_manifest(path)


def test_yaml_manifest_path_fails_with_clear_message(tmp_path):
    path = tmp_path / "identity_coherence_controls_manifest.yml"
    path.write_text("controls: []\n", encoding="utf-8")

    with pytest.raises(ValueError, match="YAML controls manifests are not implemented"):
        read_identity_controls_manifest(path)


def test_manifest_entry_rejects_nonpositive_tolerance():
    with pytest.raises(ValueError, match="precursor_tolerance_ppm must be positive"):
        IdentityControlManifestEntry(
            control_id="CTRL-1",
            control_type=ControlType.POSITIVE_TARGETED_ISTD,
            control_name="ISTD",
            expected_mapping_status=PositiveControlMappingStatus.MAPPED,
            control_expected_behavior="would_primary",
            fragment_observation_mode=FragmentObservationMode.CID_NEUTRAL_LOSS,
            precursor_tolerance_ppm=0.0,
            product_tolerance_ppm=10.0,
            cid_observed_loss_tolerance_ppm=10.0,
            rt_tolerance_sec=60.0,
            required_failure_reason_when_missed="review_only_insufficient_support",
        )
```

- [ ] **Step 2: Run the failing tests**

Run:

```powershell
uv run pytest tests\alignment\identity_coherence\test_controls_manifest.py -q
```

Expected: FAIL because `controls.py` and control enums do not exist.

- [ ] **Step 3: Add control enums**

Modify `xic_extractor/alignment/identity_coherence/schema.py` after `FragmentTagMatchPolicy`:

```python
class ControlType(StrEnum):
    POSITIVE_TARGETED_ISTD = "positive_targeted_istd"
    IDENTITY_DECOY = "identity_decoy"


class ControlStatus(StrEnum):
    ASSESSED = "assessed"
    NOT_ASSESSED = "not_assessed"
    UNMAPPED = "unmapped"
    AMBIGUOUS_MAPPING = "ambiguous_mapping"


class PositiveControlMappingStatus(StrEnum):
    MAPPED = "mapped"
    UNMAPPED = "unmapped"
    AMBIGUOUS_MAPPING = "ambiguous_mapping"
    NOT_APPLICABLE = "not_applicable"


class DecoyGenerationMethod(StrEnum):
    RT_SHIFT = "rt_shift"
    MZ_SHIFT = "mz_shift"
    FRAGMENT_TAG_SHUFFLE = "fragment_tag_shuffle"
```

- [ ] **Step 4: Add the manifest parser**

Create `xic_extractor/alignment/identity_coherence/controls.py` with this initial content:

```python
from __future__ import annotations

import csv
import math
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .schema import (
    ControlType,
    DecoyGenerationMethod,
    FragmentObservationMode,
    PositiveControlMappingStatus,
)
from .tags import normalize_fragment_tags

_REQUIRED_MANIFEST_FIELDS = (
    "control_id",
    "control_type",
    "control_name",
    "expected_mapping_status",
    "control_expected_behavior",
    "fragment_observation_mode",
    "precursor_tolerance_ppm",
    "product_tolerance_ppm",
    "cid_observed_loss_tolerance_ppm",
    "rt_tolerance_sec",
    "required_failure_reason_when_missed",
)

_DOWNSTREAM_CONTROL_TYPES = {
    "blank",
    "qc",
    "background",
    "negative_blank",
    "negative_qc",
    "contaminant",
}


@dataclass(frozen=True)
class IdentityControlManifestEntry:
    control_id: str
    control_type: ControlType
    control_name: str
    expected_mapping_status: PositiveControlMappingStatus
    control_expected_behavior: str
    fragment_observation_mode: FragmentObservationMode
    precursor_tolerance_ppm: float
    product_tolerance_ppm: float
    cid_observed_loss_tolerance_ppm: float
    rt_tolerance_sec: float
    required_failure_reason_when_missed: str
    decision_id: str = ""
    identity_family_id: str = ""
    seed_candidate_id: str = ""
    decoy_generation_method: DecoyGenerationMethod | None = None
    decoy_source_request_id: str = ""
    decoy_fragment_tags: tuple[str, ...] = ()
    positive_control_target_name: str = ""
    positive_control_target_mz: float | None = None
    positive_control_target_rt_sec: float | None = None
    positive_control_mapping_error_ppm: float | None = None
    positive_control_mapping_delta_rt_sec: float | None = None
    control_notes: str = ""

    def __post_init__(self) -> None:
        _require_text(self.control_id, "control_id")
        _require_text(self.control_name, "control_name")
        _require_text(
            self.control_expected_behavior,
            "control_expected_behavior",
        )
        _require_positive(self.precursor_tolerance_ppm, "precursor_tolerance_ppm")
        _require_positive(self.product_tolerance_ppm, "product_tolerance_ppm")
        _require_positive(
            self.cid_observed_loss_tolerance_ppm,
            "cid_observed_loss_tolerance_ppm",
        )
        _require_positive(self.rt_tolerance_sec, "rt_tolerance_sec")
        if (
            self.control_type is ControlType.IDENTITY_DECOY
            and self.decoy_generation_method is None
        ):
            raise ValueError("decoy_generation_method is required for identity_decoy")


def read_identity_controls_manifest(
    path: str | Path,
) -> tuple[IdentityControlManifestEntry, ...]:
    manifest_path = Path(path)
    suffix = manifest_path.suffix.lower()
    if suffix in {".yml", ".yaml"}:
        raise ValueError("YAML controls manifests are not implemented in this slice")
    if suffix != ".tsv":
        raise ValueError("identity controls manifest must be a .tsv file")
    return read_identity_controls_manifest_tsv(manifest_path)


def read_identity_controls_manifest_tsv(
    path: str | Path,
) -> tuple[IdentityControlManifestEntry, ...]:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, dialect="excel-tab")
        missing = tuple(
            field for field in _REQUIRED_MANIFEST_FIELDS
            if field not in (reader.fieldnames or ())
        )
        if missing:
            raise ValueError(f"controls manifest missing fields: {', '.join(missing)}")
        return tuple(
            _manifest_entry_from_row(row, row_number=index + 2)
            for index, row in enumerate(reader)
        )


def _manifest_entry_from_row(
    row: Mapping[str, str | None],
    *,
    row_number: int,
) -> IdentityControlManifestEntry:
    control_type_text = _text(row, "control_type")
    if control_type_text in _DOWNSTREAM_CONTROL_TYPES:
        raise ValueError(
            f"unsupported identity control_type at row {row_number}: "
            f"{control_type_text}"
        )
    control_type = _enum(ControlType, control_type_text, "control_type", row_number)
    decoy_method_text = _text(row, "decoy_generation_method", required=False)
    decoy_method = (
        _enum(
            DecoyGenerationMethod,
            decoy_method_text,
            "decoy_generation_method",
            row_number,
        )
        if decoy_method_text
        else None
    )
    decoy_tags, _ = normalize_fragment_tags(
        _text(row, "decoy_fragment_tags", required=False),
    )
    return IdentityControlManifestEntry(
        control_id=_text(row, "control_id"),
        control_type=control_type,
        control_name=_text(row, "control_name"),
        expected_mapping_status=_enum(
            PositiveControlMappingStatus,
            _text(row, "expected_mapping_status"),
            "expected_mapping_status",
            row_number,
        ),
        control_expected_behavior=_text(row, "control_expected_behavior"),
        fragment_observation_mode=_enum(
            FragmentObservationMode,
            _text(row, "fragment_observation_mode"),
            "fragment_observation_mode",
            row_number,
        ),
        precursor_tolerance_ppm=_positive_float(row, "precursor_tolerance_ppm"),
        product_tolerance_ppm=_positive_float(row, "product_tolerance_ppm"),
        cid_observed_loss_tolerance_ppm=_positive_float(
            row,
            "cid_observed_loss_tolerance_ppm",
        ),
        rt_tolerance_sec=_positive_float(row, "rt_tolerance_sec"),
        required_failure_reason_when_missed=_text(
            row,
            "required_failure_reason_when_missed",
        ),
        decision_id=_text(row, "decision_id", required=False),
        identity_family_id=_text(row, "identity_family_id", required=False),
        seed_candidate_id=_text(row, "seed_candidate_id", required=False),
        decoy_generation_method=decoy_method,
        decoy_source_request_id=_text(
            row,
            "decoy_source_request_id",
            required=False,
        ),
        decoy_fragment_tags=decoy_tags,
        positive_control_target_name=_text(
            row,
            "positive_control_target_name",
            required=False,
        ),
        positive_control_target_mz=_optional_float(row, "positive_control_target_mz"),
        positive_control_target_rt_sec=_optional_float(
            row,
            "positive_control_target_rt_sec",
        ),
        positive_control_mapping_error_ppm=_optional_float(
            row,
            "positive_control_mapping_error_ppm",
        ),
        positive_control_mapping_delta_rt_sec=_optional_float(
            row,
            "positive_control_mapping_delta_rt_sec",
        ),
        control_notes=_text(row, "control_notes", required=False),
    )


def _text(
    row: Mapping[str, str | None],
    field: str,
    *,
    required: bool = True,
) -> str:
    value = row.get(field)
    if value is None:
        value = ""
    text = value.strip()
    if required and not text:
        raise ValueError(f"{field} is required")
    return text


def _enum(
    enum_type: type[Enum],
    value: str,
    field: str,
    row_number: int,
):
    try:
        return enum_type(value)
    except ValueError as exc:
        raise ValueError(
            f"invalid {field} at row {row_number}: {value}"
        ) from exc


def _positive_float(row: Mapping[str, str | None], field: str) -> float:
    value = _optional_float(row, field)
    _require_positive(value, field)
    return float(value)


def _optional_float(row: Mapping[str, str | None], field: str) -> float | None:
    text = _text(row, field, required=False)
    if not text:
        return None
    try:
        value = float(text)
    except ValueError as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not math.isfinite(value):
        raise ValueError(f"{field} must be finite")
    return value


def _require_text(value: str, field: str) -> None:
    if not value.strip():
        raise ValueError(f"{field} is required")


def _require_positive(value: float | None, field: str) -> None:
    if value is None or not math.isfinite(value) or value <= 0:
        raise ValueError(f"{field} must be positive")
```

- [ ] **Step 5: Run tests**

Run:

```powershell
uv run pytest tests\alignment\identity_coherence\test_controls_manifest.py -q
uv run ruff check xic_extractor\alignment\identity_coherence\schema.py xic_extractor\alignment\identity_coherence\controls.py tests\alignment\identity_coherence\test_controls_manifest.py
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add xic_extractor\alignment\identity_coherence\schema.py xic_extractor\alignment\identity_coherence\controls.py tests\alignment\identity_coherence\test_controls_manifest.py
git commit -m "feat: parse identity coherence controls manifest"
```

---

## Task 2: Positive-Control Evaluation

**Files:**

- Modify: `xic_extractor/alignment/identity_coherence/controls.py`
- Create/Modify: `tests/alignment/identity_coherence/test_controls_evaluation.py`

- [ ] **Step 1: Write failing positive-control tests**

Create `tests/alignment/identity_coherence/test_controls_evaluation.py`:

```python
from dataclasses import replace

import pytest

from tests.alignment.identity_coherence.output_fixtures import output_record
from xic_extractor.alignment.identity_coherence.controls import (
    IdentityControlManifestEntry,
    evaluate_positive_control,
)
from xic_extractor.alignment.identity_coherence.schema import (
    ControlStatus,
    ControlType,
    FragmentObservationMode,
    IdentityDecision,
    PositiveControlMappingStatus,
)


def _positive_entry(**overrides):
    values = dict(
        control_id="CTRL-ISTD-1",
        control_type=ControlType.POSITIVE_TARGETED_ISTD,
        control_name="ISTD 5mdC",
        expected_mapping_status=PositiveControlMappingStatus.MAPPED,
        control_expected_behavior="would_primary",
        fragment_observation_mode=FragmentObservationMode.CID_NEUTRAL_LOSS,
        precursor_tolerance_ppm=10.0,
        product_tolerance_ppm=10.0,
        cid_observed_loss_tolerance_ppm=10.0,
        rt_tolerance_sec=60.0,
        required_failure_reason_when_missed="review_only_insufficient_support",
        decision_id="DEC-1",
        positive_control_target_name="5mdC",
        positive_control_target_mz=500.0,
        positive_control_target_rt_sec=300.0,
        positive_control_mapping_error_ppm=0.2,
        positive_control_mapping_delta_rt_sec=2.0,
    )
    values.update(overrides)
    return IdentityControlManifestEntry(**values)


def test_evaluate_positive_control_passes_mapped_would_primary():
    row = evaluate_positive_control(_positive_entry(), (output_record(),))

    assert row["control_id"] == "CTRL-ISTD-1"
    assert row["control_type"] == "positive_targeted_istd"
    assert row["control_status"] == ControlStatus.ASSESSED.value
    assert row["control_observed_behavior"] == (
        "would_primary_provisional_identity_family_support"
    )
    assert row["control_pass"] is True
    assert row["control_failure_reason"] == ""
    assert row["positive_control_mapping_status"] == "mapped"
    assert row["positive_control_target_name"] == "5mdC"


def test_evaluate_positive_control_fails_when_mapped_row_is_not_promoted():
    record = output_record()
    failed_decision = replace(
        record.row_result.decision,
        decision=IdentityDecision.REVIEW_ONLY_INSUFFICIENT_SUPPORT,
        decision_reason="insufficient_support",
    )
    failed_record = replace(
        record,
        row_result=replace(record.row_result, decision=failed_decision),
    )

    row = evaluate_positive_control(_positive_entry(), (failed_record,))

    assert row["control_pass"] is False
    assert row["control_observed_behavior"] == "review_only_insufficient_support"
    assert row["control_failure_reason"] == "review_only_insufficient_support"


def test_evaluate_positive_control_fails_mapping_out_of_tolerance():
    row = evaluate_positive_control(
        _positive_entry(positive_control_mapping_error_ppm=11.0),
        (output_record(),),
    )

    assert row["control_status"] == ControlStatus.UNMAPPED.value
    assert row["control_pass"] is False
    assert row["positive_control_mapping_status"] == "unmapped"
    assert row["control_failure_reason"] == (
        "positive_control_mapping_out_of_tolerance"
    )


def test_evaluate_positive_control_fails_missing_mapping_evidence():
    row = evaluate_positive_control(
        _positive_entry(positive_control_mapping_error_ppm=None),
        (output_record(),),
    )

    assert row["control_status"] == ControlStatus.UNMAPPED.value
    assert row["control_pass"] is False
    assert row["control_failure_reason"] == (
        "positive_control_mapping_missing_evidence"
    )


def test_evaluate_positive_control_unmapped_when_decision_id_missing():
    row = evaluate_positive_control(
        _positive_entry(decision_id="MISSING-DECISION"),
        (output_record(),),
    )

    assert row["control_status"] == ControlStatus.UNMAPPED.value
    assert row["control_pass"] is False
    assert row["positive_control_mapping_status"] == "unmapped"
    assert row["control_failure_reason"] == "unmapped"


def test_evaluate_positive_control_reports_ambiguous_mapping():
    first = output_record()
    second_decision = replace(
        first.row_result.decision,
        decision_id="DEC-2",
        seed_candidate_id="CAND-2",
    )
    second_seed_gate = replace(
        first.seed_gate,
        resolved_request=replace(
            first.seed_gate.resolved_request,
            decision_id="DEC-2",
            seed_candidate_id="CAND-2",
        ),
    )
    second = replace(
        first,
        seed_gate=second_seed_gate,
        row_result=replace(first.row_result, decision=second_decision),
    )

    row = evaluate_positive_control(
        _positive_entry(decision_id="", identity_family_id="IDF-1"),
        (first, second),
    )

    assert row["control_status"] == ControlStatus.AMBIGUOUS_MAPPING.value
    assert row["control_pass"] is False
    assert row["positive_control_mapping_status"] == "ambiguous_mapping"
    assert row["control_failure_reason"] == "ambiguous_mapping"


def test_evaluate_positive_control_reports_conflicting_manifest_keys():
    first = output_record()
    second_decision = replace(
        first.row_result.decision,
        decision_id="DEC-2",
        seed_candidate_id="CAND-2",
    )
    second_seed_gate = replace(
        first.seed_gate,
        resolved_request=replace(
            first.seed_gate.resolved_request,
            decision_id="DEC-2",
            seed_candidate_id="CAND-2",
        ),
    )
    second = replace(
        first,
        seed_gate=second_seed_gate,
        row_result=replace(first.row_result, decision=second_decision),
    )

    row = evaluate_positive_control(
        _positive_entry(decision_id="DEC-1", seed_candidate_id="CAND-2"),
        (first, second),
    )

    assert row["control_status"] == ControlStatus.AMBIGUOUS_MAPPING.value
    assert row["control_failure_reason"] == "ambiguous_mapping"


def test_evaluate_positive_control_reports_expected_mapping_status_mismatch():
    row = evaluate_positive_control(
        _positive_entry(expected_mapping_status=PositiveControlMappingStatus.UNMAPPED),
        (output_record(),),
    )

    assert row["control_status"] == ControlStatus.UNMAPPED.value
    assert row["control_pass"] is False
    assert row["control_failure_reason"] == "expected_mapping_status_mismatch"


def test_positive_control_labels_do_not_mutate_decision_summary():
    record = output_record()
    before = record.row_result.decision

    evaluate_positive_control(_positive_entry(), (record,))

    assert record.row_result.decision is before
    assert before.decision is IdentityDecision.WOULD_PRIMARY
```

When adding these tests, merge the new import names into the file's existing
top-level import blocks. Do not append import statements after test functions.

- [ ] **Step 2: Run failing tests**

Run:

```powershell
uv run pytest tests\alignment\identity_coherence\test_controls_evaluation.py -q
```

Expected: FAIL because `evaluate_positive_control()` does not exist.

- [ ] **Step 3: Implement positive-control evaluation**

Append this block to `controls.py`:

```python
from collections.abc import Sequence
from typing import Any, Protocol

from .schema import ControlStatus


class IdentityCoherenceOutputRecordLike(Protocol):
    seed_gate: Any
    row_result: Any


def evaluate_positive_control(
    entry: IdentityControlManifestEntry,
    records: Sequence[IdentityCoherenceOutputRecordLike],
) -> dict[str, object]:
    if entry.control_type is not ControlType.POSITIVE_TARGETED_ISTD:
        raise ValueError("evaluate_positive_control requires positive_targeted_istd")
    mapping_status, record = _resolve_record_for_entry(entry, records)
    mapping_status, mapping_failure_reason = _validate_positive_control_mapping(
        entry,
        mapping_status,
    )
    if record is None or mapping_failure_reason:
        control_status = _control_status_for_mapping_status(mapping_status)
        failure_reason = mapping_failure_reason or str(_enum_value(mapping_status))
        return _control_row(
            entry,
            control_status=control_status,
            control_observed_behavior=str(failure_reason),
            control_pass=False,
            control_failure_reason=str(failure_reason),
            positive_control_mapping_status=mapping_status,
        )
    decision = record.row_result.decision
    observed = _enum_value(decision.decision)
    passed = observed == "would_primary_provisional_identity_family_support"
    failure_reason = "" if passed else entry.required_failure_reason_when_missed
    return _control_row(
        entry,
        decision_id=decision.decision_id,
        identity_family_id=decision.identity_family_id,
        seed_candidate_id=decision.seed_candidate_id,
        control_status=ControlStatus.ASSESSED,
        control_observed_behavior=str(observed),
        control_pass=passed,
        control_failure_reason=failure_reason,
        positive_control_mapping_status=mapping_status,
    )


def _validate_positive_control_mapping(
    entry: IdentityControlManifestEntry,
    mapping_status: PositiveControlMappingStatus,
) -> tuple[PositiveControlMappingStatus, str]:
    if mapping_status is not PositiveControlMappingStatus.MAPPED:
        return mapping_status, str(_enum_value(mapping_status))
    if mapping_status is not entry.expected_mapping_status:
        return (
            PositiveControlMappingStatus.UNMAPPED,
            "expected_mapping_status_mismatch",
        )
    if entry.expected_mapping_status is not PositiveControlMappingStatus.MAPPED:
        return mapping_status, "positive_control_not_mapped"

    mapping_numbers = (
        entry.positive_control_target_mz,
        entry.positive_control_target_rt_sec,
        entry.positive_control_mapping_error_ppm,
        entry.positive_control_mapping_delta_rt_sec,
    )
    if not all(_is_finite_number(value) for value in mapping_numbers):
        return (
            PositiveControlMappingStatus.UNMAPPED,
            "positive_control_mapping_missing_evidence",
        )
    if (
        abs(float(entry.positive_control_mapping_error_ppm))
        > entry.precursor_tolerance_ppm
        or abs(float(entry.positive_control_mapping_delta_rt_sec))
        > entry.rt_tolerance_sec
    ):
        return (
            PositiveControlMappingStatus.UNMAPPED,
            "positive_control_mapping_out_of_tolerance",
        )
    return PositiveControlMappingStatus.MAPPED, ""


def _control_status_for_mapping_status(
    mapping_status: PositiveControlMappingStatus,
) -> ControlStatus:
    if mapping_status is PositiveControlMappingStatus.AMBIGUOUS_MAPPING:
        return ControlStatus.AMBIGUOUS_MAPPING
    if mapping_status is PositiveControlMappingStatus.MAPPED:
        return ControlStatus.ASSESSED
    return ControlStatus.UNMAPPED


def _resolve_record_for_entry(
    entry: IdentityControlManifestEntry,
    records: Sequence[IdentityCoherenceOutputRecordLike],
) -> tuple[PositiveControlMappingStatus, IdentityCoherenceOutputRecordLike | None]:
    supplied = _record_match_constraints(entry)
    if not supplied:
        return PositiveControlMappingStatus.UNMAPPED, None
    exact_matches = [
        record for record in records
        if all(_record_value(record, field) == value for field, value in supplied)
    ]
    if len(exact_matches) == 1:
        return PositiveControlMappingStatus.MAPPED, exact_matches[0]
    if len(exact_matches) > 1:
        return PositiveControlMappingStatus.AMBIGUOUS_MAPPING, None
    partial_fields = {
        field for field, value in supplied
        if any(_record_value(record, field) == value for record in records)
    }
    if partial_fields:
        return PositiveControlMappingStatus.AMBIGUOUS_MAPPING, None
    return PositiveControlMappingStatus.UNMAPPED, None


def _record_match_constraints(
    entry: IdentityControlManifestEntry,
) -> tuple[tuple[str, str], ...]:
    return tuple(
        (field, value)
        for field, value in (
            ("decision_id", entry.decision_id),
            ("identity_family_id", entry.identity_family_id),
            ("seed_candidate_id", entry.seed_candidate_id),
        )
        if value
    )


def _record_value(record: IdentityCoherenceOutputRecordLike, field: str) -> str:
    decision = record.row_result.decision
    values = {
        "decision_id": decision.decision_id,
        "identity_family_id": decision.identity_family_id,
        "seed_candidate_id": decision.seed_candidate_id,
    }
    return values[field]


def _is_finite_number(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
    )


def _control_row(
    entry: IdentityControlManifestEntry,
    *,
    decision_id: str = "",
    identity_family_id: str = "",
    seed_candidate_id: str = "",
    control_status: ControlStatus,
    control_observed_behavior: str,
    control_pass: bool | str,
    control_failure_reason: str,
    positive_control_mapping_status: PositiveControlMappingStatus,
    decoy_generation_method: DecoyGenerationMethod | None = None,
    decoy_source_request_id: str = "",
    decoy_shift_value: float | str = "",
    decoy_identity_constraint_changed: str = "",
) -> dict[str, object]:
    return {
        "control_id": entry.control_id,
        "control_type": entry.control_type,
        "control_name": entry.control_name,
        "decision_id": decision_id or entry.decision_id,
        "identity_family_id": identity_family_id or entry.identity_family_id,
        "seed_candidate_id": seed_candidate_id or entry.seed_candidate_id,
        "control_status": control_status,
        "control_expected_behavior": entry.control_expected_behavior,
        "control_observed_behavior": control_observed_behavior,
        "control_pass": control_pass,
        "control_failure_reason": control_failure_reason,
        "fragment_observation_mode": entry.fragment_observation_mode,
        "decoy_generation_method": decoy_generation_method or "",
        "decoy_source_request_id": decoy_source_request_id,
        "decoy_shift_value": decoy_shift_value,
        "decoy_identity_constraint_changed": decoy_identity_constraint_changed,
        "positive_control_mapping_status": positive_control_mapping_status,
        "positive_control_target_name": entry.positive_control_target_name,
        "positive_control_target_mz": entry.positive_control_target_mz,
        "positive_control_target_rt_sec": entry.positive_control_target_rt_sec,
        "positive_control_mapping_error_ppm": (
            entry.positive_control_mapping_error_ppm
        ),
        "positive_control_mapping_delta_rt_sec": (
            entry.positive_control_mapping_delta_rt_sec
        ),
        "control_notes": entry.control_notes,
    }


def _enum_value(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    return value
```

Place `Sequence`, `from typing import Any, Protocol`, and `ControlStatus` with
the top-level imports, not in the middle of the file. The block above shows the
exact new symbols but the final file must keep all imports at the top.

- [ ] **Step 4: Run tests**

Run:

```powershell
uv run pytest tests\alignment\identity_coherence\test_controls_evaluation.py -q
uv run ruff check xic_extractor\alignment\identity_coherence\controls.py tests\alignment\identity_coherence\test_controls_evaluation.py
```

Expected: PASS for positive-control tests.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor\alignment\identity_coherence\controls.py tests\alignment\identity_coherence\test_controls_evaluation.py
git commit -m "feat: evaluate identity coherence positive controls"
```

---

## Task 3: Identity-Decoy Generation And Seed-Gate Evaluation

**Files:**

- Modify: `xic_extractor/alignment/identity_coherence/controls.py`
- Modify: `tests/alignment/identity_coherence/test_controls_evaluation.py`

- [ ] **Step 1: Add failing decoy tests**

Append these tests to `tests/alignment/identity_coherence/test_controls_evaluation.py`:

```python
from xic_extractor.alignment.identity_coherence.controls import (
    IdentityControlsConfig,
    IdentityDecoySource,
    evaluate_identity_decoy,
)
from xic_extractor.alignment.identity_coherence.models import (
    SeedCandidateEvidence,
    SeedGateConfig,
)
from xic_extractor.alignment.identity_coherence.schema import (
    DecoyGenerationMethod,
    EvidenceStage,
    SeedRejectReason,
)


class OwnerLike:
    owner_apex_rt = 5.0
    owner_peak_start_rt = 4.90
    owner_peak_end_rt = 5.10
    owner_area = 1000.0
    owner_height = 200.0


def _decoy_entry(method, **overrides):
    values = dict(
        control_id=f"CTRL-DECOY-{method.value}",
        control_type=ControlType.IDENTITY_DECOY,
        control_name=f"{method.value} decoy",
        expected_mapping_status=PositiveControlMappingStatus.MAPPED,
        control_expected_behavior="not_would_primary",
        fragment_observation_mode=FragmentObservationMode.CID_NEUTRAL_LOSS,
        precursor_tolerance_ppm=10.0,
        product_tolerance_ppm=10.0,
        cid_observed_loss_tolerance_ppm=10.0,
        rt_tolerance_sec=60.0,
        required_failure_reason_when_missed="request_candidate_identity_mismatch",
        decision_id="DEC-1",
        decoy_generation_method=method,
    )
    values.update(overrides)
    return IdentityControlManifestEntry(**values)


def _decoy_source():
    return IdentityDecoySource(
        source_record=output_record(),
        seed_evidence=SeedCandidateEvidence(
            candidate_id="CAND-1",
            precursor_mz=500.0,
            product_mz=384.0,
            cid_observed_loss_da=116.0,
            fragment_tags=("MeR", "dR"),
            best_seed_rt=5.0,
            ms1_scan_support_score=0.9,
            evidence_stage=EvidenceStage.PRE_BACKFILL,
        ),
        owner_like=OwnerLike(),
    )


def test_rt_shift_decoy_uses_owner_boundary_plus_seconds_margin():
    row = evaluate_identity_decoy(
        _decoy_entry(
            DecoyGenerationMethod.RT_SHIFT,
            required_failure_reason_when_missed="seed_rt_outside_owner_peak",
        ),
        _decoy_source(),
        IdentityControlsConfig(decoy_rt_owner_boundary_margin_sec=6.0),
    )

    assert row["control_pass"] is True
    assert row["control_observed_behavior"] == (
        SeedRejectReason.SEED_RT_OUTSIDE_OWNER_PEAK.value
    )
    assert row["decoy_generation_method"] == "rt_shift"
    assert row["decoy_shift_value"] == 6.0
    assert row["decoy_identity_constraint_changed"] == "best_seed_rt"


def test_mz_shift_decoy_fails_request_candidate_identity_match():
    row = evaluate_identity_decoy(
        _decoy_entry(DecoyGenerationMethod.MZ_SHIFT),
        _decoy_source(),
        IdentityControlsConfig(),
    )

    assert row["control_pass"] is True
    assert row["control_observed_behavior"] == (
        SeedRejectReason.REQUEST_CANDIDATE_IDENTITY_MISMATCH.value
    )
    assert row["decoy_identity_constraint_changed"] == "precursor_mz;product_mz"


def test_fragment_tag_shuffle_decoy_fails_request_candidate_identity_match():
    row = evaluate_identity_decoy(
        _decoy_entry(
            DecoyGenerationMethod.FRAGMENT_TAG_SHUFFLE,
            decoy_fragment_tags=("other_diagnostic_tag",),
        ),
        _decoy_source(),
        IdentityControlsConfig(),
    )

    assert row["control_pass"] is True
    assert row["control_observed_behavior"] == (
        SeedRejectReason.REQUEST_CANDIDATE_IDENTITY_MISMATCH.value
    )
    assert row["decoy_identity_constraint_changed"] == "fragment_tags"


def test_decoy_that_reaches_coherent_seed_is_control_failure():
    row = evaluate_identity_decoy(
        _decoy_entry(
            DecoyGenerationMethod.RT_SHIFT,
            required_failure_reason_when_missed="seed_rt_outside_owner_peak",
        ),
        _decoy_source(),
        IdentityControlsConfig(decoy_rt_owner_boundary_margin_sec=6.0),
        seed_gate_config=SeedGateConfig(require_seed_rt_inside_owner_peak=False),
    )

    assert row["control_pass"] is False
    assert row["control_failure_reason"] == "decoy_seed_gate_coherent"


def test_decoy_rejected_by_earlier_seed_gate_still_passes_control():
    source = _decoy_source()
    source = replace(
        source,
        seed_evidence=replace(source.seed_evidence, ms1_scan_support_score=0.0),
    )

    row = evaluate_identity_decoy(
        _decoy_entry(
            DecoyGenerationMethod.RT_SHIFT,
            required_failure_reason_when_missed="seed_rt_outside_owner_peak",
        ),
        source,
        IdentityControlsConfig(),
        seed_gate_config=SeedGateConfig(require_seed_rt_inside_owner_peak=False),
    )

    assert row["control_pass"] is True
    assert row["control_observed_behavior"] == "low_ms1_scan_support"
    assert row["control_failure_reason"] == ""


def test_decoy_rejects_backfill_only_seed_evidence():
    source = _decoy_source()
    source = replace(
        source,
        seed_evidence=replace(
            source.seed_evidence,
            evidence_stage=EvidenceStage.BACKFILL_ONLY,
        ),
    )

    row = evaluate_identity_decoy(
        _decoy_entry(
            DecoyGenerationMethod.RT_SHIFT,
            required_failure_reason_when_missed="seed_rt_outside_owner_peak",
        ),
        source,
        IdentityControlsConfig(),
    )

    assert row["control_status"] == ControlStatus.NOT_ASSESSED.value
    assert row["control_pass"] is False
    assert row["control_observed_behavior"] == "invalid_decoy_source_stage"
    assert row["control_failure_reason"] == "invalid_decoy_source_stage"


def test_decoy_rejects_post_backfill_owner_evidence():
    source = replace(_decoy_source(), owner_evidence_stage=EvidenceStage.POST_BACKFILL)

    row = evaluate_identity_decoy(
        _decoy_entry(
            DecoyGenerationMethod.RT_SHIFT,
            required_failure_reason_when_missed="seed_rt_outside_owner_peak",
        ),
        source,
        IdentityControlsConfig(),
    )

    assert row["control_status"] == ControlStatus.NOT_ASSESSED.value
    assert row["control_pass"] is False
    assert row["control_observed_behavior"] == "invalid_decoy_source_stage"
    assert row["control_failure_reason"] == "invalid_decoy_source_stage"


def test_decoy_rejects_non_primary_or_duplicate_source():
    row = evaluate_identity_decoy(
        _decoy_entry(
            DecoyGenerationMethod.RT_SHIFT,
            required_failure_reason_when_missed="seed_rt_outside_owner_peak",
        ),
        replace(_decoy_source(), owner_assignment_status="ambiguous"),
        IdentityControlsConfig(),
    )

    assert row["control_pass"] is False
    assert row["control_failure_reason"] == "invalid_decoy_source_stage"


def test_identity_controls_config_rejects_invalid_thresholds():
    with pytest.raises(ValueError, match="positive_control_min_pass_fraction"):
        IdentityControlsConfig(positive_control_min_pass_fraction=1.5)
    with pytest.raises(ValueError, match="max_decoy_coherent_seed_count"):
        IdentityControlsConfig(max_decoy_coherent_seed_count=-1)
```

When adding these tests, merge `IdentityControlsConfig`, `IdentityDecoySource`,
`evaluate_identity_decoy`, `SeedCandidateEvidence`, `SeedGateConfig`,
`DecoyGenerationMethod`, `EvidenceStage`, and `SeedRejectReason` into the
existing top-level imports. Do not add imports below existing tests.

- [ ] **Step 2: Run failing decoy tests**

Run:

```powershell
uv run pytest tests\alignment\identity_coherence\test_controls_evaluation.py -q
```

Expected: FAIL because decoy dataclasses/functions do not exist.

- [ ] **Step 3: Implement decoy source, config, and evaluation**

Append this block to `controls.py` after the positive-control helpers:

```python
from dataclasses import replace

from .models import (
    IdentityCoherenceRequest,
    SeedCandidateEvidence,
    SeedGateConfig,
)
from .schema import EvidenceStage, RequestCandidateIdentityStatus
from .seed_gate import evaluate_seed_gate
from .tags import format_fragment_tags


@dataclass(frozen=True)
class IdentityControlsConfig:
    positive_control_min_pass_fraction: float = 1.00
    max_decoy_coherent_seed_count: int = 0
    decoy_rt_owner_boundary_margin_sec: float = 6.0

    def __post_init__(self) -> None:
        if not (0.0 < self.positive_control_min_pass_fraction <= 1.0):
            raise ValueError(
                "positive_control_min_pass_fraction must be > 0 and <= 1"
            )
        if self.max_decoy_coherent_seed_count < 0:
            raise ValueError("max_decoy_coherent_seed_count must be nonnegative")
        _require_positive(
            self.decoy_rt_owner_boundary_margin_sec,
            "decoy_rt_owner_boundary_margin_sec",
        )


@dataclass(frozen=True)
class IdentityDecoySource:
    source_record: IdentityCoherenceOutputRecordLike
    seed_evidence: SeedCandidateEvidence
    owner_like: object
    owner_assignment_status: str = "primary"
    duplicate_loser: bool = False
    owner_evidence_stage: EvidenceStage = EvidenceStage.PRE_BACKFILL


def evaluate_identity_decoy(
    entry: IdentityControlManifestEntry,
    source: IdentityDecoySource,
    config: IdentityControlsConfig,
    *,
    seed_gate_config: SeedGateConfig = SeedGateConfig(),
) -> dict[str, object]:
    if entry.control_type is not ControlType.IDENTITY_DECOY:
        raise ValueError("evaluate_identity_decoy requires identity_decoy")
    if entry.decoy_generation_method is None:
        raise ValueError("decoy_generation_method is required")

    source_decision = source.source_record.row_result.decision
    source_request_id = source.source_record.seed_gate.resolved_request.request_id
    provenance_failure = _decoy_source_provenance_failure(source)
    if provenance_failure:
        return _control_row(
            entry,
            decision_id=source_decision.decision_id,
            identity_family_id=source_decision.identity_family_id,
            seed_candidate_id=source_decision.seed_candidate_id,
            control_status=ControlStatus.NOT_ASSESSED,
            control_observed_behavior=provenance_failure,
            control_pass=False,
            control_failure_reason=provenance_failure,
            positive_control_mapping_status=(
                PositiveControlMappingStatus.NOT_APPLICABLE
            ),
            decoy_generation_method=entry.decoy_generation_method,
            decoy_source_request_id=source_request_id,
        )

    request, evidence, changed, shift_value = _build_decoy_seed_inputs(
        entry,
        source,
        config,
    )
    result = evaluate_seed_gate(
        request,
        evidence,
        source.owner_like,
        owner_assignment_status=source.owner_assignment_status,
        duplicate_loser=source.duplicate_loser,
        owner_evidence_stage=source.owner_evidence_stage,
        config=seed_gate_config,
    )
    observed = (
        _enum_value(result.seed_reject_reason)
        if result.seed_reject_reason is not None
        else _enum_value(result.seed_gate_class)
    )
    if observed == "coherent_seed":
        passed = False
        failure_reason = "decoy_seed_gate_coherent"
    else:
        passed = True
        failure_reason = ""
    return _control_row(
        entry,
        decision_id=source_decision.decision_id,
        identity_family_id=source_decision.identity_family_id,
        seed_candidate_id=source_decision.seed_candidate_id,
        control_status=ControlStatus.ASSESSED,
        control_observed_behavior=str(observed),
        control_pass=passed,
        control_failure_reason=failure_reason,
        positive_control_mapping_status=PositiveControlMappingStatus.NOT_APPLICABLE,
        decoy_generation_method=entry.decoy_generation_method,
        decoy_source_request_id=source_request_id,
        decoy_shift_value=shift_value,
        decoy_identity_constraint_changed=changed,
    )


def _decoy_source_provenance_failure(source: IdentityDecoySource) -> str:
    if (
        _enum_value(source.seed_evidence.evidence_stage)
        != EvidenceStage.PRE_BACKFILL.value
    ):
        return "invalid_decoy_source_stage"
    if (
        _enum_value(source.owner_evidence_stage)
        != EvidenceStage.PRE_BACKFILL.value
    ):
        return "invalid_decoy_source_stage"
    if source.duplicate_loser:
        return "invalid_decoy_source_stage"
    if str(_enum_value(source.owner_assignment_status)) != "primary":
        return "invalid_decoy_source_stage"
    return ""


def _build_decoy_seed_inputs(
    entry: IdentityControlManifestEntry,
    source: IdentityDecoySource,
    config: IdentityControlsConfig,
) -> tuple[IdentityCoherenceRequest, SeedCandidateEvidence, str, float | str]:
    method = entry.decoy_generation_method
    source_request = source.source_record.seed_gate.resolved_request
    decoy_request = replace(
        source_request,
        request_id=f"{entry.control_id}:decoy",
        request_candidate_identity_status=RequestCandidateIdentityStatus.NOT_ASSESSED,
    )
    if method is DecoyGenerationMethod.RT_SHIFT:
        owner_end_rt = _owner_value(source.owner_like, "owner_peak_end_rt")
        margin_sec = config.decoy_rt_owner_boundary_margin_sec
        shifted_rt = owner_end_rt + margin_sec / 60.0
        decoy_evidence = replace(source.seed_evidence, best_seed_rt=shifted_rt)
        return decoy_request, decoy_evidence, "best_seed_rt", margin_sec

    if method is DecoyGenerationMethod.MZ_SHIFT:
        identity = source_request.identity
        shifted_identity = replace(
            identity,
            precursor_mz=_shift_outside_ppm(
                float(identity.precursor_mz),
                float(identity.precursor_tolerance_ppm),
            ),
            product_mz=_shift_outside_ppm(
                float(identity.product_mz),
                float(identity.product_tolerance_ppm),
            ),
        )
        return (
            replace(decoy_request, identity=shifted_identity),
            source.seed_evidence,
            "precursor_mz;product_mz",
            "outside_tolerance",
        )

    if method is DecoyGenerationMethod.FRAGMENT_TAG_SHUFFLE:
        source_tags = tuple(source.seed_evidence.fragment_tags)
        decoy_tags = entry.decoy_fragment_tags or _default_decoy_tags(source_tags)
        identity = source_request.identity
        shifted_identity = replace(identity, fragment_tags=decoy_tags)
        return (
            replace(decoy_request, identity=shifted_identity),
            source.seed_evidence,
            "fragment_tags",
            format_fragment_tags(decoy_tags),
        )

    raise ValueError(f"unsupported decoy_generation_method: {method}")


def _owner_value(owner_like: object, field: str) -> float:
    value = getattr(owner_like, field, None)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be numeric")
    if not math.isfinite(value):
        raise ValueError(f"{field} must be finite")
    return float(value)


def _shift_outside_ppm(mz: float, tolerance_ppm: float) -> float:
    return mz * (1.0 + (tolerance_ppm + 1.0) / 1_000_000.0)


def _default_decoy_tags(source_tags: tuple[str, ...]) -> tuple[str, ...]:
    base = "identity_decoy_unmatched_tag"
    if base not in source_tags:
        return (base,)
    index = 2
    while f"{base}_{index}" in source_tags:
        index += 1
    return (f"{base}_{index}",)
```

Move the added imports into the top-level import block. Do not leave duplicate
or mid-file imports. `controls.py` intentionally uses a small Protocol for
`IdentityCoherenceOutputRecordLike` so it does not import `output.py`.

- [ ] **Step 4: Preserve the positive-margin invariant**

The coherent-decoy failure test disables the seed RT boundary gate through
`SeedGateConfig(require_seed_rt_inside_owner_peak=False)` while keeping a
positive decoy margin. Do not use a zero or negative RT-shift margin to exercise
that branch.

Do not add a production exception that allows nonpositive
`decoy_rt_owner_boundary_margin_sec`.

- [ ] **Step 5: Run tests**

Run:

```powershell
uv run pytest tests\alignment\identity_coherence\test_controls_evaluation.py -q
uv run ruff check xic_extractor\alignment\identity_coherence\controls.py tests\alignment\identity_coherence\test_controls_evaluation.py
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add xic_extractor\alignment\identity_coherence\controls.py tests\alignment\identity_coherence\test_controls_evaluation.py
git commit -m "feat: evaluate identity coherence decoys"
```

---

## Task 4: Batch Control Evaluation And Summary Rendering

**Files:**

- Modify: `xic_extractor/alignment/identity_coherence/controls.py`
- Modify: `xic_extractor/alignment/identity_coherence/output.py`
- Modify: `tests/alignment/identity_coherence/test_controls_evaluation.py`
- Modify: `tests/alignment/identity_coherence/test_output_writer.py`

- [ ] **Step 1: Add failing batch evaluation tests**

Append to `tests/alignment/identity_coherence/test_controls_evaluation.py`:

```python
def test_evaluate_identity_controls_preserves_manifest_order():
    positive = _positive_entry(control_id="CTRL-A")
    decoy = _decoy_entry(
        DecoyGenerationMethod.MZ_SHIFT,
        control_id="CTRL-B",
    )

    result = evaluate_identity_controls(
        (positive, decoy),
        records=(output_record(),),
        decoy_sources=(_decoy_source(),),
        config=IdentityControlsConfig(),
    )

    rows = result.rows
    assert [row["control_id"] for row in rows] == ["CTRL-A", "CTRL-B"]
    assert [row["control_pass"] for row in rows] == [True, True]
    assert result.positive_control_pass_fraction == 1.0
    assert result.positive_control_threshold_met is True
    assert result.decoy_coherent_seed_count == 0
    assert result.decoy_coherent_seed_threshold_met is True


def test_evaluate_identity_controls_reports_missing_decoy_source():
    decoy = _decoy_entry(DecoyGenerationMethod.MZ_SHIFT)

    result = evaluate_identity_controls(
        (decoy,),
        records=(output_record(),),
        decoy_sources=(),
        config=IdentityControlsConfig(),
    )

    rows = result.rows
    assert rows[0]["control_status"] == "unmapped"
    assert rows[0]["control_pass"] is False
    assert rows[0]["control_failure_reason"] == "missing_decoy_source"


def test_evaluate_identity_controls_flags_decoy_coherent_seed_threshold():
    decoy = _decoy_entry(
        DecoyGenerationMethod.RT_SHIFT,
        required_failure_reason_when_missed="seed_rt_outside_owner_peak",
    )
    source = _decoy_source()

    result = evaluate_identity_controls(
        (decoy,),
        records=(output_record(),),
        decoy_sources=(source,),
        config=IdentityControlsConfig(max_decoy_coherent_seed_count=0),
        seed_gate_config=SeedGateConfig(require_seed_rt_inside_owner_peak=False),
    )

    assert result.decoy_coherent_seed_count == 1
    assert result.decoy_coherent_seed_threshold_met is False
```

Merge `evaluate_identity_controls` into the existing top-level controls import
tuple instead of appending a new import in the middle of the test file.

- [ ] **Step 2: Add failing summary test**

Append to `tests/alignment/identity_coherence/test_output_writer.py`:

```python
def test_summary_renderer_reports_evaluated_identity_controls():
    record = output_record()
    markdown = render_identity_coherence_summary(
        [record],
        context=IdentityCoherenceOutputContext(
            command="identity-coherence",
            mode="inline_pre_backfill_diagnostic",
            input_source="pre_backfill",
            control_manifest_path="identity_coherence_controls_manifest.tsv",
        ),
        control_rows=(
            {
                "control_id": "CTRL-ISTD-1",
                "control_type": "positive_targeted_istd",
                "control_status": "assessed",
                "control_pass": True,
                "positive_control_mapping_status": "mapped",
                "decoy_generation_method": "",
                "control_failure_reason": "",
            },
            {
                "control_id": "CTRL-DECOY-1",
                "control_type": "identity_decoy",
                "control_status": "assessed",
                "control_pass": True,
                "positive_control_mapping_status": "not_applicable",
                "decoy_generation_method": "mz_shift",
                "control_failure_reason": "",
            },
        ),
    )

    assert "## Identity Controls" in markdown
    assert "| `positive_targeted_istd` | 1 |" in markdown
    assert "| `identity_decoy` | 1 |" in markdown
    assert "| `mapped` | 1 |" in markdown
    assert "| `mz_shift` | 1 |" in markdown
    assert "| positive_control_pass_fraction | 1 |" in markdown
    assert "| decoy_correctly_rejected_count | 1 |" in markdown
```

Also update the existing
`tests/alignment/identity_coherence/test_output_projection.py::test_project_control_row_is_pass_through_but_schema_limited`
fixture from `positive_identity_control` to `positive_targeted_istd`. The writer
is still pass-through, but tests should no longer advertise an obsolete control
type.

Also update the existing
`tests/alignment/identity_coherence/test_output_writer.py::test_summary_renderer_reports_control_rows_without_interpreting_them`
test into the evaluated-controls expectation above: remove assertions for
`## Controls Pass-Through`, replace `positive_identity_control` with
`positive_targeted_istd`, and assert the new `## Identity Controls` section.

- [ ] **Step 3: Run failing tests**

Run:

```powershell
uv run pytest tests\alignment\identity_coherence\test_controls_evaluation.py tests\alignment\identity_coherence\test_output_projection.py tests\alignment\identity_coherence\test_output_writer.py -q
```

Expected: FAIL for missing batch evaluator and old summary section text.

- [ ] **Step 4: Implement batch control evaluation**

Append to `controls.py`:

```python
@dataclass(frozen=True)
class IdentityControlEvaluationResult:
    rows: tuple[dict[str, object], ...]
    positive_control_pass_fraction: float | None
    positive_control_threshold_met: bool | None
    decoy_coherent_seed_count: int
    decoy_coherent_seed_threshold_met: bool


def evaluate_identity_controls(
    entries: Sequence[IdentityControlManifestEntry],
    *,
    records: Sequence[IdentityCoherenceOutputRecordLike],
    decoy_sources: Sequence[IdentityDecoySource],
    config: IdentityControlsConfig,
    seed_gate_config: SeedGateConfig = SeedGateConfig(),
) -> IdentityControlEvaluationResult:
    rows: list[dict[str, object]] = []
    for entry in entries:
        if entry.control_type is ControlType.POSITIVE_TARGETED_ISTD:
            rows.append(evaluate_positive_control(entry, records))
            continue
        source_status, source = _resolve_decoy_source(entry, decoy_sources)
        if source is None:
            failure_reason = (
                "ambiguous_mapping"
                if source_status is PositiveControlMappingStatus.AMBIGUOUS_MAPPING
                else "missing_decoy_source"
            )
            control_status = (
                ControlStatus.AMBIGUOUS_MAPPING
                if source_status is PositiveControlMappingStatus.AMBIGUOUS_MAPPING
                else ControlStatus.UNMAPPED
            )
            rows.append(
                _control_row(
                    entry,
                    control_status=control_status,
                    control_observed_behavior=failure_reason,
                    control_pass=False,
                    control_failure_reason=failure_reason,
                    positive_control_mapping_status=(
                        PositiveControlMappingStatus.NOT_APPLICABLE
                    ),
                    decoy_generation_method=entry.decoy_generation_method,
                )
            )
            continue
        rows.append(
            evaluate_identity_decoy(
                entry,
                source,
                config,
                seed_gate_config=seed_gate_config,
            )
        )
    row_tuple = tuple(rows)
    return IdentityControlEvaluationResult(
        rows=row_tuple,
        positive_control_pass_fraction=_positive_control_pass_fraction(row_tuple),
        positive_control_threshold_met=_positive_control_threshold_met(
            row_tuple,
            config,
        ),
        decoy_coherent_seed_count=_decoy_coherent_seed_count(row_tuple),
        decoy_coherent_seed_threshold_met=(
            _decoy_coherent_seed_count(row_tuple)
            <= config.max_decoy_coherent_seed_count
        ),
    )


def _resolve_decoy_source(
    entry: IdentityControlManifestEntry,
    decoy_sources: Sequence[IdentityDecoySource],
) -> tuple[PositiveControlMappingStatus, IdentityDecoySource | None]:
    if entry.decoy_source_request_id:
        matches = [
            source for source in decoy_sources
            if (
                source.source_record.seed_gate.resolved_request.request_id
                == entry.decoy_source_request_id
            )
        ]
        if len(matches) == 1:
            return PositiveControlMappingStatus.MAPPED, matches[0]
        if len(matches) > 1:
            return PositiveControlMappingStatus.AMBIGUOUS_MAPPING, None
    supplied = _record_match_constraints(entry)
    if not supplied:
        return PositiveControlMappingStatus.UNMAPPED, None
    matches = [
        source for source in decoy_sources
        if all(
            _record_value(source.source_record, field) == value
            for field, value in supplied
        )
    ]
    if len(matches) == 1:
        return PositiveControlMappingStatus.MAPPED, matches[0]
    if len(matches) > 1:
        return PositiveControlMappingStatus.AMBIGUOUS_MAPPING, None
    partial_fields = {
        field for field, value in supplied
        if any(
            _record_value(source.source_record, field) == value
            for source in decoy_sources
        )
    }
    if partial_fields:
        return PositiveControlMappingStatus.AMBIGUOUS_MAPPING, None
    return PositiveControlMappingStatus.UNMAPPED, None


def _positive_control_pass_fraction(
    rows: Sequence[Mapping[str, object]],
) -> float | None:
    positive_rows = [
        row for row in rows
        if _enum_value(row.get("control_type")) == "positive_targeted_istd"
    ]
    if not positive_rows:
        return None
    pass_count = sum(
        1 for row in positive_rows
        if row.get("control_pass") is True
    )
    return pass_count / len(positive_rows)


def _positive_control_threshold_met(
    rows: Sequence[Mapping[str, object]],
    config: IdentityControlsConfig,
) -> bool | None:
    fraction = _positive_control_pass_fraction(rows)
    if fraction is None:
        return None
    return fraction >= config.positive_control_min_pass_fraction


def _decoy_coherent_seed_count(rows: Sequence[Mapping[str, object]]) -> int:
    return sum(
        1 for row in rows
        if row.get("control_failure_reason") == "decoy_seed_gate_coherent"
    )
```

- [ ] **Step 5: Upgrade summary controls section**

In `output.py`, replace the existing `"## Controls Pass-Through"` block in
`render_identity_coherence_summary()` from the `lines.extend([...])` call through
the two pass-through `_counter_table(...)` calls with:

```python
    positive_rows = [
        row for row in control_rows
        if str(row.get("control_type", "")) == "positive_targeted_istd"
    ]
    positive_pass_count = sum(
        1 for row in positive_rows
        if row.get("control_pass") is True
    )
    positive_fraction = (
        "not_assessed"
        if not positive_rows
        else f"{positive_pass_count / len(positive_rows):.12g}"
    )
    decoy_rows = [
        row for row in control_rows
        if str(row.get("control_type", "")) == "identity_decoy"
    ]
    decoy_correctly_rejected_count = sum(
        1 for row in decoy_rows
        if row.get("control_pass") is True
    )
    lines.extend(
        [
            "",
            "## Identity Controls",
            "",
            (
                "Control fields validate identity diagnostic behavior only; they "
                "do not promote identities or filter the final matrix."
            ),
            "",
        ]
    )
    lines.extend(
        _counter_table(
            Counter(str(row.get("control_type", "")) for row in control_rows),
            "control_type",
        )
    )
    lines.extend(
        _counter_table(
            Counter(str(row.get("control_status", "")) for row in control_rows),
            "control_status",
        )
    )
    lines.extend(
        _counter_table(
            Counter(
                _format_tsv_value(row.get("control_pass"))
                for row in control_rows
            ),
            "control_pass",
        )
    )
    lines.extend(
        _counter_table(
            Counter(
                str(row.get("positive_control_mapping_status", ""))
                for row in control_rows
            ),
            "positive_control_mapping_status",
        )
    )
    lines.extend(
        _counter_table(
            Counter(
                str(row.get("decoy_generation_method", ""))
                for row in decoy_rows
            ),
            "decoy_generation_method",
        )
    )
    lines.extend(
        _counter_table(
            Counter(
                str(row.get("control_failure_reason", ""))
                for row in control_rows
                if str(row.get("control_failure_reason", ""))
            ),
            "control_failure_reason",
        )
    )
    lines.extend(
        [
            "| Metric | Value |",
            "| --- | ---: |",
            f"| positive_control_pass_fraction | {positive_fraction} |",
            f"| decoy_correctly_rejected_count | {decoy_correctly_rejected_count} |",
            "",
        ]
    )
```

Keep the later writer-contract row, but update it from:

```python
"| controls | pass-through only; evaluation belongs to a later controls slice |"
```

to:

```python
"| controls | evaluated rows are rendered; identity decisions remain immutable |"
```

- [ ] **Step 6: Run tests**

Run:

```powershell
uv run pytest tests\alignment\identity_coherence\test_controls_evaluation.py tests\alignment\identity_coherence\test_output_projection.py tests\alignment\identity_coherence\test_output_writer.py -q
uv run ruff check xic_extractor\alignment\identity_coherence\controls.py xic_extractor\alignment\identity_coherence\output.py tests\alignment\identity_coherence\test_controls_evaluation.py tests\alignment\identity_coherence\test_output_projection.py tests\alignment\identity_coherence\test_output_writer.py
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add xic_extractor\alignment\identity_coherence\controls.py xic_extractor\alignment\identity_coherence\output.py tests\alignment\identity_coherence\test_controls_evaluation.py tests\alignment\identity_coherence\test_output_projection.py tests\alignment\identity_coherence\test_output_writer.py
git commit -m "feat: summarize identity coherence controls"
```

---

## Task 5: Facade Exports And Boundary Tests

**Files:**

- Modify: `xic_extractor/alignment/identity_coherence/__init__.py`
- Modify: `tests/alignment/identity_coherence/test_schema_contract.py`

- [ ] **Step 1: Add failing facade and boundary tests**

Append to `tests/alignment/identity_coherence/test_schema_contract.py`:

```python
def test_identity_coherence_facade_exports_controls_surface():
    import xic_extractor.alignment.identity_coherence as identity_coherence

    assert identity_coherence.ControlType is not None
    assert identity_coherence.ControlStatus is not None
    assert identity_coherence.DecoyGenerationMethod is not None
    assert identity_coherence.PositiveControlMappingStatus is not None
    assert identity_coherence.IdentityControlEvaluationResult is not None
    assert identity_coherence.IdentityControlManifestEntry is not None
    assert identity_coherence.IdentityControlsConfig is not None
    assert identity_coherence.IdentityDecoySource is not None
    assert identity_coherence.read_identity_controls_manifest is not None
    assert identity_coherence.evaluate_positive_control is not None
    assert identity_coherence.evaluate_identity_decoy is not None
    assert identity_coherence.evaluate_identity_controls is not None


def test_domain_modules_do_not_import_controls_or_output_surfaces():
    from pathlib import Path

    package_dir = Path("xic_extractor/alignment/identity_coherence")
    forbidden_snippets = (
        "from .controls import",
        "from . import controls",
        "from .output import",
        "from . import output",
        "identity_coherence.controls",
        "identity_coherence.output",
    )
    domain_modules = (
        "candidate_matcher.py",
        "cell_evidence.py",
        "decision.py",
        "models.py",
        "request_builder.py",
        "row_evaluator.py",
        "rt_center.py",
        "schema.py",
        "seed_gate.py",
        "shape.py",
        "tags.py",
        "width.py",
    )

    violations = []
    for module_name in domain_modules:
        text = (package_dir / module_name).read_text(encoding="utf-8")
        for snippet in forbidden_snippets:
            if snippet in text:
                violations.append(f"{module_name}: {snippet}")

    assert violations == []
```

- [ ] **Step 2: Run failing test**

Run:

```powershell
uv run pytest tests\alignment\identity_coherence\test_schema_contract.py::test_identity_coherence_facade_exports_controls_surface tests\alignment\identity_coherence\test_schema_contract.py::test_domain_modules_do_not_import_controls_or_output_surfaces -q
```

Expected: facade export test FAILS.

- [ ] **Step 3: Export controls surface**

Modify `xic_extractor/alignment/identity_coherence/__init__.py`.

Add imports:

```python
from .controls import (
    IdentityControlEvaluationResult,
    IdentityControlManifestEntry,
    IdentityControlsConfig,
    IdentityDecoySource,
    evaluate_identity_controls,
    evaluate_identity_decoy,
    evaluate_positive_control,
    read_identity_controls_manifest,
    read_identity_controls_manifest_tsv,
)
```

Add schema imports:

```python
    ControlStatus,
    ControlType,
    DecoyGenerationMethod,
    PositiveControlMappingStatus,
```

Add the same names to `__all__`.

- [ ] **Step 4: Run schema contract tests**

Run:

```powershell
uv run pytest tests\alignment\identity_coherence\test_schema_contract.py -q
uv run ruff check xic_extractor\alignment\identity_coherence\__init__.py tests\alignment\identity_coherence\test_schema_contract.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor\alignment\identity_coherence\__init__.py tests\alignment\identity_coherence\test_schema_contract.py
git commit -m "feat: expose identity coherence controls facade"
```

---

## Task 6: Verification, Scope Guard, And Review Notes

**Files:**

- Modify only if needed: files already touched in Tasks 1-5.

This task verifies the unit-level evaluator and writer surface only. It does
not validate 8RAW `controls.tsv` production or real-run interpretation, because
pipeline/CLI wiring and real pre-Backfill decoy-source extraction are out of
scope for this slice. Do not describe the completed slice as an 8RAW controls
validation until a later diagnostic harness consumes actual run artifacts.

- [ ] **Step 1: Run controls-focused tests**

Run:

```powershell
uv run pytest tests\alignment\identity_coherence\test_controls_manifest.py tests\alignment\identity_coherence\test_controls_evaluation.py -q
```

Expected: PASS.

- [ ] **Step 2: Run identity coherence test suite**

Run:

```powershell
uv run pytest tests\alignment\identity_coherence -q
```

Expected: PASS.

- [ ] **Step 3: Run lint**

Run:

```powershell
uv run ruff check xic_extractor\alignment\identity_coherence tests\alignment\identity_coherence tests\test_run_extraction.py
```

Expected: PASS.

- [ ] **Step 4: Run broad test suite if practical**

Run:

```powershell
uv run pytest --tb=short -q
```

Expected: PASS. If Windows sandbox process spawning fails with `PermissionError: [WinError 5]` in `tests/test_parallel_execution.py`, rerun the same command outside the sandbox using the standard escalation path and report both results.

- [ ] **Step 5: Scope guard**

Run:

```powershell
git diff --name-only <base_commit_before_task1>..HEAD
```

Expected changed files are limited to:

```text
tests/alignment/identity_coherence/test_controls_manifest.py
tests/alignment/identity_coherence/test_controls_evaluation.py
tests/alignment/identity_coherence/test_output_writer.py
tests/alignment/identity_coherence/test_output_projection.py
tests/alignment/identity_coherence/test_schema_contract.py
xic_extractor/alignment/identity_coherence/__init__.py
xic_extractor/alignment/identity_coherence/controls.py
xic_extractor/alignment/identity_coherence/output.py
xic_extractor/alignment/identity_coherence/schema.py
```

If any of these appear, stop and explain before committing:

```text
xic_extractor/alignment/backfill.py
xic_extractor/alignment/owner_backfill.py
xic_extractor/alignment/pipeline.py
xic_extractor/extraction/
xic_extractor/output/
scripts/
```

- [ ] **Step 6: Final commit if Task 6 produced cleanup changes**

If Task 6 required cleanup edits:

```powershell
git add tests\alignment\identity_coherence\test_controls_manifest.py tests\alignment\identity_coherence\test_controls_evaluation.py tests\alignment\identity_coherence\test_output_projection.py tests\alignment\identity_coherence\test_output_writer.py tests\alignment\identity_coherence\test_schema_contract.py
git add xic_extractor\alignment\identity_coherence\__init__.py xic_extractor\alignment\identity_coherence\controls.py xic_extractor\alignment\identity_coherence\output.py xic_extractor\alignment\identity_coherence\schema.py
git commit -m "fix: verify identity coherence controls slice"
```

If no cleanup edits were required, do not create an empty commit.

---

## Self-Review Checklist

- [ ] Controls remain validation-only and cannot mutate decisions or final matrices.
- [ ] Positive-control labels are not read by seed gate, cell evidence, row evaluator, or decision logic.
- [ ] Positive controls require both strict row mapping and mapping evidence within manifest mz/RT tolerances.
- [ ] Identity decoys fail before cross-sample promotion in this slice.
- [ ] Identity decoy sources are rejected before seed-gate evaluation when they are not pre-Backfill, primary, and non-duplicate.
- [ ] `rt_shift` uses seconds-to-minutes conversion when adding the margin to owner RT.
- [ ] Background/blank/QC controls are rejected from identity controls.
- [ ] YAML is explicitly unsupported in this slice with a clear error.
- [ ] Domain modules do not import `controls.py` or `output.py`.
- [ ] No RAW/XIC retrieval, Backfill, CLI, workbook, report, or final-matrix files changed.
- [ ] The slice is not presented as real 8RAW controls validation.
- [ ] `controls.tsv` columns still match `IDENTITY_COHERENCE_CONTROL_COLUMNS`.
- [ ] Summary control counters are derived from supplied control rows only.
