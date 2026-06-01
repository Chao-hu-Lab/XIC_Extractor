# C1a Baseline Module Consolidation Closeout Note

Status: `LANDED_VALIDATED` for the C1a prerequisite to linear-edge retirement.

Branch: `codex/cleanup-retirement-foundation`

Commit: `f4b3a77 refactor: relocate AsLS baseline implementation`

Verdict:

- The canonical AsLS baseline implementation now lives in
  `xic_extractor/peak_detection/baseline.py`.
- `xic_extractor/baseline.py` is an import-compatible facade that re-exports
  `asls_baseline` for older callers.
- Maintained production/package imports use the canonical
  `xic_extractor.peak_detection.baseline` location.

Changed contract:

- C1a is a location and dependency-direction cleanup only.
- It does not delete `linear_edge`.
- It does not change the selected production baseline method.

Verification already run in the C1a phase:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_baseline.py tests/test_baseline_integration.py tests/test_scoring_context.py tests/test_p2_baseline_truth_audit.py -q
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor/peak_detection/baseline.py xic_extractor/baseline.py xic_extractor/peak_scoring.py tools/diagnostics/p2_baseline_truth_audit.py tests/test_baseline.py tests/test_baseline_integration.py tests/test_scoring_context.py tests/test_p2_baseline_truth_audit.py
rg -n "from xic_extractor\.baseline import asls_baseline|import xic_extractor\.baseline" xic_extractor tools
```

Observed results:

- `53 passed, 2 warnings` for focused tests.
- Focused ruff passed.
- The import scan returned no maintained `xic_extractor/` or `tools/`
  canonical-call-site matches.

Phase 6b usage:

- This note is the `c1a_validation_note` for the retirement prerequisite
  manifest.
