# Handoff Productization Phase Closeout

## Verdict

Status: `handoff_productization_phase_closed`.

2026-05-28 update: handoff mainline priority is now governed by
`docs/superpowers/specs/2026-05-28-product-priority-reset-decision-spec.md`.
The `alignment_matrix_handoff_behavior_spec` next action below has already been
completed by PR70. Further handoff mainline work must first resolve
`QUAL_SELECTION_READY_FOR_NEXT_BEHAVIOR_PR`.

The targeted handoff / CSV consumer surfaces remain `production_candidate`.
That status is limited to the already tested targeted selected-hypothesis
handoff and targeted CSV numeric projection. It is not a repo-wide readiness
claim and does not apply to `alignment_matrix.tsv`, resolver defaults, baseline
defaults, CWT promotion, ASLS promotion, or broad legacy retirement.

This closeout is a decision artifact. It does not change production behavior,
schemas, matrix values, resolver selection, baseline behavior, or diagnostics
semantics.

## What Actually Changed

- C0 established the product direction:
  `TraceGroup -> PeakHypothesis -> EvidenceVector -> IntegrationResult ->
  AuditTrail -> downstream matrix`.
- The scaffold made `peak_candidates.tsv` and
  `peak_candidate_boundaries.tsv` explicit debug/audit projections, not the
  canonical domain model.
- The MVP added a production-safe handoff runtime and selected-hypothesis handoff
  for targeted extraction result assembly.
- The consumer migration moved targeted CSV numeric projection to
  `ExtractionResult` selected-integration accessors while preserving emitted CSV
  schemas and values.
- Current source inspection shows `selected_handoff_peak(...)` is product-facing
  through targeted extraction, while the downstream alignment matrix still uses
  alignment owner/backfill models.

## Public Contracts Preserved

- `alignment_matrix.tsv` remains the downstream correction/statistics delivery
  surface and is not migrated in this phase.
- `xic_results.csv`, `xic_results_long.csv`, and `xic_score_breakdown.csv`
  schemas and formatting are unchanged.
- `peak_candidates.tsv` and `peak_candidate_boundaries.tsv` schemas are
  unchanged and remain debug/audit projections.
- CLI flags, config keys, workbook schemas, resolver defaults, baseline
  defaults, scoring behavior, RT policy, NL matching, and diagnostic status
  meanings are unchanged.

## Legacy Retirement Readiness Matrix

| Surface | Owner | Label | Evidence | Blocker | Next action | Next PR target |
| --- | --- | --- | --- | --- | --- | --- |
| `TraceGroup` / trace context | `peak_detection.traces`, `extraction.trace_context`, `alignment.trace_context` | `keep_for_now` | C0 source of truth and focused hypothesis / candidate tests use it as the future-facing trace wrapper. | Not a retirement candidate; semantics are not yet universal across every targeted and untargeted path. | Keep as spine contract and extend only when a consumer needs a missing semantic field. | No |
| `PeakHypothesis` / `EvidenceVector` / `IntegrationResult` / `AuditTrail` | `peak_detection.hypotheses` | `keep_for_now` | Candidate and boundary projections can build rows from hypotheses without legacy results; CSV consumer migration uses selected integration through `ExtractionResult`. | Evidence schema is still evolving and is not the only production source of truth for alignment. | Treat as the preferred new domain model; do not freeze as universal scoring authority yet. | No |
| `handoff_spine_runtime.py` | `extraction.handoff_spine_runtime` | `keep_for_now` | CodeGraph and source inspection show `selected_handoff_peak(...)` is called by targeted extraction. Runtime helper avoids audit TSV writer dependency. | Only targeted extraction consumes it; alignment matrix does not. | Keep as the production-safe targeted bridge. | No |
| `ExtractionResult.selected_hypothesis` and selected integration accessors | `extractor.ExtractionResult` | `facade_only` | Targeted CSV projection reads `reported_*` accessors instead of directly projecting legacy peak fields. | `ExtractionResult` still stores `PeakDetectionResult` for compatibility and for behavior not yet spine-owned. | New consumers should use accessors or spine-facing adapters, not raw legacy peak projection. | No |
| Targeted CSV projection | `output.csv_writers` | `facade_only` | Writer protocol includes `reported_peak_area`, `reported_peak_intensity`, boundary, width, and RT accessors; focused tests pin schema and values. | Emitted CSV remains a public compatibility surface. | Preserve schema; keep future value changes behind behavior specs. | No |
| `peak_candidates.tsv` / `peak_candidate_boundaries.tsv` projection builders | `extraction.peak_candidate_table`, `extraction.peak_candidate_boundaries`, `output.peak_candidates`, `output.peak_candidate_boundaries` | `externalize` | C0 and contract tests define them as debug/audit projections with frozen headers. | They are useful review artifacts but not the canonical product matrix. | Keep as optional projection surfaces; do not let them drive production behavior. | No |
| `PeakDetectionResult` / `PeakCandidate` / `PeakResult` | `peak_detection.models`, `signal_processing` compatibility facade | `needs_behavior_spec` | Resolver output, scoring context, messages, detection, and fallback behavior still depend on these models. | Retiring them would change production selection, messaging, or compatibility imports. | Keep active until a behavior spec migrates one production owner at a time. | No |
| `output.messages` and `output.detection` | `output.messages`, `output.detection` | `keep_for_now` | These modules still encode active user-facing message and counted-detection semantics. | Their rules are not represented fully in the hypothesis spine. | Leave as active behavior owners; migrate only with message/detection parity tests. | No |
| Anchor diagnostics and ISTD recovery helpers | `extraction.istd_recovery`, alignment / RT diagnostic helpers | `keep_for_now` | These paths encode domain-specific recovery and RT evidence behavior used by current outputs and diagnostics. | Spine does not yet own anchor recovery policy or RT correction semantics. | Keep; do not fold into handoff spine until a behavior spec names the policy. | No |
| `alignment_matrix.tsv` / `AlignedCell` / owner-backfill path | `alignment.matrix`, `alignment.pipeline`, `alignment.backfill`, `alignment.family_integration`, `alignment.owner_backfill` | `needs_behavior_spec` | CodeGraph/source inspection shows alignment output is still produced by alignment cell and owner/backfill models, not by targeted selected-hypothesis handoff. | This is the downstream delivery surface; migration can affect matrix values, cell status, and benchmark validation. | Write a parity / behavior spec for spine-derived matrix handoff before any migration. | Yes |
| Legacy resolver surfaces | resolver modules and `signal_processing` facade | `needs_behavior_spec` | Resolver choice and selected peak behavior remain production semantics. | Retirement or default switch changes selected RT/boundary/area behavior. | Keep until a reviewed resolver behavior plan authorizes promotion or retirement. | No |
| Baseline / ASLS surfaces | baseline integration modules and recent baseline specs | `needs_behavior_spec` | ASLS and baseline truth work support future behavior decisions but are not switched by handoff closeout. | Baseline change affects area and requires its own behavior acceptance. | Keep separate from handoff closeout; promote only under baseline-specific behavior spec. | No |

## Recommended Next PR

Recommended next PR: `alignment_matrix_handoff_behavior_spec`.

This PR should not start by changing matrix code. It should first write the
behavior/parity spec for whether `alignment_matrix.tsv` can consume a
spine-derived selected integration contract while preserving the downstream
correction/statistics contract. That spec should define:

- the value parity surface for `alignment_matrix.tsv`;
- which `AlignedCell` fields are spine-compatible and which remain
  alignment-owned;
- rollback rules if spine-derived values diverge;
- whether 8RAW or 85RAW validation is needed after a real behavior migration.

Phase2 cleanup should remain deferred unless it avoids the same core files or
the matrix handoff spec explicitly says the cleanup is no longer blocked.

## Non-Decisions

- No full legacy retirement is authorized.
- No `alignment_matrix.tsv` migration is authorized.
- No resolver default, baseline default, CWT production, ASLS promotion, NL
  matching, RT policy, or matrix value change is authorized.
- No 8RAW / 85RAW validation is claimed by this closeout.
- No new audit report is introduced.

## Verification

Completed in `codex/handoff-productization-closeout`.

Focused handoff / CSV tests:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -p no:cacheprovider tests\test_handoff_spine_runtime.py tests\test_result_assembly.py tests\test_target_extraction.py tests\test_csv_writers.py tests\test_peak_candidate_table.py tests\test_peak_candidate_boundaries.py tests\test_peak_candidate_audit.py -q
```

Result: `51 passed in 2.08s`.

Closeout contract test:

```powershell
python -m pytest -p no:cacheprovider tests\test_handoff_spine_runtime.py tests\test_result_assembly.py tests\test_target_extraction.py tests\test_csv_writers.py tests\test_peak_candidate_table.py tests\test_peak_candidate_boundaries.py tests\test_peak_candidate_audit.py tests\test_handoff_phase_closeout_contract.py -q
```

Result: `53 passed in 2.09s`.

Test contract compile / lint:

```powershell
python -m py_compile tests\test_handoff_phase_closeout_contract.py
$env:UV_CACHE_DIR='.uv-cache'
uv run ruff check tests\test_handoff_phase_closeout_contract.py
```

Result: compile passed; ruff reported `All checks passed!`.

Static / artifact checks:

```powershell
$repo = (Resolve-Path .).Path
git -c safe.directory="$repo" diff --check
rg -n "phase closeout|handoff_productization_phase_closed|legacy retirement" docs\superpowers\notes\2026-05-27-handoff-productization-c0-source-of-truth.md docs\superpowers\notes\2026-05-21-lcms-msms-handoff-progress-checklist.md
python -c "from pathlib import Path; paths=[Path('docs/superpowers/specs/2026-05-28-handoff-productization-phase-closeout-spec.md'), Path('docs/superpowers/plans/2026-05-28-handoff-productization-phase-closeout-goal.md'), Path('docs/superpowers/plans/2026-05-28-handoff-productization-phase-closeout-implementation-plan.md'), Path('docs/superpowers/notes/2026-05-28-handoff-productization-phase-closeout.md')]; bad=[str(p) for p in paths if p.exists() and sum(1 for line in p.read_text(encoding='utf-8').splitlines() if line.startswith(chr(96)*3)) % 2]; raise SystemExit('Unbalanced markdown fences: '+', '.join(bad) if bad else 0)"
codegraph status
git status --short --branch
```

Result: passed. `git diff --check` reported only LF-to-CRLF working-copy
warnings for the two edited historical notes. The source-of-truth pointer grep
found the expected C0/checklist references, the Markdown fence check passed,
CodeGraph reported the index up to date after `codegraph sync`, and `git status`
showed only the expected closeout docs plus the closeout contract test.

## Remaining Risk

- The spine is product-facing but not product-complete.
- The most important downstream surface, `alignment_matrix.tsv`, is not yet
  spine-derived.
- Legacy result models still own resolver, scoring, message, recovery, and
  alignment behavior.
- Any future retirement needs a behavior spec and parity tests, not just a docs
  assertion.
