# Mature Package Flow Reference Spec

**Date:** 2026-06-02
**Status:** Draft v0.1 - product-direction reference
**Readiness label:** `diagnostic_only`
**Human-facing companion:** [Raw to final matrix product story](../reports/2026-06-02-raw-to-final-matrix-product-story.html)

## Verdict

The repo should use mature LC-MS tooling as a workflow reference, not as a
parameter authority.

MZmine, xcms, OpenMS, MS-DIAL, and Skyline all separate the same product stages:

```text
raw data
  -> trace / chromatogram feature detection
  -> sample-local peak or feature objects
  -> cross-sample alignment / correspondence / consensus feature
  -> gap filling or missing-observation query
  -> annotation / evidence / curation / QC status
  -> final quantitative matrix export
```

The important lesson for XIC Extractor is not which resolver or scorer to copy.
The important lesson is that product stages are explicit. Gap filling, consensus
feature construction, evidence states, manual curation, and matrix export are
part of the product flow, not permanent side observations.

Therefore future C4, C6, region/boundary, and AsLS/final-matrix work should
stop treating `shadow_only` and `diagnostic_only` as comfortable endpoints.
Every such path must have an exit rule:

- promote into product behavior with a named gate;
- kill or retire if it adds no product decision value;
- externalize as a diagnostic tool if it is useful but not product policy;
- or stay temporarily inconclusive with the single missing evidence named.

This spec authorizes no code, schema, output, area, selected-peak, score,
confidence, or matrix behavior change by itself. It is a direction-setting
reference that future behavior specs and goals must cite when they decide
whether to promote, retire, or externalize old semantics.

## Reference Inputs

External sources are design inputs only. They do not override repo contracts,
targeted/untargeted product differences, or the user's accepted biological
evidence rules.

| Tool | Mature-flow signal | XIC interpretation |
|---|---|---|
| MZmine | Untargeted workflow turns raw LC-MS data into feature lists, aligns corresponding features across samples, applies gap filling, then exports feature lists for downstream analysis. | Alignment, gap filling, and export should be first-class product stages, with review status preserved separately from the primary matrix. |
| xcms | `fillChromPeaks` fills missing chromatographic peaks after correspondence/grouping and flags filled peaks. Its docs warn that older feature-range integration can underestimate actual peak area. | Backfill/rescue is not inherently a failure; it should be product-stateful. The linear-edge underestimation concern aligns with the need to move settled AsLS integration semantics into final quantitation. |
| OpenMS | `FeatureFinderMetabo` creates feature maps, `MapAlignerPoseClustering` adjusts RT scales, and `FeatureLinkerUnlabeledQT` groups features into consensus maps for label-free quantification. | C6 should resemble a cross-sample peak-group or consensus-feature hypothesis, while `FAM######` and `OwnerAlignedFeature` remain compatibility delivery language. |
| MS-DIAL | LC/MS workflows expose peak detection, MS2 deconvolution, identification, alignment, curation, export, and GUI review as one product workflow. | Evidence and curation surfaces can be product surfaces if their state is explicit; they should not remain hidden sidecars forever. |
| Skyline | Small-molecule quantification uses explicit targets and stable-isotope internal standards as part of the quantification workflow. | ISTD/STD evidence can be targeted-specific product logic. It should not be generalized into untargeted identity by accident, but it also should not be treated as a weak side check. |

Reference links:

- MZmine LC-MS workflow: <https://mzmine.github.io/mzmine_documentation/workflows/lcmsworkflow/lcms-workflow.html>
- xcms `fillChromPeaks`: <https://sneumann.github.io/xcms/reference/fillChromPeaks.html>
- xcms preprocessing vignette: <https://sneumann.github.io/xcms/articles/xcms.html>
- OpenMS metabolomics tutorial: <https://openms.readthedocs.io/en/release3.0.0/tutorials-and-quickstart-guides/openms-user-tutorial.html>
- OpenMS `FeatureLinkerUnlabeledQT`: <https://www.openms.org/doxygen/release/2.5.0/html/TOPP_FeatureLinkerUnlabeledQT.html>
- MS-DIAL tutorial: <https://systemsomicslab.github.io/mtbinfo.github.io/MS-DIAL/tutorial>
- Skyline small-molecule quantification tutorial: <https://skyline.ms/tutorials/25-1/SmallMoleculeQuantification/en/>

## Product Spine For XIC Extractor

The desired repo direction is:

```text
RAW / mzML / trace input
  -> Trace / trace group context
  -> sample-local PeakHypothesis
  -> EvidenceVector + IntegrationResult + AuditTrail
  -> cross-sample peak-group hypothesis
  -> missing-observation query / accepted rescue / review rescue / rejected rescue
  -> ProductionDecision for rows and cells
  -> alignment_matrix.tsv / workbook Matrix
  -> Review / Audit / diagnostics
```

Key contract:

```text
Primary matrix = accepted quantitative values only.
Review/Audit = why a value was accepted, rescued, blanked, ambiguous,
               duplicated, contradicted, or left for review.
```

This matches the existing final-matrix contract, but it tightens one missing
piece: once an integration method is the settled product quantitation method,
its value role must be clear in the primary matrix. Keeping a new integration
method only in audit after it has been promoted as product behavior creates two
competing quantitative stories.

## Directional Rules

### Rule 1 - Product stages need owners

Each future phase must name the current and future owner for the stage it
touches:

| Stage | Future owner direction |
|---|---|
| sample-local peak interpretation | `PeakHypothesis` plus typed evidence and integration facts |
| baseline and area integration | AsLS-backed `IntegrationResult` / selected integration policy |
| boundary choice | one region-decision or model-selection contract |
| scorer facts and confidence | typed evidence, decision classes, and compatibility projections |
| cross-sample grouping | `CrossSamplePeakGroupHypothesis` or equivalent consensus-feature contract |
| missing observations | explicit gap-fill/backfill query state with accepted/review/rejected tiers |
| final matrix inclusion | `ProductionDecision` row/cell policy |

If a phase cannot name the owner, it is not ready for implementation.

### Rule 2 - Shadow is a transition, not a destination

`diagnostic_only` and `shadow_only` are valid only when they are tied to a
future decision. A shadow path that cannot change the next action should either
be externalized or retired.

Future docs and goals must avoid wording like:

```text
add another sidecar, then keep observing indefinitely
```

They should instead say:

```text
observe exactly these fields; promote/kill/externalize when this named oracle
passes or fails
```

### Rule 3 - Parity is a migration guard, not the product endpoint

Parity is required when moving behavior, adapters, or public outputs. It is not
proof that the product direction is complete.

For C4/C6/region work, a parity-only phase must close by naming the next
product decision it unlocks. If it unlocks nothing, it is not worth doing.

### Rule 4 - Evidence beats score arithmetic

Weighted scores, confidence caps, and legacy reason text can remain public
compatibility projections while outputs expose them. They should not be treated
as future product semantics.

Future product decisions should be stated as typed evidence and routing:

- accepted;
- review;
- not counted;
- excluded;
- ambiguous.

Raw-score parity may be required for compatibility output. It is not the future
scientific oracle.

### Rule 5 - Gap filling/backfill is product behavior when stateful

Backfill should be treated like a missing-observation query over an already
supported cross-sample peak group. It is not inherently less product-like than
initial detection.

However, it must be stateful:

| State | Matrix behavior |
|---|---|
| accepted rescue | write quantitative value when row identity is supported |
| review rescue | keep in Review/Audit; blank primary matrix by default |
| rejected rescue | keep reason; blank primary matrix |
| absent / no signal | blank primary matrix |

Backfill must not create row identity by itself.

### Rule 6 - Final matrix must not keep retired baseline semantics

The current AsLS baseline work retired `linear_edge` from the product baseline
direction. A final quantitative matrix that continues to publish a linear-edge
or legacy-baseline area as the primary value would contradict that decision.

The remaining product decision is not whether linear edge can stay. It cannot.
The remaining decision is how to promote AsLS into the primary matrix contract:

1. AsLS-corrected selected integration area becomes the primary quantitative
   value in `alignment_matrix.tsv`;
2. AsLS-corrected selected integration area becomes primary, and a separately
   named companion output exposes legacy/raw/rollback values only for audit;
3. an approved public schema migration exposes both, but the main product value
   is still explicitly AsLS-corrected.

Any historical linear-edge or legacy/raw value may exist only as a diagnostic,
rollback, or side-by-side validation field. It must not be the primary matrix
value, the default product value, or an unnamed fallback.

This promotion requires a behavior/output spec because it can change downstream
quantitative values.

## C4 Consequences

C4 should not end at evidence projection.

Current state:

- legacy `peak_scoring.py` still owns active production selection, confidence,
  caps, review-only logic, and reason text;
- `EvidenceVector` and `CommonEvidence` already project many scorer facts;
- C4-A/B/C closed bridge work, but did not retire scorer policy.

Mature-flow correction:

- C4 compatibility projection is useful only as a migration slice.
- The next product endpoint is a model-selection or decision-semantics layer
  over selected `PeakHypothesis` objects.
- C4-D should be framed as behavior-aware product migration, not cleanup-only,
  unless it proves exact selected-hypothesis and decision/explanation parity.

Minimum future C4 behavior spec requirements:

- selected-hypothesis oracle;
- decision class oracle;
- conflict/review/not-counted/exclusion reason oracle;
- compatibility output plan for `raw_score`, `confidence`, cap labels, and
  reason text;
- stop rule for any changed selected peak, confidence, reason, public schema, or
  workbook value.

## C6 Consequences

C6 should be interpreted through the OpenMS/xcms style of consensus features
and correspondence, not through the older `family` truth language.

Current state:

- `CrossSamplePeakGroupHypothesis` owns successor construction internally;
- `OwnerAlignedFeature` remains the concrete delivery DTO for downstream
  backfill, matrix, claim registry, consolidation, writers, and process payloads;
- `FAM######` remains public row ID compatibility.

Mature-flow correction:

- C6 is not complete until downstream product stages can consume the successor
  group contract or an explicit structural delivery adapter.
- Backfill should be named as missing-observation query / gap filling, not as a
  lower-status legacy rescue path.
- `owner_clustering.py` may be a compatibility adapter candidate, but deletion
  is not the product goal; reducing duplicate semantics is the goal.

Minimum future C6 behavior or migration spec requirements:

- exact matrix/cells/review/owner-edge parity if behavior-neutral;
- explicit row identity preservation for `FAM######`;
- structural adapter plan for backfill, matrix, claim registry, consolidation,
  writers, and process payloads;
- accepted/review/rejected rescue state preservation;
- stop rule if cross-sample membership, row inclusion, cell area, or writer
  schema changes unexpectedly.

## Region And Boundary Consequences

Region/boundary work should not stay in permanent model-selection shadow.

Current state:

- product selected peak behavior is still owned by the resolver path behind
  `find_peak_and_area(...)`;
- `region_first_safe_merge` is the only promoted region behavior and is narrow;
- `RegionSelectionDecision`, boundary hypotheses, WIS, and CWT are mostly audit
  or proposal evidence.

Mature-flow correction:

- RB0/RB1 are useful only as a foundation.
- The follow-up endpoint should be a region-decision or model-selection product
  gate that can decide when boundary evidence changes the selected interval,
  when it stays review-only, and when it is killed or externalized.
- CWT is not "weak support only"; it is an evidence source whose authority
  depends on role, opportunity, comparator, and corroborating evidence.

Minimum future RB2/RB3 behavior spec requirements:

- row-level changed-boundary audit;
- baseline method provenance, currently AsLS;
- manual or targeted EIC review oracle for changed rows;
- primary selected interval and area delta policy;
- explicit promotion/kill/externalize rule for every shadow verdict class.

## AsLS And Final Matrix Consequences

The next quantitative product decision should be written before more cleanup:

```text
What area value is the final product matrix allowed to publish?
```

Current state from existing specs:

- AsLS baseline is the product baseline direction;
- linear edge is retired from product use;
- final matrix currently writes accepted matrix area through existing selected
  cell value paths, which must be audited against the retired-linear-edge
  decision before it is treated as the final AsLS product contract;
- AsLS-corrected area and uncertainty exist as audit/integration facts, but the
  primary matrix promotion still needs an explicit output contract.

Mature-flow correction:

- a final matrix cannot have Gaussian15/AsLS evidence available while an unnamed
  legacy/raw or linear-edge-compatible value remains the product value;
- the primary matrix should prefer Gaussian15-smoothed positive AsLS residual
  area when typed MS1 morphology facts exist, with AsLS baseline-corrected area
  retained as compatibility/audit fallback;
- any raw or linear-edge-compatible value is diagnostic/rollback only and needs
  an exit rule.

Next behavior/output spec:

```text
MS1 morphology primary matrix quantitative value policy
```

See [AsLS primary matrix value policy](2026-06-02-asls-primary-matrix-value-policy-spec.md).
That historical spec is superseded for current product behavior but still
records why raw and linear-edge values were retired. Current authority is
`docs/lcms-msms-evidence-rules.md`, where Gaussian15-smoothed positive AsLS
residual area owns user-facing/final matrix area when typed morphology facts
exist.

## Updated Goal Ordering

This reference changes the preferred order for future end-to-end work:

1. **MS1 morphology primary matrix value policy**
   - because quantitation is the product endpoint;
   - behavior/output spec required.
2. **Region boundary product gate**
   - because boundary determines which trace interval area integrates;
   - RB0/RB1 remain valid as foundation only.
3. **C6 downstream successor delivery**
   - because consensus/cross-sample grouping and missing-observation query are
     product stages, not just owner-family cleanup.
4. **C4 scorer-to-decision migration**
   - because it is behavior-heavy and must not be hidden as cleanup.

This ordering is a recommendation, not a hard dependency. If a future user
request chooses another order, the chosen goal must still state which product
decision it closes.

## Acceptance For Future Specs And Goals

Any future C4/C6/region/AsLS goal that cites this spec must answer:

1. Which mature-flow stage is this touching?
2. What is the current product owner?
3. What is the successor owner?
4. Is this parity-only, behavior-changing, or output-contract changing?
5. What public values or schemas may change?
6. What is the strongest oracle: tests, targeted EIC review, 8RAW, 85RAW,
   synthetic known-area trace, or downstream matrix comparison?
7. What is the exit rule for any diagnostic or shadow path?
8. What legacy code or tests can retire after successor coverage exists?

If a goal cannot answer those questions, it should stop at spec refinement.

## Non-Goals

- No copying mature-tool parameters into XIC defaults.
- No immediate change to resolver defaults.
- No immediate deletion of `legacy_savgol`, local-minimum internals,
  `owner_clustering.py`, `OwnerAlignedFeature`, or `peak_scoring.py`.
- No treating targeted ISTD/STD rules as untargeted identity truth.
- No using external tools as final product authority over current-code evidence.
- No new public schema without a behavior/output contract.

## Stop Rules

Stop and write a narrower behavior spec if a planned cleanup:

- changes selected peak, integration bounds, area, confidence, reason text,
  cap labels, or row/cell inclusion;
- changes `alignment_matrix.tsv` values or schema;
- changes workbook sheet names/order/headers/hidden states;
- makes a diagnostic sidecar required for normal product use;
- lets one evidence source become single-source authority;
- promotes or kills a shadow path without a named oracle;
- keeps a shadow path but cannot say what evidence would promote, kill, or
  externalize it.
