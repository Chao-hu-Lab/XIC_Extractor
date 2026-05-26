# tools/diagnostics/ — Diagnostic Tool Index

**Last generated:** 2026-05-26
**Total entry-points:** 38
**Total files (incl. helpers):** ~108
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

1. [Phase Gates (P1/P2/P2b/P7)](#phase-gates-p1p2p2bp7) — 6 tools
2. [Evidence Consistency](#evidence-consistency) — 2 tools
3. [Alignment Diagnostics](#alignment-diagnostics) — 6 tools
4. [Backfill Reviews](#backfill-reviews) — 5 tools
5. [Peak / Candidate Audits](#peak--candidate-audits) — 2 tools
6. [Targeted Benchmarks & Reviews](#targeted-benchmarks--reviews) — 6 tools
7. [Instrument QC](#instrument-qc) — 6 tools
8. [Family / Overlay Visualization](#family--overlay-visualization) — 2 tools
9. [Area / Region Audits](#area--region-audits) — 2 tools
10. [One-off Fixtures](#one-off-fixtures) — 1 tool

---

## Phase Gates (P1/P2/P2b/P7)

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

**Purpose**: Gate P2 AsLS shadow baseline columns against linear-edge integration audit rows for targeted ISTD benchmark selections.
**Topic group**: `p2_asls_shadow_gate.py`
**Originating spec**: `2026-05-24-peak-pipeline-area-baseline-asls-spec.md`
**Recent doc**: `plans/2026-05-25-p2-asls-baseline-shadow-implementation.md`

---

### `p2_baseline_truth_audit.py`

**Purpose**: Build a diagnostic-only baseline truth audit for P2 AsLS shadow gate ISTD families.
**Topic group**: `p2_baseline_truth_audit.py`
**Originating spec**: `2026-05-24-peak-pipeline-area-baseline-asls-spec.md` (shared with shadow gate)
**Recent doc**: `plans/2026-05-25-p2-baseline-truth-audit-implementation.md`

---

### `p2b_asls_promotion_gate.py`

**Purpose**: Run the revised P2b AsLS promotion gate.
**Topic group**: `p2b_asls_promotion_gate.py`
**Originating spec**: `2026-05-24-peak-pipeline-area-baseline-asls-promotion-spec.md`
**Recent doc**: `plans/2026-05-25-p2b-revised-asls-promotion-gate-implementation.md`, `plans/2026-05-25-p2d-rt-boundary-first-p2b-gate-implementation.md`

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
spine vs cell). The two tools below are known twins; see
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
**Duplication note**: Shares `ConsistencyRow` / `ConsistencySummary` dataclasses and 4 helpers with `evidence_spine_consistency`; pending consolidation per audit-note Cluster 1.

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

**Purpose**: Analyze matrix identity blast radius for alignment outputs.
**Topic group**: `analyze_matrix_identity_blast_radius.py` (single-file)
**Originating spec**: `2026-05-14-matrix-identity-consolidation-v2-spec.md`
**Recent doc**: `plans/2026-05-14-matrix-identity-consolidation-v2-plan.md`

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

Three overlapping axes (seed-level / family-level / row-classifier-level)
plus 2 owner-backfill economics tools. See audit-note Cluster 2 — pending
spec to decide whether these axes are orthogonal or redundant.

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
**Recent doc**: `plans/2026-05-25-p4-area-uncertainty-formula-implementation.md`

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

- `tools/diagnostics/diagnostic_io.py` — shared TSV/JSON read/write and value formatting. Currently under-used (only ~3 callers). See audit-note Cluster 3 for the consolidation plan; pending `_common/` extraction.

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
