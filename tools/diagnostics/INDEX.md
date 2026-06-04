# tools/diagnostics/ — Diagnostic Tool Index

**Last refreshed:** 2026-06-03
**Total entry-points:** 52
**Total files (incl. helpers):** 134 Python files under `tools/diagnostics/`
**Governing spec:** `docs/superpowers/specs/2026-05-26-diagnostic-tool-lifecycle-spec.md`
**Count method:** top-level `### *.py` entry headings for entry-points;
top-level `tools/diagnostics/*.py` files for total files.

---

> **For agents and developers opening a new session:** Before creating a new
> diagnostic tool in `tools/diagnostics/`, scan this index first. Most needs
> are already covered by an existing tool or its topic group. If your need
> is genuinely new, list in your PR description which existing entries you
> considered and why they are inadequate. This avoids the "agent A and
> agent B independently solve the same problem with twin tools" failure
> mode that the 2026-05-26 audit documented.
>
> This index is maintained as part of every PR that adds, removes, or
> renames a diagnostic entry-point. The file is grouped by **purpose**, not
> alphabetically — open the table of contents below to navigate.

## Table of Contents

1. [Phase Gates (P1/P2/P2b/P2c/P7)](#phase-gates-p1p2p2bp2cp7) — 7 tools
2. [Evidence Consistency](#evidence-consistency) — 8 tools
3. [Alignment Diagnostics](#alignment-diagnostics) — 6 tools
4. [Backfill Reviews](#backfill-reviews) — 7 tools
5. [Peak / Candidate Audits](#peak--candidate-audits) — 5 tools
6. [Targeted Benchmarks & Reviews](#targeted-benchmarks--reviews) — 7 tools
7. [Instrument QC](#instrument-qc) — 6 tools
8. [Family / Overlay Visualization](#family--overlay-visualization) — 3 tools
9. [Area / Region Audits](#area--region-audits) — 2 tools
10. [One-off Fixtures](#one-off-fixtures) — 1 tool

---

## Phase Gates (P1/P2/P2b/P2c/P7)

Pipeline-tier gates that compare candidate configurations against current
production, or summarize cost/parity for production decisions. These are
the strongest **promotion candidates** to `xic_extractor/diagnostics/gates/`
per the lifecycle spec.

### `p1_resolver_default_gate.py`

**Purpose**: Compare local_minimum and region_first_safe_merge targeted 8RAW ISTD area RSD and RT shifts for the P1 default-switch gate.
**Topic group**: `p1_resolver_default_gate.py` (single-file)
**Originating spec**: `2026-05-24-peak-pipeline-resolver-default-switch-spec.md`
**Recent doc**: `plans/2026-05-24-p1-resolver-default-real-data-validation.md`

---

### `p2_asls_shadow_gate.py`

**Purpose**: Gate P2 AsLS baseline area against historical linear-edge integration audit rows for targeted ISTD benchmark selections; supports both legacy AsLS-shadow and promoted AsLS schemas.
**Topic group**: `p2_asls_shadow_gate.py`
**Originating spec**: `2026-05-24-peak-pipeline-area-baseline-asls-spec.md`
**Recent doc**: `plans/2026-05-25-p2-asls-baseline-shadow-implementation.md`, `plans/2026-05-26-p2b-asls-production-promotion-plan.md`

---

### `p2_baseline_truth_audit.py`

**Purpose**: Build a diagnostic-only baseline truth audit for P2/P2b AsLS gate ISTD families; compares historical linear-edge rollback against promoted AsLS when legacy evidence is available.
**Topic group**: `p2_baseline_truth_audit.py`
**Originating spec**: `2026-05-24-peak-pipeline-area-baseline-asls-spec.md` (shared with shadow gate)
**Recent doc**: `plans/2026-05-25-p2-baseline-truth-audit-implementation.md`, `plans/2026-05-26-p2b-asls-production-promotion-plan.md`

---

### `p2b_asls_promotion_gate.py`

**Purpose**: Run the revised P2b AsLS promotion gate, including optional evidence-spine and target RT trend support for large RT-delta interpretation.
**Topic group**: `p2b_asls_promotion_gate.py`
**Originating spec**: `2026-05-24-peak-pipeline-area-baseline-asls-promotion-spec.md`
**Recent doc**: `plans/2026-05-25-p2b-revised-asls-promotion-gate-implementation.md`, `plans/2026-05-25-p2d-rt-boundary-first-p2b-gate-implementation.md`, `plans/2026-05-26-p2b-asls-production-promotion-plan.md`

---

### `asls_truth_validation.py`

**Purpose**: Run the P2c AsLS truth-validation gate with Tier A selected-family guard, locked synthetic Tier B1/B2 benchmark, optional Tier C evidence, methodology waiver documentation, retirement prerequisite manifest, and deletion-safe exit codes.
**Topic group**: `asls_truth_validation.py` + `_models`, `_manifests`, `_synthetic`, `_inputs`, `_analysis` (6 files)
**Originating spec/plan**: `specs/2026-05-26-peak-pipeline-asls-truth-validation-spec.md`, `plans/2026-05-27-p2c-tier-b-b1-b2-redesign-plan.md`
**Current gate note**: Exit `0` was the true linear-edge retirement authority consumed by the 2026-06-01 Phase 6b/Phase 7 closeout. B1 relevance fixtures are the only synthetic layer that can drive `decision_target=c1b-plan`; B2 stress evidence is reported for retirement/Tier C follow-up and must not by itself create a C1b no-go. v1 fixture outputs are non-authoritative under the B1/B2 contract and should be treated as `LEGACY_V1_NON_AUTHORITATIVE` / `INCONCLUSIVE_FIXTURE_SCOPE_MISMATCH`. After Phase 7, any linear-edge references here are historical comparison evidence, not maintained production selector support.

---

### `p7_alignment_parity.py`

**Purpose**: Run P7 alignment parity checks.
**Topic group**: `p7_alignment_parity.py`
**Originating spec/plan**: `plans/2026-05-25-evidence-chain-cost-control-implementation-plan.md`, `plans/2026-05-26-p7-stabilization-implementation-plan.md`
**Note**: No standalone spec; lives under the P7 evidence-chain cost-control plan family.

---

### `p7_evidence_cost_summary.py`

**Purpose**: Summarize P7 evidence cost savings.
**Topic group**: `p7_evidence_cost_summary.py`
**Originating spec/plan**: `plans/2026-05-25-evidence-chain-cost-control-implementation-plan.md`, `plans/2026-05-26-p7-stabilization-implementation-plan.md`

---

## Evidence Consistency

Compare evidence rows produced by parallel pipelines (targeted vs untargeted,
spine vs cell) and shared-identity sidecars. The tools below share low-level
diagnostic IO helpers where their schemas permit it, but keep separate row
models because their output schemas are intentionally different; see
`2026-05-26-diagnostic-lifecycle-audit-note.md` Cluster 1.

### `evidence_spine_consistency.py`

**Purpose**: Compare targeted candidate and untargeted alignment evidence.
**Topic group**: `evidence_spine_consistency.py` + `_io`, `_models`, `_analysis`, `_writers` (5 files)
**Originating decision**: `2026-05-18-shared-evidence-spine-adoption-decision.md`
**Recent commit**: `a3e4ea0 2026-05-25` (feat: add phase 1 peak pipeline gates)

---

### `cross_report_evidence_consistency.py`

**Purpose**: Compare targeted reliability and peak candidate evidence.
**Topic group**: `cross_report_evidence_consistency.py` + `_io`, `_models`, `_analysis`, `_writers` (5 files)
**Originating spec**: (none found — likely landed alongside post-PR60 cleanup; see `2026-05-24-post-pr60-codebase-cleanup-spec.md` Workstream G context)
**Duplication note**: Low-level parsing/writing helpers are consolidated through `xic_extractor/diagnostics/diagnostic_io.py`; `tools/diagnostics/diagnostic_io.py` remains a compatibility shim. Row dataclasses stay separate because the schemas differ.

---

### `shared_peak_identity_explanation.py`

**Purpose**: Write the default Slice 0 `diagnostic_only` shared peak identity explanation outputs from a durable manual oracle plus existing alignment/candidate-gate artifacts; with `--enable-blast-radius`, add Slice 1 blast-radius manifest, summary, run facts, and report sections over existing 8RAW / 85RAW alignment artifacts; with `--enable-shadow-label-alignment`, add V2 shadow-label alignment, machine-evidence provenance, readiness, and report artifacts. Optional `--cwt-shape-evidence-tsv`, `--tier2-trace-evidence-tsv`, `--candidate-ms2-pattern-evidence-tsv`, `--ms1-pattern-coherence-evidence-tsv`, `--qc-ms1-pattern-reference-evidence-tsv`, `--sample-negative-evidence-tsv`, `--matrix-rt-drift-policy-tsv`, `--rt-mode-evidence-tsv`, and `--peak-hypothesis-selection-tsv` inputs can mark CWT shape, Tier2 raw-trace scan/intensity, sample/candidate-aligned MS2 pattern, MS1 constellation pattern coherence, local/consensus injection-QC MS1 pattern reference, sample-level negative evidence class/detail, independent matrix RT drift facts, iRT/raw selected-apex mode membership, and mode-level PeakHypothesis selection as machine-observed evidence; `--candidate-ms2-pattern-batch-index` can generate that candidate-MS2 sidecar from the same discovery batch index used by the alignment run, `--candidate-ms2-pattern-raw-dll-dir` can additionally probe rows without `source_candidate_id` against the sample RAW file recorded in that batch index, `--generate-ms1-pattern-coherence-evidence` can generate a conservative alignment-cell boundary-constellation sidecar, `--ms1-pattern-coherence-overlay-trace-data-json` can enrich that generated MS1 sidecar with RAW-backed `family_ms1_overlay_plot` trace shape/local-window metrics and optional peak-quality feature-vector fields when overlay `rt` / `intensity` arrays are present, `--generate-matrix-rt-drift-policy` can generate the matrix RT drift policy sidecar from alignment cells plus optional owner-edge, RT-normalization-family, targeted-ISTD anchor-local trend artifacts, and optional ISTD injection-order / phase-summary provenance, `--generate-rt-mode-evidence` can generate `shared_peak_identity_rt_mode_evidence.tsv` from an existing selected-apex mode assignment TSV plus optional mode summary and candidate-MS2 tag sidecar, and `--generate-peak-hypothesis-selection` can generate `shared_peak_identity_peak_hypothesis_selection.tsv` from RT-mode evidence.
**Topic group**: `shared_peak_identity_explanation.py` + `xic_extractor/alignment/shared_peak_identity_explanation/*`
**Originating spec/plan**: `specs/2026-05-29-shared-peak-identity-evidence-explanation-pilot-design.md`; `plans/2026-05-29-shared-peak-identity-slice0-implementation-plan.md`; `plans/2026-05-29-shared-peak-identity-slice1-blast-radius-plan.md`; `plans/2026-05-30-shared-peak-identity-v15-v2-implementation-plan.md`
**Status note**: Default mode emits only the manual-oracle copy, evidence vectors, explanations, run facts, and Markdown report under `output/shared_peak_identity_evidence_explanation/`; it does not emit Slice 1 files unless `--enable-blast-radius` is passed. Slice 1 writes `shared_peak_identity_blast_radius_manifest.tsv` and `shared_peak_identity_blast_radius_summary.tsv` from existing artifacts only. V2 shadow mode writes `shared_peak_identity_shadow_labels.tsv`, `shared_peak_identity_shadow_alignment_summary.tsv`, `shared_peak_identity_v2_readiness.tsv`, `shared_peak_identity_machine_evidence_support.tsv`, and `shared_peak_identity_v2_report.md`; when the batch-index producer is enabled it also writes `shared_peak_identity_candidate_ms2_pattern_evidence.tsv`, when MS1 pattern generation is enabled it writes `shared_peak_identity_ms1_pattern_coherence_evidence.tsv`, when matrix RT drift generation is enabled it writes `shared_peak_identity_matrix_rt_drift_policy.tsv`, when RT mode generation is enabled it writes `shared_peak_identity_rt_mode_evidence.tsv`, and when PeakHypothesis generation is enabled it writes `shared_peak_identity_peak_hypothesis_selection.tsv`. `--generate-hypothesis-consistency` writes `shared_peak_identity_hypothesis_consistency.tsv` and `shared_peak_identity_hypothesis_consistency_summary.tsv`; this is a full-matrix diagnostic gate that cross-checks each PeakHypothesis against MS1 pattern, QC MS1 reference context, matrix RT drift, and candidate MS2/DDA opportunity evidence, but it does not select peaks, retarget rows, activate labels, or rewrite matrices. It can report `exploratory_only` when blast-radius evidence is not current or when decisive shape / pattern / opportunity evidence remains partial, conflicting, proxy-only, or manual-oracle-derived. Candidate MS2 pattern evidence is fail-closed and must be explicitly keyed by `feature_family_id + sample_stem`; target-label-only or RT/mz heuristic joins do not count. MS1 pattern coherence sidecars can close `formal_pattern_metric` when they emit supportive/partial `sample_constellation`, `sample_boundary_constellation`, or `trace_constellation` evidence; RAW-backed `trace_constellation` overlay rows can close `formal_shape_metric` only when they have `shape_metric_source=family_ms1_overlay_raw_trace`, `family_ms1_overlay_trace_data_json`, non-empty `shape_correlation_score`, and a machine-observed `peak_quality_vector_basis=family_ms1_overlay_raw_trace_vector` with `peak_quality_vector_status` of `supportive` or `partial_support`. QC MS1 reference sidecars can close `formal_pattern_metric` only when consensus-backed evidence levels such as `qc_consensus_with_local_qc_overlay` or `qc_consensus_qc_overlay` are supportive/partial; nearest-valid-local-only QC rows remain context-only. Consensus-backed QC conflicts can contribute to `pattern_metric_not_supportive` only when not overridden by sample-level RAW MS1 pattern support; they do not close `formal_shape_metric`. RT mode sidecars consume selected-apex mode assignments from overlay/iRT diagnostics and classify `rt_mode_pure`, `tag_backed_core_with_outlier_modes`, `irt_refined_mode_split`, `tailing_confounded`, or `consolidation_no_go`; tag-backed non-core mode membership fails closed as `rt_mode_not_supportive` and feeds the product activation `wrong_peak_conflict` rule, while tailing-confounded mode evidence remains diagnostic and must not force a split. PeakHypothesis selection sidecars convert RT-mode evidence into explicit product units: `product_candidate_core` is a mode-level candidate, `cross_mode_rescue_blocked` feeds `wrong_peak_conflict`, and `mode_split_required` / `consolidation_no_go` block family promotion until mode-aware consolidation exists. Sample negative sidecars can close `sample_level_negative_evidence` only with machine-observed `negative_evidence_class` in `no_candidate_ms1_evidence`, `pattern_mismatch`, `rt_not_explained`, or `local_peak_not_decisive`; `negative_evidence_detail` preserves narrower review reasons such as ugly shape, bad boundary, or QC reference conflict. Older overlay JSON without `rt` / `intensity` arrays remains readable but no longer counts as the full V2 formal-shape evidence chain. RAW overlay enrichment also records cell/local/global intensity metrics, including `cell_to_local_window_max_ratio`, and optional `peak_quality_*` vector fields for trace point count, boundary point count, S/N proxy, FWHM, sharpness, zigzag/noise, tailing, boundary margin, feature count, status, basis, and reason. Low shape correlation or low height can therefore be reviewed against selected-cell height dominance and trace-vector quality instead of being treated as automatic negative identity evidence. The generated MS1 sidecar remains conservative without overlay inputs: it uses existing alignment-cell apex/boundary/family-reference facts plus optional matrix RT drift policy, leaves raw shape correlation empty, and reports weak boundary-only or unmodeled-shift cases as `inconclusive` rather than false conflicts. Generated/read matrix RT drift policy evidence can close `matrix_rt_drift_policy` when supportive, and it fails closed as a machine-observed conflict when contradictory. The matrix RT drift producer reuses existing `alignment_cells.tsv`, optional `owner_edge_evidence.tsv`, optional `rt_normalization_families.tsv`, and optional paired `targeted_istd_benchmark_summary.tsv` + `rt_normalization_leave_one_anchor_out.tsv`; optional ISTD RT trend and phase-summary TSVs are provenance-only trend evidence, not a new fitted RT model. The targeted-ISTD anchor-local trend path is coverage-gated for 85RAW-like injection-order evidence and must not be used to tune RT policy from 8RAW method-smoke subsets. RAW-backed fallback is opt-in only through `--candidate-ms2-pattern-raw-dll-dir`; it uses the batch-index `raw_file`, existing `neutral_loss.collect_candidate_ms2_evidence`, and reports `sample_boundary_aligned` evidence only when a boundary/apex-aligned precursor MS2 scan is observed. Missing MS2 stays `not_observed`, not negative identity evidence; when MS1 is strongly supportive, MS1 intensity is at least `2.5e4`, RAW-boundary MS2 triggers are at least three, and the MS2 trace-strength proxy is moderate/strong, the missing expected NL is recorded as `dda_missing_nl_policy_status=not_dispositive` instead of a hard fail. This diagnostic does not mutate `alignment_review.tsv`, `alignment_cells.tsv`, `alignment_matrix.tsv`, workbooks, selected peaks, backfill, Tier 2 support, or downstream contracts, and it must not claim production readiness.
**QC reference policy note**: QC MS1 reference evidence is no longer nearest-QC-wins. `nearest_valid_qc_local_condition_only` is context only; only consensus-backed levels such as `qc_consensus_with_local_qc_overlay` or `qc_consensus_qc_overlay` can close `formal_pattern_metric`, and local-vs-consensus disagreement stays review-only. A QC consensus conflict is not a standalone veto when the target cell already has sample-level RAW MS1 pattern support; it supports product blocking only together with sample-level pattern/RT/PeakHypothesis wrong-peak evidence.

**Activation note**: With `--enable-product-activation-contract`, V2 shadow mode also writes `shared_peak_identity_activation_decisions.tsv` and `shared_peak_identity_activation_acceptance.tsv`. These files translate sidecar statuses into `auto_activate`, `auto_block`, `confidence_only`, or `review_required` product-effect candidates under `specs/2026-05-30-sidecar-to-product-label-activation-contract.md`; they remain diagnostic until a separate product wiring flag consumes them. Activation decisions keep `feature_family_id`/`candidate_container_id` as provenance and carry `peak_hypothesis_id` plus `activation_unit_scope` when a mode-level PeakHypothesis is the product candidate unit. When Slice 1 blast-radius is enabled, activation acceptance uses the current `all_available_85raw` blast-radius `assessed_row_count` as the row denominator and emits explicit basis fields so seed-scope decisions are not confused with a full production matrix mutation. `--activation-must-not-regress-tsv` evaluates a machine-readable expectation manifest such as `docs/superpowers/fixtures/shared_peak_identity_activation_must_not_regress_v1.tsv`; the manual `--activation-must-not-regress-status` flag is only a diagnostic fallback.

**Mode generalization note**: `--generate-rt-mode-evidence` can also consume repeated `--rt-mode-evidence-overlay-trace-data-json` inputs from RAW-backed `family_ms1_overlay_*` trace JSONs. iRT/assignment rows take precedence when the same family/sample is present. RAW-overlay-only split evidence is emitted as `raw_mode_review_only`; it can feed review queues and PeakHypothesis coverage, but it must not directly auto-block promotion or override the activation must-not-regress set without independent iRT/tag support. Use `--generate-mode-hypothesis-assignment` when the V2 flow should produce product-facing sample-level PeakHypothesis selection from typed iRT/mode evidence plus MS1, QC, RT-drift, and MS2 opportunity sidecars; this supersedes raw-overlay-derived mode selection for activation-facing evidence. Legacy `--generate-peak-hypothesis-selection` output is retained as diagnostic/review evidence; activation-facing auto-activation requires `peak_hypothesis_authority_source=typed_mode_hypothesis_assignment` or a locked oracle manifest. Overlay JSON `mode_windows` product-status fields are ignored by matrix construction and demoted to review-only candidates.

**Hypothesis consistency note**: `--generate-hypothesis-consistency` summarizes `scope=sidecar_key_union` by default. Interpret it as full-matrix only when the input PeakHypothesis, MS1 pattern, matrix RT drift, QC reference, and candidate MS2 sidecars are themselves full-matrix; representative or manual-oracle sidecars remain representative diagnostics.

**Opportunity-policy note**: RAW-backed MS1 overlay height/local-window evidence can satisfy `intensity_opportunity_metric` without a separate Tier 2 trace sidecar when it comes from `family_ms1_overlay_raw_trace` or the RAW trace-vector basis and intensity is at least `2.5e4`. Missing NL/product evidence with `raw_ms2_diagnostic_product_absence_reason=product_outside_diagnostic_window` is recorded as `dda_missing_nl_policy_status=not_dispositive` when the family has required-tag context, the sample has enough boundary MS2 trigger opportunity, and MS1 evidence is supportive; it remains non-dispositive evidence, not an auto-activation rule.

---

### `apply_shared_peak_identity_activation.py`

**Purpose**: Apply accepted `shared_peak_identity_activation_*` sidecars to alignment product outputs.
**Topic group**: `shared_peak_identity_explanation.py` + `xic_extractor/alignment/shared_peak_identity_explanation/product_activation.py`
**Originating spec/plan**: `specs/2026-05-30-sidecar-to-product-label-activation-contract.md`
**Status note**: This is the explicit sidecar-to-product bridge. It requires
`activation_acceptance_status=pass` by default. `--output-mode activated-copy`
writes `alignment_matrix_activated.tsv`, `alignment_review_activated.tsv`, and
`alignment_cells_activated.tsv`; `--output-mode formal` writes the formal
downstream contract files `alignment_matrix.tsv`, `alignment_review.tsv`, and
`alignment_cells.tsv` in the requested output directory. Formal matrix output
uses `peak_hypothesis_id` as row identity and keeps `feature_family_id` as
provenance. By default, rows without split/wrong-peak/mode evidence use
`<feature_family_id>::family_projection` with
`row_identity_basis=family_projection_no_split_evidence`; this is a blocker for
complete canonical row-identity readiness and is disclosed by
`canonical_row_identity_ready=FALSE`,
`canonical_row_identity_blockers=family_projection_present`,
`canonical_row_identity_scope=partial_peak_hypothesis_with_family_projections`,
`family_projection_semantics=projection_not_split_proof`, and
`all_family_split_science_ready=FALSE`. `--exclude-family-projections` is formal
mode only: it emits only explicit `peak_hypothesis_id` rows, reports skipped
unresolved projections in `family_projection_rows_excluded` and
`family_projection_cells_excluded`, and keeps
`canonical_row_identity_ready=FALSE` with
`canonical_row_identity_blockers=family_projection_excluded_incomplete_scope`
when projection rows were excluded. It cannot be combined with
`--require-complete-peak-hypothesis-identity` to certify completeness; that gate
must fail while excluded projection rows remain. This exclusion is not proof that
the full legacy family matrix has been completely split. Optional
`--legacy-rt-row-oracle-xlsx` adds
context-only `legacy_rt_row_context_id` hints from a legacy MZmine RT-row
workbook but does not mint product identities; matching outputs report
`legacy_rt_row_context_authority=context_only_not_identity_authority`. Both
modes also write `activation_application_summary.tsv` and
`activation_value_delta.tsv`. Existing matrix values are preserved; only missing
`auto_activate` cells are written, while `auto_block` cells can be blanked or
family promotion can be blocked. `activation_value_delta.tsv` records original
value, activated value, source cell area, effect, and `value_changed` for
review. If multiple provenance rows share one formal hypothesis/sample value,
the temporary pre-AsLS policy records the conflict and keeps the larger numeric
value. Formal mode refuses to overwrite source alignment TSVs unless
`--allow-overwrite-source` is passed. `--allow-non-passing-acceptance` is a
diagnostic override only and must not be used for product claims.

---

### `build_mode_hypothesis_assignment.py`

**Purpose**: Build typed sample-level PeakHypothesis assignment rows from `shared_peak_identity_rt_mode_evidence.tsv` plus candidate MS2 tag/opportunity, RAW-backed MS1 pattern, QC MS1 reference, and matrix RT drift policy sidecars.
**Topic group**: `shared_peak_identity_explanation.py` + `xic_extractor/alignment/shared_peak_identity_explanation/mode_hypothesis_assignment.py`
**Originating spec/plan**: `specs/2026-05-30-sidecar-to-product-label-activation-contract.md`
**Status note**: This is the product-facing producer for mode-aware sample assignment. It writes the existing `shared_peak_identity_peak_hypothesis_selection.tsv` schema so downstream matrix construction and activation can keep using `peak_hypothesis_id`, but the selection is no longer inferred from family overlay raw modes. A sample can become `product_candidate_core` only when typed iRT/mode evidence assigns it to a mode that has required-tag support and the sample-level MS1 shape, QC context, RT-drift policy, and boundary/MS2 opportunity evidence do not conflict. QC is a context/conflict gate, not a hard required gate: missing QC does not block when sample-level MS1, RT drift, and MS2/tag evidence support the assignment. RAW-selected or raw-overlay-only modes stay `raw_mode_review_only`; a family with no required tag becomes `consolidation_no_go`; a sample assigned to a non-tag mode while another mode carries the tag becomes `cross_mode_rescue_blocked`.

---

### `evaluate_mode_window_assignment_contract.py`

**Purpose**: Evaluate the Mode-Window Assignment Contract Gate v0 sentinel fixture against 85RAW sidecars.
**Topic group**: `shared_peak_identity_explanation.py` + `xic_extractor/alignment/shared_peak_identity_explanation/mode_window_assignment_gate.py`
**Originating spec/plan**: `specs/2026-05-30-sidecar-to-product-label-activation-contract.md`
**Status note**: This acceptance diagnostic consumes `docs/superpowers/fixtures/shared_peak_identity_mode_window_assignment_contract_v0.tsv`, a PeakHypothesis selection sidecar, and optional activation, matrix-summary, QC-reference, RT-drift, MS1-pattern, and candidate-MS2 sidecars. It writes `shared_peak_identity_mode_window_assignment_gate.tsv` plus `shared_peak_identity_mode_window_assignment_summary.tsv`. The gate checks explicit selection `peak_hypothesis_id`, activation `peak_hypothesis_id`, `product_unit_scope`, `selected_mode_id`, and `activation_unit_scope`, so legacy status/action rows cannot fake a typed mode-window acceptance. It also checks that fixture `required_evidence_oracle` requirements are backed by the supplied sidecars when the oracle names MS1, QC, RT, MS2, or tag evidence. The gate verifies that typed mode assignment can pass product-candidate and wrong-peak sentinel rows, that raw/overlay-only modes remain activation-ineligible, that QC and ISTD trend artifacts are treated as context rather than standalone identity authorities, and that any matrix with family-projection rows does not overclaim complete canonical row identity. A passing summary with `canonical_row_identity_ready=FALSE` is scoped contract acceptance only; it intentionally keeps product activation and complete canonical row identity blocked until matrix construction is ready. Use `--fail-on-gate-failure` when the command is serving as an actual acceptance gate instead of a diagnostic artifact writer.

---

### `build_peak_hypothesis_matrix.py`

**Purpose**: Build a diagnostic PeakHypothesis-assigned `alignment_matrix.tsv` before product activation by consuming source alignment TSVs plus `shared_peak_identity_peak_hypothesis_selection.tsv`, optional `shared_peak_identity_hypothesis_consistency.tsv`, and optional RAW-backed `family_ms1_overlay_*` trace-data JSONs with mode windows.
**Topic group**: `shared_peak_identity_explanation.py` + `xic_extractor/alignment/shared_peak_identity_explanation/peak_hypothesis_matrix.py`
**Originating spec/plan**: `specs/2026-05-30-sidecar-to-product-label-activation-contract.md`
**Status note**: This is the first matrix-construction boundary for mode-aware identity. It writes `alignment_matrix.tsv`, `peak_hypothesis_inventory.tsv`, `peak_hypothesis_cell_assignments.tsv`, and `peak_hypothesis_matrix_summary.tsv` in a separate output directory. The matrix row identity is `peak_hypothesis_id`; explicit product-candidate modes use `row_identity_basis=matrix_construction_peak_hypothesis`, unresolved legacy cells use `<feature_family_id>::family_projection` with `row_identity_basis=family_projection_no_split_evidence`, and hard split/wrong-peak consistency blockers are recorded in assignments but not written to the matrix. When `--overlay-trace-data-json` is supplied, each declared `mode_windows` peak with RAW trace signal is enumerated as an expanded candidate row before matrix output, so two peaks from the same `feature_family_id` can both enter the matrix as independent `peak_hypothesis_id` rows instead of competing through retarget. Any product-status fields embedded in overlay JSON `mode_windows` are ignored and demoted to `raw_mode_review_only`; only typed PeakHypothesis selection rows can supply product-facing authority. Untyped mode windows and raw-apex inferred windows are review-only expanded candidates: they use `construction_assignment_status=expanded_candidate`, default to `candidate_value_basis=raw_overlay_window_trapezoid_area`, set `canonical_row_identity_ready=FALSE` with `canonical_row_identity_blockers=raw_mode_review_only`, and must not be treated as product-ready row identity until a typed mode-hypothesis contract supplies explicit iRT/manual/tag-confirmed status. Family projection rows set `canonical_row_identity_blockers=family_projection_present`; they are acceptable bridge rows but not proof of complete canonical identity. Cells with source `alignment_cells.tsv` area but no source matrix value are recorded as candidate context only (`matrix_value_effect=source_matrix_value_missing`) until quantification/baseline policy is wired. `--require-complete-peak-hypothesis-identity` now fails unless the summary reports `canonical_row_identity_ready=TRUE`, so projection-heavy diagnostic outputs cannot be mistaken for promotion-ready matrices. This tool is `diagnostic_only`: it proves that split/wrong-peak separation can happen before matrix output, but it does not mutate source alignment artifacts or claim all-family split-science readiness.

---

### `diagnose_shared_peak_wrong_peak.py`

**Purpose**: Diagnose `wrong_peak_conflict` activation blocks and propose RAW-overlay alternate peak candidates without retargeting product outputs.
**Topic group**: `shared_peak_identity_explanation.py` + `xic_extractor/alignment/shared_peak_identity_explanation/wrong_peak_root_cause.py`
**Originating spec/plan**: `specs/2026-05-30-sidecar-to-product-label-activation-contract.md`
**Status note**: This diagnostic consumes `shared_peak_identity_activation_decisions.tsv`, `shared_peak_identity_machine_evidence_support.tsv`, `alignment_cells.tsv`, and optional `family_ms1_overlay_*` trace-data JSON files. It writes `shared_peak_identity_wrong_peak_root_cause.tsv` with the selected-cell evidence, root-cause class, selection failure mode, and strongest alternate local maximum outside the selected boundary. Alternate peaks are review candidates only; this tool does not mutate `alignment_matrix.tsv`, product labels, selected peaks, backfill, or activation decisions.

---

## Alignment Diagnostics

CLI reports and audits over alignment outputs (cells, families, owner
decisions, RT normalization, matrix identity).

### `alignment_decision_report.py`

**Purpose**: Render an HTML decision report from alignment diagnostics.
**Topic group**: `alignment_decision_report.py` + `_io`, `_styles`, `_components`, `_model`, `_rendering` (6 files)
**Originating spec**: `2026-05-16-module-responsibility-inventory.md` (decomposition target PR1) + `2026-05-24-post-pr60-codebase-cleanup-spec.md` Workstream G
**Note**: Rendering / components / styles split landed in commit `4549cdd 2026-05-24`.

---

### `untargeted_alignment_guardrails.py`

**Purpose**: Compute and compare untargeted alignment guardrails.
**Topic group**: `untargeted_alignment_guardrails.py` + `_io`, `_models`, `_metrics`, `_outputs`, `_targets` (6 files)
**Originating plan**: `plans/2026-05-13-untargeted-drift-aware-owner-edge-plan.md`
**Spec status**: ACTIVE facade per `2026-05-24-post-pr60-codebase-cleanup-spec.md:638` ("now stays as the CLI/orchestration compatibility facade").

---

### `targeted_gt_alignment_audit.py`

**Purpose**: Audit untargeted alignment against targeted workbook GT.
**Topic group**: `targeted_gt_alignment_audit.py` + `_io`, `_models`, `_analysis`, `_writers`, `_utils` (6 files)
**Originating spec**: `2026-05-16-module-responsibility-inventory.md` + Workstream G in `2026-05-24-post-pr60-codebase-cleanup-spec.md`

---

### `analyze_matrix_identity_blast_radius.py`

**Purpose**: Analyze matrix identity blast radius for alignment outputs, including projected machine-decision role/action columns from existing review and cell artifacts.
**Topic group**: `analyze_matrix_identity_blast_radius.py` (single-file)
**Originating spec**: `2026-05-14-matrix-identity-consolidation-v2-spec.md`; machine-decision projection columns from `2026-05-28-tiered-backfill-machine-decision-contract-spec.md`
**Recent doc**: `plans/2026-05-14-matrix-identity-consolidation-v2-plan.md`; `plans/2026-05-28-tiered-backfill-machine-decision-contract-implementation-plan.md`; `notes/2026-05-28-tiered-backfill-machine-decision-implementation-note.md`
**Status note**: Machine-decision columns are `diagnostic_only` projection output, not a downstream `alignment_matrix.tsv` contract.

---

### `analyze_rt_normalization_anchors.py`

**Purpose**: Analyze anchor-based RT normalization for alignment outputs.
**Topic group**: `analyze_rt_normalization_anchors.py` + `rt_normalization_anchor_{loaders, models, analysis, writers}` (5 files)
**Originating spec**: (none found; rt_normalization pipeline behavior lives in `xic_extractor/alignment/rt_normalization.py`)
**Naming note**: The entry-point uses `analyze_*` prefix while helpers use `rt_normalization_anchor_*` prefix — pending rename per audit-note Cluster discussion.

---

### `backfill_scope_probe.py`

**Purpose**: Probe alignment backfill scope size without running owner backfill.
**Topic group**: `backfill_scope_probe.py` (single-file)
**Originating doc**: `notes/2026-05-26-p8b-owner-backfill-superwindow-investigation-note.md` (recent investigation context)

---

## Backfill Reviews

Three overlapping review axes (seed-level / family-level /
row-classifier-level), 2 owner-backfill economics tools, 1 Tier 2 RAW trace
producer, and 1 `diagnostic_only` provisional candidate-gate sidecar. The
sidecars are not economics axes; they consume retained provisional backfill rows
to emit RAW-backed evidence, promotion blockers, and source hashes while the
existing review/economics axes remain pending cleanup per audit-note Cluster 2.

### `seed_aware_backfill_review.py`

**Purpose**: Build a seed-aware shadow review for rescued-heavy backfill families.
**Topic group**: `seed_aware_backfill_review.py` + `_constants`, `_io`, `_model`, `_writers` (5 files)
**Originating spec**: (none found; pre-dates the lifecycle spec)

---

### `family_ms1_backfill_review_report.py`

**Purpose**: Build a review queue for low-seed/high-backfill MS1-supported families.
**Topic group**: `family_ms1_backfill_review_report.py` + `_io`, `_model`, `_writers` (4 files)
**Originating spec**: (none found explicitly; appears in post-PR60 cleanup spec line ~183 as Workstream G product)

---

### `low_ms1_assessable_coverage_audit.py`

**Purpose**: Classify low_ms1_assessable_coverage_review families as RT/window, single-center XIC, or primary-backfill support issues.
**Topic group**: `low_ms1_assessable_coverage_audit.py` + `low_ms1_coverage_review_{classifier, loaders, models, writers}` (5 files; 683-line classifier is the largest)
**Originating spec**: `2026-05-20-low-ms1-coverage-review-module-deepening-spec.md`

---

### `ms1_index_backfill_audit.py`

**Purpose**: Audit owner-backfill vendor XIC versus MS1-index XIC.
**Topic group**: `ms1_index_backfill_audit.py` (single-file)
**Originating note**: `notes/2026-05-26-p75-85raw-reentry-validation-note.md` (recent investigation context)

---

### `owner_backfill_request_economics.py`

**Purpose**: Summarize owner-backfill request cost by final row identity.
**Topic group**: `owner_backfill_request_economics.py` (single-file)
**Originating spec**: `2026-05-15-owner-backfill-request-economics-spec.md`

---

### `provisional_backfill_candidate_gate.py`

**Purpose**: Emit a `diagnostic_only` machine sidecar for retained provisional backfill rows, including Tier 2 support components, challenge blockers, and source artifact hashes.
**Topic group**: `provisional_backfill_candidate_gate.py` + `xic_extractor/alignment/production_candidate_gate.py`
**Originating spec/plan**: `specs/2026-05-29-provisional-backfill-production-candidate-gate-design.md`; `plans/2026-05-29-provisional-backfill-diagnostic-sidecar-pilot-implementation-plan.md`
**Status note**: Writes `alignment_production_candidate_gate.tsv`; optional Tier 2 support must come from `--tier2-trace-evidence-tsv` plus `--tier2-raw-manifest-tsv`, not direct `alignment_review.tsv` tokens. Does not mutate `alignment_review.tsv`, `alignment_matrix.tsv`, workbook schemas, or downstream correction/statistics contracts.

---

### `tier2_raw_trace_reread_producer.py`

**Purpose**: Produce paired `diagnostic_only` Tier 2 RAW trace evidence and RAW manifest sidecars for retained provisional backfill candidates.
**Topic group**: `tier2_raw_trace_reread_producer.py` + `xic_extractor/alignment/tier2_trace_producer.py` + `xic_extractor/alignment/production_candidate_gate.py`
**Originating spec/plan**: `specs/2026-05-29-tier2-evidence-producer-provenance-contract-design.md`; follows the sidecar provenance gate checkpoint in `plans/2026-05-29-tier2-sidecar-provenance-gate-checkpoint-plan.md`; v0.1 diagnostic criteria review in `specs/2026-05-29-tier2-v0-coherence-criteria-review-design.md` and `plans/2026-05-29-tier2-v0-coherence-diagnostic-plan.md`.
**Status note**: Writes diagnostic-only v0.1 Tier 2 RAW trace evidence and RAW manifest sidecars. The v0.1 criteria expose scan availability, signal/noise, shape, boundary-reference, apex-span, and neighbor-interference context, but do not provide positive Tier 2 support or change `alignment_matrix.tsv`. 85RAW is out of scope until a reviewed follow-up plan is approved after a successful v0.1 8RAW diagnostic rerun.

---

## Peak / Candidate Audits

### `cwt_peak_candidate_audit.py`

**Purpose**: Audit CWT peak candidate agreement from peak_candidates.tsv.
**Topic group**: `cwt_peak_candidate_audit.py` + `_io`, `_models`, `_analysis`, `_writers` (5 files)
**Originating spec**: `2026-05-16-peak-candidate-table-v1-spec.md` + `2026-05-24-peak-pipeline-cwt-evidence-honesty-spec.md`

---

### `peak_candidate_score_calibration_report.py`

**Purpose**: Audit peak candidate scoring against newer evidence labels without changing production selection.
**Topic group**: `peak_candidate_score_calibration_report.py` + `_io`, `_models`, `_analysis`, `_writers` (5 files)
**Originating spec**: `2026-05-16-peak-candidate-table-v1-spec.md`

---

### `selected_envelope_review_queue.py`

**Purpose**: Build `diagnostic_only` selected-envelope changed-row and boundary-oracle review queue artifacts from `selected_envelope_diagnostics.tsv`.
**Topic group**: `selected_envelope_review_queue.py` + `xic_extractor/peak_detection/selected_envelope_*`
**Originating spec/plan**: `specs/2026-06-03-selected-full-envelope-quantitation-boundary-spec.md`; `plans/2026-06-03-selected-full-envelope-quantitation-boundary-implementation-goal.md`
**Status note**: Writes `selected_envelope_changed_rows.tsv`, `selected_envelope_oracle_review_queue.tsv`, `selected_envelope_diagnostic_manifest.tsv`, and `selected_envelope_review_queue.json` under an explicit output directory. This tool only packages the audit sidecar for manual/expert boundary review; it does not run RAW files, mutate selected `IntegrationResult`, change targeted workbook/CSV `Area`, or authorize FE4/8RAW by itself.

---

### `selected_envelope_plot_review.py`

**Purpose**: Render `diagnostic_only` selected-envelope boundary review plots from selected-envelope diagnostic rows, showing RAW XIC, AsLS baseline, Gaussian15 morphology overlay, resolver interval, selected envelope, optional manual/expert oracle overlay, and quantitation context in one figure.
**Topic group**: `selected_envelope_plot_review.py` + `xic_extractor/peak_detection/selected_envelope_*`
**Originating spec/plan**: `specs/2026-06-03-selected-full-envelope-quantitation-boundary-spec.md`; `plans/2026-06-03-selected-full-envelope-quantitation-boundary-implementation-goal.md`
**Status note**: Re-reads RAW files for bounded manual/expert review only. It can consume an optional `selected_envelope_boundary_oracle.tsv` / boundary-oracle TSV to draw expert-reviewed RT windows and record selected candidate id plus oracle id/source/status in `selected_envelope_plot_index.tsv`. It can also consume `chrom_peak_segment_review_rows.tsv` from `chrom_peak_segment_candidate_gate.py` to force explicit review-only segment rows into the plot index. Gaussian15 is an Xcalibur-like morphology/review trace, not an exact clone of Xcalibur's proprietary smoothing and not a product area source. Plot overlays fail closed unless oracle rows are `expert_reviewed` with manual/expert sources (`manual_overlay`, `expert_overlay`, or `manual_2raw`); targeted workbook control rows remain benchmark-only and are not drawn as boundary truth. It writes PNG/PDF overlays and `selected_envelope_plot_index.tsv`; it does not mutate selected `IntegrationResult`, change targeted workbook/CSV `Area`, or promote selected-envelope behavior by itself.

---

### `chrom_peak_segment_candidate_gate.py`

**Purpose**: Summarize scored `chrom_peak_segment` candidate adoption from
`peak_candidates.tsv`, compare selected-row area deltas against a baseline
candidate TSV, and emit a segment-native gate manifest plus changed-row TSV.
**Topic group**: `chrom_peak_segment_candidate_gate.py` (single-file)
**Originating spec/plan**:
`specs/2026-06-03-selected-full-envelope-quantitation-boundary-spec.md`;
`notes/2026-06-04-chrom-peak-segment-overlay-evidence.md`
**Status note**: Writes
`chrom_peak_segment_gate_manifest.json` and
`chrom_peak_segment_changed_rows.tsv`, plus
`chrom_peak_segment_review_rows.tsv`. This is a product-candidate diagnostic
gate for segment enumeration, not a selected-envelope promotion gate. It reports
boundary and presence sub-gates separately so area/boundary regressions do not
get mixed with analyte false-pick or review-only detection policy risk. Manual
presence review verdicts such as `expected_peak_change`, `blocked`,
`false_pick`, `inconclusive`, and `needs_followup` keep the presence gate in
`defer` until the product-selection or review policy is resolved.

---

## Targeted Benchmarks & Reviews

### `targeted_istd_benchmark.py`

**Purpose**: Run strict targeted ISTD benchmark for untargeted alignment.
**Topic group**: `targeted_istd_benchmark.py` + `_loaders`, `_matching`, `_models`, `_stats`, `_summary`, `_writers` (7 files; largest group)
**Originating spec**: `2026-05-16-targeted-benchmark-reliability-spec.md`
**Recent doc**: `plans/2026-05-16-targeted-benchmark-reliability-plan.md`

---

### `targeted_evidence_review_report.py`

**Purpose**: Render a human-first HTML report from targeted diagnostics.
**Topic group**: `targeted_evidence_review_report.py` + `_components`, `_model`, `_rendering`, `_styles` (5 files)
**Originating spec**: `2026-05-24-post-pr60-codebase-cleanup-spec.md` Workstream G (rendering split twin with `alignment_decision_report`)

---

### `targeted_peak_reliability_audit.py`

**Purpose**: Audit targeted peak reliability for benchmark eligibility.
**Topic group**: `targeted_peak_reliability_audit.py` + `_classifier`, `_loaders`, `_models`, `_writers` (5 files)
**Originating spec**: `2026-05-16-targeted-benchmark-reliability-spec.md`

---

### `targeted_nl_dropout_root_cause_audit.py`

**Purpose**: Classify targeted review-positive NL dropout root causes.
**Topic group**: `targeted_nl_dropout_root_cause_audit.py` + `_io`, `_models`, `_logic`, `_writers` (5 files)
**Originating spec**: `2026-05-17-targeted-nl-dropout-convergence-spec.md`

---

### `single_dr_production_gate_decision_report.py`

**Purpose**: Build a single-dR production gate decision report.
**Topic group**: `single_dr_production_gate_decision_report.py` + `single_dr_gate_decision_{loaders, writers}` (3 files)
**Originating spec**: `2026-05-16-module-responsibility-inventory.md:29` (designated PR2 split target)

---

### `multi_tag_adduct_audit.py`

**Purpose**: Audit multi-tag and adduct evidence.
**Topic group**: `multi_tag_adduct_audit.py` (single-file)
**Originating spec**: `2026-05-15-multi-nl-tag-and-artificial-adduct-contract.md`
**Recent doc**: `plans/2026-05-15-multi-nl-tag-and-artificial-adduct-plan.md`

---

### `build_target_pair_expected_diff_approval_registry.py`

**Purpose**: Convert explicitly user-approved `target_pair_rt_auto_reselection.tsv`
rows into a durable `model_selection_expected_diff_approval_registry` TSV for
guarded targeted product mutation.
**Topic group**: `build_target_pair_expected_diff_approval_registry.py`
(single-file)
**Originating spec**:
`specs/2026-06-03-target-pair-rt-auto-reselection-spec.md`
**Status note**: Requires repeated `--approved-row SAMPLE::TARGET` inputs and
fails closed unless each row is a `row_approval_candidate` shadow switch with
matching runtime `expected_diff_stable_row_id`, selected-candidate RT, and
paired area ratio `within_reference_range`. It does not auto-approve all watch
rows and does not recompute candidate evidence.

---

## Instrument QC

The Instrument QC suite is a coherent product surface; six entry-points
share the `instrument_qc_*` prefix. Per the lifecycle spec, several of
these are candidates for "seasonal cadence" declarations (calibration runs
are not daily).

### `instrument_qc_sequence_manifest.py`

**Purpose**: Build docs-derived instrument QC sequence manifest.
**Originating spec**: `2026-05-20-instrument-qc-phases-3-6-consolidated-spec-plan.md`

---

### `instrument_qc_sdolek_calibration.py`

**Purpose**: Calibrate Phase 1 SDO/LEK trends with method-doc order.
**Originating spec**: `2026-05-20-instrument-qc-sdolek-calibration-v1-spec.md`
**Recent doc**: `plans/2026-05-20-instrument-qc-sdolek-calibration-v1-plan.md`

---

### `instrument_qc_biological_istd_transfer_audit.py`

**Purpose**: Build audit-only evidence for clean-standard RT trend transfer to biological QC ISTDs.
**Originating spec**: `2026-05-20-instrument-qc-phases-3-6-consolidated-spec-plan.md`

---

### `instrument_qc_calibration_maturity_gate.py`

**Purpose**: Build audit-only go/no-go decisions for instrument-QC calibration maturity levels.
**Originating spec**: `2026-05-20-instrument-qc-phases-3-6-consolidated-spec-plan.md`
**Recent doc**: `plans/2026-05-21-instrument-qc-mid-long-term-calibration-gates-plan.md`

---

### `instrument_qc_matrix_calibration_preview.py`

**Purpose**: Build manifest-backed instrument QC calibration evidence bundle and optional matrix preview sidecar.
**Originating spec**: `2026-05-21-instrument-qc-matrix-calibration-productization-spec.md`
**Recent doc**: `plans/2026-05-21-instrument-qc-matrix-calibration-productization-plan.md`

---

### `instrument_qc_decision_report.py`

**Purpose**: Render a compact instrument QC decision report.
**Originating spec**: `2026-05-20-instrument-qc-phases-3-6-consolidated-spec-plan.md`

---

## Family / Overlay Visualization

Matplotlib-rendered MS1 overlay visuals for human review of family-level
backfill candidates.

### `family_ms1_overlay_plot.py`

**Purpose**: Render MS1 overlay evidence for one alignment feature family.
**Topic group**: `family_ms1_overlay_plot.py` + `_evidence`, `_models`, `_rendering`, `_rendering_styles`, `_trace`, `_writers` (7 files)
**Originating spec**: (none found; landed alongside backfill review work)

---

### `family_ms1_overlay_batch.py`

**Purpose**: Render queued family MS1 overlays from a backfill review report.
**Topic group**: shares helpers with `family_ms1_overlay_plot`
**Pairs with**: `family_ms1_backfill_review_report.py` (produces the queue, this consumes it)

---

### `qc_ms1_pattern_reference.py`

**Purpose**: Build a `diagnostic_only` nearest-injection-QC MS1 pattern reference sidecar from `family_ms1_overlay_plot` RAW trace JSON plus SampleInfo injection order; reports whether the closest QC supports, conflicts with, or cannot adjudicate a reviewed sample's selected MS1 peak.
**Topic group**: `qc_ms1_pattern_reference.py` + `xic_extractor/alignment/shared_peak_identity_explanation/qc_ms1_pattern_reference.py`
**Originating context**: V2 shared peak identity evidence-chain follow-up for using nearby QC MS1 pattern as an RT-drift / wrong-peak adjudication surface.

---

## Area / Region Audits

### `area_integration_uncertainty_audit.py`

**Purpose**: Classify targeted/untargeted area mismatch by integration audit.
**Topic group**: `area_integration_uncertainty_audit.py` + `_io`, `_models`, `_analysis`, `_writers` (5 files)
**Originating spec**: `2026-05-18-area-integration-uncertainty-audit-gate.md`
**Recent doc**: `plans/2026-05-25-p4-area-uncertainty-formula-implementation.md`, `plans/2026-05-26-p2b-asls-production-promotion-plan.md`
**Schema note**: The current accepted `alignment_cell_integration_audit.tsv` schema no longer emits linear-edge rollback columns. Historical promoted-AsLS rows that still include `area_baseline_corrected_linear_edge` remain readable as legacy comparison input.

---

### `region_first_safe_merge_comparison.py`

**Purpose**: Compare default XIC output with opt-in region-first safe merge.
**Topic group**: `region_first_safe_merge_comparison.py` (single-file)
**Originating spec**: `2026-05-18-region-first-safe-merge-validation-gate.md` + `2026-05-19-safe-merge-provenance-validation.md`

---

## One-off Fixtures

Tools that build deterministic test fixtures from production data; expected
to be re-run only when the underlying data shape changes.

### `build_istd_false_missing_fixture.py`

**Purpose**: Build ISTD false-missing validation fixture.
**Topic group**: `build_istd_false_missing_fixture.py` (single-file)
**Originating plan**: `plans/2026-05-13-untargeted-final-matrix-rescue-contract-plan.md`
**Cadence note**: "Build-once" — should declare a per-campaign or per-data-shape cadence per the lifecycle spec's seasonal-cadence exception.

---

## Shared Infrastructure

Not entry-points, but referenced by multiple topic groups:

- `xic_extractor/diagnostics/diagnostic_io.py` — package-owned shared delimited/TSV read-write, scalar parsing, header validation, label splitting, and value formatting. `tools/diagnostics/diagnostic_io.py` re-exports it as a compatibility shim for existing diagnostic CLIs. Cluster 1 and the listed Cluster 3 loaders now reuse this helper; use it before adding local `_read_required_tsv`, `_bool_value`, `_optional_float`, `_text`, `_required_indexes`, or `_write_tsv` copies.

## Maintenance Notes

- **Adding a new entry-point**: Append it to the matching group section, or
  create a new group if none fit. Always populate Purpose / Topic group /
  Originating spec — these are the minimum for an entry to be useful at
  session start.
- **Removing an entry-point** (RETIRED per spec): Remove the entry from the
  section and add a one-line tombstone in the deletion PR. Do not leave
  stale entries.
- **Group recategorization**: If a tool migrates between groups, update
  both old and new sections' tool counts in the Table of Contents.
- **Regeneration**: This file can be partially regenerated by grepping
  `description=` and `__doc__` over `tools/diagnostics/*.py` entry-points,
  but cross-references to specs/plans require human curation.
