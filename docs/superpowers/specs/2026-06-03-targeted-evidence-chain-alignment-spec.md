# Targeted Evidence-Chain Alignment Spec

**Date:** 2026-06-03
**Status:** Implemented in current branch; pending PR closeout
**Validation status:** `production_ready` for scoped targeted product detection
after focused tests, full pytest, ruff, mypy, 3RAW sentinel, 85 tissue RAW
default-target extraction gate, consumer audit, analyte old-workbook parity
audit, paired-ISTD-anchor changed-row review, counted NL-dropout no-leak review,
workbook smoke, and reviewer acceptance. This label does not promote broader
target-pair candidate switching.

Accepted validation artifacts:

- `output/targeted_projection_default_targets_20260603_030225/`
- `targeted_projection_acceptance_summary_after_selection_anchor_guard.tsv`
- `sentinel_projection_assertions_after_selection_anchor_guard.tsv`
- `analyte_old_vs_current_after_selection_anchor_guard.tsv`
- `analyte_nl_fail_counted_after_selection_anchor_guard.tsv`
- `consumer_authority_audit.tsv`
- `targeted_projection_no_leak_audit.tsv`
- `output/target_pair_rt_production_ready_20260604/default_3raw_after_anchor_source_fix/`
- `output/target_pair_rt_production_ready_20260604/full_85raw_after_anchor_source_fix/`
- `full_85raw_after_anchor_source_fix/review/sentinel_assertions.tsv`
- `full_85raw_after_anchor_source_fix/review/changed_row_review.tsv`
- `full_85raw_after_anchor_source_fix/review/counted_status_delta_vs_after_projection_fix.tsv`
- `full_85raw_after_anchor_source_fix/review/target_detection_summary.tsv`
- `full_85raw_after_anchor_source_fix/review/counted_analyte_nl_dropout_review.tsv`
- `full_85raw_after_anchor_source_fix/review/production_ready_acceptance_summary.tsv`
- `full_85raw_after_anchor_source_fix/review/run_provenance.tsv`

2026-06-04 paired-analyte production gate:

- 3RAW sentinel used `config/targets.example.csv` with settings copied
  unchanged; CLI only overrode `data_dir` and skipped Excel for machine CSV
  review. The exact 3RAW command, exit code, processed file count, diagnostics
  count, and assertion target are recorded in
  `full_85raw_after_anchor_source_fix/review/run_provenance.tsv`.
- Sentinels all pass in
  `full_85raw_after_anchor_source_fix/review/sentinel_assertions.tsv`:
  `TumorBC2258_DNA / d3-N6-medA`, `TumorBC2289_DNA / d3-5-medC`,
  `TumorBC2263_DNA / 8-oxodG`, and `TumorBC2263_DNA / 15N5-8-oxodG`.
- 85RAW default-target gate counts every ISTD as detected (`7 targets * 85
  samples`) with 1190 total rows, 85 samples, and 14 targets in
  `production_ready_acceptance_summary.tsv`.
- Counted analyte `NL_FAIL` / `NO_MS2` rows are explicit and bounded: 15 rows
  are counted, and all are accepted by paired-ISTD-anchor support and/or
  plausible DDA dropout policy in `counted_analyte_nl_dropout_review.tsv`.
- The counted analyte dropout review now carries the paired-ISTD anchor
  provenance required for production readiness: every row that claims
  `paired_istd_anchor_support` has `anchor_source=selected_istd_reported_rt`,
  positive paired ISTD RT/area, `paired_istd_counted=TRUE`,
  `anchor_within_interval=TRUE`, and `anchor_invariant_ok=TRUE`. The aggregate
  gate records `paired_anchor_invariant_failures=0`.
- Old workbook numeric RT/area is retained as compatibility evidence, not a hard
  product gate. The corrected changed-row review forward-fills the old workbook
  sample/group layout and externalizes 438 old-vs-current review rows, including
  legacy numeric rows that are now gated by product projection instead of being
  hard counted. Immediate counted-status delta versus
  `full_85raw_after_projection_fix` is 8 rows: 4 `TRUE -> FALSE`
  stricter-anchor/quality losses and 4 `FALSE -> TRUE` evidence-supported gains.
- Workbook smoke passed with
  `full_85raw_after_anchor_source_fix/base/output/xic_results_20260604_1012.xlsx`;
  console/product wording now reports `counted detection`, not `NL confirmed`.
- Final code gate passed: focused target/product tests, output workbook shard,
  full pytest (`3043 passed, 1 skipped, 16 warnings`), ruff, and mypy are
  recorded in `full_85raw_after_anchor_source_fix/review/run_provenance.tsv`.
- Pair anchor map provenance is product-critical: same-sample paired-ISTD support
  must come from credible selected ISTD MS1 `reported_rt` with positive area and
  acceptable selected-candidate quality. Window/NL anchors are evidence for
  extraction but cannot by themselves satisfy paired-anchor product support.

## Summary

Targeted extraction must align with the newer untargeted evidence-chain
direction. The product question is no longer:

```text
Does legacy targeted score/confidence/cap say this row is detected?
```

The product question becomes:

```text
What does the shared evidence decision say about this targeted peak hypothesis,
and how should that decision project into workbook, summary, and matrix values?
```

Targeted and untargeted workflows may still use different priors. Targeted has
known m/z, known RT windows, known ISTD/STD pairs, and expected NL/product
evidence. Untargeted has cross-sample hypotheses, family/cell evidence, mode
evidence, and broader MS1 pattern evidence. Those are differences in available
evidence, not justification for two independent product-decision systems.

## Current Problem

Targeted product behavior still lets legacy score/cap semantics decide
`detected` versus `ND` in places where the newer evidence-chain semantics should
be authoritative.

The concrete real-data sentinel is:

- `TumorBC2289_DNA / d3-5-medC` has a finite MS1 peak and area near the expected
  region, but the current workbook projects it as `VERY_LOW`,
  `decision: review only, not counted`, with `NL_FAIL`.
- Manual review indicates this should be explained as DDA stochastic NL dropout
  or insufficient MS2 opportunity, not true absence, because the ISTD peak has
  coherent MS1/RT/pattern support and ISTDs should be stably present after
  external addition.
- `TumorBC2258_DNA / d3-N6-medA` is the positive sentinel: it must remain
  detected after the migration.

Observed current-code 2RAW sentinel run:

```text
targets: config/targets.example.csv
settings: config/settings.csv copied unchanged into validation base
RAWs: TumorBC2258_DNA.raw, TumorBC2289_DNA.raw
output: output/targeted_default_targets_example_sentinel_20260603/base/output/xic_results_20260603_0127.xlsx
```

Observed rows:

| Sample | Target | Role | RT | Area | NL | Confidence | Current reason |
| --- | --- | --- | ---: | ---: | --- | --- | --- |
| `TumorBC2258_DNA` | `d3-N6-medA` | ISTD | 24.2752 | 512851507.67 | OK | HIGH | accepted |
| `TumorBC2289_DNA` | `d3-5-medC` | ISTD | 11.9888 | 15502090.32 | NL_FAIL | VERY_LOW | review only, not counted |

This proves the issue is not peak absence. It is a product-decision mismatch:
targeted scoring still treats an isolated NL failure as a hard detection cap.

## Product Contract

Targeted detection authority must move to:

```text
Existing peak evidence views
  (PeakHypothesis / EvidenceVector / CommonEvidence)
  -> EvidenceDecisionSemantics
  -> TargetedPriorContext + TargetedProductProjection
```

Legacy score/confidence/cap fields are demoted to evidence inputs:

- `raw_score`;
- `legacy_confidence`;
- `legacy_cap_labels`;
- local S/N features;
- shape and width features;
- trace-quality flags;
- MS2/NL status and opportunity context.

They must not directly decide:

- workbook detected versus ND;
- summary detected counts;
- final matrix value presence;
- product row state;
- review queue product status.

`TargetedPriorContext` is the targeted-only policy context: target role,
expected presence, target registry priors, STD/ISTD pairing, configured RT
window, and acquisition-opportunity interpretation. It is not part of the
shared untargeted identity spine.

`TargetedProductProjection` is the machine-readable targeted product oracle.
Every workbook, summary, review, and matrix consumer must consume this
projection instead of reparsing legacy `Confidence`, `NL`, score, cap, or free
text reason fields.

## Shared Decision Semantics

The targeted path may build an adapter/view over existing peak evidence so it
can be classified by shared evidence semantics. This adapter is not a new
durable spine and must not fork the meaning of `PeakHypothesis`,
`EvidenceVector`, or `CommonEvidence`.

The adapter should express targeted-only priors as typed evidence context, not
as separate final rules:

| Targeted fact | Shared evidence meaning |
| --- | --- |
| known target m/z and RT window | candidate prior / RT context |
| ISTD role | role-aware stability and external-addition context |
| STD/ISTD pairing | role-aware RT and paired-pattern support |
| finite RT and positive area | MS1 peak and positive quantification evidence |
| shape / local S/N / trace continuity | local MS1 coherence evidence |
| candidate-aligned MS2 and NL | candidate-aligned MS2/NL support |
| DDA trigger opportunity but missing NL | `not_observed` or plausible dropout context, not automatic absence |
| legacy score/cap | legacy evidence feature, not authority |

For paired targeted analytes/STDs, the paired ISTD RT is the primary
biological-matrix transfer anchor. A target-specific NL/product anchor is
supporting evidence only when it is close to the paired ISTD RT. If the
target-specific NL anchor is far from the paired ISTD RT, the extraction window
must remain ISTD-centered and the distant NL observation must stay review
evidence. This prevents a random DDA/NL event from becoming the selected peak
identity or boundary authority.

The ISTD-centered window is a candidate-search and review constraint, not a
hard backfill rule. If the paired STD/analyte is absent or has only unsupported
MS1 evidence, the row remains `not_counted`; do not promote it only because the
ISTD was stable. Cases like `TumorBC2263_DNA / 8-oxodG` may be rescued only when
the row-level evidence chain supports the 16-minute candidate rather than a
distant NL event. The current production rule is deliberately narrower than
"paired ISTD exists": a paired analyte may downgrade `NL_FAIL` / missing-DDA
conflict to `detected_flagged` only when it has positive MS1 RT/area inside the
target window, the selected peak interval contains the same-sample ISTD anchor
RT, and the selected candidate has no quality flags. Rows without that complete
anchor-supported MS1 interval remain `not_counted` or `ambiguous`.

The shared decision class remains:

- `accepted`;
- `review`;
- `not_counted`;
- `excluded`;
- `ambiguous`.

Targeted product projection may add product-facing states derived from those
semantics:

- `detected_clean`: counted detected row with no product review flag;
- `detected_flagged`: counted detected row with review evidence that does not
  invalidate the peak, such as role-aware plausible DDA NL dropout for ISTDs or
  paired-analyte NL dropout when same-sample ISTD anchor support and a complete
  MS1 interval make the target peak plausible;
- `not_counted`: peak evidence is insufficient or legacy-compatible review-only
  state remains unresolved;
- `excluded`: explicit identity or physical exclusion;
- `ambiguous`: conflicting evidence prevents product selection.

`detected_clean` and `detected_flagged` both carry RT/area into workbook and
matrix outputs. `detected_flagged` must remain visible in review surfaces.

Shared semantics may say `review` with `plausible_nl_dropout_review`; it must
not itself say "ISTD is present" or "this row is counted". Targeted product
projection is the only layer that can convert that shared evidence state into a
counted targeted detection.

## Targeted Product Projection Schema

The projection must be represented as typed data before rendering. At minimum,
it must carry:

- `product_state`: `detected_clean`, `detected_flagged`, `not_counted`,
  `excluded`, or `ambiguous`;
- `counted_detection`: boolean product count/matrix authority;
- `review_state`: `none`, `flagged`, or `review_required`;
- `projection_reason`: stable semicolon-separated labels for human-facing
  output;
- `support_reasons`, `review_reasons`, `conflict_reasons`,
  `not_counted_reasons`, and `exclusion_reasons`;
- `legacy_evidence`: legacy score/confidence/cap/NL fields retained for audit;
- `legacy_authority_status`: `evidence_only`, `diagnostic_only`, or `retired`;
- `benchmark_eligibility_state`, if benchmark/reliability reporting needs a
  state separate from product detection.

Output transport must be explicit. The selected implementation path is:

- add `TargetedProductProjection` to the extraction result object;
- render machine-readable projection fields into targeted long-row output and
  score breakdown;
- have workbook summaries, review metrics, and final matrix assembly consume
  `counted_detection` and `product_state`, not `Confidence`, `NL`, cap labels,
  or free-text `Reason`.

The long-row projection fields are stable advanced public schema fields. Schema
tests must cover them. Wide-only CSV-to-XLSX input without projection fields is
legacy compatibility mode and cannot be used as this migration's product
acceptance oracle.

`detected_flagged` is a targeted product counted state. It is different from
older `targeted_review_positive` benchmark/reliability language; the latter
must not be treated as a clean untargeted benchmark denominator without a
separate approved benchmark contract.

## Targeted vs Untargeted Boundary

Targeted and untargeted should share low-level evidence interpretation, but
they do not own the same product decision.

Shared evidence includes:

- MS1 peak presence, area, local S/N, shape, continuity, and trace coherence;
- RT context and RT conflict/support labels;
- candidate-aligned MS2/product/NL evidence;
- DDA opportunity and `not_observed` interpretation;
- support, concern, conflict, ambiguity, review, and exclusion vocabulary.

Targeted owns:

- known target and role priors, including ISTD/STD/analyte distinctions;
- expected ISTD presence after external addition;
- STD/ISTD pairing and role-aware RT/pattern support;
- targeted workbook, summary, review, and matrix product projection.

Untargeted owns:

- data-generated feature identity;
- cross-sample hypothesis support;
- family/cell/mode ownership;
- owner/backfill/gap-fill and final matrix row identity.

The root difference is therefore not chemistry or signal processing. It is
hypothesis source and product owner. Targeted asks whether a known target row
should project as presence/quantification. Untargeted asks whether data-derived
evidence supports a matrix identity across samples. The evidence facts can be
shared; the counted-output policy must remain workflow-owned.

## ISTD DDA Dropout Policy

For ISTD rows only, an isolated NL failure must not automatically project to
`ND` when the evidence chain supports the peak.

The shared evidence layer can identify a plausible NL-dropout review state. The
targeted projection layer then decides whether the row is a counted ISTD
detection by applying `TargetedPriorContext`.

An ISTD row may become `detected_flagged` when all are true:

- finite RT;
- positive finite area;
- coherent local MS1 peak evidence, including local S/N and shape/trace support;
- RT or paired-target context does not conflict with the selected peak;
- DDA MS2/NL evidence is missing, sparse, or NL-failed without enough opportunity
  evidence to prove that NL should have been observed;
- target role and expected-presence policy say the ISTD should be present in
  this run;
- no hard local-quality conflict, wrong-peak conflict, explicit exclusion, or
  ambiguity is present.

The product reason should expose the interpretation, for example:

```text
decision: detected_flagged; support: ms1_coherent; role-aware ISTD support;
review: plausible DDA NL dropout; concern: nl fail
```

This must not make NL failure disappear. The workbook may still show `NL_FAIL`
or an equivalent flag, but the detection state must no longer be derived from
that token alone.

## Analyte Policy

The ISTD dropout rule must not automatically promote analytes.

For analytes, NL/product/MS2 absence remains contextual evidence. A missing or
failed NL signal can become review evidence, but it should not become counted
detected unless a separate approved analyte policy exists. This is especially
important because biological samples are not expected to contain every external
standard/analyte target in the same way that externally added ISTDs should be
present.

## Legacy Score Retirement Path

This change must include an explicit exit path for legacy targeted scoring.

### Stage 1: Demote Score To Evidence

`score_candidate(...)`, confidence caps, and score-breakdown rows may continue
to exist, but only as evidence producers. New product projection code must not
ask "is confidence VERY_LOW?" or "is NL token NL_FAIL?" as the final detection
authority.

### Stage 2: Product Projection Uses Shared Decision

Workbook rows, summary detected counts, review metrics, and final matrix value
presence must read `TargetedProductProjection`, not raw score/cap/NL tokens.

Required guard tests:

- product detection count cannot be decided directly by `Confidence`;
- product detection count cannot be decided directly by `NL`;
- `NL_FAIL` can remain a review flag while still being `detected_flagged` for an
  ISTD with supportive evidence;
- `VERY_LOW` can remain legacy evidence but must not be the authority once a
  shared product projection exists.

### Stage 3: Legacy Product Authority Removal

After Stage 2 passes real-data validation, direct product uses of legacy score
authority must be removed or fenced as audit-only. Remaining score output should
be renamed or documented as legacy evidence, not product decision.

Before Stage 3 can close, run a consumer audit over workbook writers, summary
builders, review metrics, final matrix assembly, and score-breakdown exports.
Any consumer that maps `score`, `Confidence`, caps, or `NL` directly to
detected/ND is a blocker. Remaining references are allowed only when they are
clearly `legacy_evidence`, `evidence_only`, or `diagnostic_only`.

Retirement is complete when:

- no product path maps `score/confidence/cap` directly to detected/ND;
- score fields only appear in evidence, diagnostics, or audit outputs;
- tests fail if workbook or summary detection bypasses shared product
  projection;
- closeout notes list any remaining score users and their status:
  `evidence_only`, `diagnostic_only`, or `retired`.

## Non-Goals

This spec does not:

- tune peak picking, boundary selection, or AsLS integration;
- hard-code sample IDs such as `TumorBC2289_DNA`;
- hard-code target labels such as `d3-5-medC`;
- use targeted pass/fail labels in untargeted production matrix identity;
- make all analyte NL failures counted detections;
- make `NO_MS2` globally counted while `count_no_ms2_as_detected=false`;
- delete legacy scoring before product projection parity and guard tests exist.

## Implementation Ownership

Shared evidence interpretation belongs in the existing evidence/decision
modules. Targeted product projection belongs in a targeted peak-domain module,
for example `xic_extractor/peak_detection/targeted_product_projection.py`, or
an approved extension of the current selection-decision module.

Extraction code assembles `TargetedPriorContext` from target metadata, role,
pairing, RT priors, and acquisition opportunity. Output modules render and
consume projection fields; they must not recompute evidence semantics or infer
product state from legacy strings.

## Acceptance Criteria

Implementation is accepted when all are true:

- `TumorBC2289_DNA / d3-5-medC` changes from not-counted review evidence to
  `detected_flagged` with a plausible DDA NL dropout reason.
- `TumorBC2258_DNA / d3-N6-medA` remains detected.
- General analyte `NL_FAIL` rows are not automatically counted.
- Paired STD/analyte rows centered by ISTD RT are not automatically counted when
  the STD/analyte evidence is absent or unsupported.
- Default `config/targets.example.csv` targeted run with unchanged settings has
  every ISTD row satisfying the targeted dropout policy projected as
  `detected_clean` or `detected_flagged`.
- ISTD rows not projected as detected are listed with explicit blockers, such
  as no finite positive MS1 peak, hard local-quality conflict, wrong-peak
  conflict, anchor/RT conflict, explicit exclusion, or unresolved ambiguity.
- Any analyte `NL_FAIL` row newly projected as counted is listed separately and
  must have an approved non-ISTD product policy before acceptance.
- Workbook, summary, review metrics, and final matrix detection all use the
  targeted product projection.
- Legacy score/cap fields remain available for audit but cannot be the product
  authority.

## Validation Plan

Validation should run in this order:

1. Unit tests for targeted adapter/view construction from targeted peak
   evidence and existing shared evidence objects.
2. Unit tests for shared evidence semantics and targeted product projection.
3. Contract tests proving workbook/summary/review metrics read projection state.
4. Adversarial projection tests:

   - two rows with the same legacy `Confidence` and `NL` can count differently
     when their typed projection differs;
   - ISTD `NL_FAIL + VERY_LOW` can remain flagged evidence while
     `counted_detection=true` when targeted dropout policy is satisfied;
   - analyte `NL_FAIL` does not become counted only because an ISTD dropout
     rule exists;
   - a workbook/summary/review consumer fails the test if projection is absent
     and it falls back to `Confidence`, `NL`, caps, or free-text reason parsing.

5. Blast-radius report over the default-target run:

   - all ISTD not-detected rows with blockers;
   - all analyte `NL_FAIL` rows newly counted;
   - all remaining product consumers of legacy score/confidence/cap/NL tokens
     and whether each is `legacy_evidence`, `evidence_only`,
     `diagnostic_only`, or a blocker.
6. No-leak guard proving targeted projection labels and older
   `targeted_review_positive` benchmark/reliability language are not used as
   untargeted identity authority, owner/family/cell policy, or clean benchmark
   denominator without an approved contract.
7. 2RAW sentinel run with machine-readable provenance:

   - `targets.example.csv` hash;
   - `settings.csv` hash;
   - exact staged RAW basenames;
   - output path;
   - key row projection assertions.

   Preflight must use the RAW-capable environment and confirm the module-form
   runner before the sentinel launch:

   ```powershell
   .venv\Scripts\python.exe --version
   .venv\Scripts\python.exe -m scripts.run_extraction --help
   Test-Path "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R"
   Test-Path "C:\Xcalibur\system\programs"
   ```

   ```powershell
   .venv\Scripts\python.exe -m scripts.run_extraction `
     --base-dir <staged-base-with-targets.example.csv> `
     --data-dir <TumorBC2258_DNA + TumorBC2289_DNA staged RAW dir>
   ```

8. Full default-target run over the tissue RAW root if the 2RAW sentinel passes;
   this is required before claiming `production_ready`.
9. Focused no-RAW tests plus repo-local PR gate when implementation is complete.

The 2RAW sentinel is a fail-fast gate. Do not run the full 85RAW target run if
the sentinel still projects `TumorBC2289_DNA / d3-5-medC` as not counted.

## Stop Conditions

Stop and review before continuing if:

- the adapter cannot distinguish ISTD from analyte without adding a hidden
  target-name exception;
- supporting MS1/RT/shape evidence is not available in product-targeted outputs;
- product projection requires changing workbook schema in a way not covered by
  this spec;
- implementation cannot add or transport a typed projection without relying on
  free-text `Reason`, `Confidence`, `NL`, or legacy score parsing;
- counted analyte `NL_FAIL` / `NO_MS2` rows are not listed in an acceptance
  artifact with paired-anchor or plausible-DDA-dropout policy support;
- implementation would require untargeted production code to trust targeted
  pass/fail labels.

## Open Follow-Up

After this migration, a separate cleanup phase should decide whether
`score_candidate(...)` remains as a useful feature extractor or should be split
into smaller evidence producers for local S/N, shape, trace, and legacy score
audit.

After implementation acceptance, durable accepted rules should be synced into
`docs/lcms-msms-evidence-rules.md` and any targeted output contract document so
future agents do not need this spec to know that legacy score/NL tokens are no
longer product authority.
