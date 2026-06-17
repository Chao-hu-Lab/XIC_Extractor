# Shared Target/Untarget Peak Identity Spine Spec

Status: design input for implementation.

Validation label: `design_input` / `diagnostic_only`.

Updated: 2026-06-17

## Plain-language decision

The work around `NL_FAIL` 5-hmdC rescue is not just a targeted one-off. It is
the same larger problem as untargeted backfill: decide whether a visible MS1
signal is the same chromatographic peak/hypothesis before any workflow writes a
product value.

The shared layer should own peak identity facts. Targeted and untargeted should
not share the final product decision.

In short:

```text
Trace / TraceGroup
  -> PeakHypothesis
  -> EvidenceVector / identity facts
  -> IntegrationResult
  -> workflow-owned product projection
```

Untargeted methods such as own-max shape similarity, same-peak anchor matching,
competing-peak checks, boundary assessability, and provenance validation can be
moved into the shared identity layer. Targeted then adds known-target rules:
paired ISTD RT, target RT window, analyte/ISTD role, paired area ratio, NL/MS2
opportunity, target applicability, and expected-diff activation.

## Why this matters now

The `TumorBC2294_DNA / 5-hmdC` debug case showed the current split clearly:

- current HEAD internally sees a plausible MS1 candidate near `9.11708 min`;
- product output remains `not_counted` because analyte `NL_FAIL` rescue lacks a
  formal activation policy;
- a 5-case own-max diagnostic supports the `9.04-9.17 min` peak mode and makes
  the old `9.7142 min` artifact look like a weak competing peak, not the target
  rescue peak;
- this same own-max evidence style already exists in untargeted/backfill
  product-authority code, but it is not yet a targeted extraction evidence
  provider.

This is the right moment to stop treating targeted rescue and untargeted
backfill as separate algorithm families. They should share evidence providers
and diverge only at workflow policy.

## Architecture preflight contract

Goal:

- Create a shared peak-identity evidence path that both targeted extraction and
  untargeted alignment/backfill can use without leaking workflow-specific
  product rules across the boundary.

Existing owner/helper to reuse:

- Shared carrier: `xic_extractor/peak_detection/hypotheses.py`
  (`PeakHypothesis`, `EvidenceVector`, `IntegrationResult`, `AuditTrail`).
- Shared decision vocabulary: `xic_extractor/evidence_semantics.py`.
- Existing untargeted own-max evidence:
  `xic_extractor/alignment/shared_peak_identity_explanation/ms1_pattern_coherence.py`,
  `tools/diagnostics/family_ms1_overlay_evidence.py`,
  `xic_extractor/alignment/backfill_ms1_product_authority.py`.
- Existing targeted product gate:
  `xic_extractor/extraction/result_assembly.py`,
  `xic_extractor/extraction/paired_area_ratio_projection.py`.

New code location, first likely slice:

- A small package-level helper such as
  `xic_extractor/peak_detection/ms1_shape_identity.py`.
- It should contain only workflow-neutral trace operations:
  Gaussian-smoothed own-max normalization, shape similarity, candidate-to-anchor
  RT delta, competing-peak summary, and missing-metric status.
- It must not import targeted extraction, workbook writers, alignment matrix
  writers, or diagnostic renderers.

Evidence provider role:

- Output identity facts such as:
  - `own_max_same_peak_similarity`;
  - `own_max_same_peak_status`;
  - `own_max_reference_source`;
  - `candidate_anchor_rt_delta_min`;
  - `strongest_competing_peak_own_max_ratio`;
  - `competing_peak_status`;
  - artifact/provenance status when sourced from sidecar traces.
- These facts may feed `EvidenceVector` / `EvidenceDecisionSemantics`, but do
  not directly write matrix values.

Call-cost model:

- Prefer trace context already available in the active extraction/alignment run.
- Do not re-open RAW per row for the shared helper.
- Diagnostic tools may read existing trace CSV/JSON sidecars, but reusable
  package helpers should accept arrays / typed trace objects.
- Batch future RAW-backed evidence by sample/window if new trace extraction is
  unavoidable.

Public contracts at risk:

- `Product State`;
- `Counted Detection`;
- selected RT/area;
- workbook and CSV schema;
- alignment matrix inclusion;
- review/action expected diff.

Validation gate:

- First code slice: synthetic/no-RAW tests for own-max normalization,
  similarity, competing peak, and missing-data statuses.
- Targeted diagnostic slice: reproduce the 5-case 5-hmdC own-max TSV from
  existing trace CSVs without changing product output.
- Product activation slice: expected-diff contract plus focused output tests;
  8RAW before any broader run; 85RAW only once there is a decision it can close.

Stop rule:

- Stop if a shared helper needs target role, ISTD pair, alignment family status,
  matrix state, workbook schema, or output writer knowledge.
- Stop if a diagnostic sidecar starts changing product projection without an
  activation/export contract.
- Stop if an untargeted backfill reason is used as targeted counted-detection
  authority without targeted-specific gates.

## Shared identity facts

These can be shared by targeted and untargeted paths:

| Fact | Meaning | Current source |
| --- | --- | --- |
| MS1 peak present | finite RT/area/height in a candidate interval | targeted peak candidates, alignment cells |
| Own-max shape similarity | trace shape after each trace is scaled to its own maximum | untargeted overlay evidence; 5-hmdC diagnostic |
| Anchor-local same-peak support | candidate matches nearest accepted/detected anchor peak | untargeted MS1 product authority |
| Competing peak summary | stronger or meaningful peak exists outside the candidate window | selected-envelope diagnostics, overlay evidence |
| Boundary assessability | candidate has defensible start/end/baseline | selected envelope / region model-selection diagnostics |
| Candidate-aligned MS2/NL | product/NL evidence belongs to this MS1 group, not a distant event | targeted candidate MS2 evidence |
| Missing opportunity context | DDA/NL missing is `not_observed` unless opportunity proves otherwise | evidence semantics |
| Provenance/hash status | evidence sidecar is fresh and tied to the reviewed trace row | backfill product-authority code |

These facts should be represented as evidence. They are not final product states.

## Targeted-only policy

Targeted extraction owns these final gates:

- target label, role, and expected presence;
- configured target RT window;
- paired ISTD RT support;
- learned or observed analyte-vs-ISTD RT relation;
- paired target/ISTD area ratio;
- analyte/ISTD/RNA applicability rules;
- analyte `NL_FAIL` / `NO_MS2` rescue policy;
- targeted `Product State` and `Counted Detection`;
- expected-diff review before product output changes.

For the 5-hmdC NL-fail rescue path, a future counted projection should require
at least:

1. MS1 candidate positive and coherent.
2. Candidate inside target RT window.
3. Paired ISTD RT support.
4. Paired area-ratio support from counted references.
5. Shared own-max same-peak support.
6. No strong competing peak blocker.
7. No selected-envelope boundary defer/externalize guard.
8. Expected-diff approval before public output changes.

Targeted `paired_area_ratio_support` is not an untargeted identity fact. It is a
targeted quantification/response plausibility gate.

## Untargeted-only policy

Untargeted alignment/backfill owns these final gates:

- data-derived feature/family/mode identity;
- owner/backfill/gap-fill state;
- detected anchor seed count and activation unit;
- duplicate/multi-claim handling;
- family/mode consolidation;
- final alignment matrix row identity;
- product-authority allowlist/provenance for rescued cells.

Untargeted `family_ms1_overlay_anchor_peak_own_max_shape_supported` can become a
shared identity fact, but it must not carry the whole untargeted product
authority chain into targeted extraction.

## What to migrate from untargeted first

Prioritized transplant list:

1. Own-max shape normalization and Pearson similarity over a bounded local grid.
2. Anchor peak cluster assignment against detected/accepted anchors.
3. Competing peak ratio and global/local apex conflict classification.
4. Missing/inconclusive/conflict status vocabulary for trace evidence.
5. Artifact provenance checks when a sidecar trace is used as product support.

Do not migrate first:

- family-level backfill promotion;
- duplicate-loser semantics;
- owner/backfill status names;
- alignment matrix write rules;
- broad family-window rescue.

## First implementation checklist

- [x] Add shared no-RAW tests for own-max normalization and shape similarity.
- [x] Add shared no-RAW tests for competing peak classification.
- [x] Add shared no-RAW tests for missing or flat trace status.
- [x] Add package helper that accepts trace arrays and returns typed identity
      facts.
- [x] Refactor one diagnostic caller to use the helper without changing output.
- [x] Add targeted diagnostic adapter that emits own-max same-peak evidence for
      candidate rows, still `diagnostic_only`.
- [x] Only after the above, add a targeted projection test showing
      `paired_area_ratio_support` alone no longer unlocks analyte `NL_FAIL`
      rescue without own-max same-peak support.
- [x] Add expected-diff fixture before any product output changes.
- [x] Add a callable, non-default ingestion adapter that can turn reviewed
      `targeted_ms1_shape_identity_v0` support rows into projection support
      reasons without wiring it into normal extraction.
- [x] Wire an explicit opt-in settings/CLI entry that consumes the support TSV
      during normal extraction while keeping the default path unchanged.
- [x] Wire a headless auto-limited CLI workflow that builds the support TSV,
      reruns final extraction, and gates the expected diff for the accepted
      `5-hmdC + 5-medC` / `detected_flagged` scope.

## Current evidence from 5-hmdC diagnostic

Artifacts:

- `output/ms1_rescue_5hmdc_own_max_similarity_20260616/own_max_similarity_summary.tsv`
- `output/ms1_rescue_5hmdc_own_max_similarity_20260616/5hmdc_own_max_similarity_diagnostic.png`
- `output/debug_tumorbc2294_5hmdc_current_code_20260616_110408/root_cause_note.md`

Interpretation:

- The five requested `5-hmdC` rows share a same-peak-like own-max MS1 mode near
  `9.04-9.17 min`.
- `TumorBC2294_DNA` supports the `9.1171 min` candidate with own-max r
  `0.95388` and paired ISTD delta `0.0936 min`.
- The old `9.7142 min` artifact has competing peak ratio `0.20005`, which is
  below the provisional review line used in the diagnostic.
- This supports the shared identity fact, but it does not yet authorize a
  targeted product rescue because accepted-analyte anchor authority, paired
  area-ratio activation, and selected-envelope policy still need formal gates.

## Product stance

Current state is split:

- Shared MS1 shape evidence remains `diagnostic_only`.
- Targeted product projection now has a fail-closed unit contract:
  `paired_area_ratio_support` no longer unlocks analyte `NL_FAIL` rescue unless
  `own_max_same_peak_support` is also present.
- The focused expected-diff fixture is synthetic/unit-level only:
  `docs/superpowers/fixtures/targeted_nl_fail_own_max_gate_expected_diff_v0.tsv`.
- A callable ingestion adapter now exists for reviewed
  `targeted_ms1_shape_identity_v0` support rows, and normal extraction can
  consume it only through explicit opt-in configuration:
  `targeted_ms1_shape_identity_support_tsv` or
  `--targeted-ms1-shape-identity-support-tsv`.
- The explicit opt-in path has an 8RAW smoke artifact:
  `output/ms1_shape_identity_optin_8raw_20260616/expected_diff_summary.tsv`.
  It changed exactly one validation-subset row,
  `TumorBC2263_DNA / 5-hmdC`, from not-counted to detected-flagged with
  `own_max_same_peak_support`.
- The first explicit opt-in 85RAW smoke used the manual 5-row support TSV:
  `output/ms1_shape_identity_optin_85raw_20260616/expected_diff_summary.tsv`.
  It changed exactly the five reviewed support TSV rows from not-counted to
  detected-flagged, with no unexpected changed rows.
- A later generic producer 85RAW smoke used the RAW-backed support builder:
  `output/ms1_shape_identity_generic_support_85raw_20260616/expected_diff_summary.tsv`.
  It changed exactly 11 eligible rows from not-counted to detected-flagged:
  10 `5-hmdC` rows plus 1 `5-medC` row. This is the current evidence that the
  rule is not hard-coded to the original five manual review cases.
- The explicit limited headless support-TSV workflow and the headless
  auto-limited CLI workflow are now `production_ready` for the named scope only:
  `limited_5hmdc_5medc_v1`, `5-hmdC + 5-medC`, and `detected_flagged` output
  only. GUI is not connected, and no-flag normal extraction remains off.

Product decision, 2026-06-17: the limited policy may be designed for
`5-hmdC + 5-medC` only, and automatic rescue from this path must write
`detected_flagged` rather than clean `detected`. This is a scope and product
label decision. The repo now has an opt-in limited activation policy guard
(`limited_5hmdc_5medc_v1`), explicit support-TSV config/CLI wiring, replay
override rejection, method-manifest provenance, and an expected-diff gate over
the existing 85RAW generic-support artifact. The gate was hardened to require
the actual `targeted_ms1_shape_identity_v0` support TSV and require the accepted
support keys to exactly match the long-row product diff keys. A later
`xic-extractor-cli --targeted-ms1-shape-identity-auto-limited-default` workflow
now auto-builds the support TSV and reruns final extraction under the same gate.
The no-flag extraction path still remains off: normal extraction does not
auto-build the support TSV unless this explicit auto flag is used, GUI is not
connected, and the default activation policy remains `explicit_support_tsv`.
Product direction update, 2026-06-17: the accepted direction is to reduce manual
intervention. The headless auto-limited CLI is the first bounded automation
step; a future no-flag default can be considered only with a default/UX
activation contract, the same expected-diff gate, and evidence that the broader
workflow remains limited to approved targets and `detected_flagged` output.

Do not claim:

- target/untarget peak identity is unified in product code;
- no-flag/default 5-hmdC NL-fail rescue is production-ready;
- own-max similarity alone can write targeted matrix values;
- untargeted backfill authority can be reused as targeted authority unchanged.

Allowed claim:

- The next correct implementation direction is a shared MS1 same-peak identity
  evidence provider, with targeted and untargeted workflows adding their own
  product activation policies on top.
- The targeted projection gate now fails closed unless explicit
  `own_max_same_peak_support` is part of the support evidence.
- The explicit opt-in support-TSV workflow and the auto-limited headless CLI
  workflow have 8RAW and 85RAW smoke evidence. The first limited headless scope
  is `production_ready` for `limited_5hmdc_5medc_v1`: `5-hmdC + 5-medC` and
  `detected_flagged` output only. The 85RAW auto workflow changed 11 long rows
  and 66 matrix cells, with support TSV key-set equality and unchanged
  diagnostics CSV. It still needs a separate no-flag default/GUI decision before
  it can become unflagged default behavior.

## Implementation note, 2026-06-16

First no-behavior-change slice added:

- `xic_extractor/peak_detection/ms1_shape_identity.py`
- `tests/test_ms1_shape_identity.py`

The helper is workflow-neutral. It accepts RT/intensity arrays and exposes:

- `gaussian_smooth_values(...)`
- `own_max_normalized_trace(...)`
- `local_own_max_shape_similarity(...)`
- `competing_peak_summary(...)`

It does not import targeted extraction, alignment, workbook writers, matrix
writers, RAW readers, or diagnostics. No product projection uses it yet.

Second no-behavior-change slice added:

- `tools/diagnostics/family_ms1_overlay_evidence.py` now delegates its private
  `_gaussian_smooth_values(...)` wrapper to the shared helper while preserving
  the existing diagnostic import surface.
- Existing diagnostic callers that import
  `tools.diagnostics.family_ms1_overlay_evidence._gaussian_smooth_values` keep
  working; this is intentionally a compatibility wrapper, not a public API.
- No TSV/JSON/PNG schema or product projection changed.

Third no-product-behavior slice added:

- `xic_extractor/diagnostics/targeted_ms1_shape_identity.py` adds a targeted
  diagnostic adapter that accepts candidate/reference trace arrays and emits
  `targeted_ms1_shape_identity_v0` rows.
- Supported rows now emit `own_max_same_peak_support` in
  `own_max_same_peak_support_reason`, matching the product projection support
  token without injecting it into normal extraction runs.
- `tests/test_targeted_ms1_shape_identity.py` covers own-max same-peak support,
  strong competing peak warning, missing candidate RT fail-closed behavior, and
  stable TSV columns.
- The adapter is deliberately array/row based. It does not read RAW, change
  selected RT/area, write workbook output, or unlock `NL_FAIL` product rescue.
- `tools/diagnostics/targeted_ms1_shape_identity_from_grid.py` converts an
  existing own-max trace grid plus summary TSV into that row schema. It is a
  maintained replacement for the one-off 5-case conversion script and reads no
  RAW files.

Fourth fail-closed product-projection contract slice added:

- `xic_extractor/extraction/targeted_projection_reasons.py` defines
  `own_max_same_peak_support` as the shared targeted support token.
- `xic_extractor/extraction/result_assembly.py` now requires that token before
  analyte `NL_FAIL` / `NO_MS2` dropout rescue can remove
  `analyte_nl_fail_requires_policy`.
- `paired_area_ratio_projection.py` still does not create own-max evidence; it
  only adds run-level paired RT/area-ratio support.
- `tests/test_result_assembly.py` and
  `tests/test_paired_area_ratio_projection.py` now prove the fail-closed
  behavior and the positive path when the own-max token is already present.
- Synthetic expected-diff fixture:
  `docs/superpowers/fixtures/targeted_nl_fail_own_max_gate_expected_diff_v0.tsv`.
- No RAW-backed extraction run has been rerun for this contract yet.

Fifth callable-ingestion slice added:

- `xic_extractor/extraction/targeted_ms1_shape_identity_projection.py` loads or
  accepts reviewed `targeted_ms1_shape_identity_v0` rows.
- The adapter is fail-closed: it only accepts analyte rows with matching schema
  version, `diagnostic_only`, `diagnostic_only_no_product_write`, inside-window
  status, supported own-max same-peak status, and
  `own_max_same_peak_support`.
- Accepted support rows add `own_max_same_peak_support` to
  `selection_decision.support_reasons`, add evidence-source breadcrumbs, and
  re-run existing product projection through `reproject_extraction_result(...)`.
- At this slice it was callable by tests or a future explicit workflow only;
  the next slice wires the explicit opt-in settings/CLI path. It still does not
  connect GUI, workbook writing, selected-candidate changes, or normal
  extraction defaults.

Sixth explicit-opt-in pipeline slice added:

- `targeted_ms1_shape_identity_support_tsv` is now a canonical optional
  settings key. Empty means disabled.
- `xic-extractor-cli --targeted-ms1-shape-identity-support-tsv <path>` can
  override the settings value for validation runs.
- Replay mode rejects this CLI override so a replay cannot silently swap the
  support TSV outside the recorded invocation/config.
- `xic_extractor/extraction/pipeline.py` loads the TSV once, after run-level
  paired RT/area-ratio projection and before output writing, then reprojects the
  affected sample/target results.
- No GUI entry, workbook schema change, selected-candidate switch, area
  recompute, RAW-backed evidence provider, or default product behavior is added.

Seventh limited-policy product-candidate slice added:

- `targeted_ms1_shape_identity_activation_policy` is now a canonical settings
  key with default `explicit_support_tsv`.
- `limited_5hmdc_5medc_v1` is an explicit opt-in policy. When it is selected,
  the support-TSV loader rejects supported rows outside `5-hmdC` / `5-medC`.
- `xic-extractor-cli --targeted-ms1-shape-identity-activation-policy
  limited_5hmdc_5medc_v1` can override the setting for validation runs, and
  replay mode rejects this override.
- `method_manifest.json` records the activation policy so replay/provenance can
  distinguish the default explicit-support workflow from the limited policy.
- `tools/diagnostics/targeted_ms1_shape_identity_expected_diff_gate.py` gates
  expected-diff artifacts for this limited policy. It verifies long rows only
  move analyte `NL_FAIL` rows from `not_counted/FALSE` to
  `detected_flagged/TRUE` with `own_max_same_peak_support`, and matrix diff
  cells are limited to allowed `5-hmdC` / `5-medC` measurements.
- Existing 85RAW generic-support artifact gate:
  `output/ms1_shape_identity_generic_support_85raw_20260616/limited_default_expected_diff_gate_summary.tsv`
  has `gate_status=pass`, `long_changed_rows=11`, `matrix_changed_cells=66`,
  `target_counts=5-hmdC=10;5-medC=1`, and
  `matrix_target_counts=5-hmdC=60;5-medC=6`.
- 2026-06-17 support key-set hardening: the same gate now requires
  `--support-tsv` and fails closed unless accepted support TSV sample/target
  keys exactly match the long-row expected diff. The 85RAW generic-support
  artifact rerun has `support_tsv_supported_rows=11` and
  `support_tsv_target_counts=5-hmdC=10;5-medC=1`.
- This is still opt-in support-TSV behavior. It does not enable default
  automatic rescue, connect GUI, or broaden beyond `5-hmdC` / `5-medC`.

Verification:

```powershell
python -m pytest tests\test_ms1_shape_identity.py -q
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\peak_detection\ms1_shape_identity.py tests\test_ms1_shape_identity.py
python -m pytest tests\test_ms1_shape_identity.py tests\test_family_ms1_overlay_plot.py tests\test_family_ms1_overlay_batch.py -q
python -m pytest tests\test_family_ms1_alignment_experiment.py tests\test_changed_row_mode_overlay_review.py -q
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\peak_detection\ms1_shape_identity.py tools\diagnostics\family_ms1_overlay_evidence.py tests\test_ms1_shape_identity.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\peak_detection\ms1_shape_identity.py tools\diagnostics\family_ms1_overlay_evidence.py
python -m pytest tests\test_targeted_ms1_shape_identity.py tests\test_ms1_shape_identity.py -q
python -m pytest tests\test_targeted_ms1_shape_identity.py tests\test_targeted_ms1_shape_identity_from_grid.py -q
python -m pytest tests\test_ms1_shape_identity.py tests\test_targeted_ms1_shape_identity.py tests\test_family_ms1_overlay_plot.py tests\test_family_ms1_overlay_batch.py -q
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\peak_detection\ms1_shape_identity.py xic_extractor\diagnostics\targeted_ms1_shape_identity.py tools\diagnostics\family_ms1_overlay_evidence.py tools\diagnostics\targeted_ms1_shape_identity_from_grid.py tests\test_ms1_shape_identity.py tests\test_targeted_ms1_shape_identity.py tests\test_targeted_ms1_shape_identity_from_grid.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\peak_detection\ms1_shape_identity.py xic_extractor\diagnostics\targeted_ms1_shape_identity.py tools\diagnostics\family_ms1_overlay_evidence.py tools\diagnostics\targeted_ms1_shape_identity_from_grid.py
python -m pytest tests\test_result_assembly.py::test_paired_analyte_anchor_and_area_ratio_without_own_max_keeps_nl_fail_not_counted tests\test_result_assembly.py::test_paired_analyte_anchor_area_ratio_and_own_max_downgrades_nl_fail_to_review tests\test_result_assembly.py::test_paired_analyte_role_support_without_own_max_keeps_nl_fail_not_counted tests\test_result_assembly.py::test_paired_analyte_role_support_with_own_max_downgrades_nl_fail tests\test_result_assembly.py::test_approved_expected_diff_pair_evidence_downgrades_analyte_nl_fail -q
python -m pytest tests\test_paired_area_ratio_projection.py::test_run_level_area_ratio_support_without_own_max_keeps_nl_fail_not_counted tests\test_paired_area_ratio_projection.py::test_run_level_area_ratio_support_can_count_own_max_supported_nl_fail -q
python -m tools.diagnostics.targeted_ms1_shape_identity_from_grid --summary-tsv output\ms1_rescue_5hmdc_own_max_similarity_20260616\own_max_similarity_summary.tsv --trace-grid-tsv output\ms1_rescue_5hmdc_own_max_similarity_20260616\own_max_similarity_trace_grid.tsv --output-tsv output\ms1_rescue_5hmdc_own_max_similarity_20260616\targeted_ms1_shape_identity_v0.tsv --target-window-start-min 8.0 --target-window-end-min 10.0
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\extraction\targeted_ms1_shape_identity_projection.py tests\test_targeted_ms1_shape_identity_projection.py tests\test_paired_area_ratio_projection.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\extraction\targeted_ms1_shape_identity_projection.py
python -m pytest tests\test_targeted_ms1_shape_identity_projection.py tests\test_paired_area_ratio_projection.py -q
python -m pytest tests\test_settings_new_fields.py tests\test_extractor_run.py::test_run_applies_targeted_ms1_shape_identity_support_tsv tests\test_run_extraction.py::test_cli_passes_targeted_ms1_shape_identity_support_override tests\test_run_extraction.py::test_cli_replay_rejects_targeted_ms1_shape_identity_support_override -q
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\configuration\models.py xic_extractor\configuration\settings.py xic_extractor\settings_schema.py xic_extractor\extraction\pipeline.py scripts\run_extraction.py tests\test_settings_new_fields.py tests\test_extractor_run.py tests\test_run_extraction.py
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor\configuration\models.py xic_extractor\configuration\settings.py xic_extractor\settings_schema.py xic_extractor\extraction\pipeline.py scripts\run_extraction.py
.venv\Scripts\python.exe -m scripts.run_extraction --base-dir output\ms1_shape_identity_optin_8raw_20260616\baseline --data-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation --skip-excel
.venv\Scripts\python.exe -m scripts.run_extraction --base-dir output\ms1_shape_identity_optin_8raw_20260616\optin --data-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation --skip-excel --targeted-ms1-shape-identity-support-tsv output\ms1_rescue_5hmdc_own_max_similarity_20260616\targeted_ms1_shape_identity_v0.tsv
.venv\Scripts\python.exe -m scripts.run_extraction --base-dir output\ms1_shape_identity_optin_85raw_20260616\baseline --data-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R --skip-excel
.venv\Scripts\python.exe -m scripts.run_extraction --base-dir output\ms1_shape_identity_optin_85raw_20260616\optin --data-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R --skip-excel --targeted-ms1-shape-identity-support-tsv output\ms1_rescue_5hmdc_own_max_similarity_20260616\targeted_ms1_shape_identity_v0.tsv
.venv\Scripts\python.exe -m tools.diagnostics.build_targeted_ms1_shape_identity_supports --long-csv output\ms1_shape_identity_optin_85raw_20260616\baseline\output\xic_results_long.csv --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R --dll-dir C:\Xcalibur\system\programs --config-dir config --output-tsv output\ms1_shape_identity_generic_support_85raw_20260616\targeted_ms1_shape_identity_v0.tsv
.venv\Scripts\python.exe -m scripts.run_extraction --base-dir output\ms1_shape_identity_generic_support_85raw_20260616\optin --data-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R --skip-excel --targeted-ms1-shape-identity-support-tsv output\ms1_shape_identity_generic_support_85raw_20260616\targeted_ms1_shape_identity_v0.tsv
```

All listed no-RAW checks passed on 2026-06-16. The 8RAW baseline/opt-in smoke
also passed on 2026-06-16; summarized diff:
`output/ms1_shape_identity_optin_8raw_20260616/expected_diff_summary.tsv`.
The first 85RAW manual-support baseline/opt-in smoke also passed on
2026-06-16; summarized diffs:
`output/ms1_shape_identity_optin_85raw_20260616/expected_diff_summary.tsv` and
`output/ms1_shape_identity_optin_85raw_20260616/matrix_diff_summary.tsv`.
The generic producer 85RAW opt-in smoke also passed on 2026-06-16; summarized
diffs:
`output/ms1_shape_identity_generic_support_85raw_20260616/expected_diff_summary.tsv`
and `output/ms1_shape_identity_generic_support_85raw_20260616/matrix_diff_summary.tsv`.
