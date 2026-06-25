# P2B Area Mismatch Triage Note

Status: `repo_stub_plus_obsidian`
Validation status: `production_candidate`

This file is a sanitized repo stub. The full triage diary was copied to
Obsidian as `[[2026-05-26 P2b Area Mismatch Triage Note]]`; this stub preserves
the public decision needed by repo referrers.

## Public Summary

- P2B gate interpretation remains `production_candidate`.
- `AREA_MISMATCH` is not a single hard blocker class.
- `d4-N6-2HE-dA` is a non-blocking warning because the strict benchmark paired
  the target against an isotope-shifted family; area comparison is
  incommensurable in that context.
- `d3-N6-medA` is a non-blocking warning / row-level review item. The target has
  severe biological-matrix RT drift, but local RT coherence and same-surface
  evidence keep this from being a P2B hard blocker.
- Area mismatch alone must not block P2B or handoff progression when identity,
  local RT coherence, selected peak, boundary ownership, and matrix delivery are
  accepted.

## Repo Sources Of Truth

- `docs/diagnostic-ledger.md` owns the current target conclusions, rerun policy,
  and retained evidence references for P2B area mismatch.
- `docs/superpowers/plans/2026-06-15-productization-control-plane.md` owns active
  productization tier and lane state.
- `docs/superpowers/validation/productization_status_index_v1.tsv` and
  `docs/superpowers/specs/productization_authority_manifest.v1.json` own
  machine-checkable product authority.

## Optional Private Context

- Obsidian note: `[[2026-05-26 P2b Area Mismatch Triage Note]]`
- Status: `readback_verified`
- Contains: target-level evidence details, sample-level review rows, and
  diagnostic artifact references.

## Next Safe Action

Keep P2B at `production_candidate` while tracking localized ownership/boundary
tails as follow-up review items. Do not promote `AREA_MISMATCH` to a generic
hard blocker without updating `docs/diagnostic-ledger.md` and the relevant
product authority artifacts.
