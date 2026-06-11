"""Apply shared peak identity activation sidecars to alignment TSV copies."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from xic_extractor.alignment.backfill_evidence_projection import (
    load_candidate_ms2_pattern_rows,
    load_matrix_rt_drift_policy_rows,
    load_ms1_pattern_coherence_rows,
    load_qc_ms1_pattern_reference_rows,
)
from xic_extractor.alignment.shared_peak_identity_explanation import (
    machine_evidence_support,
    product_activation,
)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        if args.matrix_only:
            if args.activation_values_tsv is None:
                raise ValueError(
                    "--activation-values-tsv is required with --matrix-only"
                )
            if args.alignment_matrix_identity_tsv is None:
                raise ValueError(
                    "--alignment-matrix-identity-tsv is required with "
                    "--matrix-only"
                )
            rt_mode_evidence_rows = tuple(
                machine_evidence_support.load_rt_mode_evidence(
                    args.rt_mode_evidence_tsv
                ).values()
            )
            matrix_outputs = (
                product_activation.apply_activation_to_alignment_matrix_outputs(
                    activation_decisions_tsv=args.activation_decisions_tsv,
                    activation_acceptance_tsv=args.activation_acceptance_tsv,
                    activation_values_tsv=args.activation_values_tsv,
                    alignment_matrix_tsv=args.alignment_matrix_tsv,
                    alignment_matrix_identity_tsv=args.alignment_matrix_identity_tsv,
                    alignment_review_tsv=args.alignment_review_tsv,
                    output_dir=args.output_dir,
                    require_acceptance_pass=not args.allow_non_passing_acceptance,
                    allow_overwrite_source=args.allow_overwrite_source,
                    rt_mode_evidence_rows=rt_mode_evidence_rows,
                )
            )
            print(f"Activated matrix TSV: {matrix_outputs.matrix_tsv}")
            print(f"Activation application summary TSV: {matrix_outputs.summary_tsv}")
            print(f"Activation value delta TSV: {matrix_outputs.value_delta_tsv}")
            print(
                "Activation hypothesis identity TSV: "
                f"{matrix_outputs.hypothesis_identity_tsv}"
            )
            print(
                f"Alignment matrix identity TSV: {matrix_outputs.matrix_identity_tsv}"
            )
            return 0
        if args.alignment_cells_tsv is None:
            raise ValueError("--alignment-cells-tsv is required unless --matrix-only")
        candidate_ms2_pattern_rows = load_candidate_ms2_pattern_rows(
            args.candidate_ms2_pattern_evidence_tsv
        )
        ms1_pattern_coherence_rows = load_ms1_pattern_coherence_rows(
            args.ms1_pattern_coherence_evidence_tsv
        )
        qc_ms1_pattern_reference_rows = load_qc_ms1_pattern_reference_rows(
            args.qc_ms1_pattern_reference_evidence_tsv
        )
        matrix_rt_drift_policy_rows = load_matrix_rt_drift_policy_rows(
            args.matrix_rt_drift_policy_tsv
        )
        rt_mode_evidence_rows = tuple(
            machine_evidence_support.load_rt_mode_evidence(
                args.rt_mode_evidence_tsv
            ).values()
        )
        outputs = product_activation.apply_activation_to_alignment_outputs(
            activation_decisions_tsv=args.activation_decisions_tsv,
            activation_acceptance_tsv=args.activation_acceptance_tsv,
            alignment_matrix_tsv=args.alignment_matrix_tsv,
            alignment_matrix_identity_tsv=args.alignment_matrix_identity_tsv,
            alignment_review_tsv=args.alignment_review_tsv,
            alignment_cells_tsv=args.alignment_cells_tsv,
            output_dir=args.output_dir,
            require_acceptance_pass=not args.allow_non_passing_acceptance,
            output_mode=args.output_mode,
            allow_overwrite_source=args.allow_overwrite_source,
            legacy_rt_row_oracle_xlsx=args.legacy_rt_row_oracle_xlsx,
            legacy_rt_row_oracle_mz_ppm=args.legacy_rt_row_oracle_mz_ppm,
            legacy_rt_row_oracle_rt_tolerance_min=(
                args.legacy_rt_row_oracle_rt_tolerance_min
            ),
            require_complete_peak_hypothesis_identity=(
                args.require_complete_peak_hypothesis_identity
            ),
            exclude_family_projections=args.exclude_family_projections,
            candidate_ms2_pattern_rows=candidate_ms2_pattern_rows,
            ms1_pattern_coherence_rows=ms1_pattern_coherence_rows,
            qc_ms1_pattern_reference_rows=qc_ms1_pattern_reference_rows,
            matrix_rt_drift_policy_rows=matrix_rt_drift_policy_rows,
            rt_mode_evidence_rows=rt_mode_evidence_rows,
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Activated matrix TSV: {outputs.matrix_tsv}")
    print(f"Activated review TSV: {outputs.review_tsv}")
    print(f"Activated cells TSV: {outputs.cells_tsv}")
    print(f"Activation application summary TSV: {outputs.summary_tsv}")
    print(f"Activation value delta TSV: {outputs.value_delta_tsv}")
    if outputs.hypothesis_identity_tsv is not None:
        print(f"Activation hypothesis identity TSV: {outputs.hypothesis_identity_tsv}")
    if outputs.matrix_identity_tsv is not None:
        print(f"Alignment matrix identity TSV: {outputs.matrix_identity_tsv}")
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activation-decisions-tsv", type=Path, required=True)
    parser.add_argument("--activation-acceptance-tsv", type=Path, required=True)
    parser.add_argument("--alignment-matrix-tsv", type=Path, required=True)
    parser.add_argument(
        "--alignment-matrix-identity-tsv",
        type=Path,
        help=(
            "Required when --alignment-matrix-tsv is a public Mz/RT/sample "
            "matrix without feature_family_id. Provides peak_hypothesis_id and "
            "source family provenance for product application."
        ),
    )
    parser.add_argument("--alignment-review-tsv", type=Path, required=True)
    parser.add_argument("--alignment-cells-tsv", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--matrix-only",
        action="store_true",
        help=(
            "Apply accepted activation values to the product matrix and "
            "PeakHypothesis identity sidecars without reading or writing "
            "alignment_cells.tsv or alignment_review.tsv outputs."
        ),
    )
    parser.add_argument(
        "--activation-values-tsv",
        type=Path,
        help=(
            "Required with --matrix-only. Product-authorized activation values "
            "keyed by peak_hypothesis_id and sample_stem."
        ),
    )
    parser.add_argument(
        "--candidate-ms2-pattern-evidence-tsv",
        type=Path,
        help=(
            "Optional product-authorized Candidate MS2 pattern sidecar from "
            "authorize_backfill_candidate_ms2_pattern_evidence.py. Raw "
            "diagnostic sidecars remain review-only and fail closed."
        ),
    )
    parser.add_argument(
        "--ms1-pattern-coherence-evidence-tsv",
        type=Path,
        help=(
            "Optional product-authorized MS1 pattern coherence sidecar from "
            "authorize_backfill_ms1_pattern_evidence.py. Raw diagnostic "
            "sidecars remain review-only and fail closed."
        ),
    )
    parser.add_argument(
        "--qc-ms1-pattern-reference-evidence-tsv",
        type=Path,
        help=(
            "Optional typed QC MS1 pattern reference sidecar. When provided, "
            "rescued alignment cells receive backfill QC projection fields."
        ),
    )
    parser.add_argument(
        "--matrix-rt-drift-policy-tsv",
        type=Path,
        help=(
            "Optional typed matrix RT drift policy sidecar. When provided, "
            "rescued alignment cells receive backfill RT-drift projection fields."
        ),
    )
    parser.add_argument(
        "--rt-mode-evidence-tsv",
        type=Path,
        help=(
            "Optional shared_peak_identity_rt_mode_evidence.tsv. Formal mode "
            "uses raw_selected_rt from matching typed mode rows as the "
            "PeakHypothesis RT center instead of falling back to family center RT."
        ),
    )
    parser.add_argument(
        "--output-mode",
        choices=("activated-copy", "formal"),
        default="activated-copy",
        help=(
            "activated-copy writes *_activated.tsv sidecars; formal writes "
            "alignment_matrix.tsv, alignment_review.tsv, and alignment_cells.tsv "
            "as the product output contract. Formal alignment_matrix.tsv remains "
            "Mz/RT/sample-column downstream format; PeakHypothesis identity is "
            "written to activation_hypothesis_identity.tsv."
        ),
    )
    parser.add_argument(
        "--allow-overwrite-source",
        action="store_true",
        help=(
            "Allow formal output mode to overwrite source alignment TSVs. "
            "Use only after preserving source artifacts elsewhere."
        ),
    )
    parser.add_argument(
        "--allow-non-passing-acceptance",
        action="store_true",
        help="Diagnostic override only; product application normally requires pass.",
    )
    parser.add_argument(
        "--legacy-rt-row-oracle-xlsx",
        type=Path,
        help=(
            "Optional clean MZmine-style workbook with Mz and RT columns. "
            "Formal mode records matching rows as context only; the legacy "
            "pipeline is not product identity authority and does not replace "
            "peak_hypothesis_id."
        ),
    )
    parser.add_argument(
        "--legacy-rt-row-oracle-mz-ppm",
        type=float,
        default=20.0,
        help="m/z tolerance for --legacy-rt-row-oracle-xlsx matching.",
    )
    parser.add_argument(
        "--legacy-rt-row-oracle-rt-tolerance-min",
        type=float,
        default=1.0,
        help="RT tolerance in minutes for --legacy-rt-row-oracle-xlsx matching.",
    )
    parser.add_argument(
        "--require-complete-peak-hypothesis-identity",
        action="store_true",
        help=(
            "Fail unless formal output can emit a complete PeakHypothesis "
            "identity sidecar for every Mz/RT/sample matrix row without "
            "unresolved family projection rows."
        ),
    )
    projection_group = parser.add_mutually_exclusive_group()
    projection_group.add_argument(
        "--exclude-family-projections",
        dest="exclude_family_projections",
        action="store_true",
        default=True,
        help=(
            "Formal mode default. Exclude unresolved family projection rows "
            "from emitted alignment_matrix.tsv and report excluded row/cell "
            "counts in the application summary. Excluded rows keep canonical "
            "readiness blocked."
        ),
    )
    projection_group.add_argument(
        "--include-family-projections",
        dest="exclude_family_projections",
        action="store_false",
        help=(
            "Diagnostic legacy mode only. Include unresolved family projection "
            "rows in formal outputs for review; these rows block canonical "
            "readiness and must not be handed to downstream as product matrix."
        ),
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
