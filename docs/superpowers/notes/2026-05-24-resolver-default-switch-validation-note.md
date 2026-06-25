# Resolver Default Switch Real-Data Validation Note

Status: `repo_stub_plus_obsidian`
Validation status: `production_candidate`

This file is a sanitized repo stub. The full validation diary was copied to
Obsidian as `[[2026-05-24 Resolver Default Switch Validation Note]]`; this stub
preserves the public decision needed by repo referrers.

## Public Summary

- The P1 resolver default switch is GO for P2 entry at
  `production_candidate` strength after the 2026-05-25 hotfix evidence-chain
  continuation.
- This is an 8RAW method/P2-entry decision only. It is not 85RAW-cleared and not
  `production_ready`.
- Do not use the stale pre-hotfix `NO-GO` artifact state to block or approve
  current P2 work.
- The hotfix restored untargeted alignment production peak picking to
  `local_minimum` while keeping `region_first_safe_merge` as audit context.
- The strict ISTD blocker on `15N5-8-oxodG` was resolved in hotfix artifacts.
- The same-surface `d3-N6-medA` probe reclassified the
  apparent mismatch as a mixed-surface diagnostic artifact, not a standalone
  evidence-spine blocker.

## Repo Sources Of Truth

- `docs/diagnostic-ledger.md` owns the current rerun policy and stable P2-entry
  summary for this gate.
- `docs/superpowers/plans/2026-06-15-productization-control-plane.md` owns active
  productization tier and lane state.
- `docs/superpowers/validation/productization_status_index_v1.tsv` and
  `docs/superpowers/specs/productization_authority_manifest.v1.json` own
  machine-checkable product authority.

## Optional Private Context

- Obsidian note: `[[2026-05-24 Resolver Default Switch Validation Note]]`
- Status: `readback_verified`
- Contains: run diary, artifact list, and detailed hotfix evidence tables.

## Next Safe Action

Do not rerun this gate just to re-prove P2 entry. Rerun only after code changes
resolver default routing, candidate selection, selected boundaries, strict ISTD
benchmark behavior, identity-coherence decisions, or the cited artifacts become
stale or contradictory.
