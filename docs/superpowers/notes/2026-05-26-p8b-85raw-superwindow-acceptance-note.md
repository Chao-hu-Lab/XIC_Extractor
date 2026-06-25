# P8b 85RAW Super-Window Acceptance Note

Status: `repo_stub_plus_obsidian`
Validation status: `production_candidate`

This file is a sanitized repo stub. The full validation diary was copied to
Obsidian as `[[2026-05-26 P8b 85raw Superwindow Acceptance Note]]`; this stub
preserves the public decision needed by repo referrers.

## Public Summary

- Explicit opt-in `validation-minimal + production-equivalent +
  validation-fast + super-window` 85RAW alignment validation is
  `production_candidate`.
- The 85RAW super-window run completed and emitted the expected machine
  artifacts.
- Matrix, cells, and review surfaces were byte-identical to the accepted P8b
  exact-window reference for the checked contract.
- No new RT, identity, or coverage failure was introduced by super-window.
- The CLI default remains exact-window batching; super-window remains explicit
  opt-in until a separate promotion decision.

## Repo Sources Of Truth

- `docs/diagnostic-ledger.md` owns the current acceptance verdict and rerun
  policy for this gate.
- `docs/agent-parameter-settings.md` owns canonical 85RAW command-shape and
  foreground heartbeat rules.
- `docs/superpowers/plans/2026-06-15-productization-control-plane.md`,
  `docs/superpowers/validation/productization_status_index_v1.tsv`, and
  `docs/superpowers/specs/productization_authority_manifest.v1.json` own product
  tier, lane, and writer authority state.

## Optional Private Context

- Obsidian note: `[[2026-05-26 P8b 85raw Superwindow Acceptance Note]]`
- Status: `readback_verified`
- Contains: command transcript, artifact list, benchmark details, performance
  numbers, and warning interpretation.

## Next Safe Action

Do not rerun 85RAW just to re-prove super-window acceptance. Rerun only after
current code changes RAW locality, owner-backfill request grouping,
super-window batching/cropping, validation-fast settings, output surfaces used
by the contract, or accepted warning-class interpretation.
