# XIC Extractor Agent Contract

Repo-local rules for code design and maintenance. Global Codex rules still
apply. This file should stay short enough to influence implementation choices.

## Design Principles

- Make logic, dependencies, and data flow obvious.
- Prefer explicit interfaces over hidden coupling or global context.
- Keep one reason-to-change per module. Split by responsibility, not by fashion.
- Keep high-level domain behavior independent from IO, GUI, workbook rendering,
  process backends, and CLI wrappers.
- Use orchestration modules to coordinate focused submodules; do not let the
  orchestrator become the permanent home for every implementation detail.
- Add abstraction only when it reduces real coupling, duplication, or cognitive
  load. Avoid both monoliths and many tiny indistinguishable modules.
- Preserve public contracts unless an approved plan says otherwise.

## Ownership Map

Use these ownership boundaries by default:

- Public entry/facade: import and CLI compatibility only.
- Pipeline orchestration: workflow order, backend choice, progress, cancellation.
- Backend execution: serial/process mechanics and pickleable job payloads.
- Target extraction: one raw file plus one target, XIC trace, result assembly.
- Anchor/RT windowing: NL anchor, ISTD anchor, fallback windows, drift.
- Peak detection: resolver-specific candidate formation.
- Peak selection/recovery: choosing among existing candidates.
- Trace quality: MS1/ADAP-like quality metrics.
- Scoring: severity signals, confidence, reason, scoring-based selection.
- Output metrics: shared review/detection/flag calculations.
- Workbook sheets: worksheet rendering only.
- Workbook styles: formatting helpers only.
- HTML report: static visual report rendering only.
- Adapters: RAW reading, CSV IO, workbook IO, GUI, GitHub, and CLI edge code.

If new code crosses two ownership groups, either make the module an explicit
orchestration facade or split the behavior.

## Dependency Rules

- Domain algorithms may depend on arrays, config values, typed context objects,
  and small models.
- Domain algorithms must not import GUI, workbook builders, CLI scripts, process
  backends, or report renderers.
- IO/rendering/adapters depend inward on domain helpers, not the reverse.
- Shared dataclasses and protocols belong in small model/contract modules when
  needed to avoid circular imports.
- Windows process mode must receive pickleable payloads only. Do not pass nested
  closures or non-pickleable factories across process boundaries.

## Red Flags

Pause before adding code when any of these are true:

- The target module is near 500 lines and the change adds a new responsibility.
- The target module is near 800 lines and the change is not a local bug fix.
- The function mixes setup, parsing, algorithm, diagnostics, rendering, and IO.
- A boolean flag switches between unrelated workflows. Boolean config values are
  fine; hidden multi-workflow functions are not.
- A low-level module needs to import a high-level entry point or adapter.
- A helper requires Thermo RAW files, Excel workbooks, or GUI widgets even though
  its logic should be testable with small fixtures.
- A change to Excel formatting, process execution, scoring, or peak detection
  would force unrelated code in the same module to change.

Line count is a signal, not a hard rule. Responsibility count matters more.

## Refactor Discipline

- Move behavior before changing behavior.
- Keep compatibility wrappers at old public import locations.
- Add characterization tests before moving behavior that is not already covered.
- Do not mix structural refactors with scoring thresholds, peak selection rules,
  neutral-loss matching, or area integration changes.
- Run narrow tests for moved modules, then broader CI-equivalent checks.
- Use the 8-raw validation subset for extraction/output refactors that can
  affect real workbook output.

## Test Structure Rules

- Keep tests in `tests/`; do not place test code inside `xic_extractor/` or
  production scripts.
- Mirror the ownership map. When production behavior moves to a focused module,
  put its tests in a matching focused `test_*.py` file instead of expanding a
  broad legacy test file.
- Test behavior and public contracts first. Reach into private helpers only for
  characterization tests, algorithm edge cases, or compatibility seams that are
  hard to observe through the public entry point.
- Each test should prove one behavior with explicit inputs and assertions.
  Prefer descriptive test names over comments explaining the scenario.
- Keep unit tests deterministic, small, and independent. Use synthetic traces,
  `tmp_path`, `monkeypatch`, and small fakes before real RAW files, GUI widgets,
  or full workbooks.
- Put shared fixtures in `tests/conftest.py` only when several test files need
  them. Keep file-local fixture factories near the tests that own them.
- Parameterize equivalent edge cases instead of copy-pasting near-identical
  tests, but split cases when failures would become hard to diagnose.
- Separate real-data validation from normal unit/contract tests. Real RAW
  checks should be explicit, fixture-gated, or run through validation scripts,
  not silently required by the default suite.
- For output changes, pair narrow writer/sheet tests with at least one workbook
  contract or compare test. Do not rely on visual inspection alone.
- For process-mode changes, include a no-RAW spawn/pickling smoke test before
  any raw-data benchmark.

## Public Contracts

Treat these as public unless a plan explicitly changes them:

- CLI commands under `scripts/`
- `xic_extractor.extractor.run`
- `xic_extractor.signal_processing.find_peak_and_area`
- `scripts.csv_to_excel.run`
- config keys and example/default settings
- CSV schemas
- workbook sheet names, order, hidden states, and columns
- HTML report path naming
- run metadata keys

## Current Decomposition Targets

These modules are known maintainability targets:

- `scripts/csv_to_excel.py`: keep as CLI/import wrapper; move workbook logic to
  `xic_extractor/output/` modules.
- `xic_extractor/extractor.py`: keep as public extraction facade; move pipeline,
  backend, pre-pass, target extraction, anchor, drift, and output dispatch logic
  into `xic_extractor/extraction/`.
- `xic_extractor/signal_processing.py`: keep as compatibility facade; move
  models, resolver implementations, selection, recovery, integration, and trace
  quality into focused peak-detection modules.

See:

- `docs/superpowers/specs/2026-05-06-workbook-and-extraction-module-decomposition-spec.md`

## Source References

- Python project structure: `https://docs.python-guide.org/writing/structure/`
- pytest good integration practices:
  `https://docs.pytest.org/en/stable/explanation/goodpractices.html`
- pytest fixtures:
  `https://docs.pytest.org/en/stable/how-to/fixtures.html`
- Python testing guidance: `https://docs.python-guide.org/writing/tests/`
- Zen of Python: `https://peps.python.org/pep-0020/`
- Clean Code for Python: `https://github.com/zedr/clean-code-python`
- Google Python Style Guide: `https://google.github.io/styleguide/pyguide.html`
- Cosmic Python dependency inversion/service layer:
  `https://www.cosmicpython.com/book/introduction.html`
