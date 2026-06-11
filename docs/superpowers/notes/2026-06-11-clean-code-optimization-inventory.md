# Clean-Code Optimization Inventory

**Date:** 2026-06-11
**Status:** implementation slices landed; latest focused gates passed; prior
repo-wide gates are historical snapshots
**Scope:** XIC_Extractor current worktree on
`codex/backfill-diagnostics-architecture`

## Verdict

The highest-confidence clean-code work for this pass is not broad formatting or
large module splitting. The main actionable hotspots are:

1. Public-contract repair where cleanup removed config fields.
2. Dependency-direction repair where alignment domain modules imported generic
   helpers through `xic_extractor.diagnostics`.
3. Small algorithmic cleanup in owner backfill request fallback lookup.
4. Diagnostics runner relocation where a CLI tool still owned package-level TSV
   loading and domain reconstruction.
5. Repeated trace JSON validation where multiple rescued samples shared one
   overlay artifact.
6. Reconciliation gallery locality and render preparation where seed groups
   repeatedly filtered family-level cells/overlays and the HTML writer mixed
   render-subset preparation with string output.
7. Owner-backfill request planning was inline with RAW extraction, validation
   retry, and candidate arbitration.
8. Shadow/backfill diagnostic decisions used different ad hoc tuple payloads
   for decision reasons, warnings, and production gaps.
9. Locality diagnostics still had a private near-redundant request census that
   compared RT-distant request keys even though those keys can never be near
   redundant.
10. `backfill_scope_probe` still rebuilt owner-backfill request payloads instead
    of using the shared request-plan module used by production and process
    workers.
11. Standard-peak MS1 authority bundling had path-level trace validation
    caching, but still re-read/copied overlay trace artifacts for duplicate gate
    rows pointing at the same family and artifact paths.
12. The MS1 peak claim registry still entered exact/fuzzy duplicate work for
    per-sample buckets with only one claim candidate, even though those buckets
    can never produce duplicate replacements.
13. `changed_row_mode_overlay_review` recomputed family-level global/alignment
    mode counts inside the per-trace sample-row loop.
14. The same diagnostic's mode-aligned plot renderer still scanned every trace
    for every rendered mode, even though each trace's sample row already names
    its display/Gaussian15 modes.
15. GUI target config export accumulated extra target columns with repeated
    list membership checks, even though field order only depends on canonical
    columns plus first-seen extras.
16. `scripts/add_istd_rt_trend.py` computed per-ISTD medians by re-scanning all
    injection rows once per label, even though the source RT data can be
    accumulated once by ordered row and label.
17. `scripts/validate_migration.py` compared validation rows by first listing
    targets and then filtering the full row list once per target, even though
    the report can be built from one target-grouped pass.
18. `scripts/xlsx_to_targets.py` recomputed fuzzy ISTD-to-standard name
    similarity during both ISTD ordering and final assignment, even though the
    standard labels and RT centers are stable within one conversion run.
19. `scripts/local_minimum_param_sweep.py` recomputed per-target failure
    classifications for both workbook highlighting and the `Failures` sheet,
    even though the failure records are stable within one workbook write.
20. `tools/diagnostics/family_ms1_overlay_batch.py` repeatedly resolved the
    same scan-number retention times within one RAW handle during super-window
    grouping, union-window extraction, and trace cropping.
21. `tools/diagnostics/evidence_spine_consistency_analysis.py` matched each
    targeted candidate by scanning all detected/rescued alignment cells for the
    sample, even though the RT tolerance can bound the candidate set first.
22. `tools/diagnostics/asls_truth_validation_inputs.py` validated many hashed
    artifact refs through `_resolve_ref_path()`, and each relative ref rebuilt
    the same `base_path` repo-root lookup before checking candidate paths.
23. `tools/diagnostics/low_ms1_coverage_review_classifier.py` sorted the same
    backfill seed-group `Counter` twice to render the distribution string and
    seed overlay queue rows, even though both projections use the same order.
24. `tools/diagnostics/peak_candidate_score_calibration_analysis.py` grouped
    label impact rows by label and then rescanned each label bucket to split
    selected/rejected raw scores, even though those score buckets can be
    accumulated during the initial label collection pass.
25. `tools/diagnostics/asls_truth_validation_manifests.py` rebuilt the same
    fixture-class required-key tuple for every fixture class, even though the
    tuple depends only on the manifest's legacy/current status.
26. `scripts/analyze_xic_request_locality.py` still rebuilt same-scan
    request-key sets twice per scan-window group and filtered empty detected
    sample names once per review row, even though both can be resolved during
    the initial grouping/loading pass.
27. `tools/diagnostics/family_ms1_backfill_review_report.py` sorted candidate
    rows and then re-sorted the same candidate list with the same key to build
    the overlay image queue, even though the queue is a filtered prefix of the
    already ordered candidates.
28. `tools/diagnostics/subthreshold_sensitivity_report.py` materialized all
    per-trace subthreshold candidates before aggregation, even though the
    report only needs one streaming pass over trace candidate tuples.
29. `xic_extractor/diagnostics/retained_backfill_evidence_gate.py` rebuilt and
    sorted the same missing-overlay queue candidates separately for the full
    queue and the family-deduplicated review queue, even though both outputs use
    the same priority order.
30. `tools/diagnostics/targeted_istd_benchmark_loaders.py` normalized the same
    public matrix sample column names once for `sample_stems` and again for
    every family row/cell value, even though the column normalization is stable
    within one matrix read.
31. `tools/diagnostics/shift_aware_backfill_calibration_pack.py` first
    materialized all source-family summary rows by family, then re-scanned each
    family list to filter non-reference rows, extract source names, collect
    shape values, and collect shift values. This can be summarized with a
    per-family accumulator during the initial read.
32. `tools/diagnostics/alignment_primary_area_authority_audit.py` read the same
    `alignment_cells.tsv` twice in the CLI path: once for summary counts and
    once for flagged rows. Both outputs are derived from the same authority
    classification and can share one row analysis pass.
33. `tools/diagnostics/gaussian15_area_pressure_audit.py` read the same
    `peak_candidates.tsv` twice in the CLI path: once for detailed row audit and
    again for summary counts. The summary is fully derivable from the already
    computed audit rows.
34. `tools/diagnostics/single_dr_production_gate_decision_report.py` scanned
    the sorted `families` list separately for every gate-candidate summary even
    though each gate selection is keyed only by stable `risk_classification`.
    A single classification bucket pass can feed all gate summaries while
    preserving family order.

These items are behavior-preserving, testable without RAW, and improve the
architecture without starting a large migration.

## Implemented In This Pass

- Restored legacy/no-op `AlignmentConfig` fields:
  `mz_bucket_neighbor_radius`, `anchor_priorities`, and
  `anchor_min_scan_support_score`.
  - Reason: config keys are public surface even if current computation no
    longer consumes them.
  - Test surface: `tests/test_alignment_config.py`.
- Added neutral shared helper module `xic_extractor/tabular_io.py`.
  - `xic_extractor/diagnostics/diagnostic_io.py` and
    `tools/diagnostics/diagnostic_io.py` now re-export it as compatibility
    shims.
  - Alignment modules now import generic TSV/scalar helpers from the neutral
    module, not through the diagnostics namespace.
  - Test surface: `tests/test_diagnostic_io.py` and alignment import-boundary
    checks in `tests/test_alignment_config.py`.
- Optimized owner backfill validation fallback lookup.
  - Previous shape: each primary fallback check scanned validation-pending
    request items for the sample.
  - New shape: validation-pending `(feature_family_id, sample_stem)` keys are
    recorded in a set when pending validation work is queued.
  - Complexity: repeated O(n) lookup per request becomes O(1) membership.
  - Test surface: `tests/test_alignment_owner_backfill.py`.
- Moved `shadow_production_projection` TSV/domain loading into the package
  runner.
  - `tools/diagnostics/shadow_production_projection.py` is now a CLI facade
    with argparse, stderr handling, console output, and compatibility exports.
  - `xic_extractor/diagnostics/shadow_production_projection.py` now owns
    `run_shadow_production_projection()` plus private TSV-to-domain
    reconstruction helpers.
  - Test surface: direct package runner and CLI smoke coverage in
    `tests/test_shadow_production_projection.py`.
- Added per-run trace JSON validation caches for MS1 authority paths.
  - `xic_extractor/alignment/backfill_ms1_product_authority.py` reuses one
    parsed/hash-validated overlay trace JSON per path while preserving
    per-sample validation and audit reasons.
  - `xic_extractor/diagnostics/standard_peak_ms1_authority_bundle.py` applies
    the same path-level cache during standard-peak authority authorization.
  - Test surface: shared-trace multi-sample cache characterization in
    `tests/test_backfill_ms1_product_authority.py` and
    `tests/test_standard_peak_ms1_authority_bundle.py`.
- Reused standard-peak overlay artifacts inside the authority bundle.
  - Duplicate gate rows for the same `(family_id, trace_summary_tsv,
    trace_data_json)` now share one trace-summary read, one trace JSON copy, and
    one trace-data hash within a run.
  - Duplicate gate rows still produce duplicate source/allowlist rows; this is
    I/O reuse only, not deduplication.
  - Test surface: duplicate-gate artifact-cache characterization in
    `tests/test_standard_peak_ms1_authority_bundle.py`.
- Skipped impossible MS1 peak claim-registry duplicate work for single-candidate
  sample buckets.
  - Exact duplicate keys and fuzzy compatibility groups are now only evaluated
    when a sample bucket has at least two detected/rescued finite peak claims.
  - Behavior is unchanged: a single claim cannot produce an exact or fuzzy
    duplicate replacement.
  - Test surface: hot-path operation-count characterization in
    `tests/test_alignment_claim_registry_hot_path.py` plus existing registry
    behavior coverage in `tests/test_alignment_claim_registry.py`.
- Reused per-family mode counts in `changed_row_mode_overlay_review`.
  - `_sample_review_rows()` now computes global trace mode count and alignment
    mode count once per family instead of once per trace.
  - This preserves sample-level warning logic and output rows; it only removes
    repeated family-level set construction.
  - The drift lookup protocol now exposes `source` as a read-only property,
    matching the concrete `DriftEvidenceLookup` implementation and allowing the
    diagnostics tool to type-check directly.
  - Test surface: operation-count characterization plus existing mode overlay
    review tests in `tests/test_changed_row_mode_overlay_review.py`, with
    alignment drift-lookup protocol coverage in the focused shard.
- Bucketed mode-aligned plot traces by mode before rendering.
  - `_render_mode_aligned_plot()` now builds trace entries per display or
    Gaussian15 mode once, preserving trace order and multi-mode membership.
  - The plot loop only iterates traces associated with the current mode instead
    of scanning every family trace for every mode.
  - This is diagnostics-only rendering locality; TSV/HTML schema and warning
    decisions are unchanged.
  - Test surface: private bucket-order/membership characterization plus existing
    render-plot coverage in `tests/test_changed_row_mode_overlay_review.py`.
- Optimized GUI target config fieldname accumulation.
  - `gui.config_io._target_write_fieldnames()` now tracks seen field names in a
    set while preserving the existing output order: canonical target fields
    first, then extra fields in first-seen order.
  - The PyInstaller bundle path lookup now uses `getattr(sys, "_MEIPASS")`,
    matching runtime behavior while allowing focused mypy on the GUI helper.
  - Test surface: direct field-order characterization in
    `tests/test_gui_config_io.py`.
- Optimized ISTD RT trend median accumulation.
  - `scripts/add_istd_rt_trend.py` now builds QC/all RT value pools in one pass
    over ordered injections and each sample's actual ISTD RT entries, then
    applies the same "QC pool if at least three values, otherwise all values"
    median rule per label.
  - `InjectionOrderRow` now records the row contract used by the reader,
    median helper, and trend sheet writer, closing the focused script mypy gap.
  - Remaining scanner hits in this script are either the output matrix write
    itself (`ordered_rows x istd_labels`) or the one-pass actual RT entry scan;
    they are not the old label-by-label full row rescan.
  - Test surface: direct median-rule characterization in
    `tests/test_add_istd_rt_trend.py`.
- Optimized validation migration target grouping.
  - `scripts/validate_migration.py` now groups `ValidationRow` objects by
    target once before building target reports and failure records, preserving
    sorted target report order and per-target input row order.
  - The `merge_old_new_rows()` key-union invariant is now explicit via a source
    row variable, closing the focused script mypy narrowing gap without changing
    merge output.
  - Remaining scanner hits in this script are the expected sample-target output
    expansion, old wide-row CSV expansion, or one sorted key pass; they are not
    the old repeated full-row filtering by target.
  - Test surface: multi-target report-order characterization in
    `tests/test_validate_migration.py`.
- Precomputed ISTD pairing match plans in `scripts/xlsx_to_targets.py`.
  - Standard normalized labels and RT centers are now built once, and each ISTD
    receives one immutable match plan containing the name-only ordering score
    plus RT-gated candidate standards.
  - Assignment still preserves the existing semantics: ISTDs are processed by
    descending name score, claimed standards are skipped, first standard wins a
    tied candidate score, ISTD rows keep `istd_pair` blank, and the hard RT gate
    still emits manual-pair warnings.
  - Remaining scanner hits in this script are the one-time match-plan build,
    the reduced candidate scan, and Excel block/row parser expansion; they are
    not the old duplicated fuzzy-score computation.
  - Test surface: direct ISTD pair assignment and RT-gate characterization in
    `tests/test_xlsx_to_targets.py`.
- Reused local-minimum sweep failure records across workbook sheets.
  - `scripts/local_minimum_param_sweep.py` now computes each
    `PerTargetScoreRow` failure record once per workbook write and reuses the
    result for `PerTarget` row highlighting and `Failures` sheet expansion.
  - Focused script typing gaps found during the shard were closed with explicit
    grid constant typing, detected-program narrowing, and scalar narrowing in
    `_safe_float()`.
  - Remaining scanner hits in this script are sweep execution loops, manual
    workbook expansion, output row expansion, and run-config key sorting; they
    are not the old duplicate failure classification path.
  - Test surface: failure sheet characterization plus existing local-minimum
    sweep coverage in `tests/test_local_minimum_param_sweep.py`.
- Cached overlay scan-number retention-time lookups per RAW handle.
  - `tools/diagnostics/family_ms1_overlay_batch.py` now shares one
    scan-number to retention-time cache across super-window grouping,
    union-window construction, and crop-back-to-original-window logic.
  - This preserves the existing overlay super-window algorithm and output
    traces; it only removes repeated `retention_time_for_scan()` calls for the
    same scan number in one sample batch.
  - Focused tool typing gaps found during the shard were closed with an
    explicit RAW batch protocol and output union annotation.
  - Test surface: lookup-count characterization plus existing overlay batch
    coverage in `tests/test_family_ms1_overlay_batch.py`.
- Indexed evidence-spine alignment cells by sample and RT.
  - `tools/diagnostics/evidence_spine_consistency_analysis.py` now builds one
    RT-sorted detected/rescued cell index per sample and passes only the
    candidate's `rt +/- match_rt_min` window into the existing
    `_best_alignment_match()` tie-breaker.
  - Match semantics are unchanged: ppm filtering, primary-consolidation
    preference, RT delta ordering, and family-id tie-breaks still live in
    `_best_alignment_match()`.
  - Focused tool typing now reflects the actual 5-field match candidate tuple.
  - Test surface: RT-window index characterization plus existing evidence-spine
    consistency behavior tests in `tests/test_evidence_spine_consistency.py`.
- Cached ASLS truth-validation ref repo-root lookup by `base_path`.
  - `tools/diagnostics/asls_truth_validation_inputs.py` still resolves relative
    refs using the same candidate order: repo root first, then the manifest
    sibling path. It no longer walks parents to find the repo root once per
    hashed ref when many refs share the same `base_path`.
  - Hash validation, missing-path handling, and absolute-path behavior are
    unchanged.
  - Test surface: private ref-resolution cache characterization plus existing
    ASLS validation behavior tests in `tests/test_asls_truth_validation_inputs.py`.
- Reused sorted low-MS1 backfill seed groups across distribution and queue
  projections.
  - `tools/diagnostics/low_ms1_coverage_review_classifier.py` now sorts the
    seed-group counter once and passes the ordered groups to both
    `_format_seed_distribution()` and `_seed_overlay_rows()`.
  - Output ordering is unchanged: descending count, then lexical seed key.
  - Test surface: shared-order characterization plus existing low-MS1 coverage
    audit behavior tests in `tests/test_low_ms1_assessable_coverage_audit.py`.
- Pre-indexed reconciliation gallery cells and overlay rows by
  `(feature_family_id, seed_group_id)`.
  - Previous shape: each seed group filtered family-level cells and overlay rows
    independently.
  - New shape: one per-run seed-group cell index preserves family cell order,
    and overlay rows are split into exact seed-group rows vs legacy family
    fallback rows once.
  - Test surface: ordering/scope characterization plus existing gallery tests in
    `tests/test_backfill_evidence_reconciliation_gallery.py`.
- Extracted gallery render preparation into `_GalleryRenderContext`.
  - `write_reconciliation_gallery_html()` now delegates render-subset selection,
    shadow/projection lookup maps, representative lookup maps, and target
    benchmark context filtering to a private context builder.
  - HTML/TSV schemas and gallery row behavior are unchanged.
  - Test surface: existing HTML smoke/accessibility/projection/gallery tests in
    `tests/test_backfill_evidence_reconciliation_gallery.py`.
- Extracted owner-backfill request planning into `_OwnerBackfillRequestPlan`.
  - `build_owner_backfill_result()` now receives sample-bucketed request items
    from a pure plan helper before RAW extraction starts.
  - Primary extraction and validation retry are still unchanged; this slice only
    separates "what to query" from "how to extract/arbitrate it".
  - Test surface: no-RAW request-plan characterization plus the existing
    owner-backfill batching/validation/super-window tests in
    `tests/test_alignment_owner_backfill.py`.
- Promoted owner-backfill request planning to a shared alignment module.
  - `xic_extractor/alignment/owner_backfill_request_plan.py` now owns
    `OwnerBackfillRequestItem`, `OwnerBackfillRequestPlan`, and
    `build_owner_backfill_request_plan()`.
  - `process_backend` uses the same plan to build per-sample jobs and records
    `request_payload_count` separately from `feature_payload_count`, so multi-
    seed features are visible without duplicating feature payloads.
  - `features_for_sample()` deduplicates multi-seed features by object identity
    in O(n) while preserving feature order.
  - Test surface: process job parity coverage in
    `tests/test_alignment_process_backend.py`.
- Updated `tools/diagnostics/backfill_scope_probe.py` to use the shared
  owner-backfill request plan.
  - `_request_summary()` and `_locality_summary()` now consume the same
    sample-bucketed request items as production/process code, instead of
    rebuilding private `XICRequest` tuples per sample.
  - Locality scan-window lookup is cached per request within a sample before
    computing unique windows, overlap components, and chunked raw call counts.
  - The remaining scanner hit on `backfill_scope_probe.py` is now the expected
    linear `sample -> request items` output pass, not the old repeated
    sample-feature request reconstruction.
  - Test surface: `tests/test_backfill_scope_probe.py`.
- Shared the backfill scope probe TSV writer implementation.
  - `tools/diagnostics/backfill_scope_probe.py` keeps its private
    `_write_tsv(path, rows)` helper but delegates non-empty TSV serialization
    to `tools.diagnostics.diagnostic_io.write_tsv` with
    `extrasaction="raise"`.
  - Parent-directory creation, empty-output behavior, first-row dynamic field
    order, Python-style bool conversion, and later-row extra-key failure are
    unchanged.
  - Test surface: existing backfill scope probe tests plus focused writer
    formatting and extra-field characterization.
- Added `xic_extractor/diagnostics/backfill_decision_explanation.py` for shared
  diagnostic decision payloads.
  - `backfill_shadow_policy` and `shadow_production_projection` now share the
    same reason/warning/gap serialization shape while keeping separate decision
    taxonomies and token semantics.
  - Test surface: table-driven serialization coverage in
    `tests/test_backfill_decision_explanation.py`, plus unchanged shadow policy
    and projection output expectations.
- Extracted the shadow projection value gate into `_apply_projection_value_gate`.
  - `_projection_row()` no longer owns the accept-to-context downgrade when an
    accepted row lacks positive projected area.
  - This preserves the product rule that projection `accept` requires a
    positive projected matrix value while keeping review-only
    `identity_supported_review` context rows visible.
  - Test surface: existing projection characterization in
    `tests/test_shadow_production_projection.py`.
- Extracted current matrix/projection state into `_current_projection_state`.
  - `_projection_row()` now renders an already-classified current state instead
    of mixing matrix source, blank reason, raw status, and review-rescue checks
    into row assembly.
  - TSV fields, reason tokens, and projected-write behavior are unchanged.
  - Test surface: existing projection characterization in
    `tests/test_shadow_production_projection.py`.
- Shared TSV header / positive-int / identity-family-key helpers in
  `xic_extractor/tabular_io.py`.
  - `shadow_production_projection` and
    `standard_peak_backfill_productization` now use the same helpers for
    current matrix value lookup from `alignment_matrix.tsv` +
    `alignment_matrix_identity.tsv`.
  - Matrix identity key expansion still preserves `peak_hypothesis_id` first,
    appends `source_feature_family_ids`, and deduplicates in first-seen order.
  - TSV schemas, decision tokens, matrix/projection policy, and activation
    behavior are unchanged.
  - Test surface: canonical helper characterization in
    `tests/test_diagnostic_io.py` plus existing projection/productization tests.
- Extended `read_tsv_with_header()` for product-authority authorizers.
  - `tools/diagnostics/authorize_backfill_ms1_pattern_evidence.py` and
    `tools/diagnostics/authorize_backfill_candidate_ms2_pattern_evidence.py`
    now use the shared TSV header reader with explicit required-column
    validation and `utf-8-sig` input handling.
  - Authorization allowlist rules, output columns, audit rows, summary JSON,
    and CLI exit/error behavior are unchanged.
  - Test surface: canonical BOM/missing-column helper coverage plus existing
    MS1 and Candidate-MS2 product-authority tests.
- Shared the Targeted NL dropout root-cause TSV writer implementation.
  - `tools/diagnostics/targeted_nl_dropout_root_cause_writers.py` keeps the
    legacy `_write_tsv(path, fieldnames, rows)` symbol for
    `targeted_nl_dropout_root_cause_audit.__all__` compatibility, but delegates
    TSV serialization to `tools.diagnostics.diagnostic_io.write_tsv`.
  - `_format_value()`, TSV columns, JSON, Markdown, and audit classification
    behavior are unchanged.
  - Test surface: existing targeted NL dropout root-cause audit tests.
- Shared the area-integration uncertainty TSV writer implementation.
  - `tools/diagnostics/area_integration_uncertainty_writers.py` keeps the
    legacy `_write_tsv(path, fields, rows)` symbol for
    `area_integration_uncertainty_audit.__all__` compatibility, but delegates
    TSV serialization to `tools.diagnostics.diagnostic_io.write_tsv`.
  - The custom `.10g` float formatting, LF line terminator, TSV columns, JSON,
    Markdown, and audit classification behavior are unchanged.
  - Test surface: existing area-integration uncertainty audit tests.
- Shared the targeted ISTD benchmark TSV writer implementation.
  - `tools/diagnostics/targeted_istd_benchmark_writers.py` keeps its private
    `_write_tsv(path, fieldnames, rows)` helper but delegates TSV
    serialization to `tools.diagnostics.diagnostic_io.write_tsv`.
  - The existing `_format_value()` controls boolean and float formatting, so
    summary/match TSV columns, JSON payload, Markdown, and benchmark decisions
    are unchanged.
  - Test surface: existing targeted ISTD benchmark tests.
- Shared the family-MS1 backfill review TSV writer implementation.
  - `tools/diagnostics/family_ms1_backfill_review_writers.py` keeps its
    private `_write_tsv(path, rows, fields)` helper but delegates TSV
    serialization to `tools.diagnostics.diagnostic_io.write_tsv`.
  - The existing `_format_value()`, LF line terminator, candidate/queue/summary
    TSV columns, JSON, Markdown, and review classification behavior are
    unchanged.
  - Test surface: existing family-MS1 backfill review report tests.
- Shared the single-dR gate decision TSV writer implementation.
  - `tools/diagnostics/single_dr_gate_decision_writers.py` keeps its private
    `_write_tsv(path, rows, fieldnames=...)` helper but delegates TSV
    serialization to `tools.diagnostics.diagnostic_io.write_tsv`.
  - A small local `_format_value()` preserves the previous `csv.writer`
    conversion contract: `None` becomes empty and booleans stay Python-style
    `True` / `False` rather than the diagnostic default `TRUE` / `FALSE`.
  - TSV columns, JSON, Markdown, gate-candidate ordering, activation decisions,
    and changed-row bundle behavior are unchanged.
  - Test surface: existing single-dR production gate decision report tests plus
    a focused detected-cell bool-format characterization.
- Shared the seed-aware backfill review TSV writer implementation.
  - `tools/diagnostics/seed_aware_backfill_review_writers.py` keeps the legacy
    `_write_tsv(path, rows, fields)` symbol for
    `seed_aware_backfill_review.__all__` compatibility, but delegates TSV
    serialization to `tools.diagnostics.diagnostic_io.write_tsv`.
  - The existing `_format_value()`, `TRUE` / `FALSE` bool formatting, `.6g`
    float formatting, LF line terminator, family/blast-radius TSV columns,
    JSON, Markdown, and review/blast-radius decisions are unchanged.
  - Test surface: existing seed-aware backfill review tests plus focused
    family/blast-radius row-value formatter characterization.
- Shared the RT-normalization anchor TSV writer implementation.
  - `tools/diagnostics/rt_normalization_anchor_writers.py` keeps its private
    `_write_tsv(path, fieldnames, rows)` helper but delegates TSV serialization
    to `tools.diagnostics.diagnostic_io.write_tsv`.
  - The existing `_format_value()`, `TRUE` / `FALSE` bool formatting, finite
    float formatting, default CSV line terminator, summary/sample/anchor/
    leave-one-out/family TSV columns, JSON, and Markdown behavior are unchanged.
  - Test surface: existing RT-normalization anchor tests plus focused
    `used_in_model` bool-format characterization.
- Extended the shared TSV writer with schema-strict mode.
  - `xic_extractor/tabular_io.write_tsv()` and `write_delimited_rows()` now
    accept `extrasaction="ignore" | "raise"`; the default stays `ignore` to
    preserve already-migrated writer behavior.
  - `extrasaction="raise"` restores the bare `csv.DictWriter` failure surface
    needed by schema-strict diagnostics writers before they can safely delegate
    to the shared helper.
  - Test surface: canonical diagnostic IO tests for default field-order output,
    LF line terminator, CSV output, and extra-field rejection.
- Shared the CWT peak-candidate audit TSV writer implementation.
  - `tools/diagnostics/cwt_peak_candidate_audit_writers.py` now writes summary,
    group, far-alternative, and CWT-only TSVs through
    `tools.diagnostics.diagnostic_io.write_tsv` with `extrasaction="raise"`.
  - Summary schema strictness, `.5f` optional-float formatting, TSV columns,
    JSON, Markdown, CWT agreement classes, and conditioned classes are
    unchanged.
  - Test surface: existing CWT peak-candidate audit tests plus canonical
    `extrasaction="raise"` helper characterization.
- Shared the peak-candidate score calibration TSV writer implementation.
  - `tools/diagnostics/peak_candidate_score_calibration_writers.py` now writes
    summary, risk-row, and label-impact TSVs through
    `tools.diagnostics.diagnostic_io.write_tsv` with `extrasaction="raise"`.
  - A local `_format_value()` preserves the previous raw `csv.writer`
    conversion contract for summary values while the existing `.5f` optional
    score formatting remains unchanged.
  - Summary schema strictness, TSV columns, JSON, Markdown, risk rows, and
    label-impact rows are unchanged.
  - Test surface: existing peak-candidate score calibration tests plus focused
    summary extra-key rejection characterization.
- Shared the owner-backfill request economics TSV writer implementation.
  - `tools/diagnostics/owner_backfill_request_economics.py` keeps dynamic
    first-row field ordering and empty-output behavior, but delegates non-empty
    TSV serialization to `tools.diagnostics.diagnostic_io.write_tsv` with
    `extrasaction="raise"`.
  - A local `_format_value()` preserves previous raw `csv.writer` conversion,
    including Python-style `True` / `False`, while later-row extra keys still
    fail.
  - Summary/features TSV columns, JSON, Markdown, request-count logic, and
    ordering behavior are unchanged.
  - Test surface: existing owner-backfill request economics tests plus focused
    bool-format and later extra-key rejection characterization.
- Shared the matrix identity blast-radius TSV writer implementation.
  - `tools/diagnostics/analyze_matrix_identity_blast_radius.py` keeps its
    private `_write_tsv(path, columns, rows)` helper but delegates TSV
    serialization to `tools.diagnostics.diagnostic_io.write_tsv`.
  - A local `_tsv_value()` preserves the previous fixed-column projection:
    booleans are `TRUE` / `FALSE`, `None` becomes empty, numbers use raw csv
    string conversion, and non-column row keys remain ignored.
  - TSV columns, JSON payload, machine-decision projection, targeted benchmark
    joins, and ordering behavior are unchanged.
  - Test surface: existing matrix identity blast-radius tests plus focused
    writer value-format characterization.
- Shared the chrom peak segment gate TSV writer implementation.
  - `tools/diagnostics/chrom_peak_segment_candidate_gate.py` keeps its private
    `_write_tsv(path, rows, fieldnames)` helper but delegates TSV serialization
    to `tools.diagnostics.diagnostic_io.write_tsv` with
    `extrasaction="raise"`.
  - Explicit fieldnames, extra-key rejection, raw `csv.writer` value conversion,
    changed-row/review-row TSV columns, manifest JSON, and gate decisions are
    unchanged.
  - `_rt_reference_delta()` now annotates its optional midpoint path explicitly,
    closing the focused mypy check without changing behavior.
  - Test surface: existing chrom peak segment gate tests plus focused writer
    value-format and extra-key rejection characterization.
- Shared the untargeted alignment guardrail comparison CSV writer
  implementation.
  - `tools/diagnostics/untargeted_alignment_guardrail_io.py` keeps its private
    `_write_dict_csv(path, rows)` helper but delegates non-empty CSV
    serialization to `tools.diagnostics.diagnostic_io.write_delimited_rows` with
    `extrasaction="raise"`.
  - Required output-path validation, parent-directory creation, empty-output
    behavior, first-row dynamic field order, raw value conversion, and later-row
    extra-key failure are unchanged.
  - Test surface: existing untargeted alignment guardrail tests plus focused
    CSV writer contract characterization.
- Shared the selected-envelope review queue TSV writer implementation.
  - `tools/diagnostics/selected_envelope_review_queue.py` keeps its private
    `_write_tsv(path, fieldnames, rows)` helper but delegates TSV serialization
    to `tools.diagnostics.diagnostic_io.write_tsv`.
  - Parent-directory creation, header-only empty output, explicit field order,
    extra-key ignore behavior, LF line terminator, and tab/newline sanitization
    are unchanged.
  - Test surface: existing selected-envelope review queue tests plus focused
    writer sanitize/extra-field/header characterization.
- Shared the MS1 peak-group NL-scope gate TSV writer implementation.
  - `tools/diagnostics/ms1_peak_group_nl_scope_gate.py` keeps its private
    `_write_tsv(path, rows, fieldnames)` helper but delegates TSV serialization
    to `tools.diagnostics.diagnostic_io.write_tsv` with
    `extrasaction="raise"`.
  - Explicit fieldnames, extra-key rejection, header-only empty output, raw
    value conversion, review/context TSV schemas, and manifest/gate decisions
    are unchanged.
  - Test surface: existing MS1 peak-group NL-scope gate tests plus focused
    writer field/value/extra-key characterization.
- Shared the targeted GT alignment audit CSV writer implementation.
  - `tools/diagnostics/targeted_gt_alignment_audit_writers.py` keeps its
    private `_write_dict_csv(path, rows)` helper but delegates non-empty CSV
    serialization to `tools.diagnostics.diagnostic_io.write_delimited_rows` with
    `extrasaction="raise"`.
  - Empty-output behavior, first-row field order, formula-escape protection,
    raw value conversion, later-row extra-key failure, report rendering, SVG
    rendering, and audit output schemas are unchanged.
  - Adjacent type-only cleanup in
    `tools/diagnostics/targeted_gt_alignment_audit_utils.py` annotates the
    iterable ID joiner and float parser to close the focused mypy shard.
  - Test surface: existing targeted GT alignment audit tests plus focused CSV
    writer contract characterization.
- Shared the alignment validation TSV writer implementation.
  - `xic_extractor/alignment/validation_writer.py` keeps its private
    `_write_tsv(path, columns, rows)` helper but delegates TSV serialization to
    `xic_extractor.tabular_io.write_tsv`.
  - Parent-directory creation, returned path, explicit column order,
    header-only empty output, ignored extra keys, value formatting, formula
    escaping, and validation summary/match TSV schemas are unchanged.
  - Test surface: existing alignment validation writer tests plus focused
    private-writer header/extra-field characterization.
- Shared the discovery candidate/review CSV writer implementation.
  - `xic_extractor/discovery/csv_writer.py` now routes both
    `write_discovery_candidates_csv()` and `write_discovery_review_csv()`
    through a private `_write_csv(path, rows, columns)` helper backed by
    `xic_extractor.tabular_io.write_delimited_rows`.
  - Parent-directory creation, returned path, candidate sorting, full/review
    column contracts, header-only empty output, value formatting, tuple
    serialization, CSV quoting, formula escaping, and review-note rendering are
    unchanged.
  - Test surface: existing discovery candidate/review CSV tests.
- Shared the alignment debug TSV writer implementation.
  - `xic_extractor/alignment/debug_writer.py` keeps its private
    `_write_tsv(path, fieldnames, rows)` helper but delegates TSV serialization
    to `xic_extractor.tabular_io.write_tsv`.
  - Parent-directory creation, returned path, explicit field order,
    header-only empty output, ignored extra keys, LF line terminator, formula
    escaping, and debug TSV schemas are unchanged.
  - Test surface: existing alignment debug writer tests plus focused
    private-writer header/extra-field/LF characterization.
- Shared the identity-coherence output TSV writer implementation.
  - `xic_extractor/alignment/identity_coherence/output_writers.py` keeps its
    private `_write_tsv(path, columns, rows)` helper but delegates TSV
    serialization to `xic_extractor.tabular_io.write_tsv`.
  - Parent-directory creation, returned path, explicit columns, header-only
    empty output, ignored extra keys, raw value conversion, public facade
    exports, and identity-coherence TSV schemas are unchanged.
  - Test surface: existing identity-coherence output writer tests plus focused
    private-writer raw-conversion characterization.
- Shared the identity-coherence validation TSV writer implementation.
  - `xic_extractor/alignment/identity_coherence_validation/outputs.py` now
    writes validation summary and V0.4 acceptance TSV artifacts through
    `xic_extractor.tabular_io.write_tsv`.
  - Validation summary still relies on the caller-created output root, acceptance
    TSV still creates its parent directory and uses LF line terminators, and raw
    value conversion, markdown outputs, acceptance decisions, and diagnostic-only
    report wording are unchanged.
  - Test surface: existing identity-coherence validation output tests plus
    focused summary/acceptance TSV writer characterization.
- Shared the identity-coherence decoy-manifest proposal TSV writer
  implementation.
  - `xic_extractor/alignment/identity_coherence_validation/decoy_manifest_proposal.py`
    keeps `_write_manifest_rows(path, rows)` but delegates TSV serialization to
    `xic_extractor.tabular_io.write_tsv`.
  - Parent-directory creation, fixed control-manifest columns, header-only empty
    output, ignored extra keys, raw value conversion, proposal filtering, and
    controls-manifest reader round-trip behavior are unchanged.
  - Test surface: existing decoy-manifest proposal tests plus focused
    private-writer projection characterization.
- Shared the instrument-QC sequence manifest TSV/CSV writer implementation.
  - `xic_extractor/instrument_qc/sequence_manifest_writers.py` now writes the
    docs-derived sequence manifest TSV through `write_tsv` and the matched
    injection-order CSV through `write_delimited_rows`.
  - Parent-directory creation, fixed manifest/injection-order columns,
    header-only empty output, matched-only injection-order filtering, JSON
    summary payload, and Markdown review output are unchanged.
  - Test surface: existing sequence-manifest writer/CLI tests plus focused
    empty-output header characterization.
- Shared the RT prior pending-library CSV writer implementation.
  - `xic_extractor/rt_prior_library.py` keeps `write_pending_update()` but now
    delegates pending CSV serialization to `xic_extractor.tabular_io.write_delimited_rows`.
  - Pending-path derivation, parent-directory creation, non-mutation of the main
    library, header-only empty output, optional-float formatting, and load
    round-trip behavior are unchanged.
  - Test surface: existing RT prior library tests plus focused empty-pending
    header characterization.
- Shared the instrument-QC calibration maturity gate TSV writer implementation.
  - `xic_extractor/instrument_qc/calibration_maturity_gate_io.py` keeps
    `write_calibration_maturity_gate_tsv()` but now delegates fixed-column TSV
    serialization to `xic_extractor.tabular_io.write_tsv`.
  - Parent-directory creation, fixed maturity-gate columns, semicolon-joined
    blockers, raw string conversion, and header-only empty output are
    unchanged.
  - Test surface: existing maturity-gate decision tests plus focused writer
    schema/header characterization.
- Shared the instrument-QC calibrated trend TSV writer implementation.
  - `xic_extractor/instrument_qc/calibration_writers.py` keeps
    `write_calibrated_trend_tsv()` but now delegates fixed-column TSV
    serialization to `xic_extractor.tabular_io.write_tsv`.
  - Parent-directory creation, fixed calibrated-trend columns, semicolon-joined
    flags, raw `str()` conversion for numeric values, and header-only empty
    output are unchanged.
  - Test surface: existing calibration writer tests plus focused numeric string
    conversion and empty-output header characterization.
- Shared the biological ISTD RT transfer audit TSV writer implementation.
  - `xic_extractor/instrument_qc/rt_transfer_audit_io.py` keeps
    `write_biological_istd_transfer_audit_tsv()` but now delegates fixed-column
    TSV serialization to `xic_extractor.tabular_io.write_tsv`.
  - Parent-directory creation, fixed transfer-audit columns, existing
    `None -> ""` and `.6g` float formatting, summary JSON, and Markdown review
    output are unchanged.
  - Test surface: existing transfer-audit/CLI tests plus focused writer schema,
    value-format, and empty-output header characterization.
- Shared the instrument-QC calibration product TSV writer implementations.
  - `xic_extractor/instrument_qc/calibration_product_writers.py` now routes
    calibration evidence, matrix RT preview, RT drift model,
    leave-one-anchor-out, and matrix response preview TSVs through one private
    `_write_tsv_rows()` helper backed by `xic_extractor.tabular_io.write_tsv`.
  - Fixed artifact schemas, parent-directory creation, enum serialization,
    boolean `true`/`false`, `None -> ""`, and list semicolon-join formatting are
    unchanged because `_row_to_dict()` remains the single formatting owner.
  - Test surface: existing calibration product writer tests plus focused
    cross-writer schema/value and header-only empty-output characterization.
- Shared the base instrument-QC TSV writer implementations.
  - `xic_extractor/instrument_qc/writers.py` now routes trend, diagnostics, and
    HCD audit TSVs through one private `_write_tsv_rows()` helper backed by
    `xic_extractor.tabular_io.write_tsv`.
  - Fixed TSV schemas, parent-directory creation, raw-path string conversion,
    tuple semicolon-join fields, `None -> ""`, and legacy `str()` numeric
    conversion are unchanged through the module-local `_format_csv_value()`.
  - Test surface: existing instrument-QC writer tests plus focused HCD writer
    value-format and cross-writer empty-output header characterization.
- Shared the instrument-QC lifecycle append TSV rewrite implementation.
  - `xic_extractor/instrument_qc/lifecycle.py` now rewrites lifecycle run,
    SDOLEK, MixSTDs, and blank TSVs through `xic_extractor.tabular_io.write_tsv`
    while preserving the existing temp-file replace flow.
  - Existing-row projection, duplicate fingerprint detection, lifecycle
    summary generation, header-only blank TSV output, and lifecycle row numeric
    formatting are unchanged.
  - Test surface: existing lifecycle append/duplicate tests plus focused row
    value/header characterization.
- Shared the target-pair RT calibration TSV writer implementation.
  - `xic_extractor.tabular_io.write_tsv()` and `write_delimited_rows()` now
    accept an explicit `encoding` parameter while preserving `utf-8` as the
    default for existing callers.
  - `xic_extractor/target_pair_rt_calibration.py` now delegates TSV
    serialization to the package tabular writer with `encoding="utf-8-sig"`.
  - The target-pair calibration schema, `utf-8-sig` BOM, six-decimal RT delta
    formatting, header-only empty output, and loader round-trip behavior are
    unchanged.
  - Test surface: existing target-pair calibration tests plus focused BOM/header
    characterization and package-writer `utf-8-sig` coverage.
- Shared the P7 evidence cost summary TSV writer implementation.
  - `tools/diagnostics/p7_evidence_cost_summary.py` now delegates
    `p7_evidence_cost_summary.tsv` serialization to
    `xic_extractor.tabular_io.write_tsv`.
  - The `metric,value` schema, sorted metric rows, JSON/Markdown outputs,
    copied evidence artifacts, and CLI status behavior are unchanged.
  - Test surface: existing P7 evidence cost summary tests plus focused TSV
    header/value characterization.
- Shared the untargeted alignment guardrail case-summary TSV writer
  implementation.
  - `tools/diagnostics/untargeted_alignment_guardrail_outputs.py` now delegates
    `case_assertion_summary.tsv` serialization to
    `xic_extractor.tabular_io.write_tsv`.
  - The fixed guardrail schema, input mapping order, lowercase boolean text,
    header-only empty output, parent-directory creation, comparison rows, and
    CLI/facade import surface are unchanged.
  - `untargeted_alignment_guardrail_metrics.py` also has an adjacent
    behavior-neutral typing cleanup for optional scalar/flag parsing so the
    focused diagnostics shard can pass mypy directly.
  - Test surface: existing untargeted alignment guardrail tests plus focused
    schema/order/header-only characterization.
- Shared the multi-tag adduct audit TSV writer implementation.
  - `tools/diagnostics/multi_tag_adduct_audit.py` now delegates
    `multi_tag_adduct_summary.tsv` and `multi_tag_adduct_pairs.tsv`
    serialization to `xic_extractor.tabular_io.write_tsv`.
  - The summary schema/order, pair schema/order, JSON/Markdown outputs, and CLI
    behavior are unchanged.
  - A writer-local formatter preserves legacy `csv.DictWriter` value
    stringification, including full Python `str(float)` output for adduct pair
    deltas and ppm errors.
  - Test surface: existing multi-tag adduct CLI smoke plus focused TSV
    schema/value characterization.
- Shared the P1 resolver-default gate TSV writer implementation.
  - `tools/diagnostics/p1_resolver_default_gate.py` keeps its private
    `_write_tsv(path, fieldnames, rows)` compatibility helper, but delegates
    TSV serialization to `xic_extractor.tabular_io.write_tsv`.
  - The rows/summary TSV schemas, LF-only line endings, float formatting,
    JSON/Markdown outputs, CLI exit behavior, and path-style `--help` script
    contract are unchanged.
  - The helper now accepts any iterable of mapping rows, matching its existing
    generator call sites while keeping the shared writer call materialized at
    the boundary.
  - Test surface: existing P1 gate tests plus focused rows/summary TSV
    schema/value/LF characterization and path-style help smoke.
- Shared the P2 AsLS shadow gate TSV writer implementation.
  - `tools/diagnostics/p2_asls_shadow_gate.py` keeps its private
    `_write_tsv(path, fieldnames, rows)` compatibility helper, but delegates
    TSV serialization to `xic_extractor.tabular_io.write_tsv`.
  - The rows/summary TSV schemas, LF-only line endings, `_format_value` float
    rendering, JSON/Markdown outputs, CLI exit behavior, and path-style
    `--help` script contract are unchanged.
  - Test surface: existing P2 AsLS shadow gate tests plus focused rows/summary
    TSV schema/value/LF characterization and path-style help smoke.
- Shared the P2b AsLS promotion gate TSV writer implementation.
  - `tools/diagnostics/p2b_asls_promotion_gate.py` keeps its private
    `_write_tsv(path, fieldnames, rows)` compatibility helper, but delegates
    TSV serialization to `xic_extractor.tabular_io.write_tsv`.
  - The rows/summary TSV schemas, LF-only line endings, tuple-field semicolon
    rendering, empty optional-field rendering, `_format_value` float rendering,
    JSON/Markdown outputs, CLI exit behavior, and path-style `--help` script
    contract are unchanged.
  - Test surface: existing P2b AsLS promotion gate tests plus focused
    rows/summary TSV schema/value/LF characterization and path-style help
    smoke.
- Shared the P2 baseline truth audit TSV writer implementation.
  - `tools/diagnostics/p2_baseline_truth_audit.py` keeps its private
    `_write_tsv(path, fieldnames, rows)` compatibility helper, but delegates
    TSV serialization to `xic_extractor.tabular_io.write_tsv`.
  - The diagnostic rows/summary TSV schemas, LF-only line endings, relative
    plot paths, `_format_value` float rendering, JSON/Markdown outputs, plot
    artifact generation, CLI behavior, and path-style `--help` script contract
    are unchanged.
  - `_plot_baselines()` now types its matplotlib axis parameter as `Any`, a
    typing-only cleanup needed for focused mypy on this diagnostic module.
  - Test surface: existing P2 baseline truth audit tests plus focused
    rows/summary TSV schema/value/LF characterization and path-style help
    smoke.
- Shared the P7 alignment parity artifact TSV writer implementation.
  - `tools/diagnostics/p7_alignment_parity.py` now delegates the
    `8raw_matrix_parity.tsv`, `8raw_identity_parity.tsv`, and
    `8raw_targeted_benchmark_delta.tsv` serialization to
    `xic_extractor.tabular_io.write_tsv`.
  - The fixed `check/status/difference` schema, LF-only output,
    JSON/Markdown outputs, parity comparison decisions, and CLI status behavior
    are unchanged.
  - Test surface: existing P7 alignment parity tests plus focused artifact TSV
    schema/value/LF characterization.
- Shared the region-first safe-merge comparison TSV writer implementation.
  - `tools/diagnostics/region_first_safe_merge_comparison.py` now delegates
    comparison and summary TSV serialization to
    `xic_extractor.tabular_io.write_tsv`.
  - The comparison/summary schemas, header order, existing CRLF csv line
    endings, markdown output, comparison decisions, and CLI status behavior are
    unchanged.
  - Test surface: existing region-first safe-merge comparison tests plus
    focused comparison/summary TSV header and CRLF characterization.
- Shared the selected-envelope plot-index TSV writer implementation.
  - `tools/diagnostics/selected_envelope_plot_review.py` now delegates
    `selected_envelope_plot_index.tsv` serialization to
    `xic_extractor.tabular_io.write_tsv`.
  - The fixed plot-index header order, existing CRLF csv line endings, missing
    optional-field blank rendering, extra-key rejection, PNG/PDF generation,
    gallery HTML output, and CLI status behavior are unchanged.
  - `_select_chrom_peak_segment_for_row()` received a typing-only local variable
    rename so focused mypy can distinguish segment tuples from scored overlap
    tuples.
  - Test surface: existing selected-envelope plot review tests plus focused
    plot-index writer header/CRLF/missing-field/extra-key characterization.
- Shared the target-pair RT candidate plot-index TSV writer implementation.
  - `tools/diagnostics/target_pair_rt_candidate_plot_review.py` now delegates
    `target_pair_rt_candidate_plot_index.tsv` serialization to
    `xic_extractor.tabular_io.write_tsv`.
  - The fixed plot-index header order, existing CRLF csv line endings, missing
    optional-field blank rendering, extra-key rejection, PNG/PDF generation,
    target-pair review selection, and CLI status behavior are unchanged.
  - Test surface: existing target-pair RT candidate plot review tests plus
    focused plot-index writer header/CRLF/missing-field/extra-key
    characterization.
- Shared the family MS1 overlay trace-summary TSV writer implementation.
  - `tools/diagnostics/family_ms1_overlay_writers.py` now delegates
    `*_trace_summary.tsv` serialization to `xic_extractor.tabular_io.write_tsv`.
  - The fixed summary schema, LF-only line endings, existing `_format_float`
    rendering, trace-data JSON payload, PNG/PDF overlay rendering, and
    hypothesis-overlay rendering are unchanged.
  - `tests/test_family_ms1_overlay_plot.py` received typing-only test
    annotations for synthetic trace rows and drift lookup protocol conformance
    so the focused writer shard can run mypy directly.
  - Test surface: existing synthetic family MS1 overlay plot tests plus focused
    summary TSV LF/header characterization.
- Shared the family MS1 alignment experiment TSV writer implementations.
  - `tools/diagnostics/family_ms1_alignment_experiment.py` now delegates the
    main summary TSV, source-family summary TSV, source-family shift summary
    TSV, and best-shift summary TSV serialization to
    `xic_extractor.tabular_io.write_tsv`.
  - The fixed schemas, LF-only line endings, existing optional-float rendering,
    no-RAW CLI behavior, and PNG rendering behavior are unchanged.
  - `tests/test_family_ms1_alignment_experiment.py` received typing-only fake
    drift lookup protocol completion so focused mypy can run directly.
  - Test surface: existing family MS1 alignment experiment tests plus focused
    summary/source-summary/shift-summary TSV LF/header characterization.
- Shared the family MS1 overlay batch summary TSV writer implementation.
  - `tools/diagnostics/family_ms1_overlay_batch.py` now delegates
    `family_ms1_overlay_batch_summary.tsv` serialization to
    `xic_extractor.tabular_io.write_tsv`.
  - The fixed summary schema, LF-only line endings, existing `_format_value`
    rendering, markdown/JSON sidecar output, top30 expansion gate behavior, and
    overlay request locality/deduplication logic are unchanged.
  - Test surface: existing family MS1 overlay batch tests plus focused summary
    TSV LF/header characterization.
- Cleaned two widened writer/helper mypy surfaces exposed by the expanded gate.
  - `tools/diagnostics/standard_peak_backfill_machine_pipeline.py` now uses a
    direct review-queue/RAW/DLL `None` guard so the post-gate overlay rendering
    branch has non-null `Path` inputs without changing the missing-input error.
  - `scripts/run_alignment.py` now centralizes standard-peak preset runtime
    `int()`/`float()` coercion behind tiny helpers, preserving existing runtime
    behavior while avoiding `object`-typed conversion errors.
  - Test surface: existing standard-peak machine pipeline tests, run-alignment
    preset tests, family overlay batch tests, and widened package mypy gate.
- Shared the MS1-index backfill audit summary/example TSV writer
  implementations.
  - `tools/diagnostics/ms1_index_backfill_audit.py` now delegates
    `ms1_index_backfill_audit_summary.tsv` and
    `ms1_index_backfill_audit_examples.tsv` serialization to
    `xic_extractor.tabular_io.write_tsv`.
  - The dynamic union-of-row-keys header order, existing CRLF csv line endings,
    `str()` value rendering, None-to-blank rendering, JSON sidecar output, and
    empty-examples bare-newline behavior are unchanged.
  - Test surface: existing MS1-index audit tests plus focused summary/examples
    TSV dynamic-header/CRLF/float-rendering/empty-output characterization.
- Shared the alignment workbook compare TSV writer implementation.
  - `scripts/compare_alignment_workbooks.py` now delegates `--output-tsv`
    serialization to `xic_extractor.tabular_io.write_tsv`.
  - The fixed `status/difference` schema, parent-directory creation, LF-only
    line endings, pass/fail row selection, and text report output are
    unchanged.
  - Test surface: existing compare-alignment-workbooks CLI artifact test plus
    focused TSV header/LF/failure-row characterization.
- Shared the resolver comparison CSV writer implementation.
  - `scripts/compare_resolvers.py` now delegates `resolver_compare.csv`
    serialization to `xic_extractor.tabular_io.write_delimited_rows`.
  - The fixed resolver comparison schema, UTF-8 BOM, existing CRLF csv line
    endings, `True`/`False` detected rendering, optional-number formatting, and
    CLI stdout summary behavior are unchanged.
  - Test surface: existing compare-resolvers CLI test plus focused
    BOM/CRLF/header characterization.
- Shared the parallel benchmark summary CSV writer implementation.
  - `scripts/benchmark_parallel.py` now delegates `benchmark_summary.csv`
    serialization to `xic_extractor.tabular_io.write_delimited_rows`.
  - The fixed benchmark summary schema, UTF-8 BOM, existing CRLF csv line
    endings, elapsed-seconds `0.000` formatting, workbook path stringification,
    compare-difference joining, and benchmark CLI behavior are unchanged.
  - `tests/test_benchmark_parallel.py` received typing-only captured-config
    narrowing so focused mypy can run directly.
  - Test surface: existing benchmark parallel tests plus focused summary
    BOM/CRLF/header/timing-format characterization.
- Shared the validation harness summary CSV writer implementation.
  - `scripts/validation_harness_core.py` now delegates `validation_summary.csv`
    serialization to `xic_extractor.tabular_io.write_delimited_rows`.
  - The fixed validation summary schema, UTF-8 BOM, existing CRLF csv line
    endings, parent-directory creation, raw-count blank rendering, command
    PowerShell rendering, and compare-difference joining are unchanged.
  - The settings command tuple received a typing-only annotation so focused
    mypy can run directly.
  - Test surface: existing validation harness tests plus focused summary
    BOM/CRLF/header characterization.
- Shared the local-minimum parameter sweep settings CSV writer implementation.
  - `scripts/local_minimum_param_sweep.py` now delegates staged
    `settings.csv` serialization to `xic_extractor.tabular_io.write_delimited_rows`.
  - The fixed `key/value/description` schema, UTF-8 BOM, existing CRLF csv line
    endings, settings insertion order, canonical description lookup, and blank
    description fallback are unchanged.
  - This was layered on top of the existing dirty local-minimum sweep typing and
    workbook-failure aggregation cleanup without reverting it.
  - Test surface: existing local-minimum parameter sweep tests plus focused
    staged settings CSV BOM/CRLF/header/order characterization.
- Optimized `scripts/analyze_xic_request_locality.py` near-redundant census.
  - The private `_summarize_near_redundant_keys()` helper now sorts unique
    request keys by RT center and only evaluates candidate pairs inside the
    configured `near_rt_sec` sweep window.
  - This preserves transitive near-redundant components while avoiding
    comparisons that the RT threshold would always reject.
  - Test surface: `tests/test_analyze_xic_request_locality.py`.
- Cleaned the `tools/diagnostics/ms1_index_backfill_audit.py` typed surface.
  - Explicit optional-area annotations avoid local variable type narrowing
    drift in request comparison.
  - `_peak_config()` now passes `Path` values for `ExtractionConfig` output
    paths, matching the package contract.
  - Test surface: `tests/test_ms1_index_backfill_audit.py` plus the locality /
    MS1-index validation shard.
- Optimized peak-candidate score label-impact aggregation.
  - `_label_impact()` now accumulates selected/rejected raw-score buckets while
    collecting support/concern/cap labels, avoiding a second scan per label.
  - `_label_impact_row()` remains as a compatibility helper and delegates to
    the shared score-bucket row builder.
  - `peak_candidate_score_calibration_io.py` now narrows the required
    `selected` field to `bool` at parse time and reports invalid values through
    the existing `ValueError -> exit 2` path.
  - Test surface: label median/order characterization and invalid `selected`
    input coverage in `tests/test_peak_candidate_score_calibration_report.py`.
- Hoisted ASLS fixture-manifest required-key planning.
  - `load_fixture_manifest()` now computes the current-vs-legacy
    `required_class_keys` tuple once before validating fixture classes.
  - Missing-key, stale split policy, class coverage, and legacy/current
    semantics are unchanged.
  - Test surface: existing manifest validation coverage in
    `tests/test_asls_truth_validation_manifests.py`.
- Tightened locality diagnostic census preparation.
  - `collect_owner_backfill_requests()` now stores only non-empty detected
    sample names while reading alignment cells, avoiding a per-review-row set
    filter.
  - `_summarize_same_scan_windows()` now builds each request-key set once per
    scan-window group and reuses it for filtering, metrics, and examples.
  - Added a `RequestKey` alias to keep the census tuple shape explicit.
  - Test surface: same-window exact-duplicate characterization in
    `tests/test_analyze_xic_request_locality.py`.
- Reused family-MS1 backfill review candidate ordering for the image queue.
  - `build_review_report()` now sorts candidates once with `_candidate_sort_key`
    and filters the already ordered list to build `image_queue`.
  - The candidate TSV order, queue priority order, and queue limit behavior stay
    unchanged.
  - Test surface: multi-row queue ordering characterization in
    `tests/test_family_ms1_backfill_review_report.py`.
- Streamed subthreshold sensitivity aggregation.
  - `summarize_subthreshold_sensitivity()` now accepts any iterable of
    `(trace_key, candidates)` pairs and counts traces during aggregation.
  - `run_subthreshold_sensitivity_report()` no longer materializes all trace
    candidate tuples before computing the same gate/recovery summary rows.
  - Test surface: generator-input characterization in
    `tests/test_subthreshold_sensitivity_report.py`.
- Reused retained-backfill missing-overlay queue candidates.
  - `write_retained_backfill_gate_outputs()` now computes the ordered
    missing-overlay candidate list once and reuses it for both the exhaustive
    missing-overlay queue and the family-deduplicated review queue.
  - Queue rows, review-queue family selection, ranks, summary counts, and TSV
    schemas are unchanged.
  - Test surface: CLI queue-candidate call-count characterization in
    `tests/test_retained_backfill_evidence_gate.py`.
- Reused targeted ISTD benchmark matrix sample-column normalization.
  - Legacy and clean public matrix readers now build `(column, normalized_sample)`
    pairs once and reuse them while expanding family/sample area maps.
  - Legacy matrix support, clean `alignment_matrix_identity.tsv` provenance,
    positive-area filtering, and normalized sample names are unchanged.
  - Test surface: matrix-loader normalization call-count characterization in
    `tests/test_targeted_istd_benchmark.py`.
- Streamed shift-aware source-family summary aggregation into a per-family
  accumulator.
  - `collect_shift_aware_family_summary_rows()` now records non-reference source
    names, shape values, and absolute shift values while reading summary rows
    instead of retaining every row and traversing each family list multiple
    times.
  - Reference-only families, rows without usable shape similarity, output
    ordering, summary formatting, and TSV schema are unchanged.
  - Test surface: cross-file/missing-value accumulator characterization in
    `tests/test_shift_aware_backfill_calibration_pack.py`.
- Reused primary-area authority row analysis in the diagnostics CLI.
  - `alignment_primary_area_authority_audit.py` now computes summary counts and
    flagged rows from one shared `_analyze_primary_area_authority_rows()` pass.
  - The CLI reads `alignment_cells.tsv` once, while the existing path-based
    `summarize_primary_area_authority()` and
    `flagged_primary_area_authority_rows()` helpers remain available.
  - Test surface: CLI read-count characterization in
    `tests/test_alignment_primary_area_authority_audit.py`.
- Reused Gaussian15 area-pressure audit rows for summary output.
  - `gaussian15_area_pressure_audit.py` now derives summary counts from the
    already computed row audit in the CLI path instead of reading
    `peak_candidates.tsv` again.
  - Path-based `summarize_gaussian15_area_pressure()` and
    `gaussian15_area_pressure_rows()` helpers remain available.
  - Test surface: CLI read-count characterization in
    `tests/test_gaussian15_area_pressure_audit.py`.
- Reused single-dR gate classification buckets for gate-candidate summaries.
  - `single_dr_production_gate_decision_report.py` now indexes family rows by
    `risk_classification` once and reuses those buckets across all gate
    summaries.
  - Blocked-family order, gate candidate order, output schemas, and activation
    decision semantics are unchanged.
  - `single_dr_gate_decision_loaders.py` also now types candidate-quality values
    as allowing `None`, matching `_float_or_none()` and restoring the focused
    mypy gate.
  - Test surface: `_gate_candidates()` bucket/order characterization in
    `tests/test_single_dr_production_gate_decision_report.py`.
- Bundled matrix blast-radius input assembly.
  - `analyze_matrix_identity_blast_radius.py` now builds the alignment matrix,
    current review-row lookup, and per-family cell-row groups in one helper
    while walking review/cell TSV rows once per input surface.
  - Cluster order, sorted sample order, family cell-row order, TSV/JSON output
    schemas, machine-decision projection columns, and targeted benchmark joins
    are unchanged.
  - Test surface: input-bundle order characterization in
    `tests/test_matrix_identity_blast_radius.py`.
- Bundled owner-backfill economics cell-row indexing.
  - `owner_backfill_request_economics.py` now builds per-feature cell groups
    and first-seen sample order in one private input index.
  - Feature row order within each family, sample order, request economics,
    TSV/JSON/Markdown schemas, and diagnostic-only authority remain unchanged.
  - Test surface: cell-index order characterization in
    `tests/test_owner_backfill_request_economics.py`.
- Indexed artificial-adduct matching by m/z delta.
  - `xic_extractor/alignment/adduct_annotation.py` now sorts adduct deltas once
    and uses `bisect` to restrict candidate adducts for each RT-compatible
    family pair before the existing ppm check.
  - Pair order and adduct input order are preserved, and supported-family
    identity behavior remains unchanged.
  - Test surface: adduct input-order characterization in
    `tests/test_alignment_adduct_annotation.py` plus the existing
    artificial-adduct matrix identity guard.

## Remaining Higher-Risk Candidates

1. Product decider convergence for `backfill_shadow_policy` vs
   `shadow_production_projection`.
   - Risk: string-token and review-artifact semantics.
   - Current audit verdict: no no-behavior cleanup slice remains obvious. The
     modules already share `BackfillDecisionExplanation` and the overlay row
     selector helper while intentionally passing different overlay fallback
     policies and emitting different decision tokens.
   - Next evidence: productization spec decision first; the shared explanation
     payload, current-state helper, and projection value gate are intentionally
     not a product-policy merge.
2. Process-worker payload deepening beyond feature lists.
   - Risk: pickle payload size and worker parity.
   - Current no-RAW evidence helper:
     `owner_backfill_job_payload_metrics()` reports existing per-sample feature
     payload count, request count, request/features ratio, and pickle payload
     bytes without changing worker payload shape.
   - Next evidence: only consider passing request items across workers if an
     8RAW benchmark shows request-plan recomputation is material and the
     projected payload growth is acceptable.

## Non-Goals For This Pass

- No 8RAW or 85RAW validation.
- No CLI flag, TSV schema, workbook schema, or matrix behavior change.
- No large extraction/facade migration.
- No mass rewrite of all diagnostics scripts.

## Verification

Scanner note:

```powershell
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 60
```

The first unfiltered scanner run timed out / produced cache noise; the
actionable pass excluded `.uv-cache` and other non-source/generated surfaces.

Focused no-RAW shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_alignment_config.py tests\test_diagnostic_io.py tests\test_alignment_owner_backfill.py tests\test_alignment_owner_matrix.py tests\test_backfill_scope.py tests\test_retained_backfill_evidence_gate.py tests\test_backfill_shadow_policy_report.py tests\test_shadow_production_projection.py tests\test_backfill_ms1_product_authority.py tests\test_backfill_evidence_projection.py tests\test_backfill_candidate_ms2_product_authority.py tests\test_standard_peak_ms1_authority_bundle.py tests\test_standard_peak_backfill_chunk_consolidation.py
```

Observed result: `239 passed`.

Follow-up candidate shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_shadow_production_projection.py tests\test_backfill_ms1_product_authority.py tests\test_standard_peak_ms1_authority_bundle.py
```

Observed result: `47 passed`.

Gallery candidate shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_backfill_evidence_reconciliation_gallery.py
```

Observed result: `46 passed`.

Gallery/productization follow-up shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_backfill_evidence_reconciliation_gallery.py tests\test_standard_peak_backfill_productization.py tests\test_standard_peak_backfill_machine_pipeline.py
```

Observed result: `54 passed`.

Latest owner-backfill and diagnostic explanation shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_alignment_owner_backfill.py tests\test_backfill_decision_explanation.py tests\test_backfill_shadow_policy_report.py tests\test_shadow_production_projection.py
```

Observed result: `59 passed`.

Latest owner-backfill/process request-plan and payload-metrics shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_alignment_owner_backfill.py tests\test_alignment_process_backend.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\process_backend.py tests\test_alignment_process_backend.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\process_backend.py
```

Observed result: `45 passed`; ruff passed; mypy passed for 1 source file.

Latest shadow projection row-state/value-gate shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_shadow_production_projection.py tests\test_backfill_decision_explanation.py tests\test_backfill_shadow_policy_report.py
```

Observed result: `34 passed`.

Latest locality / MS1-index diagnostics shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_analyze_xic_request_locality.py tests\test_validate_ms1_scan_index_xic.py tests\test_ms1_index_backfill_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check scripts\analyze_xic_request_locality.py tests\test_analyze_xic_request_locality.py tools\diagnostics\ms1_index_backfill_audit.py tests\test_ms1_index_backfill_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy scripts\analyze_xic_request_locality.py tools\diagnostics\ms1_index_backfill_audit.py
```

Observed results:

- `pytest`: `7 passed`.
- `ruff`: all checks passed.
- `mypy`: success, no issues found in 2 source files.

Latest backfill scope probe request-plan shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_backfill_scope_probe.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\backfill_scope_probe.py tests\test_backfill_scope_probe.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy --follow-imports=skip tools\diagnostics\backfill_scope_probe.py
```

Observed results: `2 passed`; ruff passed; focused mypy passed for 1 source
file.

Latest backfill scope probe writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_backfill_scope_probe.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\backfill_scope_probe.py tests\test_backfill_scope_probe.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy --follow-imports=skip tools\diagnostics\backfill_scope_probe.py
```

Observed results: `4 passed`; ruff passed; focused mypy passed for 1 source
file. Candidate verdict: true dynamic-schema writer-helper cleanup. The
backfill scope probe writer now delegates non-empty TSV serialization to the
shared helper while preserving parent-directory creation, empty-output behavior,
first-row field order, Python-style bool conversion, later extra-key rejection,
and diagnostics-only TSV semantics.

Latest standard-peak authority artifact-cache shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_standard_peak_ms1_authority_bundle.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\diagnostics\standard_peak_ms1_authority_bundle.py tests\test_standard_peak_ms1_authority_bundle.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\diagnostics\standard_peak_ms1_authority_bundle.py
```

Observed results: `5 passed`; ruff passed; mypy passed for 1 source file.

Latest claim-registry hot-path shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_alignment_claim_registry_hot_path.py tests\test_alignment_claim_registry.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\claim_registry.py tests\test_alignment_claim_registry_hot_path.py tests\test_alignment_claim_registry.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\claim_registry.py
```

Observed results: `16 passed`; ruff passed; mypy passed for 1 source file.

Latest changed-row mode-overlay shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_changed_row_mode_overlay_review.py tests\test_alignment_edge_scoring.py tests\test_alignment_owner_clustering.py tests\test_alignment_pipeline.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\changed_row_mode_overlay_review.py tests\test_changed_row_mode_overlay_review.py xic_extractor\alignment\edge_scoring.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\changed_row_mode_overlay_review.py xic_extractor\alignment\edge_scoring.py
```

Observed results: `61 passed`; ruff passed; mypy passed for 2 source files.

Latest GUI config fieldname shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_gui_config_io.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check gui\config_io.py tests\test_gui_config_io.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy gui\config_io.py
```

Observed results: `1 passed`; ruff passed; mypy passed for 1 source file.

Latest ISTD RT trend median shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_add_istd_rt_trend.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check scripts\add_istd_rt_trend.py tests\test_add_istd_rt_trend.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy scripts\add_istd_rt_trend.py
```

Observed results: `2 passed`; ruff passed; mypy passed for 1 source file.

Latest validation migration grouping shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_validate_migration.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check scripts\validate_migration.py tests\test_validate_migration.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy scripts\validate_migration.py
```

Observed results: `11 passed`; ruff passed; mypy passed for 1 source file.

Latest xlsx-to-targets ISTD pairing shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_xlsx_to_targets.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check scripts\xlsx_to_targets.py tests\test_xlsx_to_targets.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy scripts\xlsx_to_targets.py
```

Observed results: `2 passed`; ruff passed; mypy passed for 1 source file.

Latest local-minimum sweep failure-cache shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_local_minimum_param_sweep.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check scripts\local_minimum_param_sweep.py tests\test_local_minimum_param_sweep.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy scripts\local_minimum_param_sweep.py
```

Observed results: `11 passed`; ruff passed; mypy passed for 1 source file.

Latest overlay scan-RT cache shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_family_ms1_overlay_batch.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\family_ms1_overlay_batch.py tests\test_family_ms1_overlay_batch.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\family_ms1_overlay_batch.py
```

Observed results: `14 passed`; ruff passed; mypy passed for 1 source file.

Latest evidence-spine RT index shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_evidence_spine_consistency.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\evidence_spine_consistency_analysis.py tests\test_evidence_spine_consistency.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\evidence_spine_consistency_analysis.py
```

Observed results: `9 passed`; ruff passed; mypy passed for 1 source file.

Latest ASLS ref-root cache shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_asls_truth_validation_inputs.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\asls_truth_validation_inputs.py tests\test_asls_truth_validation_inputs.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\asls_truth_validation_inputs.py
```

Observed results: `66 passed`; ruff passed; mypy passed for 1 source file.

Latest ASLS Tier C blocker membership shard:

- `tools/diagnostics/asls_truth_validation_inputs.py` now validates
  `tier_c_row_blockers` once per family, then reuses a `blocker_set` for
  artifact, hard-AsLS, and review-blocker membership checks. Previously the
  same validated blocker list was scanned separately for each membership class.
- Behavior is unchanged: duplicate blockers still contribute to
  `row_blocker_count` through the original list length, artifact blockers still
  fail immediately, hard blockers still force FAIL, and review blockers still
  increment `review_required_count`.
- `tests/test_asls_truth_validation_inputs.py` now characterizes duplicate
  blocker counting before the membership-set checks.

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_asls_truth_validation_inputs.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\asls_truth_validation_inputs.py tests\test_asls_truth_validation_inputs.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\asls_truth_validation_inputs.py
```

Observed results: `67 passed`; ruff passed; source mypy passed for 1 source
file. A broader attempted `mypy tools\diagnostics\asls_truth_validation_inputs.py
tests\test_asls_truth_validation_inputs.py` exposed existing test-fixture
typing issues in the test module, so the focused type gate remains source-only
for this shard.

Latest low-MS1 seed-group ordering shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_low_ms1_assessable_coverage_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\low_ms1_coverage_review_classifier.py tests\test_low_ms1_assessable_coverage_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\low_ms1_coverage_review_classifier.py
```

Observed results: `9 passed`; ruff passed; mypy passed for 1 source file.

Latest peak-candidate score label-impact shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_peak_candidate_score_calibration_report.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\peak_candidate_score_calibration_analysis.py tools\diagnostics\peak_candidate_score_calibration_io.py tests\test_peak_candidate_score_calibration_report.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\peak_candidate_score_calibration_analysis.py tools\diagnostics\peak_candidate_score_calibration_io.py
```

Observed results: `7 passed`; ruff passed; mypy passed for 2 source files.

Latest ASLS fixture-manifest required-key shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_asls_truth_validation_manifests.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\asls_truth_validation_manifests.py tests\test_asls_truth_validation_manifests.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\asls_truth_validation_manifests.py
```

Observed results: `27 passed`; ruff passed; mypy passed for 1 source file.

Latest locality same-window census shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_analyze_xic_request_locality.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check scripts\analyze_xic_request_locality.py tests\test_analyze_xic_request_locality.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy scripts\analyze_xic_request_locality.py
```

Observed results: `5 passed`; ruff passed; mypy passed for 1 source file.

Latest family-MS1 review queue ordering shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_family_ms1_backfill_review_report.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\family_ms1_backfill_review_report.py tests\test_family_ms1_backfill_review_report.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\family_ms1_backfill_review_report.py
```

Observed results: `4 passed`; ruff passed; mypy passed for 1 source file.

Latest artificial-adduct RT-window candidate shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_alignment_adduct_annotation.py tests\test_multi_tag_adduct_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\adduct_annotation.py tests\test_alignment_adduct_annotation.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\adduct_annotation.py
```

Observed results: `4 passed`; ruff passed; mypy passed for 1 source file.
Candidate verdict: true bounded package hotspot. `match_artificial_adduct_pairs`
now snapshots family id/mz/RT once, prunes pair enumeration with an RT-sorted
window, materializes `Iterable[ArtificialAdduct]` once, and emits pairs in the
same original input pair order. Added characterization for out-of-order RT input
plus generator adducts, so the optimization does not change review output order
and closes the previous iterable-consumption edge case.

Latest drift-evidence lookup cache shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_alignment_drift_evidence.py tests\test_alignment_edge_scoring.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\drift_evidence.py tests\test_alignment_drift_evidence.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\drift_evidence.py
```

Observed results: `28 passed`; ruff passed; mypy passed for 1 source file.
Candidate verdict: true package-level reuse hotspot. `DriftEvidenceLookup`
previously scanned all drift points on every `sample_delta_min()` and
`injection_order()` call. It now builds lazy per-sample median/injection-order
maps once, keeping missing-sample behavior and per-sample conflict timing. Added
characterization that a conflict on one sample does not block lookup for another
sample.

Latest overlay duplicate-XIC reuse shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_family_ms1_overlay_batch.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\family_ms1_overlay_batch.py tests\test_family_ms1_overlay_batch.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\family_ms1_overlay_batch.py
```

Observed results: `15 passed`; ruff passed; mypy passed for 1 source file.
Candidate verdict: true overlay RAW-access reuse hotspot. Within a single sample,
`_extract_overlay_traces` now deduplicates identical `(mz, rt_min, rt_max, ppm)`
requests before RAW extraction and maps the unique trace back to every original
rank/cell row. Logical output rows and `extract_xic_count` stay unchanged, while
duplicate raw requests are avoided in both fallback and superwindow extraction
paths. Added characterization that two ranks with the same sample/window produce
two review rows but only one fake RAW extraction request.

Latest targeted reliability summary aggregation shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_targeted_peak_reliability_classifier.py tests\test_targeted_peak_reliability_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\targeted_peak_reliability_classifier.py tests\test_targeted_peak_reliability_classifier.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\targeted_peak_reliability_classifier.py tests\test_targeted_peak_reliability_classifier.py
```

Observed results: `22 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: true diagnostics aggregation cleanup. `_summarize_rows`
now builds one `Counter` for reliability states per target instead of scanning
the same target rows once per state count. Added direct characterization for
target-label sort order, role selection from the first row, state counts,
`top_risk_reasons`, and first non-empty known exception.

Latest product-authority allowlist indexing shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_backfill_candidate_ms2_product_authority.py tests\test_backfill_ms1_product_authority.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\_backfill_util.py xic_extractor\alignment\backfill_candidate_ms2_product_authority.py xic_extractor\alignment\backfill_ms1_product_authority.py tests\test_backfill_candidate_ms2_product_authority.py tests\test_backfill_ms1_product_authority.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\_backfill_util.py xic_extractor\alignment\backfill_candidate_ms2_product_authority.py xic_extractor\alignment\backfill_ms1_product_authority.py
```

Observed results: `28 passed`; ruff passed; mypy passed for 3 source files.
Candidate verdict: true architecture/clean-code duplication. Candidate-MS2 and
MS1 product-authority sidecars now share
`_backfill_util.allowlist_rows_by_family_sample_key` for schema-version validation,
required `feature_family_id`/`sample_stem`, and duplicate-key detection.
Added direct duplicate-allowlist tests for both sidecars so the fail-closed
error contract stays pinned while the indexing logic is centralized.

Latest ASLS fixture-lock heldout grouping shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_asls_truth_validation_manifests.py tests\test_asls_truth_validation_synthetic.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\asls_truth_validation_manifests.py tests\test_asls_truth_validation_manifests.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\asls_truth_validation_manifests.py
```

Observed results: `39 passed`; ruff passed; mypy passed for 1 source file.
Candidate verdict: true low-risk diagnostics cleanup. `validate_fixture_lock_coverage`
now indexes heldout rows by fixture class once, then preserves the existing
`REQUIRED_FIXTURE_CLASSES` validation order and coverage/error contracts. This
does not change fixture manifest/lock schema, hash validation, required class
coverage, or hard-case coverage policy.

Latest changed-row subthreshold report reuse shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_changed_row_mode_overlay_review.py tests\test_ms1_peak_modes_detection_unchanged.py tests\test_subthreshold_sensitivity_report.py tests\test_shared_peak_identity_rt_mode_evidence.py tests\test_shared_peak_identity_peak_hypothesis_selection.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\changed_row_mode_overlay_review.py tests\test_changed_row_mode_overlay_review.py tests\test_ms1_peak_modes_detection_unchanged.py tests\test_subthreshold_sensitivity_report.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\changed_row_mode_overlay_review.py
```

Observed results: `36 passed`; ruff passed; mypy passed for 1 source file.
Candidate verdict: true diagnostics/render-path reuse hotspot.
`run_changed_row_mode_overlay_review` now computes each trace's
`subthreshold_candidate_report` once per run and passes the cached report to
sample rows, family summary, and mode plot rendering. The public helper
signature stays unchanged for `subthreshold_sensitivity_report`, and
subthreshold sample/family/HTML semantics remain pinned by the focused test.

Latest shadow projection matrix-locality shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_shadow_production_projection.py tests\test_standard_peak_backfill_productization.py tests\test_standard_peak_backfill_chunk_consolidation.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\diagnostics\shadow_production_projection.py tests\test_shadow_production_projection.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\diagnostics\shadow_production_projection.py
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_shadow_production_projection.py -q
```

Observed results: broad pytest shard `47 passed`; initial ruff reported one
test import-order issue, fixed and rerun with all checks passed; mypy passed for
1 source file; targeted shadow projection test file passed. Candidate verdict:
true package diagnostics locality cleanup. `_current_matrix_values_by_family_sample`
now accepts requested `(feature_family_id, sample_stem)` keys derived from the
retained gate rows and materializes only those matrix cells, while preserving
`peak_hypothesis_id` / `source_feature_family_ids` matching, supplied-matrix
authority, and production-decision fallback when a requested key is absent.

Latest subthreshold sensitivity streaming shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_subthreshold_sensitivity_report.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\subthreshold_sensitivity_report.py tests\test_subthreshold_sensitivity_report.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\subthreshold_sensitivity_report.py
```

Observed results: `3 passed`; ruff passed; mypy passed for 1 source file.
Candidate verdict: true diagnostics memory/locality cleanup.
`summarize_subthreshold_sensitivity` now accepts streamed trace candidate
iterables and counts traces during aggregation, so
`run_subthreshold_sensitivity_report` no longer materializes all trace
candidates before writing the same gate/recovery TSV outputs. Detection logic,
candidate semantics, output filenames, and TSV schemas are unchanged.

Latest retained gate queue-candidate reuse shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_retained_backfill_evidence_gate.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\diagnostics\retained_backfill_evidence_gate.py tests\test_retained_backfill_evidence_gate.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\diagnostics\retained_backfill_evidence_gate.py
```

Observed results: `8 passed`; ruff passed; mypy passed for 1 source file.
Candidate verdict: true diagnostics output locality cleanup. Retained backfill
gate output writing now builds and sorts missing-overlay candidates once, then
reuses that ordered list for the exhaustive queue and family-deduplicated review
queue. Gate decision logic, overlay selection, queue row schema, rank semantics,
and summary counts are unchanged.

Latest targeted ISTD matrix-loader sample-column shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_targeted_istd_benchmark.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\targeted_istd_benchmark_loaders.py tests\test_targeted_istd_benchmark.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\targeted_istd_benchmark_loaders.py
```

Observed results: `14 passed`; ruff passed; mypy passed for 1 source file.
Candidate verdict: true diagnostics loader locality cleanup. Legacy and clean
targeted ISTD benchmark matrix readers now normalize sample column names once
per matrix read and reuse those pairs across all family row value expansion.
Matrix formats, identity provenance, positive-area filtering, output summaries,
and validation-only benchmark authority are unchanged.

Latest shift-aware source-family accumulator shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_shift_aware_backfill_calibration_pack.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\shift_aware_backfill_calibration_pack.py tests\test_shift_aware_backfill_calibration_pack.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\shift_aware_backfill_calibration_pack.py
```

Observed results: `7 passed`; ruff passed; mypy passed for 1 source file.
Candidate verdict: true diagnostics aggregation cleanup. Shift-aware
source-family summary rows are now accumulated per family while reading
`*_source_family_best_shift_summary.tsv` files, avoiding a second materialized
row grouping/traversal pass. Reference filtering, shape/shift formatting,
family ordering, output filename, and TSV schema are unchanged.

Latest primary-area authority single-read shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_alignment_primary_area_authority_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\alignment_primary_area_authority_audit.py tests\test_alignment_primary_area_authority_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\alignment_primary_area_authority_audit.py
```

Observed results: `4 passed`; ruff passed; mypy passed for 1 source file.
Candidate verdict: true diagnostics CLI locality cleanup. The primary-area
authority audit CLI now reads `alignment_cells.tsv` once and shares one row
classification pass for summary counts and flagged-row output. CLI flags,
output filenames, JSON/TSV schemas, and product-authority classification
semantics are unchanged.

Latest Gaussian15 area-pressure single-read shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_gaussian15_area_pressure_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\gaussian15_area_pressure_audit.py tests\test_gaussian15_area_pressure_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\gaussian15_area_pressure_audit.py
```

Observed results: `2 passed`; ruff passed; mypy passed for 1 source file.
Candidate verdict: true diagnostics CLI locality cleanup. The Gaussian15
area-pressure audit CLI now reads `peak_candidates.tsv` once and computes
summary counts from the already built row audit. CLI flags, output filenames,
JSON/TSV schemas, readiness labels, and diagnostic-only product action remain
unchanged.

Latest single-dR gate-candidate bucket shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_single_dr_production_gate_decision_report.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\single_dr_production_gate_decision_report.py tools\diagnostics\single_dr_gate_decision_loaders.py tests\test_single_dr_production_gate_decision_report.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\single_dr_production_gate_decision_report.py
```

Observed results: `19 passed`; ruff passed; mypy passed for 1 source file.
Candidate verdict: true diagnostics report-assembly locality cleanup. The
single-dR gate report now builds risk-classification buckets once and reuses
them across gate-candidate summaries, while preserving blocked-family order and
gate-candidate output order. The loader value type was tightened to match
nullable numeric candidate metrics exposed by `_float_or_none()`.

Latest matrix blast-radius input-bundle shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_matrix_identity_blast_radius.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\analyze_matrix_identity_blast_radius.py tests\test_matrix_identity_blast_radius.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\analyze_matrix_identity_blast_radius.py
```

Observed results: `8 passed`; ruff passed; mypy passed for 1 source file.
Candidate verdict: true read-only diagnostics input-locality cleanup. The
blast-radius report now uses one private input bundle for the alignment matrix,
current review-row lookup, and per-family cell-row groups while preserving the
existing cluster order, sorted sample order, cell-row grouping order, TSV/JSON
schemas, and targeted benchmark join behavior.

Latest owner-backfill economics cell-index shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_owner_backfill_request_economics.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\owner_backfill_request_economics.py tests\test_owner_backfill_request_economics.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\owner_backfill_request_economics.py
```

Observed results: `3 passed`; ruff passed; mypy passed for 1 source file.
Candidate verdict: true diagnostics input-locality cleanup. Owner-backfill
request economics now indexes cell rows once for per-feature groups and sample
order, preserving feature row order, first-seen sample order, request economics
counts, and all output schemas.

Latest artificial-adduct delta-index shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_alignment_adduct_annotation.py tests\test_alignment_matrix_identity.py::test_artificial_adduct_annotation_does_not_demote_supported_family
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\adduct_annotation.py tests\test_alignment_adduct_annotation.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\adduct_annotation.py
```

Observed results: `5 passed`; ruff passed; mypy passed for 1 source file.
Candidate verdict: true package-level locality cleanup. Artificial-adduct
matching now indexes adduct deltas once and uses a ppm-derived `bisect` range
for each RT-compatible family pair, then preserves original adduct input order
for emitted matches.

Latest tabular identity helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_diagnostic_io.py tests\test_shadow_production_projection.py tests\test_standard_peak_backfill_productization.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\tabular_io.py xic_extractor\diagnostics\shadow_production_projection.py xic_extractor\diagnostics\standard_peak_backfill_productization.py tests\test_diagnostic_io.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\tabular_io.py xic_extractor\diagnostics\shadow_production_projection.py xic_extractor\diagnostics\standard_peak_backfill_productization.py
```

Observed results: `45 passed`; ruff passed; mypy passed for 3 source files.
Candidate verdict: true package/diagnostics helper cleanup. Current matrix
value lookups now share TSV header reading, positive `matrix_row_index`
parsing, and identity family-key expansion while preserving schema and
projection/productization behavior.

Latest authorizer TSV-header helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_diagnostic_io.py tests\test_backfill_ms1_product_authority.py tests\test_backfill_candidate_ms2_product_authority.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\tabular_io.py tools\diagnostics\authorize_backfill_ms1_pattern_evidence.py tools\diagnostics\authorize_backfill_candidate_ms2_pattern_evidence.py tests\test_diagnostic_io.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\tabular_io.py tools\diagnostics\authorize_backfill_ms1_pattern_evidence.py tools\diagnostics\authorize_backfill_candidate_ms2_pattern_evidence.py
```

Observed results: `42 passed`; ruff passed; mypy passed for 3 source files.
Candidate verdict: true tools/package helper cleanup. Product-authority
authorizer CLIs now share TSV header reading, required-column validation, and
UTF-8 BOM handling while preserving authorization rules and output contracts.

Latest targeted-NL writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_targeted_nl_dropout_root_cause_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\targeted_nl_dropout_root_cause_writers.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\targeted_nl_dropout_root_cause_writers.py
```

Observed results: `8 passed`; ruff passed; mypy passed for 1 source file.
Candidate verdict: true writer-helper cleanup. The targeted NL dropout writer
now delegates TSV serialization to the shared diagnostic helper while retaining
the legacy `_write_tsv` import/reexport surface and preserving all output
contracts.

Latest area-integration writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_area_integration_uncertainty_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\area_integration_uncertainty_writers.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\area_integration_uncertainty_writers.py
```

Observed results: `6 passed`; ruff passed; mypy passed for 1 source file.
Candidate verdict: true writer-helper cleanup. The area-integration
uncertainty writer now delegates TSV serialization to the shared diagnostic
helper while retaining the legacy `_write_tsv` import/reexport surface,
custom `.10g` numeric formatting, and output contracts.

Latest targeted ISTD writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_targeted_istd_benchmark.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\targeted_istd_benchmark_writers.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\targeted_istd_benchmark_writers.py
```

Observed results: `14 passed`; ruff passed; mypy passed for 1 source file.
Candidate verdict: true writer-helper cleanup. The targeted ISTD benchmark
writer now delegates TSV serialization to the shared diagnostic helper while
preserving `_format_value()`, summary/match TSV columns, JSON, Markdown, and
benchmark decisions.

Latest family-MS1 review writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_family_ms1_backfill_review_report.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\family_ms1_backfill_review_writers.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\family_ms1_backfill_review_writers.py
```

Observed results: `4 passed`; ruff passed; mypy passed for 1 source file.
Candidate verdict: true writer-helper cleanup. The family-MS1 review writer now
delegates TSV serialization to the shared diagnostic helper while preserving
the private `_write_tsv` caller surface, custom `_format_value()`, LF line
terminator, TSV columns, JSON, Markdown, and review decisions.

Latest single-dR gate writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_single_dr_production_gate_decision_report.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\single_dr_gate_decision_writers.py tests\test_single_dr_production_gate_decision_report.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\single_dr_gate_decision_writers.py
```

Observed results: `19 passed`; ruff passed; mypy passed for 1 source file.
Candidate verdict: true writer-helper cleanup. The single-dR gate writer now
delegates TSV serialization to the shared diagnostic helper while preserving
private `_write_tsv` caller surface, previous `None`/bool/string conversion,
TSV columns, JSON, Markdown, activation decision, and changed-row outputs.

Latest seed-aware writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_seed_aware_backfill_review.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\seed_aware_backfill_review_writers.py tests\test_seed_aware_backfill_review.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\seed_aware_backfill_review_writers.py
```

Observed results: `12 passed`; ruff passed; mypy passed for 1 source file.
Candidate verdict: true writer-helper cleanup. The seed-aware review writer now
delegates TSV serialization to the shared diagnostic helper while retaining the
legacy `_write_tsv` reexport surface, custom bool/float formatting, LF line
terminator, family/blast-radius TSV columns, JSON, Markdown, and review
decisions.

Latest RT-normalization anchor writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_rt_normalization_anchors.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\rt_normalization_anchor_writers.py tests\test_rt_normalization_anchors.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\rt_normalization_anchor_writers.py
```

Observed results: `14 passed`; ruff passed; mypy passed for 1 source file.
Candidate verdict: true writer-helper cleanup. The RT-normalization anchor
writer now delegates TSV serialization to the shared diagnostic helper while
preserving private `_write_tsv` caller surface, custom bool/float formatting,
default CSV line terminator, TSV columns, JSON, and Markdown outputs.

Latest schema-strict writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_diagnostic_io.py tests\test_cwt_peak_candidate_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\tabular_io.py tests\test_diagnostic_io.py tools\diagnostics\cwt_peak_candidate_audit_writers.py tests\test_cwt_peak_candidate_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\tabular_io.py tools\diagnostics\cwt_peak_candidate_audit_writers.py
```

Observed results: `22 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: true shared-helper architecture cleanup. The shared tabular
writer now supports schema-strict `extrasaction="raise"` without changing its
default ignore-extra-fields behavior, and the CWT peak-candidate audit writer
now delegates TSV serialization while preserving strict summary schemas,
optional-float formatting, TSV columns, JSON, Markdown, and CWT classifications.

Latest peak-candidate score writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_diagnostic_io.py tests\test_peak_candidate_score_calibration_report.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\tabular_io.py tests\test_diagnostic_io.py tools\diagnostics\peak_candidate_score_calibration_writers.py tests\test_peak_candidate_score_calibration_report.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\tabular_io.py tools\diagnostics\peak_candidate_score_calibration_writers.py
```

Observed results: `23 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: true schema-strict writer-helper cleanup. The peak-candidate
score calibration writer now delegates TSV serialization to the shared helper
with `extrasaction="raise"` while preserving raw summary value conversion,
strict summary schema checks, `.5f` score formatting, TSV columns, JSON,
Markdown, risk rows, and label-impact rows.

Latest owner-backfill economics writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_diagnostic_io.py tests\test_owner_backfill_request_economics.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\tabular_io.py tests\test_diagnostic_io.py tools\diagnostics\owner_backfill_request_economics.py tests\test_owner_backfill_request_economics.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\tabular_io.py tools\diagnostics\owner_backfill_request_economics.py
```

Observed results: `19 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: true schema-strict writer-helper cleanup. The owner-backfill
request economics writer now delegates non-empty TSV serialization to the shared
helper with `extrasaction="raise"` while preserving first-row dynamic field
order, empty-output behavior, Python-style bool conversion, summary/features
schemas, JSON, Markdown, and request-count behavior.

Latest matrix blast-radius writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_matrix_identity_blast_radius.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\analyze_matrix_identity_blast_radius.py tests\test_matrix_identity_blast_radius.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\analyze_matrix_identity_blast_radius.py
```

Observed results: `9 passed`; ruff passed; mypy passed for 1 source file.
Candidate verdict: true fixed-column writer-helper cleanup. The matrix identity
blast-radius writer now delegates TSV serialization to the shared helper while
preserving fixed-column projection, ignored extra keys, `TRUE` / `FALSE` bool
formatting, raw numeric string conversion, TSV/JSON output semantics, targeted
benchmark joins, and machine-decision projection.

Latest chrom peak segment gate writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_chrom_peak_segment_candidate_gate.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\chrom_peak_segment_candidate_gate.py tests\test_chrom_peak_segment_candidate_gate.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\chrom_peak_segment_candidate_gate.py
```

Observed results: `14 passed`; ruff passed; mypy passed for 1 source file.
Candidate verdict: true explicit-field writer-helper cleanup. The chrom peak
segment gate writer now delegates TSV serialization to the shared helper with
`extrasaction="raise"` while preserving explicit fieldnames, extra-key
rejection, raw value conversion, changed/review TSV schemas, manifest JSON, and
gate decisions. The only adjacent implementation change is an explicit optional
annotation in `_rt_reference_delta()` to match the existing midpoint fallback.

Latest untargeted guardrail CSV writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_untargeted_alignment_guardrails.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\untargeted_alignment_guardrail_io.py tests\test_untargeted_alignment_guardrails.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\untargeted_alignment_guardrail_io.py
```

Observed results: `31 passed`; ruff passed; mypy passed for 1 source file.
Candidate verdict: true dynamic CSV writer-helper cleanup. The untargeted
alignment guardrail comparison writer now delegates non-empty CSV serialization
to the shared delimited writer while preserving required output-path validation,
parent-directory creation, empty-output behavior, first-row field order,
extra-key rejection, raw value conversion, and guardrail facade compatibility.

Latest selected-envelope review queue writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_selected_envelope_review_queue.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\selected_envelope_review_queue.py tests\test_selected_envelope_review_queue.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\selected_envelope_review_queue.py
```

Observed results: `5 passed`; ruff passed; mypy passed for 1 source file.
Candidate verdict: true sanitized writer-helper cleanup. The selected-envelope
review queue writer now delegates TSV serialization to the shared helper while
preserving explicit field order, ignored extra keys, header-only empty outputs,
LF line terminator, parent-directory creation, tab/newline sanitization, JSON
manifest behavior, and diagnostic-only review-queue semantics.

Latest MS1 peak-group NL-scope gate writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_ms1_peak_group_nl_scope_gate.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\ms1_peak_group_nl_scope_gate.py tests\test_ms1_peak_group_nl_scope_gate.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\ms1_peak_group_nl_scope_gate.py
```

Observed results: `9 passed`; ruff passed; mypy passed for 1 source file.
Candidate verdict: true explicit-field writer-helper cleanup. The MS1 peak-group
NL-scope gate writer now delegates TSV serialization to the shared helper with
`extrasaction="raise"` while preserving explicit fieldnames, extra-key
rejection, header-only empty output, raw value conversion, review/context TSV
schemas, manifest JSON, and gate decisions.

Latest targeted GT alignment audit CSV writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_targeted_gt_alignment_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\targeted_gt_alignment_audit_writers.py tools\diagnostics\targeted_gt_alignment_audit_utils.py tests\test_targeted_gt_alignment_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\targeted_gt_alignment_audit_writers.py
```

Observed results: `13 passed`; ruff passed; mypy passed for 1 source file.
Candidate verdict: true dynamic CSV writer-helper cleanup. The targeted GT
alignment audit writer now delegates non-empty CSV serialization to the shared
delimited writer while preserving empty-output behavior, first-row field order,
formula-escape protection, raw value conversion, later-row extra-key failure,
report/SVG rendering, and audit output schemas. The adjacent utility annotation
cleanup is type-only and closes the same focused mypy shard.

Latest alignment validation TSV writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_alignment_validation_writer.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\validation_writer.py tests\test_alignment_validation_writer.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\validation_writer.py
```

Observed results: `3 passed`; ruff passed; mypy passed for 1 source file.
Candidate verdict: true package-level fixed-column writer-helper cleanup. The
alignment validation writer now delegates TSV serialization to the package
tabular writer while preserving parent-directory creation, returned path,
explicit column order, header-only empty output, ignored extra keys, formula
escaping, finite-float formatting, and validation summary/match schemas.

Latest discovery CSV writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_discovery_csv.py tests\test_discovery_review_csv.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\discovery\csv_writer.py tests\test_discovery_csv.py tests\test_discovery_review_csv.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\discovery\csv_writer.py
```

Observed results: `29 passed`; ruff passed; mypy passed for 1 source file.
Candidate verdict: true package-level CSV writer-helper cleanup. The discovery
candidate/review writers now share a small private writer helper backed by the
package tabular writer while preserving parent-directory creation, returned
path, candidate sorting, full/review column contracts, header-only empty output,
value formatting, tuple serialization, CSV quoting, formula escaping, and
review-note rendering.

Latest alignment debug TSV writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_alignment_debug_writer.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\debug_writer.py tests\test_alignment_debug_writer.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\debug_writer.py
```

Observed results: `4 passed`; ruff passed; mypy passed for 1 source file.
Candidate verdict: true package-level LF TSV writer-helper cleanup. The
alignment debug writer now delegates TSV serialization to the package tabular
writer while preserving parent-directory creation, returned path, explicit
field order, header-only empty output, ignored extra keys, LF line terminator,
formula escaping, and debug TSV schemas.

Latest identity-coherence output TSV writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\alignment\identity_coherence\test_output_writer.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\identity_coherence\output_writers.py tests\alignment\identity_coherence\test_output_writer.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\identity_coherence\output_writers.py
```

Observed results: `28 passed`; ruff passed; mypy passed for 1 source file.
Candidate verdict: true package-level fixed TSV writer-helper cleanup. The
identity-coherence output writer now delegates TSV serialization to the package
tabular writer while preserving parent-directory creation, returned path,
explicit columns, header-only empty output, ignored extra keys, raw value
conversion, public facade exports, and identity-coherence TSV schemas.

Latest identity-coherence validation TSV writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\alignment\identity_coherence_validation\test_outputs.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\identity_coherence_validation\outputs.py tests\alignment\identity_coherence_validation\test_outputs.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\identity_coherence_validation\outputs.py
```

Observed results: `5 passed`; ruff passed; mypy passed for 1 source file.
Candidate verdict: true package-level validation TSV writer-helper cleanup. The
identity-coherence validation output writer now delegates summary and V0.4
acceptance TSV serialization to the package tabular writer while preserving
caller-owned summary parent handling, acceptance parent creation, LF acceptance
line terminators, raw value conversion, markdown outputs, acceptance decisions,
and diagnostic-only report wording.

Latest identity-coherence decoy-manifest writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\alignment\identity_coherence_validation\test_decoy_manifest_proposal.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\identity_coherence_validation\decoy_manifest_proposal.py tests\alignment\identity_coherence_validation\test_decoy_manifest_proposal.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\identity_coherence_validation\decoy_manifest_proposal.py
```

Observed results: `8 passed`; ruff passed; mypy passed for 1 source file.
Candidate verdict: true package-level control-manifest TSV writer-helper
cleanup. The decoy-manifest proposal writer now delegates fixed-column TSV
serialization to the package tabular writer while preserving parent-directory
creation, header-only empty output, ignored extra keys, raw value conversion,
proposal filtering, and controls-manifest reader round-trip behavior.

Latest instrument-QC sequence manifest writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_instrument_qc_sequence_manifest.py tests\test_instrument_qc_sequence_manifest_cli.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\instrument_qc\sequence_manifest_writers.py tests\test_instrument_qc_sequence_manifest.py tests\test_instrument_qc_sequence_manifest_cli.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\instrument_qc\sequence_manifest_writers.py
```

Observed results: `16 passed`; ruff passed; mypy passed for 1 source file.
Candidate verdict: true package-level manifest writer-helper cleanup. The
instrument-QC sequence manifest writer now delegates TSV/CSV serialization to
the package tabular writer while preserving parent-directory creation, fixed
manifest/injection-order columns, header-only empty output, matched-only
injection-order filtering, JSON summary payload, and Markdown review output.

Latest RT prior pending-library CSV writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_rt_prior_library.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\rt_prior_library.py tests\test_rt_prior_library.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\rt_prior_library.py
```

Observed results: `6 passed`; ruff passed; mypy passed for 1 source file.
Candidate verdict: true package-level CSV writer-helper cleanup. The RT prior
pending-library writer now delegates CSV serialization to the package tabular
writer while preserving pending-path derivation, parent-directory creation,
non-mutation of the main library, header-only empty output, optional-float
formatting, and load round-trip behavior.

Latest calibration maturity gate TSV writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_instrument_qc_calibration_maturity_gate.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\instrument_qc\calibration_maturity_gate_io.py tests\test_instrument_qc_calibration_maturity_gate.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\instrument_qc\calibration_maturity_gate_io.py tests\test_instrument_qc_calibration_maturity_gate.py
```

Observed results: `6 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: true package-level fixed-column TSV writer-helper cleanup.
The calibration maturity gate writer now delegates TSV serialization to the
package tabular writer while preserving parent-directory creation, fixed
columns, semicolon-joined blockers, raw string conversion, and header-only empty
output.

Latest calibrated trend TSV writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_instrument_qc_calibration_writers.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\instrument_qc\calibration_writers.py tests\test_instrument_qc_calibration_writers.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\instrument_qc\calibration_writers.py tests\test_instrument_qc_calibration_writers.py
```

Observed results: `7 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: true package-level fixed-column TSV writer-helper cleanup.
The calibrated trend writer now delegates TSV serialization to the package
tabular writer while preserving parent-directory creation, fixed columns,
semicolon-joined flags, raw `str()` numeric conversion, and header-only empty
output.

Latest biological ISTD transfer audit TSV writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_instrument_qc_rt_transfer_audit.py tests\test_instrument_qc_biological_istd_transfer_audit_cli.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\instrument_qc\rt_transfer_audit_io.py tests\test_instrument_qc_rt_transfer_audit.py tests\test_instrument_qc_biological_istd_transfer_audit_cli.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\instrument_qc\rt_transfer_audit_io.py tests\test_instrument_qc_rt_transfer_audit.py tests\test_instrument_qc_biological_istd_transfer_audit_cli.py
```

Observed results: `11 passed`; ruff passed; mypy passed for 3 source files.
Candidate verdict: true package-level fixed-column TSV writer-helper cleanup.
The biological ISTD transfer audit writer now delegates TSV serialization to
the package tabular writer while preserving parent-directory creation, fixed
columns, existing `None -> ""` and `.6g` float formatting, summary JSON, and
Markdown review output.

Latest calibration product TSV writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_instrument_qc_calibration_product_writers.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\instrument_qc\calibration_product_writers.py tests\test_instrument_qc_calibration_product_writers.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\instrument_qc\calibration_product_writers.py tests\test_instrument_qc_calibration_product_writers.py
```

Observed results: `5 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: true package-level fixed-column TSV writer-helper cleanup.
The calibration product writer module now routes calibration evidence, matrix
RT preview, RT drift model, leave-one-anchor-out, and matrix response preview
TSVs through one private helper backed by the package tabular writer while
preserving fixed artifact schemas, enum serialization, boolean `true`/`false`,
`None -> ""`, and list semicolon-join formatting.

Latest base instrument-QC TSV writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_instrument_qc_writers.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\instrument_qc\writers.py tests\test_instrument_qc_writers.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\instrument_qc\writers.py tests\test_instrument_qc_writers.py
```

Observed results: `5 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: true package-level fixed-column TSV writer-helper cleanup.
The base instrument-QC writer module now routes trend, diagnostics, and HCD
audit TSVs through one private helper backed by the package tabular writer while
preserving fixed schemas, raw-path string conversion, tuple semicolon-join
fields, `None -> ""`, and legacy `str()` numeric conversion.

Latest instrument-QC lifecycle TSV writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_instrument_qc_lifecycle.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\instrument_qc\lifecycle.py tests\test_instrument_qc_lifecycle.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\instrument_qc\lifecycle.py tests\test_instrument_qc_lifecycle.py
```

Observed results: `4 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: true package-level append/rewrite TSV writer-helper cleanup.
The lifecycle append path now uses the package tabular writer for the temporary
rewrite file while preserving existing-row projection, duplicate fingerprint
detection, lifecycle summary generation, header-only blank TSV output, and row
numeric formatting.

Latest target-pair RT calibration TSV writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_target_pair_rt_calibration.py tests\test_diagnostic_io.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\target_pair_rt_calibration.py xic_extractor\tabular_io.py tests\test_target_pair_rt_calibration.py tests\test_diagnostic_io.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\target_pair_rt_calibration.py xic_extractor\tabular_io.py tests\test_target_pair_rt_calibration.py tests\test_diagnostic_io.py
```

Observed results: `24 passed`; ruff passed; mypy passed for 4 source files.
Candidate verdict: true encoding-preserving package writer cleanup. The
target-pair RT calibration writer now delegates TSV serialization to the package
tabular writer with `encoding="utf-8-sig"` while preserving the BOM,
six-decimal RT delta formatting, fixed schema, header-only empty output, and
loader round-trip behavior.

Latest P7 evidence cost summary TSV writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_p7_evidence_cost_summary.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\p7_evidence_cost_summary.py tests\test_p7_evidence_cost_summary.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\p7_evidence_cost_summary.py tests\test_p7_evidence_cost_summary.py
```

Observed results: `12 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: true fixed-column diagnostic TSV writer-helper cleanup. The
P7 evidence cost summary writer now delegates TSV serialization to the package
tabular writer while preserving the `metric,value` schema, sorted metric rows,
JSON/Markdown outputs, copied evidence artifacts, and CLI status behavior.

Latest untargeted alignment guardrail case-summary TSV writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_untargeted_alignment_guardrails.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\untargeted_alignment_guardrail_outputs.py tools\diagnostics\untargeted_alignment_guardrail_metrics.py tests\test_untargeted_alignment_guardrails.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\untargeted_alignment_guardrail_outputs.py tools\diagnostics\untargeted_alignment_guardrail_metrics.py tests\test_untargeted_alignment_guardrails.py
```

Observed results: `32 passed`; ruff passed; mypy passed for 3 source files.
Candidate verdict: true fixed-column diagnostic TSV writer-helper cleanup. The
untargeted guardrail case-summary writer now delegates TSV serialization to the
package tabular writer while preserving the fixed column schema, row order,
lowercase boolean text, header-only empty output, parent-directory behavior,
comparison rows, and CLI/facade import surface. The adjacent metrics change is
typing-only optional-value narrowing needed to keep the focused shard clean.

Latest multi-tag adduct audit TSV writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_multi_tag_adduct_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\multi_tag_adduct_audit.py tests\test_multi_tag_adduct_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\multi_tag_adduct_audit.py tests\test_multi_tag_adduct_audit.py
```

Observed results: `1 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: true diagnostic TSV writer-helper cleanup. The multi-tag
adduct audit now delegates summary/pairs TSV serialization to the package
tabular writer while preserving schema order, JSON/Markdown output, CLI
behavior, and legacy `str(float)` formatting for adduct pair values. The
adjacent `ArtificialAdductPair` annotation is typing-only and keeps the focused
shard mypy-clean.

Latest P1 resolver-default gate TSV writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_p1_resolver_default_gate.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\p1_resolver_default_gate.py tests\test_p1_resolver_default_gate.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\p1_resolver_default_gate.py tests\test_p1_resolver_default_gate.py
$env:PYTHONDONTWRITEBYTECODE='1'; uv run python tools\diagnostics\p1_resolver_default_gate.py --help
```

Observed results: `3 passed`; ruff passed; mypy passed for 2 source files;
path-style `--help` exited 0.
Candidate verdict: true fixed-column diagnostic TSV writer-helper cleanup. The
P1 gate rows/summary TSV helper now delegates serialization to the package
tabular writer while preserving schema order, LF-only output, `_format_value`
float rendering, JSON/Markdown output, CLI exit behavior, and direct script
bootstrap behavior.

Latest P2 AsLS shadow gate TSV writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_p2_asls_shadow_gate.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\p2_asls_shadow_gate.py tests\test_p2_asls_shadow_gate.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\p2_asls_shadow_gate.py tests\test_p2_asls_shadow_gate.py
$env:PYTHONDONTWRITEBYTECODE='1'; uv run python tools\diagnostics\p2_asls_shadow_gate.py --help
```

Observed results: `7 passed`; ruff passed; mypy passed for 2 source files;
path-style `--help` exited 0.
Candidate verdict: true fixed-column diagnostic TSV writer-helper cleanup. The
P2 AsLS shadow gate rows/summary TSV helper now delegates serialization to the
package tabular writer while preserving schema order, LF-only output,
`_format_value` float rendering, JSON/Markdown output, CLI exit behavior, and
direct script bootstrap behavior.

Latest P2b AsLS promotion gate TSV writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_p2b_asls_promotion_gate.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\p2b_asls_promotion_gate.py tests\test_p2b_asls_promotion_gate.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\p2b_asls_promotion_gate.py tests\test_p2b_asls_promotion_gate.py
$env:PYTHONDONTWRITEBYTECODE='1'; uv run python tools\diagnostics\p2b_asls_promotion_gate.py --help
```

Observed results: `9 passed`; ruff passed; mypy passed for 2 source files;
path-style `--help` exited 0.
Candidate verdict: true fixed-column diagnostic TSV writer-helper cleanup. The
P2b AsLS promotion gate rows/summary TSV helper now delegates serialization to
the package tabular writer while preserving schema order, LF-only output,
tuple-field semicolon rendering, empty optional-field rendering, `_format_value`
float rendering, JSON/Markdown output, CLI exit behavior, and direct script
bootstrap behavior.

Latest P2 baseline truth audit TSV writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_p2_baseline_truth_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\p2_baseline_truth_audit.py tests\test_p2_baseline_truth_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\p2_baseline_truth_audit.py tests\test_p2_baseline_truth_audit.py
$env:PYTHONDONTWRITEBYTECODE='1'; uv run python tools\diagnostics\p2_baseline_truth_audit.py --help
```

Observed results: `10 passed`; ruff passed; mypy passed for 2 source files;
path-style `--help` exited 0.
Candidate verdict: true fixed-column diagnostic TSV writer-helper cleanup. The
P2 baseline truth audit rows/summary TSV helper now delegates serialization to
the package tabular writer while preserving schema order, LF-only output,
relative plot paths, `_format_value` float rendering, JSON/Markdown output,
plot artifact generation, CLI behavior, and direct script bootstrap behavior.
The adjacent matplotlib axis type annotation is typing-only and keeps the
focused shard mypy-clean.

Latest P7 alignment parity artifact TSV writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_p7_alignment_parity.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\p7_alignment_parity.py tests\test_p7_alignment_parity.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\p7_alignment_parity.py tests\test_p7_alignment_parity.py
```

Observed results: `6 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: true fixed-column diagnostic TSV writer-helper cleanup. The
P7 alignment parity artifact TSV writer now delegates serialization to the
package tabular writer while preserving the `check/status/difference` schema,
LF-only output, JSON/Markdown outputs, parity comparison decisions, and CLI
status behavior.

Latest region-first safe-merge comparison TSV writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_region_first_safe_merge_comparison.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\region_first_safe_merge_comparison.py tests\test_region_first_safe_merge_comparison.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\region_first_safe_merge_comparison.py tests\test_region_first_safe_merge_comparison.py
```

Observed results: `4 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: true fixed-column diagnostic TSV writer-helper cleanup. The
region-first safe-merge comparison writer now delegates comparison/summary TSV
serialization to the package tabular writer while preserving schemas, header
order, existing CRLF csv line endings, markdown output, comparison decisions,
and CLI status behavior.

Latest selected-envelope plot-index TSV writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_selected_envelope_plot_review.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\selected_envelope_plot_review.py tests\test_selected_envelope_plot_review.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\selected_envelope_plot_review.py tests\test_selected_envelope_plot_review.py
```

Observed results: `20 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: true fixed-column diagnostic TSV writer-helper cleanup. The
selected-envelope plot-index writer now delegates serialization to the package
tabular writer while preserving fixed header order, existing CRLF csv line
endings, missing optional-field blank rendering, extra-key rejection, PNG/PDF
generation, gallery HTML output, and CLI status behavior. The adjacent segment
overlap local-variable rename is typing-only and keeps the focused shard
mypy-clean.

Latest target-pair RT candidate plot-index TSV writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_target_pair_rt_candidate_plot_review.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\target_pair_rt_candidate_plot_review.py tests\test_target_pair_rt_candidate_plot_review.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\target_pair_rt_candidate_plot_review.py tests\test_target_pair_rt_candidate_plot_review.py
```

Observed results: `7 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: true fixed-column diagnostic TSV writer-helper cleanup. The
target-pair RT candidate plot-index writer now delegates serialization to the
package tabular writer while preserving fixed header order, existing CRLF csv
line endings, missing optional-field blank rendering, extra-key rejection,
PNG/PDF generation, target-pair review selection, and CLI status behavior.

Latest family MS1 overlay trace-summary TSV writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_family_ms1_overlay_plot.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\family_ms1_overlay_writers.py tests\test_family_ms1_overlay_plot.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\family_ms1_overlay_writers.py tests\test_family_ms1_overlay_plot.py
```

Observed results: `21 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: true fixed-column diagnostic TSV writer-helper cleanup. The
family MS1 overlay trace-summary writer now delegates serialization to the
package tabular writer while preserving fixed schema, LF-only line endings,
existing `_format_float` rendering, trace-data JSON payload, PNG/PDF overlay
rendering, and hypothesis-overlay rendering. The adjacent test annotations are
typing-only and keep the focused writer shard mypy-clean.

Latest family MS1 alignment experiment TSV writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_family_ms1_alignment_experiment.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\family_ms1_alignment_experiment.py tests\test_family_ms1_alignment_experiment.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\family_ms1_alignment_experiment.py tests\test_family_ms1_alignment_experiment.py
```

Observed results: `10 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: true fixed-column diagnostic TSV writer-helper cleanup. The
family MS1 alignment experiment main summary, source-family summary,
source-family shift summary, and best-shift summary writers now delegate
serialization to the package tabular writer while preserving fixed schemas,
LF-only line endings, optional-float formatting, no-RAW CLI behavior, and PNG
rendering behavior. The adjacent fake drift lookup protocol completion is
typing-only and keeps the focused shard mypy-clean.

Latest family MS1 overlay batch summary TSV writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_family_ms1_overlay_batch.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\family_ms1_overlay_batch.py tests\test_family_ms1_overlay_batch.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\family_ms1_overlay_batch.py tests\test_family_ms1_overlay_batch.py
```

Observed results: `15 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: true fixed-column diagnostic TSV writer-helper cleanup. The
family MS1 overlay batch summary TSV writer now delegates serialization to the
package tabular writer while preserving fixed schema, LF-only line endings,
existing `_format_value` rendering, markdown/JSON sidecar output, top30
expansion gate behavior, and the existing overlay request locality/dedup logic.

Latest widened writer/helper typed-surface cleanup shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_family_ms1_overlay_batch.py tests\test_standard_peak_backfill_machine_pipeline.py tests\test_run_alignment.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\family_ms1_overlay_batch.py tests\test_family_ms1_overlay_batch.py tools\diagnostics\standard_peak_backfill_machine_pipeline.py tests\test_standard_peak_backfill_machine_pipeline.py scripts\run_alignment.py tests\test_run_alignment.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\family_ms1_overlay_batch.py tests\test_family_ms1_overlay_batch.py tools\diagnostics\standard_peak_backfill_machine_pipeline.py scripts\run_alignment.py
```

Observed results: `75 passed`; ruff passed; focused mypy passed for 4 source
files. The follow-up expanded package mypy gate passed for 45 source files.
Candidate verdict: true typing/narrowing cleanup exposed by a widened no-RAW
writer/helper gate. It preserves standard-peak overlay source validation,
standard-peak preset runtime coercion behavior, and run-alignment preset
publication behavior while making the broader typed surface checkable.

Latest MS1-index backfill audit TSV writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_ms1_index_backfill_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\ms1_index_backfill_audit.py tests\test_ms1_index_backfill_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\ms1_index_backfill_audit.py tests\test_ms1_index_backfill_audit.py
```

Observed results: `3 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: true dynamic-schema diagnostic TSV writer-helper cleanup.
The MS1-index backfill audit summary/examples writers now delegate
serialization to the package tabular writer while preserving dynamic union
header order, existing CRLF csv line endings, `str()` rendering, None-to-blank
rendering, JSON sidecar output, and empty-examples bare-newline behavior.

Latest alignment workbook compare TSV writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_compare_alignment_workbooks.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check scripts\compare_alignment_workbooks.py tests\test_compare_alignment_workbooks.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy scripts\compare_alignment_workbooks.py tests\test_compare_alignment_workbooks.py
```

Observed results: `3 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: true fixed-column script TSV writer-helper cleanup. The
alignment workbook compare TSV artifact now delegates serialization to the
package tabular writer while preserving fixed `status/difference` schema,
parent-directory creation, LF-only line endings, pass/fail row selection, and
the separate text report output.

Latest resolver comparison CSV writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_compare_resolvers.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check scripts\compare_resolvers.py tests\test_compare_resolvers.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy scripts\compare_resolvers.py tests\test_compare_resolvers.py
```

Observed results: `2 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: true fixed-column script CSV writer-helper cleanup. The
resolver comparison CSV artifact now delegates serialization to the package
delimited writer while preserving fixed resolver comparison schema, UTF-8 BOM,
existing CRLF csv line endings, `True`/`False` detected rendering,
optional-number formatting, and CLI stdout summary behavior.

Latest parallel benchmark summary CSV writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_benchmark_parallel.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check scripts\benchmark_parallel.py tests\test_benchmark_parallel.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy scripts\benchmark_parallel.py tests\test_benchmark_parallel.py
```

Observed results: `9 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: true fixed-column script CSV writer-helper cleanup. The
parallel benchmark summary CSV artifact now delegates serialization to the
package delimited writer while preserving fixed benchmark summary schema,
UTF-8 BOM, existing CRLF csv line endings, elapsed-seconds `0.000` formatting,
workbook path stringification, compare-difference joining, and benchmark CLI
behavior. The adjacent captured-config test narrowing is typing-only and keeps
the focused benchmark shard mypy-clean.

Latest validation harness summary CSV writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_validation_harness.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check scripts\validation_harness_core.py tests\test_validation_harness.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy scripts\validation_harness_core.py tests\test_validation_harness.py
```

Observed results: `23 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: true fixed-column script CSV writer-helper cleanup. The
validation harness summary CSV artifact now delegates serialization to the
package delimited writer while preserving fixed validation summary schema,
UTF-8 BOM, existing CRLF csv line endings, parent-directory creation, raw-count
blank rendering, command PowerShell rendering, and compare-difference joining.
The adjacent settings-command tuple annotation is typing-only and keeps the
focused validation harness shard mypy-clean.

Latest local-minimum parameter sweep settings CSV writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_local_minimum_param_sweep.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check scripts\local_minimum_param_sweep.py tests\test_local_minimum_param_sweep.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy scripts\local_minimum_param_sweep.py tests\test_local_minimum_param_sweep.py
```

Observed results: `12 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: true fixed-column script CSV writer-helper cleanup. The
local-minimum parameter sweep staged settings CSV writer now delegates
serialization to the package delimited writer while preserving fixed
`key/value/description` schema, UTF-8 BOM, existing CRLF csv line endings,
settings insertion order, canonical description lookup, and blank description
fallback. Existing local-minimum sweep typing/workbook-failure aggregation
cleanup remains intact.

Latest validation migration settings CSV writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_validate_migration.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check scripts\validate_migration.py tests\test_validate_migration.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy scripts\validate_migration.py tests\test_validate_migration.py
```

Observed results: `12 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: true script settings CSV writer-helper cleanup. The
migration validation settings rewrite now delegates serialization to the
package delimited writer while preserving existing settings header/extra-column
order, UTF-8 BOM, existing CRLF csv line endings, updated `data_dir` value
replacement, missing-key append behavior, and blank fallback values for
description or extra fields. Existing validation migration target-grouping
cleanup remains intact.

Latest xlsx-to-targets public target CSV writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_xlsx_to_targets.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check scripts\xlsx_to_targets.py tests\test_xlsx_to_targets.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy scripts\xlsx_to_targets.py tests\test_xlsx_to_targets.py
```

Observed results: `3 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: public-compatible script CSV writer-helper cleanup. The
XIC-compatible target CSV writer now delegates serialization to the package
delimited writer while preserving fixed target field order, UTF-8 without BOM,
existing CRLF csv line endings, stdout summary behavior, and legacy
`csv.DictWriter` value rendering via a local formatter so `100.0` stays `100.0`
instead of becoming diagnostic-style `100`.

Latest discovery batch-index CSV writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_discovery_pipeline.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\discovery\pipeline.py tests\test_discovery_pipeline.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\discovery\pipeline.py tests\test_discovery_pipeline.py
```

Observed results: `14 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: true fixed-column package CSV writer-helper cleanup. The
discovery batch index writer now delegates serialization to the package
delimited writer while preserving fixed batch-index field order, UTF-8 without
BOM, existing CRLF csv line endings, parent-directory creation, timing stage
metrics, and `csv.DictWriter`'s unexpected-column failure surface via
`extrasaction="raise"`. The adjacent test `_settings()` cast is typing-only and
keeps the constructor/post-init behavior intact.

Latest backfill-scope skipped-ledger TSV writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_backfill_scope.py tests\test_backfill_scope_probe.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\backfill_scope.py tests\test_backfill_scope.py tests\test_backfill_scope_probe.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\backfill_scope.py tests\test_backfill_scope.py tests\test_backfill_scope_probe.py
```

Observed results: `12 passed`; ruff passed; mypy passed for 3 source files.
Candidate verdict: true fixed-column package TSV writer-helper cleanup. The
skipped evidence ledger writer now delegates serialization to the package TSV
writer while preserving fixed ledger field order, UTF-8, explicit LF line
endings, parent-directory creation, and legacy `csv.DictWriter` value rendering
for floats and booleans via a local formatter. The adjacent backfill-scope
locality/request-plan cleanup remains intact.

Latest alignment public TSV writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_alignment_tsv_writer.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\tsv_writer.py tests\test_alignment_tsv_writer.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\tsv_writer.py tests\test_alignment_tsv_writer.py
```

Observed results: `38 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: public alignment TSV writer-helper cleanup with explicit
private-writer characterization. The shared alignment `_write_tsv()` now
delegates serialization to the package TSV writer while preserving local
formula escaping for headers and values, `format_value()` rendering, UTF-8,
explicit LF line endings, parent-directory creation, and header-only empty
output. The adjacent test helper `TypeGuard` annotation is typing-only.

Latest shared peak identity activation TSV writer helper shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_shared_peak_identity_product_activation.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\shared_peak_identity_explanation\product_activation.py tools\diagnostics\apply_shared_peak_identity_activation.py tests\test_shared_peak_identity_product_activation.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\shared_peak_identity_explanation\product_activation.py tools\diagnostics\apply_shared_peak_identity_activation.py tests\test_shared_peak_identity_product_activation.py
```

Observed results: `31 passed`; ruff passed; mypy passed for 3 source files.
Candidate verdict: true activation-product TSV writer-helper cleanup. The
shared peak identity activation `_write_tsv()` now delegates serialization to
the package TSV writer while preserving fixed field order, UTF-8, explicit LF
line endings, parent-directory creation, missing-column blank fallback,
extra-key ignore behavior, and header-only empty output. The adjacent CLI
output variable split and optional-path assertions are typing-only.

Latest package writer/helper combined gate:

Observed results: expanded no-RAW writer/helper pytest shard `225 passed`;
expanded ruff passed; expanded writer/helper mypy passed for 20 source files.

Writer scanner follow-up:

- The schema-strict writer helper now covers CWT, peak-candidate score
  calibration, owner-backfill economics, backfill scope probe dynamic-schema,
  chrom peak segment explicit-field writers, and MS1 peak-group NL-scope
  explicit-field writers. The default-ignore shared writer also now covers
  matrix identity blast-radius fixed-column output, alignment validation TSV
  output, discovery candidate/review CSV output, and alignment debug TSV output;
  identity-coherence output TSV artifacts now also use the package tabular
  writer, and identity-coherence validation summary/acceptance TSV artifacts now
  share the same tabular writer with their distinct parent/line-ending contracts
  preserved. Identity-coherence decoy-manifest proposal TSV output now also uses
  the package tabular writer. Instrument-QC sequence manifest TSV and injection
  order CSV artifacts now share the package tabular writer as well. Instrument-QC
  calibration maturity gate TSV output, calibrated trend TSV output, biological
  ISTD transfer audit TSV output, calibration product TSV artifacts, and RT
  prior pending-library CSV output also use the package tabular writer. Base
  instrument-QC trend/diagnostics/HCD audit TSVs now share the same package
  writer as well, and lifecycle append/rewrite TSVs now use it for temporary
  rewrite output. Target-pair RT calibration TSV output now also uses the
  package writer with explicit `utf-8-sig` encoding. P7 evidence cost summary
  TSV output and untargeted guardrail case assertion summary TSV output also use
  the package writer. Multi-tag adduct summary/pairs TSV output also uses the
  package writer with a legacy value formatter for full float stringification.
  P1 resolver-default gate rows/summary TSV output now uses the package writer
  with explicit LF line endings and its existing `_format_value` formatter.
  Validation migration settings rewrites now also use the package delimited
  writer with their existing header/extra-column rewrite contract preserved.
  Xlsx-to-targets public target CSV output now also uses the package delimited
  writer with a local legacy value formatter to preserve `csv.DictWriter`
  stringification.
  Discovery batch-index CSV output now also uses the package delimited writer
  with `extrasaction="raise"` to preserve unexpected-column failure behavior.
  Backfill-scope skipped-evidence ledger TSV output now also uses the package
  TSV writer with explicit LF endings and a local legacy value formatter.
  Public alignment TSV output now uses the package TSV writer through its
  central `_write_tsv()` helper while preserving formula escaping and
  `format_value()` rendering.
  Shared peak identity activation product TSV outputs now also use the package
  TSV writer through their central `_write_tsv()` helper.
  P2 AsLS shadow gate rows/summary TSV output now uses the same package writer
  pattern with explicit LF line endings and its existing `_format_value`
  formatter. P2b AsLS promotion gate rows/summary TSV output now also uses this
  package writer pattern while preserving tuple-field and empty optional-field
  rendering. P2 baseline truth audit rows/summary TSV output now also uses this
  package writer pattern while preserving relative plot paths and plot artifact
  generation. P7 alignment parity artifact TSV output now also uses this
  package writer pattern while preserving fixed parity-artifact schema and
  LF-only output. Region-first safe-merge comparison and summary TSV output now
  also use this package writer pattern while preserving existing CRLF csv line
  endings and comparison-review schemas. Selected-envelope plot-index TSV
  output now also uses this package writer pattern while preserving fixed
  header order, CRLF line endings, and extra-key rejection. Target-pair RT
  candidate plot-index TSV output now also uses this package writer pattern
  with the same fixed-header, CRLF, and extra-key rejection contract. Family
  MS1 overlay trace-summary TSV output now also uses the package writer while
  preserving fixed schema, LF-only line endings, and existing float rendering.
  Family MS1 alignment experiment summary/source-family TSV outputs now also
  use the package writer while preserving LF-only line endings and
  optional-float rendering. Family MS1 overlay batch summary TSV output now also
  uses the package writer while preserving fixed schema, LF-only line endings,
  `_format_value` rendering, markdown/JSON output, and request
  locality/deduplication behavior. MS1-index backfill audit summary/examples
  TSV output now also uses the package writer while preserving dynamic union
  headers, CRLF line endings, `str()` rendering, None-to-blank rendering, JSON
  output, and empty-examples bare-newline behavior. Alignment workbook compare
  TSV output now also uses the package writer while preserving fixed
  `status/difference` schema, LF-only line endings, parent-directory creation,
  and pass/fail row selection. Resolver comparison CSV output now also uses the
  package delimited writer while preserving fixed schema, UTF-8 BOM, CRLF line
  endings, detected-flag rendering, optional-number formatting, and CLI stdout
  summary behavior. Parallel benchmark summary CSV output now also uses the
  package delimited writer while preserving fixed schema, UTF-8 BOM, CRLF line
  endings, elapsed-seconds formatting, workbook path stringification, and
  compare-difference joining. Validation harness summary CSV output now also
  uses the package delimited writer while preserving fixed schema, UTF-8 BOM,
  CRLF line endings, raw-count blank rendering, command PowerShell rendering,
  and compare-difference joining. Local-minimum parameter sweep staged settings
  CSV output now also uses the package delimited writer while preserving fixed
  `key/value/description` schema, UTF-8 BOM, CRLF line endings, settings order,
  canonical description lookup, and blank description fallback.
  The shared delimited writer covers untargeted guardrail comparison CSV output
  and targeted GT alignment audit CSV output. Sanitized/LF writer coverage now
  includes selected-envelope review queue artifacts and alignment debug TSV
  artifacts. The last hash-sensitive in-memory settings CSV renderer in
  `configuration/hashing.py` now delegates to a neutral in-memory tabular
  renderer after byte-for-byte hash-input characterization. Future private
  writer candidates should still be screened for line terminator, delimiter,
  dynamic schema, encoding/BOM requirements, extra-key semantics,
  parent-directory behavior, empty-output behavior, sanitization,
  formula-escape behavior, and raw `csv.writer` conversion before migration.

Post writer-helper slice scan:

```powershell
rg -n "csv\.DictWriter|csv\.writer|writeheader\(" xic_extractor tools scripts --glob "*.py"
```

Current remaining non-output direct-writer candidates outside the shared helper:

- none

Do not batch-migrate these blindly: many are `utf-8-sig`, dynamic schema,
append/rewrite, validation-harness, or review-output surfaces that need focused
contract tests before delegating to the shared writer. Public extraction output
writers under `xic_extractor/output/` are intentionally deferred from this
diagnostics/package-helper pass because they are public workbook/CSV surfaces,
not low-risk diagnostic helper cleanup.

Latest hash-sensitive in-memory writer shard:

- `xic_extractor/tabular_io.py` now exposes `render_delimited_rows()` for
  in-memory CSV/TSV rendering without touching file newline behavior.
- `xic_extractor/configuration/hashing.py` now uses that helper for
  `_settings_csv_bytes_with_overrides()` while preserving UTF-8 BOM, CRLF CSV
  line endings, existing-key override behavior, appended override rows, and
  description fallback bytes.
- `write_delimited_rows()` and `render_delimited_rows()` now share private
  writer setup, row formatting, and strict extra-field validation helpers while
  keeping file-path newline handling and in-memory newline handling separate.
- `tests/test_diagnostic_io.py` now characterizes in-memory rendering for
  default CRLF + diagnostic value formatting, explicit LF tab-delimited output,
  and `extrasaction="raise"` failures.

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_diagnostic_io.py tests\test_config_hash.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\tabular_io.py tests\test_diagnostic_io.py tests\test_config_hash.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\tabular_io.py
rg -n "csv\.DictWriter|csv\.writer|writeheader\(" xic_extractor tools scripts --glob "*.py"
```

Observed results: `26 passed`; ruff passed; mypy passed for
`xic_extractor\tabular_io.py`; direct writer scan now reports only the shared
helpers in `tabular_io.py`.

Scanner follow-up: `xic_extractor/alignment/backfill_scope.py` around
`_loose_compatible_neighbor_ids` is currently classified as a false-positive /
already-localized loop. The code already groups by neutral-loss tag, sorts by
RT, and uses `_rt_window_neighbors` with early break; no lower-risk cleanup was
selected there in this pass. The separate skipped-ledger writer has now been
migrated to the shared package TSV writer with LF/value-format characterization.

Second scanner follow-up:

```powershell
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 80
```

Current classifications:

- `gui/config_io.py` fieldname scan: already handled in the current dirty diff
  by tracking seen fieldnames once.
- `scripts/add_istd_rt_trend.py` median calculation: already handled in the
  current dirty diff by grouping QC/all sample RT values while walking ordered
  rows once.
- `scripts/validate_migration.py`: comparison grouping is already handled in
  the current dirty diff by grouping validation rows by target once before
  comparison; settings CSV rewrite now uses the shared package delimited writer
  with header/extra-column characterization.
- `build_istd_false_missing_fixture.py`: left unchanged; fixed two-row legacy
  mapping and keyed targeted rows make the scanner hit low-impact.
- `area_integration_uncertainty_audit.py`: left unchanged in this pass; the
  facade/package split is already present and no bounded no-behavior cleanup was
  identified.
- `ms1_peak_group_nl_scope_gate.py`: writer helper cleanup is implemented, but
  the repeated-list scanner hit remains classified as unchanged; the repeated
  lists mirror separate gate/review outputs and manifest counts, so collapsing
  them now would
  trade readability for little locality gain.
- `targeted_nl_dropout_root_cause*`,
  `cross_report_evidence_consistency*`, and workbook/row compare helpers:
  currently classified as low-yield or deterministic-ordering scanner leads,
  not immediate refactor targets.
- `analyze_xic_request_locality.py`: remaining hits are expected per-sample
  candidate CSV reads, per-sample RAW handle use, and the already bounded
  near-redundant RT sweep.
- `xlsx_to_targets.py` and `local_minimum_param_sweep.py`: already handled in
  earlier current-diff slices; xlsx-to-targets target CSV writing now also uses
  the shared package delimited writer with public value-format characterization.
  Remaining hits are plan/application loops, workbook writing, or deterministic
  ordering.
- `discovery/pipeline.py`: batch-index CSV writing now uses the shared package
  delimited writer with fixed-schema and extra-column characterization.
- `shared_peak_identity_explanation/product_activation.py`: activation product
  TSV writing now uses the shared package TSV writer with LF/header-only
  characterization.
- `configuration/hashing.py`: now handled with an in-memory shared renderer and
  byte-for-byte settings override hash-input characterization.
- `folding.py` and `claim_registry.py`: left unchanged in this pass because
  their scanner hits sit inside behavior-sensitive greedy grouping / claim
  resolution algorithms that need broader parity gates before changing.
- `backfill_ms1_product_authority.py` and
  `backfill_candidate_ms2_product_authority.py`: left unchanged; sorted
  allowlist-key traversal is intentional deterministic audit output.
- `drift_evidence.py`: left unchanged; per-label sample sorting preserves
  deterministic trend output and has no lower-risk locality improvement here.

Third scanner follow-up:

- `evidence_spine_consistency_analysis.py`: already handled by the earlier
  per-sample RT-sorted cell index. Remaining scanner hits are index
  construction and summary/reason expansion, not a new bounded hotspot.
- `multi_tag_adduct_audit.py`: left unchanged; wrapper cost is now dominated by
  the package-level adduct matcher that was already indexed by m/z delta.
- `region_first_safe_merge_comparison.py`: algorithmic scanner hits remain
  unchanged; the nested work is sample/target result-matrix expansion plus
  small summary rows, not a repeated lookup that can be safely collapsed. Its
  fixed-schema comparison/summary TSV writer was handled separately in the
  writer-helper cleanup slice.
- `family_ms1_backfill_review_io.py`: left unchanged; per-directory sorted
  glob preserves argument-directory order before explicit trace JSON files, so
  global sorting would change duplicate-family override semantics.
- `p7_alignment_parity.py`: algorithmic scanner hits remain intentionally
  unchanged; sorted set comparisons are deterministic parity-report output and
  should not be optimized away without changing review readability. Its
  fixed-schema artifact TSV writer was handled separately in the writer-helper
  cleanup slice.
- `targeted_istd_benchmark_stats.py`: left unchanged; the rank/tie scanner hit
  is a sorted-rank linear pass after the initial sort, while rewriting Pearson
  into a one-pass formula risks numerical drift without a measured bottleneck.
- `alignment_decision_report_rendering.py`: left unchanged; the RT-band nested
  loop is a fixed four-outcome visual projection, not input-size-sensitive.
- `ms1_index_backfill_audit.py`: left unchanged in this no-RAW pass; remaining
  hits are RAW-facing audit aggregation/writer loops and lack a focused
  no-RAW unit surface for safe behavior-preserving refactor.
- `compare_resolvers.py`, `compare_workbooks.py`, and
  `compare_alignment_workbooks.py`: left unchanged; their scanner hits are
  deterministic output ordering or workbook/cell comparison loops that define
  the tools' public comparison behavior.

Fourth scanner follow-up:

- `tools/diagnostics/alignment_decision_report_model.py`: handled a bounded
  cleanliness-summary locality cleanup. Warning-flag membership now uses one
  precomputed set, and primary cleanliness rows are scanned once for
  zero-present counts, warning flag counts, and top warning row candidates.
  Output keys, ordered `flag_counts`, warning count formula, and top-warning
  ordering are unchanged. Known ISTD exception checks now also avoid allocating
  a new empty set for every missing target while preserving the existing
  all-modes-known behavior.

Latest alignment decision report model shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_alignment_decision_report.py tests\test_alignment_decision_report_io.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\alignment_decision_report_model.py tests\test_alignment_decision_report.py tests\test_alignment_decision_report_io.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\alignment_decision_report_model.py
```

Observed results: `13 passed`; ruff passed; mypy passed for 1 source file.

Latest single-dR loader table-cache shard:

- `tools/diagnostics/single_dr_gate_decision_loaders.py` now caches raw
  discovery candidate tables by resolved `candidate_csv` path within one
  `load_discovery_candidates()` call. It still rebuilds candidate quality rows
  per batch-index row, preserving sample fallback behavior when the candidate
  table omits `sample_stem`.
- The new characterization test proves duplicate index rows referencing the
  same candidate table only read that table once while still producing
  sample-specific candidate keys.

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_single_dr_production_gate_decision_report.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\single_dr_gate_decision_loaders.py tests\test_single_dr_production_gate_decision_report.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\single_dr_gate_decision_loaders.py
```

Observed results: `20 passed`; ruff passed; mypy passed for 1 source file.

Latest targeted peak reliability summary shard:

- `tools/diagnostics/targeted_peak_reliability_classifier.py` now builds
  per-target reliability summaries through a single accumulator per target
  instead of grouping rows and then re-scanning each target bucket for state
  counts, reason counts, and first known exception.
- Summary output ordering and contract are unchanged: target labels are still
  sorted, role still comes from the first row for the target, top risk-reason
  ordering follows first-seen `Counter.most_common()` behavior, and the first
  non-empty known exception still wins.

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_targeted_peak_reliability_classifier.py tests\test_targeted_peak_reliability_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\targeted_peak_reliability_classifier.py tests\test_targeted_peak_reliability_classifier.py tests\test_targeted_peak_reliability_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\targeted_peak_reliability_classifier.py
```

Observed results: `22 passed`; ruff passed; mypy passed for 1 source file.

Latest targeted evidence review queue shard:

- `tools/diagnostics/targeted_evidence_review_report_model.py` now precomputes
  root-cause `(sample_name, target_label)` keys once before scanning weak-area
  reliability rows. Previously that root-key set was rebuilt for every
  reliability row considered for weak-area queue insertion.
- Review queue behavior is unchanged: cross-report rows still lead, root-cause
  rows still deduplicate matching weak-area reliability rows, weak-area-only
  rows still enter the queue, and the existing priority sort remains the final
  ordering authority.
- `tests/test_targeted_evidence_review_report.py` now characterizes the
  root-row deduplication key contract directly instead of relying only on HTML
  smoke coverage.

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_targeted_evidence_review_report.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\targeted_evidence_review_report_model.py tests\test_targeted_evidence_review_report.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\targeted_evidence_review_report_model.py
```

Observed results: `8 passed`; ruff passed; mypy passed for 1 source file.

Latest targeted evidence review summary assembly shard:

- `tools/diagnostics/targeted_evidence_review_report_model.py` now builds the
  first-view summary payload from the already parsed `target_reliability` rows
  via `_report_summary()`. Previously `build_report()` re-scanned the raw
  reliability summary TSV rows four times and re-parsed the same integer
  fields after `_target_reliability()` had already normalized them.
- Report behavior is unchanged: eligible, review-positive, review, negative,
  and root-cause included counts keep the same names and integer values, while
  target ordering remains owned by `_target_reliability()`.
- `tests/test_targeted_evidence_review_report.py` now characterizes the
  `_report_summary()` payload directly. The first focused run exposed only a
  test fixture call missing the required `review_positive` keyword; after
  fixing that fixture, the full focused gate passed.

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_targeted_evidence_review_report.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\targeted_evidence_review_report_model.py tests\test_targeted_evidence_review_report.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\targeted_evidence_review_report_model.py tests\test_targeted_evidence_review_report.py
```

Observed results: first run `1 failed, 8 passed` due test fixture setup; final
rerun `9 passed`; ruff passed; mypy passed for 2 source files.

Latest targeted ISTD writer rollup reuse shard:

- `tools/diagnostics/targeted_istd_benchmark_writers.py` now materializes
  summary rows once for summary TSV and JSON output, and computes benchmark
  overall counts once for JSON and Markdown. Previously summary rows were
  re-rendered for JSON after TSV output, and overall fail/warn counts were
  recomputed separately for JSON and Markdown.
- Output behavior is unchanged: JSON `overall_status`, fail/warn counts,
  active fail/warn counts, false-positive tag count, threshold serialization,
  summary row rendering, and Markdown overall status keep the same values.
- `tests/test_targeted_istd_benchmark.py` now characterizes writer-level JSON
  and Markdown rollup agreement directly. A test-helper type cleanup changed
  `_write_targeted_workbook()` RT conversion to `float(str(...))` so the
  focused mypy gate can include the touched test file without changing fixture
  values.

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_targeted_istd_benchmark.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\targeted_istd_benchmark_writers.py tests\test_targeted_istd_benchmark.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\targeted_istd_benchmark_writers.py tests\test_targeted_istd_benchmark.py
```

Observed results: first run `15 passed` and ruff passed, with mypy exposing the
test-helper `object` to `float()` issue; final rerun `15 passed`; ruff passed;
mypy passed for 2 source files.

Latest target-pair candidate per-target grouping shard:

- `tools/diagnostics/target_pair_rt_candidate_plot_review.py` now groups
  review candidates by `target_label` once before per-target high-delta plot
  selection. Previously it built a sorted target-label list and then re-scanned
  all candidate rows for every target.
- Selection behavior is unchanged: accepted/product-switch rows still lead,
  8-oxodG contradicted and paired-area-ratio groups still run before the
  per-target pass, target groups are still processed in sorted label order,
  each target still sorts candidates by absolute pair-RT delta descending, and
  selected row identities still deduplicate across groups.
- `tests/test_target_pair_rt_candidate_plot_review.py` now characterizes
  sorted target-group emission and per-target high-delta selection directly.

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_target_pair_rt_candidate_plot_review.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\target_pair_rt_candidate_plot_review.py tests\test_target_pair_rt_candidate_plot_review.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\target_pair_rt_candidate_plot_review.py tests\test_target_pair_rt_candidate_plot_review.py
```

Observed results: `8 passed`; ruff passed; mypy passed for 2 source files.

Latest targeted NL dropout summary aggregation shard:

- `tools/diagnostics/targeted_nl_dropout_root_cause_logic.py` now accumulates
  root-cause summary counts with one pass over reliability rows and one pass
  over root-cause rows. Previously `_summary()` built separate `Counter`
  objects from separate row scans and separately summed review-positive rows.
- Summary behavior is unchanged: `rows_checked` still counts all reliability
  rows, `review_positive_count` still counts only targeted review-positive
  reliability rows, `missing_candidate_count` still comes from the
  `no_selected_candidate` bucket, and `_format_counter()` still sorts summary
  count keys lexically.
- Existing targeted NL dropout tests already cover bucket counts, product
  absence reason counts, missing-selected classification, TSV summary schema,
  and JSON summary serialization.

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_targeted_nl_dropout_root_cause_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\targeted_nl_dropout_root_cause_logic.py tests\test_targeted_nl_dropout_root_cause_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\targeted_nl_dropout_root_cause_logic.py
```

Observed results: `8 passed`; ruff passed; mypy passed for 1 source file.

Latest P7 evidence cost aggregation shard:

- `tools/diagnostics/p7_evidence_cost_summary.py` now computes timing metrics
  in one pass over timing records and skipped-ledger metrics in one pass over
  ledger rows. Previously `_timing_metrics()` used separate filtered sums for
  owner elapsed, total elapsed, extract count, and RAW call count, while
  `_ledger_metrics()` summed the same skipped-request column twice and built
  feature IDs in a separate comprehension.
- Metric names and semantics are unchanged: `raw_xic_requests_skipped` and
  `skipped_raw_xic_requests` still intentionally carry the same skipped-request
  total, `skipped_feature_count` still counts unique feature family IDs, and
  timing stages still exclude `*.extract_xic` records from total-stage elapsed.

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_p7_evidence_cost_summary.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\p7_evidence_cost_summary.py tests\test_p7_evidence_cost_summary.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\p7_evidence_cost_summary.py tests\test_p7_evidence_cost_summary.py
```

Observed results: `12 passed`; ruff passed; mypy passed for 2 source files.

Latest cross-report evidence consistency summary aggregation shard:

- `tools/diagnostics/cross_report_evidence_consistency_analysis.py` now
  accumulates consistency status counts and issue counts in one pass over
  `ConsistencyRow` output. Previously `_summary()` built an issue `Counter`
  and separately summed consistent and mismatch rows from the same tuple.
- Summary behavior is unchanged: `rows_checked` still counts rendered rows,
  missing-candidate and missing-reliability counts still come from issue
  counts, and `issue_counts` still follows first-seen issue ordering from the
  sorted consistency rows.
- `tests/test_cross_report_evidence_consistency.py` now characterizes the
  `issue_counts` string ordering explicitly so the accumulator rewrite cannot
  silently change review TSV/JSON payload semantics.

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_cross_report_evidence_consistency.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\cross_report_evidence_consistency_analysis.py tests\test_cross_report_evidence_consistency.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\cross_report_evidence_consistency_analysis.py tests\test_cross_report_evidence_consistency.py
```

Observed results: `5 passed`; ruff passed; mypy passed for 2 source files.

Latest P2 baseline truth family-summary aggregation shard:

- `tools/diagnostics/p2_baseline_truth_audit.py` now builds each family summary
  row through `_family_summary_row()`, collecting classification counts and all
  numeric summary inputs in one pass over the family bucket. Previously
  `_build_summary_rows()` re-scanned the same `family_rows` sequence for each
  median/max field after computing classification counts.
- Summary behavior is unchanged: target/family grouping order still comes from
  sorted group keys, dominant classification still follows
  `Counter.most_common(1)` first-seen tie behavior, `classification_counts`
  still sorts class names lexically, and the summary plot path still comes from
  the first row in the family bucket.
- `tests/test_p2_baseline_truth_audit.py` now characterizes a multi-row family
  summary directly, including medians, max value, dominant class,
  classification count ordering, review status, and first plot path.

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_p2_baseline_truth_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\p2_baseline_truth_audit.py tests\test_p2_baseline_truth_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\p2_baseline_truth_audit.py tests\test_p2_baseline_truth_audit.py
```

Observed results: `11 passed`; ruff passed; mypy passed for 2 source files.

Post-P2 scanner recheck:

```powershell
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 180 | rg 'Location: `tools\\diagnostics' -A 2
```

Current no-new-code classifications from the recheck:

- `tools/diagnostics/alignment_decision_report_rendering.py:426`: false
  positive. The nested loop is a fixed four-outcome RT-band rendering expansion,
  not repeated data scanning.
- `tools/diagnostics/analyze_matrix_identity_blast_radius.py:137`: false
  positive. The sorted traversal is the one-time output ordering for decision
  rows, not sort-in-loop work.
- `scripts/compare_workbooks.py:123`: left unchanged. The row/column nested
  loop is the workbook cell comparison contract itself.
- `tools/diagnostics/rt_normalization_anchor_analysis.py:41`: left unchanged.
  The sorted traversal is a one-time family ordering step; no repeated lookup
  was identified.
- `tools/diagnostics/family_ms1_alignment_experiment.py` remaining hits are
  plot rendering, source-family grouping, and shape-correlation calculations
  inside an already dirty diagnostics slice. Changing them needs a broader
  plot/shape parity gate, so no extra cleanup was stacked here.
- `tools/diagnostics/changed_row_mode_overlay_review.py` remaining hits are
  mode assignment, Gaussian15 similarity, subthreshold marker rendering, and
  mode-aligned plotting inside an already dirty diagnostics slice. These remain
  behavior-sensitive and are not a safe post-P2 add-on.

Latest targeted GT target-role loader shard:

- `tools/diagnostics/targeted_gt_alignment_audit_io.py` now builds the analyte
  and ISTD workbook row buckets through `_rows_by_target_role_map()`, scanning
  propagated target workbook rows once for both requested `(target, role)`
  pairs. Previously `_load_target_ground_truth()` scanned the same workbook rows
  once for the analyte target and again for the ISTD target.
- Public facade behavior is unchanged: `_rows_by_target_role()` remains
  available and delegates to the shared map helper, output target order still
  comes from sorted analyte sample names, unrelated target/role rows are ignored,
  and missing sample values for requested target/role rows still raise the same
  `Missing sample for <target>/<role>` error.
- `tools/diagnostics/targeted_gt_alignment_audit_writers.py` now types
  `_write_dict_csv()` as accepting `Sequence[object]` so the focused mypy gate
  covers the facade call sites without changing serialization behavior.
- `tests/test_targeted_gt_alignment_audit.py` now characterizes the shared
  target-role map grouping, compatibility helper delegation, unrelated-row
  exclusion, and missing-sample error path.

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_targeted_gt_alignment_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\targeted_gt_alignment_audit_io.py tools\diagnostics\targeted_gt_alignment_audit_writers.py tests\test_targeted_gt_alignment_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\targeted_gt_alignment_audit_io.py tools\diagnostics\targeted_gt_alignment_audit_writers.py tests\test_targeted_gt_alignment_audit.py
```

Observed results: `14 passed`; ruff passed; mypy passed for 3 source files.

Latest combined focused cleanup gate:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_alignment_adduct_annotation.py tests\test_alignment_matrix_identity.py::test_artificial_adduct_annotation_does_not_demote_supported_family tests\test_owner_backfill_request_economics.py tests\test_matrix_identity_blast_radius.py tests\test_single_dr_production_gate_decision_report.py tests\test_shift_aware_backfill_calibration_pack.py tests\test_alignment_primary_area_authority_audit.py tests\test_gaussian15_area_pressure_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\adduct_annotation.py tests\test_alignment_adduct_annotation.py tools\diagnostics\owner_backfill_request_economics.py tests\test_owner_backfill_request_economics.py tools\diagnostics\analyze_matrix_identity_blast_radius.py tests\test_matrix_identity_blast_radius.py tools\diagnostics\single_dr_production_gate_decision_report.py tools\diagnostics\single_dr_gate_decision_loaders.py tests\test_single_dr_production_gate_decision_report.py tools\diagnostics\shift_aware_backfill_calibration_pack.py tests\test_shift_aware_backfill_calibration_pack.py tools\diagnostics\alignment_primary_area_authority_audit.py tests\test_alignment_primary_area_authority_audit.py tools\diagnostics\gaussian15_area_pressure_audit.py tests\test_gaussian15_area_pressure_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\adduct_annotation.py tools\diagnostics\owner_backfill_request_economics.py tools\diagnostics\analyze_matrix_identity_blast_radius.py tools\diagnostics\single_dr_production_gate_decision_report.py tools\diagnostics\shift_aware_backfill_calibration_pack.py tools\diagnostics\alignment_primary_area_authority_audit.py tools\diagnostics\gaussian15_area_pressure_audit.py
git diff --check -- xic_extractor\alignment\adduct_annotation.py tests\test_alignment_adduct_annotation.py tools\diagnostics\owner_backfill_request_economics.py tests\test_owner_backfill_request_economics.py tools\diagnostics\analyze_matrix_identity_blast_radius.py tests\test_matrix_identity_blast_radius.py tools\diagnostics\INDEX.md docs\superpowers\notes\2026-06-11-clean-code-optimization-inventory.md docs\superpowers\notes\2026-06-11-backfill-diagnostics-architecture-cleanup-note.md
```

Observed results: `48 passed`; ruff passed; mypy passed for 7 source files;
`git diff --check` reported no whitespace errors, only CRLF conversion
warnings.

Repo gates:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tools tests scripts gui
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -v --tb=short -x
git diff --check
```

Observed results:

- `ruff`: all checks passed.
- `mypy`: success, no issues found in 329 source files.
- `pytest`: `3637 passed, 1 skipped` after the GUI config field-order, ISTD RT
  median, validation migration grouping, xlsx-to-targets ISTD pairing, and
  local-minimum sweep failure-cache characterization tests were added; the
  overlay scan-RT cache characterization updated an existing overlay test; the
  evidence-spine RT-window index characterization updated the existing
  evidence-spine consistency test shard; the ASLS ref-root cache
  characterization updated the existing ASLS validation input test shard; the
  low-MS1 seed-group ordering characterization updated the existing low-MS1
  coverage audit test shard; the peak-candidate score label-impact slice added
  score-bucket ordering and invalid `selected` input characterization. The ASLS
  fixture-manifest required-key slice reused existing manifest validation tests.
  The locality same-window census slice added exact-duplicate characterization.
  The family-MS1 review queue ordering slice extended an existing report test
  without changing the total no-RAW test count.
- `git diff --check`: no whitespace errors; only CRLF conversion warnings.

Latest shared peak identity diagnostic token shard:

- Scanner recheck found several clean package hits under
  `xic_extractor/alignment/shared_peak_identity_explanation/`. The
  `assembler.py` hit was only a low-impact per-row sequence materialization, and
  `feature_family.py` / identity-coherence grouping hits remain behavior-
  sensitive production grouping logic, so they were not changed in this shard.
- `classifier._join_unique()` now tracks already-emitted semicolon tokens with a
  local `seen` set while preserving first-seen output order. This removes the
  previous list-membership path for diagnostic fields such as
  `machine_blockers`, `source_roles_seen`, and `source_artifacts`.
- `shadow_labels._support_blockers()` uses the same local `seen` pattern for
  `machine_evidence_blockers`, preserving readiness output order while avoiding
  repeated linear membership checks as machine-evidence rows grow.
- Added focused characterization for first-seen token order in
  `tests/test_shared_peak_identity_classifier.py` and
  `tests/test_shared_peak_identity_shadow_labels.py`. This is a no-RAW,
  diagnostic-output-only cleanup; no product activation decision, matrix value,
  workbook schema, or RAW access path changes.

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_shared_peak_identity_classifier.py tests\test_shared_peak_identity_shadow_labels.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\shared_peak_identity_explanation\classifier.py xic_extractor\alignment\shared_peak_identity_explanation\shadow_labels.py tests\test_shared_peak_identity_classifier.py tests\test_shared_peak_identity_shadow_labels.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\shared_peak_identity_explanation\classifier.py xic_extractor\alignment\shared_peak_identity_explanation\shadow_labels.py tests\test_shared_peak_identity_classifier.py tests\test_shared_peak_identity_shadow_labels.py
```

Observed results: `39 passed`; ruff passed; mypy passed for 4 source files.

Latest tier2 trace producer family-cell split shard:

- `xic_extractor/alignment/validation_compare.py` was inspected but left
  unchanged: its scanner hit is the feature matching nested-loop algorithm, so
  changing it requires a dedicated validation-compare parity gate rather than a
  small cleanup shard.
- `xic_extractor/alignment/tier2_trace_producer.py` now classifies family cells
  into detected seed cells and rescued cells through
  `_split_detected_and_rescued_cells()`, scanning `cell_rows` once before the
  existing seed-count guard and rescued top-N area sort. The RAW trace loader,
  v0.1 diagnostic criteria, sidecar schema, blocker vocabulary, and rescued
  ordering remain unchanged.
- `tests/test_tier2_raw_trace_producer.py` now characterizes the multiple
  detected-seed blocker through the public `build_tier2_trace_evidence_rows()`
  path. The focused mypy gate also tightened the synthetic trace-loader return
  annotations to their actual float tuple shape.

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_tier2_raw_trace_producer.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\tier2_trace_producer.py tests\test_tier2_raw_trace_producer.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\tier2_trace_producer.py tests\test_tier2_raw_trace_producer.py
```

Observed results: `7 passed`; ruff passed; mypy passed for 2 source files.

Latest shared peak machine-evidence token uniqueness shard:

- `xic_extractor/alignment/shared_peak_identity_explanation/machine_evidence_support.py`
  still had the same order-preserving list-membership de-duplication pattern in
  `_unique()`. That helper is used for manual-derived facts,
  `missing_machine_evidence`, and literature references, all diagnostic TSV
  token fields.
- `_unique()` now uses a local `seen` set while preserving first-seen order.
  This aligns the machine-evidence support path with the earlier classifier and
  readiness blocker token cleanups without changing output vocabulary.
- `tests/test_shared_peak_identity_shadow_labels.py` now characterizes a public
  `build_machine_evidence_support_rows()` path where candidate-MS2 and MS1
  pattern evidence both produce `pattern_metric_not_supportive`; the exported
  `missing_machine_evidence` remains a single first-seen token and the evidence
  support status remains `machine_observed_conflict`.

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_shared_peak_identity_shadow_labels.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\shared_peak_identity_explanation\machine_evidence_support.py tests\test_shared_peak_identity_shadow_labels.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\shared_peak_identity_explanation\machine_evidence_support.py tests\test_shared_peak_identity_shadow_labels.py
```

Observed results: `35 passed`; ruff passed; mypy passed for 2 source files.

Post shared-peak token cleanup scanner recheck:

```powershell
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 120 | rg 'Location: `xic_extractor\\alignment\\shared_peak_identity_explanation|Location: `xic_extractor\\diagnostics|Location: `tools\\diagnostics' -A 2
```

Follow-up verdicts:

- `tools/diagnostics/shared_peak_identity_explanation.py:989`: left unchanged.
  The hit is CLI optional blast-radius artifact parsing; membership is against
  `OPTIONAL_ARTIFACT_ROLES`, and the role/path loop is one pass over explicit
  CLI arguments rather than a data-scale diagnostic hotspot.
- `xic_extractor/alignment/shared_peak_identity_explanation/wrong_peak_root_cause.py:260`:
  left unchanged. `_sample_keys()` de-duplicates at most `sample_id` and
  `sample_stem`, so the list-membership shape is bounded to two candidates.
- `xic_extractor/alignment/shared_peak_identity_explanation/writers.py`: left
  unchanged. The remaining findings are report counters and filtered report
  sections; the current dirty diff only moves the TSV writer import to
  `xic_extractor.tabular_io`.
- `tools/diagnostics/single_dr_gate_decision_loaders.py`: left unchanged in
  this pass. The existing dirty diff already caches duplicated candidate tables;
  remaining scanner hits are the cached candidate-row iteration and targeted
  ISTD family membership expansion, not repeated file reads.

Latest cross-report evidence consistency summary shard:

- `tools/diagnostics/asls_truth_validation_inputs.py` was rechecked first.
  Remaining scanner hits are already covered by existing dirty slices
  (`_repo_root_for_ref_base()` cache and Tier C blocker set membership) or are
  schema cross-check set lookups; no new ASLS change was added in this pass.
- `tools/diagnostics/cross_report_evidence_consistency_analysis.py` now keeps
  `_summary()` as a single pass over consistency rows, accumulating consistent
  count, mismatch count, and issue counts together instead of re-scanning the
  rows for each summary field.
- `tests/test_cross_report_evidence_consistency.py` characterizes the
  semicolon-joined `issue_counts` order for the fixture, preserving report
  output while covering the single-pass aggregation path.

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_cross_report_evidence_consistency.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\cross_report_evidence_consistency_analysis.py tests\test_cross_report_evidence_consistency.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\cross_report_evidence_consistency_analysis.py tests\test_cross_report_evidence_consistency.py
```

Observed results: `5 passed`; ruff passed; mypy passed for 2 source files.

Post overlay RAW access scanner recheck:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_family_ms1_overlay_batch.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\family_ms1_overlay_batch.py tests\test_family_ms1_overlay_batch.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\family_ms1_overlay_batch.py tests\test_family_ms1_overlay_batch.py
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 120 | rg 'Location: `tools\\diagnostics\\family_ms1_overlay_batch.py' -A 2
```

Observed results: `15 passed`; ruff passed; mypy passed for 2 source files.
The scanner still reports `family_ms1_overlay_batch.py:452`, `:460`, `:484`,
`:499`, and `:570`. Current verdict:

- The scan-RT cache and duplicate-XIC reuse slices already cover the safe
  no-RAW overlay locality/reuse wins in this module.
- The remaining `:452` and `:484` loops are the required request-by-family-cell
  projection that materializes one logical overlay row per request/cell.
- The `:460` and `:499` sorts preserve deterministic sample/rank output order.
- The `:570` loop maps union superwindow traces back to exact original scan
  windows. Reworking that path should be paired with RAW-backed parity evidence
  for activation decisions, value deltas, matrix, and identity, not folded into
  this no-RAW clean-code pass.

Post ISTD RT trend scanner recheck:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_add_istd_rt_trend.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check scripts\add_istd_rt_trend.py tests\test_add_istd_rt_trend.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy scripts\add_istd_rt_trend.py tests\test_add_istd_rt_trend.py
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 120 | rg 'Location: `scripts\\add_istd_rt_trend.py' -A 2
```

Observed results: `2 passed`; ruff passed; mypy passed for 2 source files.
The focused mypy gate exposed that the new test fixtures were plain
`dict[str, str]` rather than the script's `InjectionOrderRow` shape; the test
fixtures now include `injection_order` and are annotated with
`list[InjectionOrderRow]`. The remaining scanner hits are expected:

- `:248` is the already-optimized one-pass median accumulation over actual
  sample RT entries, guarded by `label_set`.
- `:301` and `:307` are workbook cell rendering loops for metadata and each
  ISTD column.
- `:365` is first-seen ISTD label collection with a `seen` set; no repeated
  list-membership path remains.

Post GUI config and locality focused gate recheck:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_gui_config_io.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check gui\config_io.py tests\test_gui_config_io.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy gui\config_io.py tests\test_gui_config_io.py
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_analyze_xic_request_locality.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check scripts\analyze_xic_request_locality.py tests\test_analyze_xic_request_locality.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy scripts\analyze_xic_request_locality.py tests\test_analyze_xic_request_locality.py
```

Observed results: GUI config `1 passed`; locality analyzer `5 passed`; both
ruff checks passed; both focused mypy checks passed for 2 source files. Current
verdict:

- `gui/config_io.py` fieldname scan is already handled by the current dirty
  diff's `seen` set and first-seen extra-field order characterization.
- `scripts/analyze_xic_request_locality.py` still shows scanner hits, but the
  true no-RAW wins already landed: detected-sample filtering avoids empty
  samples, same-scan-window census computes request keys once, and
  near-redundant grouping prunes pair checks with RT-center ordering while
  preserving transitive groups.

Post xlsx-to-targets and validation-migration focused gate recheck:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_xlsx_to_targets.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check scripts\xlsx_to_targets.py tests\test_xlsx_to_targets.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy scripts\xlsx_to_targets.py tests\test_xlsx_to_targets.py
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_validate_migration.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check scripts\validate_migration.py tests\test_validate_migration.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy scripts\validate_migration.py tests\test_validate_migration.py
```

Observed results: `xlsx_to_targets` `3 passed`; `validate_migration`
`12 passed`; both ruff checks passed; both focused mypy checks passed for 2
source files. Current verdict:

- `scripts/xlsx_to_targets.py` already precomputes ISTD match plans and uses the
  shared target CSV writer. The remaining parser loops are the sheet-block and
  row traversal contract.
- `scripts/validate_migration.py` already groups validation rows by target once
  and uses the shared CSV writer for settings updates while preserving BOM,
  field order, extra columns, and append behavior.

Latest owner-backfill request-plan seed-center reuse shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_alignment_owner_backfill.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\owner_backfill_request_plan.py tests\test_alignment_owner_backfill.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\owner_backfill_request_plan.py
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_backfill_scope_probe.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\owner_backfill_request_plan.py tests\test_alignment_owner_backfill.py tests\test_backfill_scope_probe.py
git diff --check -- xic_extractor\alignment\owner_backfill_request_plan.py tests\test_alignment_owner_backfill.py docs\superpowers\notes\2026-06-11-clean-code-optimization-inventory.md
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 180 | rg 'Location: `xic_extractor\\alignment\\owner_backfill_request_plan.py' -A 2
```

Observed results: `26 passed`; ruff passed; source-level mypy passed for 1
source file. The diagnostics consumer check `tests\test_backfill_scope_probe.py`
also passed (`4 passed`), the wider ruff check passed, and `git diff --check`
reported no whitespace errors, only the existing CRLF conversion warning for the
test file. A broader mypy call that included `tests\test_alignment_owner_backfill.py`
still hit existing test typing debt in that test module and its imported
`tests\test_alignment_owner_clustering.py`, so the gate for this package helper
uses source-level mypy plus focused pytest/ruff.

Candidate verdict: true package-level request-planning reuse cleanup.
`build_owner_backfill_request_plan()` now computes `backfill_seed_centers()`
once per feature and reuses that tuple for every requested sample. Request
materialization order is unchanged: features are still visited in input order,
samples still follow `sample_order`, and seed requests still follow
`backfill_seed_centers()` order. The scanner still reports the expected
feature/sample/seed nested loops because those loops materialize the public
logical request plan.

Latest product matrix sample-membership shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_alignment_tsv_writer.py tests\test_alignment_production_decisions.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\product_matrix.py tests\test_alignment_tsv_writer.py tests\test_alignment_production_decisions.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\product_matrix.py
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 180 | rg 'Location: `xic_extractor\\alignment\\product_matrix.py' -A 2
```

Observed results: `60 passed`; ruff passed; mypy passed for 1 source file.
Candidate verdict: true primary-matrix row cleanup with public-surface tests.
`build_product_matrix_rows()` now builds `cluster_sample_stems` once per
cluster, so the sample-value loop uses set membership instead of scanning
`cluster_cells` for every sample column. Matrix row order, identity rows,
`decisions.cell()` usage, accepted area rendering, and TSV schemas are
unchanged. Remaining scanner hits are split-hypothesis assignment/claim loops
and should stay behind matrix identity/value parity tests before further
optimization.

Latest primary-consolidation component traversal shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_alignment_primary_consolidation.py tests\test_alignment_matrix_identity.py::test_family_consolidation_loser_is_audit_only
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\primary_consolidation.py tests\test_alignment_primary_consolidation.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\primary_consolidation.py tests\test_alignment_primary_consolidation.py
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 200 | rg 'Location: `xic_extractor\\alignment\\primary_consolidation.py' -A 2
```

Observed results: `9 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: safe traversal cleanup inside a behavior-sensitive module.
`_connected_components()` now precomputes sorted neighbor tuples once per graph
before BFS, preserving sorted start order, sorted neighbor traversal, and
singleton-component exclusion. The focused test pins those traversal semantics.
The test helper `_feature_by_id()` now uses `getattr` so the focused mypy gate
does not trip over the matrix cluster union type. Remaining scanner hits in
`primary_consolidation.py` are consolidation winner/cell replacement behavior
and should not be rewritten without broader matrix identity/value parity.

Post claim-registry and process-backend focused gate recheck:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_alignment_claim_registry_hot_path.py tests\test_alignment_claim_registry.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\claim_registry.py tests\test_alignment_claim_registry_hot_path.py tests\test_alignment_claim_registry.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\claim_registry.py
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_alignment_process_backend.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\process_backend.py tests\test_alignment_process_backend.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\process_backend.py
```

Observed results: claim registry `16 passed`; process backend `20 passed`;
both ruff checks passed; both source-level mypy checks passed. Current verdict:

- `claim_registry.py` currently has the already-characterized single-candidate
  sample fast path; remaining scanner hits sit inside duplicate-claim grouping
  and winner selection behavior.
- `process_backend.py` currently has the request-plan extraction and payload
  metrics slice; remaining scanner hits are identity-trace sample grouping,
  future/result orchestration, and per-trace conversion loops. These are not
  safe no-RAW cleanups without changing job ordering/error semantics.

Post backfill-scope locality/writer focused gate recheck:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_backfill_scope.py tests\test_backfill_scope_probe.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\backfill_scope.py tests\test_backfill_scope.py tests\test_backfill_scope_probe.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\backfill_scope.py tests\test_backfill_scope.py tests\test_backfill_scope_probe.py
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 220 | rg 'Location: `xic_extractor\\alignment\\backfill_scope.py' -A 2
```

Observed results: `12 passed`; ruff passed; mypy passed for 3 source files.
Scanner still reports `_loose_compatible_neighbor_ids()` /
`_rt_window_neighbors()` around lines 259-262. Current verdict: already
localized enough for this cleanup pass. The code groups by neutral-loss tag,
sorts each tag group by RT once, then scans only backward/forward neighbors
until the RT window is exceeded. Further replacement with a more elaborate
window index would be behavior-sensitive because the production-equivalence
skip path depends on the exact loose-compatibility predicate and first
compatible-neighbor detection.

Latest pre-backfill consolidation sample-stem cache shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_pre_backfill_consolidation.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\pre_backfill_consolidation.py tests\test_pre_backfill_consolidation.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\pre_backfill_consolidation.py tests\test_pre_backfill_consolidation.py
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 220 | rg 'Location: `xic_extractor\\alignment\\pre_backfill_consolidation.py' -A 2
```

Observed results: `6 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: safe greedy-grouping constant-factor cleanup.
`_identity_groups()` now sorts features once, computes owner sample-stem sets
once per feature, and reuses those cached sets for disjointness checks. The new
test pins that sample-stem extraction is one call per feature and keeps the
winner/loser consolidation states in original feature output order. The test
file also now owns its minimal local owner fixture, so this focused mypy gate no
longer imports unrelated owner-clustering test typing debt. Scanner still flags
the group/materialization loop around line 36; that remaining loop is the
actual consolidation output rewrite and should stay behind broader matrix
identity/value parity before algorithmic changes.

Owner-matrix scanner follow-up:

```powershell
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 260 | rg 'Location: `xic_extractor\\alignment\\owner_matrix.py' -A 2
```

Current verdict: no edit. The remaining `owner_matrix.py:39` hit is the public
feature by sample matrix materialization loop. The implementation already
pre-indexes rescued cells by feature/sample and owners by sample per feature;
the loop exists to emit one public matrix cell per feature/sample combination,
so reducing it would require a product-level sparse-matrix contract change.

Latest single-dR discovery candidate loader path grouping shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_single_dr_production_gate_decision_report.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\single_dr_gate_decision_loaders.py tests\test_single_dr_production_gate_decision_report.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\single_dr_gate_decision_loaders.py
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 320 | rg 'Location: `tools\\diagnostics\\single_dr_gate_decision_loaders.py' -A 2
```

Observed results: `20 passed`; ruff passed; source-level mypy passed for
`tools\diagnostics\single_dr_gate_decision_loaders.py`. A broader mypy call that
included `tests\test_single_dr_production_gate_decision_report.py` still hit
existing test-helper typing debt around `_candidate()` row types and dynamic
`AlignedCell(**dict)` fixtures; the source gate is clean.

Candidate verdict: true diagnostics loader locality cleanup.
`load_discovery_candidates()` now groups batch-index samples by resolved
candidate CSV path, reads each candidate table once, and expands each candidate
row once per relevant sample. This preserves the compatibility behavior where a
candidate row without `sample_stem` is projected onto every index sample that
references that table, while a candidate row with an explicit `sample_stem`
stays attached to that sample only. The focused test now covers both contracts.
Scanner still reports the remaining candidate-row/sample expansion loop, which
is the required materialization of the public lookup mapping rather than
duplicate table I/O.

Latest instrument-QC sequence manifest method-detail cleanup:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_instrument_qc_sequence_manifest.py tests\test_instrument_qc_sequence_manifest_cli.py tests\test_instrument_qc_method_doc_cli.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\instrument_qc\sequence_manifest.py tests\test_instrument_qc_sequence_manifest.py tests\test_instrument_qc_sequence_manifest_cli.py tests\test_instrument_qc_method_doc_cli.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\instrument_qc\sequence_manifest.py tests\test_instrument_qc_sequence_manifest.py tests\test_instrument_qc_sequence_manifest_cli.py tests\test_instrument_qc_method_doc_cli.py
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 420 | rg 'Location: `xic_extractor\\instrument_qc\\sequence_manifest.py' -A 2
```

Observed results: `19 passed`; ruff passed; mypy passed for 4 source files.
Candidate verdict: small parsing cleanup with no manifest contract change.
`_method_activation_map()` now delegates method-detail text collection to
`_clean_table_cells()`, so each table cell is normalized once before joining.
The manifest row ordering, duplicate-doc matching, raw-only rows, activation
classification, writer schemas, and CLI contracts are unchanged. Scanner still
reports table traversal at lines 91/328/376; those are necessary DOCX table
parsing and method-detail flattening loops, not repeated lookup work that can
be removed without changing parsing behavior.

Latest artificial-adduct annotation locality shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_alignment_adduct_annotation.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\adduct_annotation.py tests\test_alignment_adduct_annotation.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\adduct_annotation.py tests\test_alignment_adduct_annotation.py
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 220 | rg 'Location: `xic_extractor\\alignment\\adduct_annotation.py' -A 2
```

Observed results: `4 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: already-converged package-level locality cleanup.
`match_artificial_adduct_pairs()` now snapshots family identity/mz/RT once,
indexes adducts once, uses RT-window candidate pairs instead of scanning every
family pair, and uses delta-sorted adduct bisection before restoring adduct
input order. The focused tests cover iterable adduct input and input-order
preservation. Scanner still reports lines 86/153/161; those are the remaining
public pair/adduct materialization loop, bounded RT-window scan, and required
candidate input-order sort rather than duplicate full-list scans.

Latest drift-evidence lookup/cache shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_alignment_drift_evidence.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\drift_evidence.py tests\test_alignment_drift_evidence.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\drift_evidence.py tests\test_alignment_drift_evidence.py
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 240 | rg 'Location: `xic_extractor\\alignment\\drift_evidence.py' -A 2
```

Observed results: `6 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: safe lookup/cache cleanup with preserved lazy conflict
behavior. `DriftEvidenceLookup` now caches median drift deltas and injection
orders by sample, so repeated `sample_delta_min()` / `injection_order()` calls
do not rescan every point. `read_targeted_istd_drift_evidence()` also computes
sorted ISTD labels once and reuses that order for trend IDs and point emission.
The focused tests cover median lookup, missing samples, lazy conflicting-order
errors, opaque trend IDs, sample ordering, and sorted label mapping. Scanner now
only reports line 89, the per-label injection-order sample traversal needed for
rolling median evidence construction.

Latest ownership resolved-group ordering shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_alignment_ownership.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\ownership.py tests\test_alignment_ownership.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\ownership.py tests\test_alignment_ownership.py
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 300 | rg 'Location: `xic_extractor\\alignment\\ownership.py' -A 2
```

Observed results: `15 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: safe owner-group constant-factor cleanup without RAW
behavior changes. `_candidate_components()` already returns each component in
the sorted `pending` order, so `_owners_for_sample()` now reuses that order for
ambiguous candidate IDs and `_primary_and_supporting()` instead of sorting the
same group again. A reversed-input characterization confirms the owner primary
still follows `_resolved_sort_key`, not input order. The scanner no longer
reports the ambiguous-path sort; remaining `ownership.py` hits are sample
ordering, batched trace extraction/materialization, component graph traversal,
and ambiguity relation checks that require broader owner parity before further
algorithm changes.

Latest RT-mode evidence family-row index shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_shared_peak_identity_rt_mode_evidence.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\shared_peak_identity_explanation\rt_mode_evidence.py tests\test_shared_peak_identity_rt_mode_evidence.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\shared_peak_identity_explanation\rt_mode_evidence.py tests\test_shared_peak_identity_rt_mode_evidence.py
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 420 | rg 'Location: `xic_extractor\\alignment\\shared_peak_identity_explanation\\rt_mode_evidence.py' -A 2
```

Observed results: `9 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: safe diagnostics row-index cleanup.
`build_rt_mode_evidence_rows()` now builds assignment and summary rows by family
once, preserving original row order and the existing blank-family fallback
semantics. Family contexts and assignment lookup now reuse those indexes instead
of repeatedly filtering the full assignment/summary tables for every family.
The new characterization test keeps explicit `mode_summary_tsv` overrides
scoped to their family. Remaining scanner hits around lines 115/173/198/279/367
are deterministic oracle/merge ordering, RAW overlay clustering, typical-gap
calculation, and mode/tag evidence traversal rather than duplicated full-table
family filtering.

Latest QC MS1 pattern reference comparison-reuse shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_shared_peak_identity_qc_ms1_pattern_reference.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\shared_peak_identity_explanation\qc_ms1_pattern_reference.py tests\test_shared_peak_identity_qc_ms1_pattern_reference.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\shared_peak_identity_explanation\qc_ms1_pattern_reference.py tests\test_shared_peak_identity_qc_ms1_pattern_reference.py
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 420 | rg 'Location: `xic_extractor\\alignment\\shared_peak_identity_explanation\\qc_ms1_pattern_reference.py' -A 2
```

Observed results: `7 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: safe diagnostics comparison-reuse cleanup.
`_qc_comparisons()` now feeds both the nearest-QC local decision and QC
consensus rows, so `_row_for_key()` no longer runs a separate
`_nearest_qc_trace()` scan or recomputes apex/shape metrics for the same
candidate references. The nearest-reference ordering is unchanged: usable local
signal with apex first, family-centered rank, injection-order delta, then sample
stem. Existing status, reason, apex-delta, shape-similarity, and consensus
output fields are preserved by the focused tests. The remaining scanner hit at
line 156 is JSON trace row materialization while loading diagnostics input, not
duplicate QC reference scanning.

Latest identity-control manifest header membership shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\alignment\identity_coherence\test_controls_manifest.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\identity_coherence\control_manifest.py tests\alignment\identity_coherence\test_controls_manifest.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\identity_coherence\control_manifest.py tests\alignment\identity_coherence\test_controls_manifest.py
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 500 | rg 'Location: `xic_extractor\\alignment\\identity_coherence\\control_manifest.py' -A 2
```

Observed results: `11 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: safe manifest parser membership cleanup.
`_validate_required_fields()` now tracks duplicate headers with both an ordered
`duplicates` list and a `duplicate_set`, then builds `fieldname_set` once for
required-header lookup. Duplicate-header and missing-required-header message
ordering remains contract-preserving; the new test covers missing required
fields in `REQUIRED_MANIFEST_FIELDS` order. The remaining scanner hit at line
77 is a conservative false positive over set membership, not a list membership
or repeated sequence scan.

Follow-up identity-control model text-field membership cleanup:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\alignment\identity_coherence\test_controls_manifest.py tests\alignment\identity_coherence\test_schema_contract.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\identity_coherence\control_models.py xic_extractor\alignment\identity_coherence\control_manifest.py tests\alignment\identity_coherence\test_controls_manifest.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\identity_coherence\control_models.py xic_extractor\alignment\identity_coherence\control_manifest.py tests\alignment\identity_coherence\test_controls_manifest.py
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 500 | rg 'Location: `xic_extractor\\alignment\\identity_coherence\\control_models.py' -A 2
```

Observed results: `92 passed`; ruff passed; mypy passed for 3 source files.
Candidate verdict: safe dataclass normalization membership cleanup.
`IdentityControlManifestEntry.__post_init__()` now uses a precomputed
`_REQUIRED_TEXT_FIELD_SET` for required text-field membership while preserving
the `_TEXT_FIELDS` iteration order. The remaining scanner hit at line 136 is a
conservative false positive over `frozenset` membership.

Identity coherence source-mapping scanner classification:

```powershell
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 500 | rg 'Location: `xic_extractor\\alignment\\identity_coherence_source_mapping.py' -A 2
```

Candidate verdict: no code change. The line-51 sort is a single deterministic
owner ordering pass, not sorting inside a repeated loop. The line-56 membership
check is against `assignment_by_candidate_id`, a dict built once from ownership
assignments. Treat both hits as scanner false positives unless future profiling
shows this source-mapping adapter itself is hot.

Latest identity-decoy default tag lookup shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\alignment\identity_coherence\test_controls_evaluation.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\identity_coherence\decoy_controls.py tests\alignment\identity_coherence\test_controls_evaluation.py tests\alignment\identity_coherence\output_fixtures.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\identity_coherence\decoy_controls.py tests\alignment\identity_coherence\test_controls_evaluation.py tests\alignment\identity_coherence\output_fixtures.py
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 500 | rg 'Location: `xic_extractor\\alignment\\identity_coherence\\decoy_controls.py' -A 2
```

Observed results: `35 passed`; ruff passed after import ordering cleanup; mypy
passed for 3 source files. Candidate verdict: safe default-tag membership
cleanup. `_default_decoy_tags()` now builds `source_tag_set` once before
checking the base unmatched tag and numeric suffix collisions. The new
characterization test covers existing `identity_decoy_unmatched_tag` and
`identity_decoy_unmatched_tag_2` collisions and preserves the generated
`identity_decoy_unmatched_tag_3` behavior. The remaining scanner hit at line 240
is a conservative false positive over set membership.

Identity coherence request-builder scanner classification:

```powershell
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 500 | rg 'Location: `xic_extractor\\alignment\\identity_coherence\\request_builder.py' -A 2
```

Candidate verdict: no code change. `_completeness_status()` already converts
`missing_flags` to a set before walking `_MISSING_STATUS_ORDER`, so the line-228
scanner hit is a conservative false positive over set membership.

Legacy alignment IO scanner classification:

```powershell
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 500 | rg 'Location: `xic_extractor\\alignment\\legacy_io.py' -A 2
```

Candidate verdict: no code change. The reported membership checks are already
against `review_by_id`, `seen_matrix_ids`, or `seen_feature_ids`, all built as
dict/set structures. Treat the current line-59/73/328 hits as scanner false
positives unless a future validation workload shows legacy IO itself is hot.

RT normalization scanner classification:

```powershell
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 500 | rg 'Location: `xic_extractor\\alignment\\rt_normalization.py' -A 2
```

Candidate verdict: no code change. `fit_sample_rt_models()` sorts
`points_by_sample.items()` once before iterating samples; it is not sorting
inside a repeated inner loop. The residual membership check uses a precomputed
`used_labels` set. Treat the current line-257/275/278 hits as scanner false
positives unless RT normalization profiling identifies this diagnostic path as
hot.

Latest production-candidate tier2 sidecar fieldname-set shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_production_candidate_gate.py tests\test_tier2_raw_trace_producer.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\production_candidate_gate.py tests\test_production_candidate_gate.py tests\test_tier2_raw_trace_producer.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\production_candidate_gate.py tests\test_production_candidate_gate.py tests\test_tier2_raw_trace_producer.py
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 500 | rg 'Location: `xic_extractor\\alignment\\production_candidate_gate.py' -A 2
```

Observed results: `61 passed`; ruff passed; mypy passed for 3 source files.
Candidate verdict: safe tier2 sidecar parser membership cleanup.
`_read_tsv_versioned_tier2_sidecar()` now builds `fieldname_set` once and uses
it for both base v0 and criteria-version-specific required-column checks while
preserving required-column order in error messages. The test helper kwargs cast
only fixes static typing for the existing parametrized sidecar override test.
Remaining scanner hits are conservative false positives: line 225 is a single
candidate-subset signature sort, line 258 is dict membership, and line 784 is
set membership.

Configuration parser/settings/targets scanner classification:

```powershell
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 700 | rg 'Location: `xic_extractor\\configuration\\(parsing|settings|targets).py' -A 2
```

Candidate verdict: no code change. `configuration/parsing.py` already builds
`available = set(fieldnames or [])` before required-column membership checks.
`configuration/settings.py` checks membership against the `migrated` dict.
`configuration/targets.py` uses a `seen` set for duplicate target ids and
`frozenset` constants for allowed enum values. Treat these current scanner hits
as conservative false positives.

Latest alignment validation compare shared-sample and pair-indexing shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_alignment_validation_compare.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\validation_compare.py tests\test_alignment_validation_compare.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\validation_compare.py tests\test_alignment_validation_compare.py
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 700 | rg 'Location: `xic_extractor\\alignment\\validation_compare.py' -A 2
```

Observed results: `11 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: safe shared-sample membership cleanup plus ppm-window pair
enumeration indexing.
`match_legacy_source()` now builds `legacy_sample_set` once before filtering the
selected sample scope, matching the already-optimized pattern in
`summarize_legacy_source()` while preserving scope order and output schema.
`_eligible_pairs()` now sorts legacy features by m/z once and uses bisect bounds
to scan only the ppm window for each XIC feature, then applies the original
ppm/RT/distance checks. Private `xic_index` / `legacy_index` fields make the
old nested-loop stable tie order explicit at the end of the match sort key.
Remaining scanner hits are conservative residuals: line 85 checks
`used_xic` / `used_legacy` sets, and line 312 is a bounded m/z-window loop, not
the previous full XIC x legacy scan.

Latest production decisions row-local lookup cleanup shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_alignment_production_decisions.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\production_decisions.py tests\test_alignment_production_decisions.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\alignment\production_decisions.py tests\test_alignment_production_decisions.py
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 700 | rg 'Location: `xic_extractor\\alignment\\production_decisions.py' -A 2
```

Observed results: `22 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: safe row-local decision reuse cleanup.
`build_production_decisions()` now appends each freshly computed
`ProductionCellDecision` into the current row's decision list while also writing
the public `cell_decisions` lookup map. This avoids rebuilding the same row
decision tuple through a second dict lookup pass, while preserving cluster/cell
ordering and the `ProductionDecisionSet` public shape. The companion test helper
typing cleanup only narrows `_feature()`, positive area handling, and dynamic
backfill kwargs so the focused mypy shard can verify the source plus test file.
The remaining scanner hit at line 98 is the necessary cluster-to-cell
materialization loop, not the removed redundant lookup pass.

Latest workbook comparer sheet membership shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_workbook_compare.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check scripts\compare_workbooks.py tests\test_workbook_compare.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy scripts\compare_workbooks.py tests\test_workbook_compare.py
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 700 | rg 'Location: `scripts\\compare_workbooks.py' -A 2
```

Observed results: `8 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: safe workbook sheet membership cleanup.
`compare_workbooks()` now builds left/right sheet-name sets once and passes the
sets into `_sheets_to_compare()`, preserving the fixed comparison order while
avoiding repeated list membership checks in the sheet loop. Remaining scanner
hits at lines 54/57 are conservative false positives over set membership; line
125 is the necessary row/column workbook diff scan.

Latest family MS1 backfill review TSV field set shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_family_ms1_backfill_review_report.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\family_ms1_backfill_review_io.py tests\test_family_ms1_backfill_review_report.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\family_ms1_backfill_review_io.py tests\test_family_ms1_backfill_review_report.py
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 700 | rg 'Location: `tools\\diagnostics\\family_ms1_backfill_review_io.py' -A 2
```

Observed results: `4 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: safe TSV required-column membership cleanup.
`_read_tsv()` now builds `field_set` once before checking required columns,
preserving required-column error ordering while avoiding repeated fieldname
sequence scans. The remaining scanner hit at line 21 is the deterministic
per-directory overlay trace JSON sort, not a required-column membership issue.

Latest targeted peak reliability workbook sample marker shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_targeted_peak_reliability_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\targeted_peak_reliability_loaders.py tests\test_targeted_peak_reliability_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\targeted_peak_reliability_loaders.py tests\test_targeted_peak_reliability_audit.py
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 900 | rg 'Location: `tools\\diagnostics\\targeted_peak_reliability_loaders.py' -A 2
```

Observed results: `21 passed`; ruff passed; mypy passed for 2 source files;
scanner returned no remaining findings for this file.
Candidate verdict: safe workbook sample-marker membership cleanup.
`_read_xic_results()` now replaces `raw_sample not in (None, "")` with explicit
`raw_sample is not None and raw_sample != ""`, preserving carry-forward sample
semantics while removing the scanner-reported per-row tuple membership pattern.

Target-pair expected-diff approval registry scanner classification:

```powershell
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 900 | rg 'Location: `tools\\diagnostics\\build_target_pair_expected_diff_approval_registry.py' -A 2
```

Candidate verdict: no code change. `_unique_review_rows_by_key()` checks
duplicate `(sample_name, target_label)` keys against `out`, a dict built in the
same pass. The line-127 scanner hit is a conservative false positive; changing
this approval-registry validation path would not improve architecture or
runtime behavior.

Latest ISTD false-missing fixture blank-check shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_istd_false_missing_fixture.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\build_istd_false_missing_fixture.py tests\test_istd_false_missing_fixture.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\build_istd_false_missing_fixture.py tests\test_istd_false_missing_fixture.py
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 900 | rg 'Location: `tools\\diagnostics\\build_istd_false_missing_fixture.py' -A 2
```

Observed results: `6 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: safe fixture-loader blank-check cleanup.
The old-matrix missing-value scan and targeted workbook sample/target
carry-forward logic now use explicit `is None` / empty-string checks instead of
tuple membership in row loops. Remaining scanner hits are conservative: line 51
iterates a fixed two-entry ISTD target map over missing samples, line 116 scans
row columns once, and lines 113/123 are dict membership checks.

Latest RT normalization anchor loader sample marker shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_rt_normalization_anchors.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\rt_normalization_anchor_loaders.py tests\test_rt_normalization_anchors.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\rt_normalization_anchor_loaders.py tests\test_rt_normalization_anchors.py
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 1000 | rg 'Location: `tools\\diagnostics\\rt_normalization_anchor_loaders.py' -A 2
```

Observed results: `14 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: safe workbook sample-marker cleanup.
`_read_anchor_points()` now replaces `raw_sample not in (None, "")` with
explicit `raw_sample is not None and raw_sample != ""`, preserving sample
carry-forward semantics. The remaining line-105 scanner hit checks `label not
in anchors`, where `anchors` is a mapping/dict, so it is a conservative false
positive.

Latest injection order CSV blank-check shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_injection_rolling.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\injection_rolling.py tests\test_injection_rolling.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\injection_rolling.py tests\test_injection_rolling.py
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 1000 | rg 'Location: `xic_extractor\\injection_rolling.py' -A 2
```

Observed results: `15 passed`; ruff passed; mypy passed for 2 source files;
scanner returned no remaining findings for this file.
Candidate verdict: safe shared injection-order loader cleanup.
`_read_csv()` now replaces `order in (None, "")` with explicit `order is None`
or empty-string checks, preserving the CSV skip semantics while removing the
scanner-reported tuple membership pattern from the row loop.

Latest instrument QC pipeline activation-method set shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_instrument_qc_pipeline.py tests\test_instrument_qc_sequence_manifest.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\instrument_qc\pipeline_inputs.py tests\test_instrument_qc_pipeline.py tests\test_instrument_qc_sequence_manifest.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\instrument_qc\pipeline_inputs.py tests\test_instrument_qc_pipeline.py tests\test_instrument_qc_sequence_manifest.py
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 1000 | rg 'Location: `xic_extractor\\instrument_qc\\pipeline_inputs.py' -A 2
```

Observed results: `21 passed`; ruff passed; mypy passed for 3 source files.
Candidate verdict: safe instrument-QC manifest membership cleanup.
`read_sequence_manifest_context()` now uses `_KNOWN_ACTIVATION_METHODS`, a
module-level `frozenset`, instead of rebuilding the activation-method set in the
row loop. Remaining scanner hits are conservative false positives: line 33 is
frozenset membership and line 56 is membership against the `seen_stems` set used
for duplicate RAW-stem detection.

Latest model-selection expected-diff approval registry header shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_model_selection_approval_registry.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\peak_detection\model_selection_approval_registry.py tests\test_model_selection_approval_registry.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\peak_detection\model_selection_approval_registry.py tests\test_model_selection_approval_registry.py
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 1000 | rg 'Location: `xic_extractor\\peak_detection\\model_selection_approval_registry.py' -A 2
```

Observed results: `4 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: safe approval-registry header membership cleanup.
`_validate_headers()` now builds `fieldname_set` once before required-column
checks, preserving missing-column order while avoiding repeated header sequence
membership checks. The remaining line-74 scanner hit is duplicate
`stable_row_id` detection against the `approvals` dict, so it is a conservative
false positive.

Latest alignment near-duplicate diagnostic loader shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_alignment_near_duplicate_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check scripts\audit_alignment_near_duplicates.py tests\test_alignment_near_duplicate_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy scripts\audit_alignment_near_duplicates.py tests\test_alignment_near_duplicate_audit.py
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 1000 | rg 'Location: `scripts\\audit_alignment_near_duplicates.py' -A 3 -B 1
```

Observed results: `2 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: safe diagnostic TSV loader cleanup.
`_load_rows()` now uses module-level `_MATRIX_METADATA_COLUMNS` instead of
rebuilding the metadata-column set per review row, and replaces tuple blank
membership with explicit `is not None` / empty-string checks. A focused loader
characterization test now locks the diagnostic input contract that metadata
columns are excluded while zero-valued sample cells still count as present. The
remaining scanner hits are conservative false positives: line 86 is membership
against a module-level `frozenset`, and line 111 checks a fixed two-name
compatibility tuple in `_first_present()`.

Latest untargeted guardrail targeted-ISTD count shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_untargeted_alignment_guardrails.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\untargeted_alignment_guardrail_targets.py tests\test_untargeted_alignment_guardrails.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\untargeted_alignment_guardrail_targets.py tests\test_untargeted_alignment_guardrails.py
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 1000 | rg 'Location: `tools\\diagnostics\\untargeted_alignment_guardrail_targets.py' -A 3 -B 1
```

Observed results: `32 passed`; ruff passed; mypy passed for 2 source files;
scanner returned no remaining findings for this file.
Candidate verdict: safe diagnostic guardrail count caching.
`targeted_istd_benchmark_guardrail_rows()` now computes active failure count
once and converts benchmark failure modes into a single `Counter`, avoiding
repeated full scans over the same targeted-ISTD summaries while preserving the
existing overall/active/miss/split/false-positive tag output rows. The old
`_count_failure_mode()` helper remains as a thin compatibility wrapper.

Latest ASLS synthetic fixture-class membership shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_asls_truth_validation_synthetic.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\asls_truth_validation_synthetic.py tests\test_asls_truth_validation_synthetic.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\asls_truth_validation_synthetic.py tests\test_asls_truth_validation_synthetic.py
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 1000 | rg 'Location: `tools\\diagnostics\\asls_truth_validation_synthetic.py' -A 3 -B 1
```

Observed results: `12 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: safe synthetic gate fixture-class membership cleanup.
`classify_tier_b_blockers()` now uses module-level
`_RELATIVE_ERROR_IMPROVEMENT_CLASSES` instead of rebuilding the three-item
fixture-class set inside the heldout-class loop. The remaining scanner hit is a
conservative false positive: membership is now against a module-level
`frozenset`, and rewriting it further would only reduce readability.

Latest instrument-QC manual review batching shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_instrument_qc_workbook.py tests\test_instrument_qc_hcd.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\instrument_qc\workbook_manual_review.py tests\test_instrument_qc_workbook.py tests\test_instrument_qc_hcd.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\instrument_qc\workbook_manual_review.py tests\test_instrument_qc_workbook.py tests\test_instrument_qc_hcd.py
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 1000 | rg 'Location: `xic_extractor\\instrument_qc\\workbook_manual_review.py' -A 3 -B 1
```

Observed results: `27 passed`; ruff passed; mypy passed for 3 source files.
Candidate verdict: safe manual-review queue batching/index cleanup.
`manual_review_rows()` now builds an isotope-support index and an
outside-window MS2 support key set once before rendering the manual review
queue. Product-miss and target-RT-window skip checks now use indexed lookups
instead of rescanning all HCD rows for each queue candidate, and Mix STDs
outside-window suppression now uses a key set. A test helper annotation was
added so the focused mypy command remains clean. Remaining scanner hits are
conservative false positives against tuple review flags and module-level
`frozenset` status membership.

Latest family MS1 overlay rendering status shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_family_ms1_overlay_rendering.py tests\test_family_ms1_overlay_plot.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\family_ms1_overlay_rendering.py tests\test_family_ms1_overlay_rendering.py tests\test_family_ms1_overlay_plot.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\family_ms1_overlay_rendering.py tests\test_family_ms1_overlay_rendering.py tests\test_family_ms1_overlay_plot.py
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 1200 | rg 'Location: `tools\\diagnostics\\family_ms1_overlay_rendering.py' -A 3 -B 1
```

Observed results: `27 passed`; ruff passed; mypy passed for 3 source files.
Candidate verdict: safe renderer status-membership cleanup.
`_selected_peak_focus_rows()`, `_plot_area_distribution()`, and
`_plot_shape_similarity()` now share module-level `_SELECTED_PEAK_STATUSES`
instead of repeating the selected-peak status literal. Remaining scanner hits
are conservative false positives: one tracks `labels_seen`, a local set used to
deduplicate legend labels, and the other two are membership against the
module-level `frozenset`.

Latest RT normalization anchor analysis modelled-row shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_rt_normalization_anchors.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\rt_normalization_anchor_analysis.py tests\test_rt_normalization_anchors.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\rt_normalization_anchor_analysis.py tests\test_rt_normalization_anchors.py
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 1200 | rg 'Location: `tools\\diagnostics\\rt_normalization_anchor_analysis.py' -A 3 -B 1
```

Observed results: `14 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: safe RT-normalization diagnostic analysis cleanup.
`_summarize_families()` now names the sorted family-id boundary and materializes
`modelled_cells` once for normalized RT and anchor-scope computation.
`_leave_one_anchor_out()` now materializes `modelled_held_points` before error
calculation. Remaining scanner hits are membership against the `models`
mapping, not list scans; the earlier sort-in-loop scanner hit is gone.

Targeted ISTD benchmark scanner classification:

```powershell
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 1200 | rg 'Location: `tools\\diagnostics\\targeted_istd_benchmark.py|Location: `tools\\diagnostics\\targeted_istd_benchmark_stats.py' -A 3 -B 1
```

Candidate verdict: no code change. `AlignmentMatrixData.sample_stems` is already
a `frozenset`, so `point.sample_stem in matrix.sample_stems` is not a list scan.
`_ranks()` is the standard sorted tie-ranking pass used by Spearman
correlation; replacing the tie scan would not improve architecture and risks
changing ranking semantics.

Latest targeted peak reliability known-exception parser shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_targeted_peak_reliability_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools\diagnostics\targeted_peak_reliability_audit.py tests\test_targeted_peak_reliability_audit.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools\diagnostics\targeted_peak_reliability_audit.py tests\test_targeted_peak_reliability_audit.py
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 1200 | rg 'Location: `tools\\diagnostics\\targeted_peak_reliability_audit.py' -A 3 -B 1
```

Observed results: `21 passed`; ruff passed; mypy passed for 2 source files;
scanner returned no remaining findings for this file.
Candidate verdict: safe CLI parser cleanup. `_parse_known_exceptions()` now
uses `partition(":")` instead of a membership check followed by `split(":", 1)`,
preserving the `TARGET:FAILURE_MODE` validation behavior.

Latest paired-area ratio projection workset shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_paired_area_ratio_projection.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\extraction\paired_area_ratio_projection.py tests\test_paired_area_ratio_projection.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\extraction\paired_area_ratio_projection.py tests\test_paired_area_ratio_projection.py
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 1200 | rg 'Location: `xic_extractor\\extraction\\paired_area_ratio_projection.py' -A 3 -B 1
```

Observed results: `7 passed`; ruff passed; mypy passed for 2 source files.
Candidate verdict: safe extraction reference-workset cleanup.
`paired_area_ratio_references()` now precomputes projection-eligible targets
once via `_paired_area_ratio_projection_targets()`, avoiding repeated
`is_istd` / missing-pair checks for every file result. Focused tests keep the
run-level paired-area support behavior locked. The remaining scanner hits are
the necessary file/result projection and file/eligible-target reference loops.

Latest instrument-QC matrix preview / decision report membership shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests\test_instrument_qc_matrix_calibration_preview.py tests\test_instrument_qc_decision_report.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\instrument_qc\calibration_matrix_preview.py xic_extractor\instrument_qc\decision_report.py tests\test_instrument_qc_matrix_calibration_preview.py tests\test_instrument_qc_decision_report.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\instrument_qc\calibration_matrix_preview.py xic_extractor\instrument_qc\decision_report.py tests\test_instrument_qc_matrix_calibration_preview.py tests\test_instrument_qc_decision_report.py
python C:\Users\user\.codex\skills\complexity-optimizer\scripts\analyze_complexity.py C:\Users\user\Desktop\XIC_Extractor --format markdown --exclude .venv --exclude .git --exclude output --exclude .worktrees --exclude htmlcov --exclude build --exclude dist --exclude .uv-cache --max-findings 1200 | rg 'Location: `xic_extractor\\instrument_qc\\calibration_matrix_preview.py|Location: `xic_extractor\\instrument_qc\\decision_report.py' -A 3 -B 1
```

Observed results: `11 passed`; ruff passed; mypy passed for 4 source files.
Candidate verdict: safe instrument-QC report/preview cleanup.
`build_rt_preview_rows()` now uses module-level `_MEASURED_CELL_STATUSES` for
measured cell gating. `_has_flag()` now scans split flags with `any()` instead
of building a set for a single lookup per row. The remaining matrix-preview
scanner hit is a conservative false positive against the module-level
`frozenset`; `decision_report.py` has no remaining scanner findings.
