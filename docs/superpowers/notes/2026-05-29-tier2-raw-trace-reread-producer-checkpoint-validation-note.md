# Tier 2 RAW Trace Re-Read Producer Checkpoint Validation Note

## Verdict

`diagnostic_only`

This checkpoint adds the first RAW-backed Tier 2 producer for retained
provisional backfill candidates. It emits paired sidecars:

- `alignment_tier2_trace_evidence.tsv`
- `alignment_tier2_raw_manifest.tsv`

It does not modify `alignment_review.tsv`, `alignment_cells.tsv`,
`alignment_matrix.tsv`, workbook schemas, or primary matrix inclusion behavior.

## Verification

```text
Focused producer/gate pytest: 63 passed in 2.18s
Focused producer ruff: All checks passed!
8RAW producer smoke: run_ok, emitted paired sidecars
8RAW gate consume smoke: diagnostic_only 7 0 False False
```

8RAW output artifacts:

- `output\tier2_raw_trace_reread_8raw_current\alignment_tier2_trace_evidence.tsv`
- `output\tier2_raw_trace_reread_8raw_current\alignment_tier2_raw_manifest.tsv`
- `output\tier2_raw_trace_reread_8raw_current\alignment_tier2_trace_evidence_summary.json`
- `output\tier2_raw_trace_reread_8raw_current_gate\alignment_production_candidate_gate.tsv`
- `output\tier2_raw_trace_reread_8raw_current_gate\alignment_production_candidate_gate.json`

## 8RAW Evidence Summary

```text
producer summary: diagnostic_only 7 7 0 4 0 3 0 False False
producer evidence_status: blocked=4, inconclusive=3
gate summary: diagnostic_only 7 0 False False
gate status: audit=7
```

Observed producer blockers:

- `metric_unavailable;weak_scan_support`: 1 row
- `metric_unavailable;low_scan_support`: 1 row
- `metric_unavailable`: 1 row
- `rescued_boundary_overlap_low`: 1 row
- `rescued_apex_span_wide;rescued_boundary_overlap_low`: 3 rows

## Contract State

- The producer uses `.venv\Scripts\python.exe`, Thermo RAW files, and the
  documented DLL dir.
- The producer writes a RAW manifest before evidence rows, then embeds the RAW
  manifest hash, alignment review hash, alignment cells hash, retained-candidate
  subset hash/count, producer version, criteria version, runtime, command, and
  UTC generation timestamp in every sidecar row.
- The existing candidate gate can consume the paired sidecars and preserve
  `production_ready=false` and `matrix_contract_changed=false`.
- Current 8RAW evidence does not produce positive Tier 2 support. The producer
  surfaced machine-readable `blocked` and `inconclusive` statuses instead of
  promoting candidates.
- Missing or unreadable RAW evidence is modeled as row-level `inconclusive`;
  hard v0 metric/coherence failures are modeled as `blocked`; weak scan support
  remains `not_supported`.

## Remaining Risk

The producer is now executable and provenance-joined, but the v0 coherence
criteria are still experimental. Current 8RAW evidence suggests the next design
question is whether the rescued-cell boundary overlap and apex-span criteria are
the right proxy for independent Tier 2 support. Do not run 85RAW or promote
rows from this checkpoint without a reviewed follow-up plan.
