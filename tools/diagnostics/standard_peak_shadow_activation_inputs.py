"""Convert standard-peak shadow projection accepts into activation inputs."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from xic_extractor.alignment.shared_peak_identity_explanation import (
    product_activation,
)
from xic_extractor.diagnostics.diagnostic_io import read_tsv_required
from xic_extractor.diagnostics.standard_peak_shadow_activation_inputs import (
    build_standard_peak_activation_inputs,
    sha256_file,
    write_standard_peak_activation_input_outputs,
)

SHADOW_PROJECTION_REQUIRED_COLUMNS = (
    "schema_version",
    "peak_hypothesis_id",
    "feature_family_id",
    "sample_stem",
    "current_raw_status",
    "current_production_status",
    "current_matrix_written",
    "shadow_decision",
    "projected_matrix_written",
    "projected_matrix_value",
    "product_authority_chain",
    "shadow_projection_row_sha256",
)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    rows = read_tsv_required(
        args.shadow_projection_cells_tsv,
        SHADOW_PROJECTION_REQUIRED_COLUMNS,
    )
    index = build_standard_peak_activation_inputs(
        rows,
        source_shadow_projection_sha256=sha256_file(
            args.shadow_projection_cells_tsv,
        ),
        source_run_id=args.source_run_id,
    )
    outputs = write_standard_peak_activation_input_outputs(
        args.output_dir,
        index,
    )
    print(f"Standard-peak activation decisions TSV: {outputs.decisions_tsv}")
    print(f"Standard-peak activation values TSV: {outputs.values_tsv}")
    print(f"Standard-peak activation acceptance TSV: {outputs.acceptance_tsv}")
    print(f"Standard-peak activation inputs summary TSV: {outputs.summary_tsv}")
    print(f"Standard-peak activation inputs summary JSON: {outputs.summary_json}")
    if args.apply_matrix_only:
        _require_apply_args(args)
        activated_dir = args.activated_output_dir or args.output_dir / (
            "activated_matrix"
        )
        applied = product_activation.apply_activation_to_alignment_matrix_outputs(
            activation_decisions_tsv=outputs.decisions_tsv,
            activation_acceptance_tsv=outputs.acceptance_tsv,
            activation_values_tsv=outputs.values_tsv,
            alignment_matrix_tsv=args.alignment_matrix_tsv,
            alignment_matrix_identity_tsv=args.alignment_matrix_identity_tsv,
            alignment_review_tsv=args.alignment_review_tsv,
            output_dir=activated_dir,
        )
        print(f"Activated matrix TSV: {applied.matrix_tsv}")
        print(f"Activation application summary TSV: {applied.summary_tsv}")
        print(f"Activation value delta TSV: {applied.value_delta_tsv}")
        print(
            "Activation hypothesis identity TSV: "
            f"{applied.hypothesis_identity_tsv}",
        )
        print(f"Alignment matrix identity TSV: {applied.matrix_identity_tsv}")
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shadow-projection-cells-tsv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-run-id", default="")
    parser.add_argument(
        "--apply-matrix-only",
        action="store_true",
        help=(
            "After writing standard-peak activation inputs, apply them through "
            "product_activation matrix-only mode. The generated acceptance must pass."
        ),
    )
    parser.add_argument("--alignment-matrix-tsv", type=Path)
    parser.add_argument("--alignment-matrix-identity-tsv", type=Path)
    parser.add_argument("--alignment-review-tsv", type=Path)
    parser.add_argument(
        "--activated-output-dir",
        type=Path,
        help=(
            "Output directory for matrix-only activation. Defaults to "
            "<output-dir>/activated_matrix."
        ),
    )
    return parser.parse_args(argv)


def _require_apply_args(args: argparse.Namespace) -> None:
    missing = [
        flag
        for flag, value in (
            ("--alignment-matrix-tsv", args.alignment_matrix_tsv),
            (
                "--alignment-matrix-identity-tsv",
                args.alignment_matrix_identity_tsv,
            ),
            ("--alignment-review-tsv", args.alignment_review_tsv),
        )
        if value is None
    ]
    if missing:
        raise ValueError(
            "--apply-matrix-only requires " + ", ".join(missing),
        )


if __name__ == "__main__":
    raise SystemExit(main())
