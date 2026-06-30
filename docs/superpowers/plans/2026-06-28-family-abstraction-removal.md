# Family Abstraction Removal — Compact Implementation Stub

Doc placement: repo_stub_plus_obsidian
Doc kind: plan
Doc lifecycle: implemented
Repo owner: docs/product/discovery.md
Doc exit rule: Keep this same-path compact stub while the branch or PR may still
reference the original plan. Retire it only after the PR closeout covers the
implementation summary, staged Obsidian source copy is promoted or explicitly
accepted, and an exact referrer scan shows no repo dependency on this path.

Status: `implemented_stub`
Validation status: `diagnostic_only`
Obsidian original lookup:
`source_repo_path:docs/superpowers/plans/2026-06-28-family-abstraction-removal.md`
Obsidian source note: `XIC Family Abstraction Removal Source`

This same-path stub replaces the long implementation plan in the public repo.
The original plan body is preserved as a private Obsidian source copy.
Repo authority lives in the product docs below, not in the historical plan body.

## Stable Result

- The old "family" wording conflated per-sample Discovery peak anchors,
  chromatographic proximity grouping, and cross-sample group identity.
- Discovery `feature_family_id` remains a public output header and compatibility
  field, but its product meaning is now a per-sample peak-anchor label.
- Cross-sample identity and matrix authority remain outside Discovery. They are
  owned by group hypotheses, PeakHypothesis evidence, and ProductWriter or
  Backfill activation contracts.
- Legacy score, confidence, family role, and review tokens may rank or annotate;
  they must not become standalone product truth.

## Repo Authority

- `docs/product/discovery.md` owns the Discovery lane and public output
  boundary.
- `docs/product/family-hypothesis-boundary.md` owns the peak-anchor,
  cross-sample group, PeakHypothesis, and projection boundary.
- `docs/architecture-contract.md` owns dependency direction and move-before-
  behavior-change discipline.

## Remaining Lifecycle Work

- Keep the live Obsidian source-copy pointer accurate.
- Condense the final implementation and verification result into the PR body or
  branch closeout.
- Run an exact referrer scan before proposing removal of this same-path stub.
- Do not treat this stub as approval for `git rm`, archive moves, output schema
  changes, or product-matrix authority changes.
