# Shared Peak Identity Slice 1 Blast Radius Implementation Plan

> **For Claude:** Use `${SUPERPOWERS_SKILLS_ROOT}/skills/collaboration/executing-plans/SKILL.md` to implement this plan task-by-task.

**Goal:** Add a Slice 1 `diagnostic_only` blast-radius / overfit assessment that uses the Slice 0 explanation output plus existing 8RAW / 85RAW alignment artifacts to report whether the explanation vocabulary generalizes beyond the seven seed families.

**Architecture:** Keep the existing `shared_peak_identity_explanation` diagnostic package as the owner. Add Slice 1 schema constants, artifact manifest generation, streaming blast-radius summarization, report sections, and CLI flags without changing selected peaks, backfill rescue, Tier 2 support, workbook output, `alignment_matrix.tsv`, or downstream contracts. Slice 1 summarizes machine-side generalization and artifact coverage; it does not create non-seed manual labels or a production gate.

**Tech Stack:** Python stdlib `csv`, `hashlib`, `pathlib`, existing `tools.diagnostics.diagnostic_io.write_tsv`, `uv run ruff`, `uv run pytest`.

**Acceptance Type:** Diagnostic. Success is internal consistency, traceability, reviewer readability, and mechanically checkable raw facts, not numerical production readiness.

**Readiness Label:** `diagnostic_only`

**Public Contract:** Extend the diagnostic CLI `tools/diagnostics/shared_peak_identity_explanation.py` with opt-in Slice 1 blast-radius flags. Add Slice 1 constants for `shared_peak_identity_blast_radius_manifest.tsv` and `shared_peak_identity_blast_radius_summary.tsv`; keep the full schema in `docs/superpowers/specs/2026-05-29-shared-peak-identity-evidence-explanation-pilot-design.md`.

---

## Context To Read First

- `AGENTS.md`
- `docs/agent-parameter-settings.md`
- `docs/agent-subagent-routing.md`
- `tools/diagnostics/INDEX.md`
- `docs/diagnostic-ledger.md`
- `docs/superpowers/specs/2026-05-29-shared-peak-identity-evidence-explanation-pilot-design.md`
- `docs/superpowers/plans/2026-05-29-shared-peak-identity-slice0-implementation-plan.md`
- `output/shared_peak_identity_evidence_explanation/shared_peak_identity_run_facts.tsv`
- `output/shared_peak_identity_evidence_explanation/shared_peak_identity_explanations.tsv`
- `output/shared_peak_identity_evidence_explanation/shared_peak_identity_evidence_vectors.tsv`

## Current Slice 0 Decision Facts

Slice 0 is allowed to proceed to Slice 1 because the current run facts show:

```text
slice=slice0
seed_rows_total=39
seed_rows_explained=39
seed_rows_unexplained=0
seed_rows_inconclusive=0
vocabulary_special_casing_detected=FALSE
blast_radius_assessed=not_run_slice0
max_overfit_risk=unassessed
```

Current explanation class counts:

```text
delta_mass_related_context_only=1
human_unjudgeable_shape_bad=8
machine_too_conservative_low_opportunity=6
machine_too_conservative_shape_or_pattern_unmodeled=19
machine_too_permissive_rt_pattern_conflict=1
machine_too_permissive_scope_rule_conflict=3
rt_drift_policy_gap=2
```

## Critical Design Constraint

Non-seed 8RAW / 85RAW rows do not have manual oracle labels. Slice 1 must therefore report machine-side compatibility, artifact coverage, missing fields, and overfit risk. It must not assert that a non-seed row is truly `pass`, `fail`, or manually contradicted.

Use the spec's Slice 1 row-grain and risk contract:

- `sample_seed_rows`: Slice 0 explanation rows where `manual_label != not_applicable` and `sample_id` is not a reserved sentinel.
- `context_rows`: sentinel rows such as `sample_id=__family_context__`; these may appear in the report but never participate in `seed_count`, `non_seed_same_family_count`, `all_available_row_count`, `compatible_row_count`, contradiction counts, ambiguity counts, or risk denominators.
- `all_available_row_count`: machine-row denominator for the current scope whose required fields are available for the class profile.
- `compatible_row_count`: subset of the denominator whose machine-side profile is compatible with the class.
- `contradictory_count`: machine-side contradiction only; this is not a manual-label contradiction.
- `ambiguous_machine_match_count`: ambiguous machine evidence such as `ambiguous_multiple_matches`, `ambiguous_ms1_owner`, or duplicated sample/family rows that make profile matching non-unique.
- `overfit_risk`: deterministic raw diagnostic risk from the spec's threshold table, not a gate verdict.

The current Slice 0 output has 39 sample-level seed rows and one context row:
`FAM001227|__family_context__`. Slice 1 must keep that context row out of all
sample-level blast-radius numerator and denominator fields.

## Freshness And Exit Rule

`present_current` requires an expected-hash authority. The implementation must
not infer freshness from path existence alone.

Expected hashes come from:

- Slice 0 `shared_peak_identity_evidence_vectors.tsv` for artifacts already used by Slice 0;
- a role-bearing expected manifest passed to Slice 1 for 85RAW artifacts and optional sidecars not present in Slice 0 evidence vectors.

If an artifact is present but has no expected hash, its manifest row is
`artifact_status=present_hash_unpinned`. It can contribute coverage facts, but
the run-level `blast_radius_assessed` cannot be `present_current`.

Slice 1 exit interpretation:

- `max_overfit_risk=high`: kill or revise the vocabulary before V2 shadow-label-alignment planning.
- `max_overfit_risk=medium`, `blast_radius_assessed != present_current`, stale required artifacts, or missing-field dominance: externalize the missing evidence and do not start V2 gate work from this run.
- `max_overfit_risk=low` with current 8RAW+85RAW manifests, zero stale required artifacts, and no sentinel leakage into sample-level counts: V2 may evaluate shadow label alignment. This remains `diagnostic_only`, not production promotion.

## Inputs

Required existing artifacts:

```text
docs/superpowers/fixtures/shared_peak_identity_manual_oracle_v1.tsv
output/shared_peak_identity_evidence_explanation/shared_peak_identity_explanations.tsv
output/shared_peak_identity_evidence_explanation/shared_peak_identity_evidence_vectors.tsv
output/shared_peak_identity_evidence_explanation/shared_peak_identity_run_facts.tsv
output/tiered_backfill_candidate_gate_8raw_current/alignment_review.tsv
output/tiered_backfill_candidate_gate_8raw_current/alignment_cells.tsv
output/tiered_backfill_candidate_gate_85raw_current/alignment_review.tsv
output/tiered_backfill_candidate_gate_85raw_current/alignment_cells.tsv
```

Optional context artifacts:

```text
candidate_gate_8raw=output/tiered_backfill_candidate_gate_8raw_current/alignment_production_candidate_gate.tsv
candidate_gate_85raw=output/tiered_backfill_candidate_gate_85raw_current/alignment_production_candidate_gate.tsv
tier2_coherence_8raw=output/tier2_v0_1_coherence_8raw_current_gate/alignment_production_candidate_gate.tsv
```

Optional artifacts must be role-bearing `ROLE=PATH` inputs. Allowed roles are
`candidate_gate_8raw`, `candidate_gate_85raw`, `tier2_trace_8raw`,
`tier2_coherence_8raw`, and `identity_diagnostic_context`. These inputs may
affect manifest/context coverage only; they must not increase sample-level
positive or compatible counts.

Optional expected-hash baseline:

```text
--expected-blast-radius-manifest <path-to-prior-manifest.tsv>
```

Without an expected manifest, 85RAW artifacts can be processed but are
`present_hash_unpinned`; the run may be useful but remains inconclusive for
`present_current` readiness facts.

## Output

Use a new pilot output directory so Slice 0 artifacts remain inspectable:

```text
output/shared_peak_identity_evidence_explanation_slice1/
```

Expected files:

```text
shared_peak_identity_manual_oracle.tsv
shared_peak_identity_evidence_vectors.tsv
shared_peak_identity_explanations.tsv
shared_peak_identity_run_facts.tsv
shared_peak_identity_explanation_report.md
shared_peak_identity_blast_radius_manifest.tsv
shared_peak_identity_blast_radius_summary.tsv
```

## Not In Scope

- No RAW scan or RAW re-read.
- No new manual oracle for non-seed rows.
- No production promotion, product label alignment, workbook mutation, or matrix mutation.
- No baseline / AsLS work.
- No use of `analyze_matrix_identity_blast_radius.py` output schema as the Slice 1 schema. That tool answers matrix-promotion impact, not explanation-vocabulary overfit.

## Stop Conditions

Stop before implementation if:

- Slice 0 run facts no longer satisfy `seed_rows_explained=seed_rows_total`, `seed_rows_unexplained=0`, `seed_rows_inconclusive=0`, and `vocabulary_special_casing_detected=FALSE`.
- The active spec cannot distinguish machine-side blast-radius facts from semantic manual truth.
- Existing artifacts cannot identify `feature_family_id`, sample IDs, row status, or source artifact identity.
- The plan/spec cannot identify sample-level seed rows separately from sentinel/context rows.
- `overfit_risk` thresholds or exit rules are absent.

Stop during implementation if:

- The 85RAW cell file requires full in-memory loading to complete.
- The manifest cannot record SHA256, row count, sample count, family count, and missing fields for each required artifact.
- `present_current` would be emitted without an expected-hash authority.
- optional context artifacts affect sample-level compatible or positive counts.
- Any Slice 1 report language implies `production_ready`, V1 gating verdict, or human pass/fail labels for non-seed rows.

## Task 0: Blocking Preflight Contract And Sampled 85RAW Smoke

**Files:**

- Modify: `docs/superpowers/specs/2026-05-29-shared-peak-identity-evidence-explanation-pilot-design.md`
- Modify: `docs/superpowers/plans/2026-05-29-shared-peak-identity-slice1-blast-radius-plan.md`
- Test later: `tests/test_shared_peak_identity_blast_radius_preflight.py`

**Step 1: Verify Slice 0 row grain**

Before coding, confirm the current Slice 0 output has:

```text
sample_seed_rows=39
context_rows=1
context_row_ids=FAM001227|__family_context__
```

The plan and implementation must exclude context rows from sample-level
blast-radius counts and risk denominators.

**Step 2: Lock the deterministic risk table**

Use the spec's risk thresholds exactly. Do not let the implementation invent
different `high` / `medium` / `low` semantics.

The minimum denominator for risk closure is:

```text
assessed_row_count >= max(50, 5 * seed_count)
```

Low risk additionally requires:

```text
compatible_fraction >= 0.01
contradictory_fraction < 0.10
ambiguous_fraction < 0.20
unavailable_fraction < 0.20
```

If these facts cannot be computed, emit `overfit_risk=unassessed` or `medium`
according to the spec table; do not coerce to low.

**Step 3: Lock freshness authority**

Implementers must choose one:

- provide `--expected-blast-radius-manifest` for 85RAW and optional sidecar freshness; or
- accept `artifact_status=present_hash_unpinned` and `blast_radius_assessed != present_current`.

Do not mark a path-only artifact as `present_current`.

**Step 4: Add sampled smoke before full 85RAW**

Add a preflight mode before any full 85RAW pass:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python -m tools.diagnostics.shared_peak_identity_explanation `
  --enable-blast-radius `
  --blast-radius-preflight-only `
  --blast-radius-sample-row-limit 1000 `
  --blast-radius-8raw-run output\tiered_backfill_candidate_gate_8raw_current `
  --blast-radius-85raw-run output\tiered_backfill_candidate_gate_85raw_current `
  --output-dir output\shared_peak_identity_evidence_explanation_slice1_preflight
```

Expected:

- reads headers plus at most 1000 data rows per large cell file;
- validates required fields and status handling;
- prints or returns sampled row/sample/family counts;
- does not write durable Slice 1 manifest or summary files.

**Step 5: Add a streaming sentinel test**

The preflight/summarizer tests must include an iterator or file-like sentinel
that fails if the implementation materializes the full reader with `list(reader)`
or otherwise consumes beyond the requested sample limit.

## Task 1: Spec Addendum And Schema Constants

**Files:**

- Modify: `docs/superpowers/specs/2026-05-29-shared-peak-identity-evidence-explanation-pilot-design.md`
- Modify: `xic_extractor/alignment/shared_peak_identity_explanation/schema.py`
- Test: `tests/test_shared_peak_identity_schema.py`

**Step 1: Write failing schema tests**

Add tests asserting:

- manifest columns match the spec's `shared_peak_identity_blast_radius_manifest.tsv`;
- summary columns match the spec's `shared_peak_identity_blast_radius_summary.tsv`;
- manifest columns include `expected_artifact_sha256` and `freshness_basis`;
- summary columns include `context_row_count`, `assessed_row_count`, `compatible_row_count`, and fraction fields;
- allowed `artifact_status` values include `present_current`, `present_hash_unpinned`, `present_missing_required_fields`, `missing`, and `present_stale_hash_mismatch`;
- allowed `scope` values include `seed`, `non_seed_same_family`, `all_available_8raw`, `all_available_85raw`, and `overall`;
- allowed `overfit_risk` values are `none`, `low`, `medium`, `high`, `unassessed`;
- Slice 1 run facts allow `slice=slice1` and `blast_radius_assessed=present_current`.

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_shared_peak_identity_schema.py -q
```

Expected: fail because Slice 1 constants do not exist.

**Step 2: Implement constants and validation**

Add:

```python
BLAST_RADIUS_MANIFEST_SCHEMA_VERSION = "shared_peak_identity_blast_radius_manifest_v1"
BLAST_RADIUS_SUMMARY_SCHEMA_VERSION = "shared_peak_identity_blast_radius_summary_v1"
BLAST_RADIUS_MANIFEST_COLUMNS = (...)
BLAST_RADIUS_SUMMARY_COLUMNS = (...)
```

Extend `ALLOWED_BY_FIELD` for `artifact_status`, `scope`, `artifact_role`, `freshness_basis`, and `overfit_risk`. Do not duplicate the full schema in additional docs.

**Step 3: Re-run schema tests**

Expected: pass.

## Task 2: Streaming Artifact Manifest Builder

**Files:**

- Create: `xic_extractor/alignment/shared_peak_identity_explanation/blast_radius.py`
- Test: `tests/test_shared_peak_identity_blast_radius_manifest.py`

**Step 1: Write failing manifest tests**

Use small temp TSVs and assert:

- SHA256 is uppercase and stable;
- row count excludes the header;
- sample count uses `sample_stem` when present;
- family count uses `feature_family_id`;
- missing required fields are listed in `missing_required_fields`;
- `artifact_status=present_missing_required_fields` when required fields are absent;
- `artifact_status=present_current` only when an expected hash exists and matches;
- `artifact_status=present_stale_hash_mismatch` when an expected hash exists and does not match;
- `artifact_status=present_hash_unpinned` when the artifact exists but has no expected hash authority;
- missing optional artifact paths emit `artifact_status=missing` without crashing.

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_shared_peak_identity_blast_radius_manifest.py -q
```

Expected: fail.

**Step 2: Implement streaming inspection**

Implement signatures:

```python
def build_blast_radius_manifest(
    *,
    manual_oracle_tsv: Path,
    slice0_explanations_tsv: Path,
    slice0_evidence_vectors_tsv: Path,
    eight_raw_run_dir: Path,
    eightyfive_raw_run_dir: Path,
    expected_manifest_tsv: Path | None = None,
    optional_artifacts: Mapping[str, Path] | None = None,
) -> tuple[dict[str, str], ...]:
    ...
```

Implementation notes:

- Use `csv.DictReader` streaming; do not load the 85RAW cell file into memory.
- Build expected hashes from Slice 0 evidence vectors first, then override or extend with `expected_manifest_tsv` when provided.
- Required 85RAW artifacts with no expected hash are `present_hash_unpinned`; they are not `present_current`.
- Required artifact IDs:
  - `manual_oracle_fixture`
  - `slice0_explanations`
  - `slice0_evidence_vectors`
  - `8raw_alignment_review`
  - `8raw_alignment_cells`
  - `85raw_alignment_review`
  - `85raw_alignment_cells`
- Required fields:
  - review: `feature_family_id`, `identity_decision`, `identity_reason`, `row_flags`
  - cells: `feature_family_id`, `sample_stem`, `status`, `apex_rt`, `peak_start_rt`, `peak_end_rt`, `rt_delta_sec`, `trace_quality`, `scan_support_score`, `reason`
- Optional artifacts must be role-bearing. Reject unknown roles rather than silently accepting path-only context.
- `generated_from_existing_artifact=TRUE` for all manifest rows in this phase.

**Step 3: Re-run manifest tests**

Expected: pass.

## Task 3: Slice 0 Class Profiles

**Files:**

- Modify: `xic_extractor/alignment/shared_peak_identity_explanation/blast_radius.py`
- Test: `tests/test_shared_peak_identity_blast_radius_profiles.py`

**Step 1: Write failing profile tests**

Create tiny Slice 0 explanation/evidence fixtures and assert profile construction returns:

- seed row IDs per `evidence_gap_class`;
- context row IDs per `evidence_gap_class`, kept out of sample-level profiles;
- seed families per class;
- seed sample keys per class;
- machine-side prerequisites per class, such as positive machine cell, absent machine cell, ambiguous machine match, RT/pattern conflict, or scope-rule conflict;
- manual-side prerequisites marked separately so non-seed rows do not become manual truth.

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_shared_peak_identity_blast_radius_profiles.py -q
```

Expected: fail.

**Step 2: Implement profile builder**

Implement:

```python
def build_class_profiles(
    explanations: Sequence[Mapping[str, str]],
    evidence_vectors: Sequence[Mapping[str, str]],
) -> dict[str, BlastRadiusClassProfile]:
    ...
```

Use a small frozen dataclass for `BlastRadiusClassProfile`. Keep it internal to the diagnostic package unless tests need to import it.

**Step 3: Re-run profile tests**

Expected: pass.

## Task 4: Streaming Blast-Radius Summary

**Files:**

- Modify: `xic_extractor/alignment/shared_peak_identity_explanation/blast_radius.py`
- Test: `tests/test_shared_peak_identity_blast_radius_summary.py`

**Step 1: Write failing summary tests**

Use small 8RAW and 85RAW temp runs. Cover:

- `seed` scope counts exactly the sample-level Slice 0 explanation rows;
- `seed_count` excludes sentinel/context rows and `context_row_count` captures them separately;
- `non_seed_same_family` excludes exact oracle row keys but includes other rows from seed families;
- `all_available_8raw` and `all_available_85raw` are computed separately;
- `assessed_row_count`, `compatible_row_count`, and fraction fields are emitted for every sample-level class/scope row;
- missing columns increase `unavailable_field_count`;
- `ambiguous_ms1_owner` and duplicate sample/family machine rows increase `ambiguous_machine_match_count`;
- `overfit_risk=high` follows the spec table: sufficient denominator, no compatible rows, low unavailable/ambiguous fractions, or high contradiction fraction;
- `overfit_risk=medium` follows the spec table for weak/noisy denominator, low compatible fraction, contradiction, ambiguity, or unavailable dominance;
- `overfit_risk=low` follows the spec table and requires current 8RAW+85RAW surfaces plus sufficient compatible broader-scope evidence.

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_shared_peak_identity_blast_radius_summary.py -q
```

Expected: fail.

**Step 2: Implement summarizer**

Implement:

```python
def build_blast_radius_summary(
    *,
    class_profiles: Mapping[str, BlastRadiusClassProfile],
    manifest_rows: Sequence[Mapping[str, str]],
    eight_raw_run_dir: Path,
    eightyfive_raw_run_dir: Path,
) -> tuple[dict[str, str], ...]:
    ...
```

Rules:

- Stream `alignment_cells.tsv`; do not load 85RAW cells into memory.
- Use review rows for family-level machine context only.
- Do not classify non-seed rows as manual pass/fail.
- Do not let context-only classes such as `delta_mass_related_context_only` create sample-level risk denominators.
- Treat candidate gates and Tier 2 sidecars as optional context; do not count them as sample-level positive evidence.
- Keep `contradictory_count` wording machine-side in code comments and report text.

**Step 3: Re-run summary tests**

Expected: pass.

## Task 5: Slice 1 Run Facts And Report Sections

**Files:**

- Modify: `xic_extractor/alignment/shared_peak_identity_explanation/classifier.py`
- Modify: `xic_extractor/alignment/shared_peak_identity_explanation/writers.py`
- Test: `tests/test_shared_peak_identity_blast_radius_writers.py`

**Step 1: Write failing writer tests**

Assert that Slice 1 writes:

- `shared_peak_identity_blast_radius_manifest.tsv`;
- `shared_peak_identity_blast_radius_summary.tsv`;
- `shared_peak_identity_run_facts.tsv` with `slice=slice1`;
- `blast_radius_assessed=present_current` only when 8RAW and 85RAW manifest rows are present, expected-hash pinned, hash-matched, and not missing required fields;
- `blast_radius_assessed=85raw_not_assessed` when 85RAW is missing or lacks required fields;
- `blast_radius_assessed=not_assessed` when required artifacts are present but hash-unpinned;
- `blast_radius_stale_artifact_count` equals the number of stale manifest rows;
- `max_overfit_risk` is the maximum severity in the summary;
- context-only rows are reported separately and do not affect `max_overfit_risk`.

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_shared_peak_identity_blast_radius_writers.py -q
```

Expected: fail.

**Step 2: Implement writer extension**

Add an opt-in writer function:

```python
def write_slice1_outputs(
    *,
    output_dir: Path,
    slice0_outputs: Slice0OutputPaths,
    manifest_rows: Sequence[Mapping[str, str]],
    summary_rows: Sequence[Mapping[str, str]],
    run_facts: Mapping[str, str],
) -> dict[str, Path]:
    ...
```

Keep `write_slice0_outputs` unchanged for default behavior. Report must include:

- Slice 1 `diagnostic_only` decision summary;
- manifest status, stale count, and missing-field count;
- freshness basis, including unpinned artifacts that block `present_current`;
- summary by `evidence_gap_class` and `scope`;
- context-only row section for sentinel rows such as `FAM001227|__family_context__`;
- separate machine-too-conservative and machine-too-permissive sections;
- Slice 1 exit interpretation: revise/kill, externalize missing evidence, or allow V2 shadow-label-alignment planning;
- explicit wording that non-seed rows are machine-side blast-radius context, not manual labels.

**Step 3: Re-run writer tests**

Expected: pass.

## Task 6: CLI Integration

**Files:**

- Modify: `tools/diagnostics/shared_peak_identity_explanation.py`
- Test: `tests/test_shared_peak_identity_cli.py`

**Step 1: Write failing CLI tests**

Add tests for:

- default invocation still emits Slice 0 only and no Slice 1 files;
- `--enable-blast-radius` requires both `--blast-radius-8raw-run` and `--blast-radius-85raw-run`;
- `--blast-radius-preflight-only` samples headers plus a bounded number of rows and writes no durable Slice 1 outputs;
- `--expected-blast-radius-manifest` controls whether required 85RAW artifacts can be `present_current`;
- `--optional-blast-radius-artifact` requires `ROLE=PATH` and rejects unknown roles;
- optional candidate/Tier 2 sidecars affect manifest/context rows only and do not increase sample-level compatible counts;
- Slice 1 invocation emits manifest and summary files;
- report wording may deny production readiness, but no output may claim production readiness.

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_shared_peak_identity_cli.py -q
```

Expected: fail.

**Step 2: Implement flags**

Add:

```text
--enable-blast-radius
--blast-radius-preflight-only
--blast-radius-sample-row-limit
--blast-radius-8raw-run
--blast-radius-85raw-run
--expected-blast-radius-manifest
--optional-blast-radius-artifact ROLE=PATH
```

Suggested real command:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python -m tools.diagnostics.shared_peak_identity_explanation `
  --manual-oracle-tsv docs\superpowers\fixtures\shared_peak_identity_manual_oracle_v1.tsv `
  --alignment-review-tsv output\tiered_backfill_candidate_gate_8raw_current\alignment_review.tsv `
  --alignment-cells-tsv output\tiered_backfill_candidate_gate_8raw_current\alignment_cells.tsv `
  --candidate-gate-tsv output\tier2_v0_1_coherence_8raw_current_gate\alignment_production_candidate_gate.tsv `
  --enable-blast-radius `
  --blast-radius-8raw-run output\tiered_backfill_candidate_gate_8raw_current `
  --blast-radius-85raw-run output\tiered_backfill_candidate_gate_85raw_current `
  --optional-blast-radius-artifact candidate_gate_8raw=output\tiered_backfill_candidate_gate_8raw_current\alignment_production_candidate_gate.tsv `
  --optional-blast-radius-artifact candidate_gate_85raw=output\tiered_backfill_candidate_gate_85raw_current\alignment_production_candidate_gate.tsv `
  --output-dir output\shared_peak_identity_evidence_explanation_slice1
```

Without `--expected-blast-radius-manifest`, this command may compute coverage
and overfit facts but must not report `blast_radius_assessed=present_current` for
unpinned 85RAW artifacts.

**Step 3: Re-run CLI tests**

Expected: pass.

## Task 7: Diagnostic Index And Handoff Notes

**Files:**

- Modify: `tools/diagnostics/INDEX.md`
- Modify or create: `docs/superpowers/notes/2026-05-29-shared-peak-identity-slice1-blast-radius-note.md`

**Step 1: Update index**

Update the `shared_peak_identity_explanation.py` entry to state:

- default mode emits Slice 0 outputs only;
- `--enable-blast-radius` emits Slice 1 manifest and summary;
- still no RAW scan, matrix mutation, workbook mutation, or production readiness claim.

**Step 2: Write note**

Record:

- input artifact paths;
- Slice 0 run facts used as the go/no-go for planning;
- preflight sample row limit and sampled counts;
- exact real CLI command;
- output file paths;
- whether 85RAW was assessed or not assessed;
- whether required 85RAW artifacts were expected-hash pinned or `present_hash_unpinned`;
- maximum overfit risk;
- next recommended action from the exit rule.

## Task 8: Focused Verification

**Files:** no source edits unless failures require root-cause fixes.

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\shared_peak_identity_explanation tools\diagnostics\shared_peak_identity_explanation.py tests\test_shared_peak_identity_oracle.py tests\test_shared_peak_identity_schema.py tests\test_shared_peak_identity_loaders.py tests\test_shared_peak_identity_assembler.py tests\test_shared_peak_identity_classifier.py tests\test_shared_peak_identity_cli.py tests\test_shared_peak_identity_blast_radius_preflight.py tests\test_shared_peak_identity_blast_radius_manifest.py tests\test_shared_peak_identity_blast_radius_profiles.py tests\test_shared_peak_identity_blast_radius_summary.py tests\test_shared_peak_identity_blast_radius_writers.py
```

Expected: pass.

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_shared_peak_identity_oracle.py tests\test_shared_peak_identity_schema.py tests\test_shared_peak_identity_loaders.py tests\test_shared_peak_identity_assembler.py tests\test_shared_peak_identity_classifier.py tests\test_shared_peak_identity_cli.py tests\test_shared_peak_identity_blast_radius_preflight.py tests\test_shared_peak_identity_blast_radius_manifest.py tests\test_shared_peak_identity_blast_radius_profiles.py tests\test_shared_peak_identity_blast_radius_summary.py tests\test_shared_peak_identity_blast_radius_writers.py -q
```

Expected: pass.

Run the sampled 85RAW preflight command from Task 0.

Expected:

- command exits 0;
- sampled counts are printed or returned;
- no durable Slice 1 manifest or summary is written;
- row consumption is bounded by `--blast-radius-sample-row-limit`.

Run the real CLI command from Task 6 only after the sampled preflight passes.

Expected:

- `shared_peak_identity_blast_radius_manifest.tsv` exists;
- `shared_peak_identity_blast_radius_summary.tsv` exists;
- run facts show `slice=slice1`;
- `blast_radius_assessed=present_current` only when both 8RAW and 85RAW surfaces are expected-hash pinned and current; otherwise the precise not-assessed/unpinned status is recorded;
- `max_overfit_risk` follows the spec table and is not coerced to low when denominators, freshness, or fields are inadequate;
- context-only rows do not appear in sample-level denominator fields;
- report remains `diagnostic_only` and contains no `production_ready` or V1 gating verdict.

Run:

```powershell
git diff --check
```

Expected: no whitespace errors.

## Task 9: Review Gate

Use repo routing from `docs/agent-subagent-routing.md`.

Minimum review angles:

- implementation-contract reviewer: confirm non-seed rows are not treated as manual truth and manifest/summary schemas match the spec;
- validation-evidence reviewer with `mode=preflight`: confirm sampled 85RAW smoke, streaming guard, freshness status, and not-assessed paths are credible before any full pass;
- tester: rerun focused gates and real CLI command, then report final `git status --short`.

Fix any blockers before considering the Slice 1 plan done.

## Acceptance Checklist

- Slice 0 remains reproducible and default CLI behavior remains Slice 0 only.
- Slice 1 emits manifest and summary only when explicitly enabled.
- 8RAW and 85RAW artifacts are read from existing files; no RAW scan occurs.
- A sampled 85RAW preflight passes before the full 85RAW pass.
- 85RAW `alignment_cells.tsv` is processed streaming, with a regression test that fails on full materialization.
- Manifest records artifact paths, observed SHA256 values, expected SHA256 values when available, freshness basis, row/sample/family counts, required-field availability, and missing fields.
- Required 85RAW artifacts without expected hashes are `present_hash_unpinned`, not `present_current`.
- Optional sidecars are role-bearing and never increase sample-level compatible/positive counts.
- Summary reports `seed_count`, `context_row_count`, `non_seed_same_family_count`, `assessed_row_count`, `all_available_row_count`, `compatible_row_count`, `unavailable_field_count`, `contradictory_count`, `ambiguous_machine_match_count`, fraction fields, and `overfit_risk` by `evidence_gap_class` and `scope`.
- Sentinel/context rows do not participate in sample-level risk denominators.
- Run facts record `slice=slice1`, `blast_radius_assessed`, `blast_radius_stale_artifact_count`, and `max_overfit_risk`.
- Exit rule is explicit: high revises/kills vocabulary; medium/not-current externalizes missing evidence; low/current allows only V2 shadow-label-alignment planning.
- Report separates machine-too-conservative and machine-too-permissive classes and states that Slice 1 is `diagnostic_only`.
- No production behavior or public downstream workbook/matrix contract changes.
