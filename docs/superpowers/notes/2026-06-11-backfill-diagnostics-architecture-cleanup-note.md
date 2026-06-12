# Backfill / Diagnostics Architecture Cleanup Note

**Date:** 2026-06-11
**Status:** cleanup + focused optimization implemented; no RAW validation run
**Scope:** backfill/alignment architecture-debt items from
`2026-06-10-backfill-alignment-architecture-debt-audit-note.md`, plus the
diagnostics shared-infrastructure surface.

## Verdict

The safe Tier 1 cleanup and the highest-confidence Tier 2/Tier 3 architecture
items have been moved from note-level observation into code:

- removed verified-dead owner-backfill code;
- kept legacy/no-op `AlignmentConfig` fields for public constructor
  compatibility while documenting that they have no computation consumers;
- consolidated repeated backfill key/token/hash/grouping helpers;
- fixed the overlay-row selection inconsistency with one fail-closed helper;
- reduced repeated hot-loop work in backfill scope and owner matrix generation;
- skipped impossible single-candidate claim-registry duplicate work;
- reused per-family mode counts in the changed-row overlay review diagnostic;
- bucketed changed-row mode-aligned plot traces by mode before rendering;
- updated the diagnostic tool index so future diagnostic work reuses the new
  package-owned helpers.

This is still a cleanup/performance slice, not a production-readiness claim.
No 8RAW or 85RAW was launched in this slice.

## Implemented

### Tier 1 Cleanup

- Deleted the uncalled `_backfill_feature_sample` path from
  `xic_extractor/alignment/owner_backfill.py`; live owner backfill remains on
  `_backfill_feature_sample_trace`.
- Preserved legacy/no-op `AlignmentConfig` fields for public compatibility:
  `mz_bucket_neighbor_radius`, `anchor_priorities`, and
  `anchor_min_scan_support_score`.
- Added `xic_extractor/alignment/_backfill_util.py` for alignment-side backfill
  key/token helpers, then reused it from:
  - `backfill_ms1_product_authority.py`;
  - `backfill_candidate_ms2_product_authority.py`;
  - `backfill_evidence_projection.py`.
- Added package-neutral `xic_extractor/tabular_io.py` as the canonical home for
  shared tabular/scalar helpers and kept `xic_extractor/diagnostics/diagnostic_io.py`
  as a compatibility shim.
- Expanded the shared helper surface with:
  - `file_sha256`;
  - `numeric_equal`;
  - `has_semicolon_token`;
  - `rows_by_text_field`.
- Updated the `tools/diagnostics/diagnostic_io.py` compatibility shim.
- Migrated backfill/standard-peak diagnostics to the shared helpers where this
  was schema-neutral and low risk.
- Moved `shadow_production_projection` TSV loading and domain reconstruction
  into `xic_extractor/diagnostics/shadow_production_projection.py`; the
  `tools/diagnostics/shadow_production_projection.py` entry point is now a thin
  CLI facade with compatibility exports.

### Tier 2 Performance Cleanup

- `select_backfill_features()` now builds a same-tag, RT-window compatibility
  neighbor index once instead of running a full-feature compatibility scan for
  every candidate skip decision.
- `backfill_request_sample_stems()` and `owner_matrix` now avoid repeated
  median-owner-area computation within the same feature.
- `owner_matrix` now computes delivery group projection once per feature and
  reuses it for detected/rescued/ambiguous/absent cell projections.
- MS1 product-authority validation now caches overlay trace JSON read/decode/hash
  results per path within a run while keeping sample-level trace checks and
  audit reasons per row.
- Reconciliation gallery build now pre-indexes seed-group cells and exact vs
  legacy overlay rows once per run instead of filtering family-level rows for
  each seed group.
- Owner-backfill now builds a pure `_OwnerBackfillRequestPlan` before primary
  RAW extraction, validation retry, fallback materialization, and candidate
  arbitration run.
- That request plan now lives in
  `xic_extractor/alignment/owner_backfill_request_plan.py` and is reused by
  `process_backend` for per-sample job construction. Process jobs record
  `request_payload_count` separately from `feature_payload_count`; they still
  pass feature payloads rather than duplicating full request items into the
  pickle boundary.
- `tools/diagnostics/backfill_scope_probe.py` now also uses the shared
  owner-backfill request plan for request counts and locality estimates.
  Diagnostics no longer rebuild private per-sample `XICRequest` tuples, and
  per-sample scan-window lookups are reused across unique-window, overlap, and
  chunked-call calculations.
- Standard-peak MS1 authority bundling now caches overlay artifacts per
  `(family_id, trace_summary_tsv, trace_data_json)` within a run. This avoids
  repeated trace-summary reads, trace JSON copies, and hash calculation for
  duplicate gate rows while preserving duplicate output rows.
- MS1 peak claim registry now skips exact/fuzzy duplicate arbitration for
  per-sample buckets with fewer than two claim candidates. Those buckets cannot
  produce replacements, so this only removes impossible hot-path work.
- `changed_row_mode_overlay_review` now computes global trace mode count and
  alignment mode count once per family before the sample trace loop. The
  warning taxonomy and TSV/HTML outputs are unchanged.
- The same changed-row overlay diagnostic now buckets traces by display or
  Gaussian15 mode before rendering mode-aligned plots, preserving trace order
  and multi-mode membership while avoiding a mode-by-all-traces scan.

### Tier 3 Overlay Selection

- Added `xic_extractor/diagnostics/backfill_overlay.py` as the canonical
  seed-specific overlay selector.
- Retained gate, shadow policy, and shadow projection now share one rule:
  - exact seed-specific rows are preferred;
  - legacy family rows are only used by callers that explicitly allow them;
  - duplicate exact rows fail closed by preferring non-support review/conflict
    verdicts over support verdicts.
- Shadow policy still derives product-facing blocker decisions from retained
  gate `challenge_blockers` / `missing_evidence`; overlay rows only supply
  review evidence such as path and shape metrics.

## Diagnostics Architecture Evaluation

The broad diagnostic directory still has many topic-specific writers and older
single-file tools. The current best boundary is not to mass-migrate all helpers
at once:

- Generic TSV/scalar/hash/text mechanics belong in
  `xic_extractor/tabular_io.py`; diagnostics import paths are compatibility
  shims.
- Seed-specific backfill overlay selection belongs in
  `xic_extractor/diagnostics/backfill_overlay.py`.
- Diagnostic CLIs should stay thin when a reusable package runner exists;
  `shadow_production_projection` is now the local example for this pattern.
- Shared overlay trace JSONs can be cached at the path/read/decode/hash layer,
  but family/sample/vector checks remain per row because they are part of the
  diagnostic evidence contract.
- The reconciliation gallery renderer now prepares its HTML subset and lookup
  maps in `_GalleryRenderContext`; the writer remains responsible for rendering,
  while index construction remains responsible for evidence classification.
- `backfill_shadow_policy` and `shadow_production_projection` now share
  `BackfillDecisionExplanation` for diagnostic decision payload shape. Their
  decision taxonomies remain separate; this is serialization hygiene, not a
  product-policy merge.
- `shadow_production_projection` now applies the projected-matrix-value rule
  through `_apply_projection_value_gate()` instead of embedding it inside row
  assembly. The rule remains unchanged: accepted projected writes require a
  positive projected matrix value; review-only identity support can carry a
  positive value as context without writing.
- The same projection runner now classifies current matrix state through
  `_current_projection_state()`, keeping matrix source, blank reason, raw
  status, and review-rescue checks separate from TSV row rendering.
- `scripts/analyze_xic_request_locality.py` remains a validation script rather
  than production logic, but its near-redundant request census now uses an RT
  sweep window before pairwise `_near_redundant` checks. This keeps the
  diagnostic useful for batching/locality decisions without adding RAW behavior.
- `tools/diagnostics/ms1_index_backfill_audit.py` now type-checks with the
  locality script: request comparison optional-area values are explicitly typed,
  and its local `ExtractionConfig` uses `Path` output fields.
- `tools/diagnostics/backfill_scope_probe.py` remains a diagnostic CLI, but its
  request summary/locality model now shares the production request-plan spine.
  The remaining scanner nested-loop warning is expected row expansion over
  already-bucketed request items, not a duplicated request construction path.
- `standard_peak_ms1_authority_bundle` now has two cache layers: trace JSON
  validation cache for product-authority checks, and overlay artifact cache for
  duplicate gate rows before source/allowlist rows are built.
- `changed_row_mode_overlay_review` remains a large topic-specific diagnostic,
  but this slice removed one repeated family-level count inside sample-row
  generation, made mode-aligned plot rendering use a mode-local trace bucket,
  and tightened the shared drift lookup protocol shape used by alignment and
  diagnostics.
- Alignment-domain backfill key helpers belong in
  `xic_extractor/alignment/_backfill_util.py`; generic scalar parsing still
  comes from the neutral helper module.
- Topic-specific `_write_tsv` functions are still acceptable when they encode
  fixed schema order, custom formatting, or report-local row models; migrate
  them on next touch rather than flattening all writer modules in one PR.
- `tools/diagnostics/INDEX.md` remains the navigation and lifecycle surface;
  this slice updated its shared-infrastructure section but did not add, remove,
  or rename diagnostic entry points.

## Deferred Decisions

These remain intentionally out of this cleanup slice:

- Tier 4 decider convergence:
  `backfill_shadow_policy` vs `shadow_production_projection`, and the
  `_same_peak_verdict` family, still need a productization-spec decision. The
  shared explanation payload, current-state helper, and projection value gate
  added here do not merge product policy.
- Deeper owner-backfill worker payload changes should be benchmark-driven.
  Passing full request items across the process boundary may reduce worker-side
  plan recomputation, but it can also increase pickle payload size; keep feature
  payloads until 8RAW evidence shows this recomputation is material.
- Output-only `backfill_*` / provenance fields should not be deleted until a
  reviewer-consumption audit proves they are unused as human review evidence.
- Broader diagnostic lifecycle retirement/promotion audit should be a separate
  read-only inventory against the lifecycle spec, then separate cleanup PRs.
- 8RAW parity/performance validation is the next evidence tier before claiming
  production-candidate performance improvement; 85RAW remains intentionally
  deferred.

## Verification

Focused no-RAW regression shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_alignment_config.py tests/test_alignment_owner_matrix.py tests/test_backfill_scope.py tests/test_retained_backfill_evidence_gate.py tests/test_backfill_shadow_policy_report.py tests/test_shadow_production_projection.py tests/test_backfill_ms1_product_authority.py tests/test_backfill_evidence_projection.py tests/test_backfill_candidate_ms2_product_authority.py tests/test_standard_peak_ms1_authority_bundle.py tests/test_standard_peak_backfill_chunk_consolidation.py
```

Observed result: `186 passed`.

Follow-up candidate shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_shadow_production_projection.py tests\test_backfill_ms1_product_authority.py tests\test_standard_peak_ms1_authority_bundle.py
```

Observed result: `47 passed`.

Gallery/productization follow-up shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_backfill_evidence_reconciliation_gallery.py tests\test_standard_peak_backfill_productization.py tests\test_standard_peak_backfill_machine_pipeline.py
```

Observed result: `54 passed`.

Owner-backfill and diagnostic explanation shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_alignment_owner_backfill.py tests\test_backfill_decision_explanation.py tests\test_backfill_shadow_policy_report.py tests\test_shadow_production_projection.py
```

Observed result: `59 passed`.

Owner-backfill/process request-plan shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_alignment_owner_backfill.py tests\test_alignment_process_backend.py
```

Observed result: `44 passed`.

Shadow projection row-state/value-gate shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_shadow_production_projection.py tests\test_backfill_decision_explanation.py tests\test_backfill_shadow_policy_report.py
```

Observed result: `34 passed`.

Locality / MS1-index diagnostics shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_analyze_xic_request_locality.py tests\test_validate_ms1_scan_index_xic.py tests\test_ms1_index_backfill_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check scripts\analyze_xic_request_locality.py tests\test_analyze_xic_request_locality.py tools\diagnostics\ms1_index_backfill_audit.py tests\test_ms1_index_backfill_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy scripts\analyze_xic_request_locality.py tools\diagnostics\ms1_index_backfill_audit.py
```

Observed results: `7 passed`; ruff passed; mypy passed for 2 source files.

Backfill scope probe request-plan shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_backfill_scope_probe.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\backfill_scope_probe.py tests\test_backfill_scope_probe.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy --follow-imports=skip tools\diagnostics\backfill_scope_probe.py
```

Observed results: `2 passed`; ruff passed; focused mypy passed.

Standard-peak authority artifact-cache shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_standard_peak_ms1_authority_bundle.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\diagnostics\standard_peak_ms1_authority_bundle.py tests\test_standard_peak_ms1_authority_bundle.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\diagnostics\standard_peak_ms1_authority_bundle.py
```

Observed results: `5 passed`; ruff passed; mypy passed.

Claim-registry hot-path shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_alignment_claim_registry_hot_path.py tests\test_alignment_claim_registry.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\claim_registry.py tests\test_alignment_claim_registry_hot_path.py tests\test_alignment_claim_registry.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\claim_registry.py
```

Observed results: `16 passed`; ruff passed; mypy passed.

Peak-candidate score label-impact shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_peak_candidate_score_calibration_report.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\peak_candidate_score_calibration_analysis.py tools\diagnostics\peak_candidate_score_calibration_io.py tests\test_peak_candidate_score_calibration_report.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\peak_candidate_score_calibration_analysis.py tools\diagnostics\peak_candidate_score_calibration_io.py
```

Observed results: `7 passed`; ruff passed; mypy passed for 2 source files.

ASLS fixture-manifest required-key shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_asls_truth_validation_manifests.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\asls_truth_validation_manifests.py tests\test_asls_truth_validation_manifests.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\asls_truth_validation_manifests.py
```

Observed results: `27 passed`; ruff passed; mypy passed for 1 source file.

Locality same-window census shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_analyze_xic_request_locality.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check scripts\analyze_xic_request_locality.py tests\test_analyze_xic_request_locality.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy scripts\analyze_xic_request_locality.py
```

Observed results: `5 passed`; ruff passed; mypy passed for 1 source file.

Family-MS1 review queue ordering shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_family_ms1_backfill_review_report.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\family_ms1_backfill_review_report.py tests\test_family_ms1_backfill_review_report.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\family_ms1_backfill_review_report.py
```

Observed results: `4 passed`; ruff passed; mypy passed for 1 source file.

Changed-row mode-overlay shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_changed_row_mode_overlay_review.py tests\test_alignment_edge_scoring.py tests\test_alignment_owner_clustering.py tests\test_alignment_pipeline.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\changed_row_mode_overlay_review.py tests\test_changed_row_mode_overlay_review.py xic_extractor\alignment\edge_scoring.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\changed_row_mode_overlay_review.py xic_extractor\alignment\edge_scoring.py
```

Observed results: `61 passed`; ruff passed; mypy passed.

Artificial-adduct RT-window candidate shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_alignment_adduct_annotation.py tests\test_multi_tag_adduct_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\adduct_annotation.py tests\test_alignment_adduct_annotation.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\adduct_annotation.py
```

Observed results: `4 passed`; ruff passed; mypy passed for 1 source file.
Scope: no-RAW package cleanup for `match_artificial_adduct_pairs`. The matcher
now snapshots family coordinates once, uses RT-locality to avoid enumerating
impossible family pairs, keeps emitted pairs sorted by original input pair
identity, and treats `adducts` as a reusable iterable. This is a behavior-safe
diagnostic-path performance cleanup, not a production activation change.

Drift-evidence lookup cache shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_alignment_drift_evidence.py tests\test_alignment_edge_scoring.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\drift_evidence.py tests\test_alignment_drift_evidence.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\drift_evidence.py
```

Observed results: `28 passed`; ruff passed; mypy passed for 1 source file.
Scope: no-RAW package cleanup for drift-prior reuse. `DriftEvidenceLookup` now
uses lazy per-sample maps for median RT drift and injection-order lookup instead
of rescanning all points per row/cell. Conflict behavior remains per-sample and
lazy; a conflict on one sample does not block another sample's lookup.

Overlay duplicate-XIC reuse shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_family_ms1_overlay_batch.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\family_ms1_overlay_batch.py tests\test_family_ms1_overlay_batch.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\family_ms1_overlay_batch.py
```

Observed results: `15 passed`; ruff passed; mypy passed for 1 source file.
Scope: no-RAW overlay RAW-access reuse cleanup. `_extract_overlay_traces`
deduplicates identical sample-local XIC requests before RAW extraction and
maps the unique trace back to all original overlay rows. This reduces avoidable
duplicate extraction work without changing rank/cell output identity, summary
schema, or activation behavior.

Targeted reliability summary aggregation shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_targeted_peak_reliability_classifier.py tests\test_targeted_peak_reliability_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\targeted_peak_reliability_classifier.py tests\test_targeted_peak_reliability_classifier.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\targeted_peak_reliability_classifier.py tests\test_targeted_peak_reliability_classifier.py
```

Observed results: `22 passed`; ruff passed; mypy passed for 2 source files.
Scope: no-RAW diagnostics aggregation cleanup. `_summarize_rows` now counts
reliability states with one per-target `Counter` instead of repeated scans.
The new direct classifier test locks target ordering, role propagation, all
four state counts, top reason ordering, and known-exception selection.

Product-authority allowlist indexing shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_backfill_candidate_ms2_product_authority.py tests\test_backfill_ms1_product_authority.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\_backfill_util.py xic_extractor\alignment\backfill_candidate_ms2_product_authority.py xic_extractor\alignment\backfill_ms1_product_authority.py tests\test_backfill_candidate_ms2_product_authority.py tests\test_backfill_ms1_product_authority.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\_backfill_util.py xic_extractor\alignment\backfill_candidate_ms2_product_authority.py xic_extractor\alignment\backfill_ms1_product_authority.py
```

Observed results: `28 passed`; ruff passed; mypy passed for 3 source files.
Scope: no-RAW architecture cleanup for product-authority sidecars. Candidate-MS2
and MS1 authorization paths now share
`_backfill_util.allowlist_rows_by_family_sample_key` for schema-version
validation, required key validation, and duplicate allowlist detection. Added
duplicate-allowlist tests for both sidecars to pin fail-closed error contracts.

ASLS fixture-lock heldout grouping shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_asls_truth_validation_manifests.py tests\test_asls_truth_validation_synthetic.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\asls_truth_validation_manifests.py tests\test_asls_truth_validation_manifests.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\asls_truth_validation_manifests.py
```

Observed results: `39 passed`; ruff passed; mypy passed for 1 source file.
Scope: no-RAW diagnostics cleanup for fixture-lock coverage validation.
`validate_fixture_lock_coverage` now groups heldout rows by fixture class once,
then keeps the existing required-class validation order, calibration/heldout
minimums, S/N strata, peak-width strata, and hard-case coverage checks. It does
not alter fixture manifest/lock schema, hashes, or product behavior.

Changed-row subthreshold report reuse shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_changed_row_mode_overlay_review.py tests\test_ms1_peak_modes_detection_unchanged.py tests\test_subthreshold_sensitivity_report.py tests\test_shared_peak_identity_rt_mode_evidence.py tests\test_shared_peak_identity_peak_hypothesis_selection.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\changed_row_mode_overlay_review.py tests\test_changed_row_mode_overlay_review.py tests\test_ms1_peak_modes_detection_unchanged.py tests\test_subthreshold_sensitivity_report.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\changed_row_mode_overlay_review.py
```

Observed results: `36 passed`; ruff passed; mypy passed for 1 source file.
Scope: no-RAW diagnostics/rendering reuse cleanup. The changed-row mode overlay
review now computes each trace's subthreshold candidate report once per run and
reuses it for sample review rows, family summary rows, and plot markers. This
keeps `subthreshold_candidate_report` import/signature behavior intact and does
not alter review-only RAW overlay authority, output file names, or TSV/HTML
meaning.

Shadow projection matrix-locality shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_shadow_production_projection.py tests\test_standard_peak_backfill_productization.py tests\test_standard_peak_backfill_chunk_consolidation.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\diagnostics\shadow_production_projection.py tests\test_shadow_production_projection.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\diagnostics\shadow_production_projection.py
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_shadow_production_projection.py -q
```

Observed results: broad pytest shard `47 passed`; ruff initially flagged a test
import-order issue, then passed after the import ordering fix; mypy passed for
1 source file; targeted shadow projection test file passed. Scope: no-RAW
diagnostics locality cleanup. The matrix cross-check helper now receives
requested gate `(family, sample)` keys and avoids expanding unrelated identity
rows across all sample columns. Supplied matrix authority, identity/source-family
matching, fallback to production-decision snapshot, output filenames, TSV/JSON
schema, and projection taxonomy remain unchanged.

Subthreshold sensitivity streaming shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_subthreshold_sensitivity_report.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\subthreshold_sensitivity_report.py tests\test_subthreshold_sensitivity_report.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\subthreshold_sensitivity_report.py
```

Observed results: `3 passed`; ruff passed; mypy passed for 1 source file.
Scope: no-RAW diagnostics memory/locality cleanup. The subthreshold sensitivity
report now streams trace candidate aggregation instead of list-materializing the
whole batch before summarization. Detection logic, output filenames, TSV
schemas, and changed-row `subthreshold_candidate_report` semantics remain
unchanged.

Retained gate queue-candidate reuse shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_retained_backfill_evidence_gate.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\diagnostics\retained_backfill_evidence_gate.py tests\test_retained_backfill_evidence_gate.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\diagnostics\retained_backfill_evidence_gate.py
```

Observed results: `8 passed`; ruff passed; mypy passed for 1 source file.
Scope: no-RAW diagnostics output locality cleanup. Retained backfill gate output
writing now builds and sorts missing-overlay queue candidates once, then reuses
that ordered list for the full queue and family-deduplicated review queue.
Gate classification, overlay selection, output filenames, TSV schemas, rank
semantics, and summary counts remain unchanged.

Targeted ISTD matrix-loader sample-column shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_targeted_istd_benchmark.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\targeted_istd_benchmark_loaders.py tests\test_targeted_istd_benchmark.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\targeted_istd_benchmark_loaders.py
```

Observed results: `14 passed`; ruff passed; mypy passed for 1 source file.
Scope: no-RAW diagnostics loader locality cleanup. Targeted ISTD benchmark
matrix loaders now normalize public matrix sample column names once per matrix
read and reuse the `(column, normalized_sample)` pairs across all family rows.
Legacy and clean matrix support, identity provenance, positive-area filtering,
output summaries, and validation-only authority remain unchanged.

Shift-aware source-family accumulator shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_shift_aware_backfill_calibration_pack.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\shift_aware_backfill_calibration_pack.py tests\test_shift_aware_backfill_calibration_pack.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\shift_aware_backfill_calibration_pack.py
```

Observed results: `7 passed`; ruff passed; mypy passed for 1 source file.
Scope: no-RAW diagnostics aggregation cleanup. Shift-aware source-family
summary rows are now accumulated per family while reading summary TSVs instead
of retaining every row and traversing each family group again for source,
shape, and shift summaries. Reference filtering, missing-shape skip behavior,
shape/shift formatting, output filename, and TSV schema remain unchanged.

Primary-area authority single-read shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_alignment_primary_area_authority_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\alignment_primary_area_authority_audit.py tests\test_alignment_primary_area_authority_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\alignment_primary_area_authority_audit.py
```

Observed results: `4 passed`; ruff passed; mypy passed for 1 source file.
Scope: no-RAW diagnostics CLI locality cleanup. The primary-area authority audit
CLI now reads `alignment_cells.tsv` once and reuses one authority-classification
pass for both summary counts and flagged rows. CLI flags, output filenames,
JSON/TSV schemas, and product-authority classification semantics remain
unchanged.

Gaussian15 area-pressure single-read shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_gaussian15_area_pressure_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\gaussian15_area_pressure_audit.py tests\test_gaussian15_area_pressure_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\gaussian15_area_pressure_audit.py
```

Observed results: `2 passed`; ruff passed; mypy passed for 1 source file.
Scope: no-RAW diagnostics CLI locality cleanup. The Gaussian15 area-pressure
audit CLI now reads `peak_candidates.tsv` once and computes summary counts from
the already built row audit. CLI flags, output filenames, JSON/TSV schemas,
readiness labels, and diagnostic-only product action remain unchanged.

Single-dR gate-candidate bucket shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_single_dr_production_gate_decision_report.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\single_dr_production_gate_decision_report.py tools\diagnostics\single_dr_gate_decision_loaders.py tests\test_single_dr_production_gate_decision_report.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\single_dr_production_gate_decision_report.py
```

Observed results: `19 passed`; ruff passed; mypy passed for 1 source file.
Scope: no-RAW diagnostics report-assembly locality cleanup. The single-dR gate
report now builds risk-classification buckets once and reuses them across
gate-candidate summaries, while preserving blocked-family order and
gate-candidate output order. The loader value type now matches nullable numeric
candidate metrics exposed by `_float_or_none()`.

Matrix blast-radius input-bundle shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_matrix_identity_blast_radius.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\analyze_matrix_identity_blast_radius.py tests\test_matrix_identity_blast_radius.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\analyze_matrix_identity_blast_radius.py
```

Observed results: `8 passed`; ruff passed; mypy passed for 1 source file.
Scope: no-RAW read-only diagnostics input-locality cleanup. The matrix identity
blast-radius report now builds the alignment matrix, current review lookup, and
per-family cell-row groups through one private input bundle while preserving
cluster order, sorted sample order, grouping order, output schemas, and
targeted benchmark join behavior.

Owner-backfill economics cell-index shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_owner_backfill_request_economics.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\owner_backfill_request_economics.py tests\test_owner_backfill_request_economics.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\owner_backfill_request_economics.py
```

Observed results: `3 passed`; ruff passed; mypy passed for 1 source file.
Scope: no-RAW diagnostics input-locality cleanup. The owner-backfill request
economics report now builds per-feature cell groups and first-seen sample order
through one private input index while preserving request economics counts,
feature row order, sample order, and output schemas.

Artificial-adduct delta-index shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_alignment_adduct_annotation.py tests\test_alignment_matrix_identity.py::test_artificial_adduct_annotation_does_not_demote_supported_family
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\adduct_annotation.py tests\test_alignment_adduct_annotation.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\adduct_annotation.py
```

Observed results: `5 passed`; ruff passed; mypy passed for 1 source file.
Scope: no-RAW package-level locality cleanup. Artificial-adduct matching now
indexes m/z deltas once and uses a ppm-derived `bisect` range per
RT-compatible family pair while preserving pair order, adduct input order, and
existing artificial-adduct identity behavior.

Combined focused cleanup gate:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_alignment_adduct_annotation.py tests\test_alignment_matrix_identity.py::test_artificial_adduct_annotation_does_not_demote_supported_family tests\test_owner_backfill_request_economics.py tests\test_matrix_identity_blast_radius.py tests\test_single_dr_production_gate_decision_report.py tests\test_shift_aware_backfill_calibration_pack.py tests\test_alignment_primary_area_authority_audit.py tests\test_gaussian15_area_pressure_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\adduct_annotation.py tests\test_alignment_adduct_annotation.py tools\diagnostics\owner_backfill_request_economics.py tests\test_owner_backfill_request_economics.py tools\diagnostics\analyze_matrix_identity_blast_radius.py tests\test_matrix_identity_blast_radius.py tools\diagnostics\single_dr_production_gate_decision_report.py tools\diagnostics\single_dr_gate_decision_loaders.py tests\test_single_dr_production_gate_decision_report.py tools\diagnostics\shift_aware_backfill_calibration_pack.py tests\test_shift_aware_backfill_calibration_pack.py tools\diagnostics\alignment_primary_area_authority_audit.py tests\test_alignment_primary_area_authority_audit.py tools\diagnostics\gaussian15_area_pressure_audit.py tests\test_gaussian15_area_pressure_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\adduct_annotation.py tools\diagnostics\owner_backfill_request_economics.py tools\diagnostics\analyze_matrix_identity_blast_radius.py tools\diagnostics\single_dr_production_gate_decision_report.py tools\diagnostics\shift_aware_backfill_calibration_pack.py tools\diagnostics\alignment_primary_area_authority_audit.py tools\diagnostics\gaussian15_area_pressure_audit.py
```

Observed results: `48 passed`; ruff passed; mypy passed for 7 source files.

Scanner follow-up: `backfill_scope._loose_compatible_neighbor_ids` was reviewed
and left unchanged. It already uses tag grouping plus an RT-sorted neighbor
window with early break, so the scanner hit is not a current bounded cleanup
target.

Latest full no-RAW repo gate:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tools tests scripts gui
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -v --tb=short -x
git diff --check
```

Observed results: ruff passed; mypy passed for `xic_extractor`; pytest
`3637 passed, 1 skipped`; `git diff --check` reported no whitespace errors,
only CRLF conversion warnings.
