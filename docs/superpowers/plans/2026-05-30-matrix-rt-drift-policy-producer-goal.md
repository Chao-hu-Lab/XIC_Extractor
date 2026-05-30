# Matrix RT Drift Policy Producer Checkpoint Goal

## GOAL

Implement a diagnostic-only producer for the Shared Peak Identity
`matrix_rt_drift_policy` sidecar, using existing alignment and RT-drift
diagnostic artifacts so V2 readiness can distinguish RT drift supported by
machine evidence from drift claims that still fail closed. Do not enable
production labels.

## CONTEXT

- Repo contract: `AGENTS.md`.
- Runtime goal and validation routing:
  `docs/agent-subagent-routing.md`, `docs/agent-parameter-settings.md`.
- Current V2 diagnostic entrypoint:
  `tools/diagnostics/shared_peak_identity_explanation.py`.
- Existing consumer contract:
  `xic_extractor/alignment/shared_peak_identity_explanation/machine_evidence_support.py`.
- Existing RT drift evidence surfaces:
  - `alignment_cells.tsv`: row-level `rt_delta_sec`.
  - `owner_edge_evidence.tsv`: `rt_raw_delta_sec`,
    `rt_drift_corrected_delta_sec`, and `drift_prior_source`.
  - `rt_normalization_families.tsv`: family-level raw vs normalized RT range
    improvement.

## CONSTRAINTS

- Keep the producer `diagnostic_only`.
- Do not mutate `alignment_review.tsv`, `alignment_cells.tsv`,
  `alignment_matrix.tsv`, workbooks, selected peaks, backfill behavior, or
  production labels.
- Reuse existing artifacts only. Do not launch RAW extraction or fit a new RT
  model inside this producer.
- Treat RT as contextual evidence. A large raw RT delta can be explainable only
  when an existing drift-corrected or normalization artifact supports it.
- Fail closed on missing, stale, contradictory, or unjoinable artifacts.

## EVIDENCE PRIORITY

1. If the row-level `alignment_cells.rt_delta_sec` is already inside the
   preferred RT window, emit `rt_close`.
2. If `owner_edge_evidence.tsv` joins to the same family/sample through sample
   stem, precursor m/z, selected apex RT, and an existing `strong_edge`, and
   shows a drift-corrected delta inside the preferred RT window, emit
   `drift_supported`.
3. If owner-edge evidence is absent but `rt_normalization_families.tsv` shows
   family-level normalization improvement large enough to explain the row
   delta, emit `drift_supported`.
4. If either source contradicts the row delta, emit `drift_not_supported`.
5. Otherwise emit `inconclusive`, which the V2 consumer must not count as
   machine-observed support.

## DONE WHEN

- The CLI can either read an existing `--matrix-rt-drift-policy-tsv` or generate
  `shared_peak_identity_matrix_rt_drift_policy.tsv` with
  `--generate-matrix-rt-drift-policy` plus optional owner-edge and/or
  RT-normalization artifacts.
- Generated rows use the same required columns as the current consumer sidecar.
- Generated `rt_close` or supportive drift rows can close
  `matrix_rt_drift_policy` for `rt_drift_possible`; contradictory rows fail
  closed as `matrix_rt_drift_policy_not_supportive`.
- Focused tests cover direct RT-close, owner-edge support, owner-edge conflict,
  RT-normalization support, CLI generation, and ambiguous CLI argument rejection.

## VERIFY

Run focused no-RAW tests:

```powershell
python -m pytest tests\test_shared_peak_identity_matrix_rt_drift_policy.py tests\test_shared_peak_identity_shadow_labels.py tests\test_shared_peak_identity_cli.py -q
```

Run lint/typecheck for touched Python:

```powershell
uv --cache-dir .uv-cache run ruff check tools\diagnostics\shared_peak_identity_explanation.py xic_extractor\alignment\shared_peak_identity_explanation tests\test_shared_peak_identity_matrix_rt_drift_policy.py tests\test_shared_peak_identity_shadow_labels.py tests\test_shared_peak_identity_cli.py
uv --cache-dir .uv-cache run mypy xic_extractor\alignment\shared_peak_identity_explanation tools\diagnostics\shared_peak_identity_explanation.py
```

## STOP RULES

- Stop if closing the drift blocker requires new RAW reads, new RT model fitting,
  product label promotion, matrix correction, or workbook/downstream schema
  changes.
- Stop if existing artifacts cannot be joined without heuristic target-label
  leakage.
- Stop after three repeated failures on the same command symptom and revisit
  the root cause.
