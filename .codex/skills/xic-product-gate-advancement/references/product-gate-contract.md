# Product Gate Contract

## Evidence Tiers

Name the strongest evidence actually inspected:

- synthetic no-RAW tests;
- focused unit/contract tests;
- no-RAW artifact parity;
- 8RAW validation;
- 85RAW validation;
- targeted benchmark;
- manual EIC/MS2 review;
- human product review;
- CI shard / GitHub checks.

Tests passing is not production readiness. Diagnostic visibility is not
activation authority.

## Expected Diff

For public-surface or authority changes, define expected diff before claiming a
gate:

- selected peak, area, or confidence;
- matrix identity or row/sample state;
- workbook/TSV/schema/output path;
- ProductWriter authority;
- activation bundle or default lane;
- downstream handoff fields.

If expected diff is unknown, the gate is not ready.

## Control Plane Boundary

Update the productization control plane only when maturity tier, active lane,
authority, product gate, or public contract state changes. If nothing changed,
say explicitly that no control-plane tier update is needed.

Active handoff updates are for continuation state, not product authority. Rewrite
handoff only when the current-state snapshot is stale for the ongoing work.
