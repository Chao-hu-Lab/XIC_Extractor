# Term-Level Vocabulary Disambiguation Spec

> **⚠️ SUPERSEDED BY CRITIQUE — DO NOT EXECUTE AS WRITTEN.** Two-round
> independent critique (2026-06-10) rejected the "rename campaign" framing as a
> sunk-cost salvage and found concrete errors (e.g. `authority` (b) coupling is
> `schema_coupled`, not `internal_only`; the A1 split also changes an audit-TSV
> column via `_candidate_outcome`; C6 parity tests do not yet exist). The
> reduced plan — a glossary doc + two targeted fixes (A1 label split,
> `consolidation_state` additive provenance) — lives in
> [2026-06-10-term-vocabulary-spec-independent-critique-note.md](../notes/2026-06-10-term-vocabulary-spec-independent-critique-note.md).
> This file is retained only as the inventory evidence base.

**Date:** 2026-06-10
**Status:** Superseded draft — inventory evidence only; framing rejected by
2026-06-10 critique. See banner above.
**Readiness label:** `diagnostic_only`
**Worktree:** `feat/untarget-diagnostics-and-perf`
**Sibling (module-level):**
[Repo semantic-overlap inventory](2026-06-02-repo-semantic-overlap-inventory-spec.md)
**Related:**
[C6 alignment stage semantics](2026-06-01-c6-alignment-stage-semantics-value-assessment-design.md),
[Diagnostic tool lifecycle](2026-05-26-diagnostic-tool-lifecycle-spec.md),
[Untargeted final matrix and rescue evidence](2026-05-13-untargeted-final-matrix-and-rescue-evidence-spec.md)

---

## Purpose

This spec is the **term-level** sibling of the module-level semantic-overlap
inventory. That spec catalogs *which modules* compete for one product job. This
spec catalogs *which words* carry multiple unrelated meanings, so that a reader
or reviewer cannot infer behavior from a name.

Goal: give each overloaded term a **disambiguation direction**, a **coupling
class** (how baked-in the term is), and an **exit rule**. Execution — the actual
renames — belongs to follow-up PRs that cite this spec. Most of these terms are
already baked into `SCHEMA_VERSION` strings, TSV/JSON columns, or test-asserted
`Literal` values, so a rename is a schema migration, not free cleanup.

## This Spec Does NOT

- rename anything, or change schemas, TSV/JSON columns, `SCHEMA_VERSION`
  strings, CLI tokens, GUI, or tests;
- re-litigate conservative gate behavior. The 60s no-drift RT wall
  (`edge_scoring`), complete-link grouping, and fail-closed primary-matrix
  writes are **deliberate specced design decisions**, not vocabulary debt — see
  *Out-of-Scope: Conservatism Is Not Vocabulary Debt* below;
- duplicate the module-level inventory. That pass is orthogonal: it routes
  module ownership; this pass routes word meanings;
- re-open the `shared_peak_identity_explanation/` directory name. The
  module-level inventory already classified it `diagnostic_preserve /
  policy_projection` and deferred any rename. Not revisited here.

## Why Term-Level Matters (Distinct From Module-Level)

The module-level inventory found overlapping module owners. But even within
correctly-separated modules, the **same word is reused for unrelated concepts**,
so a name cannot be trusted to imply behavior.

The most dangerous case is **`shadow`**. "Shadow" implies "does not affect
production." Yet `standard_peak_shadow_activation_inputs` is the direct
pre-write staging step feeding the only matrix-writing activation path. A name
that under-states its effect is a correctness hazard for reviewers, not an
aesthetic complaint. Disambiguating these words is therefore a maintainability
and a safety task.

## Coupling Classification (How Expensive Is A Rename)

| Coupling | Meaning | Rename cost |
|---|---|---|
| `internal_only` | term appears only in private functions, locals, or comments | rename freely in a move-only PR |
| `schema_coupled` | term is a `SCHEMA_VERSION`, a TSV/JSON column, a `Literal` value asserted by a contract test, or a public CLI token | rename = schema migration; requires parity test plus version bump or dual-read shim |
| `cross_spec_vocab` | term carries a fixed meaning in `docs/` or `docs/superpowers/specs/` | doc alignment only; no code change |

Default to `schema_coupled` when unsure. **A per-term coupling audit is a
prerequisite to any rename PR** — this spec does not perform that audit; it
records the best-available coupling estimate and marks low-confidence ones.

## Term Overload Inventory

All sites below were verified against current code on 2026-06-10 (direct read or
agent-traced-then-spot-checked). Refuted candidates are recorded explicitly so
they are not re-flagged.

### 1. `shadow` — 4 distinct meanings

| # | Site | Meaning |
|---|---|---|
| a | `xic_extractor/diagnostics/backfill_shadow_policy.py:23` (`SCHEMA_VERSION = "backfill_shadow_policy_v0"`, `ShadowPolicyDecision` Literal) | family/seed-group **policy simulation** — "would this group fill if the policy were live" |
| b | `xic_extractor/diagnostics/shadow_production_projection.py:35-37` (`SCHEMA_VERSION = "shadow_production_projection_v1"`, `ShadowDecision = Literal["accept","block","context"]`) | cell-level **production projection** — accept/block a rescued cell |
| c | `xic_extractor/extraction/peak_region_selection_shadow.py:15-20` (`shadow_boundary_id`, `shadow_verdict`, …) | **alternate boundary** held alongside the selected region for comparison |
| d | `tools/diagnostics/p2_asls_shadow_gate.py:1` ("P2 AsLS shadow baseline diagnostic gate") | **method-switch parallel run** before promoting AsLS baseline |

- **Collision hazard:** (a) and (b) both live in `diagnostics/` and both use
  `ShadowXxx` naming at different granularities. Across all four, `shadow`
  variously means *simulation*, *projection*, *alternate*, and *parallel run*.
- **Coupling:** `schema_coupled` (each is a `SCHEMA_VERSION` or TSV header).
- **Direction:** reserve `shadow` for one meaning (recommend *non-writing audit
  projection*, i.e. (b)); rename the others to their actual role
  (`policy_simulation`, `alternate_boundary`, `parallel_run_gate`). Rename
  `*_shadow_activation_inputs` to a name that states it is pre-write staging.
- **Exit rule:** each rename ships as a versioned schema migration with a
  diff-parity test on the affected TSV; no two renames bundled.

### 2. `gate` — 4 distinct meanings

| # | Site | Meaning |
|---|---|---|
| a | `xic_extractor/diagnostics/standard_peak_ms1_authority_bundle.py:29-36` (`STANDARD_PEAK_SUPPORTED = "standard_peak_gate_supported"`) | **pre-commit promotion gate** — approves a family before activation writes the matrix |
| b | `xic_extractor/diagnostics/retained_backfill_evidence_gate.py:23,30-36` (`EvidenceGateStatus` Literal) | **post-write diagnostic classifier** — reviews already-written cells, does not block |
| c | `tools/diagnostics/p2_asls_shadow_gate.py:1`, `tools/diagnostics/p2b_asls_promotion_gate.py:1` | **phase gate** — method-promotion milestone (P2 shadow / P2b promotion) |
| d | `xic_extractor/instrument_qc/calibration_maturity_gate.py:30` (`build_calibration_maturity_decisions`, `go_no_go`) | **instrument-QC maturity gate** — is the RT/response model mature enough |

- **Collision hazard:** (a) blocks a matrix write; (b) does not block anything.
  Same word "evidence gate" used for pre-commit control and post-write review —
  the highest-risk pair because it controls whether a reader thinks data can
  still change.
- **Coupling:** `schema_coupled` for (a)(b)(d) (Literal values / decision
  fields); (c) is partly `cross_spec_vocab` (phase labels in specs).
- **Direction:** split the word by tense — `*_admission_gate` (pre-commit) vs
  `*_review_classifier` (post-write) vs `phase_gate` (milestone) vs
  `maturity_gate` (QC).
- **Exit rule:** per-term schema migration; phase-gate renames also update the
  referencing specs.

### 3. `authority` — 3 distinct meanings

| # | Site | Meaning |
|---|---|---|
| a | `xic_extractor/alignment/backfill_evidence_projection.py:40-44` (`PRODUCT_AUTHORITY_*_FIELD`, `product_authorized`), `backfill_ms1_product_authority.py:24` | per-cell **sidecar field** asserting an MS1 evidence row is product-authorized |
| b | `xic_extractor/diagnostics/standard_peak_ms1_authority_bundle.py:29` | a **module/orchestration name** that bundles gate results + overlays |
| c | `docs/lcms-msms-evidence-rules.md:17-46` "MS1 Morphology And Area Owner" (`gaussian15_positive_asls_residual` area owner) | which **method owns the final-matrix area** — unrelated to (a)/(b) |

- **Collision hazard:** (a) is a field value and (b) is a module name, and both
  appear in the same backfill reference chain; (c) is a different axis entirely
  (area-ownership method).
- **Coupling:** (a) `schema_coupled`; (b) `internal_only` (module name);
  (c) `cross_spec_vocab`.
- **Direction:** keep `product_authority` for the sidecar field (a); rename the
  bundle module (b) to `*_authority_bundle` → `*_product_sidecar_builder` or
  similar that does not collide with the field; leave (c) as doc vocabulary but
  cross-reference so readers know "area owner" ≠ "product authority".
- **Exit rule:** field name is frozen until a sidecar schema migration; module
  rename is a free move-only PR.

### 4. `calibration` — 3 unrelated meanings

| # | Site | Meaning |
|---|---|---|
| a | `tools/diagnostics/shift_aware_backfill_calibration_pack.py:21`, `shift_aware_standard_peak_gate_calibration.py:23` | **manual-oracle labeling** pack for gate tuning |
| b | `xic_extractor/instrument_qc/calibration.py:30-40`, `tools/diagnostics/instrument_qc_sdolek_calibration.py` | **instrument-QC RT/area trend** calibration |
| c | `tools/diagnostics/peak_candidate_score_calibration_models.py:26` + report | **score-threshold analysis** |

- **Collision hazard:** three unrelated activities; today the only separator is
  the filename prefix.
- **Coupling:** `schema_coupled` (each has its own `SCHEMA_VERSION` / output).
- **Direction:** rename by activity — `*_review_oracle_pack` (a),
  `instrument_qc_*_trend` (b), `*_score_threshold_study` (c). Lowest priority of
  the four word-clusters because filename prefixes already disambiguate.
- **Exit rule:** schema migration per tool; defer until higher-risk words done.

### 5. `consolidation_state` — one field, two writers, overwrite hazard

- Field: `AlignedCell.consolidation_state` (`matrix.py:116`) and
  `CrossSamplePeakGroupHypothesis.consolidation_state`
  (`cross_sample_peak_groups.py:128`).
- Writer 1 — **pre-backfill RT-split identity merge**:
  `pre_backfill_consolidation.py:145` (`"primary_winner"`), `:167`
  (`"primary_loser"`).
- Writer 2 — **post-backfill rescue-heavy duplicate merge**:
  `primary_consolidation.py:447` (`"primary_winner"`), `:523`
  (`"primary_loser"`), `:554-558` (`"moved_to_primary_winner"`).
- **Collision hazard:** both writers emit the **same string values** into the
  **same field** for **different operations**, and Writer 2 runs later and
  **overwrites** Writer 1. A reader of `consolidation_state` cannot tell which
  operation produced the value, and the provenance of a `primary_loser` is
  ambiguous.
- **Coupling:** `schema_coupled` (field value, likely in `alignment_cells.tsv`).
- **Direction:** either (i) add an operation-provenance field
  (`consolidation_stage` ∈ {`pre_backfill`,`primary`}) so the state value keeps
  meaning, or (ii) namespace the values (`prebackfill_winner` vs
  `primary_winner`). Prefer (i) — additive, lower migration cost.
- **Exit rule:** additive column ships with a schema version bump and a
  read-back parity test; no value-string change until then.

### 6. `owner_backfill_unassessable` — one label, 5 sites, 4 causes (A1)

This is the worked example tying the semantic cleanup to the A1 finding.

| Site | reason string | upstream cause |
|---|---|---|
| `owner_backfill.py:236` | "…query was not assessable" | primary path: RAW read fail or arrays invalid (catch-all) |
| `owner_backfill.py:260` | "…validation source was not available" | validation source missing |
| `owner_backfill.py:325` | "…validation query was not assessable" | validation path: RAW/arrays fail |
| `owner_backfill.py:726` | "…query was not assessable" | `except (OSError, ValueError)` — RAW I/O **and** invalid arrays |
| `owner_backfill.py:840` | "…query was not assessable" | trace `ValueError` |

- Distinct from `owner_backfill_not_detected` (`:742`, `:858` — valid trace, no
  accepted peak), which is correctly separate.
- **Collision hazard:** four distinct causes — RAW I/O error, empty/invalid
  arrays, missing validation source, chunk-skip fallback — collapse into one
  `trace_quality`. Downstream (and operators) cannot distinguish an actual RAW
  read failure (corrupt/locked/missing file) from a genuinely empty trace. With
  `raw_xic_batch_size = 64` (production, `scripts/run_alignment.py:37`), a single
  RAW `OSError` in `_iter_exact_request_traces` skips a whole window-group and
  collapses up to 64 cells to `unassessable` (batch poisoning), even cells that
  would have extracted a real peak.
- **Coupling:** `schema_coupled` — `trace_quality` flows into
  `OwnerBackfillCandidateAuditRow` and `_candidate_outcome`, so it is an output
  value.
- **Direction (label split):** distinct `trace_quality` per cause, e.g.
  `owner_backfill_raw_read_error`, `owner_backfill_arrays_invalid`,
  `owner_backfill_validation_source_missing`, keeping
  `owner_backfill_not_detected` as-is. This is a schema migration on a
  C6 contract-hardened stage → requires cell-status parity coverage.
- **Out of scope for the rename:** the **batch-poisoning robustness fix**
  (per-item `OSError` retry in the exact path, mirroring the super-window path's
  existing graceful fallback at `owner_backfill.py:378-385`) is a **behavior
  change**, not a rename. It changes rescue counts, so it must be sequenced
  **after** the #6 recovery measurement establishes a baseline. See
  *Sequencing* below.

### Refuted / downgraded candidates (do not re-flag)

- **`has_anchor` "always True / dead field" — REFUTED.** `has_anchor=True` only
  in `_hypothesis_from_owner_group` (`cross_sample_peak_groups.py:676`); it is
  set `False` on ambiguous review-only paths (`:116`, `:281`) and merged via
  `any(...)` in `pre_backfill_consolidation.py:131`. The config thresholds
  `anchor_min_evidence_score` / `anchor_min_seed_events` are consumed in
  `edge_scoring.py:242-246`. Anchor is **not** dead. The only residual point is
  a mild root overlap between the config-threshold cluster (`anchor_min_*`) and
  the struct bool (`has_anchor`); **low priority**, not part of this cleanup.
  (`anchor_priorities` consumption is unconfirmed — needs a separate check
  before any action, not assumed dead.)
- **`status="backfilled"` collision — REFUTED.** `CellStatus`
  (`matrix.py:18-25`) is `detected/rescued/absent/unchecked/ambiguous_ms1_owner/
  duplicate_assigned`; there is no `backfilled` status. "Backfill" (process) and
  "rescued" (status) only blur in **prose**, not in code. Downgraded to a
  documentation-clarity note: prefer "backfill (process) → rescued (cell
  status)" wording in docs; no rename.

## A1 As The First Worked Example And Its Sequencing

`owner_backfill_unassessable` is the cleanest first cut because it is concrete,
verified, and bounded. It separates into two independent pieces that must NOT be
bundled (move-before-change):

1. **Label split (this spec's scope)** — schema migration giving each cause a
   distinct `trace_quality`, with C6 cell-status parity tests. No rescue-count
   change.
2. **Batch-poisoning robustness fix (behavior change, separate spec/PR)** —
   per-item `OSError` retry. Changes rescue counts → sequence after the #6
   recovery measurement so the delta is measured, per the project's
   "diagnose-before-change" discipline.

## Out-of-Scope: Conservatism Is Not Vocabulary Debt

A prior review pass framed three behaviors as "over-conservative." A cross-check
against existing specs found all three are deliberate, specced decisions, not
debt, and they are explicitly out of scope here:

- **60s no-drift-prior RT wall → weak_edge split** — specced in
  `2026-05-13-untargeted-duplicate-drift-soft-edge-design.md`.
- **complete-link requiring all-strong edges** — chosen in
  `2026-05-10-alignment-clustering-plan.md` ("intentionally closer to
  complete-link … more conservative, but protects against merging false
  positives with incompatible CID/NL evidence").
- **rescued-with-area not written to primary matrix unless authorized** —
  decided across `2026-05-13-untargeted-final-matrix-and-rescue-evidence-spec.md`
  and `2026-06-02-asls-primary-matrix-value-policy-spec.md` (fail-closed).

Any revisit of these requires their own behavior-change spec plus real-data
validation; the empirical question "is the conservatism too costly?" is answered
by the **#6 recovery/conservatism-cost diagnostic** (per-cell block-reason
distribution + 60s-wall split attribution), not by vocabulary work.

## Non-Goals (mirror the module-level inventory)

- No schema, TSV, JSON, workbook, config, CLI, GUI, or public-import change
  without a separate migration/behavior spec.
- No rename of a term baked into an accepted `SCHEMA_VERSION` without a version
  bump plus diff-parity test.
- No bundling of two renames, or a rename with a behavior change, in one PR.
- No deletion of code under this inventory's authority.

## Acceptance Criteria For This Spec

- Every overloaded term has: verified distinct sites (file:line), a coupling
  class, a disambiguation direction, and an exit rule.
- Refuted candidates (`has_anchor`, `status="backfilled"`) are recorded as NOT
  debt so they are not re-flagged.
- A1 (`owner_backfill_unassessable`) is captured as the worked example with its
  label-split / robustness-fix split and the sequencing constraint vs #6.
- The conservatism items are explicitly fenced out as specced design.

## Recommended Execution Order

1. **A1 label split** — highest concreteness, bounded, C6 parity coverage.
2. **`consolidation_state` provenance** — additive field, low migration cost,
   removes a real provenance ambiguity.
3. **`shadow` disambiguation** — highest correctness hazard (under-stated
   effect), but largest blast radius; do after the cheaper two prove the
   migration+parity pattern.
4. **`gate` disambiguation** — pre-commit vs post-write split.
5. **`authority` module rename** (free move-only) + doc cross-reference for the
   area-owner sense.
6. **`calibration`** — lowest priority; filename prefixes already disambiguate.

## Verification Note

Inventory sites were confirmed by direct code read and a verification agent on
2026-06-10. Two earlier candidates were **refuted** during verification
(`has_anchor` always-True, `status="backfilled"`) and removed from scope.
`anchor_priorities` consumption and the exact set of TSV columns carrying each
term are **not yet audited** — the per-term coupling audit is a prerequisite to
each rename PR, not a claim made here.

Per project discipline, this draft should receive the two-round independent
critique (local self-critique + a separate-session root critique) before any
execution PR.
