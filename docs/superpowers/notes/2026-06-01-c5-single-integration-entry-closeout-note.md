# C5 Single Integration Entry Closeout Note

**Date:** 2026-06-01
**Branch:** `codex/cleanup-retirement-foundation`
**Status:** `production_candidate` for the C5 prerequisite to C1b; no behavior
change in this phase.

## Verdict

The maintained production/package callers no longer call
`integrate_linear_edge_baseline` directly. They route through
`integrate_with_baseline` / the current method-preserving integration surfaces.
This closes the C5 blocker for continuing toward linear-edge retirement, while
leaving C1b responsible for deleting the selector and legacy implementation
after the final retirement gate passes.

## Scan

Command:

```powershell
rg -n "integrate_linear_edge_baseline" xic_extractor tools scripts tests
```

Direct references found:

| Path | Classification | Reason |
|---|---|---|
| `xic_extractor/peak_detection/baseline.py` | implementation / selector | Defines the legacy implementation and the method-preserving selector branch. C1b owns deletion. |
| `tools/diagnostics/asls_truth_validation_synthetic.py` | comparator diagnostic | Synthetic truth-validation comparator still needs linear-edge until the final retirement gate passes. C1b must migrate, externalize, or delete it before removing the function. |
| `tests/test_baseline_integration.py` | regression / migration guard | Tests legacy linear-edge math, selector dispatch, and the package-wide no-direct-production-caller contract. |

No `scripts/` direct caller was found.

## Verification

Already-covered guard:

- `tests/test_baseline_integration.py::test_production_code_uses_selector_for_linear_edge_baseline`
  scans `xic_extractor/` and fails if any package file except
  `peak_detection/baseline.py` mentions `integrate_linear_edge_baseline`.

Focused checks for this phase:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_baseline_integration.py -q
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tests/test_baseline_integration.py xic_extractor/peak_detection
```

## Next Dependency

C1b may start only after the later retirement gates produce
`GO_FOR_LINEAR_EDGE_RETIREMENT`. At that point, the remaining direct references
above must be removed or replaced as part of the deletion commit.
