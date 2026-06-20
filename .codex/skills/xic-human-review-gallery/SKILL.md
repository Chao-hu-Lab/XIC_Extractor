---
name: xic-human-review-gallery
description: Use when creating, reviewing, or fixing XIC human-review Gallery, overlay, guide HTML, browser smoke, visual evidence, or review UX artifacts for Backfill, Discovery, product-gate, or evidence interpretation work.
---

# XIC Human Review Gallery

Use for human-review visual artifacts. The job is to make evidence reviewable
without creating a second Gallery system or confusing diagnostic visuals with
ProductWriter authority.

## Use Pattern

1. Find the existing Gallery/Overlay owner before creating a new HTML path.
2. Name the review lens: Backfill context, Discovery identity, Authority
   boundary, or tutorial/guide.
3. Keep evidence roles separate: MS1 context, CID/MS2 tag evidence, candidates,
   row identity, and matrix authority are not interchangeable.
4. Prefer overlay PNG/real assets and in-app Browser smoke over manual
   screenshots or Chrome-only assumptions.
5. Track guide/index/summary files only; keep large PNG bundles, full TSVs,
   trace JSON, and generated galleries ignored unless a contract says otherwise.

## Output Contract

State:

- existing owner/helper reused or why none fits;
- review lens and what the human should decide;
- generated guide/gallery paths and heavy artifact retention policy;
- browser smoke evidence across desktop/mobile when layout matters;
- explicit authority boundary: diagnostic, review evidence, or product gate.

## References

- Gallery ownership, lens separation, and browser smoke:
  `references/gallery-review-contract.md`
- Trigger and near-neighbor cases:
  `evals/trigger-cases.md`
- Portable skill interface metadata:
  `agents/interface.yaml`
