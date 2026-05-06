# XIC Extractor Agent Contract

This file defines repo-local engineering contracts for XIC Extractor. Global
agent rules still apply; this file only records project-specific architecture
and maintenance expectations.

## Architecture Boundaries

XIC Extractor should prefer thin orchestration modules that coordinate focused
submodules. Do not keep adding independent responsibilities to a single large
file just because the current entry point already has nearby code.

Preferred pattern:

- A public entry module preserves import and CLI compatibility.
- Focused submodules own domain behavior, IO, rendering, scoring, or backend
  mechanics.
- The entry module wires those pieces together and contains minimal domain
  logic.

Examples:

- `xic_extractor/extractor.py` should be the public extraction entry point, not
  the permanent home for process backends, ISTD pre-pass, RT windowing, anchor
  selection, target extraction, diagnostics, and output dispatch.
- `scripts/csv_to_excel.py` should remain a CLI/import compatibility wrapper,
  not the permanent home for every workbook sheet, style, metric, parser, and
  review-rule helper.
- `xic_extractor/signal_processing.py` should not permanently contain every
  resolver, candidate model, selection rule, trace-quality metric, and area
  integration helper.

## Module Responsibility Rules

Before adding non-trivial behavior to a module, check whether the change belongs
to an existing focused owner or deserves a new focused module.

Use these ownership boundaries by default:

- Pipeline orchestration: high-level flow, backend selection, cancellation, and
  progress coordination.
- Backend execution: serial/process execution mechanics and pickleable job
  payloads.
- Target extraction: one raw file plus one target, including XIC extraction and
  result assembly.
- Anchor/RT windowing: NL anchor, ISTD anchor, fallback windows, and drift
  helpers.
- Peak detection: resolver-specific candidate formation.
- Peak selection: choosing among already-built candidates.
- Trace quality: MS1/ADAP-like quality metrics.
- Scoring: severity signals, confidence, reason construction, and scoring-based
  selection helpers.
- Output metrics: shared review/detection/flag calculations.
- Workbook sheets: one sheet module per worksheet.
- Workbook styles: formatting helpers only.
- HTML report: static visual report rendering only.

## Size And Refactor Triggers

Line count is not a hard quality metric, but it is a useful maintenance signal.

When a production module approaches roughly 500 lines, new behavior should come
with an explicit reason for staying in that file. When a module approaches
roughly 800 lines, avoid adding new responsibilities unless the task is an
immediate bug fix. Prefer extracting a focused submodule first or opening a
follow-up maintainability issue/spec.

For scripts and validation tools, a larger file can be acceptable, but only when
it owns one coherent workflow. If a script mixes parsing, execution, scoring,
and workbook rendering, split it before adding more features.

## Public Contract Preservation

Refactors must preserve public surfaces unless a plan explicitly says otherwise.

Public surfaces include:

- CLI commands under `scripts/`
- `xic_extractor.extractor.run`
- `scripts.csv_to_excel.run`
- config keys and default/example settings
- workbook sheet names, sheet order, hidden states, and output columns
- CSV schemas
- HTML report path naming
- run metadata keys

When moving code, add or keep compatibility wrappers at the old import location.

## Refactor Discipline

For maintainability refactors:

- Move behavior before changing behavior.
- Keep commits small enough to review by responsibility.
- Add characterization tests before moving code when behavior is not already
  covered.
- Run narrow tests for the moved module, then broader CI-equivalent checks.
- Use the 8-raw validation subset for extraction/output refactors when behavior
  could affect real workbook output.
- Do not mix scoring threshold changes, selection-rule changes, or area
  integration changes into structural refactor commits.

