# Shared Peak Identity Slice 0 Implementation Plan

> **For Claude:** Use `${SUPERPOWERS_SKILLS_ROOT}/skills/collaboration/executing-plans/SKILL.md` to implement this plan task-by-task.

**Goal:** Build the Slice 0 shared peak identity explanation pilot so the seven-family manual oracle can be represented as machine-readable evidence vectors, explanations, run facts, and a compact report without changing production behavior.

**Architecture:** Hand-author the durable manual oracle first, then add a focused `xic_extractor.alignment.shared_peak_identity_explanation` diagnostic package for schema constants, loading, assembling, classification, and writing. Keep `tools/diagnostics/shared_peak_identity_explanation.py` as a thin CLI facade over existing alignment and Tier 2 sidecar artifacts; no RAW scanning, no matrix mutation, and no Slice 1 blast-radius outputs.

**Tech Stack:** Python 3, `csv`, `hashlib`, `dataclasses`, `pathlib`, existing `tools.diagnostics.diagnostic_io`, pytest, ruff, mypy-compatible type hints.

**Acceptance Type:** Diagnostic. Success means internal consistency, readable explanations, token-domain closure, and the seven seed families covered without family-specific exceptions; no numerical production gate applies.

**Readiness Label:** `diagnostic_only`

**Public Contract:** New diagnostic CLI `tools/diagnostics/shared_peak_identity_explanation.py`; new package `xic_extractor/alignment/shared_peak_identity_explanation/`; durable fixture `docs/superpowers/fixtures/shared_peak_identity_manual_oracle_v1.tsv`; output directory `output/shared_peak_identity_evidence_explanation/`. Output schemas and enum domains are owned by `docs/superpowers/specs/2026-05-29-shared-peak-identity-evidence-explanation-pilot-design.md`; this plan references that spec instead of duplicating long schema lists.

---

## Preconditions And Scope

Read before coding:

- `AGENTS.md`
- `docs/agent-subagent-routing.md`
- `docs/agent-parameter-settings.md`
- `tools/diagnostics/INDEX.md`
- `docs/superpowers/specs/2026-05-29-shared-peak-identity-evidence-explanation-pilot-design.md`
- `docs/superpowers/notes/2026-05-29-shared-peak-identity-context7-package-audit.md`

Current reusable machine artifacts for Slice 0 acceptance:

- `output/tiered_backfill_candidate_gate_8raw_current/alignment_review.tsv`
- `output/tiered_backfill_candidate_gate_8raw_current/alignment_cells.tsv`
- `output/tier2_v0_1_coherence_8raw_current_gate/alignment_production_candidate_gate.tsv`

Do not implement now:

- Slice 1 blast-radius manifest or summary.
- V2 shadow label convergence.
- RAW re-read, 8RAW rerun, 85RAW rerun, CWT ridge tracking, AsLS/baseline work.
- Changes to `alignment_matrix.tsv`, workbook schemas, selected peak scoring, backfill rescue decisions, or Tier 2 support-token derivation.

Stop if:

- The oracle cannot encode the manual review without ambiguous sample scope.
- Existing machine artifacts cannot identify machine labels/blockers for a reviewed seed row.
- Multiple machine rows match one oracle row and the implementation cannot preserve `ambiguous_multiple_matches`.
- Any proposed classifier rule becomes family-specific instead of evidence-fact based.
- Slice 0 would need RAW access to explain the seed cases.
- The reviewed sample list for an `all reviewed cells` family cannot be named
  without inferring it from machine-artifact availability.

Commit is user-gated. Do not include `git add` or `git commit` in task steps.

## Task 1: Durable Manual Oracle Fixture

**Files:**

- Create: `docs/superpowers/fixtures/shared_peak_identity_manual_oracle_v1.tsv`
- Test: `tests/test_shared_peak_identity_oracle.py`

**Step 1: Write the failing oracle fixture test**

Add a test that loads the fixture with `csv.DictReader(delimiter="\t")` and asserts:

- required columns match the spec's Slice 0 oracle schema;
- `oracle_schema_version` is one stable value for all rows;
- `oracle_row_id` is unique and equals `<feature_family_id>|<sample_id>`;
- required seed families are represented: `FAM000144`, `FAM000610`, `FAM001227`, `FAM001589`, `FAM001658`, `FAM002175`;
- `FAM000610` and `FAM002175` each contain exactly the named current 8RAW reviewed samples below; tests must not derive this scope from `alignment_cells.tsv`;
- the `FAM001227|__family_context__` row uses `manual_label=not_applicable`, `sample_id=__family_context__`, `related_family_id=FAM001239`, and does not become `human_unjudgeable`;
- the fixture contains at least one `pass`, `suspect`, `fail`, `human_unjudgeable`, and `not_applicable` manual label.

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_shared_peak_identity_oracle.py -q
```

Expected: fails because the fixture does not exist.

**Step 2: Author the TSV fixture**

Create the fixture from the user-reviewed cases in the spec. Use one row per directly reviewed cell, one context row for the `FAM001227` / `FAM001239` delta-mass relationship, and explicit scope-derived fail rows only where the reviewed scope makes the sample set known.

Important encoding decisions:

- `FAM000144`: direct rows for `NormalBC2312_DNA`, `BenignfatBC1151_DNA`, and the rejected `TumorBC2312_DNA` candidate.
- `FAM000610`: direct rows for the manually reviewed current 8RAW sample set: `BenignfatBC1055_DNA`, `BenignfatBC1151_DNA`, `Breast_Cancer_Tissue_pooled_QC3`, `Breast_Cancer_Tissue_pooled_QC5`, `NormalBC2263_DNA`, `NormalBC2312_DNA`, `TumorBC2263_DNA`, and `TumorBC2312_DNA`.
- `FAM001227`: direct rows for `Breast_Cancer_Tissue_pooled_QC5`, `NormalBC2263_DNA`, `TumorBC2312_DNA`, `NormalBC2312_DNA`, and `TumorBC2263_DNA`, plus scope-derived fail rows only for known reviewed-set unmentioned cells.
- `FAM001589`: at least one direct `human_unjudgeable` row, with `shape_bad;human_unjudgeable`.
- `FAM001658`: direct rows for `BenignfatBC1151_DNA`, `Breast_Cancer_Tissue_pooled_QC3`, `Breast_Cancer_Tissue_pooled_QC5`, and `NormalBC2312_DNA`.
- `FAM002175`: direct rows for the manually reviewed current 8RAW sample set: `BenignfatBC1055_DNA`, `BenignfatBC1151_DNA`, `Breast_Cancer_Tissue_pooled_QC3`, `Breast_Cancer_Tissue_pooled_QC5`, `NormalBC2263_DNA`, `NormalBC2312_DNA`, `TumorBC2263_DNA`, and `TumorBC2312_DNA`.

**Step 3: Re-run the oracle test**

Run the same pytest command.

Expected: pass.

## Task 2: Schema Constants And Token Closure

**Files:**

- Create: `xic_extractor/alignment/shared_peak_identity_explanation/__init__.py`
- Create: `xic_extractor/alignment/shared_peak_identity_explanation/schema.py`
- Test: `tests/test_shared_peak_identity_schema.py`

**Step 1: Write failing token-domain tests**

Add tests that import schema constants and assert:

- every controlled output column has an allowed-token set;
- semicolon-token fields reject embedded whitespace and unknown tokens;
- `matched_source_row_ids` is validated as dynamic provenance (`semicolon_source_row_id_list`), not as a controlled enum token list; every ID must point to an emitted evidence/source row;
- sentinel rows allow `manual_label=not_applicable`, `machine_current_label=not_applicable`, and `machine_match_status=not_applicable`;
- Slice 0 run facts require `slice=slice0`, `blast_radius_assessed=not_run_slice0`, and `max_overfit_risk=unassessed`.

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_shared_peak_identity_schema.py -q
```

Expected: fails because the package does not exist.

**Step 2: Implement schema constants and validators**

Implement:

- column tuples for the four Slice 0 outputs;
- allowed-value dictionaries for controlled fields;
- `validate_token(value, field)`;
- `validate_semicolon_tokens(value, field, allowed_tokens)`;
- `validate_row_tokens(row, allowed_by_field)`.

Do not paste the long schema into the plan or report. The constants are code-level contract tests that mirror the spec.

**Step 3: Re-run schema tests**

Run the same pytest command.

Expected: pass.

## Task 3: Oracle Loader And Machine Artifact Loader

**Files:**

- Create: `xic_extractor/alignment/shared_peak_identity_explanation/oracle.py`
- Create: `xic_extractor/alignment/shared_peak_identity_explanation/machine_artifacts.py`
- Test: `tests/test_shared_peak_identity_loaders.py`

**Step 1: Write failing loader tests**

Cover:

- durable oracle loading rejects missing required columns;
- duplicate `oracle_row_id` fails;
- sentinel rows never attempt machine joins;
- `sample_id` joins to machine `sample_stem`;
- an ambiguous duplicate machine row for one family/sample returns `machine_match_status=ambiguous_multiple_matches` and preserves all `source_row_id` values;
- missing machine rows return `machine_match_status=no_match`, not guessed labels;
- the optional candidate-gate sidecar is loaded only as family-level context (`candidate_gate_family_context`) and never as a sample-level Tier 2 RAW reread match.

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_shared_peak_identity_loaders.py -q
```

Expected: fails because loaders do not exist.

**Step 2: Implement loaders**

Use `tools.diagnostics.diagnostic_io.read_tsv_required` for TSV reads. Add lightweight dataclasses only where they reduce keying ambiguity:

- `ManualOracleRow`
- `MachineArtifactRow`
- `MachineMatch`

Artifact loader responsibilities:

- read `alignment_review.tsv` and `alignment_cells.tsv`;
- optionally read `alignment_production_candidate_gate.tsv` as family-level context only;
- normalize `sample_stem` to oracle `sample_id` by exact string match first;
- preserve source artifact path and SHA256;
- produce `source_row_id` values such as `alignment_cells.tsv:<1-based data row number>`.

Do not import RAW readers, workbook writers, or alignment pipeline modules.

**Step 3: Re-run loader tests**

Run the same pytest command.

Expected: pass.

## Task 4: Evidence Vector Assembler

**Files:**

- Create: `xic_extractor/alignment/shared_peak_identity_explanation/assembler.py`
- Test: `tests/test_shared_peak_identity_assembler.py`

**Step 1: Write failing assembler tests**

Cover:

- at least one evidence vector row is emitted per oracle row;
- additional evidence vector rows are emitted for each matched machine source, preserving source row IDs instead of collapsing ambiguous matches;
- sentinel context rows carry machine columns as `not_applicable`;
- machine source roles are projected as `selected_peak`, `rescued_cell`, or `candidate_gate_family_context` based on artifact source; `tier2_raw_reread` is reserved for sample-level Tier 2 trace sidecars, not the family-level candidate gate;
- blank numeric fields remain blank and are never interpreted as zero;
- artifact SHA256 values are copied into output rows;
- `matched_source_row_ids` aggregates the emitted machine source row IDs for each explanation row;
- all controlled tokens in emitted evidence vectors pass schema validation.

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_shared_peak_identity_assembler.py -q
```

Expected: fails because the assembler does not exist.

**Step 2: Implement the assembler**

Implement a pure function:

```python
def assemble_evidence_vectors(
    oracle_rows: Sequence[ManualOracleRow],
    machine_matches: Mapping[str, Sequence[MachineMatch]],
) -> tuple[dict[str, str], ...]:
    ...
```

Fill evidence facts conservatively:

- use present machine artifact fields for current label, reasons, blockers, RT, boundary, intensity, scan availability, and Tier 2 context;
- set unavailable fields to `not_assessed` or `unavailable` according to the spec;
- do not compute new shape, CWT, or pattern similarity metrics from RAW.

**Step 3: Re-run assembler tests**

Run the same pytest command.

Expected: pass.

## Task 5: Explanation Classifier And Run Facts

**Files:**

- Create: `xic_extractor/alignment/shared_peak_identity_explanation/classifier.py`
- Test: `tests/test_shared_peak_identity_classifier.py`

**Step 1: Write failing classifier tests**

Cover the seed cases that define the vocabulary:

- `FAM000144|NormalBC2312_DNA` and `FAM000144|BenignfatBC1151_DNA` classify as too-conservative or machine-agreement explanations, not failure.
- `FAM000144|TumorBC2312_DNA` classifies as `machine_too_permissive_rt_pattern_conflict`.
- scope-derived manual-fail rows with positive sample-level machine evidence classify as `machine_too_permissive_scope_rule_conflict`, not `machine_agrees_with_manual`.
- `FAM001227|__family_context__` classifies as `delta_mass_related_context_only`.
- `FAM001589` rows classify as `human_unjudgeable_shape_bad`.
- low-intensity supported cells can classify as `machine_too_conservative_low_opportunity`.
- no-match behavior is explicit: manual pass/suspect rows with no sample-level machine match remain explained by the relevant too-conservative class; manual fail rows with no positive sample-level machine evidence may be machine agreement.
- run facts count total/explained/unexplained/inconclusive seed rows and set `vocabulary_special_casing_detected=FALSE`.
- run facts require `seed_rows_explained=seed_rows_total`, `seed_rows_unexplained=0`, and `seed_rows_inconclusive=0` for the Slice 0 vocabulary-validation target.
- a metamorphic test proves the same evidence vector classified under a different `feature_family_id` keeps the same explanation class/status, preventing family-specific classifier exceptions.

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_shared_peak_identity_classifier.py -q
```

Expected: fails because classifier code does not exist.

**Step 2: Implement classifier rules**

Implement:

```python
def classify_explanations(
    oracle_rows: Sequence[ManualOracleRow],
    evidence_rows: Sequence[Mapping[str, str]],
) -> tuple[dict[str, str], ...]:
    ...

def build_slice0_run_facts(
    explanations: Sequence[Mapping[str, str]],
    *,
    durable_oracle_path: Path,
    durable_oracle_sha256: str,
) -> dict[str, str]:
    ...
```

Rules must use reusable evidence tags and machine blockers, not family IDs. Family IDs may appear in tests only to prove the seed cases are covered.

If a seed row would classify as `unexplained_machine_manual_gap`, or if a seed row remains unresolved `inconclusive`, the implementation should still write diagnostic facts but the run facts must make the vocabulary target fail by count. Do not mark that run as `vocabulary_validated`.

**Step 3: Re-run classifier tests**

Run the same pytest command.

Expected: pass.

## Task 6: Writers And CLI

**Files:**

- Create: `xic_extractor/alignment/shared_peak_identity_explanation/writers.py`
- Create: `tools/diagnostics/shared_peak_identity_explanation.py`
- Test: `tests/test_shared_peak_identity_cli.py`

**Step 1: Write failing CLI tests**

Cover:

- CLI writes `shared_peak_identity_manual_oracle.tsv`, evidence vectors, explanations, run facts, and report to the output directory;
- no Slice 1 blast-radius files are written;
- report starts with a compact decision summary containing `diagnostic_only`, Slice 0 facts, whether the vocabulary held or which raw fact blocked it, top blocking rows/classes, and explicit next action;
- report echoes run facts and separates machine-too-conservative from machine-too-permissive examples;
- missing required input artifacts fail with exit code `2` and a clear path/column message;
- running the CLI does not modify the source `alignment_review.tsv`, `alignment_cells.tsv`, or `alignment_matrix.tsv`.

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_shared_peak_identity_cli.py -q
```

Expected: fails because the CLI does not exist.

**Step 2: Implement writers**

Use `write_tsv(..., lineterminator="\n")`. Writers should render rows they receive and validate token domains before writing. They must not recompute domain evidence.

**Step 3: Implement CLI**

Required arguments:

```text
--manual-oracle-tsv
--alignment-review-tsv
--alignment-cells-tsv
--output-dir
```

Optional argument:

```text
--candidate-gate-tsv
```

`--candidate-gate-tsv` is optional family-level context only. It must not be joined through `sample_id`, must not populate `tier2_raw_reread`, and must not imply positive Tier 2 support.

The CLI orchestration order is:

1. load oracle;
2. load machine artifacts;
3. assemble evidence vectors;
4. classify explanations;
5. build run facts;
6. write Slice 0 outputs and report.

**Step 4: Re-run CLI tests**

Run the same pytest command.

Expected: pass.

## Task 7: Diagnostic Index And End-To-End Slice 0 Run

**Files:**

- Modify: `tools/diagnostics/INDEX.md`
- Generated: `output/shared_peak_identity_evidence_explanation/*`

**Step 1: Update diagnostic index**

Register `shared_peak_identity_explanation.py` under Evidence Consistency or Alignment Diagnostics. The entry must state:

- purpose;
- topic group;
- originating spec path;
- `diagnostic_only`;
- Slice 0 outputs;
- no RAW scanning and no `alignment_matrix.tsv` mutation.

**Step 2: Run the focused test shard**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests\test_shared_peak_identity_oracle.py tests\test_shared_peak_identity_schema.py tests\test_shared_peak_identity_loaders.py tests\test_shared_peak_identity_assembler.py tests\test_shared_peak_identity_classifier.py tests\test_shared_peak_identity_cli.py -q
```

Expected: pass.

**Step 3: Run ruff on changed Python files**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\shared_peak_identity_explanation tools\diagnostics\shared_peak_identity_explanation.py tests\test_shared_peak_identity_oracle.py tests\test_shared_peak_identity_schema.py tests\test_shared_peak_identity_loaders.py tests\test_shared_peak_identity_assembler.py tests\test_shared_peak_identity_classifier.py tests\test_shared_peak_identity_cli.py
```

Expected: pass.

**Step 4: Run the real Slice 0 diagnostic**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python -m tools.diagnostics.shared_peak_identity_explanation `
  --manual-oracle-tsv docs\superpowers\fixtures\shared_peak_identity_manual_oracle_v1.tsv `
  --alignment-review-tsv output\tiered_backfill_candidate_gate_8raw_current\alignment_review.tsv `
  --alignment-cells-tsv output\tiered_backfill_candidate_gate_8raw_current\alignment_cells.tsv `
  --candidate-gate-tsv output\tier2_v0_1_coherence_8raw_current_gate\alignment_production_candidate_gate.tsv `
  --output-dir output\shared_peak_identity_evidence_explanation
```

Expected: exit code `0`; Slice 0 output files exist; `shared_peak_identity_run_facts.tsv` has `slice=slice0`, `blast_radius_assessed=not_run_slice0`, `max_overfit_risk=unassessed`, `vocabulary_special_casing_detected=FALSE`, `seed_rows_explained=seed_rows_total`, `seed_rows_unexplained=0`, and `seed_rows_inconclusive=0`.

**Step 5: Run docs/diff smoke checks**

Run:

```powershell
rg -n "production_ready|shadow_ready|blast_radius_manifest|blast_radius_summary" output\shared_peak_identity_evidence_explanation\shared_peak_identity_explanation_report.md
```

Expected: no production-ready claim; Slice 1 terms may appear only as explicit non-goals or not-run facts.

Run:

```powershell
git diff --check
```

Expected: no whitespace errors.

## Task 8: Independent Verification And Completion Audit

**Files:**

- No planned source edits from reviewer/tester roles.

**Step 1: Use repo routing for implementation acceptance**

Ask a read-only `implementation-contract-reviewer` to review the implementation against the spec and plan, focusing on CLI/schema/diagnostic-index/test coverage and no production contract drift.

Ask a `tester` to run the focused verification shard and CLI command in a clean context. The tester may write normal pytest/cache/output side effects but must not edit source/docs/config/tests.

**Step 2: Fix any blocking findings**

If the reviewer or tester finds a blocker, fix it in the main agent scope and rerun the relevant focused verification.

**Step 3: Completion audit**

Check:

- Slice 0 output files exist and validate controlled tokens.
- `shared_peak_identity_run_facts.tsv` reports the required Slice 0 facts.
- all seed rows are explained; no explanation row uses `unexplained_machine_manual_gap`.
- No Slice 1 files are emitted.
- No production matrix/workbook/selection behavior changed.
- `git status --short --branch` shows only expected docs/source/test/output changes plus any pre-existing unrelated dirty files.

Do not mark the goal complete until this audit is true.
