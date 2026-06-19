# XIC Productization Pulse - 2026-06-19 21:40

Historical pulse: this snapshot predates the later Discovery parser and
resolved-claim matrix-decision fix. Use the current handoff for latest state.

## Verdict

- Branch `cc/framework-improvements` is clean and ahead of origin by 78 commits.
- Current product tier remains `product_ready_default_matrix_activated`.
- Default matrix authority is still exactly 511 accepted Backfill cells plus detected values; broad 4613-row Backfill remains parked.
- The latest cleanup commit `1c0536eb` refactors retention and QuantMatrix replay helpers only. It does not change ProductWriter, default extraction, workbook/GUI, selected peak/area, counted detection, or Backfill authority.
- Current validation status for the cleanup/refactor is `diagnostic_only`.

## Lane Snapshot

| Lane | Tier | Evidence Added | Blocker / Next Evidence |
| --- | --- | --- | --- |
| Default QuantMatrix output | `product_ready_default_matrix_activated` | Phase 11 activated default output with 17489 detected cells, 511 accepted Backfill cells, 18000 quant-available cells, zero unused expected-diff rows | Regenerate discovery/alignment/default activation if the `300.1605 -> 184.113` target row must appear in the activated matrix |
| Broad Backfill | parked | Authority/control-plane docs still hold broad Backfill out of writer scope | Needs independent truth source plus expected-diff authority update before reopening |
| Validation artifact retention | `diagnostic_only` cleanup | 169 retained validation files, 135 externalized artifacts, 0 `shrink_later`; shared retention helper committed | Keep generated dumps out of tracked validation unless contract/index/hash/summary/minimal fixture |
| Fixture retention | `diagnostic_only` cleanup | 28 retained fixture files; fixture checker reuses shared retention helper | Resolve `chrom_peak_segment_presence_review_manual_oracle_v1.tsv` as active oracle or archived note-only oracle |
| QuantMatrix replay helpers | `diagnostic_only` cleanup | Shared bundle/path/hash/replay helper now materializes externalized `cell_provenance.tsv` without durable temp paths | Deepen only if another caller needs the same replay orchestration |
| Targeted MS1 limited rescue | `production_ready` narrow lane | Control plane still limits ready claim to `limited_5hmdc_5medc_v1` / `5-hmdC + 5-medC` / `detected_flagged` | GUI and broader targets remain blocked |

## What Changed

- Latest commit: `1c0536eb Refactor artifact retention and QuantMatrix replay helpers`.
- Previous cleanup commits in the same window removed generated validation/fixture dumps from tracked contract surfaces and planned/implemented retention cleanup.
- Handoff was refreshed at `2026-06-19 21:16 +08:00` and remains the compact current-state snapshot.

## Evidence Freshness

- Inspected `git status --short --branch`: clean before this pulse report was written, `ahead 78`.
- Inspected `git log --since="7 days ago"`: latest HEAD is `1c0536eb`.
- Inspected current handoff: `docs/superpowers/handoffs/current/cc-framework-improvements-productization.md`.
- Inspected control-plane anchors around Phase 11, broad Backfill, Targeted MS1, ReviewAction, and GUI boundaries.
- Latest recorded verification includes ruff, mypy, focused pytest shards, retention checkers, QuantMatrix check-only chain, productization state checker, hook smoke, diff check, and secret/local-path scan.

## Risks Of Overclaim

- Do not claim the activated `quant_matrix.tsv` contains the `d4-N6-2HE-dA` `300.1605 -> 184.113` row until a later regeneration reruns discovery/alignment/default activation.
- Do not treat externalized full TSVs as tracked product contracts; tracked summaries/minimal fixtures plus replay hashes are the contract.
- Do not treat lockbox/review-packet/manual-review surfaces as ProductWriter authority.
- Do not infer GUI readiness or broader Targeted MS1 readiness from the current headless limited rescue lane.
- Full pytest is not green: it stops at an unrelated stale candidate-id fixture in `tests/test_alignment_identity_coherence_pipeline.py::test_run_alignment_emits_identity_coherence_diagnostic_when_opted_in`.

## Next Best Actions

1. Resolve `chrom_peak_segment_presence_review_manual_oracle_v1.tsv` as active fixture or archive.
2. Decide whether to open a separate regeneration goal for the `300.1605 -> 184.113` target row.
3. Fix or regenerate the stale candidate-id test fixture blocking full pytest.
