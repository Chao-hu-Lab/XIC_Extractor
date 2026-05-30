# Shared Peak Identity V1.5 / V2 Goal

## Goal

Finish a `diagnostic_only` V1.5 / V2 checkpoint that produces a concrete
shadow-label alignment answer for the current shared peak identity evidence
chain, without treating stale or legacy 85RAW artifacts as scientific proof.

## Context

- Repo instructions: `AGENTS.md`.
- Runtime routing: `docs/agent-subagent-routing.md`.
- RAW / validation settings: `docs/agent-parameter-settings.md`.
- Active spec:
  `docs/superpowers/specs/2026-05-29-shared-peak-identity-evidence-explanation-pilot-design.md`.
- Prior Slice 1 output:
  `output/shared_peak_identity_evidence_explanation_slice1/`.

## Constraints

- Keep this checkpoint `diagnostic_only`.
- Do not mutate `alignment_matrix.tsv`, selected peaks, backfill behavior,
  workbook output, production labels, or downstream contracts.
- Do not use an expected blast-radius manifest as semantic evidence. It is only
  freshness / stale-artifact authority.
- V2 may run in `exploratory_only` mode when blast-radius evidence is not
  current; it must not claim `shadow_ready_candidate` unless the V2 readiness
  facts meet that gate.
- Machine evidence changes must be literature-backed. If a shape, pattern,
  opportunity, or RT-drift metric is not supported by a paper or official method
  document, keep it out of the V2 gate.
- For mass-spectrometry interpretation, missing DDA/product-ion evidence remains
  `not_observed` unless acquisition opportunity and local sensitivity are shown;
  do not infer chemical absence from missing fragmentation alone.
- Do not count manual-oracle-derived shape / pattern / opportunity facts as
  machine-observed evidence.
- Preserve existing Slice 0 and Slice 1 public TSV schemas.

## Done When

- The diagnostic CLI can emit V2 shadow-label artifacts:
  `shared_peak_identity_shadow_labels.tsv`,
  `shared_peak_identity_shadow_alignment_summary.tsv`,
  `shared_peak_identity_v2_readiness.tsv`,
  `shared_peak_identity_machine_evidence_support.tsv`, and
  `shared_peak_identity_v2_report.md`.
- The V2 readiness artifact gives a single machine-readable answer:
  `shadow_ready_candidate`, `exploratory_only`, `blocked_by_vocabulary`, or
  `blocked_by_overfit_risk`.
- Current real artifacts produce an explicit answer explaining whether the
  machine-only evidence chain is ready for autonomous manual-like pass/fail.
- The V2 readiness and support sidecar distinguish machine-observed,
  machine-proxy, manual-oracle-derived, and unavailable evidence, with named
  literature-backed blocker categories.
- Existing CWT and Tier2 raw-trace sidecars can be used as optional
  machine-observed evidence inputs, but their meaning stays diagnostic-only and
  does not imply chemical identity.
- Candidate-MS2 pattern evidence can be generated from reviewed discovery
  candidate joins or the opt-in RAW-boundary fallback only; target-label-only,
  RT/mz-only, or undocumented heuristic joins are out of scope.
- Focused tests pass.
- No unrelated dirty files are introduced.

## Verify

Run focused lint and tests for:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\shared_peak_identity_explanation tools\diagnostics\shared_peak_identity_explanation.py tests\test_shared_peak_identity_schema.py tests\test_shared_peak_identity_shadow_labels.py tests\test_shared_peak_identity_candidate_ms2_pattern.py tests\test_shared_peak_identity_cli.py
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_shared_peak_identity_schema.py tests\test_shared_peak_identity_shadow_labels.py tests\test_shared_peak_identity_candidate_ms2_pattern.py tests\test_shared_peak_identity_cli.py -q
```

Run the current diagnostic with `--enable-shadow-label-alignment` over the
current Slice 1 inputs and inspect `shared_peak_identity_v2_readiness.tsv`.

## Stop Rules

- Stop if V2 would require production behavior changes.
- Stop if the current artifacts cannot identify manual rows and machine rows at
  the same row grain.
- Stop if a test failure requires weakening existing Slice 0 / Slice 1
  contracts.
