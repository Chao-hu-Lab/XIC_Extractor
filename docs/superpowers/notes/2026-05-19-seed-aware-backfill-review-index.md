# Seed-Aware Backfill Review Index

Doc placement: repo_support_doc
Doc kind: validation_artifact
Doc lifecycle: active
Repo owner: docs/product/backfill.md
Doc exit rule: Retire or move to Obsidian after the seed-aware Backfill gate is promoted into a formal product contract or killed.

## Verdict

`shadow_gate_ready`

The seed-aware review rule is ready as a shadow gate candidate, not as a
production matrix rule. This checkpoint does not change matrix identity,
backfill behavior, scoring, reliability, or output schemas.

## Evidence Inputs

- Review candidates:
  `output\diagnostics\untargeted_revalidation_after_targeted_fix_85raw\family_ms1_backfill_review_seed_audit_cp_overlayed\family_ms1_backfill_review_candidates.tsv`
- Top-10 smoothed overlay batch:
  `output\diagnostics\untargeted_revalidation_after_targeted_fix_85raw\family_ms1_overlay_top10_seed_audit_cp_smoothed15\family_ms1_overlay_batch_summary.tsv`
- Seed-specific low-coverage overlay batch:
  `output\diagnostics\untargeted_revalidation_after_targeted_fix_85raw\family_ms1_seed_overlay_low_coverage_cp\family_ms1_overlay_batch_summary.tsv`
- Low-coverage detail rows:
  `output\diagnostics\untargeted_revalidation_after_targeted_fix_85raw\low_ms1_assessable_coverage_seed_audit_cp\low_ms1_assessable_coverage_rows.tsv`
- Owner backfill seed audit:
  `output\alignment\untargeted_revalidation_after_targeted_fix_85raw_region_first_safe_merge_seed_audit\alignment_owner_backfill_seed_audit.tsv`

## Output Index

- Review summary:
  `output\diagnostics\untargeted_revalidation_after_targeted_fix_85raw\seed_aware_backfill_review_cp\seed_aware_backfill_review_summary.tsv`
- Family decisions:
  `output\diagnostics\untargeted_revalidation_after_targeted_fix_85raw\seed_aware_backfill_review_cp\seed_aware_backfill_review_families.tsv`
- Blast radius:
  `output\diagnostics\untargeted_revalidation_after_targeted_fix_85raw\seed_aware_backfill_review_cp\seed_aware_backfill_blast_radius.tsv`
- Human summary:
  `output\diagnostics\untargeted_revalidation_after_targeted_fix_85raw\seed_aware_backfill_review_cp\seed_aware_backfill_review.md`

## Current 85RAW Result

| class | count | interpretation |
|---|---:|---|
| `seed_shape_supported_review_candidate` | 5 | seed-aware MS1 evidence supports review candidate status |
| `neighbor_interference_review` | 5 | high neighboring MS1 interference blocks automatic escalation |
| `not_assessable` | 91 | seed-specific overlay has not been generated yet |

Shadow blast radius:

- affected families: `5`
- shadow-withheld rescued cells: `387`
- production matrix changes: `none`

## Key Families

| family | m/z | class | reason | overlay |
|---|---:|---|---|---|
| `FAM020034` | 616.805 | `seed_shape_supported_review_candidate` | seed-specific overlays support MS1 shape; family-center overlay was a false negative | `output\diagnostics\untargeted_revalidation_after_targeted_fix_85raw\family_ms1_seed_overlay_low_coverage_cp\fam020034_seed1_overlay.png` |
| `FAM012728` | 358.062 | `neighbor_interference_review` | seed-specific coverage improves, but neighboring interference remains high | `output\diagnostics\untargeted_revalidation_after_targeted_fix_85raw\family_ms1_seed_overlay_low_coverage_cp\fam012728_seed1_overlay.png` |
| `FAM014256` | 392.08 | `neighbor_interference_review` | high neighboring MS1 interference | `output\diagnostics\untargeted_revalidation_after_targeted_fix_85raw\family_ms1_overlay_top10_seed_audit_cp_smoothed15\fam014256_ms1_overlay_review.png` |
| `FAM016922` | 472.198 | `neighbor_interference_review` | high neighboring MS1 interference | `output\diagnostics\untargeted_revalidation_after_targeted_fix_85raw\family_ms1_overlay_top10_seed_audit_cp_smoothed15\fam016922_ms1_overlay_review.png` |
| `FAM004459` | 283.154 | `neighbor_interference_review` | high neighboring MS1 interference | `output\diagnostics\untargeted_revalidation_after_targeted_fix_85raw\family_ms1_overlay_top10_seed_audit_cp_smoothed15\fam004459_ms1_overlay_review.png` |
| `FAM006664` | 295.106 | `neighbor_interference_review` | high neighboring MS1 interference | `output\diagnostics\untargeted_revalidation_after_targeted_fix_85raw\family_ms1_overlay_top10_seed_audit_cp_smoothed15\fam006664_ms1_overlay_review.png` |

## Overlay Reading Guide

- Top-left is the main human decision panel. It aligns every trace to its
  selected apex and scales each trace to 0-1, so it asks whether detected and
  rescued cells have similar MS1 peak shape.
- Bottom-left is absolute-RT context, not abundance. Each trace is scaled to
  its own maximum, so it asks whether the traces land in the same RT region.
- Bottom-middle is raw-intensity context. It keeps the original MS1 intensity
  scale, so it is the panel for DDA trigger / signal-height interpretation.

## Rerun Command

```powershell
uv --cache-dir .uv-cache run python tools\diagnostics\seed_aware_backfill_review.py `
  --review-candidates-tsv output\diagnostics\untargeted_revalidation_after_targeted_fix_85raw\family_ms1_backfill_review_seed_audit_cp_overlayed\family_ms1_backfill_review_candidates.tsv `
  --overlay-batch-summary-tsv output\diagnostics\untargeted_revalidation_after_targeted_fix_85raw\family_ms1_overlay_top10_seed_audit_cp_smoothed15\family_ms1_overlay_batch_summary.tsv `
  --overlay-batch-summary-tsv output\diagnostics\untargeted_revalidation_after_targeted_fix_85raw\family_ms1_seed_overlay_low_coverage_cp\family_ms1_overlay_batch_summary.tsv `
  --low-ms1-rows-tsv output\diagnostics\untargeted_revalidation_after_targeted_fix_85raw\low_ms1_assessable_coverage_seed_audit_cp\low_ms1_assessable_coverage_rows.tsv `
  --backfill-seed-audit-tsv output\alignment\untargeted_revalidation_after_targeted_fix_85raw_region_first_safe_merge_seed_audit\alignment_owner_backfill_seed_audit.tsv `
  --output-dir output\diagnostics\untargeted_revalidation_after_targeted_fix_85raw\seed_aware_backfill_review_cp
```

## Next Rule Candidate

Future production work, if approved, should start as an opt-in gate:

- keep rescued-heavy family backfill eligible only when seed-specific overlay
  supports MS1 shape,
- no high neighboring interference is present,
- active ISTD / known high-confidence targets are protected by explicit
  review rules,
- and 8RAW then 85RAW strict benchmark does not regress.
