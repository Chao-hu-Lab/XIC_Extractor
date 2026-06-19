# LC-MS CID Neutral Loss Discovery Architecture Alternatives Brief

## Status

Decision document only. Do not implement either alternative from this brief until
the expected diff and validation gate are accepted.

This brief compares two ways to continue the CID-NL Discovery redesign:

- **A: Incremental owner-deepening** inside the current Discovery workflow.
- **B: Feature-primary replacement** that makes MS1 feature identity an explicit
  intermediate model before MS2/CID-NL evidence becomes a normal Discovery row.

Hard constraint:

- There must not be two maintained Discovery systems.
- If B is approved, `scripts/run_discovery.py` remains the public entry point,
  old internals become a thin compatibility facade or are deleted in the same
  migration sequence, and product code must not keep an A/B runtime flag after
  validation closes.

## Shared Product Rule

Row identity is an MS1 chromatographic feature. CID-NL/MS2 evidence can support,
rescue, or downgrade that feature, but a scan precursor, product+NL inference, or
single MS2 event cannot directly become matrix-writing authority.

## Current Baseline

Current flow:

1. `scripts/run_discovery.py`
2. `xic_extractor.discovery.pipeline.run_discovery`
3. `collect_strict_nl_seeds`
4. `group_discovery_seeds`
5. `backfill_ms1_candidates`
6. `assign_feature_families`
7. `csv_writer`
8. `alignment/csv_io.py`

Current real-data evidence:

- The `product_plus_neutral_loss` rescue baseline exists.
- The `300.1605 -> 184.113` TumorBC2312_DNA candidate is recovered as
  `TumorBC2312_DNA#19561@mz300.160635_p184.113235`.
- The `301.165 -> 185.116` isotope-related tag row remains valid and must not be
  deleted just because it is isotope-related.
- Current validation is `diagnostic_only` for the new Discovery/alignment
  evidence; default matrix activation still needs a separate expected-diff rerun.

## Alternative A - Incremental Owner-Deepening

Shape:

- Keep the current orchestration order.
- Add explicit machine fields inside existing owners:
  - `discovery_candidate_state`;
  - `ms1_feature_row_id`;
  - acquisition metadata and absence reason fields;
  - evidence path and decision reason code.
- Treat `candidate_id` as legacy provenance until `ms1_feature_row_id` is ready
  to become the alignment row key.

Expected diff:

- Mostly additive CSV columns.
- `candidate_id` remains available; parser accepts legacy fixtures.
- Candidate counts should stay close to current outputs unless the new
  `discovery_candidate_state` marks rows as review-only/reject.
- No default matrix, ProductWriter, GUI, workbook, Backfill authority, or 85RAW
  behavior changes.

Why A may be better:

- Lower migration risk.
- Smaller public contract diff.
- Easier to land with focused tests and the existing 300/184 checker.
- Keeps current validated recall rescue while making the hidden row-state policy
  explicit.

Why A may be worse:

- The current flow is still MS2-seed-first; it may keep leaking scan-centric
  assumptions into row identity.
- `candidate_id` remains scan-bound until a later migration.
- The code may stay harder to reason about if `ms1_backfill` continues to be both
  feature reconciliation and candidate construction.

## Alternative B - Feature-Primary Replacement

Shape:

- Keep `scripts/run_discovery.py` as the public entry point.
- Replace the internal row-construction model with an explicit
  `DiscoveryFeature` / `PeakHypothesis`-like layer:
  - MS1 feature hypothesis owns apex m/z, RT apex, RT bounds, area, height,
    trace quality, and feature identity.
  - MS2 scans become evidence events attached to features.
  - scan-precursor, isolation metadata, and product+NL inference are evidence
    paths, not row keys.
  - repeated DDA scans collapse under the same feature boundary before CSV row
    rendering.
- Current `ms2_seeds`, `grouping`, and `ms1_backfill` logic is either moved
  behind this feature-primary model or deleted after migration.

Expected diff:

- Public row identity likely changes:
  - `ms1_feature_row_id` becomes the primary alignment row key;
  - legacy `candidate_id` becomes provenance or compatibility-only;
  - parser tests must prove old artifacts either remain readable or fail with a
    clear migration message.
- Candidate counts may decrease if repeated MS2 events collapse earlier.
- Review-only/rejected counts may increase if product+NL evidence has no
  matching MS1 feature.
- Row ordering may change and must be listed in expected-diff output.
- A successor checker is required before RAW validation if legacy
  scan-bound `candidate_id` no longer names the row.

Why B may be better:

- Better matches mature feature-first LC-MS software patterns.
- Makes the product rule easier to explain: row = MS1 feature, evidence = MS2/NL.
- Reduces the chance that representative scan choice changes row identity.
- Can remove the conceptual overload from `ms1_backfill`.

Why B may be worse:

- Larger migration and review surface.
- Higher risk of breaking alignment parser assumptions and historical fixtures.
- Could increase RAW/XIC cost if implemented as global MS1 enumeration instead
  of evidence-scoped feature hypotheses.
- Needs stronger expected-diff tooling before it is safe to run broad validation.

## A/B Comparison Oracle

Use the same oracle for both alternatives.

Must win or tie:

- `300.1605 -> 184.113` is recovered in TumorBC2312_DNA and QC samples.
- `301.165 -> 185.116` remains present when it carries its own tag evidence.
- Repeated MS2 under one MS1 peak does not produce duplicate normal rows.
- product+NL without a real MS1 peak is review-only/reject, not a normal row.
- co-isolation or multiple plausible MS1 features is ambiguous, not silently
  accepted.
- alignment parser can read the chosen CSV contract.

Metrics to compare:

- true-feature recall for named manual/EIC cases;
- candidate count, normal/review-only/reject count, duplicate row count;
- `scan_precursor`, `product_plus_neutral_loss`, and `mixed` basis counts;
- RAW opens, MS2 scans iterated, XIC calls, smoothing/integration calls;
- seed/group/candidate/feature counts;
- 8RAW runtime and timing-stage deltas;
- number of changed public columns and changed row identifiers.

Decision rule:

- Choose A if it matches B on recall and row-inflation safety while keeping a
  smaller public contract diff.
- Choose B only if it gives a material gain in row identity clarity, duplicate
  collapse, false-row control, call cost, or maintainability.
- If B wins, do not ship it as a second path. Convert old internals into a thin
  facade or delete them after parser/output migration passes.

## Validation Commands

### No-RAW focused contract gate

```powershell
uv run pytest tests/test_discovery_ms2_seeds.py tests/test_discovery_grouping.py tests/test_discovery_ms1_backfill.py tests/test_discovery_csv.py tests/test_alignment_csv_io.py tests/test_discovery_pipeline.py -v --tb=short
```

```powershell
uv run python scripts/check_discovery_precursor_inference_artifact.py --check-only --summary-json output\discovery_architecture_ab\baseline_precursor_inference_check.json
```

### One-RAW named manual/EIC gate

Run this for each implemented variant output. Use `a_incremental` or
`b_feature_primary` as `<variant>`.

```powershell
.venv\Scripts\python.exe scripts\run_discovery.py `
  --raw C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation\TumorBC2312_DNA.raw `
  --dll-dir C:\Xcalibur\system\programs `
  --output-dir output\discovery_architecture_ab\<variant>\one_raw_tumorbc2312 `
  --rt-min 22 `
  --rt-max 25 `
  --timing-output output\discovery_architecture_ab\<variant>\one_raw_tumorbc2312\timing.json
```

For A, the existing checker should remain usable:

```powershell
.venv\Scripts\python.exe scripts\check_discovery_precursor_inference_artifact.py `
  --candidates-csv output\discovery_architecture_ab\a_incremental\one_raw_tumorbc2312\discovery_candidates.csv `
  --expected-row-count 157 `
  --summary-json output\discovery_architecture_ab\a_incremental\one_raw_tumorbc2312\precursor_inference_check.json `
  --check-only
```

For B, do not treat the old checker failure as a scientific failure if the row
key changed. B must first add a successor expected-diff checker that verifies the
same biological facts by `ms1_feature_row_id` and provenance.

Proposed command shape after that checker exists:

```powershell
.venv\Scripts\python.exe scripts\check_discovery_architecture_ab_artifact.py `
  --baseline-candidates output\discovery_architecture_ab\a_incremental\one_raw_tumorbc2312\discovery_candidates.csv `
  --candidate-candidates output\discovery_architecture_ab\b_feature_primary\one_raw_tumorbc2312\discovery_candidates.csv `
  --focus-sample TumorBC2312_DNA `
  --focus-precursor-mz 300.1605 `
  --focus-product-mz 184.113 `
  --preserve-precursor-mz 301.165 `
  --preserve-product-mz 185.116 `
  --preserve-tag DNA_dR `
  --summary-json output\discovery_architecture_ab\b_feature_primary\one_raw_tumorbc2312\architecture_ab_check.json `
  --check-only
```

Successor checker requirements:

- Verify the rescued focus pair as `300.1605 -> 184.113`.
- Verify the preserved isotope/tag pair as `301.165 -> 185.116`, not merely any
  row with product `185.116`.
- Assert sample, tag/provenance, row-state, and MS1 feature/provenance identity
  for both pairs.
- If there is no manual EIC/MS2 inspection for a B output, label the result
  `diagnostic_only`.

### 8RAW Discovery/parser parity gate

Only run after focused tests and the one-RAW gate pass.

```powershell
.venv\Scripts\python.exe scripts\run_discovery.py `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation `
  --dll-dir C:\Xcalibur\system\programs `
  --output-dir output\discovery_architecture_ab\<variant>\8raw_discovery `
  --timing-output output\discovery_architecture_ab\<variant>\8raw_discovery\timing.json
```

Then run parser compatibility against the produced
`discovery_batch_index.csv`.

```powershell
.venv\Scripts\python.exe -c "from pathlib import Path; from xic_extractor.alignment.csv_io import read_discovery_batch_index, read_discovery_candidates_csv; batch=read_discovery_batch_index(Path(r'output\discovery_architecture_ab\<variant>\8raw_discovery\discovery_batch_index.csv')); [read_discovery_candidates_csv(path) for path in batch.candidate_csvs.values()]; print('discovery_parser_smoke_status: pass')"
```

The acceptance criteria are:

- batch index resolves all candidate/review CSV paths;
- candidate CSVs parse;
- duplicate row identity fails closed;
- row count delta is explained;
- no default matrix or Backfill authority is claimed.

Do not run 85RAW for this brief.

## No-Two-Systems Rule

If A is chosen:

- B remains design notes only.
- No feature flag or hidden B path is added.

If B is chosen:

- First implementation may use a temporary adapter only to compare outputs. It
  must not be exposed as a product runtime mode.
- Put temporary adapter code under a clearly named experimental comparison
  owner, not behind `scripts/run_discovery.py` CLI/config flags.
- The same phase must define the deletion/facade endpoint for the old internal
  path.
- If B does not beat A on the one-RAW oracle, the temporary adapter is deleted or
  left unmerged with design notes only.
- If B beats A, the same implementation plan must define how old internals
  become a thin facade or are deleted; do not keep both internal workflows.
- Product entry points expose one Discovery workflow.
- Old tests are either migrated to the new contract or kept only as fixture
  compatibility tests.

## Recommendation Before Implementation

Next decision: choose whether B deserves a short design spike. If yes, write the
successor expected-diff checker first, then build only enough temporary adapter
code to run the one-RAW comparison. If no, implement A directly. B should not
touch ProductWriter/default matrix/Backfill/GUI, and no replacement should
advance to 8RAW until the one-RAW comparison justifies it.

## Decision Spike v1 Result - 2026-06-20

Decision:

- Do not build the B temporary comparison adapter in this branch yet.
- Proceed with A incremental owner-deepening first: add explicit
  `discovery_candidate_state` and `ms1_feature_row_id` to the existing
  Discovery owner path, with writer/reader roundtrip and parser tests, before
  any B feature-primary adapter is allowed to claim a successor oracle pass.

Evidence:

- Added successor checker:
  `scripts/check_discovery_architecture_ab_artifact.py`.
- Focused checker tests passed:
  `python -m pytest tests\test_discovery_architecture_ab_artifact.py tests\test_discovery_precursor_inference_artifact.py -q`
  (`13 passed`).
- Focused ruff passed:
  `uv run ruff check scripts/check_discovery_architecture_ab_artifact.py tests/test_discovery_architecture_ab_artifact.py`.
- One-RAW A baseline ran successfully for `TumorBC2312_DNA` RT `22-25`:
  `output/discovery_architecture_ab/a_incremental/one_raw_tumorbc2312/`.
- Legacy precursor-inference checker passed that output with 157 rows and SHA256
  `E69C53CE5F054C3D6385A2A66BD1B85B9D0F567F91BBC7F5A78BAC7D73953C44`, confirming
  the current A path still recovers `300.1605 -> 184.113` and preserves
  `301.165 -> 185.116`.
- The successor checker intentionally fails the same A output because the
  current public Discovery CSV lacks `discovery_candidate_state` and
  `ms1_feature_row_id`. Its summary is
  `output/discovery_architecture_ab/a_incremental/one_raw_tumorbc2312/architecture_ab_check.json`;
  the alignment parser compatibility status is `pass`, row count is 157, and
  basis counts are 146 `product_plus_neutral_loss`, 6 `mixed`, and 5
  `scan_precursor`.

Interpretation:

- A already passes the legacy biology recall/provenance check for the named
  one-RAW case, so there is no current evidence that a B adapter would beat A on
  recall.
- A does not yet satisfy the successor row-state / MS1-row-identity contract.
  That is an A owner-deepening gap, not a reason to create a second Discovery
  system.
- B can be reopened only after the A successor contract exists and passes the
  one-RAW checker; any B adapter must remain temporary, outside
  `scripts/run_discovery.py` flags/config, and must be deleted or left unmerged
  if it does not materially beat A on the same oracle.

Validation label:

- Current evidence is `diagnostic_only`.
- No ProductWriter/default matrix/workbook/GUI/Backfill authority changed.
- No control-plane maturity tier or active lane update is required for this
  checker/decision spike.

## A Owner-Deepening Result - 2026-06-20

Decision:

- Keep the A owner-deepening path.
- Do not build or merge the B feature-primary temporary adapter.
- Do not run 8RAW for this decision: focused tests plus the one-RAW oracle now
  answer the architecture question.

Implementation:

- Added additive `discovery_candidates.csv` fields:
  `discovery_candidate_state` and `ms1_feature_row_id`.
- `discovery.models` owns state vocabulary and row-id construction.
- `DiscoveryCandidate.from_values` assigns state/id before the writer.
- `discovery.csv_writer` remains render-only.
- `alignment.csv_io` parses successor fields, rejects invalid state/identity
  combinations, validates `ms1_feature_row_id` sample/tag/precursor/RT identity,
  and still reads legacy candidate CSVs that predate the additive successor
  columns.
- No `scripts/run_discovery.py` CLI/config flag or B adapter was added.

Focused verification:

- `python -m pytest tests/test_discovery_csv.py tests/test_alignment_csv_io.py tests/test_discovery_architecture_ab_artifact.py tests/test_discovery_ms1_backfill.py tests/test_discovery_precursor_inference_artifact.py -q`
  passed: `92 passed`.
- `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor/discovery/models.py xic_extractor/discovery/ms1_backfill.py xic_extractor/alignment/csv_io.py tests/test_discovery_csv.py tests/test_alignment_csv_io.py tests/test_discovery_architecture_ab_artifact.py tests/alignment_pipeline_helpers.py tests/test_shared_peak_identity_candidate_ms2_pattern.py`
  passed.
- `python scripts/check_productization_state.py` passed.

One-RAW oracle:

- Reran `TumorBC2312_DNA.raw` RT `22-25` into
  `output/discovery_architecture_ab/a_incremental/one_raw_tumorbc2312/`.
- Legacy precursor-inference checker passed with 157 rows and SHA256
  `5267A602D520FAE4F3B11E2CDB99525849D7FD2C01F33ACC37F6D4548194114D`.
- Successor architecture checker passed with readiness label `diagnostic_only`;
  alignment parser status was `pass`.
- Basis counts: 146 `product_plus_neutral_loss`, 6 `mixed`, 5
  `scan_precursor`.
- State counts: 46 `ms1_feature_nl_rescued`, 5
  `ms1_feature_nl_supported`, 106 `review_only_orphan_nl`.

Named facts:

- `300.1605 -> 184.113` recovered as
  `TumorBC2312_DNA#19561@mz300.160635_p184.113235`, state
  `ms1_feature_nl_rescued`, row identity
  `TumorBC2312_DNA|DNA_dR|300.160635|23.341692`, basis
  `product_plus_neutral_loss`, tag `DNA_dR`.
- `301.165 -> 185.116` preserved as its own `DNA_dR` tag-evidence row:
  `TumorBC2312_DNA#19561@mz301.164978_p185.115845`, state
  `ms1_feature_nl_rescued`, row identity
  `TumorBC2312_DNA|DNA_dR|301.164978|23.341692`, basis `mixed`.
- The two named rows have distinct `ms1_feature_row_id` values, so preserving
  `301.165 -> 185.116` does not depend on demoting/deleting it or treating
  candidates as matrix rows.

Interpretation:

- A now satisfies the successor state/row-identity contract for the bounded
  one-RAW oracle.
- B remains closed because it has no demonstrated material one-RAW advantage
  over A, and maintaining two Discovery systems would add product risk without
  decision value.
- Evidence remains `diagnostic_only`; no ProductWriter/default
  matrix/workbook/GUI/Backfill authority changed.
- No productization control-plane update is required because no maturity tier,
  active lane, ProductWriter/default matrix activation, selected area/counting,
  or Backfill writer authority changed.
