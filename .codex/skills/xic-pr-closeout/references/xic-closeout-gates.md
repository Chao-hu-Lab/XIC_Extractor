# XIC Closeout Gates

Use this after loading global `pr-closeout`.

## CI-Equivalent Gate

Before opening, updating, or marking a PR ready, run the repo CI-equivalent
commands unless the user or PR state makes a narrower closeout explicit:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -v --tb=short -x
```

Treat real lint, typecheck, or test failures as blockers. Fix them and rerun the
failed gate before PR. If dependency resolution, executable spawn, or DLL loading
is blocked by the environment, report the blocker instead of substituting a
narrower check.

## XIC Closeout Fields

Include when relevant:

- readiness label: `diagnostic_only`, `shadow_ready`, `production_candidate`,
  `production_ready`, or `inconclusive`;
- validation tier: synthetic, focused tests, 8RAW, 85RAW, targeted benchmark,
  manual EIC/MS2 review, or CI shard;
- downstream handoff impact, especially whether `alignment_matrix.tsv` is
  preserved or changed;
- whether `peak_candidates.tsv` is debug/audit projection or production
  contract;
- important artifacts or output indexes under `output/` or `docs/superpowers/`;
- skipped RAW validation and what future evidence would close the risk;
- merge mode and whether branch history, worktree contents, or local `output/`
  artifacts must be preserved.

## XIC Overclaim Guard

Do not claim production behavior from wrappers, reports, sidecars, or TSV
diagnostics alone. State what was observed and what remains unproven.

Do not let a PR description imply handoff productization progress unless the PR
actually advances `TraceGroup`, `PeakHypothesis`, `EvidenceVector`,
`IntegrationResult`, `AuditTrail`, or downstream matrix handoff.
