# Shared Evidence Spine Adoption Decision

Date: 2026-05-18
Branch: `codex/region-first-safe-merge-validation`

## Scope

This checkpoint finishes the partially completed LC-MS/MS evidence spine work.
It does not change scoring, neutral-loss logic, reliability state, matrix
identity, production gates, workbook schema, or default resolver behavior.

The goal was audit parity: targeted and untargeted paths should express trace,
boundary, and region evidence using the same `Trace` / `TraceGroup` semantics.

## Checkpoint Results

### CP0: Detected-cell audit parity freeze

- Commit: `98f7771 feat: carry region audit through untargeted detected cells`
- Narrow tests: `61 passed`
- `ruff check .`: passed
- `mypy xic_extractor`: passed
- 8RAW alignment evidence:
  - `alignment_matrix.tsv` hash unchanged:
    `3EA29292127A94328D1A7B1EF072B0A911D609555AC0B4153C2166141202CA7E`
  - `alignment_review.tsv` hash unchanged:
    `9BAF49F353FBCF4CAA1299CCABE0B2A31DDBE979A5CE5D81A61957290204AACA`
  - detected-cell region audit fill rate: `2961 / 2961`

### CP1: Targeted TraceGroup adoption

- Commit: `328447e refactor: route targeted peak audit through trace groups`
- Targeted candidate / boundary / extractor tests: `63 passed`
- `ruff` on changed files: passed
- `mypy xic_extractor`: passed
- 8RAW targeted validation:
  - baseline:
    `output/validation_harness/region_safe_merge_v1_8raw/tissue_8raw_local_minimum`
  - new:
    `output/validation_harness/evidence_spine_tracegroup_cp1_8raw_keepcsv/tissue_8raw_local_minimum`
  - `xic_results.csv` hash unchanged:
    `4DE99D31510F20F56124EF24D767C0F160C0DBC0D2A41A97527C9EF0742D4422`
  - workbook `XIC Results` selected RT / area unchanged
  - `peak_candidates.tsv` and `peak_candidate_boundaries.tsv` headers unchanged

### CP2: Untargeted TraceGroup adoption

- Commit: `9593f39 refactor: route untargeted region audit through trace groups`
- Alignment owner / backfill / family / process / writer tests: `111 passed`
- `ruff` on changed files: passed
- `mypy xic_extractor`: passed
- 8RAW alignment validation:
  - baseline:
    `output/alignment/region_safe_merge_v1_8raw_region_first_safe_merge`
  - new:
    `output/alignment/evidence_spine_tracegroup_cp2_8raw_region_first_safe_merge`
  - `alignment_matrix.tsv` hash unchanged:
    `3EA29292127A94328D1A7B1EF072B0A911D609555AC0B4153C2166141202CA7E`
  - `alignment_review.tsv` hash unchanged:
    `9BAF49F353FBCF4CAA1299CCABE0B2A31DDBE979A5CE5D81A61957290204AACA`
  - `alignment_cells.tsv` header unchanged
  - detected region audit fill rate: `2961 / 2961`
  - rescued region audit fill rate: `3318 / 3318`

### CP3: Evidence spine consistency diagnostic

- Commit: `3544065 feat: add evidence spine consistency diagnostic`
- Diagnostic test: `3 passed`
- `ruff` on diagnostic/test: passed
- `mypy tools/diagnostics/evidence_spine_consistency.py`: passed
- 8RAW smoke output:
  - `output/diagnostics/evidence_spine_consistency_cp3_8raw/evidence_spine_consistency_summary.tsv`
  - `output/diagnostics/evidence_spine_consistency_cp3_8raw/evidence_spine_consistency_rows.tsv`
  - `output/diagnostics/evidence_spine_consistency_cp3_8raw/evidence_spine_consistency.json`
  - `output/diagnostics/evidence_spine_consistency_cp3_8raw/evidence_spine_consistency.md`
- Smoke summary:
  - rows checked: `72`
  - matched rows: `56`
  - consistent rows: `41`
  - missing alignment rows: `16`
  - included ISTD rows: `56`
  - mismatch reason counts:
    - `consistent:41`
    - `no_alignment_mz_rt_match:16`
    - `region_verdict_mismatch:15`
    - `local_mixture_mismatch:15`
    - `boundary_start_delta_gt_0.10:4`

## Interpretation

The shared evidence spine adoption itself is successful. For matched high-value
rows, targeted and untargeted selected RT / area are now comparable through the
same trace and region vocabulary without changing production outputs.

The remaining mismatches are not evidence-spine transport failures:

- `d3-N6-medA`, `5-medC`, and most stable ISTD rows match with effectively
  unchanged RT / area.
- Missing alignment matches are concentrated in targets outside the current
  dR-only alignment evidence surface, especially RNA-tag ISTD and low-scope
  targets.
- The dominant non-missing mismatch is region/local-mixture label disagreement,
  while selected RT / area can still be effectively identical. That points to
  semantic calibration of diagnostic labels, not a new production gate.

## Decision

Continue from evidence quality, not another resolver rule.

Next direction:

1. If a representative area mismatch reproduces while targeted and untargeted
   trace context agree, investigate baseline / integration uncertainty.
2. If the reproduced mismatch is caused by shallow local-minimum splitting,
   continue local mixture model-selection, still opt-in or shadow-first.
3. If targeted and untargeted trace context diverge in future cases, fix the
   evidence spine before changing scoring or production gates.

Explicitly do not do:

- GC-MS pipeline
- ML / DL model
- adaptive ROI tracking
- new resolver family
- default resolver switch
