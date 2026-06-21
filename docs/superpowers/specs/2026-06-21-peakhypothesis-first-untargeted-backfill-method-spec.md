# PeakHypothesis-First Untargeted Discovery And Backfill Method Spec

Status: `design_input` / `diagnostic_only`.

Updated: 2026-06-22

## Plain-Language Decision

The current problem is not solved by lowering one threshold. The method needs a
clearer identity model.

`family` is an evidence/provenance bucket. It is not automatically the final
feature ID, and it must not become ProductWriter authority by itself. Multiple
families can point to the same real MS1 trace because they came from different
DDA/MS2 seeds, precursor/product contexts, source/successor migrations, or
alignment histories.

The product-facing unit should be:

```text
source family / discovery family / successor family
  -> evidence provenance
  -> PeakHypothesis / collapsed MS1 trace identity
  -> sample-local cell evidence
  -> workflow-specific product gate
  -> ProductWriter only after an explicit activation contract
```

In short: preserve family provenance, but make the method judge the collapsed
MS1 hypothesis and its sample cells.

## Rule-First Contract

Work question:

- Can the current CID-NL-derived Backfill expansion candidate packet be
  advanced toward product readiness without projecting family-level evidence
  onto cells that did not earn it?

Demonstration evidence:

- Current 666-cell Backfill expansion packet.
- Full-chain checker result: `374/666` pass, `292/666` held.
- Shift-aware sensitivity artifacts showing that whole-family thresholding is
  too blunt.
- Calibration cases discussed in review:
  - `FAM017098`: mixed small-peak/big-peak pattern, with the NL-tagged
    hypothesis on the larger peak near 15 min.
  - `FAM020411`: clean single main hypothesis near 8 min.
  - `FAM016893` and `FAM012491`: useful borderline calibration cases.

Proposed rule:

- Use standard-peak evidence to prove a defensible hypothesis boundary.
- Use shift-aware similarity as a selective source-family / sample-cell support
  gate, not as an all-or-nothing family promotion gate.
- Ignore source families that do not point to the selected hypothesis instead
  of letting them block unrelated matching cells.
- Keep own-max evidence as a per-cell same-peak support requirement.
- Product writing still requires expected diff, provenance, writer scope, and
  control-plane coverage.

Full relevant scope:

- Current bounded Backfill expansion packet: 666 cells.
- Current CID-NL Discovery default activation remains the already accepted
  95-cell Discovery lane and is not reopened by this spec.

Ambiguous bucket:

- Cells with conflicting source families.
- Cells where the NL-tagged anchor and strongest MS1 peak disagree.
- Cells where the same sample subtype is internally RT-incoherent.
- Cells where cross-subtype RT shift may explain a mode split but boundary or
  same-peak support is still unresolved.
- Cells with non-standard or multi-peak traces where the selected hypothesis
  boundary cannot be defended.
- Cells with missing or below-threshold own-max evidence.

Expected output/change:

- First output: diagnostic selective-gate TSV/summary over the 666-cell packet.
- Later output, only after acceptance: a bounded expected-diff/authority
  contract for the accepted cells.

Near-neighbor work excluded:

- Broad Backfill.
- Workbook/GUI behavior.
- Default matrix activation without a new expected-diff contract.
- Discovery row deletion, demotion, or merge decisions.
- Treating sparse untargeted rows as failures solely because prevalence is low.

Stop rule:

- Stop if the method requires a second Discovery system, a second ProductWriter
  path, family-level evidence projection to cells, broad Backfill policy, or a
  public output change without expected diff.

## Vocabulary And Ownership

| Term | Meaning in this spec | Authority boundary |
| --- | --- | --- |
| `source_family` | Original provenance bucket that supplied evidence for a candidate. | Evidence only. |
| `discovery_family` | Discovery grouping or seed-derived family context. | Evidence/provenance only. |
| `successor_family` | Candidate successor row context after Discovery/alignment migration. | Candidate row context only. |
| `PeakHypothesis` | Collapsed MS1 trace identity with selected RT/m/z window, boundary, evidence vector, and audit trail. | Can feed product gates; not direct writer authority. |
| `sample cell` | `PeakHypothesis + sample_stem` value/evidence unit. | Can pass, hold, review, or block through workflow gates. |
| `ProductWriter` | Public matrix/workbook/CSV writer boundary. | Requires registered scope, expected diff, provenance, tests, and control-plane/status coverage. |

Required invariant:

- A product action must name the `PeakHypothesis` and the `sample cell`.
  Family provenance may explain the action, but it cannot replace those keys.

## Method Direction

### 1. Discovery Feature Inclusion

Untargeted analysis should be inclusive. If a successor candidate has its own
CID-NL tag evidence and a real MS1/quant peak, low prevalence is not a product
blocker by itself. Downstream feature filtering owns prevalence and missingness
filtering.

Therefore:

- Source/successor m/z or RT mismatch can be identity evidence, merge evidence,
  or migration evidence.
- It must not block a successor that has its own tag and MS1 peak evidence from
  being considered as a feature.
- Existing guardrails remain:
  - `300.1605 -> 184.113` stays recovered as source context.
  - `301.165 -> 185.116` stays preserved as its own tag-backed pair.

### 2. Backfill Expansion

Backfill is harder than Discovery because it fills missing sample cells for an
existing accepted hypothesis. It must prove that the missing cell belongs to the
same MS1 hypothesis, not merely that a nearby signal exists.

The full chain remains:

1. expected-diff/provenance row exists;
2. sample-local source evidence exists;
3. RAW trace identity is observed;
4. standard-peak boundary is defensible;
5. shift-aware same-hypothesis support exists for the relevant source family or
   cell;
6. own-max same-peak metric passes for the cell;
7. product-authorized MS1 sidecar row can be joined by stable keys;
8. writer authority is granted only through a separate activation contract.

The current `374/666` pass result is useful evidence, but it is not the final
method because step 5 is currently too family-wide.

### 3. Selective Shift-Aware Gate

Current issue:

- A whole-family shift-aware gate can reject a clean hypothesis because one
  unrelated or weak source family does not align.
- It can also overstate support if it treats family-level support as if every
  cell in the family passed.

Replacement rule:

```text
standard peak boundary required
  + source-family or cell points to selected hypothesis
  + own-max same-peak support for the cell
  = eligible support for that cell only
```

Operational details:

- Keep Gaussian smoothing for review/shape evidence.
- Keep standard-peak boundary as a required hypothesis-boundary gate.
- Do not use one `family_r >= threshold` as final product support.
- Use a loose source-family/hypothesis similarity threshold only to decide
  which groups deserve attention.
- Use a stricter source-family or per-cell support rule to decide which cells
  can pass.
- If a source family points to a different peak mode, mark that source family or
  its cells as held/ignored for this hypothesis instead of blocking unrelated
  matching source families.
- If a sample has only the wrong peak mode, hold that sample cell unless its own
  NL tag/trace proves the selected hypothesis.

Subtype-aware RT coherence:

- Within the same biological/sample subtype, RT for the same hypothesis should
  usually be relatively tight. A same-subtype RT outlier is stronger evidence
  for a wrong peak mode, bad boundary, or unresolved competing hypothesis.
- Across different sample subtypes, such as Tumor, Normal, and Benignfat, larger
  RT shifts are more plausible and should not be treated as automatic identity
  failure.
- Cross-subtype shift is explanatory evidence, not authority. A shifted cell
  still needs its own MS1 peak, same-peak/own-max support, defensible boundary,
  tag/source provenance, and expected-diff authority before writing.
- The long-term implementation should derive subtype from sample metadata when
  available. Filename prefixes can be used only as a diagnostic approximation.
- Current diagnostic default: flag same-subtype RT span above `0.50 min` for
  review. This is a review threshold, not a ProductWriter tolerance.
- The current diagnostic also emits a compact `family + sample_subtype` split
  review queue so human/AI review sees ambiguous groups, not all flagged cells.
- The current diagnostic split decision packet routes flagged groups into:
  clean target-mode candidates that may feed the full evidence chain,
  target-mode cells whose boundaries must be reviewed first, off-target cells
  that must be held/remapped, and missing/unclassified cells. This routing is
  diagnostic-only and cannot activate matrix writes by itself.
- The clean-target replay consumes the same selective source-family evidence
  through the existing MS1 product-authority sidecar schema. This is not a new
  ProductWriter path: it only changes which evidence can produce sidecar rows.
  Current replay result: the old full-chain baseline remains 51/112 pass, but
  selective source-family projection reaches 84/112 pass and leaves 28 true
  method holds.
- The current bounded default activation filters the existing
  expected-diff/provenance contract down to those 84 projected-pass clean-target
  cells. It replays 84 matrix changes across 7 rows, has 0 unused
  expected-diff rows, and writes externalized default matrix/provenance outputs
  plus compact tracked summary/check/manifest files. It is now
  `production_ready` for the registered
  `backfill_expansion_clean_target_selective_activation_84_cells` scope only.
  The default matrix/ProductWriter change is bounded to those 84 cells; workbook,
  GUI, selected peak, selected area, and counted detection remain unchanged.

Threshold stance:

- `0.95` is too strict as a universal final cutoff.
- This spec does not promote a new product threshold yet.
- The next diagnostic replay should evaluate a parameter grid, with candidate
  defaults documented separately before any product activation:
  - loose attention threshold around `0.85`;
  - selective support threshold around `0.90`;
  - own-max threshold remains unchanged unless a separate sensitivity review
    justifies changing it.

The important change is the unit of judgment, not the exact numeric cutoff.

### 4. PeakHypothesis Collapse

Many families pointing to the same MS1 trace is expected under the old
provenance model. It becomes a problem only if the code treats each family as a
final product ID.

The adjusted method should produce or approximate a collapse map:

```text
family evidence rows
  -> candidate PeakHypothesis group
  -> selected hypothesis anchor RT/m/z
  -> contributing source families
  -> included / ignored / held cells
```

Collapse criteria should be based on:

- same or compatible RT apex/boundary;
- same-subtype RT coherence and cross-subtype RT-shift compatibility;
- same m/z window with review display at four decimal places;
- matching CID-NL/product-ion tag context where relevant;
- same-peak own-max/shape support;
- absence of unresolved competing-peak conflict;
- stable provenance back to the source evidence rows.

Collapse must not delete source rows or erase provenance. It only tells the
gate which evidence buckets describe the same product hypothesis.

## Implementation Phases

### Phase 0 - Freeze The Spec And Scope

Tasks:

- Add this spec as the method contract.
- Do not change ProductWriter/default matrix/workbook/GUI.
- Do not change active authority lanes.

Deliverables:

- This spec.
- A short handoff note only if the active next step changes.

Acceptance:

- File is reviewed as `design_input`.
- Control plane is unchanged unless authority/tier/active lane changes.

### Phase 1 - Diagnostic Collapse Map

Tasks:

- Build a no-RAW diagnostic map over the current 666-cell packet.
- Join families, source families, successor context, tag evidence, RT/m/z, and
  existing overlay/trace evidence into candidate `PeakHypothesis` groups.
- Preserve all source provenance.

Deliverables:

- Compact TSV/summary under a retained validation path.
- Counts by hypothesis, source family, sample cell, included/ignored/held.

Acceptance:

- No ProductWriter or matrix changes.
- The map explains why multiple families can point to one hypothesis.
- `FAM017098` is represented as a 15-min anchored hypothesis with non-matching
  peak modes held or ignored, not as a whole-family failure. The diagnostic also
  reports whether the 14.x/15.x mode split is coherent within or across sample
  subtypes.
- `FAM020411` is represented as the 8-min main hypothesis, not rejected only
  because unrelated family evidence is weak.
- The compact split decision packet explains whether each flagged
  `family + sample_subtype` group has clean target-mode cells for the next
  evidence chain, boundary-bridged cells that must remain held, or off-target
  cells that require remap/hold.
- The clean-target-only full-chain replay projects those clean target cells back
  onto the existing evidence chain. Current diagnostic result: 51/112 clean
  target candidates pass, 61/112 remain held. This means peak-mode cleanup is
  necessary but not sufficient for Product Ready.

### Phase 2 - Selective Shift-Aware Checker

Tasks:

- Add a checker that replays the 666-cell packet with selective shift-aware
  evidence.
- Report per-cell states:
  - `pass`;
  - `held_no_standard_peak_boundary`;
  - `held_shift_aware_not_same_hypothesis`;
  - `held_own_max_missing`;
  - `held_own_max_below_threshold`;
  - `held_conflicting_peak_mode`;
  - `held_same_subtype_rt_incoherent`;
  - `review_cross_subtype_rt_shift`;
  - `ignored_source_family_not_this_hypothesis`.

Deliverables:

- Checker script/test.
- Summary TSV/JSON.
- Optional overlay review index for newly rescued and newly held cells.

Acceptance:

- Existing `374/666` pass cells remain explainable.
- Newly passing cells must pass by cell/source-family evidence, not family
  projection.
- Held cells include explicit reasons.

### Phase 3 - Full-Chain Integration

Tasks:

- Replace or augment the current whole-family shift-aware gate in the full-chain
  diagnostic with the selective gate.
- Keep expected-diff, sample-local, RAW trace identity, own-max, and MS1
  product-authority sidecar joins intact.

Deliverables:

- Updated full-chain diagnostic summary.
- Focused tests for exact key joins, pass/hold reasons, and no writer authority.

Acceptance:

- `--require-full-chain` still fails until the accepted scope is truly complete.
- The checker cannot silently pass a cell when any required evidence is missing
  or unjoinable.
- Product authority fields remain false unless an activation contract is added.

### Phase 4 - Full Scope Replay

Tasks:

- Replay the diagnostic over the full 666-cell packet.
- Run 8RAW smoke only if the no-RAW replay changes method behavior enough that
  stale trace evidence is a concern.
- Do not rerun 85RAW unless it closes a product decision that no existing
  artifact can answer.

Deliverables:

- Updated pass/hold count.
- Review queue containing only genuinely ambiguous or conflicting cells.

Acceptance:

- Obvious pass/fail cells are machine-classified.
- Human review is limited to ambiguity, conflict, or rule gaps.
- Sparse untargeted prevalence is not treated as a false-positive reason.

### Phase 5 - Product Activation Contract

Tasks:

- If the accepted set is bounded and defensible, write a new expected-diff and
  authority contract for that set only.
- Decide whether to promote:
  - all 666 cells, if full-chain support reaches 666/666; or
  - a bounded subset, if the product decision explicitly accepts subset
    activation.

Deliverables:

- Expected-diff/provenance artifact.
- Authority manifest/status-index update, if writer authority changes.
- Control-plane update, if tier, active lane, authority, schema, or public
  surface changes.

Acceptance:

- Exact keyset and value checks pass.
- No default matrix drift outside the accepted set.
- ProductWriter authority is named and registered.
- Heavy matrices and generated overlays remain out of git.

Current activation result:

- `backfill_expansion_clean_target_selective_product_activation_v1` is the
  production-ready expected-diff/provenance activation for the 84
  projected-pass clean-target cells.
- The packet excludes the 28 projected-held clean-target cells, 37
  boundary-review cells, and 29 off-target hold/remap cells.
- The active scope is
  `backfill_expansion_clean_target_selective_activation_84_cells`; it is
  registered in the authority manifest, status index, and control plane.

### Phase 6 - Teaching And Maintenance Docs

Tasks:

- Update the evidence-chain source of truth if a durable evidence provider,
  state, gate, or authority boundary changes.
- Update the HTML guide only after the source of truth is stable.

Deliverables:

- Source-of-truth diff.
- Optional human guide update for the adjusted evidence chain.

Acceptance:

- The guide explains family provenance vs `PeakHypothesis` identity.
- The guide does not imply diagnostic artifacts are writer authority.

## Product Safety Invariants

- Do not maintain two Discovery systems.
- Do not make CID-NL/MS2 evidence direct ProductWriter authority.
- Do not change default matrix/ProductWriter/workbook/GUI/Backfill authority
  from this spec alone.
- Do not demote or delete `301.165 -> 185.116` while it has its own tag
  evidence.
- Do not hide a new method behind an unrelated `scripts/run_discovery.py`
  flag.
- Do not put full matrices, full opportunity maps, or large overlay bundles in
  git.
- Do not treat candidates as matrix rows.
- Do not project row/family evidence onto sample cells.

## Review Display Requirements

- m/z values in review-facing overlays and titles should display four decimal
  places where practical.
- Four-decimal display is a review/readability change only. It must not change
  extraction windows, tolerance math, row identity, or ProductWriter behavior.
- Overlay legends must state whether a trace is source-family provenance,
  successor/hypothesis evidence, or sample-local cell evidence.

## Success Criteria For Method Adjustment

The method adjustment is acceptable when:

1. The code can explain why several families point to one MS1 trace without
   turning that into duplicate product IDs.
2. The 666-cell packet is classified by a selective hypothesis/cell rule, not a
   whole-family shortcut.
3. `FAM017098` and `FAM020411` are handled according to their selected
   hypotheses rather than rejected by unrelated family-wide evidence.
4. Every pass/hold decision names stable row, sample, provenance, tag/source,
   and evidence state.
5. Product activation, if any, is driven by expected diff and authority
   manifest updates, not by diagnostic counts alone.
