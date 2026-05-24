# Identity Coherence V0.4 Acceptance Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the final V0.4 acceptance layer for the identity coherence prototype so 8RAW parity, reviewed controls, and known out-of-scope boundaries are reported as one explicit Go/No-Go handoff.

**Architecture:** Keep the acceptance layer inside the existing standalone validator, `scripts/validate_identity_coherence_8raw.py`. It reads only the validator's own `ValidationResult` rows and frozen sidecar TSV outputs; it must not import alignment internals, RAW readers, Backfill, workbook code, final matrix code, or downstream filtering code. The acceptance layer summarizes readiness for method review, not 85RAW production execution.

**Tech Stack:** Python 3.11+, `argparse`, `csv`, `dataclasses`, `pathlib`, `pytest`, existing `scripts/validate_identity_coherence_8raw.py`, PowerShell.

---

## Scope Boundary

In scope:

- Add V0.4 acceptance rows and Markdown output to `scripts/validate_identity_coherence_8raw.py`.
- Add an opt-in CLI gate, `--require-v04-acceptance`, that exits non-zero unless acceptance passes.
- Add tests in `tests/test_validate_identity_coherence_8raw.py`.
- Run the existing 8RAW validator in acceptance mode if a reviewed controls manifest exists.

Out of scope:

- No changes to `xic_extractor/alignment/identity_coherence_adapter.py`.
- No changes to `xic_extractor/alignment/identity_coherence/`.
- No changes to RAW/XIC retrieval, process backend, Backfill, final matrix, workbook rendering, or downstream filtering.
- No automatic positive-control discovery or targeted ISTD mapping. Positive controls require a reviewed controls manifest.
- No 85RAW execution or 85RAW threshold policy.

This is a closure layer. It must not change identity decisions or sidecar TSV content.

## Output Contract

Existing validation outputs stay unchanged:

```text
output\identity_coherence_8raw_validation\identity_coherence_8raw_validation_summary.tsv
output\identity_coherence_8raw_validation\identity_coherence_8raw_validation_report.md
```

New acceptance outputs:

```text
output\identity_coherence_8raw_validation\identity_coherence_v04_acceptance.tsv
output\identity_coherence_8raw_validation\identity_coherence_v04_acceptance.md
```

Acceptance TSV columns:

```text
criterion
status
evidence
details
```

Allowed `status` values:

```text
pass
fail
not_assessed
```

Acceptance criteria:

| Criterion | Pass condition |
| --- | --- |
| `serial_process_sidecar_parity` | `requests_tsv_exact`, `decisions_tsv_exact`, `cell_evidence_tsv_exact`, `controls_tsv_parity_only`, and `summary_md_presence` are all `pass`. |
| `reviewed_controls_manifest` | `controls_manifest_assessment` reports `provided` and the supplied manifest path ends with `.reviewed.tsv`; `.proposed.tsv` paths are already rejected by the validator CLI. |
| `positive_control_sensitivity` | `positive_control_pass_fraction` is `pass`. |
| `identity_decoy_specificity` | `decoy_coherent_seed_count` is `pass` with both serial and process values equal to `0`, and `decoy_correctly_rejected_count` is `pass`. |
| `v04_acceptance` | All required criteria above are `pass`. |

If no `.reviewed.tsv` controls manifest is supplied, `serial_process_sidecar_parity` may pass but `v04_acceptance` must fail with a clear message. That is the intended state until the proposal is manually reviewed and positive controls are added.

### Behavior Change Note

Before this plan, default validator mode returned exit code `1` for any
`ValidationRow.status == "fail"`, including method-control rows such as
`positive_control_pass_fraction`, `decoy_coherent_seed_count`, and
`decoy_correctly_rejected_count`.

After this plan, default mode returns exit code `1` only when sidecar parity
fails. Method-control failures print `NO-GO identity_coherence_v04_acceptance`
and write acceptance TSV/Markdown, but return exit code `0` unless
`--require-v04-acceptance` is set. Existing wrappers or CI jobs that want
positive-control/decoy failure to be fatal must add `--require-v04-acceptance`.

## Files

- Modify: `scripts/validate_identity_coherence_8raw.py`
- Modify: `tests/test_validate_identity_coherence_8raw.py`

## Task 0: Preflight

**Files:** none.

- [ ] **Step 1: Confirm worktree status**

Run:

```powershell
Set-Location "C:\Users\user\Desktop\XIC_Extractor\.worktrees\untargeted-backfill-logic-reset"
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset status --short --branch
```

Expected: branch is `codex/untargeted-backfill-logic-reset`; no unrelated dirty tracked files.

- [ ] **Step 2: Confirm the current 8RAW validator still passes narrow tests**

Run:

```powershell
uv run pytest tests\test_validate_identity_coherence_8raw.py -q
```

Expected: PASS.

If `uv` fails because the sandbox cannot write to the global cache, keep the
cache inside this worktree and rerun the same command:

```powershell
New-Item -ItemType Directory -Force .uv-cache | Out-Null
$env:UV_CACHE_DIR = ".uv-cache"
uv run pytest tests\test_validate_identity_coherence_8raw.py -q
```

## Task 1: Add V0.4 Acceptance Evaluation

**Files:**

- Modify: `scripts/validate_identity_coherence_8raw.py`
- Modify: `tests/test_validate_identity_coherence_8raw.py`

- [ ] **Step 1: Add failing acceptance tests**

Update the import block in `tests/test_validate_identity_coherence_8raw.py` to import:

```python
    V04_ACCEPTANCE_PASS_PREFIX,
    _merge_method_row,
    evaluate_v04_acceptance,
```

Append these tests:

```python
def test_merge_method_row_preserves_process_process_value() -> None:
    merged = _merge_method_row(
        ValidationRow("decoy_correctly_rejected_count", "pass", "3/3", "3/3", "s"),
        ValidationRow("decoy_correctly_rejected_count", "pass", "2/3", "2/3", "p"),
    )

    assert merged.serial_value == "3/3"
    assert merged.process_value == "2/3"


def _validation_result_with_rows(rows: tuple[ValidationRow, ...]) -> ValidationResult:
    return ValidationResult(rows=rows)


def test_evaluate_v04_acceptance_fails_without_reviewed_controls() -> None:
    result = _validation_result_with_rows(
        (
            ValidationRow("requests_tsv_exact", "pass", "3", "3", "ok"),
            ValidationRow("decisions_tsv_exact", "pass", "3", "3", "ok"),
            ValidationRow("cell_evidence_tsv_exact", "pass", "8", "8", "ok"),
            ValidationRow("controls_tsv_parity_only", "pass", "0", "0", "ok"),
            ValidationRow(
                "controls_manifest_assessment",
                "not_assessed",
                "not_provided",
                "not_provided",
                "no manifest",
            ),
            ValidationRow(
                "positive_control_pass_fraction",
                "not_assessed",
                "not_assessed",
                "not_assessed",
                "no manifest",
            ),
            ValidationRow(
                "decoy_coherent_seed_count",
                "not_assessed",
                "not_assessed",
                "not_assessed",
                "no manifest",
            ),
            ValidationRow(
                "decoy_correctly_rejected_count",
                "not_assessed",
                "not_assessed",
                "not_assessed",
                "no manifest",
            ),
            ValidationRow("summary_md_presence", "pass", "present", "present", "ok"),
        )
    )

    report = evaluate_v04_acceptance(
        result,
        controls_manifest=Path("identity_coherence_controls_manifest.reviewed.tsv"),
    )

    rows = {row.criterion: row for row in report.rows}
    assert rows["serial_process_sidecar_parity"].status == "pass"
    assert rows["reviewed_controls_manifest"].status == "fail"
    assert rows["v04_acceptance"].status == "fail"
    assert not report.accepted


def test_evaluate_v04_acceptance_passes_when_controls_pass() -> None:
    result = _validation_result_with_rows(
        (
            ValidationRow("requests_tsv_exact", "pass", "3", "3", "ok"),
            ValidationRow("decisions_tsv_exact", "pass", "3", "3", "ok"),
            ValidationRow("cell_evidence_tsv_exact", "pass", "8", "8", "ok"),
            ValidationRow("controls_tsv_parity_only", "pass", "2", "2", "ok"),
            ValidationRow(
                "controls_manifest_assessment",
                "not_assessed",
                "provided",
                "provided",
                "manifest provided",
            ),
            ValidationRow(
                "positive_control_pass_fraction",
                "pass",
                "1.000",
                "1.000",
                "all positives passed",
            ),
            ValidationRow(
                "decoy_coherent_seed_count",
                "pass",
                "0",
                "0",
                "no decoy promotion",
            ),
            ValidationRow(
                "decoy_correctly_rejected_count",
                "pass",
                "3/3",
                "3/3",
                "all decoys rejected",
            ),
            ValidationRow("summary_md_presence", "pass", "present", "present", "ok"),
        )
    )

    report = evaluate_v04_acceptance(
        result,
        controls_manifest=Path("identity_coherence_controls_manifest.reviewed.tsv"),
    )

    rows = {row.criterion: row for row in report.rows}
    assert rows["positive_control_sensitivity"].status == "pass"
    assert rows["identity_decoy_specificity"].status == "pass"
    assert rows["v04_acceptance"].status == "pass"
    assert report.accepted


def test_evaluate_v04_acceptance_fails_for_non_reviewed_manifest_name() -> None:
    result = _validation_result_with_rows(
        (
            ValidationRow("requests_tsv_exact", "pass", "3", "3", "ok"),
            ValidationRow("decisions_tsv_exact", "pass", "3", "3", "ok"),
            ValidationRow("cell_evidence_tsv_exact", "pass", "8", "8", "ok"),
            ValidationRow("controls_tsv_parity_only", "pass", "2", "2", "ok"),
            ValidationRow(
                "controls_manifest_assessment",
                "not_assessed",
                "provided",
                "provided",
                "manifest provided",
            ),
            ValidationRow(
                "positive_control_pass_fraction",
                "pass",
                "1.000",
                "1.000",
                "all positives passed",
            ),
            ValidationRow(
                "decoy_coherent_seed_count",
                "pass",
                "0",
                "0",
                "no decoy promotion",
            ),
            ValidationRow(
                "decoy_correctly_rejected_count",
                "pass",
                "3/3",
                "3/3",
                "all decoys rejected",
            ),
            ValidationRow("summary_md_presence", "pass", "present", "present", "ok"),
        )
    )

    report = evaluate_v04_acceptance(result, controls_manifest=Path("controls.tsv"))

    rows = {row.criterion: row for row in report.rows}
    assert rows["reviewed_controls_manifest"].status == "fail"
    assert rows["v04_acceptance"].status == "fail"
    assert not report.accepted


def test_evaluate_v04_acceptance_fails_when_decoy_promotes() -> None:
    result = _validation_result_with_rows(
        (
            ValidationRow("requests_tsv_exact", "pass", "3", "3", "ok"),
            ValidationRow("decisions_tsv_exact", "pass", "3", "3", "ok"),
            ValidationRow("cell_evidence_tsv_exact", "pass", "8", "8", "ok"),
            ValidationRow("controls_tsv_parity_only", "pass", "2", "2", "ok"),
            ValidationRow(
                "controls_manifest_assessment",
                "not_assessed",
                "provided",
                "provided",
                "manifest provided",
            ),
            ValidationRow(
                "positive_control_pass_fraction",
                "pass",
                "1.000",
                "1.000",
                "all positives passed",
            ),
            ValidationRow(
                "decoy_coherent_seed_count",
                "fail",
                "1",
                "1",
                "decoy promoted",
            ),
            ValidationRow(
                "decoy_correctly_rejected_count",
                "fail",
                "2/3",
                "2/3",
                "one decoy promoted",
            ),
            ValidationRow("summary_md_presence", "pass", "present", "present", "ok"),
        )
    )

    report = evaluate_v04_acceptance(
        result,
        controls_manifest=Path("identity_coherence_controls_manifest.reviewed.tsv"),
    )

    rows = {row.criterion: row for row in report.rows}
    assert rows["identity_decoy_specificity"].status == "fail"
    assert rows["v04_acceptance"].status == "fail"
    assert not report.accepted


def test_evaluate_v04_acceptance_fails_when_decoy_rejected_count_fails() -> None:
    result = _validation_result_with_rows(
        (
            ValidationRow("requests_tsv_exact", "pass", "3", "3", "ok"),
            ValidationRow("decisions_tsv_exact", "pass", "3", "3", "ok"),
            ValidationRow("cell_evidence_tsv_exact", "pass", "8", "8", "ok"),
            ValidationRow("controls_tsv_parity_only", "pass", "2", "2", "ok"),
            ValidationRow(
                "controls_manifest_assessment",
                "not_assessed",
                "provided",
                "provided",
                "manifest provided",
            ),
            ValidationRow(
                "positive_control_pass_fraction",
                "pass",
                "1.000",
                "1.000",
                "all positives passed",
            ),
            ValidationRow(
                "decoy_coherent_seed_count",
                "pass",
                "0",
                "0",
                "no coherent decoy",
            ),
            ValidationRow(
                "decoy_correctly_rejected_count",
                "fail",
                "2/3",
                "2/3",
                "one decoy not correctly rejected",
            ),
            ValidationRow("summary_md_presence", "pass", "present", "present", "ok"),
        )
    )

    report = evaluate_v04_acceptance(
        result,
        controls_manifest=Path("identity_coherence_controls_manifest.reviewed.tsv"),
    )

    rows = {row.criterion: row for row in report.rows}
    assert rows["identity_decoy_specificity"].status == "fail"
    assert rows["v04_acceptance"].status == "fail"
    assert not report.accepted
```

- [ ] **Step 2: Run the new tests and verify RED**

Run:

```powershell
uv run pytest tests\test_validate_identity_coherence_8raw.py -q
```

Expected: FAIL because `_merge_method_row` still uses the wrong process column
and `evaluate_v04_acceptance` is not implemented.

- [ ] **Step 3: Add acceptance dataclasses and evaluator**

Before adding the acceptance helpers, fix the existing method-row merge bug:

```python
def _merge_method_row(serial: ValidationRow, process: ValidationRow) -> ValidationRow:
    status = "pass" if serial.status == process.status == "pass" else "fail"
    if serial.status == process.status == "not_assessed":
        status = "not_assessed"
    return ValidationRow(
        check_name=serial.check_name,
        status=status,
        serial_value=serial.serial_value,
        process_value=process.process_value,
        details=f"serial: {serial.details}; process: {process.details}",
    )
```

Acceptance checks trust the merged serial/process values. Do not use
`process.serial_value` for the merged process column.

In `scripts/validate_identity_coherence_8raw.py`, add this after `ValidationResult`:

```python
ACCEPTANCE_SUMMARY_COLUMNS = (
    "criterion",
    "status",
    "evidence",
    "details",
)

V04_ACCEPTANCE_PASS_PREFIX = (
    "PASS identity_coherence_v04_acceptance "
    "scope=8raw_method_review_only not_85raw_ready"
)

SIDECAR_PARITY_CHECKS = (
    "requests_tsv_exact",
    "decisions_tsv_exact",
    "cell_evidence_tsv_exact",
    "controls_tsv_parity_only",
    "summary_md_presence",
)


@dataclass(frozen=True)
class AcceptanceRow:
    criterion: str
    status: str
    evidence: str
    details: str


@dataclass(frozen=True)
class AcceptanceReport:
    rows: tuple[AcceptanceRow, ...]

    @property
    def accepted(self) -> bool:
        rows = {row.criterion: row for row in self.rows}
        final = rows.get("v04_acceptance")
        return final is not None and final.status == "pass"
```

Add these helpers after `compare_identity_coherence_bundles()`:

```python
def sidecar_parity_failed_count(result: ValidationResult) -> int:
    return len(_sidecar_parity_failures(result))


def _sidecar_parity_failures(result: ValidationResult) -> tuple[str, ...]:
    rows_by_name = {row.check_name: row for row in result.rows}
    failures: list[str] = []
    for name in SIDECAR_PARITY_CHECKS:
        row = rows_by_name.get(name)
        if row is None or row.status != "pass":
            failures.append(name)
    return tuple(failures)


def evaluate_v04_acceptance(
    result: ValidationResult,
    *,
    controls_manifest: Path | None = None,
) -> AcceptanceReport:
    rows_by_name = {row.check_name: row for row in result.rows}
    parity = _acceptance_sidecar_parity(rows_by_name)
    controls = _acceptance_reviewed_controls(rows_by_name, controls_manifest)
    positives = _acceptance_positive_controls(rows_by_name)
    decoys = _acceptance_identity_decoys(rows_by_name)
    required = (parity, controls, positives, decoys)
    if all(row.status == "pass" for row in required):
        final = AcceptanceRow(
            criterion="v04_acceptance",
            status="pass",
            evidence="all_required_criteria_passed",
            details=(
                "V0.4 diagnostic mechanics and reviewed controls passed for "
                "8RAW method review; this does not clear 85RAW execution."
            ),
        )
    else:
        failing = ",".join(row.criterion for row in required if row.status != "pass")
        final = AcceptanceRow(
            criterion="v04_acceptance",
            status="fail",
            evidence=failing,
            details=(
                "V0.4 acceptance is blocked until all required criteria pass; "
                "do not treat serial/process parity alone as method validation."
            ),
        )
    return AcceptanceReport(rows=(*required, final))


def _acceptance_sidecar_parity(
    rows_by_name: dict[str, ValidationRow],
) -> AcceptanceRow:
    required = SIDECAR_PARITY_CHECKS
    missing = [name for name in required if name not in rows_by_name]
    failing = [
        name
        for name in required
        if name in rows_by_name and rows_by_name[name].status != "pass"
    ]
    if not missing and not failing:
        return AcceptanceRow(
            criterion="serial_process_sidecar_parity",
            status="pass",
            evidence=",".join(required),
            details="serial and process frozen sidecars match exactly",
        )
    evidence = ",".join((*missing, *failing))
    return AcceptanceRow(
        criterion="serial_process_sidecar_parity",
        status="fail",
        evidence=evidence,
        details="serial/process sidecar parity must pass before method review",
    )


def _acceptance_reviewed_controls(
    rows_by_name: dict[str, ValidationRow],
    controls_manifest: Path | None,
) -> AcceptanceRow:
    row = rows_by_name.get("controls_manifest_assessment")
    reviewed_path = (
        controls_manifest is not None
        and controls_manifest.name.lower().endswith(".reviewed.tsv")
    )
    if (
        row is not None
        and row.serial_value == row.process_value == "provided"
        and reviewed_path
    ):
        return AcceptanceRow(
            criterion="reviewed_controls_manifest",
            status="pass",
            evidence="provided",
            details=(
                "a .reviewed.tsv controls manifest was supplied to the validator"
            ),
        )
    return AcceptanceRow(
        criterion="reviewed_controls_manifest",
        status="fail",
        evidence="not_provided_or_not_reviewed",
        details=(
            "a .reviewed.tsv controls manifest is required; proposed manifests "
            "and ad-hoc TSV paths cannot satisfy this criterion"
        ),
    )


def _acceptance_positive_controls(
    rows_by_name: dict[str, ValidationRow],
) -> AcceptanceRow:
    row = rows_by_name.get("positive_control_pass_fraction")
    if row is not None and row.status == "pass":
        return AcceptanceRow(
            criterion="positive_control_sensitivity",
            status="pass",
            evidence=f"{row.serial_value}/{row.process_value}",
            details=row.details,
        )
    return AcceptanceRow(
        criterion="positive_control_sensitivity",
        status="fail",
        evidence=_row_evidence(row),
        details="positive controls must be present and pass before V0.4 acceptance",
    )


def _acceptance_identity_decoys(
    rows_by_name: dict[str, ValidationRow],
) -> AcceptanceRow:
    coherent = rows_by_name.get("decoy_coherent_seed_count")
    rejected = rows_by_name.get("decoy_correctly_rejected_count")
    if (
        coherent is not None
        and rejected is not None
        and coherent.status == "pass"
        and coherent.serial_value == coherent.process_value == "0"
        and rejected.status == "pass"
    ):
        return AcceptanceRow(
            criterion="identity_decoy_specificity",
            status="pass",
            evidence=f"promoted=0 rejected={rejected.serial_value}",
            details="identity decoys were rejected without coherent-seed promotion",
        )
    return AcceptanceRow(
        criterion="identity_decoy_specificity",
        status="fail",
        evidence=(
            f"promoted={_row_evidence(coherent)} "
            f"rejected={_row_evidence(rejected)}"
        ),
        details="identity decoys must not reach coherent seed or would-primary",
    )


def _row_evidence(row: ValidationRow | None) -> str:
    if row is None:
        return "missing"
    return f"{row.status}:{row.serial_value}/{row.process_value}"
```

- [ ] **Step 4: Run tests and verify GREEN**

Run:

```powershell
uv run pytest tests\test_validate_identity_coherence_8raw.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```powershell
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset add scripts\validate_identity_coherence_8raw.py tests\test_validate_identity_coherence_8raw.py
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset commit -m "feat: evaluate identity coherence v04 acceptance"
```

## Task 2: Emit Acceptance TSV And Markdown

**Files:**

- Modify: `scripts/validate_identity_coherence_8raw.py`
- Modify: `tests/test_validate_identity_coherence_8raw.py`

- [ ] **Step 1: Add failing output tests**

Append:

```python
def test_write_validation_outputs_writes_acceptance_artifacts(tmp_path: Path) -> None:
    result = _validation_result_with_rows(
        (
            ValidationRow("requests_tsv_exact", "pass", "3", "3", "ok"),
            ValidationRow("decisions_tsv_exact", "pass", "3", "3", "ok"),
            ValidationRow("cell_evidence_tsv_exact", "pass", "8", "8", "ok"),
            ValidationRow("controls_tsv_parity_only", "pass", "2", "2", "ok"),
            ValidationRow(
                "controls_manifest_assessment",
                "not_assessed",
                "provided",
                "provided",
                "manifest provided",
            ),
            ValidationRow(
                "positive_control_pass_fraction",
                "pass",
                "1.000",
                "1.000",
                "all positives passed",
            ),
            ValidationRow(
                "decoy_coherent_seed_count",
                "pass",
                "0",
                "0",
                "no decoy promotion",
            ),
            ValidationRow(
                "decoy_correctly_rejected_count",
                "pass",
                "3/3",
                "3/3",
                "all decoys rejected",
            ),
            ValidationRow("summary_md_presence", "pass", "present", "present", "ok"),
        )
    )

    acceptance = write_validation_outputs(
        output_root=tmp_path,
        result=result,
        controls_manifest=tmp_path / "controls.reviewed.tsv",
    )

    acceptance_tsv = tmp_path / "identity_coherence_v04_acceptance.tsv"
    acceptance_md = tmp_path / "identity_coherence_v04_acceptance.md"
    assert acceptance_tsv.exists()
    assert acceptance_md.exists()
    assert "v04_acceptance\tpass" in acceptance_tsv.read_text(encoding="utf-8")
    assert acceptance.accepted
    markdown = acceptance_md.read_text(encoding="utf-8")
    assert "# Identity Coherence V0.4 Acceptance" in markdown
    assert "| `v04_acceptance` | `pass` |" in markdown
    assert "does not clear 85RAW execution" in markdown


def test_write_validation_outputs_keeps_parity_report_pass_when_controls_fail(
    tmp_path: Path,
) -> None:
    result = _validation_result_with_rows(
        (
            ValidationRow("requests_tsv_exact", "pass", "3", "3", "ok"),
            ValidationRow("decisions_tsv_exact", "pass", "3", "3", "ok"),
            ValidationRow("cell_evidence_tsv_exact", "pass", "8", "8", "ok"),
            ValidationRow("controls_tsv_parity_only", "pass", "2", "2", "ok"),
            ValidationRow(
                "controls_manifest_assessment",
                "not_assessed",
                "provided",
                "provided",
                "manifest provided",
            ),
            ValidationRow(
                "positive_control_pass_fraction",
                "fail",
                "0.500",
                "0.500",
                "one positive control failed",
            ),
            ValidationRow(
                "decoy_coherent_seed_count",
                "pass",
                "0",
                "0",
                "no decoy promotion",
            ),
            ValidationRow(
                "decoy_correctly_rejected_count",
                "pass",
                "3/3",
                "3/3",
                "all decoys rejected",
            ),
            ValidationRow("summary_md_presence", "pass", "present", "present", "ok"),
        )
    )

    acceptance = write_validation_outputs(
        output_root=tmp_path,
        result=result,
        controls_manifest=tmp_path / "controls.reviewed.tsv",
    )

    report = (tmp_path / "identity_coherence_8raw_validation_report.md").read_text(
        encoding="utf-8",
    )
    assert "Parity result: PASS" in report
    assert not acceptance.accepted
```

- [ ] **Step 2: Run the new test and verify RED**

Run:

```powershell
uv run pytest tests\test_validate_identity_coherence_8raw.py::test_write_validation_outputs_writes_acceptance_artifacts -q
```

Expected: FAIL because the acceptance files are not written.

- [ ] **Step 3: Write acceptance output helpers**

In `scripts/validate_identity_coherence_8raw.py`, change
`write_validation_outputs(...) -> None` to
`write_validation_outputs(...) -> AcceptanceReport`. Then write acceptance
artifacts after the existing validation summary and report:

```python
    acceptance = evaluate_v04_acceptance(
        result,
        controls_manifest=controls_manifest,
    )
    _write_acceptance_tsv(
        output_root / "identity_coherence_v04_acceptance.tsv",
        acceptance,
    )
    _write_acceptance_md(
        output_root / "identity_coherence_v04_acceptance.md",
        report=acceptance,
        controls_manifest=controls_manifest,
    )
    return acceptance
```

Add these helpers near `_write_summary_tsv()`:

Before adding `_write_acceptance_tsv`, update `_write_report_md()` so `Parity
result` uses sidecar-only parity, not every validation row:

```python
    parity_result = (
        "PASS" if sidecar_parity_failed_count(result) == 0 else "FAIL"
    )
```

```python
def _write_acceptance_tsv(path: Path, report: AcceptanceReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=ACCEPTANCE_SUMMARY_COLUMNS,
            dialect="excel-tab",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in report.rows:
            writer.writerow(
                {
                    "criterion": row.criterion,
                    "status": row.status,
                    "evidence": row.evidence,
                    "details": row.details,
                }
            )


def _write_acceptance_md(
    path: Path,
    *,
    report: AcceptanceReport,
    controls_manifest: Path | None,
) -> None:
    controls_text = (
        str(controls_manifest) if controls_manifest is not None else "not_provided"
    )
    verdict = "PASS" if report.accepted else "FAIL"
    lines = [
        "# Identity Coherence V0.4 Acceptance",
        "",
        (
            "This report closes the V0.4 8RAW diagnostic acceptance loop. It is "
            "diagnostic-only and does not validate final matrix filtering, "
            "background filtering, normalization, statistics, or 85RAW execution."
        ),
        "",
        f"**Verdict:** `{verdict}`",
        "",
        f"**Reviewed controls manifest:** `{controls_text}`",
        "",
        "| Criterion | Status | Evidence | Details |",
        "| --- | --- | --- | --- |",
    ]
    for row in report.rows:
        lines.append(
            f"| `{row.criterion}` | `{row.status}` | "
            f"{_format_markdown_cell(row.evidence)} | "
            f"{_format_markdown_cell(row.details)} |"
        )
    lines.extend(
        [
            "",
            "## Handoff Notes",
            "",
            (
                "- A PASS means the V0.4 diagnostic is ready for human method "
                "review on the 8RAW subset."
            ),
            (
                "- A PASS does not authorize 85RAW execution; 85RAW still "
                "requires a reviewed count/fraction policy and request-budget "
                "ceiling."
            ),
            (
                "- A FAIL with passing serial/process parity usually means "
                "reviewed controls are missing or controls failed; do not "
                "reinterpret that as a retrieval or Backfill failure."
            ),
            (
                "- Contaminants that are chromatographically coherent can "
                "still appear as would-primary diagnostic rows; downstream "
                "filtering owns final-matrix exclusion."
            ),
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _format_markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
```

- [ ] **Step 4: Run tests and verify GREEN**

Run:

```powershell
uv run pytest tests\test_validate_identity_coherence_8raw.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```powershell
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset add scripts\validate_identity_coherence_8raw.py tests\test_validate_identity_coherence_8raw.py
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset commit -m "feat: emit identity coherence v04 acceptance report"
```

## Task 3: Add Strict Acceptance CLI Gate

**Files:**

- Modify: `scripts/validate_identity_coherence_8raw.py`
- Modify: `tests/test_validate_identity_coherence_8raw.py`

- [ ] **Step 1: Add failing CLI tests**

Append:

```python
def test_main_require_v04_acceptance_returns_one_when_not_accepted(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    batch = _write(tmp_path / "batch.csv", "sample_stem,raw_file,candidate_csv\n")
    raw_dir = tmp_path / "raw"
    dll_dir = tmp_path / "dll"
    raw_dir.mkdir()
    dll_dir.mkdir()
    output_root = tmp_path / "out"
    result = _validation_result_with_rows(
        (
            ValidationRow("requests_tsv_exact", "pass", "3", "3", "ok"),
            ValidationRow("decisions_tsv_exact", "pass", "3", "3", "ok"),
            ValidationRow("cell_evidence_tsv_exact", "pass", "8", "8", "ok"),
            ValidationRow("controls_tsv_parity_only", "pass", "0", "0", "ok"),
            ValidationRow(
                "controls_manifest_assessment",
                "not_assessed",
                "not_provided",
                "not_provided",
                "no manifest",
            ),
            ValidationRow(
                "positive_control_pass_fraction",
                "not_assessed",
                "not_assessed",
                "not_assessed",
                "no manifest",
            ),
            ValidationRow(
                "decoy_coherent_seed_count",
                "not_assessed",
                "not_assessed",
                "not_assessed",
                "no manifest",
            ),
            ValidationRow(
                "decoy_correctly_rejected_count",
                "not_assessed",
                "not_assessed",
                "not_assessed",
                "no manifest",
            ),
            ValidationRow("summary_md_presence", "pass", "present", "present", "ok"),
        )
    )
    monkeypatch.setattr(validation_script, "run_validation", lambda **_: result)

    code = validation_script.main(
        [
            "--discovery-batch-index",
            str(batch),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--output-root",
            str(output_root),
            "--require-v04-acceptance",
        ]
    )

    assert code == 1
    stderr = capsys.readouterr().err
    assert "FAIL identity_coherence_v04_acceptance" in stderr
    assert "reviewed_controls_manifest" in stderr
    assert (output_root / "identity_coherence_v04_acceptance.tsv").exists()


def test_main_without_strict_acceptance_prints_no_go_but_returns_zero(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    batch = _write(tmp_path / "batch.csv", "sample_stem,raw_file,candidate_csv\n")
    raw_dir = tmp_path / "raw"
    dll_dir = tmp_path / "dll"
    raw_dir.mkdir()
    dll_dir.mkdir()
    output_root = tmp_path / "out"
    result = _validation_result_with_rows(
        (
            ValidationRow("requests_tsv_exact", "pass", "3", "3", "ok"),
            ValidationRow("decisions_tsv_exact", "pass", "3", "3", "ok"),
            ValidationRow("cell_evidence_tsv_exact", "pass", "8", "8", "ok"),
            ValidationRow("controls_tsv_parity_only", "pass", "0", "0", "ok"),
            ValidationRow(
                "controls_manifest_assessment",
                "not_assessed",
                "not_provided",
                "not_provided",
                "no manifest",
            ),
            ValidationRow(
                "positive_control_pass_fraction",
                "not_assessed",
                "not_assessed",
                "not_assessed",
                "no manifest",
            ),
            ValidationRow(
                "decoy_coherent_seed_count",
                "not_assessed",
                "not_assessed",
                "not_assessed",
                "no manifest",
            ),
            ValidationRow(
                "decoy_correctly_rejected_count",
                "not_assessed",
                "not_assessed",
                "not_assessed",
                "no manifest",
            ),
            ValidationRow("summary_md_presence", "pass", "present", "present", "ok"),
        )
    )
    monkeypatch.setattr(validation_script, "run_validation", lambda **_: result)

    code = validation_script.main(
        [
            "--discovery-batch-index",
            str(batch),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--output-root",
            str(output_root),
        ]
    )

    assert code == 0
    stdout = capsys.readouterr().out
    assert "PASS identity_coherence_sidecar_parity" in stdout
    assert "NO-GO identity_coherence_v04_acceptance" in stdout
    assert "reviewed_controls_manifest" in stdout


def test_main_require_v04_acceptance_passes_when_accepted(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    batch = _write(tmp_path / "batch.csv", "sample_stem,raw_file,candidate_csv\n")
    raw_dir = tmp_path / "raw"
    dll_dir = tmp_path / "dll"
    controls = tmp_path / "controls.reviewed.tsv"
    raw_dir.mkdir()
    dll_dir.mkdir()
    controls.write_text("reviewed\n", encoding="utf-8")
    output_root = tmp_path / "out"
    result = _validation_result_with_rows(
        (
            ValidationRow("requests_tsv_exact", "pass", "3", "3", "ok"),
            ValidationRow("decisions_tsv_exact", "pass", "3", "3", "ok"),
            ValidationRow("cell_evidence_tsv_exact", "pass", "8", "8", "ok"),
            ValidationRow("controls_tsv_parity_only", "pass", "2", "2", "ok"),
            ValidationRow(
                "controls_manifest_assessment",
                "not_assessed",
                "provided",
                "provided",
                "manifest provided",
            ),
            ValidationRow(
                "positive_control_pass_fraction",
                "pass",
                "1.000",
                "1.000",
                "all positives passed",
            ),
            ValidationRow(
                "decoy_coherent_seed_count",
                "pass",
                "0",
                "0",
                "no decoy promotion",
            ),
            ValidationRow(
                "decoy_correctly_rejected_count",
                "pass",
                "3/3",
                "3/3",
                "all decoys rejected",
            ),
            ValidationRow("summary_md_presence", "pass", "present", "present", "ok"),
        )
    )
    monkeypatch.setattr(validation_script, "run_validation", lambda **_: result)

    code = validation_script.main(
        [
            "--discovery-batch-index",
            str(batch),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--output-root",
            str(output_root),
            "--controls-manifest",
            str(controls),
            "--require-v04-acceptance",
        ]
    )

    assert code == 0
    stdout = capsys.readouterr().out
    assert "PASS identity_coherence_sidecar_parity" in stdout
    assert V04_ACCEPTANCE_PASS_PREFIX in stdout
```

- [ ] **Step 2: Run the new tests and verify RED**

Run:

```powershell
uv run pytest tests\test_validate_identity_coherence_8raw.py::test_main_require_v04_acceptance_returns_one_when_not_accepted tests\test_validate_identity_coherence_8raw.py::test_main_without_strict_acceptance_prints_no_go_but_returns_zero tests\test_validate_identity_coherence_8raw.py::test_main_require_v04_acceptance_passes_when_accepted -q
```

Expected: FAIL because `--require-v04-acceptance` is not implemented.

- [ ] **Step 3: Add the CLI flag and gate**

In `main()`, add:

```python
    parser.add_argument(
        "--require-v04-acceptance",
        action="store_true",
        help=(
            "Exit non-zero unless serial/process parity, reviewed controls, "
            "positive controls, and identity decoys pass V0.4 acceptance."
        ),
    )
```

In `run_validation()`, keep proposal generation guarded by the existing
`result.failed_count` branch, but add an inline comment there:

```python
        # Proposal generation stays conservative: if any existing validation
        # row is already failed, do not emit a new proposed controls manifest.
```

Capture the `AcceptanceReport` returned by `write_validation_outputs(...)`:

```python
        acceptance = write_validation_outputs(
            output_root=args.output_root,
            result=result,
            controls_manifest=args.controls_manifest,
        )
```

Replace the existing `if result.failed_count:` sidecar-failure block with a
sidecar-only check:

```python
    sidecar_failed_count = sidecar_parity_failed_count(result)
    if sidecar_failed_count:
        print(
            "FAIL identity_coherence_sidecar_parity "
            f"failed={sidecar_failed_count}",
            file=sys.stderr,
        )
        return 1
```

After that sidecar-only check, compute the final acceptance row:

```python
    acceptance_rows = {row.criterion: row for row in acceptance.rows}
    final_acceptance = acceptance_rows["v04_acceptance"]
```

Then add the strict acceptance gate:

```python
    if args.require_v04_acceptance and not acceptance.accepted:
        print(
            "FAIL identity_coherence_v04_acceptance "
            f"reason={final_acceptance.evidence} "
            f"summary={args.output_root / 'identity_coherence_v04_acceptance.md'}",
            file=sys.stderr,
        )
        return 1
```

After the existing sidecar PASS print, add:

```python
    if acceptance.accepted:
        print(
            f"{V04_ACCEPTANCE_PASS_PREFIX} "
            f"summary={args.output_root / 'identity_coherence_v04_acceptance.md'}"
        )
    else:
        print(
            "NO-GO identity_coherence_v04_acceptance "
            f"reason={final_acceptance.evidence} "
            f"summary={args.output_root / 'identity_coherence_v04_acceptance.md'}"
        )
```

- [ ] **Step 4: Run tests and verify GREEN**

Run:

```powershell
uv run pytest tests\test_validate_identity_coherence_8raw.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```powershell
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset add scripts\validate_identity_coherence_8raw.py tests\test_validate_identity_coherence_8raw.py
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset commit -m "feat: gate identity coherence v04 acceptance"
```

## Task 4: Final Verification And Real 8RAW Closure Run

**Files:** no source edits expected.

- [ ] **Step 1: Run focused tests**

Run:

```powershell
uv run pytest tests\test_validate_identity_coherence_8raw.py tests\test_run_alignment.py tests\test_alignment_identity_coherence_adapter.py tests\alignment\identity_coherence -q
```

Expected: PASS.

- [ ] **Step 2: Run lint for modified files**

Run:

```powershell
uv run ruff check scripts\validate_identity_coherence_8raw.py tests\test_validate_identity_coherence_8raw.py
```

Expected: PASS.

- [ ] **Step 3: Run boundary grep**

Run:

```powershell
rg -n "xic_extractor\.alignment|identity_coherence_adapter|identity_coherence\.controls|raw_reader|open_raw|extract_xic|owner_backfill|primary_matrix|final_matrix|workbook|process_backend" scripts\validate_identity_coherence_8raw.py
```

Expected: no matches.

Then run the test-file audit:

```powershell
rg -n "xic_extractor\.alignment|identity_coherence\.controls|raw_reader|open_raw|extract_xic|owner_backfill|primary_matrix|final_matrix|workbook|process_backend" tests\test_validate_identity_coherence_8raw.py
```

Expected: tests may contain only explicit manifest-reader fixtures or comments.
This is a syntactic firewall for the standalone validator; if the validator
grows beyond TSV/report logic, replace this grep with an AST import scan.

- [ ] **Step 4: Run 8RAW validator without reviewed controls**

Run:

```powershell
uv run python scripts\validate_identity_coherence_8raw.py `
  --discovery-batch-index output\discovery\timing_phase0_8raw\discovery_batch_index.csv `
  --raw-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" `
  --dll-dir "C:\Xcalibur\system\programs" `
  --output-root output\identity_coherence_8raw_validation `
  --write-controls-manifest-proposal output\identity_coherence_8raw_validation\identity_coherence_controls_manifest_8raw.proposed.tsv
```

Expected:

```text
PASS identity_coherence_sidecar_parity summary=output\identity_coherence_8raw_validation\identity_coherence_8raw_validation_report.md
NO-GO identity_coherence_v04_acceptance reason=reviewed_controls_manifest,positive_control_sensitivity,identity_decoy_specificity summary=output\identity_coherence_8raw_validation\identity_coherence_v04_acceptance.md
Controls manifest proposal: output\identity_coherence_8raw_validation\identity_coherence_controls_manifest_8raw.proposed.tsv
```

Also expected:

```text
output\identity_coherence_8raw_validation\identity_coherence_v04_acceptance.tsv
output\identity_coherence_8raw_validation\identity_coherence_v04_acceptance.md
```

Acceptance verdict should be `FAIL` in the TSV/Markdown and `NO-GO` on stdout
because reviewed controls are not supplied yet. The command still exits `0`
when `--require-v04-acceptance` is not set, preserving the sidecar parity
validator contract.

- [ ] **Step 5: Run 8RAW strict acceptance only if reviewed controls exist**

Run:

```powershell
$reviewedManifest = "output\identity_coherence_8raw_validation\identity_coherence_controls_manifest_8raw.reviewed.tsv"
if (Test-Path $reviewedManifest) {
  uv run python scripts\validate_identity_coherence_8raw.py `
    --discovery-batch-index output\discovery\timing_phase0_8raw\discovery_batch_index.csv `
    --raw-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" `
    --dll-dir "C:\Xcalibur\system\programs" `
    --output-root output\identity_coherence_8raw_validation_reviewed `
    --controls-manifest $reviewedManifest `
    --require-v04-acceptance
} else {
  Write-Output "NO-GO reviewed controls validation: $reviewedManifest does not exist"
}
```

Expected:

- If the reviewed manifest does not exist: print the `NO-GO` line, stop the
  method acceptance closure, and do not fabricate controls. This is an expected
  handoff state: manually review the proposed manifest, add positive controls,
  save it as `.reviewed.tsv`, then rerun strict acceptance.
- If the reviewed manifest exists and passes: exit code `0`, sidecar parity PASS, V0.4 acceptance PASS.
- If the reviewed manifest exists but acceptance fails: exit code `1`; inspect `identity_coherence_v04_acceptance.md` and fix controls or method logic before 85RAW planning.

- [ ] **Step 6: Commit verification-related source changes**

If Task 4 did not change source files, no commit is needed. If Task 4 required a small source/test fix, commit only that fix:

```powershell
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset status --short
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset add scripts\validate_identity_coherence_8raw.py tests\test_validate_identity_coherence_8raw.py
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset commit -m "test: verify identity coherence v04 acceptance closure"
```

## Stop Conditions

Stop and ask for review if any of these occur:

- serial/process sidecar parity fails;
- `.proposed.tsv` is the only available controls manifest and no reviewed manifest exists;
- positive controls are absent or fail;
- any identity decoy reaches coherent seed or would-primary;
- the validator needs to import alignment internals or RAW adapters to compute acceptance;
- the implementation touches Backfill, final matrix, workbook rendering, or downstream filtering.

## Self-Review Checklist

- [ ] Acceptance layer reads only `ValidationResult` rows and the validator's own outputs.
- [ ] `--require-v04-acceptance` is opt-in and does not break existing parity-only validation.
- [ ] Missing reviewed controls produce an explicit V0.4 acceptance FAIL, not a silent PASS.
- [ ] Reviewed controls require a `.reviewed.tsv` manifest path; `.proposed.tsv` cannot satisfy acceptance.
- [ ] Positive controls and decoys are both required for acceptance.
- [ ] V0.4 acceptance PASS does not claim 85RAW readiness.
- [ ] No new identity promotion logic, thresholds, or downstream filtering rules were added.
- [ ] Tests cover missing controls, passing controls, decoy promotion failure, output files, and CLI strict mode.
- [ ] Focused tests and ruff pass.

## Execution Handoff

After this plan lands, execute it with either:

1. **Subagent-Driven (recommended)**: one worker for Task 1-3 code/tests, then main-line verification and Task 4 real-data run.
2. **Inline Execution**: implement Task 1-3 in this session and reserve subagents for review only.

Because the write scope is a single script plus one test file, inline execution is acceptable if the main agent keeps commits task-sized and runs the real 8RAW closure command at the end.
