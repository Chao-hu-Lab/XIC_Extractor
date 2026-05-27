# Resolver Default Switch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement P1 by making `region_first_safe_merge` the extraction /
targeted-validation default while preserving legacy resolver values as accepted
explicit modes.

**Architecture:** Change only the default surfaces and audit provenance required by P1. Keep resolver implementations intact: `local_minimum`, `legacy_savgol`, `arbitrated`, and `region_first_safe_merge` remain supported modes until Cleanup C2. Add safe-merge rejection reasons as additive audit fields so failed promotions are explainable without changing gate thresholds.

**Post-hotfix correction (2026-05-25):** The real-data validation slice proved
that `region_first_safe_merge` must not be passed through to untargeted
alignment production yet. `scripts/run_alignment.py --resolver-mode` may default
to `region_first_safe_merge` as a CLI/audit surface, but alignment production
peak picking must coerce it to `local_minimum`; region-first evidence remains
audit context. Task 2's passthrough instructions below are superseded by this
correction and must not be re-applied without a new reviewed plan.

**Tech Stack:** Python, argparse, pytest, existing extraction / peak detection dataclasses and TSV writers.

**Spec:** `docs/superpowers/specs/2026-05-24-peak-pipeline-resolver-default-switch-spec.md`

---

## Execution Rules

1. Work only in `C:\Users\user\Desktop\XIC_Extractor\.worktrees\peak-pipeline-modernization`.
2. Do not implement Cleanup C-specs.
3. Do not remove any resolver mode from `RESOLVER_MODES`.
4. Do not change safe-merge thresholds or scoring weights.
5. Use TDD for each behavior change: write/update tests first, verify failure when practical, implement, rerun focused tests.
6. Keep real-data validation as a separate gate after unit tests pass; do not claim production readiness from unit tests alone.
7. Do not start implementation until this plan has passed review and any review findings have been patched into the plan.
8. After executing this plan, run a post-implementation review against the plan,
   P1 spec, AGENTS.md contract, public surfaces, and test coverage. Fix any
   actionable issue before declaring the slice complete.

---

## Plan Review Gate

Before code edits begin, this plan must be reviewed against:

- P1 spec requirements and the modernization overview
- live code paths named in the plan
- public contracts for settings, CLI defaults, and `peak_candidates.tsv`
- test commands and expected failure/pass states

Review output must be recorded in the conversation or a short note. Any
actionable review finding must be patched into this plan before Task 1 starts.

### Initial Plan Review Result

Review status: patched after review, not yet implemented.

Fixes applied before implementation:

- Task 2 now references the actual existing `test_run_alignment.py` test name
  and requires renaming it to match the new behavior.
- Task 3 now covers failed safe-merge reasons beyond the first eligibility
  helper, including missing selected shadow boundaries and promoted-area ratio
  failures.
- Task 4 now references the actual header tuple in
  `tests/test_peak_candidate_table.py`.

---

## Files And Responsibilities

- `xic_extractor/settings_schema.py` — canonical settings default and user-facing resolver description.
- `config/settings.example.csv` — sample config default.
- `scripts/run_alignment.py` — CLI default and alignment production resolver passthrough.
- `xic_extractor/peak_detection/region_safe_merge.py` — safe-merge eligibility reason helper and outcome propagation.
- `xic_extractor/peak_detection/models.py` — additive selected-candidate audit field for failed safe-merge promotion reason.
- `xic_extractor/peak_detection/hypotheses.py` — carry the new audit field into the hypothesis spine.
- `xic_extractor/extraction/peak_candidate_table.py` — emit the new audit column.
- `tests/test_config.py` — settings/default contract.
- `tests/test_run_alignment.py` — CLI default and passthrough contract.
- `tests/test_region_safe_merge.py` — failed safe-merge reason contract.
- `tests/test_peak_candidate_table.py` — additive TSV column contract.

---

## Task 1 — Settings Defaults

**Files:**

- Modify: `tests/test_config.py`
- Modify: `xic_extractor/settings_schema.py`
- Modify: `config/settings.example.csv`

- [ ] **Step 1: Update the failing tests**

In `tests/test_config.py`, update the existing default assertions:

```python
assert config.resolver_mode == "region_first_safe_merge"
```

and:

```python
assert resolver_row["value"] == "region_first_safe_merge"
assert "legacy_savgol" in resolver_row["description"]
assert "local_minimum" in resolver_row["description"]
assert "arbitrated" in resolver_row["description"]
assert "region_first_safe_merge" in resolver_row["description"]
```

- [ ] **Step 2: Run the focused tests and confirm they fail**

Run:

```powershell
python -m pytest tests\test_config.py::test_load_config_reads_settings_and_targets tests\test_config.py::test_settings_example_documents_region_first_safe_merge_mode -q
```

Expected before implementation: assertions still see `legacy_savgol`.

- [ ] **Step 3: Update defaults**

In `xic_extractor/settings_schema.py`, change:

```python
"resolver_mode": "legacy_savgol",
```

to:

```python
"resolver_mode": "region_first_safe_merge",
```

Keep `RESOLVER_MODES` unchanged.

In `config/settings.example.csv`, change the `resolver_mode` value from
`legacy_savgol` to `region_first_safe_merge`. Keep the description listing all
currently accepted modes.

- [ ] **Step 4: Rerun the focused tests**

Run:

```powershell
python -m pytest tests\test_config.py::test_load_config_reads_settings_and_targets tests\test_config.py::test_settings_example_documents_region_first_safe_merge_mode -q
```

Expected: pass.

---

## Task 2 — `run_alignment.py` Effective Default

**Files:**

- Modify: `tests/test_run_alignment.py`
- Modify: `tests/test_validation_harness.py`
- Modify: `scripts/run_alignment.py`
- Modify: `scripts/validation_harness.py`
- Modify: `scripts/validation_harness_core.py`

- [ ] **Step 1: Update/add CLI contract tests**

Post-hotfix, `tests/test_run_alignment.py` must keep the alignment production
guard explicit:

```python
def test_run_alignment_cli_keeps_region_first_safe_merge_out_of_production_mode(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
```

It must assert that explicit `region_first_safe_merge` remains coerced for
alignment production:

```python
assert captured["peak_config"].resolver_mode == "local_minimum"
```

Add a default-mode test that omits `--resolver-mode`:

```python
def test_run_alignment_cli_defaults_to_local_minimum_production_mode(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    batch_index = tmp_path / "discovery_batch_index.csv"
    batch_index.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir = tmp_path / "raws"
    raw_dir.mkdir()
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()
    output_dir = tmp_path / "out"
    captured: dict[str, object] = {}

    def fake_run_alignment(**kwargs):
        captured.update(kwargs)
        return AlignmentRunOutputs()

    monkeypatch.setattr(run_alignment, "run_alignment", fake_run_alignment)

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(batch_index),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert code == 0
    assert captured["peak_config"].resolver_mode == "local_minimum"
```

- [ ] **Step 2: Run the focused tests and confirm they fail**

Run:

```powershell
python -m pytest tests\test_run_alignment.py::test_run_alignment_cli_defaults_to_local_minimum_production_mode tests\test_run_alignment.py::test_run_alignment_cli_keeps_region_first_safe_merge_out_of_production_mode -q
```

Expected: both tests pass in the hotfix-aligned state.

- [ ] **Step 3: Update CLI defaults and preserve the alignment production guard**

In `scripts/run_alignment.py`, change:

```python
default="local_minimum",
```

to:

```python
default="region_first_safe_merge",
```

Keep the alignment production rewrite helper:

```python
def _alignment_production_resolver_mode(resolver_mode: str) -> str:
    if resolver_mode == "region_first_safe_merge":
        return "local_minimum"
    return resolver_mode
```

Also update `scripts/validation_harness.py --resolver-mode` and
`ValidationRunSpec.resolver_mode` defaults to:

```python
default="region_first_safe_merge"
```

- [ ] **Step 4: Rerun focused tests**

Run:

```powershell
python -m pytest tests\test_run_alignment.py -q
```

Expected: pass.

---

## Task 3 — Safe-Merge Failed-Gate Reason

**Files:**

- Modify: `tests/test_region_safe_merge.py`
- Modify: `xic_extractor/peak_detection/region_safe_merge.py`
- Modify: `xic_extractor/peak_detection/models.py`
- Modify: `xic_extractor/peak_detection/hypotheses.py`

- [ ] **Step 1: Add eligibility reason tests**

In `tests/test_region_safe_merge.py`, update the import block:

```python
from xic_extractor.peak_detection.region_safe_merge import (
    RegionFirstSafeMergeOutcome,
    apply_region_first_safe_merge_decision,
    eligibility_for_region_first_safe_merge,
)
```

Then add tests for a passing decision and one failed gate:

```python
def test_safe_merge_eligibility_reports_ok_reason() -> None:
    result = eligibility_for_region_first_safe_merge(
        _decision(
            shadow_boundary_id="left;right",
            source="adjacent_wis_local_minimum_merge",
        )
    )

    assert result.eligible is True
    assert result.reason == "eligible"


def test_safe_merge_eligibility_reports_failed_gap_gate() -> None:
    result = eligibility_for_region_first_safe_merge(
        _decision(
            shadow_boundary_id="left;right",
            source="adjacent_wis_local_minimum_merge",
            selected_interval_gap_max_min=0.2,
        )
    )

    assert result.eligible is False
    assert result.reason == "gap_exceeds_safe_merge_max"
```

- [ ] **Step 2: Run the focused tests and confirm they fail**

Run:

```powershell
python -m pytest tests\test_region_safe_merge.py::test_safe_merge_eligibility_reports_ok_reason tests\test_region_safe_merge.py::test_safe_merge_eligibility_reports_failed_gap_gate -q
```

Expected before implementation: `eligibility_for_region_first_safe_merge` does
not exist.

- [ ] **Step 3: Implement reason-bearing helper**

In `xic_extractor/peak_detection/region_safe_merge.py`, add:

```python
@dataclass(frozen=True)
class SafeMergeEligibility:
    eligible: bool
    reason: str
```

Add `eligibility_for_region_first_safe_merge(decision)` that mirrors the
existing gates and returns stable reason strings:

```python
def eligibility_for_region_first_safe_merge(
    decision: RegionSelectionDecision,
) -> SafeMergeEligibility:
    if decision.shadow_status != "evaluated":
        return SafeMergeEligibility(False, "shadow_not_evaluated")
    if decision.shadow_verdict != "merge_suggested":
        return SafeMergeEligibility(False, "shadow_verdict_not_merge_suggested")
    if decision.merge_suggestion_source != "adjacent_wis_local_minimum_merge":
        return SafeMergeEligibility(False, "unsupported_merge_suggestion_source")
    if (decision.selected_interval_count or 0) < 2:
        return SafeMergeEligibility(False, "selected_interval_count_lt_2")
    gap_max = decision.selected_interval_gap_max_min
    if gap_max is None:
        return SafeMergeEligibility(False, "selected_interval_gap_missing")
    if gap_max > SAFE_MERGE_GAP_MAX_MIN:
        return SafeMergeEligibility(False, "gap_exceeds_safe_merge_max")
    if (
        decision.area_ratio is not None
        and decision.area_ratio > SAFE_MERGE_AREA_RATIO_MAX
    ):
        return SafeMergeEligibility(False, "shadow_area_ratio_exceeds_safe_merge_max")
    if decision.current_rt_apex_min is None or decision.shadow_rt_apex_min is None:
        return SafeMergeEligibility(False, "apex_rt_missing")
    if (
        abs(decision.current_rt_apex_min - decision.shadow_rt_apex_min)
        > SAFE_MERGE_APEX_DELTA_MAX_MIN
    ):
        return SafeMergeEligibility(False, "apex_delta_exceeds_safe_merge_max")
    return SafeMergeEligibility(True, "eligible")
```

Change `is_region_first_safe_merge_eligible` to:

```python
def is_region_first_safe_merge_eligible(
    decision: RegionSelectionDecision,
) -> bool:
    return eligibility_for_region_first_safe_merge(decision).eligible
```

- [ ] **Step 4: Propagate failed reason to selected candidate audit**

Add to `PeakCandidate` in `xic_extractor/peak_detection/models.py`:

```python
safe_merge_rejection_reason: str = ""
```

Add to `AuditTrail` in `xic_extractor/peak_detection/hypotheses.py`:

```python
safe_merge_rejection_reason: str = ""
```

Map it wherever safe-merge audit fields are already copied from
`PeakCandidate` to `AuditTrail`.

In `apply_region_first_safe_merge_decision`, compute eligibility once. When the
decision is a merge suggestion but fails a gate, return the selected candidate
with `safe_merge_rejection_reason` set to the failed reason. Do not set the
field for non-merge-suggested rows unless the reason is useful to reviewers.

Also handle the two post-eligibility failures that happen after the first gate
check:

- if `_selected_shadow_boundaries(...)` returns empty after eligibility passes,
  set `safe_merge_rejection_reason="shadow_boundaries_missing"`
- if the recomputed promoted-area ratio falls outside
  `[SAFE_MERGE_AREA_RATIO_MIN, SAFE_MERGE_AREA_RATIO_MAX]`, set
  `safe_merge_rejection_reason="promoted_area_ratio_outside_safe_merge_range"`

When setting a rejection reason, update the returned
`RegionFirstSafeMergeOutcome` consistently:

```python
rejected_candidate = replace(
    selected_candidate,
    safe_merge_rejection_reason=reason,
)
return RegionFirstSafeMergeOutcome(
    candidates_result=replace(
        candidates_result,
        candidates=_replace_candidate(
            candidates_result.candidates,
            selected_candidate,
            rejected_candidate,
        ),
    ),
    selected_candidate=rejected_candidate,
    candidate_scores=_replace_candidate_scores(
        candidate_scores,
        selected_candidate,
        rejected_candidate,
    ),
    decision=decision,
)
```

Add one focused test that calls `apply_region_first_safe_merge_decision(...)`
with a large promoted-area ratio and asserts:

```python
assert outcome.promoted is False
assert (
    outcome.selected_candidate.safe_merge_rejection_reason
    == "promoted_area_ratio_outside_safe_merge_range"
)
```

- [ ] **Step 5: Rerun region-safe-merge tests**

Run:

```powershell
python -m pytest tests\test_region_safe_merge.py -q
```

Expected: pass.

---

## Task 4 — TSV Audit Column

**Files:**

- Modify: `tests/test_peak_candidate_table.py`
- Modify: `xic_extractor/extraction/peak_candidate_table.py`

- [ ] **Step 1: Add TSV column test**

In `tests/test_peak_candidate_table.py`, update
`_SAFE_MERGE_PROVENANCE_HEADERS` to include:

```python
"safe_merge_rejection_reason",
```

after `safe_merge_promotion_selected_interval_gap_max_min`.

Add or update a row-building test:

```python
assert row["safe_merge_rejection_reason"] == "gap_exceeds_safe_merge_max"
```

- [ ] **Step 2: Run the focused test and confirm it fails**

Run:

```powershell
python -m pytest tests\test_peak_candidate_table.py::test_build_rows_exposes_safe_merge_promotion_provenance -q
```

Expected before implementation: missing column/value.

- [ ] **Step 3: Emit the column**

In `xic_extractor/extraction/peak_candidate_table.py`, add the header:

```python
"safe_merge_rejection_reason",
```

and row value:

```python
"safe_merge_rejection_reason": hypothesis.audit.safe_merge_rejection_reason,
```

- [ ] **Step 4: Rerun focused tests**

Run:

```powershell
python -m pytest tests\test_peak_candidate_table.py tests\test_region_safe_merge.py -q
```

Expected: pass.

---

## Task 5 — Focused Regression Suite

**Files:** no planned source edits unless tests expose a real defect.

- [ ] **Step 1: Run P1-focused tests**

Run:

```powershell
python -m pytest tests\test_config.py tests\test_run_alignment.py tests\test_region_safe_merge.py tests\test_peak_candidate_table.py -q
```

Expected: pass.

- [ ] **Step 2: Run affected-test discovery**

Run:

```powershell
codegraph affected xic_extractor\settings_schema.py scripts\run_alignment.py xic_extractor\peak_detection\region_safe_merge.py xic_extractor\peak_detection\models.py xic_extractor\peak_detection\hypotheses.py xic_extractor\extraction\peak_candidate_table.py
```

Use the output to decide whether an additional narrow test shard is needed.

- [ ] **Step 3: Run import/compile smoke**

Run:

```powershell
python -m py_compile xic_extractor\settings_schema.py scripts\run_alignment.py xic_extractor\peak_detection\region_safe_merge.py xic_extractor\peak_detection\models.py xic_extractor\peak_detection\hypotheses.py xic_extractor\extraction\peak_candidate_table.py
```

Expected: no output and exit code 0.

---

## Task 6 — Gate Note Stub

**Files:**

- Create: `docs/superpowers/notes/2026-05-24-resolver-default-switch-implementation-note.md`

- [ ] **Step 1: Record implementation status**

Create a short note with:

```markdown
# Resolver Default Switch Implementation Note

**Date:** 2026-05-24
**Branch:** codex/peak-pipeline-modernization
**Gate status:** diagnostic_only

## Implemented

- `region_first_safe_merge` is now the canonical targeted / extraction default and `run_alignment.py --resolver-mode` default.
- `run_alignment.py` keeps rewriting `region_first_safe_merge` to `local_minimum`
  for untargeted alignment production peak picking.
- Safe-merge failed-gate reasons are emitted as additive candidate audit data.

## Verified

- List exact pytest / py_compile commands and results.

## Not Yet Production Ready

- 8RAW strict ISTD benchmark not run in this implementation slice.
- 85RAW cohort validation not run.
- Identity coherence gate not run.

## Next Gate

Run the P1 acceptance commands from the spec and record GO / NO-GO separately.
```

- [ ] **Step 2: Do not mark `production_ready`**

The note stays `diagnostic_only` until real-data gates run.

---

## Final Acceptance

P1 implementation is ready for real-data validation when:

- focused pytest shard passes
- compile smoke passes
- `peak_candidates.tsv` schema change is intentional and documented
- implementation note exists with `diagnostic_only`
- post-implementation review has run and any actionable findings are fixed
- no Cleanup C-spec code has been touched

Do not proceed to P2 until P1 real-data validation has a GO / NO-GO note.
