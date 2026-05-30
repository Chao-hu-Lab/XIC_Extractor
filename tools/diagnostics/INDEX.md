# tools/diagnostics/ — Diagnostic Tool Index

**Last generated:** 2026-05-29
**Total entry-points:** 41
**Total files (incl. helpers):** ~114
**Governing spec:** `docs/superpowers/specs/2026-05-26-diagnostic-tool-lifecycle-spec.md`

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
2. [Evidence Consistency](#evidence-consistency) — 3 tools
3. [Alignment Diagnostics](#alignment-diagnostics) — 6 tools
4. [Backfill Reviews](#backfill-reviews) — 7 tools
5. [Peak / Candidate Audits](#peak--candidate-audits) — 2 tools
6. [Targeted Benchmarks & Reviews](#targeted-benchmarks--reviews) — 6 tools
7. [Instrument QC](#instrument-qc) — 6 tools
8. [Family / Overlay Visualization](#family--overlay-visualization) — 2 tools
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

**Purpose**: Gate P2 AsLS baseline area against linear-edge integration audit rows for targeted ISTD benchmark selections; supports both legacy AsLS-shadow and promoted AsLS schemas.
**Topic group**: `p2_asls_shadow_gate.py`
**Originating spec**: `2026-05-24-peak-pipeline-area-baseline-asls-spec.md`
**Recent doc**: `plans/2026-05-25-p2-asls-baseline-shadow-implementation.md`, `plans/2026-05-26-p2b-asls-production-promotion-plan.md`

---

### `p2_baseline_truth_audit.py`

**Purpose**: Build a diagnostic-only baseline truth audit for P2/P2b AsLS gate ISTD families; compares linear-edge rollback against promoted AsLS when available.
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
**Current gate note**: Exit `0` is reserved for true linear-edge retirement authority. B1 relevance fixtures are the only synthetic layer that can drive `decision_target=c1b-plan`; B2 stress evidence is reported for retirement/Tier C follow-up and must not by itself create a C1b no-go. v1 fixture outputs are non-authoritative under the B1/B2 contract and should be treated as `LEGACY_V1_NON_AUTHORITATIVE` / `INCONCLUSIVE_FIXTURE_SCOPE_MISMATCH`.

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
spine vs cell). The two tools below share low-level diagnostic IO helpers, but
keep separate row models because their output schemas are intentionally
different; see `2026-05-26-diagnostic-lifecycle-audit-note.md` Cluster 1.

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
**Duplication note**: Low-level parsing/writing helpers are consolidated through `diagnostic_io.py`; row dataclasses stay separate because the schemas differ.

---

### `shared_peak_identity_explanation.py`

**Purpose**: Write the default Slice 0 `diagnostic_only` shared peak identity explanation outputs from a durable manual oracle plus existing alignment/candidate-gate artifacts; with `--enable-blast-radius`, add Slice 1 blast-radius manifest, summary, run facts, and report sections over existing 8RAW / 85RAW alignment artifacts; with `--enable-shadow-label-alignment`, add V2 shadow-label alignment, machine-evidence provenance, readiness, and report artifacts. Optional `--cwt-shape-evidence-tsv`, `--tier2-trace-evidence-tsv`, and `--candidate-ms2-pattern-evidence-tsv` inputs can mark CWT shape, Tier2 raw-trace scan/intensity, and sample/candidate-aligned MS2 pattern facts as machine-observed evidence; `--candidate-ms2-pattern-batch-index` can generate that candidate-MS2 sidecar from the same discovery batch index used by the alignment run, and `--candidate-ms2-pattern-raw-dll-dir` can additionally probe rows without `source_candidate_id` against the sample RAW file recorded in that batch index.
**Topic group**: `shared_peak_identity_explanation.py` + `xic_extractor/alignment/shared_peak_identity_explanation/*`
**Originating spec/plan**: `specs/2026-05-29-shared-peak-identity-evidence-explanation-pilot-design.md`; `plans/2026-05-29-shared-peak-identity-slice0-implementation-plan.md`; `plans/2026-05-29-shared-peak-identity-slice1-blast-radius-plan.md`; `plans/2026-05-30-shared-peak-identity-v15-v2-implementation-plan.md`
**Status note**: Default mode emits only the manual-oracle copy, evidence vectors, explanations, run facts, and Markdown report under `output/shared_peak_identity_evidence_explanation/`; it does not emit Slice 1 files unless `--enable-blast-radius` is passed. Slice 1 writes `shared_peak_identity_blast_radius_manifest.tsv` and `shared_peak_identity_blast_radius_summary.tsv` from existing artifacts only. V2 shadow mode writes `shared_peak_identity_shadow_labels.tsv`, `shared_peak_identity_shadow_alignment_summary.tsv`, `shared_peak_identity_v2_readiness.tsv`, `shared_peak_identity_machine_evidence_support.tsv`, and `shared_peak_identity_v2_report.md`; when the batch-index producer is enabled it also writes `shared_peak_identity_candidate_ms2_pattern_evidence.tsv`. It can report `exploratory_only` when blast-radius evidence is not current or when decisive shape / pattern / opportunity evidence remains partial, conflicting, proxy-only, or manual-oracle-derived. Candidate MS2 pattern evidence is fail-closed and must be explicitly keyed by `feature_family_id + sample_stem`; target-label-only or RT/mz heuristic joins do not count. RAW-backed fallback is opt-in only through `--candidate-ms2-pattern-raw-dll-dir`; it uses the batch-index `raw_file`, existing `neutral_loss.collect_candidate_ms2_evidence`, and reports `sample_boundary_aligned` evidence only when a boundary/apex-aligned precursor MS2 scan is observed. Missing MS2 stays `not_observed`, not negative identity evidence. This diagnostic does not mutate `alignment_review.tsv`, `alignment_cells.tsv`, `alignment_matrix.tsv`, workbooks, selected peaks, backfill, Tier 2 support, or downstream contracts, and it must not claim production readiness.

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

## Area / Region Audits

### `area_integration_uncertainty_audit.py`

**Purpose**: Classify targeted/untargeted area mismatch by integration audit.
**Topic group**: `area_integration_uncertainty_audit.py` + `_io`, `_models`, `_analysis`, `_writers` (5 files)
**Originating spec**: `2026-05-18-area-integration-uncertainty-audit-gate.md`
**Recent doc**: `plans/2026-05-25-p4-area-uncertainty-formula-implementation.md`, `plans/2026-05-26-p2b-asls-production-promotion-plan.md`
**Schema note**: When promoted AsLS audit rows include `area_baseline_corrected_linear_edge`, baseline-area mismatch checks use that linear-edge-compatible rollback value, not the promoted AsLS value.

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

- `tools/diagnostics/diagnostic_io.py` — shared delimited/TSV read-write, scalar parsing, header validation, label splitting, and value formatting. Cluster 1 and the listed Cluster 3 loaders now reuse this module; use it before adding local `_read_required_tsv`, `_bool_value`, `_optional_float`, `_text`, `_required_indexes`, or `_write_tsv` copies.

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
