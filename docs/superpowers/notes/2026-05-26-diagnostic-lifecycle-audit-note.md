# Diagnostic Tool Lifecycle - 2026-05-26 Audit

**Date:** 2026-05-26
**Worktree:** `codex/peak-pipeline-modernization`
**Audit method:** Subagent-driven inventory of `tools/diagnostics/`, `scripts/`,
`xic_extractor/diagnostics/` with caller / docs / commit cross-reference.
**Governing spec:** `docs/superpowers/specs/2026-05-26-diagnostic-tool-lifecycle-spec.md`

---

## Summary

- `tools/diagnostics/` contains ~108 `.py` files across 30+ topic groups.
- `xic_extractor/` and `scripts/` import **zero** modules from `tools.diagnostics`.
- `xic_extractor/diagnostics/` contains only `timing.py`; the in-package
  diagnostic path is effectively dead.
- 11 files classified `RETIRED` (no caller, no docs reference, no commit in
  60+ days, only a sentinel test).
- 6 topic groups identified as promotion candidates to a future
  `xic_extractor/diagnostics/gates/` package.
- 3 duplication clusters identified for consolidation.

## RETIRED Candidates (RETRACTED)

**Status as of 2026-05-26 strict re-audit:** The initial classification of
11 files as `RETIRED` has been **formally retracted**. Zero files satisfied
all four demotion conditions when evaluated under a strict reading of the
spec's "docs reference" rule.

**Why the first audit was wrong.** The first pass used a narrow definition
of "no docs reference in the last 30 days" - essentially commit-log
mentions only. It missed extensive textual references in
`docs/superpowers/specs/` and `docs/superpowers/plans/` from the last 2-16
days. The lifecycle spec was clarified on the same day (2026-05-26) to
make explicit that **any textual mention** counts as a reference, including
prose, code examples, sample commands, checklists, and inventory tables.

**Revised disposition of the original 11 candidates:**

- **2 ACTIVE misclassified as ORPHAN:**
  - `tools/diagnostics/untargeted_alignment_guardrails.py` -
    `docs/superpowers/specs/2026-05-24-post-pr60-codebase-cleanup-spec.md:638`
    explicitly declares it "now stays as the CLI/orchestration
    compatibility facade" (2 days old at audit time).
  - `tools/diagnostics/single_dr_production_gate_decision_report.py` -
    `docs/superpowers/specs/2026-05-16-module-responsibility-inventory.md:29`
    designates it as the active facade for PR2 split work; its test
    directly invokes `report.main(...)` with frozen-schema assertions.
- **9 DORMANT misclassified as ORPHAN:** The remaining 9 modules are
  recent (2-16 days old commits), cited in plans actively being executed
  (e.g., `2026-05-13-untargeted-final-matrix-rescue-contract-plan.md`,
  `2026-05-14-matrix-identity-consolidation-v2-plan.md`), and their tests
  are frozen-schema assertions of public outputs - not sentinel imports.
  These are not retired; they are simply between scheduled uses.

**Lesson recorded.** The deeper failure here is not a missing rule - it is
that the first-pass agent did not see what was visible to a careful human
reader (recent specs, plan-driven work). Most diagnostic tools in this
repo exist for a reason; the operational problem is not "too many tools"
but **agent-to-agent discoverability of existing tools**. Follow-up work
shifts from "delete orphans" to "build a tool index" - see
`tools/diagnostics/INDEX.md` (under construction) for the catalog every
new session is expected to read first.

**PR A (mass deletion) is SUPERSEDED.** Future cleanup PRs may still
delete individual files if and only if a strict per-file evaluation
against all four demotion conditions passes; the spec's
`RETIRED` definition (as clarified 2026-05-26) is the only authority.

## Promotion Candidates (6 topic groups)

These are phase gates explicitly designated by specs / plans / recent commits;
under the spec's "spec-designation" promotion trigger, they should move into
`xic_extractor/diagnostics/gates/`:

| Group | Source spec / plan / commit |
|---|---|
| `p1_resolver_default_gate` | `2026-05-24-peak-pipeline-resolver-default-switch-spec.md`; commit `ebfa2a3` |
| `p2_asls_shadow_gate` | `2026-05-24-peak-pipeline-area-baseline-asls-spec.md` |
| `p2_baseline_truth_audit` | same as above |
| `p2b_asls_promotion_gate` | `2026-05-24-peak-pipeline-area-baseline-asls-promotion-spec.md` |
| `p7_alignment_parity`, `p7_evidence_cost_summary` | `2026-05-25-evidence-chain-cost-control-implementation-plan.md` |
| `evidence_spine_consistency*` | `2026-05-18-shared-evidence-spine-adoption-decision.md`; recent commit `a3e4ea0` |

**Recommended action:** Sequence of promotion PRs, one per group. Each moves
the topic's files into `xic_extractor/diagnostics/gates/<group>/`, leaves a
thin shim in `tools/diagnostics/` for CLI compatibility, adds a no-RAW import
smoke test, and does not change any TSV/JSON/Markdown schema.

## Duplication Clusters

### Cluster 1: Evidence Consistency Twins

- `tools/diagnostics/evidence_spine_consistency*` (5 files)
- `tools/diagnostics/cross_report_evidence_consistency*` (5 files)

**Status:** addressed by `2026-05-26-diagnostic-cleanup-cluster1-3-plan.md`.
The two groups now share low-level TSV/scalar/writer helpers through
`tools/diagnostics/diagnostic_io.py`.

`ConsistencyRow` and `ConsistencySummary` remain independently defined because
the row schemas are not identical. Treat future duplicate helper additions here
as drift; do not merge the row dataclasses without an explicit schema contract.

### Cluster 2: Backfill Review Trio

- `tools/diagnostics/seed_aware_backfill_review*` (5 files)
- `tools/diagnostics/family_ms1_backfill_review*` (4 files)
- `tools/diagnostics/low_ms1_coverage_review*` (4 files; includes a
  683-line classifier) plus `low_ms1_assessable_coverage_audit.py`

Three different "review TSV row" schemas for what appears to be the same
underlying "backfill outcome review" semantics. May or may not be legitimately
orthogonal (seed-level vs family-level vs row-classifier-level).

**Recommended action:** Spec first. Write a short spec or plan that defines
whether the three axes are orthogonal (legitimate) or redundant views
(mergeable). Only then proceed to consolidation. Do not collapse blindly.

### Cluster 3: Writer Infrastructure Non-Sharing

- `tools/diagnostics/diagnostic_io.py` now owns shared delimited/TSV IO,
  scalar parsing, label splitting, required-column reads, and workbook header
  index validation.
- The originally listed writer / loader modules were migrated where
  behavior-equivalent:
  - `build_istd_false_missing_fixture.py`
  - `cross_report_evidence_consistency_io.py`
  - `cwt_peak_candidate_audit_io.py`
  - `rt_normalization_anchor_loaders.py`
  - `targeted_gt_alignment_audit_io.py`
  - `targeted_istd_benchmark_loaders.py`
  - `targeted_nl_dropout_root_cause_io.py`
  - `targeted_peak_reliability_loaders.py`

**Status:** addressed for the listed modules. No `_common/` package was added
because the repeated behavior fit the existing `diagnostic_io.py` module and a
new package would add ceremony without reducing more coupling.

## Suggested Implementation Sequence

Per the spec's principle of "rules first, actions in separate PRs":

1. **PR A (SUPERSEDED):** The original "delete 11 `RETIRED` files" plan is
   retracted; see the RETIRED Candidates section above. Replaced by a
   discoverability initiative: generate `tools/diagnostics/INDEX.md` and
   add an `AGENTS.md` rule that new sessions must consult it before
   creating new diagnostic tools.
2. **PR B (medium risk, ~10-15h):** Promote the 6 phase-gate groups into
   `xic_extractor/diagnostics/gates/`. One sub-PR per group is recommended
   for review clarity.
3. **PR C (DONE):** Evidence-consistency common helpers consolidated through
   `diagnostic_io.py`; schema-specific row models retained.
4. **PR D (write-only spec first, then implementation):** Spec defining
   backfill review axis semantics (Cluster 2), then consolidation PR(s).
5. **PR E (DONE for listed modules):** Cluster 3 listed modules migrated to
   `diagnostic_io.py` where behavior-equivalent. Future diagnostics should use
   that module before adding local parser/writer helpers.

## Out-of-Scope For This Audit Note

This note is the 2026-05-26 disposition. It does not classify every file
beyond the punch list above. Subsequent quarterly lifecycle audits append
new notes under `docs/superpowers/notes/` with their own date prefix and
may reclassify items as the codebase evolves.
