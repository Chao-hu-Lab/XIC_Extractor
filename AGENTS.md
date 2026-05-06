# XIC Extractor Agent Contract

This file defines repo-local engineering contracts for XIC Extractor. Global
agent rules still apply; this file only records project-specific architecture
and maintenance expectations.

## Design References

These rules are adapted to this repo from a few mature Python and clean-code
guides:

- The Hitchhiker's Guide to Python emphasizes that project structure should make
  logic, dependencies, data flow, and grouping clear.
- Clean Code guidance emphasizes one responsibility per function/module, one
  level of abstraction per function, and descriptive names over explanatory
  comments.
- `clean-code-python` frames SOLID/Clean Code ideas as guidelines, not laws.
- Cosmic Python's service-layer pattern separates workflow orchestration from
  domain behavior and keeps entry points thin.

Use these as pragmatic guardrails. Do not introduce extra layers when a small,
cohesive module is easier to understand and test.

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
- Dependency direction should point from orchestration/adapters toward focused
  domain helpers, not from domain helpers back into CLI, GUI, workbook, or
  process-runner code.
- Workflow orchestration belongs in one module layer; algorithm details and IO
  rendering belong in separate modules.

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

Ask these questions before editing a large module:

- What single actor or reason-to-change owns this behavior?
- Is this workflow orchestration, domain logic, IO, rendering, or test/validation
  support?
- Does the new code operate at the same abstraction level as nearby code?
- Would a future change to Excel formatting, process execution, peak detection,
  or scoring force an unrelated part of this module to change?
- Can this behavior be tested without Thermo RAW files, Excel workbooks, or GUI
  widgets?

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

Avoid modules that mix more than one of these ownership groups unless they are
explicit orchestration facades.

## Orchestration Module Rules

An orchestration module may know the sequence of a workflow, but it should not
own the implementation details of every step.

Good orchestration modules:

- expose the public entry point,
- validate and normalize high-level inputs,
- call focused submodules in a readable order,
- pass explicit data structures between steps,
- preserve cancellation/progress contracts when they are part of the workflow,
- stay easy to characterize with high-level tests.

Bad orchestration modules:

- contain low-level algorithm internals,
- render workbook/HTML details inline,
- build process-pool payloads and also score peaks,
- mutate global state for convenience,
- rely on long flag-argument branches that effectively implement multiple
  workflows inside one function.

If a function has distinct sections such as setup, parsing, algorithm,
rendering, diagnostics, and writing, split those sections into named helpers or
submodules unless the function is already a short facade.

## Dependency And Data Flow Rules

Prefer explicit data flow over hidden coupling.

- Pass typed dataclasses or simple dictionaries at module boundaries when the
  project already uses them.
- Keep IO adapters at the edges: RAW reading, CSV reading/writing, workbook
  rendering, HTML rendering, GUI widgets, and GitHub/CLI wrappers should not be
  imported by core scoring or peak-detection logic.
- Core algorithms should accept arrays, config values, and small context objects,
  not full GUI/config/workbook objects.
- Avoid circular imports by moving shared models to a small `models.py` or
  contract module.
- When a process backend is involved, module boundaries must preserve Windows
  spawn picklability. Do not pass nested closures or non-pickleable factories
  across process boundaries.

## Size And Refactor Triggers

Line count is not a hard quality metric, but it is a useful maintenance signal.

When a production module approaches roughly 500 lines, new behavior should come
with an explicit reason for staying in that file. When a module approaches
roughly 800 lines, avoid adding a new ownership group unless the task is an
immediate bug fix. Small local fixes may still happen in large modules, but they
should not make the module responsible for another workflow. Prefer extracting a
focused submodule first or opening a follow-up maintainability issue/spec.

For scripts and validation tools, a larger file can be acceptable, but only when
it owns one coherent workflow. If a script mixes parsing, execution, scoring,
and workbook rendering, split it before adding more features.

Counting responsibilities is more important than counting lines. A 350-line
module that owns one algorithm can be acceptable. A 250-line module that mixes
GUI, IO, scoring, and formatting is already a design smell.

## Function-Level Rules

Functions should read at one level of abstraction.

- A high-level workflow function should call named steps, not inline every
  implementation detail.
- A low-level helper should do one mechanical thing and be easy to unit test.
- Avoid boolean flag arguments that switch between unrelated behaviors. This is
  not a ban on boolean config values such as `emit_review_report` or
  `strict_preferred_rt`; it is a warning against one function owning multiple
  unrelated workflows behind a flag. Prefer separate functions or strategy
  objects when the branches represent different workflows.
- Keep names domain-specific and consistent: use the same vocabulary for target,
  candidate, anchor, trace quality, NL evidence, review row, and workbook sheet
  concepts across modules.

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
- After a structural refactor, check that module dependencies still match the
  intended ownership boundaries. If a low-level module imports a high-level
  entry point, workbook builder, GUI section, or process backend, treat it as a
  design regression.

## Source Links

- Python project structure: `https://docs.python-guide.org/writing/structure/`
- Clean Code for Python: `https://github.com/zedr/clean-code-python`
- Clean Code summary: `https://github.com/thomasruegg/clean-code-summary`
- Cosmic Python service layer: `https://www.cosmicpython.com/book/chapter_04_service_layer.html`
- Clean Architecture Python example: `https://github.com/cdddg/py-clean-arch`
