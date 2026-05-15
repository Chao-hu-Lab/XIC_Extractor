# Alignment Module Responsibility Contract

**Date:** 2026-05-16
**Status:** Draft contract for future refactor PRs
**Inventory:** `docs/superpowers/specs/2026-05-16-module-responsibility-inventory.md`

---

## Summary

This contract defines where future untargeted alignment and diagnostic code
belongs. It exists to stop responsibility drift after the rapid addition of
alignment diagnostics, ISTD benchmarks, backfill economics, RT warping evidence,
and single-dR production gates.

This is a refactor contract only. It does not authorize scientific behavior
changes.

## Responsibility Boundaries

### Alignment Domain

Domain modules own scientific decisions and small typed contracts:

- row identity decisions,
- cell quality decisions,
- owner/backfill semantics,
- single-dR gate classification,
- clustering and family compatibility,
- primary family winner selection.

Domain modules may depend on config values, dataclasses, arrays, and small
helpers. They must not import CLI scripts, workbook builders, HTML renderers,
GitHub adapters, or diagnostics report writers.

### Pipeline Orchestration

`xic_extractor/alignment/pipeline.py` should remain an orchestration facade:

- read discovery inputs,
- choose serial/process execution,
- coordinate owner building, clustering, backfill, matrix building, and writers,
- record timing,
- return `AlignmentRunOutputs`.

It should not permanently own raw timing wrappers, output path construction,
atomic write mechanics, metadata assembly, or report-specific formatting. These
belong in focused helper modules once moved with tests.

### Diagnostics Data Loading

Diagnostic CLIs under `tools/diagnostics/` may load TSV, CSV, JSON, and workbook
inputs. Loading should be isolated from classification and rendering so future
reports can reuse the same parsing contracts.

Diagnostic loaders must fail clearly on missing required columns and must not
silently reinterpret production output schemas.

### Report Models

Report model code owns summary dictionaries or dataclasses that answer one
diagnostic question:

- run verdict,
- ISTD benchmark summary,
- matrix cleanliness,
- backfill economics,
- single-dR gate candidates,
- RT normalization context.

Report models may consume production domain helpers, such as identity gate
classification. They must not duplicate production gate thresholds.

### Rendering And Writers

HTML, Markdown, TSV, and JSON writers own presentation only:

- escaping,
- formatting,
- section layout,
- table rows,
- chart-ready summaries,
- file writes.

Writers must not decide row promotion, demotion, benchmark verdicts, or gate
recommendations.

## Non-Goals

Future responsibility-splitting PRs under this contract must not change:

- `production_family`, `provisional_discovery`, or `audit_family` semantics,
- single-dR production gate thresholds,
- backfill request or confirmation behavior,
- iRT, LOESS, or RT-warping gate behavior,
- targeted ISTD benchmark strict verdict rules,
- TSV, XLSX, JSON, Markdown, or HTML output schemas,
- public CLI flags,
- artifact names for output levels.

Any behavior change must be a separate PR with its own spec, tests, and real-data
validation plan.

## Future PR Order

1. `alignment_decision_report.py`
   - Split loading, report model, and HTML rendering.
   - Preserve generated verdicts and existing HTML sections.

2. `single_dr_production_gate_decision_report.py`
   - Split alignment/discovery/RT/ISTD loaders, family classifier, gate
     candidate model, and writers.
   - Keep classification delegated to `xic_extractor.alignment.identity_gates`
     where production rules exist.

3. `targeted_istd_benchmark.py`
   - Split targeted workbook loader, alignment loader, candidate matcher,
     statistics, and output writers.
   - Preserve strict DNA ISTD benchmark behavior.

4. `xic_extractor/alignment/pipeline.py`
   - Extract output paths, metadata, atomic writer, and timed raw source helpers.
   - Keep `run_alignment(...)` as the stable orchestration entry point.

5. `xic_extractor/alignment/primary_consolidation.py`
   - Add characterization tests first.
   - Then split graph construction, winner selection, observation merge, and
     loser clone helpers only if tests pin behavior.

## Required Tests For Refactor PRs

- Diagnostic split PRs must keep the existing CLI entry points and output files
  unchanged.
- Pipeline split PRs must preserve `AlignmentRunOutputs`, output-level artifact
  names, and lazy RAW reader import behavior.
- Consolidation split PRs must include characterization tests for duplicate graph
  components, winner selection, merged winner cells, and loser audit retention.
- Any refactor that can affect real matrix output must run the 8RAW validation
  subset before merge.

## Review Checklist

Before merging a responsibility-splitting PR, verify:

- It is a move-only PR unless explicitly scoped otherwise.
- Public imports and CLI commands still work.
- Domain modules do not import diagnostics, reports, workbooks, GUI, or scripts.
- Diagnostic modules do not reimplement production gate thresholds.
- Tests live near the moved responsibility rather than expanding only a legacy
  catch-all test file.
- No real-data behavior is claimed unchanged unless validated or structurally
  impossible to change.
