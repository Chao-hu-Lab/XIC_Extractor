"""Write shared peak identity explanation and shadow-label diagnostics."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

from xic_extractor.alignment.shared_peak_identity_explanation import (
    candidate_ms2_pattern,
    machine_evidence_support,
)
from xic_extractor.alignment.shared_peak_identity_explanation.assembler import (
    assemble_evidence_vectors,
)
from xic_extractor.alignment.shared_peak_identity_explanation.blast_radius import (
    CELLS_REQUIRED_FIELDS,
    OPTIONAL_ARTIFACT_ROLES,
    REVIEW_REQUIRED_FIELDS,
    build_blast_radius_manifest,
    build_blast_radius_summary,
    build_class_profiles,
    preflight_tsv_artifact,
)
from xic_extractor.alignment.shared_peak_identity_explanation.classifier import (
    build_slice0_run_facts,
    build_slice1_run_facts,
    classify_explanations,
)
from xic_extractor.alignment.shared_peak_identity_explanation.machine_artifacts import (
    MachineMatch,
    load_machine_matches,
)
from xic_extractor.alignment.shared_peak_identity_explanation.oracle import (
    load_manual_oracle,
    oracle_rows_as_dicts,
)
from xic_extractor.alignment.shared_peak_identity_explanation.shadow_labels import (
    build_shadow_alignment_summary,
    build_shadow_label_rows,
    build_v2_readiness,
)
from xic_extractor.alignment.shared_peak_identity_explanation.writers import (
    write_slice0_outputs,
    write_slice1_outputs,
    write_v2_outputs,
)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        outputs = run_explanation(
            manual_oracle_tsv=args.manual_oracle_tsv,
            alignment_review_tsv=args.alignment_review_tsv,
            alignment_cells_tsv=args.alignment_cells_tsv,
            output_dir=args.output_dir,
            candidate_gate_tsv=args.candidate_gate_tsv,
            enable_blast_radius=args.enable_blast_radius,
            blast_radius_preflight_only=args.blast_radius_preflight_only,
            blast_radius_sample_row_limit=args.blast_radius_sample_row_limit,
            blast_radius_8raw_run=args.blast_radius_8raw_run,
            blast_radius_85raw_run=args.blast_radius_85raw_run,
            expected_blast_radius_manifest=args.expected_blast_radius_manifest,
            optional_blast_radius_artifacts=args.optional_blast_radius_artifact,
            enable_shadow_label_alignment=args.enable_shadow_label_alignment,
            cwt_shape_evidence_tsv=args.cwt_shape_evidence_tsv,
            tier2_trace_evidence_tsv=args.tier2_trace_evidence_tsv,
            candidate_ms2_pattern_evidence_tsv=(
                args.candidate_ms2_pattern_evidence_tsv
            ),
            candidate_ms2_pattern_batch_index=args.candidate_ms2_pattern_batch_index,
            candidate_ms2_pattern_raw_dll_dir=(
                args.candidate_ms2_pattern_raw_dll_dir
            ),
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    for label, path in outputs.items():
        print(f"{label}: {path}")
    return 0


def run_explanation(
    *,
    manual_oracle_tsv: Path,
    alignment_review_tsv: Path,
    alignment_cells_tsv: Path,
    output_dir: Path,
    candidate_gate_tsv: Path | None = None,
    enable_blast_radius: bool = False,
    blast_radius_preflight_only: bool = False,
    blast_radius_sample_row_limit: int = 1000,
    blast_radius_8raw_run: Path | None = None,
    blast_radius_85raw_run: Path | None = None,
    expected_blast_radius_manifest: Path | None = None,
    optional_blast_radius_artifacts: Sequence[str] | None = None,
    enable_shadow_label_alignment: bool = False,
    cwt_shape_evidence_tsv: Path | None = None,
    tier2_trace_evidence_tsv: Path | None = None,
    candidate_ms2_pattern_evidence_tsv: Path | None = None,
    candidate_ms2_pattern_batch_index: Path | None = None,
    candidate_ms2_pattern_raw_dll_dir: Path | None = None,
) -> Mapping[str, Path | str]:
    optional_artifacts = _parse_optional_blast_radius_artifacts(
        optional_blast_radius_artifacts
    )
    if enable_blast_radius and (
        blast_radius_8raw_run is None or blast_radius_85raw_run is None
    ):
        raise ValueError(
            "--enable-blast-radius requires --blast-radius-8raw-run and "
            "--blast-radius-85raw-run"
        )
    if blast_radius_preflight_only and not enable_blast_radius:
        raise ValueError("--blast-radius-preflight-only requires --enable-blast-radius")
    if blast_radius_sample_row_limit < 0:
        raise ValueError("--blast-radius-sample-row-limit must be non-negative")
    if candidate_ms2_pattern_evidence_tsv and candidate_ms2_pattern_batch_index:
        raise ValueError(
            "use either --candidate-ms2-pattern-evidence-tsv or "
            "--candidate-ms2-pattern-batch-index, not both"
        )
    if candidate_ms2_pattern_batch_index and not enable_shadow_label_alignment:
        raise ValueError(
            "--candidate-ms2-pattern-batch-index requires "
            "--enable-shadow-label-alignment"
        )
    if candidate_ms2_pattern_raw_dll_dir and not candidate_ms2_pattern_batch_index:
        raise ValueError(
            "--candidate-ms2-pattern-raw-dll-dir requires "
            "--candidate-ms2-pattern-batch-index"
        )
    if blast_radius_preflight_only:
        if blast_radius_8raw_run is None or blast_radius_85raw_run is None:
            raise AssertionError("blast-radius run paths were validated above")
        return _preflight_blast_radius_inputs(
            eight_raw_run_dir=blast_radius_8raw_run,
            eightyfive_raw_run_dir=blast_radius_85raw_run,
            sample_row_limit=blast_radius_sample_row_limit,
        )

    oracle_rows = load_manual_oracle(manual_oracle_tsv)
    matches = load_machine_matches(
        oracle_rows=oracle_rows,
        alignment_review_tsv=alignment_review_tsv,
        alignment_cells_tsv=alignment_cells_tsv,
        candidate_gate_tsv=candidate_gate_tsv,
    )
    cwt_shape_evidence = machine_evidence_support.load_cwt_shape_evidence(
        cwt_shape_evidence_tsv
    )
    tier2_trace_evidence = machine_evidence_support.load_tier2_trace_evidence(
        tier2_trace_evidence_tsv
    )
    generated_candidate_ms2_outputs: dict[str, Path] = {}
    if candidate_ms2_pattern_batch_index is not None:
        generated_candidate_ms2_path = (
            output_dir / "shared_peak_identity_candidate_ms2_pattern_evidence.tsv"
        )
        candidate_ms2_pattern.write_candidate_ms2_pattern_rows(
            generated_candidate_ms2_path,
            candidate_ms2_pattern.build_candidate_ms2_pattern_rows(
                alignment_cells_tsv=alignment_cells_tsv,
                alignment_review_tsv=alignment_review_tsv,
                discovery_batch_index_csv=candidate_ms2_pattern_batch_index,
                raw_dll_dir=candidate_ms2_pattern_raw_dll_dir,
                oracle_keys=(
                    (row.feature_family_id, row.sample_id)
                    for row in oracle_rows
                    if not row.is_sentinel
                ),
            ),
        )
        candidate_ms2_pattern_evidence_tsv = generated_candidate_ms2_path
        generated_candidate_ms2_outputs["candidate_ms2_pattern_evidence"] = (
            generated_candidate_ms2_path
        )
    candidate_ms2_pattern_evidence = (
        machine_evidence_support.load_candidate_ms2_pattern_evidence(
            candidate_ms2_pattern_evidence_tsv
        )
    )
    evidence_rows = assemble_evidence_vectors(oracle_rows, matches)
    explanations = classify_explanations(oracle_rows, evidence_rows)
    run_facts = build_slice0_run_facts(
        explanations,
        durable_oracle_path=manual_oracle_tsv,
    )
    slice0_outputs = write_slice0_outputs(
        output_dir=output_dir,
        durable_oracle_path=manual_oracle_tsv,
        oracle_rows=oracle_rows_as_dicts(oracle_rows),
        evidence_rows=evidence_rows,
        explanation_rows=explanations,
        run_facts=run_facts,
    )
    if not enable_blast_radius:
        if enable_shadow_label_alignment:
            return _write_v2_from_current_outputs(
                output_dir=output_dir,
                prior_outputs=slice0_outputs,
                explanations=explanations,
                run_facts=run_facts,
                machine_matches=matches,
                cwt_shape_evidence=cwt_shape_evidence,
                tier2_trace_evidence=tier2_trace_evidence,
                candidate_ms2_pattern_evidence=candidate_ms2_pattern_evidence,
                extra_outputs=generated_candidate_ms2_outputs,
            )
        return slice0_outputs

    if blast_radius_8raw_run is None or blast_radius_85raw_run is None:
        raise AssertionError("blast-radius run paths were validated above")

    manifest_rows = build_blast_radius_manifest(
        manual_oracle_tsv=manual_oracle_tsv,
        slice0_explanations_tsv=slice0_outputs["explanations"],
        slice0_evidence_vectors_tsv=slice0_outputs["evidence_vectors"],
        eight_raw_run_dir=blast_radius_8raw_run,
        eightyfive_raw_run_dir=blast_radius_85raw_run,
        expected_manifest_tsv=expected_blast_radius_manifest,
        optional_artifacts=optional_artifacts,
    )
    summary_rows = build_blast_radius_summary(
        class_profiles=build_class_profiles(explanations, evidence_rows),
        manifest_rows=manifest_rows,
        eight_raw_run_dir=blast_radius_8raw_run,
        eightyfive_raw_run_dir=blast_radius_85raw_run,
    )
    slice1_run_facts = build_slice1_run_facts(
        slice0_run_facts=run_facts,
        manifest_rows=manifest_rows,
        summary_rows=summary_rows,
    )
    slice1_outputs = write_slice1_outputs(
        output_dir=output_dir,
        slice0_outputs=slice0_outputs,
        manifest_rows=manifest_rows,
        summary_rows=summary_rows,
        run_facts=slice1_run_facts,
    )
    if enable_shadow_label_alignment:
        return _write_v2_from_current_outputs(
            output_dir=output_dir,
            prior_outputs=slice1_outputs,
            explanations=explanations,
            run_facts=slice1_run_facts,
            machine_matches=matches,
            cwt_shape_evidence=cwt_shape_evidence,
            tier2_trace_evidence=tier2_trace_evidence,
            candidate_ms2_pattern_evidence=candidate_ms2_pattern_evidence,
            extra_outputs=generated_candidate_ms2_outputs,
        )
    return slice1_outputs


def _write_v2_from_current_outputs(
    *,
    output_dir: Path,
    prior_outputs: Mapping[str, Path],
    explanations: Sequence[Mapping[str, str]],
    run_facts: Mapping[str, str],
    machine_matches: Mapping[str, Sequence[MachineMatch]],
    cwt_shape_evidence: Mapping[tuple[str, str], Mapping[str, str]],
    tier2_trace_evidence: Mapping[str, Mapping[str, str]],
    candidate_ms2_pattern_evidence: Mapping[tuple[str, str], Mapping[str, str]],
    extra_outputs: Mapping[str, Path] | None = None,
) -> Mapping[str, Path | str]:
    shadow_rows = build_shadow_label_rows(explanations)
    shadow_summary_rows = build_shadow_alignment_summary(shadow_rows)
    machine_evidence_support_rows = (
        machine_evidence_support.build_machine_evidence_support_rows(
            explanations=explanations,
            shadow_rows=shadow_rows,
            machine_matches=machine_matches,
            cwt_shape_evidence=cwt_shape_evidence,
            tier2_trace_evidence=tier2_trace_evidence,
            candidate_ms2_pattern_evidence=candidate_ms2_pattern_evidence,
        )
    )
    readiness_row = build_v2_readiness(
        run_facts=run_facts,
        shadow_rows=shadow_rows,
        machine_evidence_support_rows=machine_evidence_support_rows,
    )
    return write_v2_outputs(
        output_dir=output_dir,
        prior_outputs={**dict(prior_outputs), **dict(extra_outputs or {})},
        shadow_rows=shadow_rows,
        summary_rows=shadow_summary_rows,
        readiness_row=readiness_row,
        machine_evidence_support_rows=machine_evidence_support_rows,
    )


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manual-oracle-tsv", type=Path, required=True)
    parser.add_argument("--alignment-review-tsv", type=Path, required=True)
    parser.add_argument("--alignment-cells-tsv", type=Path, required=True)
    parser.add_argument("--candidate-gate-tsv", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--enable-blast-radius", action="store_true")
    parser.add_argument("--blast-radius-preflight-only", action="store_true")
    parser.add_argument("--blast-radius-sample-row-limit", type=int, default=1000)
    parser.add_argument("--blast-radius-8raw-run", type=Path)
    parser.add_argument("--blast-radius-85raw-run", type=Path)
    parser.add_argument("--expected-blast-radius-manifest", type=Path)
    parser.add_argument("--enable-shadow-label-alignment", action="store_true")
    parser.add_argument("--cwt-shape-evidence-tsv", type=Path)
    parser.add_argument("--tier2-trace-evidence-tsv", type=Path)
    parser.add_argument("--candidate-ms2-pattern-evidence-tsv", type=Path)
    parser.add_argument("--candidate-ms2-pattern-batch-index", type=Path)
    parser.add_argument("--candidate-ms2-pattern-raw-dll-dir", type=Path)
    parser.add_argument(
        "--optional-blast-radius-artifact",
        action="append",
        default=[],
        metavar="ROLE=PATH",
    )
    return parser.parse_args(argv)


def _parse_optional_blast_radius_artifacts(
    values: Sequence[str] | None,
) -> dict[str, Path]:
    artifacts: dict[str, Path] = {}
    for value in values or ():
        if "=" not in value:
            raise ValueError("--optional-blast-radius-artifact requires ROLE=PATH")
        role, path_text = value.split("=", 1)
        if not role or not path_text:
            raise ValueError("--optional-blast-radius-artifact requires ROLE=PATH")
        if role in artifacts:
            raise ValueError(f"duplicate optional blast-radius role: {role}")
        if role not in OPTIONAL_ARTIFACT_ROLES:
            raise ValueError(f"unknown optional blast-radius artifact role: {role}")
        artifacts[role] = Path(path_text)
    return artifacts


def _preflight_blast_radius_inputs(
    *,
    eight_raw_run_dir: Path,
    eightyfive_raw_run_dir: Path,
    sample_row_limit: int,
) -> dict[str, str]:
    artifacts = {
        "8raw_alignment_review": (
            eight_raw_run_dir / "alignment_review.tsv",
            REVIEW_REQUIRED_FIELDS,
        ),
        "8raw_alignment_cells": (
            eight_raw_run_dir / "alignment_cells.tsv",
            CELLS_REQUIRED_FIELDS,
        ),
        "85raw_alignment_review": (
            eightyfive_raw_run_dir / "alignment_review.tsv",
            REVIEW_REQUIRED_FIELDS,
        ),
        "85raw_alignment_cells": (
            eightyfive_raw_run_dir / "alignment_cells.tsv",
            CELLS_REQUIRED_FIELDS,
        ),
    }
    results: dict[str, str] = {}
    for artifact_id, (path, required_fields) in artifacts.items():
        inspection = _preflight_one_artifact(
            path,
            required_fields=required_fields,
            sample_row_limit=sample_row_limit,
        )
        for field in (
            "artifact_status",
            "row_count",
            "sample_count",
            "family_count",
            "missing_required_fields",
        ):
            results[f"preflight_{artifact_id}_{field}"] = inspection[field]
    return results


def _preflight_one_artifact(
    path: Path,
    *,
    required_fields: frozenset[str],
    sample_row_limit: int,
) -> Mapping[str, str]:
    if not path.exists():
        return {
            "artifact_status": "missing",
            "row_count": "0",
            "sample_count": "0",
            "family_count": "0",
            "available_required_fields": "",
            "missing_required_fields": ";".join(sorted(required_fields)),
        }
    return preflight_tsv_artifact(
        path,
        required_fields=required_fields,
        sample_row_limit=sample_row_limit,
    )


if __name__ == "__main__":
    raise SystemExit(main())
