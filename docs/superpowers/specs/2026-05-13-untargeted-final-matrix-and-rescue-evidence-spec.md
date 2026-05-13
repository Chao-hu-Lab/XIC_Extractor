# Untargeted Final Matrix And Rescue Evidence Spec

**Date:** 2026-05-13
**Status:** Draft for implementation planning
**Branch:** `codex/untargeted-discovery-v1-implementation`
**Worktree:** `C:\Users\user\Desktop\XIC_Extractor\.worktrees\untargeted-discovery-v1-implementation`

## Summary

The final untargeted deliverable should look like the old unfiltered pipeline
matrix: feature rows by sample columns, with quantitative area values or blanks.

The old pipeline's missing values must not be treated as ground-truth absence.
Filtered matrix and targeted workbook checks show that even internal standards
can be missed by the old workflow. The new workflow should keep higher
sensitivity and stronger rescue behavior, but it must separate final
quantification from diagnostic state.

Core rule:

```text
Final matrix = accepted quantitative values only.
Diagnostics = how each value was detected, rescued, rejected, duplicated, or reviewed.
```

## Evidence Behind This Spec

### Old Matrix Shape Is Still The Desired Product Shape

The old unfiltered pipeline output is the expected final presentation style:

```text
feature coordinate columns + sample intensity columns
```

Cells are values or blanks. Users should not need to read alignment status
strings to use the matrix.

### Old Missing Values Are Not Ground Truth

The filtered matrix marks six red-font internal-standard rows. Two of them
show meaningful missingness in the old pipeline:

| Old row | Targeted identity | Old filtered matrix missing | Targeted method result |
|---|---|---:|---|
| `245.1332/12.28` | `d3-5-medC` | 5 sample gaps | all 5 are present, `HIGH`, `NL ok` |
| `261.1283/8.97` | `d3-5-hmdC` | 11 sample gaps | all 11 are present, `HIGH`, `NL ok` |

This means old-pipeline blanks include false missing values caused by weak
extraction/alignment/rescue behavior.

This evidence must be converted into a reproducible validation fixture before
implementation. The fixture should be a small CSV/TSV or spec table that records:

- source workbook path and worksheet for the old matrix observation;
- source workbook path and worksheet for the targeted result observation;
- old row coordinate and targeted identity;
- old-missing sample IDs;
- targeted result rows for the same sample IDs;
- the exact targeted fields used as evidence, such as detection grade and
  neutral-loss/pass flag;
- the matching rule used to connect old row coordinate, targeted identity, and
  sample identity.

Therefore:

- old matrix sparsity is not an acceptance target;
- a higher-rescue matrix is not inherently worse;
- validation must ask whether rescued values are supported, not whether there
  are many rescued values.

## Product Contract

### Production Workbook

The production workbook should contain a first-class matrix sheet matching the
legacy handoff shape.

Preferred production sheet shape:

```text
Mz | RT | sample_1 | sample_2 | ... | sample_n
```

Legacy-compatible alternative:

```text
Mz/RT | sample_1 | sample_2 | ... | sample_n
```

The production matrix may include a `SampleInfo` sheet when available. It must
not require debug TSVs to be usable.

The production matrix must not contain these strings in sample cells:

- `detected`
- `rescued`
- `duplicate_assigned`
- `ambiguous_ms1_owner`
- `absent`
- `unchecked`

Sample cells contain only:

- accepted numeric area values;
- blank for any non-accepted, non-quantified, missing, duplicate-loser, or
  review-only state.

### Primary Matrix Row Inclusion

Cleaning sample cells is not enough. The primary final matrix must also exclude
rows that contain no accepted quantitative evidence.

A feature-family row may appear in the primary final matrix only when both are
true:

1. at least one sample cell writes an accepted numeric area value;
2. row-level identity support passes the rules in this spec and the related
   owner/drift specs.

Rows must not appear in the primary final matrix when they are:

- all blank after production-cell filtering;
- review-only rescue candidates;
- rejected-rescue-only candidates;
- duplicate-loser-only candidates;
- `identity_anchor_lost` rows without a passing identity review.

Those rows still belong in review/audit outputs. If an implementation offers an
all-candidates export, it must be clearly named as diagnostic and must not be
the primary user-facing matrix.

### Diagnostics And Validation Outputs

Diagnostic outputs remain required for development and review, but they are not
the final user-facing matrix.

Diagnostics may contain:

- per-cell status;
- detected versus rescued origin;
- rescue evidence tier;
- RT delta and drift-corrected RT delta;
- peak quality evidence;
- scan support;
- claim-registry winner/loser;
- duplicate pressure;
- row-level warning/review flags.

These belong in `alignment_cells.tsv`, `alignment_matrix_status.tsv`,
`alignment_review.tsv`, review HTML, or hidden/audit workbook sheets, not in the
primary intensity matrix.

The production workbook must include at least one audit/review sheet carrying
the diagnostic reason behind each blank or accepted rescue. External TSV/HTML
files may provide deeper review surfaces, but they must not be the only place
where a user can understand why a production cell is blank.

The in-workbook audit sheet must include enough fields to trace each production
decision:

- feature identifier or `Mz`/`RT` coordinate;
- sample identifier;
- raw cell status;
- rescue tier when applicable;
- whether the primary matrix cell was written;
- blank reason when the primary matrix cell is blank;
- claim-registry winner/loser state when applicable;
- row-level review flags.

## Rescue Semantics

`rescued` is not a failure state. It means the old discovery/MS2 event did not
produce a sample-local detected cell, but MS1 re-extraction found a candidate
peak for an already established feature family.

Given the internal-standard evidence above, rescue is scientifically necessary.
The implementation must not suppress rescue just to mimic old-pipeline
sparsity.

The needed change is rescue grading.

### Rescue Tiers

Use explicit tiers in diagnostics.

| Tier | Meaning | Production matrix cell |
|---|---|---|
| `accepted_rescue` | MS1 peak is good enough to quantify for an already supported feature family. | write area |
| `review_rescue` | peak exists but identity or quality evidence is incomplete. | blank by default; visible in review |
| `rejected_rescue` | peak is too weak, duplicated, contradictory, or ambiguous. | blank |

The exact score thresholds belong in the implementation plan, but the evidence
categories are part of this spec:

- RT agreement with raw and drift-corrected family center;
- peak shape / continuity / scan support;
- local signal-to-noise or prominence;
- duplicate claim status;
- whether the family still has row-level identity support;
- whether nearby competing owners make the assignment ambiguous.

### Detected And Rescued Are Different But Both Can Quantify

`detected` should continue to mean original discovery/MS2 evidence exists for
that sample-feature cell.

`accepted_rescue` can still write an area value, but it must remain traceable as
rescued in diagnostics.

The final matrix intentionally hides this distinction from the main sample
cells. The diagnostic layer preserves it.

## Row-Level Identity Support

Feature-family rows must not be created or merged by rescued cells alone.

Rows need row-level identity support from detected owner evidence:

- sample-local owner evidence;
- neutral-loss/product compatibility;
- drift-aware owner edge evidence when applicable;
- supporting repeated events or tail events when they map to the same MS1 owner.

After claim registry, a row may lose some quantitative cells to duplicate
assignment. This does not automatically invalidate the row. However, a row whose
final accepted matrix cells are all rescued needs explicit review unless the
implementation can prove that row-level identity support remains valid and not
stolen by another family.

This state should be called out separately from ordinary high rescue rate.

Suggested diagnostic flags:

| Flag | Meaning |
|---|---|
| `rescue_heavy` | accepted rescued cells exceed detected cells, but detected support remains. |
| `rescue_only_review` | production candidates remain but no final detected cell remains after claim registry. |
| `duplicate_claim_pressure` | one or more cells lost quantitative ownership to another family. |
| `identity_anchor_lost` | all originally detected quantitative cells became duplicate losers or review-only cells. |

`rescue_heavy` is not automatically a failure. `rescue_only_review` and
`identity_anchor_lost` are not final acceptance failures by definition, but they
must not be silently hidden.

## Guardrail Changes

The current guardrail `high_backfill_dependency_families` is too blunt if it
means "rescued > detected". In this dataset, that can simply mean the new method
is recovering false missing values that the old pipeline failed to detect.

Replace or split it into more informative metrics:

| Metric | Purpose |
|---|---|
| `accepted_rescue_rate` | how much of the final matrix comes from accepted rescue |
| `review_rescue_count` | how many rescue candidates were kept out of the final matrix |
| `rescue_only_review_families` | rows with no final detected cell but rescued candidates exist |
| `identity_anchor_lost_families` | rows whose detected support was lost to duplicate claims |
| `duplicate_claim_pressure_families` | rows affected by shared MS1 peak claims |
| `negative_checkpoint_production_families` | known negative fixture should not become accepted production |
| `istd_false_missing_recovery` | internal-standard old-missing cells recovered by the new method |

The guardrail should not fail a run solely because many cells are rescued.

It should fail or require review when:

- rescued values become accepted without peak/RT/claim evidence;
- weak or duplicate-conflicted rescue writes area into the final matrix;
- negative checkpoint features become accepted production rows;
- a row has no valid identity support but still writes production values.

## Validation Fixtures

Targeted results are validation fixtures, not production label rules.

Use the targeted workbook to evaluate whether the untargeted method recovers
signals that old untargeted/metabCombiner output missed.

Required validation checks:

1. Internal-standard recovery check
   - `d3-5-medC` at approximately `245.1332/12.28`
   - `d3-5-hmdC` at approximately `261.1283/8.97`
   - Old filtered-matrix missing samples should not be interpreted as true
     absence when targeted says `HIGH` and `NL ok`.
   - The implementation plan must define the exact m/z tolerance, RT tolerance,
     and sample-name mapping used for this check. Tests must fail if these
     matching parameters are implicit.

2. Positive checkpoint recovery
   - `5-medC`
   - `5-hmdC`
   - Count accepted detections/rescues separately.

3. Negative checkpoint protection
   - `8-oxodG`
   - No target-label exception may create an accepted untargeted production row.

4. Output-surface check
   - primary final matrix contains numeric values or blanks only;
   - status strings appear only in diagnostics.
   - primary final matrix excludes all-blank, review-only, rejected-only,
     duplicate-loser-only, and unresolved `identity_anchor_lost` rows.

## Non-Goals

This spec does not define feature filtering.

This spec does not say the final matrix should become sparse like the old
pipeline.

This spec does not allow target labels to become production identity rules.

This spec does not remove debug/status TSVs. It moves them out of the primary
user-facing matrix.

This spec does not force an immediate threshold for accepted rescue. Thresholds
must be written in the implementation plan with tests and real-data validation.

## Acceptance Criteria

A future implementation satisfies this spec when:

1. The production matrix has the legacy-style intensity shape.
2. Production sample cells contain only numeric area values or blanks.
3. `detected` and `accepted_rescue` can both write numeric values.
4. `review_rescue`, `rejected_rescue`, `duplicate_assigned`,
   `ambiguous_ms1_owner`, `absent`, and `unchecked` write blanks.
5. Diagnostics preserve the original status and rescue tier for every cell.
6. Old-pipeline missing internal-standard cells are evaluated against targeted
   evidence and not treated as absence ground truth.
7. Guardrails distinguish rescue recovery from orphaned or duplicate-conflicted
   rescue.
8. Negative targeted checkpoints remain validation-only and do not become
   production exceptions.
9. The primary final matrix excludes rows with no accepted quantitative cell.
10. The production workbook includes an audit/review sheet explaining accepted
    rescues and blank production cells.
11. Validation fixtures make old-missing sample IDs, targeted evidence fields,
    tolerance values, and sample-name mapping explicit.

## Relationship To Existing Specs

This spec refines:

- `docs/superpowers/specs/2026-05-11-untargeted-alignment-output-contract.md`
- `docs/superpowers/specs/2026-05-11-sample-local-ms1-ownership-drift-aware-alignment-spec.md`
- `docs/superpowers/specs/2026-05-13-untargeted-duplicate-drift-soft-edge-design.md`

It does not replace their ownership or drift-edge rules. It clarifies that final
matrix presentation should be clean and legacy-shaped, while high-sensitivity
rescue remains necessary and must be graded rather than broadly penalized.
