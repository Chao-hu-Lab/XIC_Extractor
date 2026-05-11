# Sample-Local MS1 Ownership and Drift-Aware Alignment Spec

## Summary

Untargeted discovery/alignment should move from an MS2-event-first model to a
sample-local MS1 peak ownership model.

The core contract is:

```text
Within each RAW file, MS1 chromatographic peaks own quantitation.
MS2/NL events explain and constrain those MS1 peaks.
Cross-sample alignment aligns MS1 peak instances under MS2/NL constraints.
Production output should expose one row per aligned MS1 feature, not one row per
MS2 trigger.
```

This spec is a direction correction for the untargeted pipeline. It also marks
several current surfaces as development/debug-only candidates so they can be
removed or hidden from production defaults later.

## Motivation

Real 8-RAW inspection showed four important cases:

| Case | Observation | Design implication |
|---|---|---|
| Case 1, m/z 242.114 | Same chemical-looking MS1 feature drifts by sample class, and multiple MS2 events can point to the same sample-local MS1 peak. | RT drift must be modeled after sample-local ownership, not by forcing one fixed RT window. |
| Case 3, m/z 322.143 | Similar class-linked RT drift appears in another feature. | Cross-sample alignment needs drift-aware grouping, constrained by MS1 ownership and MS2/NL compatibility. |
| Case 4, m/z 251.084 | Many NL/MS2 events sit on the same MS1 peak/tail region. | Duplicate removal is not a special case; MS2 triggers on a peak tail should become evidence/detail of one MS1 feature. |
| Case 2, m/z 296.074 | Doublet/multipeak regions can make ownership ambiguous. | v1 should label ambiguity instead of pretending every close signal is safely resolvable. |

The current implementation partially handles duplicate ownership after
alignment, but it does not use the strongest local evidence early enough:

```text
multiple candidates in the same RAW file resolving to the same MS1 apex/window
```

That evidence should define sample-local MS1 feature instances before
cross-sample production rows are finalized.

## Problem Statement

The current direction has several failure modes:

- MS2 event rows can survive as separate production rows even when they point to
  the same sample-local MS1 peak.
- RT drift can make the same feature appear as different families across sample
  classes.
- Near-duplicate folding is too late in the pipeline and risks becoming a stack
  of special cases.
- Development/debug outputs can look like production surfaces, increasing UX
  cost and user confusion.
- Some current logic is closer to FH-style event alignment than the intended
  XIC-first method.

The desired method should not copy FH's weakness:

```text
FH: MS2 trigger/event first, then downstream tools try to clean duplicates.
XIC untargeted: MS1 peak ownership first, then MS2 events explain that peak.
```

## Core Definitions

| Term | Meaning |
|---|---|
| MS2 event candidate | One strict NL/product evidence event from one RAW file, with precursor/product/observed loss and local MS1 extraction evidence. |
| Sample-local MS1 peak instance | One chromatographic MS1 peak in one RAW file, represented by m/z, apex RT, peak start/end, area, and member MS2 event candidates. |
| MS1 peak ownership | The rule that a sample-local MS1 peak area can be owned by only one production feature cell. |
| Supporting MS2 event | An MS2 event candidate assigned to an already-owned MS1 peak instance; it supports identity/detail but does not create a new production row. |
| Ambiguous MS1 region | A local trace region where multiple peaks, shoulders, or tails make ownership uncertain. Ambiguous regions are retained for debug/review rather than aggressively collapsed. |
| Drift-aware alignment | Cross-sample grouping that allows retention-time movement across sample class or injection behavior while preserving MS1 ownership and MS2/NL compatibility. |

## V1 Scope Locks

The first implementation must be conservative. These locks prevent the method
from drifting back into mz/RT-only or event-only alignment:

- V1 uses exact `neutral_loss_tag` equality only. Do not merge across
  "compatible NL families" until a real NL-family config/table exists with
  tests.
- V1 sample-local MS1 ownership is not gated by `neutral_loss_tag`. Ownership
  is chromatographic. `neutral_loss_tag` constrains cross-sample identity and
  production grouping.
- V1 does not depend on sample class metadata. Tumor/Normal/Benign/QC-linked RT
  drift is an observed phenomenon, not an input contract.
- V1 must not merge by broad RT proximity alone. Wider RT tolerance is allowed
  only after sample-local MS1 ownership and MS2/NL compatibility are satisfied.
- V1 must not use rescued/backfilled overlap as identity proof.
- V1 must not let rescued/backfilled cells seed, bridge, or expand alignment
  groups or RT drift relationships.
- V1 must not require HCD/full-fragment pattern matching for CID datasets.

## Algorithm Contract

### Layer 1: Candidate Generation

Discovery still starts from strict NL/product events.

Allowed evidence:

- neutral loss tag
- precursor m/z
- product m/z
- observed neutral loss
- MS2 seed RT
- MS1 XIC around the event
- MS1 peak apex/start/end/area when available

Candidate generation may be sensitive. More candidates are acceptable at this
stage because cleanup should happen through ownership, not by suppressing
potential evidence too early.

### Layer 2: Sample-Local MS1 Peak Ownership

Before cross-sample production alignment, candidates from the same RAW file must
be grouped into sample-local MS1 peak instances.

Ownership is chromatographic. Two candidates in the same sample may share one
MS1 peak instance even when their MS2/NL evidence differs.

Two candidates in the same sample should share one MS1 peak instance when:

```text
precursor m/z is compatible
their resolved MS1 peak windows overlap enough
their apex RTs are close or one seed is on the other's peak shoulder/tail
```

MS2/NL evidence must be attached to the owner as identity evidence, not used to
split sample-local ownership by default.

The strongest v1 signal is exact resolved peak identity:

```text
same sample + same resolved MS1 apex/window -> same MS1 peak instance
```

Implementation requirement:

```text
The ownership stage must re-extract or otherwise own stable MS1 peak boundaries.
It must not rely on candidate CSV peak_start/peak_end columns being populated.
```

The current candidate CSV may contain empty `ms1_peak_start_rt` /
`ms1_peak_end_rt`. A valid implementation must therefore produce ownership
evidence from the RAW/XIC trace or a focused intermediate model with:

- `owner_apex_rt`
- `owner_peak_start_rt`
- `owner_peak_end_rt`
- `owner_area`
- assigned MS2 event ids
- assignment reason

V1 named gates:

| Gate | Meaning | V1 source |
|---|---|---|
| `owner_precursor_ppm` | Maximum precursor m/z distance for candidates to compete for one local owner. | `AlignmentConfig.max_ppm` unless a narrower ownership config is introduced. |
| `owner_exact_apex_match` | Candidates resolved to the same `owner_apex_rt` within the trace sampling precision. | Re-extracted XIC owner model. |
| `owner_window_overlap_fraction` | Intersection of peak windows divided by the shorter window. | Named constant/config in implementation plan; test boundary required. |
| `owner_apex_close_sec` | Maximum apex delta for same-owner candidates when windows overlap. | Named constant/config in implementation plan; test boundary required. |
| `owner_tail_assignment` | Event seed lies on a monotonic shoulder/tail of the dominant owner peak and does not create another local maximum. | Re-extracted XIC owner model. |
| `owner_multiplet_ambiguity` | Multiple local maxima or low valley separation makes ownership unsafe. | Re-extracted XIC owner model. |

Rules:

- One MS1 peak instance owns one area value per sample.
- Multiple MS2 events on the same peak become supporting events.
- Supporting events must remain available in debug/detail output.
- A peak tail event should not create a separate production row when the MS1
  evidence clearly belongs to the same peak.
- Ambiguous doublet/multipeak regions should be marked `ambiguous_ms1_owner`
  rather than over-collapsed.
- A single owner id must not contribute its quantified area to multiple
  production cells.

### Layer 2b: Owner Identity Evidence

Each sample-local MS1 owner carries MS2/NL evidence sets.

V1 owner identity model:

| Field | Meaning |
|---|---|
| `primary_identity_event` | The best MS2/NL event attached to the owner for cross-sample identity. |
| `supporting_events` | Other MS2/NL events assigned to the same owner. |
| `identity_conflict` | Set when supporting events disagree in a way v1 cannot safely reconcile. |

`primary_identity_event` selection should be deterministic and testable. The
implementation plan must define the winner key, for example highest evidence
score, then stronger MS1 support, then lower RT, then candidate id.

Cross-sample production grouping uses owner-level identity evidence. It must not
clone one sample-local area into multiple production rows just because one owner
has multiple MS2 events.

### Layer 3: Cross-Sample Alignment

Cross-sample alignment should align sample-local MS1 peak instances, not raw MS2
event candidates.

Required constraints:

- exact `neutral_loss_tag` match in v1
- compatible precursor m/z
- compatible product m/z and observed neutral loss
- no known MS2 pattern conflict
- plausible RT relationship after allowing drift

RT drift must be treated as real:

- Same feature can shift by sample class, matrix, injection behavior, or method
  drift.
- RT windows should not be so strict that class-linked drift splits one feature.
- RT windows should not be so loose that unrelated isomers are merged.

In v1, drift-aware alignment can be conservative:

```text
Use wider RT candidates only when MS1 ownership is clean and MS2/NL evidence is
compatible. Otherwise mark review/ambiguous.
```

Hard rule:

```text
Broad RT proximity can nominate candidates for comparison, but it cannot be the
reason they merge.
```

An aligned feature that spans large RT drift must be explainable by:

- sample-local MS1 owners that are internally clean;
- exact NL tag agreement;
- precursor/product/observed-loss compatibility; and
- no known MS2 pattern conflict.

V1 cross-sample named gates:

| Gate | Meaning | V1 source |
|---|---|---|
| `identity_neutral_loss_tag` | Exact canonical tag match. | Discovery config, normalized non-empty string. |
| `identity_precursor_ppm` | Owner precursor center distance. | `AlignmentConfig.max_ppm`, with preferred/max tiers allowed. |
| `identity_product_ppm` | Primary identity event product m/z distance. | `AlignmentConfig.product_mz_tolerance_ppm`. |
| `identity_observed_loss_ppm` | Primary identity event observed neutral-loss distance. | `AlignmentConfig.observed_loss_tolerance_ppm`. |
| `identity_rt_candidate_window_sec` | Wide RT window used only to nominate comparisons. | Named config/constant in implementation plan. |
| `identity_drift_edge` | A detected owner-to-owner edge supported by clean MS1 owners and MS2/NL compatibility. | Detected owners only. |
| `cid_ms2_conflict` | CID v1 has no full pattern match; conflict only exists when tags/product/observed loss are incompatible or future signature data explicitly disagrees. | CID/NL evidence model. |

`neutral_loss_tag` behavior:

- Tags must be normalized to a canonical non-empty string before comparison.
- Missing or unknown tags may remain in debug candidates.
- Missing or unknown tags must not participate in production cross-sample
  alignment in v1.
- Numeric observed-loss tolerance must not substitute for exact tag equality in
  v1.

Rescued/backfilled rule:

```text
Only MS2-backed detected owners can create alignment edges and define RT drift.
Rescued cells can fill an already-created anchored feature group, but cannot
establish identity, bridge two groups, or expand the drift window.
```

If multiple local MS1 owners fit a rescue target, the cell must remain blank and
be marked `ambiguous_ms1_owner` or `unchecked`; it must not pick one by area
alone.

### Layer 4: Production Matrix

Production matrix rows represent aligned MS1 features.

Production cells:

| Cell status | Matrix value | Meaning |
|---|---|---|
| detected | area | Sample has original MS2 event evidence and a valid MS1 owner. |
| rescued | area | Sample lacks original MS2 event evidence but has a valid MS1 backfill tied to an anchored feature. |
| absent | blank | Checked and no acceptable MS1 peak was found. |
| unchecked | blank | Not eligible or trace could not be evaluated. |
| duplicate_assigned | blank | MS1 peak is owned by another production feature; keep detail/debug evidence. |
| ambiguous_ms1_owner | blank by default | Region is not safe to collapse or quantify automatically. |

Blank remains the production representation for missing, unchecked, duplicate,
and ambiguous cells. Do not encode absence as zero.

Status semantics:

| Cell status | Checked? | Present? | Counts as absent? | Preserved in debug/status output? |
|---|---:|---:|---:|---:|
| detected | yes | yes | no | yes |
| rescued | yes | yes | no | yes |
| absent | yes | no | yes | yes |
| unchecked | no | no | no | yes |
| duplicate_assigned | yes | no | no | yes |
| ambiguous_ms1_owner | yes | no | no | yes |

`ambiguous_ms1_owner` means the trace was inspected enough to know that the
region is unsafe for automatic ownership. It is checked-but-not-quantified.

Ambiguity decision table:

| Situation | Production row behavior | Cell status | Matrix value | Review/HTML disclosure |
|---|---|---|---|---|
| One owner group has one ambiguous sample cell. | Emit the production feature row. | `ambiguous_ms1_owner` for that sample. | blank | Count in `ambiguous_ms1_owner_count`; warning/reason required. |
| All candidate evidence for a would-be feature is ambiguous and has no clean detected owner. | Do not promote to production by default. Keep debug/detail. | debug-only ambiguous records | blank | Debug summary only. |
| Two resolved local MS1 peaks are separated by clear valley/local maxima. | Emit separate owners if identity evidence supports both, otherwise one production owner plus debug ambiguous evidence. | detected/rescued or `ambiguous_ms1_owner` | area only for safe owners | Warning if split was caused by ambiguity. |
| Same dominant apex/window with shoulder/tail events. | Emit one production owner. | detected/rescued for owner, supporting events in detail. | owner area | Optional supporting-event count. |

Production review/HTML must expose checked-but-not-quantified states at row or
summary level:

- `duplicate_assigned_count`
- `ambiguous_ms1_owner_count`
- `checked_count`
- deterministic warning/reason text

Per-event details may stay debug-only, but production output must not make these
cells look like ordinary missing values.

### Layer 5: Debug and Development Detail

Detailed event-level evidence should remain available, but not as the default
production surface.

Debug/detail outputs may include:

- event candidate table
- event-to-MS1-owner assignment table
- ambiguous owner table
- MS2 event counts per MS1 feature
- duplicate/assigned event reason
- optional raw trace snapshots or HTML visualization

These surfaces are for method development and troubleshooting. They should not
compete with the production matrix as the main user-facing deliverable.

## Decision Table

```text
+----------------+----------------+----------------+----------------+------------------+
| Same sample    | Same MS1 apex/  | MS2/NL no      | Region clear   | Production result|
| candidates     | window          | conflict       |                |                  |
+----------------+----------------+----------------+----------------+------------------+
| yes            | yes            | yes            | yes            | one MS1 owner    |
| yes            | yes            | yes            | no             | ambiguous owner  |
| yes            | yes            | no             | any            | split/review     |
| yes            | no, overlap    | yes            | yes            | one MS1 owner if |
|                | on shoulder    |                |                | shoulder/tail    |
| yes            | no             | yes            | doublet        | ambiguous owner  |
| yes            | no             | no             | any            | separate         |
| no             | n/a            | yes            | clean          | cross-sample     |
|                |                |                |                | alignment can    |
|                |                |                |                | compare owners   |
+----------------+----------------+----------------+----------------+------------------+
```

## Production Output Contract

This spec follows
`docs/superpowers/specs/2026-05-11-untargeted-alignment-output-contract.md`.

Production default:

```text
alignment_results.xlsx
review_report.html
```

Machine/validation outputs:

```text
alignment_matrix.tsv
```

Debug/development opt-in outputs:

```text
alignment_cells.tsv
alignment_matrix_status.tsv
event_candidates.tsv/csv
event_to_ms1_owner.tsv
ambiguous_ms1_owners.tsv
debug HTML or raw trace snapshots
```

The algorithm contract is:

- One production row per aligned MS1 feature.
- Supporting MS2 events do not create extra production rows.
- Extra detail must be traceable but not forced into the first screen.

Migration from current CLI outputs:

- Current TSV-first outputs are staging surfaces.
- Production readiness requires output levels:
  - `production`: XLSX + review HTML.
  - `machine`: production outputs plus `alignment_matrix.tsv`.
  - `debug`: machine outputs plus cells/status/event ownership detail.
- Tests must assert default artifact lists for each output level before changing
  CLI defaults.

## Overdesign and Extraction Candidates

Several current directions should be reclassified before the next production
push.

### Keep As Core

- strict NL/product event discovery
- sample-local MS1 peak extraction
- sample-local MS1 ownership
- MS2/NL-constrained cross-sample alignment
- MS1 backfill for anchored features
- production matrix with blank missing values

### Move To Debug / Development Opt-In

- event-level candidate CSV as a primary surface
- `alignment_cells.tsv` as a default output
- `alignment_matrix_status.tsv` as a default output
- verbose review fields that explain implementation internals instead of user
  decisions
- HTML views that repeat TSV/Excel text without adding visual evidence

### Revisit Or Remove

- near-duplicate folding as a late-stage patch if sample-local ownership can
  solve the same issue earlier
- warning labels whose action is unclear
- outputs that duplicate the same information without a different user job
- feature-family concepts that still behave like MS2 event families instead of
  MS1 peak owners

## Non-Goals

- Do not solve hard doublet/multipeak deconvolution in v1.
- Do not require HCD/full-fragment pattern matching for CID data.
- Do not make broad RT drift alone sufficient for merging.
- Do not remove debug outputs before the production matrix contract is stable.
- Do not force XLSX versus TSV in this algorithm spec.

## Acceptance Criteria For Future Implementation

- In one RAW file, multiple MS2 events resolving to the same MS1 apex/window
  produce one sample-local MS1 owner.
- The production matrix does not emit separate rows for peak-tail MS2 triggers
  on the same MS1 owner.
- Supporting MS2 events remain traceable in debug/detail output.
- RT drift across sample classes can be represented without splitting obvious
  same-feature cases like Case 1 and Case 3.
- Ambiguous doublet/multipeak cases like Case 2 are not aggressively collapsed.
- Case 4-like tail/event duplication is reduced before production output.
- Matrix missing/duplicate/ambiguous values remain blank, not zero.
- Any remaining extra production rows must be explainable as true MS1 peak
  separation, MS2/NL conflict, or ambiguity.

## Validation Set

Use the existing 8-RAW validation output and RAW inspection cases as the first
validation set:

- `case1_mz242_5medC_like`
- `case2_mz296_dense_duplicate`
- `case3_mz322_dense_duplicate`
- `case4_mz251_anchor_shadow_duplicates`

Expected qualitative outcomes:

- Case 1 and Case 3 should reduce event-row fragmentation while allowing
  sample-class RT drift.
- Case 4 should collapse or assign tail events under one MS1 owner instead of
  producing many production rows.
- Case 2 should remain review/ambiguous if the MS1 trace suggests true doublet
  or unresolved multiplet behavior.

Minimum executable gates for the implementation plan:

- Case 1 fixture: multiple same-sample events resolving to one MS1 apex/window
  must produce one owner and supporting events.
- Case 3 fixture: cross-sample RT drift must not split a clean same-feature
  owner group when NL/product/observed-loss evidence is compatible.
- Case 4 fixture: tail events on one MS1 peak must not create separate
  production rows.
- Case 2 fixture: unresolved doublet/multipeak ownership must produce
  `ambiguous_ms1_owner` or separate owners, not an unconditional merge.
- Negative fixture: same m/z/RT but different `neutral_loss_tag` must not merge
  in v1.
- Negative fixture: broad RT proximity without shared clean sample-local
  ownership must not merge.

Fixture manifest required in the implementation plan:

| Fixture | Input requirements | Expected owner/output contract |
|---|---|---|
| `case1_same_owner_with_class_drift` | At least two samples; same m/z/NL/product evidence; same-sample duplicate MS2 events resolving to one owner; cross-sample owner RTs shifted. | One owner per sample; one production feature row; supporting events retained; no duplicate production rows. |
| `case3_drift_without_event_fragmentation` | Clean owners across samples with RT spread larger than narrow event clustering but compatible primary identity events. | One production feature row; drift explained by detected owners; no rescued cell used as bridge. |
| `case4_tail_events_on_one_peak` | Several same-sample MS2 seeds on the dominant peak/tail with same precursor region. | One owner; tail events supporting/debug; production row count does not equal event count. |
| `case2_unresolved_doublet` | Two local maxima or low valley separation with events mapping to different maxima. | Separate safe owners or `ambiguous_ms1_owner`; no unconditional merge. |
| `negative_different_nl_tag` | Same m/z/RT owner candidates but different canonical `neutral_loss_tag`. | One sample-local owner may carry multiple events, but cross-sample production grouping must not merge identities by numeric loss alone. |
| `negative_rescued_bridge` | Two detected groups connected only by rescued/backfilled overlap. | Groups remain separate or review/ambiguous; rescued cells do not create identity edge. |

The implementation plan must list exact synthetic candidate ids, sample stems,
tags, m/z, RT windows, owner windows, expected owner count, expected production
row count, expected statuses, and pytest commands for these fixtures.

## Relationship To Existing Specs

This spec supersedes the direction of treating near-duplicate folding as the
main cleanup mechanism. Folding can remain an implementation tactic, but the
primary model should be sample-local MS1 ownership.

Related documents:

- `docs/superpowers/specs/2026-05-06-numofinder-inspired-ms2-evidence-and-discovery-spec.md`
- `docs/superpowers/specs/2026-05-09-untargeted-discovery-v1-spec.md`
- `docs/superpowers/specs/2026-05-11-ms2-constrained-ms1-feature-family-spec.md`
- `docs/superpowers/specs/2026-05-11-untargeted-alignment-output-contract.md`
