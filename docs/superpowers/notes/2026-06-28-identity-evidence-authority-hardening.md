# Identity, Evidence, and Authority Hardening

Doc placement: repo_support_doc
Doc kind: note
Doc lifecycle: active
Repo owner: docs/product/evidence-spine.md
Doc exit rule: Retire or move to Obsidian after the listed hardening follow-ups are represented in product docs, specs, or tracked issues.

This note records follow-up implementation risks found while closing the
family-abstraction-removal branch. Stable rules belong in
`docs/product/family-hypothesis-boundary.md` and `docs/product/evidence-spine.md`.

## Current Branch Change

- Product activation now fails closed at the internal helper boundary:
  `_peak_hypothesis_matrix_rows()` defaults to excluding `family_projection`
  rows. Existing public callers already passed an explicit value, so this is a
  hardening change rather than a product-output behavior change.
- The product boundary doc now states that helpers capable of including
  `family_projection` rows must default to exclusion and require explicit
  diagnostic or compatibility opt-in.

## Audit Result

| Area | Current state | Follow-up |
| --- | --- | --- |
| Product activation | Public formal mode excludes `family_projection` by default; helper default now matches fail-closed policy. | Keep `--include-family-projections` diagnostic-only and never treat it as canonical identity readiness. |
| PeakHypothesis matrix construction | Construction can record `family_projection` assignments in audit/inventory rows, but complete identity mode rejects them. | Consider a schema migration from `write_family_projection_cell` to less ambiguous wording only with a planned public-schema change. |
| Cross-sample group labels | Product docs treat `feature_family_id` / `public_family_id` as compatibility display labels and `group_hypothesis_id` as identity where available. | Do not rename public files or columns without a compatibility plan. |
| Owner/backfill ambiguity | Family abstraction removal does not resolve `ambiguous_ms1_owner`, duplicate assignment, or high-backfill-dependency cases. | Use targeted existing-artifact audits before code changes; rerun RAW only when behavior changes need new evidence. |
| Matrix/ProductWriter authority | Existing gates reject family-projection identity in product matrix paths. | Future evidence providers must feed typed evidence/model selection before ProductWriter authority. |
| Fast mode/performance | Exact vendor-XIC behavior and approximate scan-index ideas remain separate. | Keep approximate fast mode behind explicit validation and product framing. |

## Stop Rules

- If a change touches selected area, counted detection, matrix values, active
  ProductWriter scope, or maturity tier, move it out of this cleanup line and
  update the productization control plane.
- If validation needs 8RAW or 85RAW evidence, write the expected-diff contract
  first and run the documented foreground validation path.
