# Handoff Productization Consumer Migration Spec

**Date:** 2026-05-28
**Branch / worktree:** `codex/handoff-productization-consumer-migration` /
`.worktrees\handoff-productization-consumer-migration`
**Status:** draft for critical review
**Authoritative inputs:**

- `docs/superpowers/notes/2026-05-27-handoff-productization-c0-source-of-truth.md`
- `docs/superpowers/notes/2026-05-28-handoff-productization-mvp-closeout.md`

## Decision

Migrate the next product-facing consumer after the handoff MVP:
targeted output row projection should consume a selected-hypothesis-derived
integration view from `ExtractionResult`, while preserving current CSV values
and schemas.

The intended runtime direction remains:

```text
TraceGroup -> PeakHypothesis -> EvidenceVector -> IntegrationResult
  -> AuditTrail -> ExtractionResult -> targeted CSV projections
```

This PR may claim `handoff_spine_consumer_migration_ready` /
`production_candidate`. It must not claim `production_ready`, downstream
alignment-matrix migration, default-switch readiness, CWT production promotion,
ASLS promotion, or real-data acceptance.

The C0 note established the scaffold and first audit consumer migration. The
MVP closeout advanced production assembly to consume the selected hypothesis.
This spec is the next targeted product-facing consumer migration. It does not
replace the separate future `alignment_matrix.tsv` handoff decision.

## Why This Consumer

The previous MVP made `ExtractionResult` assembly consume the selected
production-safe `PeakHypothesis`, but targeted output writers still project most
machine-facing values by peeking back into `PeakDetectionResult.peak`.

Moving targeted CSV row projection to a selected integration view is the lowest
cost product-facing migration that is not another audit report:

- it affects a real emitted machine surface;
- it is immediately downstream of `ExtractionResult`, the current selected
  production result object;
- it can be guarded with deterministic parity tests and does not require RAW
  validation unless parity breaks;
- it creates the same consumer pattern future `alignment_matrix.tsv` work should
  use before any matrix behavior change is proposed.

This is intentionally not a direct `alignment_matrix.tsv` migration. The
alignment matrix path has separate owner/backfill/cell-quality semantics. A
writer-only adapter over `AlignedCell` would look like migration without moving
selection or integration authority. Future matrix work should start only after
this output-consumer pattern is proven and should carry its own behavior/parity
contract.

## Scope

### C1 - Selected Integration View On `ExtractionResult`

Add a production-safe selected integration view to `ExtractionResult`.

Expected shape:

- `ExtractionResult` may store the selected `PeakHypothesis` for internal
  product handoff.
- Public compatibility remains: existing `peak_result`, `peak`, `nl_result`,
  `nl_token`, `reported_rt`, `total_severity`, and constructor call sites remain
  valid.
- New or updated read-only accessors expose row-projection values from
  `selected_hypothesis.integration` when present:
  - reported RT;
  - raw area;
  - raw height / intensity from `height_raw`;
  - peak start;
  - peak end;
  - peak width, formatted with the existing absolute-width semantics.
- When no selected hypothesis exists, accessors fall back to current
  `PeakDetectionResult` / selected-candidate behavior.
- The selected integration view must use raw integrated area for current output
  parity. Baseline-corrected area remains separate evidence and must not
  silently replace emitted `Area`.
- Legacy fallback is allowed inside `ExtractionResult` accessors only. Targeted
  output writers should not keep direct `result.peak_result.peak` projection for
  RT, area, intensity, peak start, peak end, or peak width.

### C2 - Result Assembly Wiring

Update `build_extraction_result(...)` so the selected hypothesis passed by
`target_extraction.py` is retained on the emitted `ExtractionResult`.

Constraints:

- Do not rebuild hypotheses in the writer layer.
- Do not import candidate/audit TSV writer modules from production result or
  output code.
- Do not pull CWT audit-only proposals into production `ExtractionResult`.
- Do not generate MS2 evidence for all candidates.

### C3 - Targeted CSV Consumer Migration

Migrate targeted output row builders in `xic_extractor/output/csv_writers.py` to
consume the selected integration view instead of directly formatting
`result.peak_result.peak` fields.

Required parity surfaces:

- `xic_results.csv` header/order unchanged.
- `xic_results_long.csv` header/order unchanged.
- `xic_score_breakdown.csv` header/order unchanged.
- Existing no-peak / error / neutral-loss behavior unchanged.
- Existing detection-counting behavior unchanged.
- `csv_writers.py` should consume projection accessors/protocol fields for
  numeric peak projection. It must not rebuild hypotheses or use audit helpers.

This is a projection migration only. It must not change peak selection,
confidence, reason, score breakdown, NL token priority, target grouping, or
diagnostic semantics.

### C4 - Contract Tests And Closeout

Add focused synthetic tests that prove:

- `ExtractionResult` row-projection accessors use selected
  `IntegrationResult` values when a selected hypothesis exists.
- The same accessors fall back to legacy values when no selected hypothesis is
  present.
- Wide and long CSV row builders emit selected integration values when a
  synthetic fixture deliberately makes selected `IntegrationResult` values
  differ from legacy `PeakDetectionResult.peak`. The test must cover RT, raw
  area, raw intensity, peak start, peak end, absolute peak width, and unchanged
  NL / confidence / reason / schema.
- Wide and long CSV row builders remain value-equivalent when the selected
  hypothesis is produced by `build_production_peak_hypotheses(...)` from the
  same legacy `PeakDetectionResult`. This is the parity oracle for current
  runtime behavior.
- No-peak rows still emit `ND` for RT, area, intensity, start, end, and width.
- Wide and long CSV rows remain value-equivalent for the existing deterministic
  fixture.
- A deliberately different selected-hypothesis integration changes only the
  projection view in a direct accessor test, not production selection logic.
- Score breakdown and NL token behavior remain unchanged.

Add a closeout note after implementation that records:

- this PR migrated a targeted output consumer, not alignment matrix behavior;
- `alignment_matrix.tsv` remains the downstream correction/statistics contract;
- future matrix work needs a separate parity/behavior spec;
- status is `handoff_spine_consumer_migration_ready` /
  `production_candidate`, not `production_ready`.

## Out Of Scope

- Phase2 cleanup.
- `alignment_matrix.tsv` value, schema, writer, or production-decision changes.
- Default resolver, scoring weight, baseline, ASLS, CWT, NL matching, or RT
  policy changes.
- New CLI flags, config keys, workbook sheets, TSV columns, metadata sidecars,
  or report formats.
- Broad refactors of `PeakDetectionResult`, `PeakCandidate`,
  `AlignmentMatrix`, or `AlignedCell`.
- 8RAW / 85RAW validation unless deterministic parity tests expose an
  unintended production output change.

## Public Contracts

Preserve these as byte-level or field-level contracts for this PR:

- `xic_results.csv` schema and formatting.
- `xic_results_long.csv` schema and formatting.
- `xic_score_breakdown.csv` schema and formatting.
- `peak_candidates.tsv` and `peak_candidate_boundaries.tsv` schemas.
- `alignment_matrix.tsv` schema and values.
- CLI flags, config keys, workbook schemas, and resolver/baseline defaults.

## Acceptance Criteria

- `ExtractionResult` exposes a selected integration view with legacy fallback.
- `build_extraction_result(...)` stores the selected hypothesis passed by the
  existing production handoff runtime.
- `xic_extractor/output/csv_writers.py` uses the selected integration view for
  RT, area, intensity, start, end, and width projection.
- `xic_extractor/output/csv_writers.py` no longer directly reads
  `result.peak_result.peak` for RT, area, intensity, start, end, or width
  projection; fallback behavior is owned by `ExtractionResult`.
- Existing output writer tests still pass.
- New tests pin selected-integration projection and legacy fallback behavior.
- New tests include a CSV-level divergent selected-integration fixture so the
  consumer migration cannot pass as an accessor-only wrapper.
- New tests include a runtime-selected-hypothesis CSV parity fixture and a
  no-peak writer regression.
- New tests prove output schemas do not change.
- No alignment matrix code changes are required.
- No audit-only CWT proposals enter production output projection.
- No real-data validation is required unless parity breaks.
- Post-implementation review confirms this is a real product-facing consumer
  migration, not another audit-only adapter.

## Verification

Focused tests:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -p no:cacheprovider tests\test_result_assembly.py tests\test_target_extraction.py tests\test_csv_writers.py tests\test_messages.py tests\test_handoff_spine_runtime.py -q
```

Static checks:

```powershell
python -m py_compile xic_extractor\extractor.py xic_extractor\extraction\result_assembly.py xic_extractor\extraction\target_extraction.py xic_extractor\extraction\handoff_spine_runtime.py xic_extractor\output\csv_writers.py
$env:UV_CACHE_DIR='.uv-cache'
uv run ruff check xic_extractor\extractor.py xic_extractor\extraction\result_assembly.py xic_extractor\extraction\target_extraction.py xic_extractor\extraction\handoff_spine_runtime.py xic_extractor\output\csv_writers.py tests\test_result_assembly.py tests\test_target_extraction.py tests\test_csv_writers.py tests\test_messages.py tests\test_handoff_spine_runtime.py
git diff --check
```

Architecture drift check:

```powershell
rg -n "add_cwt_proposals_for_audit|peak_candidate_table|peak_candidate_boundaries|peak_candidate_audit" xic_extractor\extractor.py xic_extractor\output\csv_writers.py xic_extractor\extraction\result_assembly.py xic_extractor\extraction\handoff_spine_runtime.py
rg -n "peak_result\.peak|result\.peak_result\.peak" xic_extractor\output\csv_writers.py
```

Expected: production result/output code has no audit writer or CWT audit
proposal dependency. The second command should return no projection hits in
`csv_writers.py`; fallback access to legacy `PeakDetectionResult.peak` belongs
inside `ExtractionResult` accessors.

## Stop Rules

Stop before implementation or split the PR if:

- preserving output parity requires changing resolver selection, scoring,
  baseline integration, NL matching, diagnostics, or matrix values;
- output writers need to rebuild hypotheses or call audit TSV helpers;
- the selected integration view cannot represent existing emitted RT / area /
  intensity / boundary values without semantic loss;
- output width cannot preserve the current absolute-width formatting rule;
- a baseline-corrected area would need to replace raw emitted `Area`;
- alignment matrix code becomes necessary to complete this PR;
- focused tests show real production output drift that is not purely an
  intentional accessor-unit-test fixture.

## Review Questions

1. Does this migrate a real product-facing consumer, or is it just another
   compatibility wrapper?
2. Is targeted CSV projection the right next consumer before touching
   `alignment_matrix.tsv`?
3. Are the fallback rules strong enough to preserve current output behavior?
4. Does the spec avoid silently promoting baseline-corrected area into emitted
   `Area`?
5. Are verification commands narrow enough to avoid another expensive,
   non-decision-changing validation loop?
