# Confidence / Reason / Detection Precedence Contract

This is the single quick-reference for **where the final `Confidence`, `Reason`,
and counted-detection values on a targeted workbook row come from**. It is a
code-anchored map, not a rationale document.

- Design rationale and the authority-migration decision live in
  `docs/product/alignment.md` and `docs/product/evidence-spine.md`; the dated
  targeted evidence-chain spec is retained only as a migration/history stub.
- Module ownership lives in `docs/architecture-contract.md`.
- This file only answers: *given a row, which layer decided its displayed
  `Confidence` / `Reason` and whether it counts?* Keep it in sync when any of the
  cited functions change.

## Authority, highest to lowest

`TargetedProductProjection` is the authority. Legacy `Confidence` / `NL` / score
/ cap fields are **evidence inputs**, not deciders (spec §"Product Contract").
The displayed cell value is resolved through these layers in order; a higher
layer overrides a lower one.

| # | Layer | Produces | Resolution point |
| --- | --- | --- | --- |
| A | Candidate scoring | `peak_result.confidence` / `peak_result.reason` (from `EvidenceSignalSet` + severities) | `peak_detection/candidate_scoring.py` via `peak_detection/facade.py:find_peak_and_area` |
| B | Hypothesis selection decision | `selection_decision.projected_confidence` / `projected_reason` | `extraction/result_assembly.py:_result_confidence` (169), `:_result_reason` (180) — used **only when `selection_decision is not None`**, else falls back to layer A (`peak_result.confidence or "HIGH"`) |
| C | Stored result | `result.confidence` / `result.reason` (= resolved A or B) | `extraction/result_assembly.py:build_extraction_result` (71-72) |
| D | Targeted product projection | `product_state`, `counted_detection`, `projection_reason` (built from hypothesis `decision_semantics` + `selection_decision` overlay + role-aware downgrade rules) | `extraction/result_assembly.py:_targeted_product_projection` (198-309) |
| E | Display resolution | the values written to the workbook / CSV | `output/csv_writers.py:_display_confidence` (335), `:_display_reason` (328) |

## What each consumer actually reads

- **Displayed `Confidence` cell** — `_display_confidence` (csv_writers.py:335):
  returns `"VERY_LOW"` when `projection.product_state ∈ {ambiguous, excluded,
  not_counted}`, otherwise `result.confidence` (layer C). The projection can
  force the cell down but does not raise it.
- **Displayed `Reason` cell** — `_display_reason` (csv_writers.py:328): returns
  `projection.projection_reason` when non-empty, otherwise `result.reason`
  (layer C). The projection reason almost always wins for projected rows.
- **Counted detection / Summary counts / matrix presence** — `projection.
  counted_detection` and `product_state` (consumed at
  `output/detection.py:49`). **Not** `Confidence`, `NL`, or score. This is the
  count/matrix authority; the displayed `Confidence` cell is presentation only.

## One-line mental model

> Scoring (A) proposes a confidence; hypothesis selection (B) may re-project it;
> both are stored on the result (C); the **product projection (D) is the
> authority**; the display layer (E) shows `result.confidence` unless the
> projection demoted the row, and shows `projection_reason` whenever it exists.

## Invariants to preserve

- Layers A and B are **evidence inputs**. Do not let `peak_result.confidence` or
  raw score/cap labels directly decide counts, matrix presence, or product row
  state — route those through `counted_detection` / `product_state` (spec
  §"Product Contract" lines 152-158).
- `_display_confidence` only ever **demotes** to `VERY_LOW`; it must not promote.
  If you need a row to read higher, fix the projection, not the display layer.
- Adding a new evidence source must not add a sixth resolution point. New
  evidence enters at layer A/B as typed context and is reconciled inside the
  projection (layer D), keeping this table at five layers.
- `reproject_extraction_result` (result_assembly.py:93) re-runs layers B-D for an
  already-built result; it must keep the same precedence as
  `build_extraction_result`.
