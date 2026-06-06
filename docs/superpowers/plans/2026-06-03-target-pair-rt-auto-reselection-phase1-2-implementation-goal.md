# Target Pair RT Auto-Reselection Phase 1/2 Implementation Goal

**Date:** 2026-06-03
**Status:** Reviewed v0.3 - ready for Phase 1/2 implementation; no code
execution started
**Readiness target:** `diagnostic_only` after no-RAW Phase 1/2 implementation.
`shadow_ready` requires the optional 2RAW fail-fast plus 8RAW shadow changed-row
gate. Phase 3 product mutation is explicitly out of scope.
**Primary spec:** [Target pair RT auto-reselection spec](../specs/2026-06-03-target-pair-rt-auto-reselection-spec.md)

Reviewer gate:

- `strategy-challenger` xhigh review: blocker re-check passed.
- `implementation-contract-reviewer` xhigh review: blocker re-check passed after
  v0.3 GUI metadata/source-hash wording fix.
- `validation-evidence-reviewer` xhigh review: blocker re-check passed.
- Goal lint: passed with `lint_goal.py`.

```text
/goal
GOAL:
Implement only Phase 1 and Phase 2 of target pair RT auto-reselection: make
target pair-RT metadata/calibration explicit and emit shadow auto-reselection
diagnostics, without changing selected product candidates, workbook detection,
summary counts, final matrix presence, or matrix area values.

CONTEXT:
- Repository/worktree:
  `C:\Users\user\Desktop\XIC_Extractor`, current branch.
- Required repo instructions:
  `AGENTS.md`,
  `docs/agent-subagent-routing.md`,
  `docs/agent-parameter-settings.md` before Python, RAW, DLL, long validation,
  or output-level commands.
- Primary spec:
  `docs/superpowers/specs/2026-06-03-target-pair-rt-auto-reselection-spec.md`.
  This goal may narrow execution scope but must never override the primary spec.
- Related specs:
  `docs/superpowers/specs/2026-06-03-targeted-evidence-chain-alignment-spec.md`,
  `docs/superpowers/specs/2026-06-03-selected-full-envelope-quantitation-boundary-spec.md`.
- Durable evidence rules:
  `docs/lcms-msms-evidence-rules.md`.
- Existing Phase 3 gate surfaces that must remain authority for product switches:
  `xic_extractor/peak_detection/model_selection.py`,
  `xic_extractor/peak_detection/model_selection_approval_registry.py`.
- Existing pair-RT / scoring surface that must be fenced:
  `xic_extractor/rt_prior_library.py`,
  `xic_extractor/extraction/scoring_factory.py`,
  `xic_extractor/peak_scoring.py`.
- Code surfaces to inspect first:
  `xic_extractor/configuration/csv_io.py`,
  `xic_extractor/configuration/targets.py`,
  `xic_extractor/configuration/models.py`,
  `xic_extractor/configuration/settings.py`,
  `xic_extractor/configuration/hashing.py`,
  `xic_extractor/settings_schema.py`,
  `gui/config_io.py`,
  `xic_extractor/extraction/target_extraction.py`,
  `xic_extractor/extraction/output_dispatch.py`,
  `xic_extractor/output/schema.py`,
  `xic_extractor/output/csv_writers.py`,
  `xic_extractor/peak_detection/targeted_product_projection.py`,
  existing candidate/selected-envelope/model-selection diagnostic writers.
- Test surfaces to inspect first:
  `tests/test_settings_new_fields.py`,
  `tests/test_targets_section.py`,
  `tests/test_rt_prior_library.py`,
  `tests/test_scoring_context.py`,
  `tests/test_target_extraction.py`,
  `tests/test_peak_model_selection.py`,
  `tests/test_model_selection_approval_registry.py`,
  `tests/test_output_schema_contract.py`,
  `tests/test_csv_writers.py`,
  `tests/test_selected_full_envelope_diagnostics.py`,
  `tests/test_targeted_product_projection.py`.
- Sentinel labels to preserve exactly:
  `TumorBC2289_DNA / d3-5-medC`,
  `TumorBC2258_DNA / d3-N6-medA`,
  `TumorBC2263_DNA / 8-oxodG`.

CONSTRAINTS:
- Do not implement Phase 3 product mutation.
- Do not emit product `auto_reselected` rows. Phase 2 may emit
  `shadow_auto_reselect_proposed` and `auto_reselect_blocked` only.
- Do not change selected product candidate id, workbook detected/ND state,
  summary detected counts, final matrix value presence, final matrix area,
  selected-envelope product area, or primary output semantics.
- Do not let Mix STDs-only calibration, `config_fallback`, label regex, or ISTD
  presence select a biological-matrix product candidate.
- Do not add a public `STD` role. Targeted product roles remain `ISTD` and
  `Analyte`.
- Do not infer isotope product behavior from target labels. Label regex may be a
  diagnostic suggestion only; product behavior must use explicit metadata or
  calibration artifact fields.
- When `target_pair_rt_calibration_path` is configured, `rt_prior_library_path`
  becomes adapter/debug-only for this goal. It may be read only to produce or
  compare calibration artifacts, but it must not populate scoring RT prior,
  `prefer_rt_prior_tiebreak`, selected-candidate ranking, workbook detection,
  summary counts, or matrix behavior.
- Do not let output writers, workbook/report builders, or diagnostics recompute
  target pair RT selection decisions. They render package-level decision models.
- Do not rescan Mix STDs RAW during normal targeted extraction. Calibration is an
  input artifact.
- Preserve backward compatibility when optional target metadata columns are
  absent.
- Preserve hidden target metadata through GUI load/save/export. Do not silently
  drop metadata. If the GUI cannot safely edit these fields, metadata-present
  target files are no-edit/pass-through for those hidden columns.
- Preserve unrelated dirty worktree changes. Do not stage, revert, commit, push,
  open PRs, or clean generated outputs unless the user explicitly asks.
- Verification integrity: do not weaken tests, assertions, schema checks,
  generated-output checks, or diagnostics gates to make this goal pass.

PHASES:

Phase 0 - Goal Review Gate
Purpose:
- Land this goal only after repo-routed xhigh review closes blockers.
Done when:
- `strategy-challenger`, `implementation-contract-reviewer`, and
  `validation-evidence-reviewer` report no blocking findings, or every blocker is
  fixed in this document and re-checked when material.
- This goal still explicitly excludes Phase 3 product mutation.

Phase 1 - Metadata, Calibration Artifact, And Authority Fence
Purpose:
- Make pair RT knowledge explicit and loadable without changing product behavior.
Allowed work:
- Add optional target metadata fields:
  `isotope_label_type` and `paired_rt_relation`.
- Define and validate metadata enum/default behavior:
  missing columns default to `unknown` / `none`;
  `isotope_label_type` is owned by ISTD rows;
  `paired_rt_relation` is owned by paired Analyte rows.
- Preserve hidden optional metadata fields through GUI target import/export.
  If metadata is present and the visible GUI cannot edit it safely, keep it
  hidden and pass-through on save; do not reject, rewrite, or drop the fields.
- Add advanced setting `target_pair_rt_calibration_path`, default blank/disabled.
- Add `target_pair_rt_calibration.tsv` schema/model/loader with required fields
  from the spec, including `schema_version`, `target_config_hash`, source hash,
  `source_hash_status`, calibration status/level, and transfer status.
- Add or name `compute_target_config_hash(targets_csv)` as a target-only hash
  owner under `xic_extractor/configuration/hashing.py`.
- Ensure the target-only hash changes when target metadata changes and does not
  change only because settings, output paths, or `target_pair_rt_calibration_path`
  changed.
- Add a producer or adapter from existing Mix STDs trend / clean-standard output
  or existing RT prior rows into `target_pair_rt_calibration.tsv`.
- Implement and test the fixed `rt_prior_library` authority fence:
  with `target_pair_rt_calibration_path` configured, legacy `rt_prior_library_path`
  cannot inject scoring RT priors or change selected candidates; it is
  adapter/debug-only.
- Define calibration loader failure handling:
  invalid schema and duplicate `(target_label, paired_istd_label)` rows fail
  configuration loading;
  target hash mismatch and source hash mismatch are non-product blocked rows in
  shadow diagnostics and block product activation;
  missing source hash is allowed only as `source_hash_status=missing` and cannot
  support product activation.
Forbidden work:
- No selected candidate mutation.
- No workbook/matrix/summary/review product behavior changes.
- No Mix STDs RAW scan during targeted extraction.
Done when:
- Focused tests cover target metadata parsing/defaults/invalid enums.
- GUI import/export tests preserve hidden optional metadata fields through
  load/save/export or enforce no-edit/pass-through behavior.
- Settings/config tests cover `target_pair_rt_calibration_path` blank/default and
  explicit path behavior.
- Calibration artifact schema/load tests cover required columns, invalid schema,
  source/config hash mismatch handling, and non-product behavior.
- Target-only hash tests cover include/exclude behavior.
- `rt_prior_library` fence tests prove the new path cannot create duplicate RT
  selection authority.
- Combined-path tests prove enabling both `target_pair_rt_calibration_path` and
  `rt_prior_library_path` does not change candidate selection through legacy RT
  scoring.
- Calibration loader tests cover invalid schema, duplicate rows, hash mismatch,
  and missing source hash behavior.
- No product selected peak or primary output behavior changes.

Phase 2 - Shadow Auto-Reselection Diagnostics
Purpose:
- Prove which target rows would be proposed/blocked for pair-RT reselection, and
  why, while keeping product outputs unchanged.
Allowed work:
- Read `target_pair_rt_calibration_path` into targeted evidence context.
- Hydrate alternate-candidate evidence enough to classify shadow proposals,
  blocked rows, `limited_evidence_shadow`, `inconclusive`, and `blocked_diff`.
- Add package-level decision model/writer for
  `target_pair_rt_auto_reselection.tsv`.
- Write `target_pair_rt_auto_reselection.tsv` under the extraction output
  directory only when `target_pair_rt_calibration_path` is configured and
  `emit_peak_candidates=True`, so the run also emits peer diagnostics such as
  `peak_candidates.tsv` and selected-envelope diagnostics. If calibration is
  configured but `emit_peak_candidates=False`, do not write a standalone Phase 2
  TSV; emit a stable diagnostic/summary reason that shadow reselection artifact
  output was not requested.
- Include required join/audit fields in `target_pair_rt_auto_reselection.tsv`:
  `sample_name`, `target_label`, `role`, `trace_group_id`,
  `previous_candidate_id`, `selected_candidate_id`, `selection_action`,
  `selection_basis`, `selection_status`, `product_switch_allowed`,
  `expected_diff_stable_row_id`, `evidence_comparison_policy`,
  previous/selected RT, paired ISTD RT, expected/observed/error pair delta,
  calibration source/status, missing-MS2 explanation, role policy,
  `gate_decision`, and `block_reason`.
- Add schema/join tests proving the TSV can join to targeted rows,
  `peak_candidates.tsv`, and selected-envelope/model-selection diagnostics.
- Do not add `trace_group_id` to `peak_candidates.tsv`. Join to
  `peak_candidates.tsv` uses `(sample_name, target_label, candidate_id)`, where
  `previous_candidate_id` and `selected_candidate_id` must match
  `peak_candidates.tsv.candidate_id`. `trace_group_id` may join to
  selected-hypothesis/model-selection diagnostics only.
- Add summary counts for `limited_evidence_shadow`, `inconclusive`,
  `blocked_diff`, `shadow_auto_reselect_proposed`, and
  `auto_reselect_blocked`.
- Add `changed_row_denominator` and `false_positive_strata` fields/counts, including
  old/new RT, pair delta error, missing-MS2 opportunity class,
  `product_switch_allowed_true_count`, and `auto_reselected_count`.
- Add sentinel fixture/tests for `d3-5-medC`, `d3-N6-medA`, and `8-oxodG`
  shadow behavior without product mutation.
Forbidden work:
- No product `auto_reselected`.
- Every Phase 2 pair-RT row must have `product_switch_allowed=False`.
- Do not consume the expected-diff approval registry for pair-RT product
  activation during Phase 2.
- No workbook/summary/final-matrix selected candidate, detection, presence, or
  area changes.
- No Phase 3 biological-transfer gate implementation except names/blocked status
  needed for diagnostics.
Done when:
- `target_pair_rt_auto_reselection.tsv` schema/join tests pass.
- Output-dispatch tests prove the TSV is emitted only with calibration configured
  and `emit_peak_candidates=True`, and is not emitted as an orphan artifact
  without peer candidate diagnostics.
- Shadow rows retain old and proposed candidate identity/RT evidence.
- Every Phase 2 row has `selection_action` in
  `none|shadow_auto_reselect_proposed|auto_reselect_blocked`.
- `product_switch_allowed_true_count=0` and `auto_reselected_count=0`.
- `changed_row_denominator`, `false_positive_strata`, old/new RT, pair delta error,
  and missing-MS2 opportunity class are present in the shadow summary.
- Incomplete alternate evidence is reported as `limited_evidence_shadow` or
  `inconclusive`, not promotion-ready.
- Rows without complete analyte MS1 evidence are blocked, not backfilled.
- Sentinel tests show expected shadow proposal/blocking behavior while product
  workbook/matrix behavior remains unchanged.

DONE WHEN:
- Phase 1 and Phase 2 are implemented, tested, and reviewed.
- The primary spec remains the source of product truth and this goal remains a
  finish-line contract, not a duplicate spec.
- `target_pair_rt_calibration_path` exists as a disabled-by-default advanced
  input with schema/hash validation.
- Optional target metadata is parsed and preserved through GUI/import/export
  surfaces. If not visibly editable, it remains hidden no-edit/pass-through and
  must not be rejected, rewritten, or dropped.
- `target_pair_rt_auto_reselection.tsv` exists as the Phase 2 shadow artifact
  with stable join keys and audit fields.
- Baseline-vs-calibration fixture tests prove selected candidate id, workbook
  detection/ND, summary detected counts, final matrix presence, and area values
  are unchanged except for explicit diagnostic/shadow artifacts.
- Product outputs are unchanged except for explicit diagnostic/shadow artifacts
  and schema additions allowed by Phase 1/2.
- No-RAW verification closes `diagnostic_only` only.
- Phase 3 remains blocked and unimplemented.
- Repo-routed read-only review after implementation finds no blocker for Phase
  1/2 closeout.
- `shadow_ready` is claimed only if the optional RAW gate also passes:
  2RAW fail-fast plus 8RAW shadow changed-row gate with unchanged product outputs,
  `changed_row_denominator`, `false_positive_strata`, old/new RT, pair delta error,
  missing-MS2 opportunity class, `product_switch_allowed_true_count=0`, and
  `auto_reselected_count=0`.

VERIFY:
- Run focused no-RAW tests covering configuration, calibration artifact, hash,
  RT-prior fence, shadow diagnostics, output schema, and sentinel fixtures.
- At minimum, start with:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_settings_new_fields.py tests/test_settings_section_advanced.py tests/test_targets_section.py tests/test_rt_prior_library.py tests/test_scoring_context.py tests/test_scoring_factory.py tests/test_target_extraction.py tests/test_extractor_run.py tests/test_peak_model_selection.py tests/test_model_selection_approval_registry.py tests/test_output_schema_contract.py tests/test_csv_writers.py tests/test_peak_candidate_table.py tests/test_targeted_product_projection.py`
- Add and run new focused tests introduced by this goal.
- If the closeout claims only `diagnostic_only`, RAW validation is not required
  unless implementation evidence shows synthetic/fixture tests cannot prove the
  contract.
- If the closeout claims `shadow_ready`, first read
  `docs/agent-parameter-settings.md`, then run the documented 2RAW fail-fast and
  8RAW foreground shadow changed-row gates. Do not run 85RAW for this goal.
- Inspect generated TSV/schema artifacts when tests write them.
- If verification cannot run because of sandbox, dependency, DLL, or RAW runner
  blockers, stop and report the exact blocker instead of substituting an
  unrelated narrower check.

OUTPUT:
- Changed files grouped by Phase 1 and Phase 2.
- Key decisions, especially hash owner, RT-prior fence, and diagnostics owner.
- Verification commands and observed results.
- Whether final status is `diagnostic_only`, `shadow_ready`, or blocked. Explain
  which validation tier supports that label.
- Remaining Phase 3 risks and the next required gate before product mutation.

STOP RULES:
- Stop if any change would mutate selected product candidates, workbook detection,
  summary counts, final matrix presence, or area values.
- Stop if a reviewer identifies a third selection authority, duplicate RT prior
  authority, or Mix STDs/config fallback product promotion path.
- Stop if implementation would require adding `trace_group_id` to
  `peak_candidates.tsv` or changing existing candidate-table public schema
  outside the explicit Phase 2 shadow TSV.
- Stop if target metadata or calibration artifact ingestion would silently drop
  public fields.
- Stop if alternate-candidate evidence cannot be hydrated enough to label rows
  as proposed/blocked/inconclusive without guessing.
- Stop on missing secrets, production credentials, destructive data operations,
  unsafe permissions, or unclear RAW/DLL paths.
- Stop after three failed attempts on the same symptom and revisit root cause.
- Do not mark complete until the final state has been checked against
  `DONE WHEN`.
```
