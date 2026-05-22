# Untargeted Identity Coherence Diagnostic Prototype Spec

**Date:** 2026-05-22
**Status:** Method review draft v0.3
**Branch:** `codex/untargeted-backfill-logic-reset`
**Worktree:** `C:\Users\user\Desktop\XIC_Extractor\.worktrees\untargeted-backfill-logic-reset`

---

## Summary

This spec keeps the correct abstraction boundary:

```text
identity formation first
Backfill / value recovery second
```

However, v0.2 had a methodological flaw: an RT-windowed peak search before
Backfill is still methodologically close to Backfill. It prevents leakage from
Backfill outputs, but it does not by itself prove identity quality.

V0.3 therefore changes the prototype question:

```text
Can pre-Backfill seed specificity plus independent per-sample trace identity
checks separate plausible untargeted identities from RT-coherent background or
rescue-heavy rows?
```

This is not a full rejection of the coherence diagnostic. It is a narrower
claim: RT-only coherence is useful as a retrieval and audit signal, but it is
not enough to promote an identity.

The diagnostic remains non-mutating. It must not change `alignment_matrix.tsv`,
workbooks, current Backfill behavior, or production promotion logic.

## Design Stance After External Review

The external review raised valid risks, but this spec does not accept every
claim unchanged. The resulting design stance is:

| Review point | Decision | Rationale |
| --- | --- | --- |
| RT-windowed peak finding is too close to Backfill | Accepted | A pre-Backfill run prevents output leakage, but methodologically it is still similar to Backfill if it only checks peak presence and RT. |
| Therefore the diagnostic is useless | Rejected | The diagnostic still catches single-sample seeds, insufficient recurrence, center instability, Backfill evidence leakage, threshold-policy errors, and multi-seed ambiguity. |
| Seed qualification is load-bearing | Accepted | Weak or background-like seeds cannot be rescued by recurrence alone. Seed specificity must be promoted from a loose filter to a first-class gate. |
| All discrimination should live in seed qualification | Modified | Non-seed samples often lack MS2 evidence, so seed specificity anchors the identity while MS1 trace identity checks support cross-sample coherence. |
| Shape/scoring can wait until a later phase | Rejected for MVP | At least one non-RT trace identity basis must be present in v0.3, otherwise coherence collapses back to RT-local Backfill-like peak finding. |
| Targeted ISTDs should all pass | Modified | ISTDs are positive-control yardsticks, not a blanket pass rule. Only mapped targeted/stable control rows have expected diagnostic outcomes, and misses must be explained. |
| Post-hoc `alignment-dir` can drive the diagnostic | Rejected as primary path | Current TSVs distinguish `detected` and `rescued`, but they are not a complete pre-Backfill owner-state snapshot. Post-hoc mode is comparison/reporting only. |
| Four frozen TSV schemas are too heavy for prototype learning | Accepted with constraint | Freeze only `decisions.tsv`, `cell_evidence.tsv`, and `summary.md`; keep broader evidence tables exploratory until 8RAW review. |
| A major untargeted redesign means starting from scratch | Rejected | Existing untargeted owner/alignment modules and targeted extraction/scoring diagnostics are reusable foundations, not legacy debris. |

## Method Correction

The prototype must not define coherence as only:

```text
seed center -> broad RT window -> find peak -> RT gate -> would-primary
```

That is too close to current owner Backfill mechanics. It can promote the same
rescue-heavy rows when broad background signal has RT-windowed peaks in many
samples.

The useful part of the diagnostic is not "Backfill earlier." The useful part is
making identity promotion observable before value recovery:

- which seed is allowed to ask the cross-sample question;
- which samples pass independent identity checks;
- which rows are only RT-local recurrence;
- which apparent support depends on Backfill evidence;
- which threshold policy would break when moving from 8RAW to 85RAW.

V0.3 may still use XIC extraction to collect candidate traces, but promotion
requires evidence that is independent of simple RT-windowed peak presence:

- seed specificity before any across-sample scan;
- per-sample trace identity / shape quality;
- recurrence background guard.

The resulting decision should then be benchmarked against targeted ISTD or
stable-control yardsticks. Control labels validate the diagnostic; they do not
promote identities.

RT coherence is necessary but not sufficient.

## Reuse Existing Foundations

This reset is not a rewrite-from-zero. The current untargeted path has already
built useful foundations, and the targeted path is a major source of validated
methods.

Untargeted foundations to reuse:

- `build_sample_local_owners` and `SampleLocalMS1Owner` as the pre-Backfill
  owner evidence surface;
- `cluster_sample_local_owners` and `OwnerAlignedFeature` as the starting
  identity-family grouping surface;
- ambiguous-owner and duplicate-owner signals as seed specificity and
  Review-only pressure;
- `pre_backfill_consolidation` logic as prior art for compatible owner grouping,
  not as the final identity algorithm;
- existing `trace_quality`, `scan_support_score`, `region_*`, and integration
  audit fields as candidate identity inputs;
- current `production_decisions`, `matrix_identity`, and TSV writers as
  comparison surfaces, not promotion evidence.

Targeted foundations to reuse:

- targeted peak detection and integration primitives, including peak width,
  baseline, scan support, and boundary/integration audit metrics;
- targeted scoring concepts such as support/concern labels, raw score,
  `shape_clean`, `shape_poor`, and CWT/shape support where available;
- targeted ISTD benchmark diagnostics as positive-control yardsticks;
- targeted peak reliability and NL-dropout diagnostics as examples for
  separating infrastructure failure, data-quality failure, and plausible
  biological signal;
- targeted RT/ISTD drift evidence as validation or drift-calibration context,
  not direct row identity-promotion evidence.

Dependency boundary:

- `xic_extractor.alignment.identity_coherence` may reuse small domain primitives,
  typed models, and metric functions that are already independent of IO.
- It must not import `tools.diagnostics.*`, workbook/report renderers, GUI code,
  CLI scripts, or process backends.
- Targeted diagnostics can provide validation artifacts and metric definitions.
  If a diagnostic metric becomes required for promotion, first extract it into a
  small domain/shared module with focused tests, then import that module from the
  identity-coherence implementation.

Design rule:

```text
reuse mature extraction, scoring, audit, and benchmark primitives;
rewrite only the identity-promotion layer that combines them for untargeted rows.
```

The new diagnostic should therefore be thin orchestration around existing
signals wherever possible. New code is justified when the existing module lacks
the untargeted-specific identity contract, not merely because the old algorithm
will be replaced.

## Non-Goals

- No production matrix behavior change.
- No replacement of current `owner_backfill.py`.
- No new default Backfill gate.
- No production graph merge/split implementation.
- No GUI change.
- No workbook schema change.
- No frozen broad multi-table diagnostic schema before 8RAW learning.

## Prototype Data Flow

The primary implementation path is inline pre-Backfill:

```text
build_owners
  -> cluster_owners
  -> identity_coherence_diagnostic       # new opt-in diagnostic stage
  -> owner_backfill                      # unchanged production path
  -> build_matrix / review / cells       # unchanged production path
```

This is the only clean path for promotion evidence because the diagnostic needs
pre-Backfill owner state.

Post-run `--alignment-dir` mode is allowed only for comparison and report
joining. It must not be the source of promotion evidence unless the input
artifact explicitly encodes pre-Backfill provenance.

Current `alignment_cells.tsv` has useful `status` and `source_candidate_id`
columns, and `rescued` cells are distinguishable from `detected` cells. That is
not enough to make a post-hoc run the canonical source of pre-Backfill owner
state, because the diagnostic needs all candidate/owner context before
Backfill and before production consolidation decisions.

## Evidence Firewall

Allowed for identity promotion:

- neutral loss tag from the active discovery/profile context;
- product m/z and observed neutral loss tolerance evidence;
- pre-Backfill sample-local MS1 owner evidence;
- diagnostic vendor XIC traces collected before Backfill;
- seed specificity metrics derived before Backfill;
- trace identity / shape metrics derived from diagnostic candidate traces;

Validation-only evidence:

- targeted ISTD benchmark/control labels and positive-control classes;
- targeted benchmark diagnostics emitted by `tools/diagnostics/*`;
- current production `production_decisions`, `matrix_identity`, and workbook
  outputs;
- post-hoc `alignment-dir` joins used only for comparison/reporting.

Validation-only evidence may appear in summary tables, benchmark sections, and
positive-control columns. It must not change `decision`,
`total_coherent_sample_count`, `non_seed_coherent_sample_count`, or any
promotion gate.

Forbidden for identity promotion:

- `owner_backfill` rescued area/status;
- `backfill`, `rescued`, `absent`, `unchecked` production statuses;
- final `include_in_primary_matrix`;
- workbook values;
- family-center re-extraction after Backfill;
- post-Backfill row inclusion or rescue dependency.

The summary must assert:

```text
promotion_used_forbidden_evidence = false
```

The decisions table should keep `forbidden_evidence_seen` when comparison
inputs contain forbidden evidence. It should not carry a per-row "used"
column that is defined to be always false.

## Discriminator Model

V0.3 promotion requires three layers. A candidate that fails any blocking layer
stays Review-only.

```text
medium seed specificity
  -> RT-local candidate trace retrieval
  -> independent trace identity checks
  -> diagnostic would-primary / review-only decision
```

### Layer 1: Seed Specificity

Seed qualification is the load-bearing gate.

Minimum v0.3 seed requirements:

- neutral loss tag matches the active profile;
- product m/z is inside tolerance;
- observed neutral loss is inside tolerance;
- sample-local MS1 owner exists before Backfill;
- area, apex RT, height, start RT, and end RT are finite;
- owner is not ambiguous and not a duplicate loser;
- seed has enough fragment specificity to distinguish it from generic
  background recurrence.

`high evidence score` is not required as a blanket rule, but low-specificity
seeds cannot be rescued by recurrence alone.

Required seed diagnostic fields:

```text
seed_specificity_class =
  high_specificity | medium_specificity | low_specificity | background_like

seed_reject_reason =
  missing_fragment_evidence
  no_quantifiable_owner
  ambiguous_owner
  duplicate_loser
  backfill_only_evidence
  nonfinite_peak
  low_fragment_specificity
  background_like_seed
```

Background-like seeds are Review-only even if they recur in many samples.

### Layer 2: RT-Local Candidate Retrieval

XIC extraction in V0.3 is candidate retrieval, not promotion evidence by
itself.

RT units must be explicit:

```text
initial_rt_min = seed_rt_min - (max_rt_sec / 60.0)
initial_rt_max = seed_rt_min + (max_rt_sec / 60.0)
```

The retrieval window may default to `max_rt_sec = 180` for 8RAW exploration,
but the extracted peak is only a candidate for further checks.

### Layer 3: Trace Identity Checks

Every non-seed sample that contributes to would-primary must pass at least one
non-RT identity check.

V0.3 minimum independent checks:

- peak morphology is complete and finite;
- peak width is within a bounded ratio of the seed peak width;
- local baseline / interference is not obviously incompatible;
- normalized local trace shape has enough similarity to the seed or group
  prototype when enough points exist;
- area/height pattern is not a flat high-recurrence background signature.

The exact first implementation can use simple deterministic metrics, but the
decision must expose which non-RT check admitted the sample. A cell cannot be
`coherent` only because a positive peak exists inside an RT window.

Required cell evidence category:

```text
cell_identity_basis =
  seed_sample
  rt_plus_shape
  rt_plus_width
  rt_plus_baseline
  rt_plus_area_pattern
  rt_only_review_only
  blocked_infrastructure
  data_quality_reject
```

`rt_only_review_only` is never allowed to support would-primary.

## RT Center Rules

The provisional center is another load-bearing step and must not be hand-waved.

For v0.3:

- the seed sample always anchors the first provisional center;
- non-seed candidates can contribute to the provisional center only after
  passing basic morphology completeness;
- candidates farther than `seed_center_candidate_sec` from the seed RT are not
  used to estimate the center;
- `max_center_drift_sec` must be tighter than `preferred_rt_sec`.

Baseline review parameters for 8RAW:

| Parameter | Default | Unit | Meaning |
| --- | ---: | --- | --- |
| `max_rt_sec` | 180 | seconds | Broad retrieval window. |
| `preferred_rt_sec` | 60 | seconds | Final RT acceptance gate after independent checks. |
| `seed_center_candidate_sec` | 30 | seconds | Max seed distance for center-estimation candidates. |
| `max_center_drift_sec` | 30 | seconds | Seed-anchor guard; intentionally tighter than the 60 sec gate. |

Promotion must report:

```text
center_method
center_candidate_count
center_drift_sec
center_decision =
  seed_anchored | recentered_stable | center_unstable_review_only
```

## Support Thresholds

Do not treat `min_coherent_samples = 3` as a dataset-independent product rule.

For the 8RAW review subset:

```text
min_total_coherent_samples = 3
seed_counts_toward_total = true
min_non_seed_coherent_samples = 2
```

The diagnostic must report both absolute count and fraction:

```text
total_coherent_sample_count
non_seed_coherent_sample_count
assessed_sample_count
coherent_sample_fraction
```

For 85RAW, the 8RAW threshold cannot be copied blindly because `3/8` and
`3/85` have very different meaning. 85RAW validation must use a reviewed
threshold policy, such as a minimum count plus minimum fraction, before any
production interpretation.

## Positive Controls And Yardsticks

V0.3 must include a cheap positive-control yardstick before interpreting 8RAW
results.

Required if available:

- targeted ISTD benchmark output from existing `tools/diagnostics/targeted_istd_benchmark.py`;
- selected stable-like ISTD or targeted control rows mapped to untargeted
  candidate families;
- expected outcome for each control:
  - pass seed specificity where applicable;
  - pass trace identity checks;
  - explain misses explicitly when not promoted.

The Go/No-Go table cannot use vague "expected stable-like rows" without naming
the control set or linking the benchmark artifact.

## Diagnostic Output Contract

V0.3 intentionally freezes only the minimum review surface needed to audit both
row-level decisions and the load-bearing per-sample non-RT evidence:

```text
untargeted_identity_coherence_decisions.tsv
untargeted_identity_coherence_cell_evidence.tsv
untargeted_identity_coherence_summary.md
```

Exploratory aggregate/detail tables are allowed but not frozen before 8RAW:

```text
untargeted_identity_coherence_candidates.tsv
untargeted_identity_coherence_groups.tsv
```

The optional tables should be emitted when useful, but their schema may change
until the first 8RAW review identifies the fields that actually matter.

### Required `decisions.tsv` Columns

```text
decision_id
source_feature_family_id
primary_seed_id
seed_sample_stem
seed_specificity_class
decision
decision_reason
total_coherent_sample_count
non_seed_coherent_sample_count
assessed_sample_count
coherent_sample_fraction
min_total_coherent_samples
min_non_seed_coherent_samples
center_decision
center_drift_sec
non_rt_identity_pass_count
rt_only_candidate_count
blocked_infrastructure_count
data_quality_reject_count
coherent_sample_ids
rt_only_sample_ids
blocked_sample_ids
data_quality_reject_sample_ids
forbidden_evidence_seen
positive_control_class
positive_control_expected_decision
notes
```

Decision enum:

```text
would_primary_independent_identity_support
review_only_low_seed_specificity
review_only_rt_only_support
review_only_insufficient_support
review_only_center_unstable
review_only_background_like_recurrence
review_only_multi_seed_requires_phase2
blocked_infrastructure
```

`blocked_infrastructure` is separate from data-quality rejection. It covers
missing RAW, unreadable files, extraction crashes, and malformed required
inputs. Non-finite traces or bad peak fields are data-quality outcomes unless
they prevent the run from assessing the sample at all.

### Required `cell_evidence.tsv` Columns

This table is narrow but frozen because every non-seed coherent sample must have
an auditable non-RT identity basis. It is not the old broad `cells.tsv` schema.

```text
decision_id
source_feature_family_id
sample_stem
sample_role
cell_decision
rt_delta_center_sec
rt_gate_result
non_rt_identity_basis
non_rt_identity_result
evidence_source
reject_reason
```

`sample_role` enum:

```text
seed
non_seed
```

`cell_decision` enum:

```text
coherent_identity_supported
rt_only_review_only
outside_rt_gate
data_quality_reject
blocked_infrastructure
not_assessed
```

For a `non_seed` sample to contribute to
`non_seed_coherent_sample_count`, `cell_decision` must be
`coherent_identity_supported`, `rt_gate_result` must be pass, and
`non_rt_identity_result` must be pass. RT-only rows remain review evidence, not
promotion evidence.

### Required `summary.md` Sections

- command and mode;
- inline pre-Backfill input source or explicit reason a post-hoc run is
  comparison-only;
- input hashes and row counts;
- positive-control artifact and mapped control rows;
- evidence firewall assertion;
- seed specificity counts;
- RT-only candidate counts;
- independent trace identity pass counts;
- per-sample evidence coverage and missing-basis counts;
- infrastructure-blocked counts;
- data-quality reject counts;
- threshold count and fraction summaries;
- RAW/XIC request and timing counters;
- Go / No-Go / Pivot table.

## CLI / Invocation Contract

Preferred inline mode:

```powershell
python scripts\run_alignment.py `
  <existing args> `
  --emit-identity-coherence-diagnostic `
  --identity-coherence-output-dir <diagnostic_output_dir>
```

Equivalent diagnostic module mode is acceptable only if it consumes an explicit
pre-Backfill owner-state export produced before `owner_backfill`:

```powershell
python -m tools.diagnostics.untargeted_identity_coherence `
  --pre-backfill-owner-state <owner_state.jsonl> `
  --raw-dir <raw_dir> `
  --output-dir <diagnostic_output_dir>
```

Post-hoc comparison mode:

```powershell
python -m tools.diagnostics.untargeted_identity_coherence_report `
  --alignment-dir <existing_alignment_output_dir> `
  --diagnostic-dir <diagnostic_output_dir>
```

Post-hoc comparison mode must not promote identities.

## Failure Modes That Must Be Explainable

Infrastructure-blocked:

- missing required input file;
- missing required input column;
- missing RAW source;
- RAW extraction error;
- process worker failure;
- malformed pre-Backfill owner-state export.

Data-quality or identity rejects:

- missing fragment evidence;
- low fragment specificity;
- background-like seed;
- ambiguous owner;
- duplicate loser;
- Backfill-only evidence rejected;
- non-finite trace or peak field;
- zero candidate peak;
- incomplete peak boundaries;
- center drift unstable;
- outside recentered RT gate;
- RT-only support with no independent trace identity basis;
- insufficient total or non-seed coherent samples;
- multi-seed ambiguity requiring Phase 2.

## Go / No-Go / Pivot Rules

| Observation after 8RAW | Decision |
| --- | --- |
| Positive-control ISTD/stable rows pass with independent identity support | Proceed to 85RAW threshold-policy review. |
| Controls fail because only RT support is present | No-Go; add trace identity metrics before continuing. |
| Weak or background-like seeds become would-primary through recurrence | No-Go; tighten seed specificity/background guard. |
| Any row is promoted by Backfill/rescued evidence | No-Go; fix evidence firewall. |
| Most would-primary rows are `rt_only_review_only` before non-RT checks | Pivot to shape/trace scoring before expanding scope. |
| 8RAW threshold looks good but fraction would be trivial in 85RAW | Define count+fraction policy before 85RAW. |
| Multi-seed/overflow dominates candidate decisions | Pivot to Phase 2 graph merge/split spec. |
| RAW/XIC request count projects poorly to 85RAW | Add request-budget/locality design before 85RAW. |
| Infrastructure-blocked count is high | Fix run/input infrastructure before scientific interpretation. |

## Acceptance Criteria Before Implementation

This spec is ready for implementation only after review signs off on:

- the method difference from Backfill is explicit and accepted;
- seed specificity classes and reject reasons are sufficient to block
  background-like recurrence;
- at least one independent non-RT trace identity check is in V0.3 MVP;
- 8RAW and 85RAW threshold policies are separated;
- seed sample counting is explicit (`seed + at least 2 non-seed` for 8RAW);
- targeted ISTD/control rows are named or a benchmark artifact is provided;
- inline pre-Backfill data flow is accepted as the primary path;
- output scope is limited to `decisions.tsv`, `cell_evidence.tsv`, and
  `summary.md` as frozen contracts for the first run.

## Review Questions

1. What is the minimum acceptable seed specificity gate for V0.3?
2. Which first non-RT trace identity check should be in MVP: shape similarity,
   peak-width ratio, baseline/interference flag, or area-pattern guard?
3. Should background-like recurrence always block would-primary even when the
   total coherent count is high?
4. Which targeted ISTD or stable rows should be the 8RAW positive controls?
5. Is `seed + 2 non-seed coherent samples` the right 8RAW support threshold?
6. What count+fraction policy should be reviewed before 85RAW?
7. Is post-hoc `alignment-dir` mode acceptable only as comparison/reporting?
