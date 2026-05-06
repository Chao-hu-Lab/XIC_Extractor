# NuMoFinder-Inspired MS2 Evidence And Discovery Spec

**Date:** 2026-05-06
**Status:** Draft
**Implementation plan:** Not written yet. This document defines direction and product contract only.

---

## 1. Summary

NuMoFinder is a useful design reference because it treats nucleoside modification discovery as a combined MS1/MS2 problem:

1. search MS1 traces for candidate precursor peaks,
2. extract MS2 product-ion traces,
3. align MS2 product evidence back to MS1 peaks by retention time,
4. use DNA/RNA neutral-loss mass logic to support known and unknown nucleoside modifications.

XIC Extractor should not copy NuMoFinder's implementation directly. The useful transfer is the evidence model:

- MS2 evidence should become trace-level and candidate-aligned, not just target-window presence/absence.
- Neutral-loss evidence should support both targeted quantification and future unknown discovery.
- Clean-matrix tissue data should be the model-building baseline. Complex matrices such as urine are later stress tests and optimization targets.
- The long-term direction is not only targeted extraction. The project should leave a deliberate path toward semi-targeted and eventually untargeted nucleoside modification discovery.

This spec defines the target evidence model and phased product direction. It does not define implementation tasks.

## 2. Reference Scope

### 2.1 NuMoFinder as design reference

Reference repository:

```text
https://github.com/ChenfengZhao/NuMoFinder
```

Relevant observed source concepts:

| NuMoFinder concept | Why it matters for XIC Extractor |
|---|---|
| MS1 peak search by m/z trace | Confirms the core problem is chromatographic candidate formation, not only formula matching. |
| MS2 product-ion extraction | MS2 evidence can be a trace with its own apex, area, and RT behavior. |
| MS1/MS2 RT alignment tolerance | MS2 support should be evaluated near the candidate peak, not globally across the target window. |
| `Matched_Counts` | Multiple product ions / matched MS2 records can become evidence strength. |
| DNA/RNA fixed neutral-loss masses | Neutral-loss mass logic can be reused for targeted and unknown discovery. |
| Unknown search from MS2 product masses | Long-term untargeted direction: infer precursor candidates from fragment/product evidence. |
| Relative MS1/MS2 height and area | Useful reporting/debug signals, especially for evidence confidence. |

### 2.2 What is explicitly not imported

The following are not project decisions for XIC Extractor:

- Do not switch the raw-data path from Thermo RawFileReader to `.mzXML` / `.mzML`.
- Do not replace current workbook-centered delivery with NuMoFinder's CSV-only output.
- Do not adopt NuMoFinder's hard peak filters as ND gates.
- Do not replace current area integration with NuMoFinder's Simpson integration over smoothed traces.
- Do not assume NuMoFinder's nearest-precursor behavior is strict enough for current candidate-level NL validation.
- Do not add an untargeted mode before targeted evidence semantics are stable.

## 3. Product Direction

XIC Extractor should evolve in three layers.

### 3.1 Layer 1: Targeted MS2 Trace Evidence

This is the next practical direction.

Given a target and selected MS1 candidate, the system should evaluate whether MS2 evidence supports that same candidate:

- Is there MS2 trigger evidence near the candidate RT?
- Is the strict observed neutral loss valid for the candidate-aligned MS2 scans?
- Do product-ion intensities form a plausible local trace?
- Does the MS2 product apex align with the MS1 candidate apex?
- Is MS2 evidence strong enough to increase confidence or weak enough to explain a review flag?

This layer remains targeted. It does not discover new compounds.

### 3.2 Layer 2: Semi-Targeted Neutral-Loss Discovery

After targeted evidence is stable, the system may propose unknown candidates using constrained domain assumptions:

- known DNA/RNA neutral-loss masses,
- known polarity/adduct assumptions,
- user-provided RT and m/z bounds,
- optional database exclusion for already-known targets,
- evidence shown as review candidates, not final quantitative results.

Semi-targeted candidates should be reported separately from targeted quantification.

### 3.3 Layer 3: Untargeted NuMo Discovery

The long-term goal is an untargeted or near-untargeted nucleoside modification discovery workflow:

1. scan MS2 spectra for product ions consistent with DNA/RNA nucleoside chemistry,
2. infer possible precursor masses from neutral-loss relationships,
3. return to MS1 traces to find chromatographic candidates,
4. score candidates using MS1 shape, MS2 trace, neutral loss, isotope/adduct/domain evidence, and cross-sample patterns,
5. generate a discovery report with candidate identity, evidence, uncertainty, and review priority.

This layer should be designed as a discovery workflow, not as an overload of the existing targeted result table.

## 4. Model-Building Principle

Clean-matrix tissue data is the preferred model-building set.

Reasoning:

- clean matrix makes correct chromatographic behavior easier to identify,
- ISTD RT trend and expected target distribution are easier to reason about,
- false positives from matrix complexity are less likely to dominate early parameter decisions,
- the resulting evidence model can later be hardened against urine and other complex matrices.

Complex matrix validation remains important, but it should be used as a robustness test after the clean-matrix behavior is coherent.

## 5. Targeted Evidence Contract

### 5.1 Candidate-aligned MS2 evidence

Every selected MS1 candidate should be able to receive MS2 evidence scoped to that candidate.

Candidate-aligned means:

- evidence is evaluated relative to the selected candidate RT or peak region,
- evidence is not borrowed from unrelated MS2 scans elsewhere in the target RT window,
- workbook and reason text should distinguish broad target-window MS2 trigger from strict candidate-aligned NL support.

### 5.2 Trace-level MS2 evidence

MS2 should support more than a boolean pass/fail.

Suggested v1 evidence fields:

| Field | Meaning |
|---|---|
| `ms2_trigger_count_near_candidate` | Number of MS2 scans near the selected MS1 candidate. |
| `strict_nl_match_count_near_candidate` | Number of candidate-aligned scans with observed neutral loss within tolerance. |
| `ms2_product_peak_count` | Number of local product-ion peaks aligned with the MS1 candidate. |
| `ms2_product_apex_rt` | Apex RT of the strongest aligned MS2 product trace. |
| `ms2_product_apex_delta_min` | Difference between MS1 candidate apex RT and MS2 product apex RT. |
| `ms2_product_height` | Height/intensity of the strongest aligned MS2 product peak. |
| `ms2_product_area` | Optional area of the aligned MS2 product trace. |
| `ms2_trace_continuity` | Whether product evidence is trace-like rather than isolated scan noise. |
| `ms2_evidence_strength` | Derived soft signal: `none`, `weak`, `moderate`, or `strong`. |

These fields may initially remain internal or appear only in technical/debug output. They should not force a default workbook schema change unless a later UX decision requires it.

### 5.3 Scoring behavior

MS2 trace evidence should be soft evidence.

Expected behavior:

- Strong candidate-aligned MS2 evidence may increase confidence or break candidate ties.
- Weak MS2 evidence may lower confidence and add review reasons.
- Missing MS2 trigger may remain a warning when DDA stochasticity is plausible.
- Strict observed NL failure should remain important, but reason text must make clear whether the failure is candidate-aligned.
- Trace-level evidence should not override a clearly invalid MS1 candidate by itself.

### 5.4 Relationship with current ADAP-like trace quality

ADAP-like trace quality and MS2 trace evidence solve different problems:

| Layer | Question |
|---|---|
| MS1 trace quality | Is the extracted chromatographic candidate plausible? |
| MS2 trace evidence | Does fragmentation evidence support this same candidate? |
| NL validation | Is the observed product/precursor relationship chemically consistent? |
| ISTD/RT evidence | Is the candidate consistent with expected retention behavior? |

The scoring model should keep these signals separate before combining them into confidence and reason text.

## 6. Semi-Targeted Discovery Contract

Semi-targeted discovery should be explicitly opt-in.

Inputs:

- raw file or batch,
- polarity,
- nucleoside type: DNA, RNA, or both,
- neutral-loss mass assumptions,
- m/z search range,
- RT search range,
- product-ion intensity threshold,
- optional known-target/database exclusion list.

Outputs:

- candidate precursor m/z,
- inferred product m/z or neutral loss,
- candidate RT,
- MS1 trace evidence,
- MS2 product trace evidence,
- observed neutral-loss evidence,
- whether candidate overlaps a known target,
- review priority and reason.

Semi-targeted output should not silently merge into targeted quantification. It should be a candidate-discovery artifact.

## 7. Untargeted Discovery Contract

The eventual untargeted workflow should be evidence-first, not name-first.

Candidate identity states:

| State | Meaning |
|---|---|
| `known_target` | Candidate matches a configured target. |
| `database_candidate` | Candidate matches an external nucleoside modification database. |
| `neutral_loss_candidate` | Candidate is inferred from neutral-loss/product evidence but lacks database identity. |
| `unknown_candidate` | Candidate has reproducible MS1/MS2 evidence but unresolved chemistry. |

Untargeted results must be treated as hypotheses. They require a discovery review report, not only quantitative area values.

## 8. Reporting Direction

### 8.1 Targeted reporting

Targeted Excel remains the official delivery artifact.

Possible future additions:

- optional Score Breakdown fields for MS2 trace evidence,
- HTML plots showing MS1 and MS2 product traces around selected candidate RT,
- candidate-aligned NL evidence summary,
- clearer distinction between `MS2 triggered`, `strict NL matched`, and `candidate-aligned product trace`.

### 8.2 Discovery reporting

Discovery output should be visual-first:

- candidate list sorted by evidence strength,
- MS1 trace beside MS2 product trace,
- precursor/product/neutral-loss table,
- cross-sample recurrence heatmap,
- known-target overlap warning,
- review action: accept, reject, merge with known target, or add as new target.

Excel can remain exportable, but discovery review should not rely on Excel alone.

## 9. Validation Strategy

### 9.1 Targeted evidence validation

Use clean tissue first.

Representative checks:

- selected candidate should not change for strong clean peaks,
- MS2 trace evidence should explain cases where MS1 shape is weak but product evidence is strong,
- candidate-aligned NL should reduce misleading target-window NL pass/fail text,
- 8-raw validation subset should show interpretable Review Queue reasons,
- full tissue batch should be used only after subset behavior is stable.

### 9.2 Complex matrix validation

Use urine or other complex matrices after clean tissue behavior is coherent.

Purpose:

- detect false positives from matrix product-ion noise,
- test whether MS2 trace evidence over-promotes poor MS1 candidates,
- tune soft evidence weights without breaking clean-matrix behavior.

### 9.3 Discovery validation

Discovery validation requires different truth criteria:

- reproducibility across injections/samples,
- chromatographic co-elution of MS1 and MS2 evidence,
- plausible neutral-loss relationship,
- absence/presence in expected sample classes,
- manual inspection of high-priority candidates.

Area accuracy is not the first metric for discovery candidates.

## 10. Non-Goals For The Next Implementation Stage

The next implementation stage should not:

- implement full untargeted discovery,
- switch default resolver,
- add new GUI-heavy controls before evidence semantics are stable,
- change default workbook schema,
- change area integration,
- convert `.raw` files to `.mzML`, `.mzXML`, or other intermediate formats,
- make NuMoFinder a runtime dependency.

## 11. Open Questions

1. Should MS2 product trace area be calculated on raw product-ion intensities, smoothed product-ion intensities, or both?
2. Should candidate-aligned MS2 evidence use candidate peak boundaries or a fixed RT half-window around MS1 apex?
3. Should strong MS2 evidence be allowed to rescue weak MS1 candidates, and if yes, how much?
4. What minimum evidence is needed before a semi-targeted candidate appears in a discovery report?
5. Should DNA/RNA neutral-loss masses be fixed internal constants or user-visible method profile values?
6. How should external modification databases be versioned and recorded in run metadata?

## 12. Acceptance Criteria For This Spec

This spec is ready for implementation planning when:

- targeted MS2 trace evidence is accepted as the next practical implementation layer,
- semi-targeted and untargeted discovery are accepted as future layers, not immediate scope,
- clean tissue is accepted as the primary model-building validation set,
- complex matrix validation is accepted as a later robustness step,
- NuMoFinder remains a design reference, not a dependency or code source to copy.
