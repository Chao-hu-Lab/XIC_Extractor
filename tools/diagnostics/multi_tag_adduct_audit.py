from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from types import SimpleNamespace

from xic_extractor.alignment.adduct_annotation import (
    load_artificial_adducts,
    match_artificial_adduct_pairs,
)

_REQUIRED_REVIEW_COLUMNS = (
    "feature_family_id",
    "neutral_loss_tag",
    "family_center_mz",
    "family_center_rt",
    "include_in_primary_matrix",
)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    payload = build_audit(
        alignment_dir=args.alignment_dir,
        selected_tags=_split_csv_arg(args.selected_tags),
        tag_combine_mode=args.tag_combine_mode,
        artificial_adduct_list=args.artificial_adduct_list,
        baseline_alignment_dir=args.baseline_alignment_dir,
    )
    write_audit_outputs(args.output_dir, payload)
    return 0


def build_audit(
    *,
    alignment_dir: Path,
    selected_tags: tuple[str, ...],
    tag_combine_mode: str,
    artificial_adduct_list: Path | None = None,
    baseline_alignment_dir: Path | None = None,
) -> dict[str, object]:
    review_rows = _read_review(alignment_dir / "alignment_review.tsv")
    baseline_rows = (
        _read_review(baseline_alignment_dir / "alignment_review.tsv")
        if baseline_alignment_dir is not None
        else ()
    )
    pairs = ()
    if artificial_adduct_list is not None:
        pairs = match_artificial_adduct_pairs(
            [_family(row) for row in review_rows],
            load_artificial_adducts(artificial_adduct_list),
            rt_window_min=0.05,
            mz_tolerance_ppm=10.0,
        )
    matrix_row_count = _primary_count(review_rows)
    return {
        "selected_tags": list(selected_tags),
        "tag_combine_mode": tag_combine_mode,
        "matrix_row_count": matrix_row_count,
        "review_row_count": len(review_rows),
        "tag_overlap": _tag_overlap(review_rows),
        "artificial_adduct_pair_count": len(pairs),
        "matrix_row_delta_vs_baseline": (
            matrix_row_count - _primary_count(baseline_rows)
        ),
        "artificial_adduct_pairs": [
            {
                "parent_family_id": pair.parent_family_id,
                "related_family_id": pair.related_family_id,
                "adduct_name": pair.adduct_name,
                "mz_delta_observed": pair.mz_delta_observed,
                "mz_delta_error_ppm": pair.mz_delta_error_ppm,
                "rt_delta_min": pair.rt_delta_min,
            }
            for pair in pairs
        ],
    }


def write_audit_outputs(output_dir: Path, payload: dict[str, object]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "multi_tag_adduct_summary.tsv"
    pairs_path = output_dir / "multi_tag_adduct_pairs.tsv"
    json_path = output_dir / "multi_tag_adduct.json"
    md_path = output_dir / "multi_tag_adduct.md"

    _write_summary(summary_path, payload)
    _write_pairs(pairs_path, payload)
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    md_path.write_text(_markdown(payload), encoding="utf-8")


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit multi-tag and adduct evidence.")
    parser.add_argument("--alignment-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--selected-tags", default="dR,R,MeR")
    parser.add_argument("--tag-combine-mode", default="union")
    parser.add_argument("--artificial-adduct-list", type=Path)
    parser.add_argument("--baseline-alignment-dir", type=Path)
    return parser.parse_args(argv)


def _read_review(path: Path) -> tuple[dict[str, str], ...]:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            fieldnames = tuple(reader.fieldnames or ())
            missing = [
                column
                for column in _REQUIRED_REVIEW_COLUMNS
                if column not in fieldnames
            ]
            if missing:
                raise ValueError(
                    f"{path}: missing required columns: {', '.join(missing)}"
                )
            return tuple(dict(row) for row in reader)
    except OSError as exc:
        raise ValueError(f"{path}: could not read alignment review TSV: {exc}") from exc


def _primary_count(rows: tuple[dict[str, str], ...]) -> int:
    return sum(1 for row in rows if row.get("include_in_primary_matrix") == "TRUE")


def _tag_overlap(rows: tuple[dict[str, str], ...]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        tags = row.get("matched_tag_names") or row.get("neutral_loss_tag", "")
        normalized = tuple(tag for tag in tags.split(";") if tag)
        if normalized:
            counts[";".join(sorted(normalized))] += 1
    return dict(sorted(counts.items()))


def _family(row: dict[str, str]) -> SimpleNamespace:
    return SimpleNamespace(
        feature_family_id=row["feature_family_id"],
        family_center_mz=float(row["family_center_mz"]),
        family_center_rt=float(row["family_center_rt"]),
    )


def _split_csv_arg(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _write_summary(path: Path, payload: dict[str, object]) -> None:
    fields = (
        "selected_tags",
        "tag_combine_mode",
        "matrix_row_count",
        "review_row_count",
        "artificial_adduct_pair_count",
        "matrix_row_delta_vs_baseline",
    )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerow(
            {
                "selected_tags": ";".join(payload["selected_tags"]),  # type: ignore[arg-type]
                "tag_combine_mode": payload["tag_combine_mode"],
                "matrix_row_count": payload["matrix_row_count"],
                "review_row_count": payload["review_row_count"],
                "artificial_adduct_pair_count": payload["artificial_adduct_pair_count"],
                "matrix_row_delta_vs_baseline": payload["matrix_row_delta_vs_baseline"],
            }
        )


def _write_pairs(path: Path, payload: dict[str, object]) -> None:
    fields = (
        "parent_family_id",
        "related_family_id",
        "adduct_name",
        "mz_delta_observed",
        "mz_delta_error_ppm",
        "rt_delta_min",
    )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(payload["artificial_adduct_pairs"])  # type: ignore[arg-type]


def _markdown(payload: dict[str, object]) -> str:
    return "\n".join(
        [
            "# Multi-Tag Adduct Audit",
            "",
            f"- selected_tags: {', '.join(payload['selected_tags'])}",  # type: ignore[arg-type]
            f"- tag_combine_mode: {payload['tag_combine_mode']}",
            f"- matrix_row_count: {payload['matrix_row_count']}",
            f"- review_row_count: {payload['review_row_count']}",
            "- artificial_adduct_pair_count: "
            f"{payload['artificial_adduct_pair_count']}",
            "- matrix_row_delta_vs_baseline: "
            f"{payload['matrix_row_delta_vs_baseline']}",
            "",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
