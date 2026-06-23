# Backfill Auto-Write Ground-Truth Critical Review - 2026-06-18

Status: strategy reset / implementation hold. This is not a new design program.

Decision challenged: can Backfill stop adding hand-carved writer slices without
replacing them with another open-ended stack of design artifacts?

## Verdict

The strategy reset is directionally correct, but it is not yet an
implementation ticket for broader matrix writes.

The correct product objective is:

1. mechanically adjudicate all 4613 candidate rows;
2. keep ProductWriter as the only matrix-writing authority;
3. write only rows with explicit `write_ready` authority and expected-diff pass;
4. turn unresolved rows into review/evidence tasks with clear reasons.

The next Backfill step is one read-only gate packet,
`backfill_ground_truth_gate_v1`. It is not another
`quality_blockers`-derived evidence slice, not a ProductWriter expansion, and
not a commitment to build a model.

## Plain Language

`4613 rows` means candidate cells where the extractor already has a candidate
MS1 morphology area. It does not mean 4613 approved writes.

Current approved product writing is still 511 cells. The useful broadening
target is the 3015 dirty-but-trace-matched cells, because they have stored trace
provenance but no approved evidence class. The 1087 `missing_overlay_path` cells
are not auto-writeable under the current evidence contract because there is no
stored trace to verify.

The current heldout trace oracle mostly asks: if we reintegrate this stored
trace, do we get nearly the same boundary and area? That is useful, but it does
not by itself prove the original peak choice was biologically or chemically
correct. The suspected hard failure is wrong-small-peak or family confusion,
especially visible in ISTD behavior.

## Fact Revalidation

Confirmed in this review:

- Backfill promotes the cell's own MS1 morphology area. In
  `xic_extractor/alignment/shared_peak_identity_explanation/product_activation.py`,
  `ACTIVE_PRIMARY_MATRIX_AREA_SOURCES` only includes
  `MS1_MORPHOLOGY_PRIMARY_MATRIX_AREA_SOURCE`, and
  `_matrix_value_for_activation()` returns `primary_matrix_area` only for those
  sources.
- Current 85RAW generated-policy replay remains 4613 policy rows, 511
  `write_ready`, 0 `detected_flagged`, and 4102 `blocked`. The expected-diff
  writer packet writes 511 cells and passes.
- The six active ISTDs are mapped by `targeted_istd_benchmark` selected family
  IDs, not by naive monoisotopic m/z grep. In the benchmark summary, all six
  active ISTDs have 85/85 untargeted positives.
- A small no-RAW matrix check over those six ISTD families found no sample above
  3x median, while every family has low-side outliers. This supports the working
  hypothesis that observed morphology/integration failures are mostly
  under-estimation, not inflation.

Facts that still need to be pinned before product implementation:

- The under-estimation claim should be joined to targeted per-sample areas when
  available. Current matrix evidence supports direction, but not a final
  absolute error bound.
- The 3015 dirty-but-traced rows need a current feature distribution summary so
  degraded ISTD traces can be compared against real dirty rows. If synthetic
  dirty traces do not cover the real dirty distribution, the labels are not
  enough.
- The 1087 missing-trace rows need trace regeneration or must remain blocked.
  They cannot be rescued by a model trained on traced rows.

## Minimal Gate

Do not start with degradation code or a classifier. First make one small,
auditable packet that can answer whether broad Backfill has a simple product
gate or should stay parked.

`backfill_ground_truth_gate_v1` must contain only these sections:

1. `facts`: re-confirm the 4613 / 511 / 3015 / 1087 counts and input hashes.
2. `ISTD truth`: selected-feature mapping, signed area error against an
   independent reference where available, and low/high outlier direction.
3. `dirty profile`: feature distribution for the 3015 dirty-but-traced rows
   compared with the 511 approved rows.
4. `acceptance table`: numeric pass/fail thresholds for any future gate,
   including selection correctness, signed area error, leakage-free split unit,
   family-confusion failure, and minimum coverage of the 3015 rows.

The current round-trip oracle output must not become model training labels. It
can test reintegration determinism, but it is blind to a wrong starting peak.

If this packet cannot express a short, human-readable gate, broad Backfill
should stay `blocked` / `parked` instead of accumulating more diagnostics.

Do not treat 8RAW as an independent batch-transfer proof unless the packet
justifies why it is independent enough for that claim; otherwise call it a
smaller historical validation subset.

## Edge Cases / Failure Modes

Block broader writing until these are explicitly handled:

- Family confusion or wrong-small-peak selection. Degrading one clean trace does
  not reproduce an alignment/family-assignment mistake.
- `isotope_shift` target mapping. ISTD family lookup must use
  `targeted_istd_benchmark.selected_feature_id`.
- Missing trace / overlay rows. These must stay `blocked` until trace evidence
  exists.
- Low signal where scan count, width, height, and apex delta interact. Avoid
  another nested height/scan/shape rule unless it collapses into a tested
  calibrated gate.
- Batch transfer. A threshold tuned on the 85RAW fixture must be challenged on a
  separate batch or a sealed lockbox before it claims product authority.

## Dependency Chain / Self-Consistency

The dependency chain should be:

```text
candidate row
  -> mechanical adjudication
  -> evidence grade / decision / write authority
  -> ProductWriter expected-diff
  -> matrix write
```

It must not become:

```text
quality blocker token
  -> hand-written slice
  -> direct matrix write
```

Quality sidecars remain explanation-only. They may create review questions or
evidence tasks, but they do not create write authority.

If an `authority_manifest` or candidate-adjudication schema is added, that is a
public contract and needs docs plus focused tests before any ProductWriter
behavior changes.

## Required Next Artifact

Before any code change that broadens Backfill writer authority, produce one
small read-only artifact:

`docs/superpowers/notes/backfill_ground_truth_gate_v1.md`

That artifact should fit on one readable page plus tables/links. If it needs a
large design tree to explain why rows are safe, it is not ready to feed
ProductWriter.

## Stop Rules

Stop immediately if any broader Backfill plan does one of these:

- trains or approves rows using only the existing round-trip reintegration
  oracle;
- treats `quality_blockers` as writer authority;
- includes `missing_overlay_path` rows without regenerated trace evidence;
- cannot explain each auto-written row with evidence grade, authority source,
  threshold, and expected-diff status;
- does not define numeric acceptance criteria strong enough to fail a bad
  model;
- cannot separate single-trace integration error from family-confusion error;
- requires more diagnostic sidecars without changing the product decision;
- changes selected peak, selected area, counted detection, workbook values, or
  primary matrix values without a public expected-diff contract.

## Placement

This note belongs under `docs/superpowers/notes/` because it is a strategy
review and implementation gate. The control plane remains the tier authority.
The current handoff should point here as the first Backfill read for the next
agent.
