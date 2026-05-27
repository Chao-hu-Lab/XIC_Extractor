# P1 Resolver Default Real-Data Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run and document the P1 real-data validation gate for the `region_first_safe_merge` default switch before any P2 implementation begins.

**Architecture:** Add one small diagnostic CLI to summarize the P1-specific targeted 8RAW area/RT acceptance metrics, then run existing validation harnesses and diagnostics for targeted output, untargeted alignment, identity coherence, and area uncertainty. Keep production behavior untouched; this plan only adds validation tooling and decision notes.

**Tech Stack:** Python, argparse, csv/json, pytest, existing validation harnesses, existing diagnostics under `tools/diagnostics/`, PowerShell commands on Windows.

**Spec:** `docs/superpowers/specs/2026-05-24-peak-pipeline-resolver-default-switch-spec.md`

---

## Execution Rules

1. Work only in `C:\Users\user\Desktop\XIC_Extractor\.worktrees\peak-pipeline-modernization`.
2. Do not implement Cleanup C-specs.
3. Do not start P2 until this plan records a P1 GO / NO-GO / inconclusive validation note.
4. Do not change resolver behavior, scoring weights, safe-merge thresholds, or public TSV schemas in this validation slice.
5. Do not start implementation until this plan has passed review and any actionable findings have been patched into the plan.
6. After executing this plan, run a post-implementation review against the plan, P1 spec, AGENTS.md contract, public surfaces, generated artifacts, and test coverage. Fix any actionable issue before declaring this validation slice complete.
7. Use module-mode commands (`python -m ...`) for scripts under `scripts/` and `tools/diagnostics/` so repo imports resolve from the worktree.
8. If RAW/DLL paths are missing or real-data commands fail due to environment, stop and write an `inconclusive` note with the exact failing command and error.

---

## Review Gates

### Plan Review Gate

Before Task 1 starts, review this plan against:

- P1 validation contract lines 73-91 in `2026-05-24-peak-pipeline-resolver-default-switch-spec.md`
- modernization overview order: P1 validation before P2
- existing diagnostic CLI interfaces verified by `--help`
- AGENTS.md gate-language requirement
- output paths under task-specific `output/phase1_p1_resolver_default_validation/`

Patch any finding into this file before code or real-data commands run.

### Initial Plan Review Result

Reviewed before implementation on 2026-05-24 against the P1 spec, modernization
overview, live `--help` output for planned CLIs, and AGENTS.md gate-language
rules. Findings patched into this plan:

- The validation note task now uses a concrete `NOT_RUN` ledger instead of
  editable placeholder text.
- The area-uncertainty baseline is pinned to
  `docs/superpowers/specs/2026-05-18-area-integration-uncertainty-decision.md`,
  where `boundary_sensitive = 1` and `unexplained_area_mismatch = 0`.
- Targeted reliability, strict ISTD benchmark, evidence-spine, and
  area-uncertainty steps now include exact machine checks.
- The reviewed 8RAW controls manifest was not present in this worktree during
  initial plan review. The 2026-05-25 gate repair supplied the accepted
  V0.4-reviewed manifest before the final identity-coherence gate, so the run
  may become `production_candidate` if the strict reviewed-controls rerun and
  pre-change identity-family comparison pass.

### Post-Implementation Review Gate

After all tasks finish, perform a code-review-style pass:

- Did the new diagnostic report only read existing outputs and avoid production mutation?
- Did all real-data outputs live under `output/phase1_p1_resolver_default_validation/`?
- Did the decision note use one explicit gate status: `production_candidate`, `diagnostic_only`, or `inconclusive`?
- Did any Cleanup C-spec code or P2 code get touched?
- Did focused tests and compile/import smoke pass?

Fix actionable findings immediately.

---

## Files And Responsibilities

- `tools/diagnostics/p1_resolver_default_gate.py` — new read-only diagnostic CLI for comparing baseline vs candidate targeted 8RAW ISTD area RSD and RT median shift.
- `tests/test_p1_resolver_default_gate.py` — deterministic tests for the new diagnostic.
- `docs/superpowers/notes/2026-05-24-resolver-default-switch-validation-note.md` — final P1 real-data gate note.
- Existing real-data outputs under `output/phase1_p1_resolver_default_validation/` — generated artifacts only, not staged unless explicitly requested.

---

## Acceptance Rules

The validation note records `Gate status: production_candidate` only if all of these are true:

- targeted 8RAW baseline and candidate runs complete
- every ISTD row has `area_rsd_delta_pct <= 0.5`
- every ISTD row has `rt_median_abs_delta_sec <= 0.5`
- `d3-N6-medA` is present in the targeted comparison and has no targeted reliability regression
- untargeted local-minimum and region-first-safe-merge alignment runs complete
- strict targeted ISTD benchmark has no new active failures in the candidate run
- identity coherence sidecar parity passes
- identity coherence controls / decoy verdicts pass against a reviewed 8RAW
  controls manifest
- identity-family count comparison against a pre-change 8RAW baseline is
  available and within +/- 2; if the pre-change baseline is not available, the
  gate cannot be stronger than `inconclusive`
- area integration uncertainty audit reports `unexplained_area_mismatch == 0`
- area uncertainty summary has `unexplained_area_mismatch_count == 0`
- area uncertainty `boundary_sensitive` count is `<= 2`, using the 2026-05-18
  baseline note value `boundary_sensitive = 1`

If any required command fails, a required reviewed controls manifest is absent,
or the pre-change identity-family baseline is absent, record
`Gate status: inconclusive` and do not proceed to P2.

If required real-data commands run and produce an acceptance failure, record
`Gate status: diagnostic_only` with `P1 default switch decision: NO-GO`. This
is stronger than `inconclusive`: the evidence is usable, but it blocks
promotion.

---

## Task 1 — Diagnostic CLI For P1 Targeted Area/RT Gate

**Files:**

- Create: `tests/test_p1_resolver_default_gate.py`
- Create: `tools/diagnostics/p1_resolver_default_gate.py`

- [x] **Step 1: Write tests for pass/fail area RSD and RT gates**

Create `tests/test_p1_resolver_default_gate.py` with:

```python
import csv
import json
from pathlib import Path

from tools.diagnostics import p1_resolver_default_gate as gate


def test_p1_gate_passes_stable_istd_area_and_rt(tmp_path: Path) -> None:
    targets = tmp_path / "targets.csv"
    _write_targets(targets)
    baseline = tmp_path / "baseline.csv"
    candidate = tmp_path / "candidate.csv"
    _write_results(
        baseline,
        [
            ("S1", 100.0, 10.0, 50.0, 8.0),
            ("S2", 110.0, 10.0, 52.0, 8.0),
            ("S3", 120.0, 10.0, 54.0, 8.0),
        ],
    )
    _write_results(
        candidate,
        [
            ("S1", 100.5, 10.001, 51.0, 8.0),
            ("S2", 110.5, 10.001, 52.5, 8.0),
            ("S3", 120.5, 10.001, 54.5, 8.0),
        ],
    )

    outputs, result = gate.run_p1_resolver_default_gate(
        baseline_results_csv=baseline,
        candidate_results_csv=candidate,
        targets_csv=targets,
        output_dir=tmp_path / "gate",
    )

    assert result.overall_status == "PASS"
    assert result.failed_count == 0
    assert outputs.summary_tsv.is_file()
    payload = json.loads(outputs.json_path.read_text(encoding="utf-8"))
    assert payload["overall_status"] == "PASS"


def test_p1_gate_fails_when_istd_rsd_regresses(tmp_path: Path) -> None:
    targets = tmp_path / "targets.csv"
    _write_targets(targets)
    baseline = tmp_path / "baseline.csv"
    candidate = tmp_path / "candidate.csv"
    _write_results(
        baseline,
        [
            ("S1", 100.0, 10.0, 50.0, 8.0),
            ("S2", 100.0, 10.0, 50.0, 8.0),
            ("S3", 100.0, 10.0, 50.0, 8.0),
        ],
    )
    _write_results(
        candidate,
        [
            ("S1", 80.0, 10.0, 50.0, 8.0),
            ("S2", 100.0, 10.0, 50.0, 8.0),
            ("S3", 120.0, 10.0, 50.0, 8.0),
        ],
    )

    _outputs, result = gate.run_p1_resolver_default_gate(
        baseline_results_csv=baseline,
        candidate_results_csv=candidate,
        targets_csv=targets,
        output_dir=tmp_path / "gate",
    )

    row = next(row for row in result.rows if row.target_label == "ISTD_A")
    assert row.status == "FAIL"
    assert "area_rsd_regression" in row.failure_reasons
    assert result.overall_status == "FAIL"


def test_main_writes_outputs_and_returns_failure_code(tmp_path: Path) -> None:
    targets = tmp_path / "targets.csv"
    _write_targets(targets)
    baseline = tmp_path / "baseline.csv"
    candidate = tmp_path / "candidate.csv"
    _write_results(
        baseline,
        [("S1", 100.0, 10.0, 50.0, 8.0), ("S2", 100.0, 10.0, 50.0, 8.0)],
    )
    _write_results(
        candidate,
        [("S1", 100.0, 10.02, 50.0, 8.0), ("S2", 100.0, 10.02, 50.0, 8.0)],
    )
    output_dir = tmp_path / "gate"

    code = gate.main(
        [
            "--baseline-results-csv",
            str(baseline),
            "--candidate-results-csv",
            str(candidate),
            "--targets-csv",
            str(targets),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert code == 1
    assert (output_dir / "p1_resolver_default_gate_rows.tsv").is_file()
    assert (output_dir / "p1_resolver_default_gate_summary.tsv").is_file()
    assert (output_dir / "p1_resolver_default_gate.json").is_file()
    assert (output_dir / "p1_resolver_default_gate.md").is_file()


def _write_targets(path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("label", "mz", "is_istd"),
        )
        writer.writeheader()
        writer.writerow({"label": "ISTD_A", "mz": "100.0", "is_istd": "TRUE"})
        writer.writerow({"label": "Analyte", "mz": "101.0", "is_istd": "FALSE"})
        writer.writerow({"label": "ISTD_B", "mz": "102.0", "is_istd": "TRUE"})


def _write_results(path: Path, rows: list[tuple[str, float, float, float, float]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "SampleName",
                "ISTD_A_Area",
                "ISTD_A_RT",
                "ISTD_B_Area",
                "ISTD_B_RT",
                "Analyte_Area",
                "Analyte_RT",
            ),
        )
        writer.writeheader()
        for sample, istd_a_area, istd_a_rt, istd_b_area, istd_b_rt in rows:
            writer.writerow(
                {
                    "SampleName": sample,
                    "ISTD_A_Area": istd_a_area,
                    "ISTD_A_RT": istd_a_rt,
                    "ISTD_B_Area": istd_b_area,
                    "ISTD_B_RT": istd_b_rt,
                    "Analyte_Area": "999",
                    "Analyte_RT": "1.0",
                }
            )
```

- [x] **Step 2: Run tests and confirm they fail**

Run:

```powershell
python -m pytest tests\test_p1_resolver_default_gate.py -q
```

Expected before implementation: import failure because `tools.diagnostics.p1_resolver_default_gate` does not exist.

- [x] **Step 3: Implement the diagnostic CLI**

Create `tools/diagnostics/p1_resolver_default_gate.py` with these public names:

```python
from __future__ import annotations

import argparse
import csv
import json
import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class P1GateOutputs:
    rows_tsv: Path
    summary_tsv: Path
    json_path: Path
    markdown_path: Path


@dataclass(frozen=True)
class P1GateRow:
    target_label: str
    sample_count: int
    baseline_area_rsd_pct: float | None
    candidate_area_rsd_pct: float | None
    area_rsd_delta_pct: float | None
    rt_median_abs_delta_sec: float | None
    status: str
    failure_reasons: tuple[str, ...]


@dataclass(frozen=True)
class P1GateResult:
    overall_status: str
    failed_count: int
    max_area_rsd_delta_pct: float | None
    max_rt_median_abs_delta_sec: float | None
    rows: tuple[P1GateRow, ...]
```

Implement:

```python
def run_p1_resolver_default_gate(
    *,
    baseline_results_csv: Path,
    candidate_results_csv: Path,
    targets_csv: Path,
    output_dir: Path,
    max_rsd_regression_pct: float = 0.5,
    max_rt_median_shift_sec: float = 0.5,
) -> tuple[P1GateOutputs, P1GateResult]:
    ...
```

Implementation requirements:

- read `targets_csv` and include only rows with `is_istd` parsed as true
- read result rows by `SampleName`
- for each ISTD, read `<label>_Area` and `<label>_RT` from both result files
- compare only samples present in both files
- compute area RSD as sample standard deviation divided by mean, multiplied by 100
- compute `area_rsd_delta_pct = candidate_area_rsd_pct - baseline_area_rsd_pct`
- compute `rt_median_abs_delta_sec = median(abs(candidate_rt - baseline_rt)) * 60`
- mark `FAIL` when `area_rsd_delta_pct > 0.5`
- mark `FAIL` when `rt_median_abs_delta_sec > 0.5`
- mark `FAIL` when fewer than two paired samples are available
- output:
  - `p1_resolver_default_gate_rows.tsv`
  - `p1_resolver_default_gate_summary.tsv`
  - `p1_resolver_default_gate.json`
  - `p1_resolver_default_gate.md`
- `main(argv)` returns `0` on `PASS`, `1` on metric failure, and `2` for missing input/columns or parse errors

- [x] **Step 4: Run focused diagnostic tests**

Run:

```powershell
python -m pytest tests\test_p1_resolver_default_gate.py -q
```

Expected: pass.

---

## Task 2 — Targeted 8RAW Baseline And Candidate Runs

**Files:** no source edits expected.

- [x] **Step 1: Preflight real-data paths**

Run:

```powershell
Test-Path "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation"
Test-Path "C:\Xcalibur\system\programs"
```

Expected:

```text
True
True
```

If either path is false, stop and write an `inconclusive` validation note.

- [x] **Step 2: Dry-run targeted baseline and candidate commands**

Run:

```powershell
python -m scripts.validation_harness `
  --suite tissue-8raw `
  --output-root output\phase1_p1_resolver_default_validation\targeted `
  --run-id local_minimum `
  --resolver-mode local_minimum `
  --setting emit_peak_candidates=true `
  --setting keep_intermediate_csv=true `
  --dry-run

python -m scripts.validation_harness `
  --suite tissue-8raw `
  --output-root output\phase1_p1_resolver_default_validation\targeted `
  --run-id region_first_safe_merge `
  --resolver-mode region_first_safe_merge `
  --setting emit_peak_candidates=true `
  --setting keep_intermediate_csv=true `
  --dry-run
```

Expected:

- baseline dry-run contains `--resolver-mode local_minimum`
- candidate dry-run contains `--resolver-mode region_first_safe_merge`
- both dry-runs include `--setting emit_peak_candidates=true`
- both dry-runs include `--setting keep_intermediate_csv=true` so downstream
  diagnostics can read `xic_results.csv`

- [x] **Step 3: Run targeted baseline and candidate**

Run:

```powershell
python -m scripts.validation_harness `
  --suite tissue-8raw `
  --output-root output\phase1_p1_resolver_default_validation\targeted `
  --run-id local_minimum `
  --resolver-mode local_minimum `
  --setting emit_peak_candidates=true `
  --setting keep_intermediate_csv=true

python -m scripts.validation_harness `
  --suite tissue-8raw `
  --output-root output\phase1_p1_resolver_default_validation\targeted `
  --run-id region_first_safe_merge `
  --resolver-mode region_first_safe_merge `
  --setting emit_peak_candidates=true `
  --setting keep_intermediate_csv=true
```

Expected artifacts:

- `output\phase1_p1_resolver_default_validation\targeted\local_minimum\tissue_8raw_local_minimum\xic_results.csv`
- `output\phase1_p1_resolver_default_validation\targeted\local_minimum\tissue_8raw_local_minimum\xic_results_process_w4.xlsx`
- `output\phase1_p1_resolver_default_validation\targeted\local_minimum\tissue_8raw_local_minimum\peak_candidates.tsv`
- `output\phase1_p1_resolver_default_validation\targeted\local_minimum\tissue_8raw_local_minimum\peak_candidate_boundaries.tsv`
- `output\phase1_p1_resolver_default_validation\targeted\region_first_safe_merge\tissue_8raw_region_first_safe_merge\xic_results.csv`
- `output\phase1_p1_resolver_default_validation\targeted\region_first_safe_merge\tissue_8raw_region_first_safe_merge\xic_results_process_w4.xlsx`
- `output\phase1_p1_resolver_default_validation\targeted\region_first_safe_merge\tissue_8raw_region_first_safe_merge\peak_candidates.tsv`
- `output\phase1_p1_resolver_default_validation\targeted\region_first_safe_merge\tissue_8raw_region_first_safe_merge\peak_candidate_boundaries.tsv`

If either run fails, stop and write an `inconclusive` validation note.

---

## Task 3 — Targeted Comparison, Reliability, And P1 Area/RT Gate

**Files:** no source edits expected after Task 1.

- [x] **Step 1: Run targeted safe-merge comparison**

Run:

```powershell
python -m tools.diagnostics.region_first_safe_merge_comparison `
  --default-dir output\phase1_p1_resolver_default_validation\targeted\local_minimum\tissue_8raw_local_minimum `
  --safe-merge-dir output\phase1_p1_resolver_default_validation\targeted\region_first_safe_merge\tissue_8raw_region_first_safe_merge `
  --targets-csv config\targets.example.csv `
  --output-dir output\phase1_p1_resolver_default_validation\diagnostics\targeted_comparison
```

Expected:

- `output\phase1_p1_resolver_default_validation\diagnostics\targeted_comparison\region_first_safe_merge_comparison.tsv`
- markdown summary names changed targets and includes `d3-N6-medA` if it changed

- [x] **Step 2: Run targeted reliability audits**

Run:

```powershell
python -m tools.diagnostics.targeted_peak_reliability_audit `
  --targeted-workbook output\phase1_p1_resolver_default_validation\targeted\local_minimum\tissue_8raw_local_minimum\xic_results_process_w4.xlsx `
  --peak-candidates-tsv output\phase1_p1_resolver_default_validation\targeted\local_minimum\tissue_8raw_local_minimum\peak_candidates.tsv `
  --known-target-exception d3-N6-medA:AREA_MISMATCH `
  --output-dir output\phase1_p1_resolver_default_validation\diagnostics\targeted_reliability_local_minimum

python -m tools.diagnostics.targeted_peak_reliability_audit `
  --targeted-workbook output\phase1_p1_resolver_default_validation\targeted\region_first_safe_merge\tissue_8raw_region_first_safe_merge\xic_results_process_w4.xlsx `
  --peak-candidates-tsv output\phase1_p1_resolver_default_validation\targeted\region_first_safe_merge\tissue_8raw_region_first_safe_merge\peak_candidates.tsv `
  --known-target-exception d3-N6-medA:AREA_MISMATCH `
  --output-dir output\phase1_p1_resolver_default_validation\diagnostics\targeted_reliability_region_first_safe_merge
```

Expected:

- both commands exit 0
- both output `targeted_peak_reliability.json`
- candidate summary must not increase `targeted_negative_count` for ISTDs

- [x] **Step 3: Check ISTD targeted-negative regression**

Run:

```powershell
@'
import csv
from pathlib import Path

targets_path = Path("config/targets.example.csv")
baseline_path = Path("output/phase1_p1_resolver_default_validation/diagnostics/targeted_reliability_local_minimum/targeted_peak_reliability_summary.tsv")
candidate_path = Path("output/phase1_p1_resolver_default_validation/diagnostics/targeted_reliability_region_first_safe_merge/targeted_peak_reliability_summary.tsv")

with targets_path.open(newline="", encoding="utf-8-sig") as handle:
    istd_labels = {
        row["label"]
        for row in csv.DictReader(handle)
        if str(row.get("is_istd", "")).strip().upper() in {"1", "TRUE", "YES", "Y"}
    }

def read_counts(path: Path) -> dict[str, int]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return {
            row["target_label"]: int(row.get("targeted_negative_count") or 0)
            for row in csv.DictReader(handle, delimiter="\t")
            if row.get("target_label") in istd_labels
        }

baseline = read_counts(baseline_path)
candidate = read_counts(candidate_path)
regressions = [
    f"{label}:{baseline.get(label, 0)}->{candidate.get(label, 0)}"
    for label in sorted(istd_labels)
    if candidate.get(label, 0) > baseline.get(label, 0)
]
if regressions:
    raise SystemExit("FAIL targeted_reliability_istd_negative_count " + ";".join(regressions))
print(f"PASS targeted_reliability_istd_negative_count checked={len(istd_labels)}")
'@ | python -
```

Expected:

```text
PASS targeted_reliability_istd_negative_count checked=<ISTD count>
```

- [x] **Step 4: Run P1 area RSD / RT shift gate**

Run:

```powershell
python -m tools.diagnostics.p1_resolver_default_gate `
  --baseline-results-csv output\phase1_p1_resolver_default_validation\targeted\local_minimum\tissue_8raw_local_minimum\xic_results.csv `
  --candidate-results-csv output\phase1_p1_resolver_default_validation\targeted\region_first_safe_merge\tissue_8raw_region_first_safe_merge\xic_results.csv `
  --targets-csv config\targets.example.csv `
  --output-dir output\phase1_p1_resolver_default_validation\diagnostics\p1_area_rt_gate
```

Expected:

- exit code 0 for GO
- `p1_resolver_default_gate_rows.tsv` has one row per ISTD
- max `area_rsd_delta_pct` is `<= 0.5`
- max `rt_median_abs_delta_sec` is `<= 0.5`

If this command exits 1, continue only to write a NO-GO note; do not proceed to P2.

---

## Task 4 — Untargeted Alignment, ISTD Benchmark, And Area Uncertainty

**Files:** no source edits expected.

- [x] **Step 1: Run 8RAW discovery once**

Run:

```powershell
python -m scripts.run_discovery `
  --raw-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" `
  --dll-dir "C:\Xcalibur\system\programs" `
  --output-dir output\phase1_p1_resolver_default_validation\discovery\dR `
  --neutral-loss-tag DNA_dR `
  --neutral-loss-da 116.0474 `
  --resolver-mode local_minimum
```

Expected:

- `output\phase1_p1_resolver_default_validation\discovery\dR\discovery_batch_index.csv`

- [x] **Step 2: Run local-minimum and region-first alignment**

Run:

```powershell
python -m scripts.run_alignment `
  --discovery-batch-index output\phase1_p1_resolver_default_validation\discovery\dR\discovery_batch_index.csv `
  --raw-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" `
  --dll-dir "C:\Xcalibur\system\programs" `
  --output-dir output\phase1_p1_resolver_default_validation\alignment\local_minimum `
  --resolver-mode local_minimum `
  --performance-profile validation-fast `
  --emit-alignment-cells `
  --emit-alignment-integration-audit `
  --emit-alignment-status-matrix

python -m scripts.run_alignment `
  --discovery-batch-index output\phase1_p1_resolver_default_validation\discovery\dR\discovery_batch_index.csv `
  --raw-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" `
  --dll-dir "C:\Xcalibur\system\programs" `
  --output-dir output\phase1_p1_resolver_default_validation\alignment\region_first_safe_merge `
  --resolver-mode region_first_safe_merge `
  --performance-profile validation-fast `
  --emit-alignment-cells `
  --emit-alignment-integration-audit `
  --emit-alignment-status-matrix
```

Expected:

- both commands exit 0
- both output `alignment_matrix.tsv`, `alignment_review.tsv`, `alignment_cells.tsv`, and `alignment_cell_integration_audit.tsv`

- [x] **Step 3: Run strict targeted ISTD benchmark for both alignments**

Run:

```powershell
python -m tools.diagnostics.targeted_istd_benchmark `
  --targeted-workbook output\phase1_p1_resolver_default_validation\targeted\local_minimum\tissue_8raw_local_minimum\xic_results_process_w4.xlsx `
  --alignment-dir output\phase1_p1_resolver_default_validation\alignment\local_minimum `
  --targeted-reliability-json output\phase1_p1_resolver_default_validation\diagnostics\targeted_reliability_local_minimum\targeted_peak_reliability.json `
  --strict-targeted-reliability `
  --output-dir output\phase1_p1_resolver_default_validation\diagnostics\untargeted_istd_benchmark_local_minimum

python -m tools.diagnostics.targeted_istd_benchmark `
  --targeted-workbook output\phase1_p1_resolver_default_validation\targeted\region_first_safe_merge\tissue_8raw_region_first_safe_merge\xic_results_process_w4.xlsx `
  --alignment-dir output\phase1_p1_resolver_default_validation\alignment\region_first_safe_merge `
  --targeted-reliability-json output\phase1_p1_resolver_default_validation\diagnostics\targeted_reliability_region_first_safe_merge\targeted_peak_reliability.json `
  --strict-targeted-reliability `
  --output-dir output\phase1_p1_resolver_default_validation\diagnostics\untargeted_istd_benchmark_region_first_safe_merge
```

Expected:

- candidate run has no new `active_fail_count` relative to baseline
- candidate `targeted_istd_benchmark_summary.tsv` does not introduce new ISTD `FAIL` rows

- [x] **Step 4: Check strict ISTD benchmark regression**

Run:

```powershell
@'
import json
from pathlib import Path

baseline_path = Path("output/phase1_p1_resolver_default_validation/diagnostics/untargeted_istd_benchmark_local_minimum/targeted_istd_benchmark.json")
candidate_path = Path("output/phase1_p1_resolver_default_validation/diagnostics/untargeted_istd_benchmark_region_first_safe_merge/targeted_istd_benchmark.json")

baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
candidate = json.loads(candidate_path.read_text(encoding="utf-8"))

baseline_active_fail = int(baseline.get("active_fail_count", 0))
candidate_active_fail = int(candidate.get("active_fail_count", 0))
if candidate_active_fail > baseline_active_fail:
    raise SystemExit(
        f"FAIL targeted_istd_active_fail_count {baseline_active_fail}->{candidate_active_fail}"
    )

def active_fail_labels(payload: dict) -> set[str]:
    labels = set()
    for row in payload.get("summaries", []):
        if (
            str(row.get("active_tag", "")).upper() == "TRUE"
            and row.get("status") == "FAIL"
        ):
            labels.add(str(row.get("target_label", "")))
    return labels

new_failures = sorted(active_fail_labels(candidate) - active_fail_labels(baseline))
if new_failures:
    raise SystemExit("FAIL targeted_istd_new_active_failures " + ";".join(new_failures))
print(
    "PASS targeted_istd_benchmark_regression "
    f"active_fail_count={candidate_active_fail} baseline={baseline_active_fail}"
)
'@ | python -
```

Expected:

```text
PASS targeted_istd_benchmark_regression active_fail_count=<candidate> baseline=<baseline>
```

If this check fails, stop the remaining real-data tasks, write the validation
note with `Gate status: diagnostic_only`, and record the failing target label
and failure mode. Do not proceed to P2.

- [ ] **Step 5: Run evidence spine consistency**

Run:

```powershell
python -m tools.diagnostics.evidence_spine_consistency `
  --targeted-dir output\phase1_p1_resolver_default_validation\targeted\region_first_safe_merge\tissue_8raw_region_first_safe_merge `
  --alignment-dir output\phase1_p1_resolver_default_validation\alignment\region_first_safe_merge `
  --output-dir output\phase1_p1_resolver_default_validation\diagnostics\evidence_spine_consistency
```

Expected:

- `evidence_spine_consistency_rows.tsv` exists
- `d3-N6-medA` rows are present
- `d3-N6-medA` mismatch reason is `consistent` for rows that were previously consistent

- [ ] **Step 6: Check d3-N6-medA evidence-spine consistency**

Run:

```powershell
@'
import csv
from pathlib import Path

rows_path = Path("output/phase1_p1_resolver_default_validation/diagnostics/evidence_spine_consistency/evidence_spine_consistency_rows.tsv")
with rows_path.open(newline="", encoding="utf-8-sig") as handle:
    rows = [row for row in csv.DictReader(handle, delimiter="\t") if row.get("target_label") == "d3-N6-medA"]
if not rows:
    raise SystemExit("FAIL evidence_spine_d3_N6_medA missing_rows")
bad = [
    f"{row.get('sample', '')}:{row.get('mismatch_reason', '')}"
    for row in rows
    if row.get("mismatch_reason") != "consistent"
]
if bad:
    raise SystemExit("FAIL evidence_spine_d3_N6_medA " + ";".join(bad))
print(f"PASS evidence_spine_d3_N6_medA consistent_rows={len(rows)}")
'@ | python -
```

Expected:

```text
PASS evidence_spine_d3_N6_medA consistent_rows=<row count>
```

- [ ] **Step 7: Run area integration uncertainty audit**

Run:

```powershell
python -m tools.diagnostics.area_integration_uncertainty_audit `
  --evidence-spine-rows-tsv output\phase1_p1_resolver_default_validation\diagnostics\evidence_spine_consistency\evidence_spine_consistency_rows.tsv `
  --targeted-peak-candidates-tsv output\phase1_p1_resolver_default_validation\targeted\region_first_safe_merge\tissue_8raw_region_first_safe_merge\peak_candidates.tsv `
  --targeted-boundaries-tsv output\phase1_p1_resolver_default_validation\targeted\region_first_safe_merge\tissue_8raw_region_first_safe_merge\peak_candidate_boundaries.tsv `
  --alignment-integration-audit-tsv output\phase1_p1_resolver_default_validation\alignment\region_first_safe_merge\alignment_cell_integration_audit.tsv `
  --output-dir output\phase1_p1_resolver_default_validation\diagnostics\area_integration_uncertainty
```

Expected:

- `area_integration_uncertainty_summary.tsv` exists
- `unexplained_area_mismatch` count is `0`
- `boundary_sensitive` count is `<= 2` relative to the 2026-05-18 baseline
  value `boundary_sensitive = 1`

- [ ] **Step 8: Check area integration uncertainty acceptance**

Run:

```powershell
@'
import csv
from pathlib import Path

summary_path = Path("output/phase1_p1_resolver_default_validation/diagnostics/area_integration_uncertainty/area_integration_uncertainty_summary.tsv")
with summary_path.open(newline="", encoding="utf-8-sig") as handle:
    row = next(csv.DictReader(handle, delimiter="\t"))

unexplained = int(row.get("unexplained_area_mismatch_count") or 0)
if unexplained != 0:
    raise SystemExit(f"FAIL unexplained_area_mismatch_count={unexplained}")

bucket_counts = {}
for item in str(row.get("bucket_counts", "")).split(";"):
    if not item:
        continue
    label, count = item.split(":", 1)
    bucket_counts[label] = int(count)

boundary_sensitive = bucket_counts.get("boundary_sensitive", 0)
if boundary_sensitive > 2:
    raise SystemExit(f"FAIL boundary_sensitive={boundary_sensitive} baseline=1 max=2")
print(
    "PASS area_integration_uncertainty "
    f"unexplained_area_mismatch_count={unexplained} boundary_sensitive={boundary_sensitive}"
)
'@ | python -
```

Expected:

```text
PASS area_integration_uncertainty unexplained_area_mismatch_count=0 boundary_sensitive=<0-2>
```

---

## Task 5 — Identity Coherence Gate

**Files:** no source edits expected.

- [ ] **Step 1: Record identity coherence preflight**

Run:

```powershell
$reviewedManifest = "output\phase1_p1_resolver_default_validation\identity_coherence_hotfix\identity_coherence_controls_manifest_8raw.reviewed.tsv"
$prechangeDecisions = "output\phase1_p1_resolver_default_validation\identity_coherence_prechange\serial\identity_coherence\untargeted_identity_coherence_decisions.tsv"
Write-Output "reviewed_manifest_exists=$(Test-Path $reviewedManifest)"
Write-Output "prechange_decisions_exists=$(Test-Path $prechangeDecisions)"
```

Expected after the 2026-05-25 gate repair:

```text
reviewed_manifest_exists=True
prechange_decisions_exists=True
```

If either remains false after Task 5, the P1 validation decision must be
`inconclusive`. Continue running sidecar parity so the note records useful
evidence, but do not mark the gate `production_candidate`.

- [ ] **Step 2: Run sidecar parity and controls proposal**

Run:

```powershell
python -m scripts.validate_identity_coherence_8raw `
  --discovery-batch-index output\phase1_p1_resolver_default_validation\discovery\dR\discovery_batch_index.csv `
  --raw-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" `
  --dll-dir "C:\Xcalibur\system\programs" `
  --output-root output\phase1_p1_resolver_default_validation\identity_coherence `
  --write-controls-manifest-proposal output\phase1_p1_resolver_default_validation\identity_coherence\identity_coherence_controls_manifest_8raw.proposed.tsv
```

Expected:

- stdout contains `PASS identity_coherence_sidecar_parity`
- proposal TSV is written

- [ ] **Step 3: Run reviewed-controls gate only when reviewed manifest exists**

Run:

```powershell
$reviewedManifest = "output\phase1_p1_resolver_default_validation\identity_coherence_hotfix\identity_coherence_controls_manifest_8raw.reviewed.tsv"
if (Test-Path $reviewedManifest) {
  .\.venv\Scripts\python.exe -m scripts.validate_identity_coherence_8raw `
    --discovery-batch-index output\phase1_p1_resolver_default_validation\discovery\dR\discovery_batch_index.csv `
    --raw-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" `
    --dll-dir "C:\Xcalibur\system\programs" `
    --output-root output\phase1_p1_resolver_default_validation\identity_coherence_hotfix_reviewed `
    --controls-manifest $reviewedManifest `
    --require-v04-acceptance
} else {
  Write-Output "INCONCLUSIVE reviewed controls manifest missing: $reviewedManifest"
}
```

Expected:

- if the reviewed manifest exists, stdout contains `PASS identity_coherence_v04_acceptance`
- if it does not exist, the P1 validation decision must be `inconclusive`

- [ ] **Step 4: Compare identity-family count only when pre-change baseline exists**

Run:

```powershell
@'
import csv
from pathlib import Path

baseline_path = Path("output/phase1_p1_resolver_default_validation/identity_coherence_prechange/serial/identity_coherence/untargeted_identity_coherence_decisions.tsv")
candidate_path = Path("output/phase1_p1_resolver_default_validation/identity_coherence_hotfix_reviewed/serial/identity_coherence/untargeted_identity_coherence_decisions.tsv")

if not baseline_path.is_file():
    print(f"INCONCLUSIVE identity_family_prechange_baseline_missing: {baseline_path}")
    raise SystemExit(0)
if not candidate_path.is_file():
    raise SystemExit(f"FAIL identity_family_candidate_missing: {candidate_path}")

def family_count(path: Path) -> int:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = csv.DictReader(handle, delimiter="\t")
        return len({row.get("identity_family_id", "") for row in rows if row.get("identity_family_id", "")})

baseline = family_count(baseline_path)
candidate = family_count(candidate_path)
delta = candidate - baseline
if abs(delta) > 2:
    raise SystemExit(f"FAIL identity_family_count baseline={baseline} candidate={candidate} delta={delta}")
print(f"PASS identity_family_count baseline={baseline} candidate={candidate} delta={delta}")
'@ | python -
```

Expected after the 2026-05-25 gate repair:

```text
PASS identity_family_count baseline=2302 candidate=2302 delta=0
```

---

## Task 6 — Validation Note And Post-Run Review

**Files:**

- Create: `docs/superpowers/notes/2026-05-24-resolver-default-switch-validation-note.md`

- [x] **Step 1: Write the validation note**

Create / update `docs/superpowers/notes/2026-05-24-resolver-default-switch-validation-note.md`
with this final structure:

```markdown
# Resolver Default Switch Real-Data Validation Note

**Date:** 2026-05-24
**Branch:** codex/peak-pipeline-modernization
**Worktree:** .worktrees/peak-pipeline-modernization
**Gate status:** production_candidate

## Decision

- P1 default switch decision: GO_FOR_P2_ENTRY
- Scope: 8RAW method / P2-entry only; not 85RAW or production_ready.

## Artifacts

- Targeted local-minimum: `output/phase1_p1_resolver_default_validation/targeted/local_minimum/tissue_8raw_local_minimum/`
- Targeted region-first-safe-merge: `output/phase1_p1_resolver_default_validation/targeted/region_first_safe_merge/tissue_8raw_region_first_safe_merge/`
- Targeted comparison: `output/phase1_p1_resolver_default_validation/diagnostics/targeted_comparison/`
- P1 area/RT gate: `output/phase1_p1_resolver_default_validation/diagnostics/p1_area_rt_gate/`
- Untargeted local-minimum alignment: `output/phase1_p1_resolver_default_validation/alignment/local_minimum/`
- Untargeted region-first-safe-merge alignment: `output/phase1_p1_resolver_default_validation/alignment/region_first_safe_merge/`
- ISTD benchmark local-minimum: `output/phase1_p1_resolver_default_validation/diagnostics/untargeted_istd_benchmark_local_minimum/`
- ISTD benchmark region-first-safe-merge: `output/phase1_p1_resolver_default_validation/diagnostics/untargeted_istd_benchmark_region_first_safe_merge/`
- Evidence spine consistency: `output/phase1_p1_resolver_default_validation/diagnostics/evidence_spine_consistency/`
- Area integration uncertainty: `output/phase1_p1_resolver_default_validation/diagnostics/area_integration_uncertainty/`
- Hotfix reviewed identity coherence: `output/phase1_p1_resolver_default_validation/identity_coherence_hotfix_reviewed/`
- Reviewed controls manifest: `output/phase1_p1_resolver_default_validation/identity_coherence_hotfix/identity_coherence_controls_manifest_8raw.reviewed.tsv`
- Pre-change identity-family baseline: `output/phase1_p1_resolver_default_validation/identity_coherence_prechange/serial/identity_coherence/untargeted_identity_coherence_decisions.tsv`

## Gate Results

| Gate | Result | Evidence |
|---|---|---|
| Targeted 8RAW runs | PASS | validation summaries written for local-minimum and region-first-safe-merge targeted runs |
| Area RSD / RT shift | PASS | hotfix gate summary: `overall_status=PASS`, `failed_count=0` |
| Targeted reliability | PASS_WITH_WARNINGS | reliability audits exited 0; ISTD targeted negative count regression passed |
| Untargeted alignment | PASS | hotfix alignment output written under `alignment/region_first_safe_merge_hotfix/` |
| Strict ISTD benchmark | PASS | hotfix candidate `active_fail_count=0` |
| Evidence spine d3-N6-medA consistency | PASS_WITH_WARNINGS | same-surface probe passes; mixed-surface mismatch is diagnostic-only |
| Area integration uncertainty | PASS | `unexplained_area_mismatch_count=0`, `boundary_sensitive=1` |
| Identity coherence sidecar parity | PASS | serial/process sidecars exact-match |
| Reviewed controls / decoys | PASS | V0.4 reviewed manifest supplied; 5/5 positives passed and 3/3 decoys rejected |
| Identity-family pre-change count | PASS | baseline rows `2302`, candidate rows `2302`, byte-identical decisions |

## Review

- Post-run review status: completed.
- Findings fixed: stale gate wording and missing reviewed-controls / baseline
  evidence references were patched.

## Next Step

- P2 plan may be written next.
- Cleanup C-spec implementation remains on hold.
```

Update every executed gate row from `NOT_RUN` to `PASS`, `FAIL`, or
`INCONCLUSIVE` before closing the task. The final gate status may be:

- `production_candidate` only when every required gate passes and reviewed controls exist
- `diagnostic_only` when real-data commands produced a NO-GO acceptance failure,
  or when real-data commands were not executed at all
- `inconclusive` when the reviewed controls manifest is missing, a real-data command cannot run, or baseline evidence is missing and no earlier NO-GO metric exists

- [x] **Step 2: Run focused verification**

Run:

```powershell
python -m pytest tests\test_p1_resolver_default_gate.py tests\test_validation_harness.py tests\test_run_alignment.py tests\test_targeted_peak_reliability_audit.py tests\test_targeted_istd_benchmark.py tests\test_area_integration_uncertainty_audit.py tests\test_validate_identity_coherence_8raw.py -q

python -m py_compile tools\diagnostics\p1_resolver_default_gate.py scripts\validation_harness.py scripts\validation_harness_core.py scripts\run_alignment.py scripts\run_discovery.py scripts\validate_identity_coherence_8raw.py

git diff --check
```

Expected:

- pytest shard passes
- py_compile exits 0
- diff check exits 0

- [x] **Step 3: Run post-implementation review**

Review this validation slice against the plan and P1 spec:

- new diagnostic reads only CSV/TSV/JSON and writes under requested output dir
- no Cleanup C-spec implementation files were touched
- no P2 production code was touched
- note uses explicit gate language
- every real-data gate has an artifact path and PASS/FAIL/INCONCLUSIVE status

Fix actionable issues immediately, then rerun the focused verification commands in Step 2.

---

## Final Acceptance

This P1 validation slice is complete when:

- the plan has been reviewed and patched before Task 1 implementation
- `tools/diagnostics/p1_resolver_default_gate.py` has focused tests
- targeted 8RAW validation commands were run or an environment blocker was recorded
- untargeted 8RAW validation commands were run or an environment blocker was recorded
- identity coherence status was recorded
- area uncertainty status was recorded
- validation note exists with `production_candidate`, `diagnostic_only`, or `inconclusive`
- post-implementation review has run and actionable issues are fixed

Do not start P2 until the validation note records a P1 GO condition strong enough for the overview ordering rule.
