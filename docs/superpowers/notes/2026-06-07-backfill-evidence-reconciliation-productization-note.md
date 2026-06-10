# Backfill Evidence Reconciliation Productization Note

Date: 2026-06-07

Status: `shadow_ready` for Slice 0/1 diagnostic review surface.

## Verdict

Implemented the backfill evidence reconciliation machine index and human gallery
surface. This closes diagnostic/review observability for family/seed-group
backfill evidence chains, but it does not promote product behavior.

No product promotion was attempted. The implementation does not mutate
`alignment_review.tsv`, `alignment_cells.tsv`, `alignment_matrix.tsv`, workbook
schemas, selected cells, product decisions, RAW/DLL paths, or downstream matrix
handoff.

## New Surfaces

- `tools/diagnostics/backfill_evidence_reconciliation_gallery.py`
- `xic_extractor/diagnostics/backfill_reconciliation_gallery.py`
- `tests/test_backfill_evidence_reconciliation_gallery.py`
- `backfill_evidence_reconciliation_groups.tsv`
- `backfill_evidence_reconciliation_representative_cells.tsv`
- `backfill_evidence_reconciliation_summary.json`
- `backfill_evidence_reconciliation_gallery.html`

The HTML gallery is table-first, uses collapsed row details, exposes source
artifact links, and keeps PNG links usable as direct anchors with a JS lightbox
enhancement.

Post-review hardening fixed:

- candidate-gate source hash mismatches and missing source hashes fail closed;
- malformed `production_candidate` rows with blockers do not count as
  product-grade support;
- `detected=0` families are excluded from the backfill review queue and counted
  separately because they do not have a detected seed/owner to backfill from;
- review output ordering is disagreement-first;
- PNG, input, and generated artifact links are rebased relative to the gallery
  HTML path;
- dangerous PNG href schemes are rejected before `href` or lightbox dataset
  rendering;
- HTML uses the exact run `validation_label`.

## Evidence-Authority Boundary

The gallery keeps these categories separate:

- product behavior from alignment/product artifacts;
- product-grade support from candidate-gate / Tier 2 evidence rows;
- review-only visual support from seed-aware or overlay rows;
- dependent context from seed/request provenance;
- blockers, missing evidence, stale source, and join gaps.

It does not compute a composite `backfill_score`.

## Existing-Artifact Smoke

Command:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python tools/diagnostics/backfill_evidence_reconciliation_gallery.py --alignment-review-tsv output/backfill_evidence_gate_8raw_20260605/projected_alignment/alignment_review.tsv --alignment-cells-tsv output/backfill_evidence_gate_8raw_20260605/projected_alignment/alignment_cells.tsv --alignment-matrix-tsv output/backfill_evidence_gate_8raw_20260605/projected_alignment/alignment_matrix.tsv --overlay-batch-summary-tsv output/backfill_evidence_gate_8raw_20260605/changed_row_ms1_overlay_review_20260605/family_ms1_overlay_batch_summary.tsv --output-dir output/backfill_evidence_reconciliation_20260607 --source-run-id backfill_evidence_gate_8raw_20260605
```

Observed output:

- `output/backfill_evidence_reconciliation_20260607/backfill_evidence_reconciliation_groups.tsv`
- `output/backfill_evidence_reconciliation_20260607/backfill_evidence_reconciliation_representative_cells.tsv`
- `output/backfill_evidence_reconciliation_20260607/backfill_evidence_reconciliation_summary.json`
- `output/backfill_evidence_reconciliation_20260607/backfill_evidence_reconciliation_gallery.html`

Summary:

- `group_count`: 850
- `representative_cell_count`: 1237
- `excluded_family_counts`: `detected_zero_family=110`
- `validation_label`: `diagnostic_only`
- `matrix_contract_changed`: false
- `product_behavior_changed`: false
- `missing_evidence_counts`: `missing_seed_provenance=850`
- `reconciliation_class_counts`: `not_assessable_missing_seed_provenance=850`

Interpretation: this 8RAW root contains projected alignment and overlay summary
artifacts, but no `alignment_owner_backfill_seed_audit.tsv` or
`alignment_production_candidate_gate.tsv` in the same root. The gallery therefore
fails closed and reports missing seed provenance instead of treating overlay
presence as product-grade support.

## Browser Smoke

Headless Chromium smoke checked:

- desktop 1440x900;
- mobile 390x844;
- desktop with 200 percent zoom;
- `lang="zh-Hant"`;
- sticky table header;
- horizontal scroll wrapper;
- collapsed details by default;
- direct PNG anchor fallback;
- accessible lightbox marker `aria-modal="true"`;
- PNG href resolves to an existing file from the gallery directory;
- direct PNG image loads inside the lightbox;
- lightbox opens via Enter and Space, focuses close button, closes on Esc, and
  restores focus;
- Tab and Shift+Tab remain inside the modal while it is open;
- search filter targets only main table rows, not nested representative rows.

Observed top-level gallery rows: 850.

## Verification

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_backfill_evidence_reconciliation_gallery.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools/diagnostics/backfill_evidence_reconciliation_gallery.py xic_extractor/diagnostics/backfill_reconciliation_gallery.py tests/test_backfill_evidence_reconciliation_gallery.py
```

Observed:

- `12 passed`
- `All checks passed!`

## Remaining Gaps

- Product promotion remains unattempted.
- Initial smoke did not prove production readiness because the representative
  8RAW artifact root lacked seed audit and candidate-gate sidecars.
- A future allowlisted product-promotion slice still needs a reviewed promotion
  sub-contract, product-grade machine evidence, 8RAW validation, 85RAW
  validation, and validation-evidence reviewer acceptance.

## Follow-up: 8RAW Seed Chain

After reviewing the first gallery, `detected=0` families were confirmed as
out-of-scope for backfill review because they have no detected seed/owner to
backfill from. The gallery now excludes those families from the main review
queue and reports them separately.

New 8RAW alignment with seed audit:

```powershell
.venv\Scripts\python.exe -m scripts.run_alignment --discovery-batch-index local_validation_artifacts\discovery\accepted_p8b\8raw\discovery_batch_index.csv --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation --dll-dir C:\Xcalibur\system\programs --output-dir output\backfill_evidence_chain_8raw_seed_audit_20260607\alignment --expected-sample-count 8 --output-level validation-minimal --backfill-scope production-equivalent --audit-evidence-mode none --performance-profile validation-fast --owner-backfill-window-strategy super-window --owner-backfill-superwindow-span-factor 2 --emit-alignment-cells --emit-alignment-backfill-seed-audit --timing-output output\backfill_evidence_chain_8raw_seed_audit_20260607\alignment\timing.json --timing-live-output output\backfill_evidence_chain_8raw_seed_audit_20260607\alignment\timing.live.json
```

Observed alignment outputs:

- `output/backfill_evidence_chain_8raw_seed_audit_20260607/alignment/alignment_review.tsv`
- `output/backfill_evidence_chain_8raw_seed_audit_20260607/alignment/alignment_cells.tsv`
- `output/backfill_evidence_chain_8raw_seed_audit_20260607/alignment/alignment_matrix.tsv`
- `output/backfill_evidence_chain_8raw_seed_audit_20260607/alignment/alignment_owner_backfill_seed_audit.tsv`

Seed audit summary:

- `SeedRows`: 2280
- `SeedFamilies`: 960

Updated reconciliation with seed audit + overlay:

- `output/backfill_evidence_chain_8raw_seed_audit_20260607/reconciliation_seed_overlay/backfill_evidence_reconciliation_gallery.html`
- `group_count`: 974 seed groups
- `excluded_family_counts`: `detected_zero_family=110`
- `missing_evidence_counts`: none
- `reconciliation_class_counts`:
  `evidence_inconclusive=908`,
  `product_accepts_but_evidence_conflicts=39`,
  `product_accepts_and_visual_supports=27`

Updated reconciliation with seed audit + same-source candidate gate + overlay:

- `output/backfill_evidence_chain_8raw_seed_audit_20260607/reconciliation_seed_gate_overlay/backfill_evidence_reconciliation_gallery.html`
- `group_count`: 974 seed groups
- `excluded_family_counts`: `detected_zero_family=110`
- stale source warnings: 0

The candidate gate sidecar for this new alignment root is same-source but has
`row_count=0`, because `provisional_backfill_candidate_gate.py` still targets
the older `provisional_retention_candidate` scope. The current product path
labels many relevant rows as `production_family` with
`backfill_cell_evidence_required` /
`missing_independent_backfill_identity_evidence`, so the next design issue is a
product-authority evidence gate for actual retained/backfilled product rows, not
another provisional-only gate.

## Follow-up: Retained Product Backfill Gate

Implemented a diagnostic-only sidecar for actual product-retained backfill rows:

- `tools/diagnostics/retained_backfill_evidence_gate.py`
- `xic_extractor/diagnostics/retained_backfill_evidence_gate.py`
- `tests/test_retained_backfill_evidence_gate.py`
- `alignment_retained_backfill_evidence_gate.tsv`
- `alignment_retained_backfill_evidence_gate.json`
- `alignment_retained_backfill_missing_overlay_queue.tsv`

This gate targets rows with product-retained backfill behavior:

- `include_in_primary_matrix=TRUE`
- `identity_decision=production_family`
- detected count greater than zero
- quantifiable, accepted, review-only, or cell-level rescue/backfill context

It excludes `detected=0` families from main rows and counts them separately.
It does not read RAW/DLL, generate overlays, recompute similarity, mutate
alignment artifacts, mutate workbook schemas, or claim production readiness.

Command:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python -m tools.diagnostics.retained_backfill_evidence_gate --alignment-dir output/backfill_evidence_chain_8raw_seed_audit_20260607/alignment --overlay-batch-summary-tsv output/backfill_evidence_gate_8raw_20260605/changed_row_ms1_overlay_review_20260605/family_ms1_overlay_batch_summary.tsv --output-dir output/backfill_evidence_chain_8raw_seed_audit_20260607/retained_backfill_evidence_gate --source-run-id 8raw_seed_audit_20260607
```

Observed output:

- `output/backfill_evidence_chain_8raw_seed_audit_20260607/retained_backfill_evidence_gate/alignment_retained_backfill_evidence_gate.tsv`
- `output/backfill_evidence_chain_8raw_seed_audit_20260607/retained_backfill_evidence_gate/alignment_retained_backfill_evidence_gate.json`

Summary:

- `family_count`: 271 product-retained backfill families
- `row_count` / `seed_group_count`: 377 family/seed rows
- `excluded_family_counts`: `detected_zero_family=110`
- main rows with detected count zero: 0
- `status_counts`:
  `evidence_missing=311`,
  `evidence_conflict=39`,
  `visual_support=27`
- `production_ready`: false
- `matrix_contract_changed`: false

Interpretation: the current product-retained backfill path has 27 visual
support rows and 39 direct visual conflict rows from the old overlay summary.
The dominant remaining gap is missing overlay evidence for 311 product-retained
family/seed rows. This sidecar is a stable machine input for the next
product-authority decision, but it remains `diagnostic_only`.

Subagent review found no blocker and one P3 hardening item: if
`alignment_review.tsv` reports detected count greater than zero but the joined
`alignment_cells.tsv` rows contain no `status=detected`, the retained gate could
otherwise emit a main row with `detected_cell_count=0`. The gate now fails that
source-drift case closed by excluding the row from the main TSV and counting it
under `excluded_family_counts.detected_cell_join_mismatch`. The 8RAW retained
gate rerun did not hit this new exclusion; counts remained unchanged and main
rows with `detected_cell_count=0` remained 0.

The retained gate now also writes a missing-overlay queue for rows where seed
provenance exists but overlay evidence is missing. The queue is directly
consumable by `family_ms1_overlay_batch.py` and includes `seed_group_id`,
seed m/z, seed RT window, ppm, product behavior, and suggested overlay command
arguments. `family_ms1_overlay_batch.py` now preserves optional `seed_group_id`
in `family_ms1_overlay_batch_summary.tsv`, and retained-gate overlay joins
prefer exact `seed_group_id` matches. Legacy overlay summaries without
`seed_group_id` remain family-level fallback evidence.

Top 30 missing-overlay RAW-backed batch:

```powershell
.venv\Scripts\python.exe -m tools.diagnostics.family_ms1_overlay_batch --review-queue-tsv output\backfill_evidence_chain_8raw_seed_audit_20260607\retained_backfill_evidence_gate\alignment_retained_backfill_missing_overlay_queue.tsv --alignment-cells output\backfill_evidence_chain_8raw_seed_audit_20260607\alignment\alignment_cells.tsv --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation --dll-dir C:\Xcalibur\system\programs --output-dir output\backfill_evidence_chain_8raw_seed_audit_20260607\retained_backfill_evidence_gate\missing_overlay_top30 --limit 30 --ppm 10
```

Observed top30 overlay result:

- output summary:
  `output/backfill_evidence_chain_8raw_seed_audit_20260607/retained_backfill_evidence_gate/missing_overlay_top30/family_ms1_overlay_batch_summary.tsv`
- requested rows: 30
- succeeded: 30
- failed: 0
- PNG missing after success: 0
- `ms1_shape_supports_family_backfill`: 18
- `review_required_neighboring_ms1_interference`: 12
- top30 expansion gate: `blocked`

Combined retained gate with the old overlay summary plus the new top30
seed-specific overlay summary:

- output:
  `output/backfill_evidence_chain_8raw_seed_audit_20260607/retained_backfill_evidence_gate_with_top30_overlay/alignment_retained_backfill_evidence_gate.json`
- `family_count`: 271
- `row_count` / `seed_group_count`: 377
- `excluded_family_counts`: `detected_zero_family=110`
- `status_counts`:
  `evidence_missing=281`,
  `evidence_conflict=51`,
  `visual_support=45`
- `missing_overlay_queue_count`: 281
- `production_ready`: false
- `matrix_contract_changed`: false

Additional missing-overlay RAW-backed batches were generated from the same
queue, preserving exact `seed_group_id` provenance:

- ranks 31-60:
  `output/backfill_evidence_chain_8raw_seed_audit_20260607/retained_backfill_evidence_gate/missing_overlay_031_060/family_ms1_overlay_batch_summary.tsv`
  - requested rows: 30
  - succeeded: 30
  - failed: 0
  - `ms1_shape_supports_family_backfill`: 16
  - `review_required_neighboring_ms1_interference`: 12
  - `review_required_uncertain_ms1_shape`: 2
- ranks 61-90:
  `output/backfill_evidence_chain_8raw_seed_audit_20260607/retained_backfill_evidence_gate/missing_overlay_061_090/family_ms1_overlay_batch_summary.tsv`
  - requested rows: 30
  - succeeded: 30
  - failed: 0
  - `ms1_shape_supports_family_backfill`: 8
  - `review_required_neighboring_ms1_interference`: 19
  - `review_required_uncertain_ms1_shape`: 3
- ranks 91-120:
  `output/backfill_evidence_chain_8raw_seed_audit_20260607/retained_backfill_evidence_gate/missing_overlay_091_120/family_ms1_overlay_batch_summary.tsv`
  - requested rows: 30
  - succeeded: 30
  - failed: 0
  - `ms1_shape_supports_family_backfill`: 25
  - `review_required_neighboring_ms1_interference`: 5

Aggregated top120 missing-overlay result:

- requested rows: 120
- succeeded: 120
- failed: 0
- PNG missing after success: 0
- `ms1_shape_supports_family_backfill`: 67
- `review_required_neighboring_ms1_interference`: 48
- `review_required_uncertain_ms1_shape`: 5

Combined retained gate with the old overlay summary plus top120 seed-specific
overlay summaries:

- output:
  `output/backfill_evidence_chain_8raw_seed_audit_20260607/retained_backfill_evidence_gate_with_top120_overlay/alignment_retained_backfill_evidence_gate.json`
- `family_count`: 271
- `row_count` / `seed_group_count`: 377
- `excluded_family_counts`: `detected_zero_family=110`
- `status_counts`:
  `evidence_missing=191`,
  `evidence_conflict=92`,
  `visual_support=94`
- `missing_overlay_queue_count`: 191
- `production_ready`: false
- `matrix_contract_changed`: false

Interpretation: top120 overlay generation converted 120 previously missing
rows into visual evidence rows. Supported rows increased from 27 to 94, and
conflict/review rows increased from 39 to 92. The remaining 191 rows are still
`evidence_missing`; the 92 conflict rows are intentionally left for manual
review rather than being treated as product-ready support.

## Follow-up: Full Missing-Overlay Completion

The remaining missing-overlay queue was completed from the original 311-row
queue:

- ranks 121-150:
  - requested rows: 30
  - succeeded: 30
  - `ms1_shape_supports_family_backfill`: 25
  - `review_required_neighboring_ms1_interference`: 5
- ranks 151-180:
  - requested rows: 30
  - succeeded: 30
  - `ms1_shape_supports_family_backfill`: 20
  - `review_required_neighboring_ms1_interference`: 10
- ranks 181-210:
  - requested rows: 30
  - succeeded: 30
  - `ms1_shape_supports_family_backfill`: 26
  - `review_required_neighboring_ms1_interference`: 2
  - `review_required_uncertain_ms1_shape`: 2
- ranks 211-240:
  - requested rows: 30
  - succeeded: 30
  - `ms1_shape_supports_family_backfill`: 20
  - `review_required_neighboring_ms1_interference`: 9
  - `review_required_uncertain_ms1_shape`: 1
- ranks 241-270:
  - requested rows: 30
  - succeeded: 30
  - `ms1_shape_supports_family_backfill`: 25
  - `review_required_neighboring_ms1_interference`: 4
  - `review_required_uncertain_ms1_shape`: 1
- ranks 271-300:
  - requested rows: 30
  - succeeded: 30
  - `ms1_shape_supports_family_backfill`: 21
  - `review_required_neighboring_ms1_interference`: 6
  - `review_required_uncertain_ms1_shape`: 3
- ranks 301-311:
  - requested rows: 11
  - succeeded: 11
  - `ms1_shape_supports_family_backfill`: 8
  - `review_required_neighboring_ms1_interference`: 2
  - `review_required_uncertain_ms1_shape`: 1

Full generated missing-overlay result:

- requested rows: 311
- succeeded: 311
- failed: 0
- PNG/PDF missing after success: 0
- `ms1_shape_supports_family_backfill`: 212
- `review_required_neighboring_ms1_interference`: 86
- `review_required_uncertain_ms1_shape`: 13

Combined retained gate with the old overlay summary plus all 311 generated
seed-specific overlay summaries:

- output:
  `output/backfill_evidence_chain_8raw_seed_audit_20260607/retained_backfill_evidence_gate_with_full_missing_overlay/alignment_retained_backfill_evidence_gate.json`
- `family_count`: 271
- `row_count` / `seed_group_count`: 377
- `excluded_family_counts`: `detected_zero_family=110`
- `status_counts`:
  `evidence_conflict=138`,
  `visual_support=239`
- `missing_overlay_queue_count`: 0
- `production_ready`: false
- `readiness_label`: `diagnostic_only`
- `matrix_contract_changed`: false

Interpretation: the evidence-chain gap is no longer missing overlay generation.
All product-retained backfill family/seed rows now have visual overlay evidence.
The remaining work is human review of the 138 conflict/review rows and deciding
whether any supported subset can be promoted through an explicit production
policy. No promotion was attempted in this slice.

## Follow-up: Gallery Family-First UX Correction

Manual review of `FAM000087` in
`output/backfill_evidence_chain_8raw_seed_audit_20260607/reconciliation_seed_gate_overlay/backfill_evidence_reconciliation_gallery.html`
showed that the HTML main table was misleading: the same family appeared twice
because the renderer used family/seed-group rows as the primary table surface.
The two seed groups were near-identical aliases (`mz=254.097/254.098`,
`rt=13.3525/13.1836`) and shared the same legacy family-level overlay PNG.

The renderer was corrected so the HTML gallery is family-first:

- each family appears once in the main review table;
- seed groups, seed m/z/RT/window, per-seed evidence state, and representative
  cells live under collapsed details;
- duplicate main-row links to the same legacy family-level overlay PNG are
  de-duplicated;
- `review_required_*` overlay verdicts are classified as
  `human_visual_judgment_only` instead of `evidence_blocks_backfill`, because
  neighboring MS1 interference is a human review point rather than a hard veto.

The machine TSV remains a family/seed-group index. Product behavior remains
unchanged and no backfill promotion was attempted. The same HTML output path was
regenerated with the full overlay summary set:

- `output/backfill_evidence_chain_8raw_seed_audit_20260607/reconciliation_seed_gate_overlay/backfill_evidence_reconciliation_gallery.html`
- `FAM000087` main HTML row count: 1
- `group_count`: 974 family/seed groups
- `representative_cell_count`: 1424
- `reconciliation_class_counts`:
  `evidence_inconclusive=739`,
  `product_accepts_and_visual_supports=235`

Verification:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_retained_backfill_evidence_gate.py tests/test_family_ms1_overlay_batch.py tests/test_backfill_evidence_reconciliation_gallery.py tests/test_provisional_backfill_candidate_gate_cli.py tests/test_production_candidate_gate.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor/diagnostics/retained_backfill_evidence_gate.py tools/diagnostics/retained_backfill_evidence_gate.py tools/diagnostics/family_ms1_overlay_batch.py tests/test_retained_backfill_evidence_gate.py tests/test_family_ms1_overlay_batch.py xic_extractor/diagnostics/backfill_reconciliation_gallery.py tools/diagnostics/backfill_evidence_reconciliation_gallery.py tests/test_backfill_evidence_reconciliation_gallery.py tools/diagnostics/provisional_backfill_candidate_gate.py tests/test_provisional_backfill_candidate_gate_cli.py tools/diagnostics/INDEX.md
```

Observed:

- `86 passed`
- `All checks passed!`

## Follow-up: Scaled-to-own-max Evidence Correction

Manual review of `FAM000540` showed that the bottom-left overlay panel
(`Absolute RT context: each trace scaled to its own max`) was stronger evidence
than the apex-aligned panel for that family. The old overlay verdict only used
the apex-aligned shape support fraction plus local/global-apex checks, so
`FAM000540` stayed at `review_required_neighboring_ms1_interference` even though
the absolute RT own-max shapes were visually coherent.

The MS1 overlay evidence summary now keeps the original
`shape_supported_fraction` meaning and adds separate own-max evidence:

- `absolute_own_max_shape_supported_fraction`
- `absolute_trace_apex_cluster_fraction`
- `absolute_trace_apex_delta_abs_median_min`

These metrics do not create a composite `backfill_score`. They allow
`ms1_shape_supports_family_backfill` when coverage is sufficient, own-max shape
support and absolute apex clustering are both strong, and the selected peak is
not dominated by a much larger off-target global max.

For `FAM000540`, refreshed evidence is:

- `family_verdict=ms1_shape_supports_family_backfill`
- `shape_supported_fraction=0.625`
- `absolute_own_max_shape_supported_fraction=0.875`
- `absolute_trace_apex_cluster_fraction=0.75`
- `global_apex_interference_fraction=0.25`
- `low_selected_peak_dominance_fraction=0`

The overlay batch summaries, trace JSON/TSV, PNG/PDF overlays, retained gate,
and family-first gallery were regenerated from existing trace JSONs; no RAW
re-read or product matrix mutation was performed. The current HTML remains:

- `output/backfill_evidence_chain_8raw_seed_audit_20260607/reconciliation_seed_gate_overlay/backfill_evidence_reconciliation_gallery.html`
- `FAM000540` main HTML label count: 1
- `FAM000540` seed-group rows in machine TSV: 2
- `FAM000540` evidence state: `review_only_visual_support`
- `FAM000540` reconciliation class: `product_accepts_and_visual_supports`

Subagent review found that the reconciliation gallery still grouped overlay
evidence by family only, which could broadcast seed-specific overlay verdicts
and own-max notes to sibling seed groups. The join was corrected:

- nonblank overlay `seed_group_id` rows now match only the same seed group;
- blank legacy overlay rows remain family-level fallback only when no
  seed-specific overlay exists for the current seed group;
- the machine groups TSV schema is unchanged.

The current regenerated reconciliation summary after this fix is:

- `group_count`: 974
- `representative_cell_count`: 1424
- `evidence_authority_state`:
  `dependent_context_only=597`,
  `human_visual_judgment_only=60`,
  `review_only_visual_support=317`
- `reconciliation_class_counts`:
  `evidence_inconclusive=657`,
  `product_accepts_and_visual_supports=317`

The older one-off changed-row HTML was also refreshed from the updated
`family_ms1_overlay_batch_summary.tsv` to avoid stale manual-review display:

- `output/backfill_evidence_gate_8raw_20260605/changed_row_ms1_overlay_review_20260605/review_gallery.html`
- `FAM000540` now displays
  `family_verdict=ms1_shape_supports_family_backfill`
  with own-max/absolute-apex metrics.
