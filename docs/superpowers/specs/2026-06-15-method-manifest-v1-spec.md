# method_manifest_v1 productization spec

日期: 2026-06-15
狀態: replay_executor_checkpoint
目標 tier: `missing` -> `production_ready` for targeted CLI replay parity
控制台: [productization control plane](../plans/2026-06-15-productization-control-plane.md)

## Productization intake

- Feature/lane: `method_manifest_v1`
- Current tier: `missing`
- Desired tier this PR: `production_surface`
- Product surface touched:
  - `output/method_manifest.json`
  - targeted extraction CLI run envelope
  - workbook `Run Metadata` references to the JSON manifest and targeted output schema
- Domain authority owner:
  - `xic_extractor.output.method_manifest` owns manifest schema, serialization, and replay envelope semantics.
  - `xic_extractor.configuration.hashing` remains owner of existing `config_hash` and `target_config_hash`; the manifest must label them as fragments, not full method hashes.
  - extraction/pipeline writers remain output producers; they must not recompute domain decisions for the manifest.
- Files/modules likely touched:
  - `xic_extractor/output/method_manifest.py`
  - `xic_extractor/extraction/output_dispatch.py`
  - `xic_extractor/output/metadata.py`
  - `scripts/run_extraction.py`
  - focused tests under `tests/`
- Public contract affected:
  - Adds a new JSON sidecar. Existing CSV/workbook columns and selected peak/area/count/reason behavior must remain unchanged.
  - Adds `xic-extractor-cli --replay-manifest PATH` as a manifest-authoritative replay mode.
  - `Run Metadata` may gain manifest location/schema keys and targeted output schema version, but must remain human-readable.
- Expected output change:
  - Every targeted extraction run writes `method_manifest.json` next to `xic_results.csv`.
  - The manifest contains stable schema/version fields, input artifacts, config fragments, runtime/backend, CLI invocation when available, output artifact pointers, and targeted output schema headers.
- Expected-diff needed: no, unless implementation changes selected peak, area, confidence, reason, counted detection, matrix values, workbook sheet order, or existing required columns.
- Validation fixture: synthetic/focused unit and contract tests first; no 8RAW/85RAW unless output behavior changes beyond additive manifest metadata.
- Stop rule:
  - Stop if the manifest starts requiring full sample metadata universe, review roundtrip, alignment replay, or matrix activation in this lane.
  - Stop if replay execution semantics expand beyond targeted extraction CLI replay from the manifest.
- Rollback rule:
  - Remove the additive sidecar emission and `Run Metadata` reference; existing CSV/workbook outputs must still be produced from current code paths.
- Downstream consumer:
  - short term: validation harness and manifest-driven replay CLI.
  - not in scope: downstream statistical matrix pipeline, manual review import, alignment output contract.

## Capability inventory

Already exists:

- `Run Metadata` workbook sheet with `config_hash`, `app_version`, `generated_at`, resolver and scoring settings.
- `config_hash`: hash of target CSV bytes plus settings CSV bytes, with CLI override bytes reflected.
- `target_config_hash`: target CSV byte hash fragment.
- Headless targeted CLI: `scripts/run_extraction.py`.
- Output sidecars from extraction pipeline and workbook generation.

Implemented by the replay checkpoint:

- Machine-readable `method_manifest.json`.
- Full method envelope naming input artifact hashes, settings/target fragments, runtime/backend, CLI argv, output artifacts, and schema versions.
- `output_schema` block naming targeted output schema version plus long CSV, diagnostics CSV, and score breakdown CSV headers.
- Clear wording that `config_hash` is not a full method hash.
- Focused contract tests proving manifest emission does not mutate product outputs.
- Manifest-driven CLI replay with source artifact validation.

Still missing:

- Timestamped workbook hash capture for full exact replay verification.
- GUI/CLI parity replay smoke on a representative fixture.

## Manifest v1 contract

The manifest is an additive JSON sidecar named `method_manifest.json` written in the same directory as `config.output_csv`.

Required top-level keys:

| Key | Type | Meaning |
|---|---|---|
| `schema_version` | string | Literal `method_manifest_v1`. |
| `generated_at` | string | UTC timestamp in `YYYY-MM-DDTHH:MM:SSZ`. |
| `app_version` | string | Same source as workbook metadata. |
| `run_kind` | string | Initially `targeted_extraction`. |
| `invocation` | object | CLI argv and base/config/output context when available. |
| `input_artifacts` | object | Target/settings/data/DLL/sample metadata artifact descriptors. |
| `config_fragments` | object | Existing hash fragments with explicit scope labels. |
| `method_settings` | object | Stable config values that affect extraction/scoring/output behavior. |
| `target_summary` | object | Target count and role/applicability summary. |
| `runtime` | object | Python/platform/backend/parallel execution information. |
| `output_artifacts` | object | Known output paths and existence/hash status. |
| `replay_status` | object | Whether this manifest is sufficient for exact replay. |

Artifact descriptor shape:

```json
{
  "path": "string or null",
  "exists": true,
  "sha256": "64 hex chars or null",
  "scope": "settings|targets|raw_dir|dll_dir|sample_metadata|output"
}
```

Replay semantics for v1:

- `method_manifest_v1` is a run envelope plus a targeted extraction CLI replay contract.
- `replay_status.capability` must be `manifest_driven_cli_replay`.
- `replay_status.exact_replay_ready` remains `false` until timestamped workbook hash capture is recorded.
- `replay_status.blockers` must explicitly list missing pieces when full exact replay verification is not possible.
- `xic-extractor-cli --replay-manifest PATH` validates schema, run kind, config directory, output mode, required settings/targets hashes, and required raw/DLL directories before extraction.
- Replay mode rejects runtime override flags (`--base-dir`, `--data-dir`, `--skip-excel`, `--excel`, parallel overrides, and expected-diff approval override) so the manifest remains the replay authority.
- Review roundtrip, alignment replay, sample metadata universe, and matrix activation remain out of scope.

### Implementation-ready contract appendix

This appendix closes the pre-implementation contract decisions from review.

#### Path policy

- Output artifacts use paths relative to the output directory when possible.
- Inputs outside the output directory use normalized string paths. They are provenance, not portable replay guarantees.
- Missing optional paths are represented as `null` path, `exists=false`, `sha256=null`.
- Directory artifacts record `exists` and `path`; `sha256` is `null` unless the directory has an explicit manifest file.

#### Required artifact IDs

`input_artifacts` must contain exactly these keys in v1:

- `settings_csv`
- `targets_csv`
- `raw_dir`
- `dll_dir`
- `injection_order_source`
- `rt_prior_library`
- `target_pair_rt_calibration`
- `expected_diff_approval_registry`

`output_artifacts` must contain exactly these keys in v1:

- `output_csv`
- `long_csv`
- `diagnostics_csv`
- `score_breakdown_csv`
- `method_manifest_json`

The timestamped workbook is intentionally excluded from manifest v1 to avoid a hash cycle:
the CLI writes the manifest during extraction output dispatch, then workbook generation
may add a human-readable reverse reference to the manifest. A later replay verification
lane can add workbook hash capture if needed.

#### Required nested fields

Minimal valid JSON shape:

```json
{
  "schema_version": "method_manifest_v1",
  "generated_at": "2026-06-15T00:00:00Z",
  "app_version": "0.2.0",
  "run_kind": "targeted_extraction",
  "invocation": {
    "entrypoint": "xic_extractor.extractor.run",
    "argv": null,
    "base_dir": null,
    "config_dir": null,
    "settings_overrides": {},
    "output_mode": null
  },
  "input_artifacts": {
    "settings_csv": {
      "path": "../config/settings.csv",
      "exists": true,
      "sha256": "64 hex or null",
      "scope": "settings"
    },
    "targets_csv": {
      "path": "../config/targets.csv",
      "exists": true,
      "sha256": "64 hex or null",
      "scope": "targets"
    },
    "raw_dir": {
      "path": "C:/data/raw",
      "exists": true,
      "sha256": null,
      "scope": "raw_dir"
    },
    "dll_dir": {
      "path": "C:/Xcalibur/system/programs",
      "exists": true,
      "sha256": null,
      "scope": "dll_dir"
    },
    "injection_order_source": {
      "path": null,
      "exists": false,
      "sha256": null,
      "scope": "sample_metadata"
    },
    "rt_prior_library": {
      "path": null,
      "exists": false,
      "sha256": null,
      "scope": "rt_prior"
    },
    "target_pair_rt_calibration": {
      "path": null,
      "exists": false,
      "sha256": null,
      "scope": "target_pair_rt_calibration"
    },
    "expected_diff_approval_registry": {
      "path": null,
      "exists": false,
      "sha256": null,
      "scope": "expected_diff"
    }
  },
  "config_fragments": {
    "config_hash": {
      "value": "8hex",
      "scope": "targets_csv + settings_csv_effective_bytes",
      "is_full_method_hash": false
    },
    "target_config_hash": {
      "value": "8hex",
      "scope": "targets_csv_bytes",
      "is_full_method_hash": false
    }
  },
  "method_settings": {
    "resolver_mode": "region_first_safe_merge",
    "smooth_window": 15,
    "smooth_polyorder": 3,
    "ms1_morphology_smoothing_window_points": 15,
    "peak_rel_height": 0.95,
    "peak_min_prominence_ratio": 0.1,
    "ms2_precursor_tol_da": 1.6,
    "nl_min_intensity_ratio": 0.01,
    "count_no_ms2_as_detected": false,
    "parallel_mode": "process",
    "parallel_workers": 1,
    "emit_score_breakdown": false,
    "emit_review_report": false,
    "emit_peak_candidates": false,
    "keep_intermediate_csv": false
  },
  "target_summary": {
    "target_count": 2,
    "analyte_count": 1,
    "istd_count": 1,
    "sample_applicability_values": ["all"],
    "isotope_label_type_values": ["unknown"]
  },
  "runtime": {
    "python_version": "3.x",
    "platform": "Windows-...",
    "backend": "serial",
    "parallel_workers": 1
  },
  "output_artifacts": {
    "output_csv": {
      "path": "xic_results.csv",
      "exists": false,
      "sha256": null,
      "scope": "output"
    },
    "long_csv": {
      "path": "xic_results_long.csv",
      "exists": false,
      "sha256": null,
      "scope": "output"
    },
    "diagnostics_csv": {
      "path": "xic_diagnostics.csv",
      "exists": false,
      "sha256": null,
      "scope": "output"
    },
    "score_breakdown_csv": {
      "path": "xic_score_breakdown.csv",
      "exists": false,
      "sha256": null,
      "scope": "output"
    },
    "method_manifest_json": {
      "path": "method_manifest.json",
      "exists": true,
      "sha256": null,
      "scope": "output"
    }
  },
  "replay_status": {
    "capability": "manifest_driven_cli_replay",
    "exact_replay_ready": false,
    "blockers": [
      "output_mode_not_recorded",
      "timestamped_workbook_hash_not_recorded"
    ]
  }
}
```

#### Emission and output contract

- `method_manifest.json` is always emitted for targeted extraction runs that reach output dispatch, even when `keep_intermediate_csv=false`.
- This intentionally changes the output-directory contract from "no CSV sidecars when intermediate CSV is disabled" to "no CSV sidecars, but always a manifest JSON".
- The manifest must not cause CSV result rows, workbook sheet order, selected peak, area, confidence, reason, counted detection, or matrix values to change.
- `Run Metadata` may add `targeted_output_schema_version`, `method_manifest_schema`, `method_manifest_path`, and `method_manifest_sha256` rows, but existing metadata keys must stay in their current relative order.
- `xic_extractor.extractor.run` may receive an additive keyword-only manifest context only if needed. The preferred v1 path is to keep CLI-specific argv/base-dir context in `scripts.run_extraction` and pure output-context serialization in `xic_extractor.output.method_manifest`.

## Promotion packet

### Capability

- Name: `method_manifest_v1`
- Previous tier: `missing`
- Proposed tier after initial manifest checkpoint: `production_candidate`
- Replay checkpoint tier: `production_ready` for targeted CLI replay parity; not full exact artifact replay.
- Owner: `xic_extractor.output.method_manifest`

### Public surface

- CLI/config/GUI/output/report:
  - additive `output/method_manifest.json`
  - `xic-extractor-cli --replay-manifest PATH`
  - optional workbook `Run Metadata` references: targeted output schema version and manifest schema/path/hash
- Schema/version:
  - `schema_version = method_manifest_v1`
  - `targeted_output_schema_version = targeted_output_v1`
- Downstream consumer:
  - validation harness and manifest-driven CLI replay

### Domain authority

- Decision owner:
  - no selected peak/area/count/reason decision changes in this lane.
- Evidence source:
  - existing config, target, runtime, and output artifact state.
- Why writer/report is not recomputing domain logic:
  - manifest writer serializes provenance and run envelope only; it must not inspect chromatograms or recompute product projection.

### Behavior delta

- What changes:
  - targeted extraction writes a stable JSON manifest sidecar.
  - `xic-extractor-cli --replay-manifest PATH` can rerun from the manifest after validating required input artifacts.
  - workbook metadata can point to the manifest.
- What must not change:
  - selected peak, area, confidence, reason, counted detection, CSV/workbook schema except additive metadata rows.
- Expected-diff artifact:
  - not required unless behavior changes beyond additive metadata.
- Rows/targets/samples affected:
  - none in product result rows; run-level sidecar only.

### Validation

- Synthetic tests:
  - manifest serialization, artifact hashing, missing path handling.
- Focused unit/integration tests:
  - extraction output dispatch emits manifest.
  - metadata rows include manifest reference without breaking existing keys.
  - manifest labels `config_hash` and `target_config_hash` as fragments.
  - replay loader validates required hashes and directories.
  - CLI replay rejects runtime override flags and drifted manifest inputs.
- 8RAW:
  - not required for additive sidecar.
- 85RAW:
  - not required.
- Manual review:
  - not required.
- Downstream smoke:
  - JSON load + required key assertions.

### Audit and replay

- Metadata/provenance:
  - input artifacts, config fragments, target summary, runtime/backend, output artifacts.
- Manifest/replay support:
  - manifest-driven CLI replay for targeted extraction runs.
  - not full exact replay verification until workbook hash capture exists.
- Review/action log:
  - not in scope.

### Stop/rollback

- Stop if:
  - replay semantics expand beyond targeted extraction CLI replay.
  - sample metadata contract becomes a prerequisite beyond recording current `injection_order_source`.
  - output row values or existing workbook schema change.
- Roll back by:
  - removing additive manifest sidecar and metadata references.
- Residual risk:
  - v1 can rerun from a manifest but does not yet verify timestamped workbook artifacts by hash.

## Implementation plan

1. Add `xic_extractor.output.method_manifest` with pure serialization helpers.
2. Write manifest from `extraction.output_dispatch.write_outputs` after existing CSV/diagnostic sidecars are written.
3. Pass optional CLI argv/base-dir/output-mode context from `scripts/run_extraction.py`.
4. Add `--replay-manifest` mode that validates the manifest and refuses runtime override flags.
5. Add focused tests for manifest schema, hashes, output dispatch emission, workbook metadata compatibility, replay validation, and replay CLI behavior.
6. Update productization control plane maintenance log and active board tier after verification.

## Out of scope

- Full exact replay verification with timestamped workbook hash capture.
- Review decision import or manual boundary reintegration.
- Full sample metadata schema.
- Alignment output contract.
- Any change to peak picking, scoring, selected area, detection counting, or matrix activation.

## Implementation closeout

- Implemented owner: `xic_extractor.output.method_manifest`
- Implemented public surface:
  - additive `method_manifest.json` next to targeted extraction output CSV path
  - additive workbook `Run Metadata` rows: `targeted_output_schema_version`, `method_manifest_schema`, `method_manifest_path`, `method_manifest_sha256`
  - CLI context overwrite for `xic-extractor-cli` invocation metadata
  - `xic-extractor-cli --replay-manifest PATH`
  - manifest `output_schema` block with targeted output, long CSV, diagnostics CSV, and score breakdown CSV schema versions/headers
- Tier after replay checkpoint: `production_ready` for targeted CLI replay parity; not full exact artifact replay
- Replay status: `manifest_driven_cli_replay`; not full exact replay-ready because timestamped workbook hash capture is intentionally excluded
- Expected-diff: not required; implementation does not alter selected peak, area, confidence, reason, counted detection, matrix values, existing CSV columns, or workbook sheet order
- Focused validation:
  - `python -m pytest tests\test_method_manifest.py tests\test_output_metadata.py tests\test_extractor.py::test_run_does_not_write_intermediate_csv_by_default tests\test_excel_sheets_contract.py::test_default_output_only_has_one_xlsx -q`
  - `python -m pytest tests\test_method_manifest.py tests\test_run_extraction.py -q`
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\output\method_manifest.py xic_extractor\output\metadata.py xic_extractor\extraction\output_dispatch.py scripts\run_extraction.py tests\test_method_manifest.py tests\test_output_metadata.py tests\test_extractor.py tests\test_excel_sheets_contract.py`
  - `python -m pytest tests\test_method_manifest.py tests\test_output_metadata.py tests\test_excel_pipeline.py tests\test_excel_sheets_contract.py tests\test_csv_to_excel.py tests\test_workbook_compare.py tests\test_extractor.py tests\test_extractor_run.py tests\test_parallel_execution.py -q`
  - `python -m pytest tests\test_output_schema_contract.py tests\test_output_metadata.py tests\test_method_manifest.py -q`
- RAW-backed validation:
  - `docs/superpowers/notes/2026-06-15-replay-executor-validation-note.md`
  - targeted 8RAW CSV-only replay processed `8` RAW files in both runs and emitted `155` diagnostics in both runs.
  - `xic_results.csv`, `xic_results_long.csv`, and `xic_diagnostics.csv` matched byte-for-byte between initial run and replay.
  - targeted 8RAW Excel-mode replay processed `8` RAW files in both runs and workbook compare passed between initial run and replay.
  - targeted 85RAW replay processed `85` RAW files in both runs and emitted `1715` diagnostics in both runs.
  - 85RAW `xic_results.csv`, `xic_results_long.csv`, and `xic_diagnostics.csv` matched byte-for-byte between initial run and replay.
  - 85RAW workbook compare passed between initial run and replay.
  - replay runtime override rejection returned `LASTEXITCODE=2` before opening RAW.
- Residual blocker before full exact artifact replay:
  - no timestamped workbook hash capture
  - no GUI/CLI parity replay smoke because GUI replay is not yet wired to mainline
