# Matrix Identity Consolidation v2 Spec

**Date:** 2026-05-14
**Status:** Corrected copy for `algorithm-performance-optimization`; matrix identity gate implemented, iRT diagnostic deferred
**Branch:** `codex/algorithm-performance-optimization`
**Worktree:** `C:\Users\user\Desktop\XIC_Extractor\.worktrees\algorithm-performance-optimization`

## Summary

The untargeted final matrix should contain stable feature-family identities, not
every plausible XIC/backfill candidate that appears during alignment.

The previous final-matrix contract cleaned the cell surface:

```text
primary matrix cells = accepted numeric areas or blanks
audit/review cells   = statuses, rescue tiers, duplicate ownership, reasons
```

This spec adds the missing row-level contract:

```text
primary matrix rows     = feature families with durable identity support
provisional/review rows = low-support detected discovery evidence
audit rows              = rescue-only, duplicate-only, ambiguous-only, and losers
```

The goal is to keep the old pipeline's clean matrix shape while preserving the
new pipeline's higher sensitivity in audit/review surfaces.

## Problem

The current pipeline has improved recovery and diagnostics, but 85-RAW review
evidence shows that row promotion remains too permissive. The main unresolved
problem is not exact same-peak double counting. It is that weak row identities
survive too long:

- zero-present families;
- duplicate-only families;
- families dominated by backfilled/rescued cells;
- single-`dR` families where one or two detected seeds are amplified into a
  mostly backfilled production row;
- single-`dR` families where weak detected seed quality plus dominant backfill
  creates too much false-positive room;
- single-sample local owners that are treated as final matrix identities instead
  of retained provisional discovery evidence;
- families with high duplicate claim pressure but no durable winner decision.

These rows are useful diagnostics or provisional discoveries. They should remain
in Review/Audit surfaces. They should not automatically become user-facing
matrix rows.

## Product Contract

### Primary Matrix

The primary matrix is the handoff surface for downstream preprocessing,
normalization, and statistics.

Each row must represent one accepted feature-family identity.

Each sample cell must contain only:

- accepted numeric area values;
- blank.

No status strings, review-only candidates, duplicate-loser values, or orphaned
backfill values may appear in the primary matrix.

### Audit And Review

Audit/review outputs remain complete and must preserve all candidate evidence:

- raw cell status;
- rescue tier;
- blank reason;
- original discovery owner;
- backfill source;
- duplicate winner/loser state;
- row-level identity decision;
- row-level promotion or rejection reason.

Losing or review-only candidates are not deleted. They are explicitly moved out
of the primary matrix.

## Definitions

| Term | Meaning |
|---|---|
| `candidate` | A detected or extracted LC-MS event before row-level production promotion. |
| `feature family` | A group of compatible events/backfill measurements that could represent one final matrix row. |
| `production family` | A feature family allowed to appear in the primary matrix. |
| `provisional discovery` | A detected feature family kept in Review/Audit because it may be real but has not earned primary matrix identity. |
| `audit family` | A feature family kept only in diagnostics/review because it lacks detected discovery support or lost the family-winner decision. |
| `durable identity support` | Evidence that the row identity is supported before or independently of backfill. |
| `local-only owner` | A row whose identity support comes from one sample-local owner only. |
| `rescue/backfill` | MS1 measurement for an already established family, not identity evidence by itself. |
| `duplicate claim pressure` | One or more cells lost area ownership to another family. |

## Identity Evidence Model

Row promotion must be decided by a single row-identity decision layer, not by
ad hoc writer checks or post-hoc guardrail counting.

### Inputs

The identity layer may read:

- `family_evidence`;
- `has_anchor`;
- event cluster count and event member count;
- detected cell count before and after claim registry;
- shared cell-quality decisions for each cell;
- quantifiable detected-cell count;
- quantifiable rescue-cell count;
- review rescue count and reason from shared cell-quality decisions;
- duplicate assigned count;
- ambiguous owner count;
- present rate;
- existing row flags;
- warning/reason fields from review output.

The identity layer must not read targeted labels as production identity rules.
Targeted labels remain validation fixtures only.

### Cell-Quality Source Of Truth

The identity layer must not independently recompute production cell acceptance
from raw `status` and `area` alone.

Cell usability must come from a shared cell-quality decision layer used by both:

- row identity promotion; and
- `production_decisions.py` cell output decisions.

That shared layer is responsible for local cell quality facts such as finite
area, complete peak fields, rescue RT validity, duplicate-loser state, and
ambiguous owner state. Row identity then decides whether those usable cells are
allowed to enter the primary matrix. This prevents the benchmark/guardrail layer
from using a different definition of "accepted" than production output.

### Primary Evidence Classes

The row decision should expose a `primary_evidence` field.

| Class | Meaning | Default primary matrix behavior |
|---|---|---|
| `multi_sample_owner` | Multiple quantifiable detected cells support the row after claim registry. | Eligible |
| `owner_complete_link` | Existing owner/family evidence links compatible events with durable support. | Eligible in Phase A when at least two quantifiable detected cells remain |
| `anchored_family` | Anchor evidence exists and at least one quantifiable detected cell remains. | Provisional by default in Phase A when fewer than two quantifiable detected cells remain |
| `single_sample_local_owner` | One local owner only, with no durable cross-sample support. | Provisional by default |
| `rescue_only` | Row has rescue/backfill candidates but no quantifiable detected identity support. | Audit |
| `duplicate_only` | Row only contains duplicate losers or duplicate-dominated evidence. | Audit |
| `zero_present` | Row has no quantifiable cell evidence. | Audit |
| `ambiguous_owner` | Ownership conflict prevents durable row identity. | Audit |

### Hard Gates

A family must fail primary matrix promotion when any hard gate applies:

1. `quantifiable_cell_count == 0`.
2. `quantifiable_detected_count == 0`.
3. all quantifiable cells are rescued/backfilled.
4. all original detected support was lost to duplicate assignment.
5. `single_sample_local_owner` is the only identity evidence. It fails primary
   promotion but remains `provisional_discovery`, not `audit_family`.
6. `review_only` is set on the cluster/family.
7. duplicate or ambiguous ownership removes the only durable identity support.
8. Phase A only: fewer than two quantifiable detected cells remain, unless a
   later phase implements a tested explicit exception.
9. Single-`dR` extreme backfill dependency: one or two quantifiable detected
   identity-support cells and quantifiable rescue cells in at least 70% of
   samples. These rows remain `provisional_discovery` because manual EIC review
   showed plausible MS1 peaks but weak NL/MS2 support and a large false-positive
   gap.
10. Single-`dR` weak-seed backfill dependency: no more than three quantifiable
    detected identity-support cells, quantifiable rescue cells in at least 60%
    of samples, and weak detected seed quality. Weak seed quality means
    `evidence_score < 60`, `seed_event_count < 2`,
    `abs(neutral_loss_mass_error_ppm) > 10`, or detected candidate join missing.

Backfill/rescue may improve matrix completeness only after a family has already
passed identity eligibility.

### Soft Flags

A production family may still appear in the primary matrix with review flags:

| Flag | Meaning |
|---|---|
| `rescue_heavy` | Quantifiable rescue count exceeds quantifiable detected count, but durable detected support remains. |
| `high_backfill_dependency` | Low detected support plus dominant backfill; in the single-`dR` extreme case this blocks primary promotion. |
| `weak_seed_backfill_dependency` | Dominant single-`dR` backfill whose detected seeds fail the production seed-quality floor; this blocks primary promotion. |
| `duplicate_claim_pressure` | Some cells lost area ownership, but the winning row still has durable support. |
| `anchored_single_detected` | Anchor exists but quantifiable detected support is narrow. |
| `low_present_rate` | Present rate is low but row identity is still supported. |

Soft flags must be visible in `alignment_review.tsv` and workbook Audit/Review.

## Family Winner Policy (Phase A2)

Near-duplicate families should be resolved before final matrix export whenever
they compete for the same plausible row identity.

This spec owns the intended policy, but the first implementation phase should
not half-implement family competition while introducing the weak-row promotion
gate. Phase A must first report the blast radius of the strict row-identity gate
and make production output consume the same identity decision everywhere. Phase
A2 may implement family winner selection after the 8-RAW and 85-RAW reports show
which competing families remain problematic.

Family competition should use the existing claim-registry outcome plus row-level
evidence:

1. group compatible families by neutral-loss tag, m/z window, RT window, product
   m/z / observed neutral-loss compatibility, and overlapping ownership claims;
2. choose the winner using durable identity support first;
3. use quantifiable detected count before quantifiable rescue count;
4. use duplicate claim winner state before raw area size;
5. keep losers in Audit/Review with `audit_family` decision and loser reason.

This is a row-identity policy, not a feature-filtering policy. It must not
delete diagnostic candidates.

## Retention-Time Drift And Normalized RT Evidence

Cui et al. 2018, "Normalized Retention Time for Targeted Analysis of the DNA
Adductome", is directly relevant to the drift behavior observed in this project.
The paper's key engineering lesson is not to loosen RT identity windows. The key
lesson is to map RT into a reference-normalized coordinate before using RT as
identity evidence across changing chromatographic conditions.

Implementation status correction: commit `48a5b1b` did not implement this
normalized RT diagnostic. A first diagnostic now exists at
`tools/diagnostics/analyze_rt_normalization_anchors.py`. The current production
alignment code can still only use targeted ISTD RT trends and injection-order
rolling medians as drift evidence for owner-edge scoring; normalized RT is not
yet a production promotion rule.

For this project, that suggests a diagnostic layer before any production
algorithm change:

```text
raw RT per sample/run
  -> anchor RT model from stable reference nucleosides / ISTDs / canonical rows
  -> normalized RT or predicted RT residual
  -> identity and drift review evidence
```

The paper uses canonical nucleosides as shared RT references for targeted DNA
adductomics. The same concept can be adapted here if the anchors are actually
observable in the current run. Candidate anchors include:

- canonical nucleosides when present in the method/output;
- DNA ISTDs that pass the targeted benchmark;
- high-confidence recurring untargeted families after identity consolidation.

This must start as a diagnostic, not a hidden promotion rule. The diagnostic
should report:

- anchor availability per RAW/sample;
- fitted RT transform quality;
- residual RT error per anchor;
- whether family RT disagreement improves in normalized RT space;
- families whose raw RT fails but normalized RT supports a common identity;
- families whose normalized RT still conflicts and should remain split/audit.

Current diagnostic outputs:

```text
output\diagnostics\phase_o_rt_normalization_piecewise_8raw_20260514
output\diagnostics\phase_o_rt_normalization_piecewise_85raw_20260514
output\diagnostics\phase_p_rt_normalization_injection_local_85raw_20260514
```

The first robust/piecewise trial is promising but not production-ready:

- 8-RAW: `PASS`, complete active DNA ISTD anchor coverage, 2 excluded anchor
  observations, median RT-range improvement about `+0.062 min`.
- 85-RAW existing preconsolidation output: `WARN`, complete active DNA ISTD
  anchor coverage, 23 excluded anchor observations, 20 of them `d3-N6-medA`,
  median RT-range improvement about `-0.083 min`.
- 85-RAW with injection-order-aware local references: `PASS`, all 85 samples
  modelled, 2 excluded anchor observations, median RT-range improvement about
  `+0.013 min` overall and `+0.021 min` on primary families.

The existing project already used injection order in `drift_evidence.py` for
targeted ISTD drift evidence. The first normalized RT diagnostic did not. The
new `injection-local-median` reference source closes that gap for diagnostics.

Treat normalized RT as review evidence until per-family positive improvement
gates prove clear benefit. The current evidence supports injection-local iRT as
a scoring input candidate, not as an unconditional production promotion rule.

2026-05-15 diagnostic v2 update:

- `tools/diagnostics/analyze_rt_normalization_anchors.py` now also emits
  `rt_normalization_leave_one_anchor_out.tsv`.
- The JSON payload includes `leave_one_anchor_out` and `rt_band_summary` for
  anchor prediction quality and RT-band-specific improvement/worsening review.
- `rt_normalization_families.tsv` includes diagnostic-only fields:
  `rt_band`, `normalized_rt_support`, `anchor_scope`, `anchor_support_level`,
  and `local_residual_window_min`.
- `tools/diagnostics/alignment_decision_report.py` can render this artifact via
  `--rt-normalization-json` as an optional `RT Warping Evidence` section.
- These fields are review/annotation evidence only. They are not primary matrix
  promotion gates and do not change fixed alignment tolerances by themselves.

Important boundary:

- The paper's multi-minute prediction window is for scheduled acquisition across
  chromatographic settings. It must not be copied as a final identity tolerance.
- Existing strict targeted ISTD benchmark thresholds remain the near-term
  production validation gate.
- Normalized RT evidence can become a row-identity input only after it is shown
  to improve 8-RAW/85-RAW benchmark behavior without increasing SPLIT or false
  positive rows.

## Required Output Fields

`alignment_review.tsv` should expose row identity decisions in addition to the
current production counts.

Required fields:

- `include_in_primary_matrix`;
- `identity_decision` (`production_family`, `provisional_discovery`, or
  `audit_family`);
- `identity_confidence` (`high`, `medium`, `review`, `none`);
- `primary_evidence`;
- `identity_reason`;
- `quantifiable_detected_count`;
- `quantifiable_rescue_count`;
- `review_rescue_count`;
- `duplicate_assigned_count`;
- `ambiguous_ms1_owner_count`;
- `row_flags`.

`accepted_cell_count` may remain as the existing post-row-gate primary matrix
cell count. It must not be used as a synonym for pre-row-gate quantifiable
detected or rescue support.

The primary matrix does not need identity fields. The audit/review surface does.

## Validation Strategy

### Unit/Contract Tests

Required behavior tests:

1. row identity and production cell output consume the same shared cell-quality
   decisions.
2. `single_sample_local_owner` with one detected cell and multiple rescues is
   `provisional_discovery` by default and excluded from the primary matrix.
3. `owner_complete_link`, `cid_nl_only`, or multi-sample detected support with
   at least two quantifiable detected cells remains production.
4. rescue-only rows remain audit-only even when rescued areas are high quality.
5. duplicate-only rows remain audit-only.
6. rows with quantifiable rescue plus no quantifiable detected cell remain
   audit-only.
7. rows with quantifiable detected support plus many quantifiable rescues remain
   production with `rescue_heavy`.
8. anchored single-detected families are `provisional_discovery` in Phase A.
9. `alignment_matrix.tsv` and workbook `Matrix` use the identity decision layer.
10. `alignment_review.tsv` reports identity decision fields.
11. guardrails count production families from identity decisions, not raw status
   counts.
12. targeted ISTD benchmark output includes identity decision/reason for every
    matched or missing candidate.
13. preflight blast-radius diagnostics fail clearly when required alignment TSV
    columns are missing instead of silently approximating cell quality.

### Real-Data Gates

Use the same validation surfaces as the existing untargeted work:

0. Preflight blast-radius report on the latest comparable 8-RAW and 85-RAW
   outputs before changing production behavior, joined to targeted benchmark
   matches when active ISTD stop conditions are evaluated.
1. 8-RAW validation-fast run with `--emit-alignment-cells`.
2. Strict targeted ISTD benchmark against the run-matched targeted workbook:
   `xic_results_20260512_1151.xlsx` for 8-RAW and
   `xic_results_20260512_1200.xlsx` for 85-RAW. Identity decision and rejection
   reason should be available in the benchmark or its joined diagnostics.
3. Targeted checkpoint audit for `5-medC` and `5-hmdC`.
4. 85-RAW comparison focused on:
   - production family count;
   - zero-present production families;
   - duplicate-only production families;
   - high-backfill production families;
   - targeted ISTD benchmark deltas.
5. RT-drift diagnostic, if implemented:
    - anchor count by sample;
    - RT transform fit quality;
    - raw RT versus normalized RT residual distributions;
    - effect on SPLIT/MISS classifications for targeted ISTDs.
   Current diagnostic also reports per-family raw vs normalized RT range and
   range improvement.

The expected direction is fewer weak production rows, not exact equality with
the old pipeline.

## Non-Goals

- Do not tune mz/RT thresholds in this work.
- Do not introduce multi-tag discovery.
- Do not use targeted labels as production identity rules.
- Do not remove Audit/Review candidates.
- Do not make old-pipeline sparsity the success definition.
- Do not add DNP/MA behavior changes in this spec.

## Acceptance Criteria

An implementation satisfies this spec when:

1. Row promotion is owned by one explicit identity decision layer.
2. `single_sample_local_owner` no longer enters the primary matrix by itself.
3. rescue/backfill cannot create row identity.
4. duplicate-only and zero-present families cannot become primary matrix rows.
5. rescue-heavy but identity-supported rows can remain production with flags.
6. primary matrix output and workbook Matrix both use the same identity decision.
7. Audit/Review keeps every candidate and explains every provisional or
   audit-only row.
8. guardrails consume identity decision fields when available.
9. 8-RAW targeted ISTD gate does not regress.
10. 85-RAW weak-row counts move in the intended direction without hiding
    diagnostic evidence.
11. Phase A explicitly defers family winner selection unless the implementation
    includes a separate tested Phase A2.

## Relationship To Existing Specs

This spec refines:

- `docs/superpowers/specs/2026-05-11-ms2-constrained-ms1-feature-family-spec.md`
- `docs/superpowers/specs/2026-05-11-sample-local-ms1-ownership-drift-aware-alignment-spec.md`
- `docs/superpowers/specs/2026-05-13-untargeted-final-matrix-and-rescue-evidence-spec.md`

It does not replace the cell-level final matrix contract. It adds the missing
row-identity promotion contract above it.
