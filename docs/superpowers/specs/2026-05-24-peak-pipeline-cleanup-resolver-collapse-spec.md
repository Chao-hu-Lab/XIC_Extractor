# C2 — Resolver Public-Surface Contract Cleanup Spec

**Date:** 2026-05-24
**Status:** Current executable scope v0.6 — `arbitrated` retired; Phase 1
resolver public-surface contract synchronized without accepted-mode behavior
changes
**Overview:** [Peak pipeline cleanup roadmap overview](2026-05-24-peak-pipeline-cleanup-roadmap-overview-spec.md)
**Current reassessment:** [Peak pipeline cleanup current-state reassessment](2026-06-01-peak-pipeline-cleanup-current-state-reassessment-spec.md)
**One-goal execution contract:** [Peak pipeline cleanup one-goal phase contract](2026-06-01-peak-pipeline-cleanup-one-goal-phase-contract-spec.md)
**Precondition:** current-state reassessment accepted. `linear_edge` and
`arbitrated` retirements remain closed. No remaining accepted resolver value is
removed unless a separate public migration contract approves it.

## 2026-06-01 Implementation Closeout

The cleanup-retirement branch completed the `arbitrated` portion of C2:

- `arbitrated` is no longer in `RESOLVER_MODES`.
- Config loading, GUI normalization, CLI parsers, validation harnesses, and
  direct programmatic `resolver_mode="arbitrated"` inputs reject with
  `arbitrated resolver mode is retired; use region_first_safe_merge`.
- The `arbitrated` facade branch and private merge helpers were deleted.
- `_combine_proposal_sources` was preserved because supported recovery logic
  still uses it.
- The required one-shot 8RAW comparison did not show `arbitrated` materially
  outperforming the supported conservative path.

The closeout note is
`docs/superpowers/notes/2026-06-01-phase8-arbitrated-resolver-retirement-note.md`.

Remaining C2 work is intentionally not completed here: `legacy_savgol` remains
an accepted mode, `local_minimum` remains accepted, CWT evidence remains a
proposal/audit surface, and `region_first_safe_merge` remains the public
compatibility name for conservative local-minimum + WIS/safe-merge behavior.

2026-06-01 current-state reassessment supersedes the older deletion-oriented C2
wording. The executable scope is the public-surface contract below. Current
direction is:

- keep `legacy_savgol` as a useful clean-trace / compatibility path unless a
  separate public migration contract changes it;
- keep local-minimum internals as boundary/proposal evidence;
- treat CWT as an evidence-chain integration assessment, not as dead-code
  deletion;
- first fix resolver public-surface contract drift, including unsupported
  programmatic resolver fallback behavior.

## 2026-06-01 Phase 1 Contract Closeout

Phase 1 completed the C2 public-surface cleanup slice:

- README now distinguishes tracked settings / validation-harness default
  `region_first_safe_merge` from the programmatic `ExtractionConfig`
  compatibility default `legacy_savgol`.
- Accepted top-level values remain `legacy_savgol`, `local_minimum`, and
  `region_first_safe_merge`.
- `region_first_safe_merge` remains a compatibility token for local-minimum
  boundary plus safe-merge/WIS promotion, not a true region-first v2 claim.
- `find_peak_candidates(...)` now rejects unsupported programmatic
  `resolver_mode` values explicitly instead of silently using `legacy_savgol`.
- `ExtractionConfig.resolver_mode = "legacy_savgol"` is preserved and tested as
  a programmatic compatibility default, not the tracked user-facing default.
- `DiscoverySettings.resolver_mode = "local_minimum"`,
  `instrument_qc/pipeline_extraction.py`, and `scripts/run_discovery.py` stay
  intentionally divergent because those flows consume local-minimum boundary
  evidence directly. Changing them would be a behavior decision, not cleanup.
- `scripts/run_alignment.py` continues to accept `region_first_safe_merge` at the
  CLI boundary and coerce production extraction metadata to `local_minimum`.
  This preserves the existing validation contract.

No accepted resolver behavior, selected peak, area, confidence, reason text,
TSV schema, or workbook schema changed in this phase.

## Purpose

Make the resolver public surface honest and consistent across config, README,
GUI, CLI, programmatic defaults, and the peak-detection facade.

C2 no longer means "delete every old resolver except one." User calibration and
current-code review changed the scope:

- `legacy_savgol` remains useful for normal clean peaks and must not be deleted
  in this cleanup phase.
- `local_minimum` internals remain the core boundary/proposal evidence for the
  conservative production path.
- `region_first_safe_merge` remains a compatibility token for conservative
  local-minimum + WIS/safe-merge behavior, not true region-first v2.
- CWT is not a top-level resolver deletion target here; it moves to a separate
  evidence-role assessment.

This phase introduces no behavior change for accepted resolver modes. Validation
is public-contract consistency plus focused tests. A true region-first v2,
resolver default change, or CWT scoring-policy change belongs in a separate
behavior spec.

## Current State

`xic_extractor/settings_schema.py` accepts three resolver values:
`legacy_savgol`, `local_minimum`, and `region_first_safe_merge`.
`arbitrated` is retired and rejected with a migration message.

`xic_extractor/peak_detection/facade.py` dispatches accepted values, rejects the
retired `arbitrated` value with a migration message, and rejects unsupported
programmatic values explicitly.

CWT is an additional proposal/evidence source, not a top-level
`resolver_mode`.

| Mode (top-level dispatch) | Role | Post-P1 status |
|---------------------------|------|----------------|
| `legacy_savgol` | SG smoothing + prominence | Accepted clean-trace / compatibility path; programmatic `ExtractionConfig` compatibility default |
| `local_minimum` | Local minimum boundary | Accepted compatibility and production-internal proposal path |
| `arbitrated` | Merge legacy + local results | **Retired in 2026-06-01 cleanup-retirement branch** |
| `region_first_safe_merge` | Compatibility name for local-minimum boundary plus safe-merge/WIS promotion | **Tracked settings / validation-harness default; alignment production metadata coerces to `local_minimum`; not true region-first v2** |

Plus a **non-dispatched proposal source** (not a `resolver_mode` value, no
`facade.py` branch): `centwave_cwt` invoked via `peak_detection/cwt.py`
infrastructure. After P5 the CWT call only produces flag evidence; it does
not function as a top-level resolver.

Additional intentionally divergent `resolver_mode` surfaces:

- `xic_extractor/discovery/models.py:117`
- `xic_extractor/instrument_qc/pipeline_extraction.py:126`
- `scripts/run_discovery.py` default

These hardcoded sites bypass the canonical settings defaults but are not stale
by themselves. Phase 1 classified them as intentionally divergent until a
separate behavior spec proves they should change.

Validation harness defaults are synchronized with tracked settings at
`region_first_safe_merge`.

## Required Change

Synchronize resolver contract surfaces while preserving accepted behavior.

### Step 1 — Resolver public-surface inventory

Classify every resolver-facing surface as synchronized, intentionally divergent,
or stale:

- `README.md`
- `config/settings.example.csv`
- `xic_extractor/settings_schema.py`
- `xic_extractor/configuration/models.py::ExtractionConfig.resolver_mode`
- `xic_extractor/configuration/settings.py`
- GUI resolver combo and local-minimum panel behavior
- `scripts/run_alignment.py` default and
  `_alignment_production_resolver_mode(...)`
- `scripts/run_discovery.py` default
- `scripts/validation_harness*.py`
- `xic_extractor/peak_detection/facade.py`
- tests and docs that list accepted resolver values

The inventory must state:

- which values remain accepted;
- whether `legacy_savgol` is a normal option, advanced/compatibility option, or
  programmatic compatibility default;
- why `run_alignment.py` may accept `region_first_safe_merge` while production
  extraction metadata still records `local_minimum`;
- whether `ExtractionConfig.resolver_mode = "legacy_savgol"` is intentional
  compatibility or stale default;
- whether validation harness defaults and accepted/rejected resolver values are
  synchronized with the public contract;
- whether the facade unknown-value fallback will be fixed in this phase.

### Step 2 — Preserve completed `arbitrated` retirement

Implementation status: completed in the 2026-06-01 cleanup-retirement branch.
Do not re-open it. This C2 follow-up only verifies that current public surfaces
still reject `arbitrated` with the retirement message and do not list it as an
accepted option.

### Step 3 — Preserve `legacy_savgol` as accepted clean-trace / compatibility path

The earlier draft proposed demoting `legacy_savgol` to a utility and deleting
its top-level resolver path. That instruction is superseded. Current policy:

- keep `legacy_savgol` accepted;
- describe its intended role honestly as clean-trace / compatibility behavior;
- do not delete the module, fallback branch, or SG helper code in this phase;
- only change labels, defaults, or visibility through a public migration
  contract.

### Step 4 — Move CWT questions to the evidence-role spec

The earlier draft treated CWT as a resolver-retirement cleanup item. That
instruction is superseded. Current policy:

- CWT is not a top-level resolver value;
- `centwave_cwt` remains a limited proposal/evidence source;
- CWT scoring points, cap logic, proposal behavior, and future role are owned by
  the CWT evidence-role brainstorming/spec phase, not by C2;
- do not promote or delete CWT in C2.

### Step 5 — Classify hardcoded resolver-mode sites

Hardcoded resolver values are not automatically dead overrides. Classify each
one by owner and reason:

- `discovery/models.py:117` — **intentionally divergent discovery default**:
  discovery consumes local-minimum boundary evidence directly.
- `instrument_qc/pipeline_extraction.py:126` — **intentionally divergent QC
  helper config**: QC extraction uses local-minimum boundary behavior directly.
- `scripts/run_alignment.py` maps `region_first_safe_merge` to `local_minimum`
  for production extraction; this is a public CLI compatibility boundary.
- `scripts/run_discovery.py` defaults to `local_minimum` for discovery-specific
  boundary evidence.

Allowed outcomes:

- keep as an intentionally divergent product contract;
- change to the canonical setting if tests prove no behavior contract is being
  changed;
- document as a later behavior decision.

Do not normalize these values just for tidiness.

### Step 6 — Rename `resolver_mode` (optional)

The public name `region_first_safe_merge` remains imperfect but stable. Two
future options exist:

- (a) keep the field with `region_first_safe_merge` literal for compatibility
  while documenting that the implementation is
  `local_minimum_with_wis_merge_v1`
- (b) remove the field entirely, hardcoding the resolver in `facade.py`

Decision for this phase: keep the current public field and accepted values.
Renaming or removing `resolver_mode` is out of scope.

### Step 7 — Facade unknown-value fail-fast

Implemented in Phase 1: direct programmatic calls to `find_peak_candidates(...)`
with an unsupported `resolver_mode` raise an explicit `ValueError` instead of
falling through to `legacy_savgol`.

This is allowed only if accepted values keep identical behavior and tests cover:

- `legacy_savgol`
- `local_minimum`
- `region_first_safe_merge`
- retired `arbitrated`
- an unknown unsupported value

## Validation Contract

Focused public-contract validation required:

1. Accepted resolver values still load and route as before:
   `legacy_savgol`, `local_minimum`, `region_first_safe_merge`.
2. `arbitrated` still fails fast with the retirement message.
3. Facade unsupported values raise an explicit error.
4. `ExtractionConfig.resolver_mode` default policy is asserted by a focused
   config test, whether the default is kept or changed.
5. README / config example / settings schema / validation harness defaults no
   longer contradict each other on resolver defaults, accepted modes, rejected
   modes, or alignment production coercion.
6. `config/settings.example.csv` no longer claims `linear_edge` is supported for
   `baseline_integration_method`.
7. No RAW validation is required unless this phase changes behavior for an
   accepted resolver mode. If behavior changes, stop and write a behavior spec.

Suggested focused tests:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_config.py tests/test_validation_harness.py tests/test_signal_processing.py tests/test_signal_processing_selection.py tests/test_run_alignment.py tests/test_run_discovery.py tests/test_settings_section_advanced.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
```

## Rollback Condition

Roll back or stop if any of:

- an accepted resolver value changes behavior;
- `legacy_savgol` or `local_minimum` is removed or silently remapped;
- `run_alignment.py` production coercion changes without a behavior spec;
- README/config/GUI/CLI surfaces still disagree after the phase;
- a direct programmatic caller depends on the old unknown-value fallback and no
  migration path is documented.

## What This Spec Does Not Change

- production peak selection for `region_first_safe_merge`
- production peak selection for `legacy_savgol` or `local_minimum`
- local-minimum proposal internals used by the supported conservative default
- true region-first v2 behavior
- CWT scoring, cap logic, or proposal behavior
- AsLS baseline (owned by C1)
- area integration entry (owned by C5)
- hypothesis spine (owned by C3)
- scoring weights
- TSV column names

## Open Questions

- Should the public config value eventually be renamed from
  `region_first_safe_merge` to `local_minimum_with_wis_merge_v1`, or should the
  old name remain as a stable compatibility token until true region-first v2 is
  ready? Defer to a config migration spec.
- Does `_CWT_SAME_APEX_SUPPORT_POINTS = 5` give measurable benefit on the
  strict ISTD benchmark? Current reassessment reframes this as an evidence-role
  inventory plus pre-registered promote / keep-audit / externalize-or-kill gate,
  not an immediate CWT deletion question.
- Does `discovery/models.py:117`'s `resolver_mode = "local_minimum"` override
  serve a discovery-specific purpose (e.g. discovery needs a different
  cutoff than extraction)? Classify before changing it.

## Acceptance Owner

Engineering owner confirms the resolver public-surface inventory, runs focused
contract tests, and records any intentionally divergent defaults. PR includes
the surface inventory summary and the exact tests run.
