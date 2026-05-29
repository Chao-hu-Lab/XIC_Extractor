# Shared Peak Identity Slice 1 Blast-Radius Implementation Note

## Current Verdict

Slice 1 integration is implemented as `diagnostic_only` CLI/writer behavior.
Default CLI execution remains Slice 0 only. Slice 1 outputs are emitted only
when `--enable-blast-radius` is passed.

The sampled preflight and full Slice 1 command were executed after the
integration implementation. The full run used current local artifacts but did
not provide an expected 85RAW blast-radius manifest, so required 85RAW surfaces
remain `present_hash_unpinned` and the run is intentionally `not_assessed` for
current-readiness purposes.

## Input Artifact Paths

- Manual oracle:
  `docs/superpowers/fixtures/shared_peak_identity_manual_oracle_v1.tsv`
- Slice 0 8RAW review:
  `output/tiered_backfill_candidate_gate_8raw_current/alignment_review.tsv`
- Slice 0 8RAW cells:
  `output/tiered_backfill_candidate_gate_8raw_current/alignment_cells.tsv`
- Candidate gate context:
  `output/tier2_v0_1_coherence_8raw_current_gate/alignment_production_candidate_gate.tsv`
- Slice 1 8RAW run:
  `output/tiered_backfill_candidate_gate_8raw_current`
- Slice 1 85RAW run:
  `output/tiered_backfill_candidate_gate_85raw_current`

## Slice 0 Go/No-Go Facts

The prior Slice 0 go/no-go expected for Slice 1 planning remains:

- `seed_rows_explained = seed_rows_total`
- `seed_rows_unexplained = 0`
- `seed_rows_inconclusive = 0`
- `vocabulary_special_casing_detected = FALSE`

Reconfirm these in `shared_peak_identity_run_facts.tsv` before treating a real
Slice 1 run as current evidence.

## Preflight

Recommended sampled preflight limit: `1000` rows per required artifact.

Command:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python -m tools.diagnostics.shared_peak_identity_explanation `
  --manual-oracle-tsv docs\superpowers\fixtures\shared_peak_identity_manual_oracle_v1.tsv `
  --alignment-review-tsv output\tiered_backfill_candidate_gate_8raw_current\alignment_review.tsv `
  --alignment-cells-tsv output\tiered_backfill_candidate_gate_8raw_current\alignment_cells.tsv `
  --candidate-gate-tsv output\tier2_v0_1_coherence_8raw_current_gate\alignment_production_candidate_gate.tsv `
  --enable-blast-radius `
  --blast-radius-preflight-only `
  --blast-radius-sample-row-limit 1000 `
  --blast-radius-8raw-run output\tiered_backfill_candidate_gate_8raw_current `
  --blast-radius-85raw-run output\tiered_backfill_candidate_gate_85raw_current `
  --output-dir output\shared_peak_identity_evidence_explanation_slice1_preflight
```

Expected preflight behavior:

- Prints `preflight_*_row_count`, `sample_count`, `family_count`,
  `artifact_status`, and `missing_required_fields`.
- Does not write `shared_peak_identity_blast_radius_manifest.tsv`.
- Does not write `shared_peak_identity_blast_radius_summary.tsv`.

Sampled counts from real artifacts:

- `8raw_alignment_review`: rows `1000`, samples `0`, families `1000`,
  status `present_hash_unpinned`, missing fields empty.
- `8raw_alignment_cells`: rows `1000`, samples `8`, families `125`,
  status `present_hash_unpinned`, missing fields empty.
- `85raw_alignment_review`: rows `1000`, samples `0`, families `1000`,
  status `present_hash_unpinned`, missing fields empty.
- `85raw_alignment_cells`: rows `1000`, samples `85`, families `12`,
  status `present_hash_unpinned`, missing fields empty.

## Full Slice 1 Command

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python -m tools.diagnostics.shared_peak_identity_explanation `
  --manual-oracle-tsv docs\superpowers\fixtures\shared_peak_identity_manual_oracle_v1.tsv `
  --alignment-review-tsv output\tiered_backfill_candidate_gate_8raw_current\alignment_review.tsv `
  --alignment-cells-tsv output\tiered_backfill_candidate_gate_8raw_current\alignment_cells.tsv `
  --candidate-gate-tsv output\tier2_v0_1_coherence_8raw_current_gate\alignment_production_candidate_gate.tsv `
  --enable-blast-radius `
  --blast-radius-8raw-run output\tiered_backfill_candidate_gate_8raw_current `
  --blast-radius-85raw-run output\tiered_backfill_candidate_gate_85raw_current `
  --optional-blast-radius-artifact candidate_gate_8raw=output\tiered_backfill_candidate_gate_8raw_current\alignment_production_candidate_gate.tsv `
  --optional-blast-radius-artifact candidate_gate_85raw=output\tiered_backfill_candidate_gate_85raw_current\alignment_production_candidate_gate.tsv `
  --output-dir output\shared_peak_identity_evidence_explanation_slice1
```

Use `--expected-blast-radius-manifest <path>` when 85RAW expected hashes are
pinned. Without it, 85RAW required artifacts can be summarized but must remain
`present_hash_unpinned`, so `blast_radius_assessed` cannot be `present_current`.

## Output Files

- `output/shared_peak_identity_evidence_explanation_slice1/shared_peak_identity_manual_oracle.tsv`
- `output/shared_peak_identity_evidence_explanation_slice1/shared_peak_identity_evidence_vectors.tsv`
- `output/shared_peak_identity_evidence_explanation_slice1/shared_peak_identity_explanations.tsv`
- `output/shared_peak_identity_evidence_explanation_slice1/shared_peak_identity_run_facts.tsv`
- `output/shared_peak_identity_evidence_explanation_slice1/shared_peak_identity_explanation_report.md`
- `output/shared_peak_identity_evidence_explanation_slice1/shared_peak_identity_blast_radius_manifest.tsv`
- `output/shared_peak_identity_evidence_explanation_slice1/shared_peak_identity_blast_radius_summary.tsv`

## Real-Run Placeholders

## Real-Run Results

- `blast_radius_assessed`: `not_assessed`
- Required 85RAW expected-hash status: `present_hash_unpinned`
- Manifest status counts: `present_current=2`, `present_hash_unpinned=7`
- `blast_radius_stale_artifact_count`: `0`
- `max_overfit_risk`: `unassessed`
- Summary risk counts: `none=5`, `unassessed=30`
- Output directory:
  `output/shared_peak_identity_evidence_explanation_slice1`
- Next recommended action: provide a pinned expected blast-radius manifest if
  this run should close current-readiness. Until then, treat Slice 1 as useful
  coverage/shape context only and externalize the missing freshness evidence.
