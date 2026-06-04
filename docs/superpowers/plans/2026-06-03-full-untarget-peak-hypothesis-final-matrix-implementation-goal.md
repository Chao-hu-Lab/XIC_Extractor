# Full Untarget PeakHypothesis Final Matrix Implementation Goal

Reviewer gate:

- `strategy-challenger`: initial blocker was no-split admission. A no-split
  hypothesis must be backed by complete split evaluation, not by relabeling
  unresolved family projections. Re-check verdict: blocker closed.
- `implementation-contract-reviewer`: initial blockers were public schema
  ambiguity, missing identity-sidecar exact schema, and missing product writer
  path ownership. Re-check verdict: blockers closed.

```text
/goal
GOAL:
Implement the full untargeted PeakHypothesis final matrix contract end to end:
the product `alignment_matrix.tsv` and workbook `Matrix` use only `Mz`, `RT`,
and sample columns, while every product row has complete non-projection
`PeakHypothesis` identity recorded in `alignment_matrix_identity.tsv`.

CONTEXT:
- Repository: `C:\Users\user\Desktop\XIC_Extractor`
- Active branch/worktree: `codex/cleanup-retirement-foundation`
- Primary spec:
  `docs/superpowers/specs/2026-06-03-full-untarget-peak-hypothesis-final-matrix-contract.md`
- Superseded spec:
  `docs/superpowers/specs/2026-05-14-final-matrix-identity-contract.md`
- Related activation/diagnostic contract:
  `docs/superpowers/specs/2026-05-30-sidecar-to-product-label-activation-contract.md`
- Evidence guardrails:
  `docs/lcms-msms-evidence-rules.md`
- Routing and validation rules:
  `AGENTS.md`
  `docs/agent-subagent-routing.md`
  `docs/agent-parameter-settings.md` before RAW, Python runner, or long validation commands
- Current product path that must be changed, not bypassed:
  `scripts/run_alignment.py`
  `xic_extractor/alignment/pipeline.py`
  `xic_extractor/alignment/pipeline_outputs.py`
  `xic_extractor/alignment/tsv_writer.py`
  `xic_extractor/alignment/xlsx_writer.py`
- Existing diagnostic/bridge path to preserve as diagnostic-only unless the
  implementation explicitly promotes it:
  `xic_extractor/alignment/shared_peak_identity_explanation/peak_hypothesis_matrix.py`
  `tools/diagnostics/build_peak_hypothesis_matrix.py`
  `tools/diagnostics/apply_shared_peak_identity_activation.py`
- Existing tests that currently protect old family-shaped product output and must be updated intentionally:
  `tests/test_untargeted_final_matrix_contract.py`
  `tests/test_alignment_tsv_writer.py`
  `tests/test_alignment_xlsx_writer.py`
  `tests/test_alignment_pipeline_outputs.py`
  `tests/test_run_alignment.py`
  `tests/test_alignment_pipeline.py`
  `tests/test_shared_peak_identity_peak_hypothesis_matrix.py`
  `tests/test_shared_peak_identity_product_activation.py`
  `tests/test_shared_peak_identity_schema.py`
  `tests/test_shared_peak_identity_mode_window_assignment_gate.py`
- Current known blocker evidence:
  `output/untargeted_hypothesis_product_path_audit_20260603/` reports
  `canonical_row_identity_ready=FALSE`,
  `canonical_row_identity_blockers=family_projection_present`,
  `family_projection_rows=610`, and `projected_cell_count=39091`.

CONSTRAINTS:
- Do not relabel unresolved `family_projection` rows as no-split hypotheses.
  A no-split product row requires `row_identity_basis=no_split_peak_hypothesis`,
  `split_evaluation_status=complete_no_product_ready_split`, and
  `projection_status=not_projection`.
- Product rows must reject `family_projection`,
  `family_projection_no_split_evidence`, incomplete split evaluation,
  raw-overlay-only identity, review-only identity, and any non-`not_projection`
  projection status.
- Preserve the clean product matrix surface: `alignment_matrix.tsv` and workbook
  `Matrix` expose only `Mz`, `RT`, and sample columns.
- Preserve detailed provenance and reviewability by emitting
  `alignment_matrix_identity.tsv` with the exact schema from the spec whenever
  `alignment_matrix.tsv` is emitted.
- Preserve review/audit outputs as the place for ids, old `feature_family_id`
  provenance, evidence status, rejected candidates, and review-only signals.
- Do not change AsLS baseline, integration area policy, target labels, target
  benchmark behavior, or RAW acquisition interpretation except as directly
  required to keep existing values flowing through the new row identity surface.
- Verification integrity: do not weaken or bypass tests, assertions, lint,
  typecheck, validation, generated-output checks, screenshots, or external
  blockers to make the goal pass; fix the root cause or report the blocker.
- Treat the public matrix schema change as a data-migration-style contract
  change for downstream consumers. If a supported `dry-run` path exists, use it
  before overwriting or replacing real output artifacts; if true `dry-run` is
  unavailable, state that explicitly and use a disposable output directory or
  test fixture rehearsal instead.
- Provide rollback or forward-only recovery notes for downstream consumers:
  name the old family-shaped columns, the new clean columns, and the sidecar
  fields that replace old identity/provenance access.
- Provide integrity evidence for any real or fixture output comparison: product
  row counts, identity-sidecar row counts, sample column counts, duplicate
  source-peak checks, and projection-row counts.
- Do not delete legacy family/owner code in this goal. It may remain as
  constructor, adapter, compatibility, provenance, or diagnostic code.
- Do not make target labels part of untargeted product identity.
- Do not weaken lint, typecheck, assertions, schema validation, generated-output
  checks, diagnostic gates, or tests to make the goal pass.
- Do not stage, commit, push, merge, or open a PR unless the user explicitly asks.
- Keep scope limited to product final-matrix identity wiring and its required
  tests/docs. Defer unrelated cleanup, performance tuning, and broad legacy-code
  deletion.

DONE WHEN:
- `alignment_matrix.tsv` emitted by the real untargeted product path has exact
  headers: `Mz`, `RT`, followed by sample columns in `sample_order`.
- Workbook `Matrix` has the same clean row order and public columns as
  `alignment_matrix.tsv`.
- `alignment_matrix_identity.tsv` is emitted through the product output path
  whenever `alignment_matrix.tsv` is emitted, with the exact schema and token
  contract defined in the spec.
- Every product matrix row has exactly one identity-sidecar row with matching
  1-based `matrix_row_index`, matching displayed `Mz`/`RT`, and
  `projection_status=not_projection`.
- No product row uses `family_projection`, `family_projection_no_split_evidence`,
  review-only/raw-overlay-only identity, or incomplete split-evaluation status.
- No-split rows are backed by explicit complete split evaluation:
  `row_identity_basis=no_split_peak_hypothesis` and
  `split_evaluation_status=complete_no_product_ready_split`.
- Split rows, when present in tests, use `row_identity_basis=split_peak_hypothesis`
  and `split_evaluation_status=complete_product_ready_split`.
- A split parent aggregate row and its child rows cannot both write values to
  the product matrix.
- One source peak/cell cannot contribute matrix value to more than one product
  hypothesis row.
- Review-only or raw-overlay-only candidates stay blank in the product matrix
  and remain inspectable in review/audit sidecars.
- Existing diagnostic projection tooling remains diagnostic/bridge-only and
  cannot satisfy complete product identity while projection rows or excluded
  projections remain.
- The old family-shaped public Matrix contract is marked superseded in docs and
  no focused writer/pipeline tests still require family id columns in the
  product `Matrix` surface.
- Migration/recovery notes explain how downstream consumers should replace old
  family-shaped columns with `alignment_matrix_identity.tsv` fields.
- Integrity evidence is captured for focused test fixtures or diagnostic
  artifacts, including:
  product row count equals identity-sidecar row count, sample columns match,
  projection-row count is zero for product output, and duplicate source-peak
  writes are absent.
- No unrelated dirty files are staged or reverted.

VERIFY:
- Run focused product contract tests:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_untargeted_final_matrix_contract.py tests/test_alignment_tsv_writer.py tests/test_alignment_xlsx_writer.py tests/test_alignment_pipeline_outputs.py tests/test_run_alignment.py tests/test_alignment_pipeline.py`
- Run focused PeakHypothesis/activation gate tests:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_shared_peak_identity_peak_hypothesis_matrix.py tests/test_shared_peak_identity_product_activation.py tests/test_shared_peak_identity_schema.py tests/test_shared_peak_identity_mode_window_assignment_gate.py`
- Run lint on touched implementation/test surfaces:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor/alignment tools/diagnostics tests/test_untargeted_final_matrix_contract.py tests/test_alignment_tsv_writer.py tests/test_alignment_xlsx_writer.py tests/test_alignment_pipeline_outputs.py tests/test_run_alignment.py tests/test_alignment_pipeline.py tests/test_shared_peak_identity_peak_hypothesis_matrix.py tests/test_shared_peak_identity_product_activation.py tests/test_shared_peak_identity_schema.py tests/test_shared_peak_identity_mode_window_assignment_gate.py`
- If this goal becomes PR-ready, run the repo PR verification gate from
  `AGENTS.md`:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests`
  `$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor`
  `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -v --tb=short -x`
- If a command fails because sandbox blocks dependency resolution, executable
  spawn, or DLL loading, rerun the same command with approval rather than
  replacing it with a narrower proof.
- If real-data evidence is needed to close a product-readiness claim, first use
  existing no-RAW diagnostics or focused output comparison. Do not start 85RAW
  or a likely long RAW run without the XIC RAW validation skill and explicit
  user approval.

OUTPUT:
- Changed files grouped by product writer path, PeakHypothesis identity path,
  tests, diagnostics, and docs.
- Whether the final state is `diagnostic_only`, `shadow_ready`,
  `production_candidate`, `production_ready`, or `inconclusive`.
- Key decisions made about no-split admission, split rows, identity-sidecar
  schema, output-level wiring, and diagnostic bridge retirement.
- Exact verification commands run and observed results.
- Remaining risk, especially any gap between synthetic/no-RAW verification and
  real 8RAW/85RAW or targeted benchmark evidence.
- Follow-up items for legacy cleanup that were intentionally deferred.

STOP RULES:
- Stop before product wiring if complete split evaluation cannot be defined or
  tested without relabeling unresolved projections.
- Stop if the implementation would keep family/projection semantics in the
  product matrix under a new name.
- Stop if public schema changes conflict with downstream consumers and no
  compatibility or migration decision is documented.
- Stop if RAW runner paths, Thermo DLL paths, or output-level behavior are
  unclear before launching RAW-backed validation.
- Stop on secrets, production credentials, destructive data operations, unsafe
  permissions, or requests to bypass tests/lint/typecheck.
- Stop after three failed attempts on the same symptom and revisit the
  root-cause hypothesis instead of adding patches.
- Do not mark complete until the final state is audited against every `DONE WHEN`
  item in this goal.
```
