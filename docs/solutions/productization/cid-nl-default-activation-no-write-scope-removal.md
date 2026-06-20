---
title: "CID-NL Default Activation No-Write Scope Removal"
date: "2026-06-20"
category: "productization"
module: "cid-nl-default-activation"
status: "current"
tags: ["cid-nl", "default-activation", "scope-removal", "authority"]
source_refs:
  - "docs/superpowers/plans/2026-06-15-productization-control-plane.md"
  - "docs/superpowers/validation/cid_nl_default_activation_remaining_identity_gate_v1/README.md"
---

# CID-NL Default Activation No-Write Scope Removal

## When To Read

Read this when a default-activation gate has terminal authority cells that
cannot be bridged to one safe new row, but the product decision needs to move
forward without granting new writer authority.

## Problem

The CID-NL activation path had 27 remaining authority cells after the bridge,
reconstruction, and cell-local gates. Treating those cells as unresolved forever
would block progress, but forcing them onto candidate rows would make CID-NL or
MS2 evidence direct ProductWriter authority.

## Tempting Wrong Path

Do not pick an arbitrary candidate for all-blank ambiguity, do not choose one
detected row when multiple ambiguous candidates are detected, and do not treat a
source-feature-family identity hit as a replay bridge when m/z/RT does not make
that target safe.

## Working Pattern

Use a final no-write gate that consumes the previous identity gate and only
converts known terminal blocker classes into explicit scope removals:

- `blocked_identity_missing` ->
  `scope_removed_missing_identity_no_write`
- `blocked_ambiguous_all_blank` ->
  `scope_removed_ambiguous_blank_no_write`
- `blocked_ambiguous_multiple_detected_candidates` ->
  `scope_removed_ambiguous_multiple_detected_no_write`

Everything else remains fail-closed. The activation candidate contract can then
be expressed as write the safe blanks, preserve detected no-write cells, and
omit explicit scope removals.

## Evidence

- Commands actually run:
  `python -m pytest tests/test_cid_nl_default_activation_remaining_identity_gate.py -q`;
  `python -m pytest tests/test_cid_nl_default_activation_bridge_gate.py tests/test_cid_nl_default_activation_authority_reconstruction_gate.py tests/test_cid_nl_default_activation_cell_local_identity_gate.py tests/test_cid_nl_default_activation_remaining_identity_gate.py -q`;
  `uv run ruff check scripts/check_cid_nl_default_activation_remaining_identity_gate.py tests/test_cid_nl_default_activation_remaining_identity_gate.py`;
  `python scripts/check_cid_nl_default_activation_remaining_identity_gate.py --require-pass`.
- Artifact paths:
  versioned report under
  `docs/superpowers/validation/cid_nl_default_activation_remaining_identity_gate_v1/`;
  full generated audit under ignored
  `output/validation/cid_nl_default_activation_remaining_identity_gate_v1/`.
- Reviewer: subagent review found no findings and independently confirmed 511
  classified cells, 147 writes, 337 detected/no-write cells, 27 scope removals,
  and 0 unresolved cells.

## Limits

This does not write the default matrix and does not promote CID-NL/MS2 evidence
or candidates into ProductWriter authority. It only closes the identity blocker
for the next expected-diff/default-activation candidate gate.

## Next Time

1. Reuse the previous identity gate output instead of inventing another source
   of truth.
2. Keep terminal blocker conversion to an allow-list and fail closed for stale
   coordinates or unknown blocked states.
3. Make the next candidate gate prove writes, detected no-write preservation,
   and scope removals separately.
4. Keep full audit TSVs and matrix sidecars under ignored `output/validation`,
   not under version-controlled `docs/superpowers/validation`.
