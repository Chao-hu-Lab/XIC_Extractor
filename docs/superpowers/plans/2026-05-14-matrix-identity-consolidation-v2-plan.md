# Matrix Identity Consolidation v2 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an explicit row-identity decision layer so weak untargeted families stay in Audit/Review and only durable feature-family identities enter the primary matrix.

**Architecture:** Separate local cell quality from row identity. A shared cell-quality layer decides whether each cell is quantitatively usable. The row-identity layer consumes those shared decisions and decides whether the family can enter the primary matrix. `production_decisions`, TSV/XLSX writers, guardrails, and targeted benchmark diagnostics must all read the same row identity result.

**Tech Stack:** Python dataclasses, existing `AlignmentMatrix`, `AlignmentConfig`, TSV/XLSX writers, `pytest`, real-data diagnostic scripts under `tools/diagnostics/`.

**Corrected worktree:** `C:\Users\user\Desktop\XIC_Extractor\.worktrees\algorithm-performance-optimization`

**Execution status on this worktree:** Phase A row identity gate plus a tested Phase A2 family-winner demotion were implemented in commit `48a5b1b` (`feat: gate untargeted matrix identity`). The optional iRT-style RT normalization diagnostic described below was **not** implemented in that commit.

**iRT correction:** Cui et al. 2018 supports reference-normalized RT as a drift-aware coordinate. The current codebase already has a related but weaker mechanism (`targeted_istd_trend` + SampleInfo injection-order rolling median drift correction). That mechanism is not a full iRT model: it does not fit canonical/reference anchor transforms, does not output normalized RT scores, and does not report anchor residuals. Treat iRT as pending diagnostic work unless `tools/diagnostics/analyze_rt_normalization_anchors.py` is implemented and validated.

---

## Prerequisites

Use this worktree:

```text
C:\Users\user\Desktop\XIC_Extractor\.worktrees\algorithm-performance-optimization
```

Primary spec:

```text
docs/superpowers/specs/2026-05-14-matrix-identity-consolidation-v2-spec.md
```

Related specs:

```text
docs/superpowers/specs/2026-05-11-ms2-constrained-ms1-feature-family-spec.md
docs/superpowers/specs/2026-05-13-untargeted-final-matrix-and-rescue-evidence-spec.md
```

Hard constraints:

- Do not use targeted workbook labels inside production alignment code.
- Do not delete Audit/Review candidates.
- Do not tune mz/RT thresholds in this plan.
- Do not change DNP or MA.
- Keep default behavior strict for the primary matrix.
- Do not let the identity layer recompute cell quantifiability from raw `status` and `area` alone.

## Task 0: Preflight Blast-Radius Gate Before Production Wiring

**Purpose:** Build the pure decision pieces needed for a read-only blast-radius report, but do not wire them into production matrix export yet.

**Files:**
- Create: `xic_extractor/alignment/cell_quality.py`
- Create: `xic_extractor/alignment/matrix_identity.py`
- Create: `tools/diagnostics/targeted_istd_benchmark.py`
- Create: `tools/diagnostics/analyze_matrix_identity_blast_radius.py`
- Test: `tests/test_alignment_cell_quality.py`
- Test: `tests/test_alignment_matrix_identity.py`
- Test: `tests/test_targeted_istd_benchmark.py`
- Test: `tests/test_matrix_identity_blast_radius.py`

**Step 0: Add or verify strict targeted ISTD benchmark inputs**

The repo must have a strict benchmark producer before blast-radius preflight can
enforce active ISTD stop conditions. If `targeted_istd_benchmark.py` does not
exist, create it in this task.

Input:

```text
targeted workbook:
  Targets
  XIC Results

alignment run dir:
  alignment_review.tsv
  alignment_cells.tsv
  alignment_matrix.tsv
```

Output:

```text
targeted_istd_benchmark_summary.tsv
targeted_istd_benchmark_matches.tsv
targeted_istd_benchmark.json
targeted_istd_benchmark.md
```

Strict benchmark behavior:

- load active DNA ISTDs from targeted workbook: `Role == ISTD` and `NL (Da)` within `116.0474 +/- 0.01`;
- exclude inactive RNA tag `[13C,15N2]-8-oxo-Guo` / `132.0423`;
- require six active DNA ISTDs, each with exactly one primary matrix hit;
- classify each active ISTD as PASS/MISS/SPLIT against current primary matrix hits;
- compute RT mean delta, sample-level RT median absolute delta, and sample-level RT p95 delta;
- compute log-area Spearman and Pearson correlation against targeted area;
- enforce strict defaults:
  - RT mean delta <= `0.15 min`;
  - sample-level RT median absolute delta <= `0.15 min`;
  - sample-level RT p95 <= `0.30 min`;
  - log-area Spearman >= `0.90`;
  - log-area Pearson >= `0.80`;
  - coverage >= targeted positive count - `max(1, 2%)`;
- output the matched `feature_family_id` values needed by blast-radius preflight;
- fail clearly when required workbook sheets or alignment TSV columns are missing.

Unit tests must cover active NL filtering, RNA-tag exclusion, PASS/MISS/SPLIT
classification, RT threshold failure, area-correlation failure, coverage failure,
and missing required workbook/TSV columns.

Run:

```powershell
uv run pytest tests\test_targeted_istd_benchmark.py -q
```

Expected: PASS before Step 6 preflight is allowed.

**Step 1: Add shared cell-quality tests**

Write tests proving that cell usability is not status-only:

- detected cells require finite positive area;
- rescue cells require finite positive area, complete peak fields, and RT within the existing production rescue tolerance;
- duplicate losers and ambiguous MS1 owners are not identity support;
- absent/unchecked/review-only cells are not quantifiable cells;
- rescue cells can be quantifiable matrix evidence but never detected identity evidence.

Ownership boundary:

- `xic_extractor/alignment/cell_quality.py` accepts `AlignedCell` objects and
  config only.
- TSV parsing and missing-column checks belong in `tools/diagnostics/` or a
  diagnostic-only helper, not in the domain module.

Run:

```powershell
uv run pytest tests\test_alignment_cell_quality.py -q
```

Expected: FAIL before `cell_quality.py` exists.

**Step 2: Implement shared cell quality**

Create a small decision model, for example:

```python
@dataclass(frozen=True)
class CellQualityDecision:
    sample_name: str
    feature_family_id: str
    raw_status: str
    quality_status: Literal[
        "detected_quantifiable",
        "rescue_quantifiable",
        "review_rescue",
        "duplicate_loser",
        "ambiguous_owner",
        "blank",
        "invalid",
    ]
    matrix_area: float | None
    quality_reason: str
```

The implementation may reuse existing helper logic from
`production_decisions.py`, but the shared helper must be the source consumed by
both row identity and production cell output after integration.

Run:

```powershell
uv run pytest tests\test_alignment_cell_quality.py -q
```

Expected: PASS.

**Step 3: Add matrix identity tests using cell-quality decisions**

Write tests in `tests/test_alignment_matrix_identity.py`:

- `single_sample_local_owner` with one detected cell and multiple rescues is audit-only;
- `owner_complete_link` or multi-sample detected support is production;
- rescue-only rows are audit-only even with good rescued areas;
- duplicate-only rows are audit-only;
- rescue-heavy rows remain production only when durable detected support remains;
- anchored single-detected rows are audit-only in Phase A;
- identity output exposes `identity_decision`, `primary_evidence`, `identity_reason`, and row flags.

Run:

```powershell
uv run pytest tests\test_alignment_matrix_identity.py -q
```

Expected: FAIL before `matrix_identity.py` exists.

**Step 4: Implement pure matrix identity decisions**

Create a row decision model, for example:

```python
@dataclass(frozen=True)
class MatrixIdentityRowDecision:
    feature_family_id: str
    include_in_primary_matrix: bool
    identity_decision: Literal["production_family", "audit_family"]
    identity_confidence: Literal["high", "medium", "review", "none"]
    primary_evidence: str
    identity_reason: str
    quantifiable_detected_count: int
    quantifiable_rescue_count: int
    review_rescue_count: int
    duplicate_assigned_count: int
    ambiguous_ms1_owner_count: int
    row_flags: tuple[str, ...]
```

Rules for Phase A:

- detected identity support comes only from `detected_quantifiable` cell-quality decisions;
- rescue/backfill can increase accepted matrix cells only after row identity passes;
- `single_sample_local_owner` is audit-only by default;
- `owner_complete_link` and `cid_nl_only` require at least two quantifiable detected cells;
- rescue-only, duplicate-only, zero-present, and ambiguous-only rows are audit-only;
- anchored single-detected rows are audit-only in Phase A and flagged as `anchored_single_detected`;
- `rescue_heavy` is a flag, not a promotion rule.

Run:

```powershell
uv run pytest tests\test_alignment_cell_quality.py tests\test_alignment_matrix_identity.py -q
```

Expected: PASS.

**Step 5: Add read-only blast-radius diagnostic**

Create `tools/diagnostics/analyze_matrix_identity_blast_radius.py`.

Inputs:

```text
alignment_review.tsv
alignment_cells.tsv
alignment_matrix.tsv
```

Targeted benchmark files are produced by `targeted_istd_benchmark.py` and are
required when enforcing active ISTD stop conditions:

```text
targeted_istd_benchmark_matches.tsv
targeted_istd_benchmark_summary.tsv
targeted_istd_benchmark.json
```

The diagnostic may read targeted benchmark files because it lives under
`tools/diagnostics/`. Production alignment code must not read targeted labels.
Active ISTD rows must come from benchmark files, not from row-name heuristics.

Minimum alignment TSV columns required for a complete blast-radius result:

```text
alignment_cells.tsv:
  feature_family_id
  sample_stem
  status
  area
  peak_start_rt
  peak_end_rt
  rt_delta_sec
  reason

alignment_review.tsv:
  feature_family_id
  include_in_primary_matrix
  family_evidence or evidence
```

If any required column is missing, the diagnostic must output
`evidence_status=evidence_incomplete`, list `missing_required_columns`, and exit
non-zero unless an explicit `--allow-incomplete-summary` flag is used. It must
not silently approximate rescue quality from `status` and `area` alone.

Outputs:

```text
matrix_identity_blast_radius.tsv
matrix_identity_blast_radius.json
```

Report fields:

```text
feature_family_id
current_include_in_primary_matrix
proposed_include_in_primary_matrix
identity_decision
primary_evidence
identity_reason
quantifiable_detected_count
quantifiable_rescue_count
duplicate_assigned_count
ambiguous_ms1_owner_count
row_flags
would_change_to_audit
would_change_to_production
evidence_status
missing_required_columns
targeted_benchmark_class
targeted_target_name
targeted_role
active_dna_istd_candidate
```

Blast-radius tests must cover:

- complete alignment TSV input produces `evidence_status=complete`;
- missing peak/RT columns produce `evidence_status=evidence_incomplete`;
- active DNA ISTD rows are identified only through targeted benchmark input;
- missing targeted benchmark files stop the preflight when active ISTD stop
  conditions are enabled.

Run:

```powershell
uv run pytest tests\test_matrix_identity_blast_radius.py -q
```

Expected: PASS.

**Step 6: Run preflight on current comparable outputs**

Use the freshest 8-RAW and 85-RAW alignment outputs available in `output\`.
If either output is missing, run only the available output and mark the missing
one in the report.

Expected preflight summary:

- how many current primary rows would become audit-only;
- how many active DNA ISTD / checkpoint rows would be affected after joining targeted benchmark files;
- counts by `primary_evidence`;
- top examples for `single_sample_local_owner`, `rescue_only`, `duplicate_only`, and `anchored_single_detected`.

Stop and review before production wiring if:

- targeted benchmark files are missing and active ISTD stop conditions cannot be evaluated;
- any active DNA ISTD would become audit-only in the preflight;
- `5-medC` or `5-hmdC` checkpoint rows look like they would be removed only because of missing diagnostic fields rather than weak identity;
- most current primary rows would disappear, suggesting a parser or evidence mapping bug.

## Task 1: Route Production Decisions Through Shared Quality And Identity

**Files:**
- Modify: `xic_extractor/alignment/production_decisions.py`
- Test: `tests/test_alignment_production_decisions.py`

**Step 1: Write failing regression tests**

Update production-decision tests:

- single-sample local-owner rows are audit-only;
- rescued cells become `review_rescue` when row identity is audit-only;
- production rows with durable detected support still accept valid rescue cells;
- invalid rescue cells remain review/blank for the same reason as before;
- row-level flags include identity-layer flags.

Run:

```powershell
uv run pytest tests\test_alignment_production_decisions.py -q
```

Expected: FAIL before integration because production still has its own row
identity shortcut.

**Step 2: Integrate without duplicating acceptance logic**

Inside `build_production_decisions`:

1. build shared cell-quality decisions;
2. build matrix identity decisions from those shared decisions;
3. use `identity_decision.row(cluster_id).include_in_primary_matrix` as the row gate;
4. use the same cell-quality decision to decide accepted/review/blank cell output;
5. merge identity row flags into the existing review flags;
6. remove the special case that treats `single_sample_local_owner` as durable row identity.

Run:

```powershell
uv run pytest tests\test_alignment_cell_quality.py tests\test_alignment_matrix_identity.py tests\test_alignment_production_decisions.py -q
```

Expected: PASS.

## Task 2: Expose Identity Fields In Review Output

**Files:**
- Modify: `xic_extractor/alignment/tsv_writer.py`
- Modify: `xic_extractor/alignment/xlsx_writer.py`
- Test: `tests/test_alignment_tsv_writer.py`
- Test: `tests/test_alignment_xlsx_writer.py`
- Test: `tests/test_untargeted_final_matrix_contract.py`

**Step 1: Write failing writer tests**

Assert that `alignment_review.tsv` and workbook Audit/Review expose:

- `identity_decision`;
- `identity_confidence`;
- `primary_evidence`;
- `identity_reason`;
- `quantifiable_detected_count`;
- `quantifiable_rescue_count`;
- `review_rescue_count`;
- `duplicate_assigned_count`;
- `ambiguous_ms1_owner_count`;
- `row_flags`.

Keep existing `accepted_cell_count` as the post-row-gate count used by legacy
diagnostics, but do not use it as pre-gate identity support.

Add final matrix assertions:

- audit-only identity rows do not appear in `alignment_matrix.tsv`;
- audit-only identity rows do not appear in workbook `Matrix`;
- the same candidates still appear in Audit/Review.

Run:

```powershell
uv run pytest tests\test_alignment_tsv_writer.py tests\test_alignment_xlsx_writer.py tests\test_untargeted_final_matrix_contract.py -q
```

Expected: FAIL before writer wiring.

**Step 2: Implement writer wiring**

Update review columns and workbook review rendering. Do not add identity fields
to the primary matrix; it remains a clean intensity matrix.

Run:

```powershell
uv run pytest tests\test_alignment_tsv_writer.py tests\test_alignment_xlsx_writer.py tests\test_untargeted_final_matrix_contract.py -q
```

Expected: PASS.

## Task 3: Update Targeted Benchmark Diagnostics

**Correction/status:** In commit `48a5b1b`, the strict benchmark and guardrail consumption are usable, but benchmark match rows were not expanded with `alignment_identity_decision` / `alignment_identity_reason`. Keep this task as follow-up if identity-aware PASS/MISS/SPLIT explanations are required directly inside the targeted benchmark TSV/JSON.

**Files:**
- Modify: `tools/diagnostics/targeted_istd_benchmark.py`
- Modify: `tools/diagnostics/targeted_gt_alignment_audit.py`
- Test: `tests/test_targeted_istd_benchmark.py`
- Test: `tests/test_targeted_gt_alignment_audit.py`

**Step 1: Write failing targeted benchmark tests**

Add cases proving the targeted benchmark can explain why a targeted feature
matched or failed:

- matched primary hit reports `identity_decision=production_family`;
- `MISS` caused by row identity reports `identity_decision=audit_family` and `identity_reason`;
- `SPLIT` reports identity decisions for each competing primary candidate;
- legacy alignment outputs without identity columns still fall back to current behavior.

Run:

```powershell
uv run pytest tests\test_targeted_istd_benchmark.py tests\test_targeted_gt_alignment_audit.py -q
```

Expected: FAIL before diagnostic update.

**Step 2: Implement identity-aware diagnostic output**

Propagate these fields into benchmark matches/summary where available:

```text
alignment_identity_decision
alignment_primary_evidence
alignment_identity_reason
alignment_row_flags
```

The diagnostic may read identity fields from `alignment_review.tsv` and
`alignment_cells.tsv`, but production alignment code must not read targeted
labels.

Run:

```powershell
uv run pytest tests\test_targeted_istd_benchmark.py tests\test_targeted_gt_alignment_audit.py -q
```

Expected: PASS.

## Task 4: Update Guardrails To Trust Identity Decisions

**Files:**
- Modify: `tools/diagnostics/untargeted_alignment_guardrails.py`
- Test: `tests/test_untargeted_alignment_guardrails.py`

**Step 1: Write failing guardrail tests**

Add test cases:

- if `identity_decision=audit_family`, guardrails do not count it as production even when raw statuses are present;
- if `identity_decision=production_family`, guardrails count it as production;
- old schema still falls back to `include_in_primary_matrix`, then `accepted_cell_count`, then raw status counts.

Run:

```powershell
uv run pytest tests\test_untargeted_alignment_guardrails.py -q
```

Expected: FAIL before guardrail update.

**Step 2: Implement guardrail update**

In `_is_production_family`, prefer identity fields in this order:

1. `identity_decision`;
2. `include_in_primary_matrix`;
3. `accepted_cell_count`;
4. legacy raw production status counts.

Run:

```powershell
uv run pytest tests\test_untargeted_alignment_guardrails.py -q
```

Expected: PASS.

## Task 5: Real-Data Validation Gates

**Files:**
- No production files unless validation reveals a bug.
- Output: existing `output\alignment\...` and `output\diagnostics\...` folders.

**Step 1: Run focused unit suite**

Run:

```powershell
uv run pytest tests\test_alignment_cell_quality.py tests\test_alignment_matrix_identity.py tests\test_alignment_production_decisions.py tests\test_alignment_tsv_writer.py tests\test_alignment_xlsx_writer.py tests\test_untargeted_final_matrix_contract.py tests\test_targeted_istd_benchmark.py tests\test_targeted_gt_alignment_audit.py tests\test_untargeted_alignment_guardrails.py tests\test_matrix_identity_blast_radius.py -q
```

Expected: PASS.

**Step 2: Run 8-RAW validation-fast alignment**

Use the current project runner and the same validation-fast command pattern used
for prior untargeted validation. Required output must include:

```text
alignment_review.tsv
alignment_matrix.tsv
alignment_cells.tsv
```

If an existing fresh 8-RAW alignment run was produced after the code change,
reuse it. Otherwise rerun with `--emit-alignment-cells`.

**Step 3: Run strict targeted ISTD benchmark**

Run the existing targeted benchmark diagnostic against:

```text
8-RAW:  C:\Users\user\Desktop\XIC_Extractor\output\xic_results_20260512_1151.xlsx
85-RAW: C:\Users\user\Desktop\XIC_Extractor\output\xic_results_20260512_1200.xlsx
```

Expected:

- six active DNA ISTDs still have exactly one primary matrix hit;
- RNA tag `[13C,15N2]-8-oxo-Guo` remains inactive/excluded;
- RT and area trend checks do not regress;
- every PASS/MISS/SPLIT row includes identity decision/reason fields.

**Step 4: Run 85-RAW comparison**

Rerun or reuse an 85-RAW alignment output after code change.

Compare:

- total production families;
- zero-present production families;
- duplicate-only production families;
- high-backfill production families;
- targeted checkpoint result for `5-medC`;
- targeted checkpoint result for `5-hmdC`;
- strict targeted ISTD benchmark summary.

Expected direction:

- zero-present production families -> 0;
- duplicate-only production families -> 0 or materially reduced;
- high-backfill production rows reduced only when they lack detected identity;
- Audit/Review row counts can remain high.

Stop and report instead of tuning thresholds if:

- strict ISTD benchmark regresses;
- targeted labels would be needed to make production row identity pass;
- the change improves weak-row counts only by hiding diagnostics;
- an expected targeted checkpoint row fails because cell-quality parsing is missing fields from the alignment output.

## Phase A2: Family Winner Policy

Do not implement this in Phase A unless the user explicitly expands scope after
the weak-row gate report.

Phase A2 may proceed only after Phase A validation shows unresolved competing
families remain in the primary matrix.

Required before implementation:

- a report grouping near-duplicate families by tag, m/z, RT, product/observed loss, and overlapping ownership claims;
- examples showing that multiple current production rows represent one plausible identity;
- tests proving the loser remains in Audit/Review rather than being deleted.

Winner rule priority:

1. durable detected identity support;
2. quantifiable detected count;
3. existing claim-registry winner state;
4. lower duplicate/ambiguous pressure;
5. quantifiable rescue completeness;
6. area only as a final tie-breaker.

## Optional Phase B: iRT-Style RT Drift Diagnostic

**Status:** First diagnostic implemented after commit `48a5b1b`; do not describe
it as part of the matrix identity gate itself.

**Files:**
- Created: `tools/diagnostics/analyze_rt_normalization_anchors.py`
- Created: `tests/test_rt_normalization_anchors.py`
- Do not modify production alignment gates in this phase.

**Scientific reference:**

```text
Cui et al. 2018. Normalized Retention Time for Targeted Analysis of the DNA Adductome.
Analytical Chemistry 90(24):14111-14115. DOI: 10.1021/acs.analchem.8b04660.
```

**Purpose:**

The paper supports using reference-normalized RT as a drift-aware coordinate.
For this project, implement the idea first as a diagnostic. Do not copy the
paper's scheduled-SRM acquisition window as a matrix identity tolerance.

Current implementation boundary:

- Existing `xic_extractor/alignment/drift_evidence.py` can read targeted ISTD RTs and SampleInfo injection order, compute a local rolling-median RT drift per sample, and feed drift-corrected RT deltas into owner-edge scoring.
- That is iRT-adjacent drift evidence, not the paper's full normalized RT / iRT score strategy.
- `tools/diagnostics/analyze_rt_normalization_anchors.py` now fits per-sample
  anchor RT normalization models, emits anchor residuals, and compares raw vs
  normalized RT ranges for alignment families.
- This remains review evidence only. It is not yet a primary matrix promotion
  rule.

8-RAW trial output:

```text
output\diagnostics\phase_n_rt_normalization_8raw_20260514
```

Updated 8-RAW result with auto piecewise model and anchor-quality gating:

- 6 active DNA ISTD anchors available in all 8 samples.
- 2 anchor observations excluded by the `0.30 min` residual gate.
- All review families with enough cells: 293 improved, 220 worsened.
- Median RT-range improvement: about `+0.062 min`.
- Diagnostic status: `PASS`.

85-RAW trial against the existing
`phase_l_preconsolidate_seed2_recenter_min2_85raw` output:

- 6 active DNA ISTD anchors available in all 85 samples.
- 23 anchor observations excluded; 20 were `d3-N6-medA`, matching the
  suspected targeted peak issue.
- All review families with enough cells: 545 improved, 772 worsened.
- Median RT-range improvement: about `-0.083 min`.
- Diagnostic status: `WARN`.

Injection-order-aware 85-RAW trial:

```text
output\diagnostics\phase_p_rt_normalization_injection_local_85raw_20260514
```

- Uses `SampleInfo.xlsx` injection order with `reference-source =
  injection-local-median` and `--injection-window 4`.
- This is different from the original global iRT diagnostic. It maps each
  sample's anchor RTs to a local rolling median reference from nearby
  injections.
- All 85 samples were modelled after adding the missing `QC_4` / `QC4` alias.
- 2 anchor observations were excluded: one `d3-5-medC`, one `d3-N6-medA`.
- All review families with enough cells: 740 improved, 575 worsened.
- Primary families: 457 improved, 304 worsened.
- Median RT-range improvement: about `+0.013 min` overall and `+0.021 min` on
  primary families.
- Diagnostic status: `PASS`.

This confirms the user's concern: the project already used injection order for
targeted ISTD drift evidence, but the first normalized RT diagnostic did not.
On 85 RAW, injection-local iRT changes the result from `WARN` to `PASS`.

Interpretation: the concept is useful as an evidence layer, especially for
families that improve strongly in normalized RT space, but it is not yet strong
enough to become an unconditional production promotion gate. Next refinements
should use injection-local improvement as a positive evidence input only when
the family-level normalized RT range improves, not as a blanket replacement for
raw RT.

Diagnostic acceptance:

- enough anchors are available in most samples;
- anchor fit residuals are stable;
- targeted ISTD SPLIT/MISS cases improve in normalized RT space;
- false-positive/duplicate pressure does not increase.

If these conditions do not hold, keep RT normalization as review evidence only.

## Task 6: Final Review And Commit

**Step 1: Run final focused tests**

Run:

```powershell
uv run pytest tests\test_alignment_cell_quality.py tests\test_alignment_matrix_identity.py tests\test_alignment_production_decisions.py tests\test_alignment_tsv_writer.py tests\test_alignment_xlsx_writer.py tests\test_untargeted_final_matrix_contract.py tests\test_targeted_istd_benchmark.py tests\test_targeted_gt_alignment_audit.py tests\test_untargeted_alignment_guardrails.py tests\test_matrix_identity_blast_radius.py -q
```

Expected: PASS.

**Step 2: Inspect diff**

Run:

```powershell
git diff --check
git diff --stat
```

Expected:

- no whitespace errors;
- only identity decision, writer, diagnostics, tests, and docs changed;
- no unrelated output artifacts are staged.

**Step 3: Commit**

Commit only after unit tests pass and real-data validation is summarized:

```powershell
git add xic_extractor\alignment\cell_quality.py xic_extractor\alignment\matrix_identity.py xic_extractor\alignment\production_decisions.py xic_extractor\alignment\tsv_writer.py xic_extractor\alignment\xlsx_writer.py tools\diagnostics\analyze_matrix_identity_blast_radius.py tools\diagnostics\targeted_istd_benchmark.py tools\diagnostics\targeted_gt_alignment_audit.py tools\diagnostics\untargeted_alignment_guardrails.py tests\test_alignment_cell_quality.py tests\test_alignment_matrix_identity.py tests\test_alignment_production_decisions.py tests\test_alignment_tsv_writer.py tests\test_alignment_xlsx_writer.py tests\test_untargeted_final_matrix_contract.py tests\test_targeted_istd_benchmark.py tests\test_targeted_gt_alignment_audit.py tests\test_untargeted_alignment_guardrails.py tests\test_matrix_identity_blast_radius.py docs\superpowers\specs\2026-05-14-matrix-identity-consolidation-v2-spec.md docs\superpowers\plans\2026-05-14-matrix-identity-consolidation-v2-plan.md
git commit -m "feat: add untargeted matrix identity promotion gate"
```

## Done When

- Preflight blast-radius report exists before production writer behavior changes.
- Row promotion is owned by one explicit identity decision layer.
- Cell quality is shared by row identity and production cell decisions.
- `single_sample_local_owner`, rescue-only, duplicate-only, and zero-present rows do not enter the primary matrix.
- Primary matrix output and workbook Matrix both use the same identity decision.
- Audit/Review keeps every candidate and explains every audit-only row.
- Targeted ISTD benchmark reports identity reasons for PASS/MISS/SPLIT.
- Guardrails consume identity decision fields when available.
- Focused tests pass.
- 8-RAW targeted ISTD benchmark passes.
- 85-RAW comparison shows weak production rows are reduced without losing audit evidence.
