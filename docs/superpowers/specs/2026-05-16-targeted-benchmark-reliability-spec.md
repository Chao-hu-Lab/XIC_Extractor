# Targeted Benchmark Reliability Spec

**Date:** 2026-05-16
**Status:** Draft spec for targeted-side benchmark reliability work
**Branch:** `codex/targeted-benchmark-reliability`
**Worktree:** `C:\Users\user\Desktop\XIC_Extractor\.worktrees\targeted-benchmark-reliability`

## Summary

The targeted workflow is now the main validation benchmark for untargeted
alignment. That means targeted output must expose when a detected peak is strong
enough to be used as benchmark evidence and when it is only a weak targeted
candidate that needs review.

This spec does not change untargeted matrix identity rules. It adds a targeted
reliability layer so cases like suspected low-area or wrong-peak `d3-N6-medA`
results are visible before they are used to judge untargeted ISTD behavior.

## Problem

Targeted extraction currently has useful scoring fields:

- `Confidence`;
- `Reason`;
- `NL`;
- `Score Breakdown`;
- RT prior and prior source;
- quality flags and severity labels.

However, the downstream benchmark question is stricter than the extraction
question.

Extraction question:

```text
Did targeted extraction find a plausible peak for this target in this sample?
```

Benchmark question:

```text
Is this targeted result reliable enough to act as ground-truth-like evidence
when validating untargeted alignment?
```

Those are not the same. A low-area, low-confidence, RT-inconsistent, or weak
MS2/NL targeted result can be useful for manual review, but it should not silently
become the standard that untargeted alignment is punished against.

## Product Contract

Targeted output must support four distinct states:

| State | Meaning | Benchmark behavior |
|---|---|---|
| `benchmark_eligible` | Strong targeted evidence suitable for targeted-vs-untargeted validation. | Can count as benchmark positive evidence. |
| `targeted_review_positive` | Targeted found a finite positive-area peak with strong RT/MS1/shape/trace support, but one expected benchmark signal failed, such as plausible NL dropout. | Keep as targeted-side positive review evidence; strict benchmark excludes it from clean denominator and reports a warning. |
| `targeted_review` | Targeted found a finite positive-area peak, but the evidence is weak or suspicious. | Keep in targeted output; annotate benchmark as targeted-side review risk. |
| `targeted_negative` | No usable targeted peak evidence, such as missing/invalid RT, missing/non-positive area, or no selected peak. | Do not count as positive benchmark evidence. |

This contract is diagnostic-first. It does not require changing the primary
`XIC Results` workbook schema in the first implementation phase. A diagnostic
TSV/JSON report may provide the reliability state until a future plan explicitly
changes workbook columns.

State precedence must be explicit:

1. No usable peak evidence becomes `targeted_negative`.
2. A finite RT and positive area with strong peak evidence but a plausible
   isolated benchmark-signal dropout becomes `targeted_review_positive`.
3. A finite RT and positive area with weak or suspicious evidence becomes
   `targeted_review`, even when the concern is severe.
4. A finite RT and positive area with strong evidence and no blocking review
   risk becomes `benchmark_eligible`.

In particular, `VERY_LOW`, `NL_FAIL`, and `NO_MS2` rows with finite RT and
positive area are targeted-side review evidence by default, not true negatives.
They are not clean benchmark positives, but they should remain visible because
they may explain targeted-side failures such as a wrong peak.

`NL_FAIL` must not remain a single undifferentiated reason. A selected peak with
strong local S/N, clean shape, clean trace, and no hard local-quality concern is
`targeted_review_positive` with `plausible_nl_dropout`. NL failure without that
support remains `targeted_review` with `hard_nl_conflict`.

The dropout split must use the shared evidence consistency classifier in
`xic_extractor.evidence_semantics`, not a targeted-only rule. The same semantic
labels are consumed by candidate-score calibration so targeted workbook review
and candidate-table diagnostics supervise each other instead of drifting.

## Non-Goals

This work must not:

- change untargeted alignment production gates;
- change final matrix identity decisions;
- read targeted labels from production untargeted code;
- retune peak picking thresholds without a failing characterization case;
- make iRT, LOESS, or RT warping a hard targeted exclusion rule;
- remove weak targeted evidence from review outputs;
- change workbook schemas without a separate schema-change step.

## Reliability Inputs

The reliability layer may consume existing targeted extraction outputs:

- `XIC Results`;
- `Score Breakdown` when emitted;
- `Targets`;
- `Diagnostics`;
- target role and ISTD pairing;
- neutral-loss status;
- confidence and reason text;
- RT, peak boundaries, width, intensity, and area;
- prior RT and prior source;
- quality flags and total severity.

It may also consume optional validation context:

- strict targeted ISTD benchmark JSON;
- sample metadata and injection order;
- known targeted-side exceptions.

Optional context can annotate reports. It must not become hidden production
targeted extraction logic.

## Reliability Signals

The first reliability implementation should classify rows using visible,
explainable signals rather than a single opaque score.

### Strong Evidence Signals

- `Confidence == HIGH` or `MEDIUM`;
- accepted ISTD rows with `Confidence == LOW`, finite positive area/RT, and
  strict NL support;
- `NL == OK` or acceptable warning token;
- RT prior severity is close or absent for targets without priors;
- no hard trace-quality flags;
- positive finite area and RT;
- peak width and local signal quality are plausible;
- Score Breakdown support dominates concerns.

### Review Risk Signals

- `Confidence == LOW` for non-ISTD rows, or for ISTD rows that were not
  accepted with strict NL support;
- `Confidence == VERY_LOW`;
- `NL == NO_MS2` or weak MS2 trace when NL evidence is expected;
- `NL == NL_FAIL`;
- RT prior is far from observed peak;
- selected peak is outside the target RT window unless a strong anchor explains
  it;
- peak shape, edge, scan-support, or continuity flags are present;
- area is extreme-low relative to the target's own detected distribution or
  paired ISTD trend;
- the targeted result is already a known benchmark exception.

### Special Case: Suspected `d3-N6-medA` Targeted Peak Issue

`d3-N6-medA` has been observed as a likely targeted-side issue when area is far
too low and the selected peak is inconsistent with expected behavior. The system
should not hard-code this target as invalid. Instead, it should expose the
generic signals that explain why the row is a targeted review risk:

- weak area rank;
- weak or conflicting MS2/NL evidence;
- RT or anchor inconsistency;
- low final confidence or confidence caps.

Known exceptions may be passed to diagnostics to explain report verdicts, but
the reliability logic should remain target-agnostic.

## Detection Versus Benchmark Eligibility

Existing detection acceptance currently allows some `LOW` confidence rows when
MS2/NL status is acceptable. That can remain true for targeted extraction.

Benchmark eligibility should be stricter, but not stricter than the physical
ISTD evidence:

```text
targeted detected/review output != benchmark eligible positive evidence
```

This separation is the main contract. It allows targeted extraction to remain
sensitive while preventing weak targeted evidence from becoming a misleading
untargeted benchmark.

## Output Contract

Phase A should produce a diagnostic report under `tools/diagnostics/`:

```text
targeted_peak_reliability_summary.tsv
targeted_peak_reliability_rows.tsv
targeted_peak_reliability.json
targeted_peak_reliability.md
```

Required row fields:

| Field | Meaning |
|---|---|
| `sample_name` | Sample identifier from targeted output. |
| `target_label` | Target label from workbook output. |
| `role` | `ISTD` or `Analyte`. |
| `rt` | Targeted selected RT, if present. |
| `area` | Targeted area, if present. |
| `confidence` | Existing targeted confidence. |
| `nl` | Existing targeted NL token. |
| `prior_rt` | Prior RT from Score Breakdown, if available. |
| `prior_source` | Prior source from Score Breakdown, if available. |
| `total_severity` | Existing total severity, if available. |
| `quality_flags` | Existing quality flags, if available. |
| `reliability_state` | `benchmark_eligible`, `targeted_review_positive`, `targeted_review`, or `targeted_negative`. |
| `risk_reasons` | Semicolon-separated explainable risk labels. |

Required summary fields:

| Field | Meaning |
|---|---|
| `target_label` | Target label. |
| `role` | Target role. |
| `benchmark_eligible_count` | Rows suitable for benchmark positives. |
| `targeted_review_positive_count` | Rows with strong selected peak evidence but non-clean benchmark evidence such as plausible NL dropout. |
| `targeted_review_count` | Rows with targeted evidence but review risk. |
| `targeted_negative_count` | Rows without usable targeted evidence. |
| `top_risk_reasons` | Most common risk labels. |
| `known_exception` | Optional annotation only. |

## Integration With Existing Benchmark

`tools/diagnostics/targeted_istd_benchmark.py` should continue to produce the
strict untargeted benchmark. A later implementation step may add an optional
input:

```powershell
--targeted-reliability-json <path>
```

When provided, the benchmark can annotate targeted-side review risk and avoid
treating weak targeted rows as clean positive evidence. This must remain a
diagnostic behavior and must not feed production untargeted identity logic.

### Cross-report Evidence Consistency

`tools/diagnostics/cross_report_evidence_consistency.py` compares
`targeted_peak_reliability_rows.tsv` with selected rows from `peak_candidates.tsv`.
It is a diagnostic bridge between targeted workbook reliability and candidate
evidence. It must not change targeted extraction, candidate scoring, or
benchmark gate behavior.

Required inputs:

```powershell
--targeted-reliability-rows-tsv <path>
--peak-candidates-tsv <path>
--output-dir <path>
```

Optional input:

```powershell
--targeted-workbook <path>
```

When the targeted workbook is provided, report rows must include `target_mz` so
manual EIC review does not require a separate label lookup.

The report should classify mismatches including:

- `targeted_clean_candidate_conflict`;
- `review_positive_not_supported_by_candidate`;
- `targeted_review_candidate_suggests_dropout`;
- `targeted_negative_candidate_has_peak`;
- `missing_selected_candidate`;
- `missing_targeted_reliability`;
- `multiple_selected_candidates`.

These mismatches are review prompts, not production decisions.

### Strict Reliability Denominator Semantics

Default benchmark behavior must remain backward compatible when no reliability
JSON is provided.

When strict targeted reliability mode is enabled, the benchmark must not overload
or silently reinterpret existing counts. It should report these counts
separately:

| Field | Meaning |
|---|---|
| `targeted_positive_count` | Existing raw targeted positive count: finite RT, positive area. |
| `clean_targeted_positive_count` | Count of `benchmark_eligible` rows. |
| `targeted_review_positive_count` | Count of finite positive-area rows classified as `targeted_review_positive`. |
| `targeted_review_count` | Count of finite positive-area rows classified as `targeted_review`. |
| `targeted_negative_count` | Count of rows classified as `targeted_negative`. |
| `coverage_denominator_count` | Count used to compute `coverage_minimum`; equals `clean_targeted_positive_count` in strict reliability mode. |

Coverage and RT/area correlation calculations in strict reliability mode must
use only `benchmark_eligible` samples:

- `targeted_review_positive` samples are excluded from coverage denominator and
  correlation pairs in strict mode, but are counted separately from weaker
  review evidence;
- `targeted_review` samples are excluded from coverage denominator and
  correlation pairs;
- `targeted_review_positive` and `targeted_review` samples must not create
  `MISS`, `DRIFT`, or `AREA_MISMATCH` failures by themselves;
- `targeted_review` samples must be reported as targeted-side review risk, for
  example with `TARGETED_REVIEW_EVIDENCE`;
- `targeted_review_positive` samples must be reported with
  `TARGETED_REVIEW_POSITIVE_EVIDENCE`;
- if an active target has too few clean samples after review exclusion, the
  benchmark is inconclusive for that target and must not be reported as a clean
  `PASS`.

If the existing benchmark summary model cannot represent an inconclusive or
warning state, Phase B must add explicit warning fields before enabling strict
targeted reliability mode.

## Acceptance Criteria

This work is accepted when:

- targeted reliability diagnostics can identify weak targeted positives without
  deleting them from targeted output;
- suspected `d3-N6-medA`-style low-area or wrong-peak cases are explained by
  generic risk reasons;
- high-confidence ISTD rows remain benchmark eligible;
- `targeted_istd_benchmark.py` can optionally annotate targeted-side review
  risk without changing production alignment;
- tests cover loader behavior, reliability state decisions, and benchmark
  compatibility;
- no untargeted matrix rows change unless a later plan explicitly scopes that
  change.

## Stop Conditions

Stop and review before implementation continues if:

- the required reliability signal is not present in existing targeted outputs
  and would require raw trace reprocessing;
- proposed rules would demote many high-confidence ISTD rows;
- a rule needs a target name hard-code rather than generic evidence;
- workbook schema changes become necessary;
- untargeted production code would need targeted workbook labels.
