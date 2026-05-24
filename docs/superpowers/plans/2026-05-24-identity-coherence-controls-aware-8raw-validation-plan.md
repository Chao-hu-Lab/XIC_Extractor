# Identity Coherence Controls-Aware 8RAW Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the 8RAW identity coherence validation runner so it can interpret `controls.tsv`, generate a reviewed decoy manifest proposal, and run the real 8RAW validation path without overclaiming final-matrix or downstream filtering validity.

**Architecture:** Keep the validator as a standalone CLI wrapper around `scripts/run_alignment.py`. It still must not import alignment internals, RAW readers, Backfill, workbook code, or final matrix code. Controls interpretation is TSV-only: read frozen sidecar outputs, summarize positive-control and identity-decoy status, and generate a decoy manifest proposal from existing diagnostic rows for human review.

**Tech Stack:** Python 3.11+, `argparse`, `csv`, `dataclasses`, `pathlib`, `subprocess`, `pytest`, existing identity coherence sidecar TSVs, PowerShell.

---

## Scope Boundary

In scope:

- Extend `scripts/validate_identity_coherence_8raw.py`.
- Extend `tests/test_validate_identity_coherence_8raw.py`.
- Interpret the already-written `untargeted_identity_coherence_controls.tsv` in the validation summary.
- Generate an identity-decoy-only manifest proposal from `requests.tsv` + `decisions.tsv`.
- Recreate the missing 8RAW discovery batch index when real-data prerequisites are available.
- Run the 8RAW serial-vs-process validator with `validation-fast` process settings.

Out of scope:

- No changes to `xic_extractor/alignment/identity_coherence_adapter.py`.
- No changes to `xic_extractor/alignment/process_backend.py`.
- No changes to `xic_extractor/raw_reader.py`, RAW/XIC retrieval, Backfill, final matrix filtering, workbook rendering, or downstream statistical filtering.
- No automatic positive-control selection. Positive controls require reviewed targeted ISTD/stable-feature mapping and must not be fabricated from untargeted rows.
- No 85RAW policy.

The decoy proposal produced by this plan is a review artifact. It is not a validated manifest until the user reviews it and copies/renames it to a `.reviewed.tsv` manifest path. The validator must reject `.proposed.tsv` paths passed to `--controls-manifest`; proposals are never controls evidence.

## Current State

The previous plan added:

```text
scripts/validate_identity_coherence_8raw.py
tests/test_validate_identity_coherence_8raw.py
```

The current worktree preflight found:

```text
output\discovery\timing_phase0_8raw\discovery_batch_index.csv -> missing
C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation -> exists
C:\Xcalibur\system\programs -> exists
```

This plan therefore includes a real-data step to regenerate the discovery batch index before running the validator.

## Output Contract

Existing validation outputs stay unchanged:

```text
output\identity_coherence_8raw_validation\serial\...
output\identity_coherence_8raw_validation\process\...
output\identity_coherence_8raw_validation\identity_coherence_8raw_validation_summary.tsv
output\identity_coherence_8raw_validation\identity_coherence_8raw_validation_report.md
```

New optional proposal output:

```text
output\identity_coherence_8raw_validation\identity_coherence_controls_manifest_8raw.proposed.tsv
```

The proposal path is explicit. The validator must not silently treat a proposal as reviewed controls evidence.

## Task 0: Preflight

**Files:** none.

- [ ] **Step 1: Confirm worktree and base commit**

```powershell
Set-Location "C:\Users\user\Desktop\XIC_Extractor\.worktrees\untargeted-backfill-logic-reset"
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset status --short
$baseCommit = git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset rev-parse HEAD
$baseCommit
New-Item -ItemType Directory -Force output\identity_coherence_8raw_validation | Out-Null
$baseCommit | Set-Content output\identity_coherence_8raw_validation\.base_commit.txt
```

Expected: clean or only this plan file when execution starts.

- [ ] **Step 2: Check real-data prerequisites**

```powershell
Test-Path output\discovery\timing_phase0_8raw\discovery_batch_index.csv
Test-Path "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation"
Test-Path "C:\Xcalibur\system\programs"
```

Expected at plan-write time: first path may be `False`; RAW and DLL paths are `True`.

## Task 1: Add Controls TSV Interpretation Rows

**Files:**

- Modify: `scripts/validate_identity_coherence_8raw.py`
- Modify: `tests/test_validate_identity_coherence_8raw.py`

- [ ] **Step 1: Add failing tests for controls method rows**

Update the import block in `tests/test_validate_identity_coherence_8raw.py` to include `ValidationRow`, if it is not already imported. Append:

```python
def _write_controls_bundle(
    root: Path,
    *,
    controls_rows: str,
) -> DiagnosticBundle:
    # Minimal fixture for method-row calculation. Frozen output schema parity is
    # covered by the existing writer tests; this validator only consumes these
    # five controls.tsv fields for summary metrics.
    bundle = _bundle(root)
    _write(bundle.requests_tsv, "request_id\tseed_candidate_id\nICR-1\tC1\n")
    _write(
        bundle.decisions_tsv,
        "decision_id\tdecision\n"
        "ICD-1\twould_primary_provisional_identity_family_support\n",
    )
    _write(bundle.cell_evidence_tsv, "decision_id\tsample_id\nICD-1\tS2\n")
    _write(
        bundle.controls_tsv,
        "control_id\tcontrol_type\tcontrol_pass\tcontrol_status\t"
        "control_failure_reason\n"
        + controls_rows,
    )
    _write(bundle.summary_md, "# Summary\n")
    return bundle


def test_controls_rows_remain_not_assessed_without_manifest(tmp_path: Path) -> None:
    serial = _write_controls_bundle(
        tmp_path / "serial",
        controls_rows="IDC-1\tidentity_decoy\ttrue\tassessed\t\n",
    )
    process = _write_controls_bundle(
        tmp_path / "process",
        controls_rows="IDC-1\tidentity_decoy\ttrue\tassessed\t\n",
    )

    result = compare_identity_coherence_bundles(
        serial,
        process,
        controls_manifest=None,
    )

    rows = {row.check_name: row for row in result.rows}
    assert rows["controls_manifest_assessment"].status == "not_assessed"
    assert rows["positive_control_pass_fraction"].status == "not_assessed"
    assert rows["decoy_coherent_seed_count"].status == "not_assessed"


def test_controls_rows_report_positive_and_decoy_metrics(tmp_path: Path) -> None:
    manifest = tmp_path / "controls.tsv"
    manifest.write_text("manifest\n", encoding="utf-8")
    controls = (
        "PC-1\tpositive_targeted_istd\ttrue\tassessed\t\n"
        "IDC-1\tidentity_decoy\ttrue\tassessed\t\n"
    )
    serial = _write_controls_bundle(tmp_path / "serial", controls_rows=controls)
    process = _write_controls_bundle(tmp_path / "process", controls_rows=controls)

    result = compare_identity_coherence_bundles(
        serial,
        process,
        controls_manifest=manifest,
    )

    rows = {row.check_name: row for row in result.rows}
    assert rows["positive_control_pass_fraction"].status == "pass"
    assert rows["positive_control_pass_fraction"].serial_value == "1.000"
    assert rows["decoy_coherent_seed_count"].status == "pass"
    assert rows["decoy_coherent_seed_count"].serial_value == "0"
    assert rows["decoy_correctly_rejected_count"].serial_value == "1/1"


def test_controls_rows_fail_when_decoy_reaches_coherent_seed(tmp_path: Path) -> None:
    manifest = tmp_path / "controls.tsv"
    manifest.write_text("manifest\n", encoding="utf-8")
    controls = (
        "IDC-1\tidentity_decoy\tfalse\tassessed\tdecoy_seed_gate_coherent\n"
    )
    serial = _write_controls_bundle(tmp_path / "serial", controls_rows=controls)
    process = _write_controls_bundle(tmp_path / "process", controls_rows=controls)

    result = compare_identity_coherence_bundles(
        serial,
        process,
        controls_manifest=manifest,
    )

    rows = {row.check_name: row for row in result.rows}
    assert rows["decoy_coherent_seed_count"].status == "fail"
    assert rows["decoy_coherent_seed_count"].serial_value == "1"


def test_controls_rows_do_not_interpret_when_controls_parity_fails(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "controls.tsv"
    manifest.write_text("manifest\n", encoding="utf-8")
    serial = _write_controls_bundle(
        tmp_path / "serial",
        controls_rows="IDC-1\tidentity_decoy\ttrue\tassessed\t\n",
    )
    process = _write_controls_bundle(
        tmp_path / "process",
        controls_rows="IDC-1\tidentity_decoy\tfalse\tassessed\t"
        "decoy_seed_gate_coherent\n",
    )

    result = compare_identity_coherence_bundles(
        serial,
        process,
        controls_manifest=manifest,
    )

    rows = {row.check_name: row for row in result.rows}
    assert rows["controls_tsv_parity_only"].status == "fail"
    assert rows["decoy_coherent_seed_count"].status == "fail"
    assert rows["decoy_coherent_seed_count"].serial_value == "not_assessed"
    assert rows["decoy_coherent_seed_count"].process_value == "not_assessed"
```

- [ ] **Step 2: Run tests to verify RED**

```powershell
uv run pytest tests\test_validate_identity_coherence_8raw.py -q
```

Expected: fail because `positive_control_pass_fraction`, `decoy_coherent_seed_count`, and `decoy_correctly_rejected_count` rows are not produced.

- [ ] **Step 3: Implement controls TSV summarizer**

In `scripts/validate_identity_coherence_8raw.py`, update `compare_identity_coherence_bundles()` so it appends controls method rows:

```python
def compare_identity_coherence_bundles(
    serial: DiagnosticBundle,
    process: DiagnosticBundle,
    *,
    controls_manifest: Path | None = None,
) -> ValidationResult:
    controls_parity = _compare_tsv(
        "controls_tsv_parity_only",
        serial.controls_tsv,
        process.controls_tsv,
        success_details=(
            "controls file parity only; method controls summarized separately"
        ),
    )
    rows = [
        _compare_tsv("requests_tsv_exact", serial.requests_tsv, process.requests_tsv),
        _compare_tsv(
            "decisions_tsv_exact",
            serial.decisions_tsv,
            process.decisions_tsv,
        ),
        _compare_tsv(
            "cell_evidence_tsv_exact",
            serial.cell_evidence_tsv,
            process.cell_evidence_tsv,
        ),
        controls_parity,
        _controls_manifest_row(controls_manifest),
        *_control_method_rows(
            serial.controls_tsv,
            process.controls_tsv,
            controls_manifest,
            controls_parity_pass=controls_parity.status == "pass",
        ),
        _compare_summary_presence(serial.summary_md, process.summary_md),
    ]
    return ValidationResult(rows=tuple(rows))
```

Add helpers near `_controls_manifest_row()`:

```python
def _control_method_rows(
    serial_controls_tsv: Path,
    process_controls_tsv: Path,
    controls_manifest: Path | None,
    *,
    controls_parity_pass: bool,
) -> tuple[ValidationRow, ...]:
    if controls_manifest is None:
        return (
            ValidationRow(
                check_name="positive_control_pass_fraction",
                status="not_assessed",
                serial_value="not_assessed",
                process_value="not_assessed",
                details="controls manifest not provided",
            ),
            ValidationRow(
                check_name="decoy_coherent_seed_count",
                status="not_assessed",
                serial_value="not_assessed",
                process_value="not_assessed",
                details="controls manifest not provided",
            ),
            ValidationRow(
                check_name="decoy_correctly_rejected_count",
                status="not_assessed",
                serial_value="not_assessed",
                process_value="not_assessed",
                details="controls manifest not provided",
            ),
        )
    if not controls_parity_pass:
        return (
            ValidationRow(
                check_name="positive_control_pass_fraction",
                status="fail",
                serial_value="not_assessed",
                process_value="not_assessed",
                details="controls TSV parity failed; method rows not interpreted",
            ),
            ValidationRow(
                check_name="decoy_coherent_seed_count",
                status="fail",
                serial_value="not_assessed",
                process_value="not_assessed",
                details="controls TSV parity failed; method rows not interpreted",
            ),
            ValidationRow(
                check_name="decoy_correctly_rejected_count",
                status="fail",
                serial_value="not_assessed",
                process_value="not_assessed",
                details="controls TSV parity failed; method rows not interpreted",
            ),
        )
    serial_rows = _read_tsv_dict_rows(serial_controls_tsv)
    process_rows = _read_tsv_dict_rows(process_controls_tsv)
    serial_positive = _positive_control_fraction_row(
        _rows_by_control_type(serial_rows, "positive_targeted_istd"),
    )
    process_positive = _positive_control_fraction_row(
        _rows_by_control_type(process_rows, "positive_targeted_istd"),
    )
    serial_coherent = _decoy_coherent_count_row(
        _rows_by_control_type(serial_rows, "identity_decoy"),
    )
    process_coherent = _decoy_coherent_count_row(
        _rows_by_control_type(process_rows, "identity_decoy"),
    )
    serial_rejected = _decoy_rejected_count_row(
        _rows_by_control_type(serial_rows, "identity_decoy"),
    )
    process_rejected = _decoy_rejected_count_row(
        _rows_by_control_type(process_rows, "identity_decoy"),
    )
    return (
        _merge_method_row(serial_positive, process_positive),
        _merge_method_row(serial_coherent, process_coherent),
        _merge_method_row(serial_rejected, process_rejected),
    )


def _read_tsv_dict_rows(path: Path) -> tuple[dict[str, str], ...]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, dialect="excel-tab")
        return tuple(dict(row) for row in reader)


def _rows_by_control_type(
    rows: tuple[dict[str, str], ...],
    control_type: str,
) -> list[dict[str, str]]:
    return [row for row in rows if row.get("control_type") == control_type]


def _merge_method_row(serial: ValidationRow, process: ValidationRow) -> ValidationRow:
    status = "pass" if serial.status == process.status == "pass" else "fail"
    if serial.status == process.status == "not_assessed":
        status = "not_assessed"
    return ValidationRow(
        check_name=serial.check_name,
        status=status,
        serial_value=serial.serial_value,
        process_value=process.serial_value,
        details=f"serial: {serial.details}; process: {process.details}",
    )


def _positive_control_fraction_row(
    rows: list[dict[str, str]],
) -> ValidationRow:
    if not rows:
        return ValidationRow(
            check_name="positive_control_pass_fraction",
            status="not_assessed",
            serial_value="0/0",
            process_value="0/0",
            details="no positive_targeted_istd controls in controls.tsv",
        )
    passed = sum(1 for row in rows if _control_pass_is_true(row))
    fraction = passed / len(rows)
    value = f"{fraction:.3f}"
    return ValidationRow(
        check_name="positive_control_pass_fraction",
        status="pass" if passed == len(rows) else "fail",
        serial_value=value,
        process_value=value,
        details=f"{passed}/{len(rows)} positive controls passed",
    )


def _decoy_coherent_count_row(rows: list[dict[str, str]]) -> ValidationRow:
    if not rows:
        return ValidationRow(
            check_name="decoy_coherent_seed_count",
            status="not_assessed",
            serial_value="0",
            process_value="0",
            details="no identity_decoy controls in controls.tsv",
        )
    coherent = sum(
        1
        for row in rows
        if row.get("control_failure_reason") == "decoy_seed_gate_coherent"
    )
    return ValidationRow(
        check_name="decoy_coherent_seed_count",
        status="pass" if coherent == 0 else "fail",
        serial_value=str(coherent),
        process_value=str(coherent),
        details="decoy controls that reached coherent_seed",
    )


def _decoy_rejected_count_row(rows: list[dict[str, str]]) -> ValidationRow:
    if not rows:
        return ValidationRow(
            check_name="decoy_correctly_rejected_count",
            status="not_assessed",
            serial_value="0/0",
            process_value="0/0",
            details="no identity_decoy controls in controls.tsv",
        )
    passed = sum(1 for row in rows if _control_pass_is_true(row))
    value = f"{passed}/{len(rows)}"
    return ValidationRow(
        check_name="decoy_correctly_rejected_count",
        status="pass" if passed == len(rows) else "fail",
        serial_value=value,
        process_value=value,
        details="identity decoys rejected before false promotion",
    )


def _control_pass_is_true(row: dict[str, str]) -> bool:
    # Intentional duplication: validator must not import alignment internals,
    # and independent controls summary computation is the cross-check.
    return row.get("control_pass", "").strip().lower() == "true"
```

- [ ] **Step 4: Verify and commit**

```powershell
uv run pytest tests\test_validate_identity_coherence_8raw.py -q
uv run ruff check scripts\validate_identity_coherence_8raw.py tests\test_validate_identity_coherence_8raw.py
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset add scripts\validate_identity_coherence_8raw.py tests\test_validate_identity_coherence_8raw.py
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset commit -m "feat: summarize identity coherence controls validation"
```

## Task 2: Generate A Decoy Controls Manifest Proposal

**Files:**

- Modify: `scripts/validate_identity_coherence_8raw.py`
- Modify: `tests/test_validate_identity_coherence_8raw.py`

- [ ] **Step 1: Add failing proposal tests**

Append:

```python
# This fixture intentionally uses the proposal writer's minimum input surface.
# Do not consolidate it with _write_bundle(); this test needs seed_gate_class.
def _write_proposal_source_bundle(root: Path) -> DiagnosticBundle:
    bundle = _bundle(root)
    _write(
        bundle.requests_tsv,
        "request_id\tdecision_id\tseed_candidate_id\tseed_sample\t"
        "fragment_observation_mode\tprecursor_mz\tproduct_mz\tfragment_tags\t"
        "fragment_tag_match_policy\tfragment_profile_id\tfragment_profile_hash\t"
        "precursor_tolerance_ppm\tproduct_tolerance_ppm\tcid_observed_loss_da\t"
        "cid_observed_loss_tolerance_ppm\trequest_identity_completeness_status\t"
        "request_candidate_identity_status\tprecursor_error_ppm\tproduct_error_ppm\t"
        "cid_observed_loss_error_ppm\tcid_observed_loss_error_da\t"
        "request_builder_flags\n"
        "ICR-1\tICD-1\tC1\tS1\tcid_neutral_loss\t500.0\t384.0\tDNA_dR\t"
        "all_request_tags_supported\tdefault\tunavailable\t20.0\t20.0\t"
        "116.0474\t20.0\tcomplete\tmatch\t0.1\t0.2\t0.3\t0.0001\t\n",
    )
    _write(
        bundle.decisions_tsv,
        "decision_id\tidentity_family_id\tseed_candidate_id\tseed_sample\t"
        "seed_gate_class\tdecision\n"
        "ICD-1\tICF-1\tC1\tS1\tcoherent_seed\t"
        "would_primary_provisional_identity_family_support\n",
    )
    _write(bundle.cell_evidence_tsv, "decision_id\tsample_id\nICD-1\tS2\n")
    _write(bundle.controls_tsv, "control_id\tcontrol_type\tcontrol_pass\n")
    _write(bundle.summary_md, "# Summary\n")
    return bundle


def test_write_decoy_manifest_proposal_from_serial_bundle(tmp_path: Path) -> None:
    bundle = _write_proposal_source_bundle(tmp_path / "serial")
    proposal = tmp_path / "identity_coherence_controls_manifest_8raw.proposed.tsv"

    count = write_decoy_manifest_proposal(
        bundle,
        proposal,
        max_decoys=1,
    )

    assert count == 1
    text = proposal.read_text(encoding="utf-8")
    assert "control_id\tcontrol_type\tcontrol_name" in text
    assert "IDC-001\tidentity_decoy\tAuto-proposed rt_shift decoy for ICR-1" in text
    assert "\tnot_applicable\t" in text
    assert "\tseed_rt_outside_owner_peak\t" in text
    assert "\tICR-1\t" in text
    assert "\trt_shift\t" in text


def test_write_decoy_manifest_proposal_writes_header_when_no_sources(
    tmp_path: Path,
) -> None:
    bundle = _write_proposal_source_bundle(tmp_path / "serial")
    _write(
        bundle.decisions_tsv,
        "decision_id\tidentity_family_id\tseed_candidate_id\tseed_sample\t"
        "seed_gate_class\tdecision\n"
        "ICD-1\tICF-1\tC1\tS1\treview_only_seed_gate_failed\t"
        "review_only_seed_gate_failed\n",
    )
    proposal = tmp_path / "proposal.tsv"

    count = write_decoy_manifest_proposal(bundle, proposal, max_decoys=3)

    assert count == 0
    lines = proposal.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert lines[0].startswith("control_id\tcontrol_type\tcontrol_name")


def test_write_decoy_manifest_proposal_respects_zero_limit(
    tmp_path: Path,
) -> None:
    bundle = _write_proposal_source_bundle(tmp_path / "serial")
    proposal = tmp_path / "proposal.tsv"

    count = write_decoy_manifest_proposal(bundle, proposal, max_decoys=0)

    assert count == 0
    assert len(proposal.read_text(encoding="utf-8").splitlines()) == 1


def test_write_decoy_manifest_proposal_joins_by_decision_id(
    tmp_path: Path,
) -> None:
    bundle = _write_proposal_source_bundle(tmp_path / "serial")
    _write(
        bundle.requests_tsv,
        bundle.requests_tsv.read_text(encoding="utf-8").replace(
            "ICR-1\tICD-1\tC1\tS1",
            "ICR-WRONG\tICD-OTHER\tC1\tS9",
        )
        + bundle.requests_tsv.read_text(encoding="utf-8").splitlines()[1]
        .replace("ICR-1\tICD-1\tC1\tS1", "ICR-RIGHT\tICD-1\tC1\tS1")
        + "\n",
    )
    proposal = tmp_path / "proposal.tsv"

    count = write_decoy_manifest_proposal(bundle, proposal, max_decoys=1)

    assert count == 1
    text = proposal.read_text(encoding="utf-8")
    assert "\tICR-RIGHT\t" in text
    assert "\tICR-WRONG\t" not in text


def test_write_decoy_manifest_proposal_skips_incomplete_tolerances(
    tmp_path: Path,
) -> None:
    bundle = _write_proposal_source_bundle(tmp_path / "serial")
    bundle.requests_tsv.write_text(
        bundle.requests_tsv.read_text(encoding="utf-8").replace(
            "\t20.0\t20.0\t116.0474\t20.0\t",
            "\t20.0\t\t116.0474\t20.0\t",
        ),
        encoding="utf-8",
    )
    proposal = tmp_path / "proposal.tsv"

    count = write_decoy_manifest_proposal(bundle, proposal, max_decoys=1)

    assert count == 0
    assert len(proposal.read_text(encoding="utf-8").splitlines()) == 1


def test_write_decoy_manifest_proposal_round_trips_through_manifest_reader(
    tmp_path: Path,
) -> None:
    from xic_extractor.alignment.identity_coherence.controls import (
        read_identity_controls_manifest,
    )

    bundle = _write_proposal_source_bundle(tmp_path / "serial")
    proposal = tmp_path / "proposal.tsv"

    write_decoy_manifest_proposal(bundle, proposal, max_decoys=1)

    entries = read_identity_controls_manifest(proposal)
    assert len(entries) == 1
    assert entries[0].control_type.value == "identity_decoy"
    assert entries[0].expected_mapping_status.value == "not_applicable"
    assert entries[0].decoy_generation_method.value == "rt_shift"
    assert entries[0].decoy_source_request_id == "ICR-1"


def test_run_validation_does_not_write_proposal_when_parity_fails(
    tmp_path: Path,
) -> None:
    proposal = tmp_path / "proposal.tsv"
    proposal.write_text("stale\n", encoding="utf-8")

    def fake_runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        output_dir = Path(command[command.index("--output-dir") + 1])
        bundle = _write_proposal_source_bundle(output_dir / "identity_coherence")
        if output_dir.name == "process":
            bundle.decisions_tsv.write_text("different\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "", "")

    result = run_validation(
        discovery_batch_index=tmp_path / "batch.csv",
        raw_dir=tmp_path,
        dll_dir=tmp_path,
        output_root=tmp_path / "out",
        controls_manifest=None,
        controls_manifest_proposal=proposal,
        runner=fake_runner,
    )

    assert result.failed_count > 0
    assert not proposal.exists()
```

Update the import block to include:

```python
write_decoy_manifest_proposal,
```

- [ ] **Step 2: Run tests to verify RED**

```powershell
uv run pytest tests\test_validate_identity_coherence_8raw.py -q
```

Expected: fail because `write_decoy_manifest_proposal` does not exist.

- [ ] **Step 3: Implement proposal writer**

Add constants near `VALIDATION_SUMMARY_COLUMNS`:

```python
# Keep this in sync with controls.py:REQUIRED_MANIFEST_FIELDS plus the optional
# fields read by _entry_from_row(); tests must round-trip proposals through the
# real manifest reader to catch drift.
CONTROL_MANIFEST_COLUMNS = (
    "control_id",
    "control_type",
    "control_name",
    "expected_mapping_status",
    "control_expected_behavior",
    "fragment_observation_mode",
    "precursor_tolerance_ppm",
    "product_tolerance_ppm",
    "cid_observed_loss_tolerance_ppm",
    "rt_tolerance_sec",
    "required_failure_reason_when_missed",
    "decision_id",
    "identity_family_id",
    "seed_candidate_id",
    "decoy_generation_method",
    "decoy_source_request_id",
    "decoy_fragment_tags",
    "positive_control_target_name",
    "positive_control_target_mz",
    "positive_control_target_rt_sec",
    "positive_control_mapping_error_ppm",
    "positive_control_mapping_delta_rt_sec",
    "control_notes",
)
```

Add:

```python
def write_decoy_manifest_proposal(
    serial_bundle: DiagnosticBundle,
    proposal_path: Path,
    *,
    max_decoys: int = 3,
) -> int:
    if max_decoys < 0:
        raise ValueError("max_decoys must be nonnegative")
    request_rows = _read_tsv_dict_rows(serial_bundle.requests_tsv)
    decision_rows = _read_tsv_dict_rows(serial_bundle.decisions_tsv)
    request_by_decision = {
        row.get("decision_id", ""): row
        for row in request_rows
        if row.get("decision_id")
    }
    proposal_rows: list[dict[str, str]] = []
    for decision in decision_rows:
        if len(proposal_rows) >= max_decoys:
            break
        if decision.get("seed_gate_class") != "coherent_seed":
            continue
        request = request_by_decision.get(decision.get("decision_id", ""))
        if request is None:
            continue
        if request.get("seed_candidate_id") != decision.get("seed_candidate_id"):
            continue
        if request.get("seed_sample") != decision.get("seed_sample"):
            continue
        if not _proposal_request_has_required_values(request):
            continue
        proposal_rows.append(
            _decoy_manifest_row(
                index=len(proposal_rows) + 1,
                request=request,
                decision=decision,
            )
        )
    _write_manifest_rows(proposal_path, proposal_rows)
    return len(proposal_rows)


def _proposal_request_has_required_values(request: dict[str, str]) -> bool:
    required = (
        "fragment_observation_mode",
        "precursor_tolerance_ppm",
        "product_tolerance_ppm",
        "cid_observed_loss_tolerance_ppm",
    )
    return all(request.get(field, "").strip() for field in required)


def _decoy_manifest_row(
    *,
    index: int,
    request: dict[str, str],
    decision: dict[str, str],
) -> dict[str, str]:
    request_id = request.get("request_id", "")
    return {
        "control_id": f"IDC-{index:03d}",
        "control_type": "identity_decoy",
        "control_name": f"Auto-proposed rt_shift decoy for {request_id}",
        "expected_mapping_status": "not_applicable",
        "control_expected_behavior": "decoy_rejected_before_promotion",
        "fragment_observation_mode": request.get("fragment_observation_mode", ""),
        "precursor_tolerance_ppm": request.get("precursor_tolerance_ppm", ""),
        "product_tolerance_ppm": request.get("product_tolerance_ppm", ""),
        "cid_observed_loss_tolerance_ppm": request.get(
            "cid_observed_loss_tolerance_ppm", ""
        ),
        "rt_tolerance_sec": "60.0",
        "required_failure_reason_when_missed": "seed_rt_outside_owner_peak",
        "decision_id": decision.get("decision_id", ""),
        "identity_family_id": decision.get("identity_family_id", ""),
        "seed_candidate_id": decision.get("seed_candidate_id", ""),
        "decoy_generation_method": "rt_shift",
        "decoy_source_request_id": request_id,
        "decoy_fragment_tags": "",
        "positive_control_target_name": "",
        "positive_control_target_mz": "",
        "positive_control_target_rt_sec": "",
        "positive_control_mapping_error_ppm": "",
        "positive_control_mapping_delta_rt_sec": "",
        "control_notes": (
            "auto-proposed identity decoy; review and rename to .reviewed.tsv "
            "before using as validation input"
        ),
    }


def _write_manifest_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=CONTROL_MANIFEST_COLUMNS,
            dialect="excel-tab",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    column: row.get(column, "")
                    for column in CONTROL_MANIFEST_COLUMNS
                }
            )
```

- [ ] **Step 4: Wire proposal output into `run_validation()`**

Change `run_validation()` signature:

```python
def run_validation(
    *,
    discovery_batch_index: Path,
    raw_dir: Path,
    dll_dir: Path,
    output_root: Path,
    controls_manifest: Path | None,
    controls_manifest_proposal: Path | None = None,
    runner: CommandRunner | None = None,
) -> ValidationResult:
```

After `compare_identity_coherence_bundles(...)`, add. This intentionally refuses
to write proposals from a failed parity run; stale proposal files are removed so
the CLI cannot leave a misleading artifact behind.

```python
    if controls_manifest_proposal is not None:
        if result.failed_count:
            controls_manifest_proposal.unlink(missing_ok=True)
        else:
            write_decoy_manifest_proposal(
                bundle_from_output_dir(serial_output),
                controls_manifest_proposal,
            )
```

- [ ] **Step 5: Verify and commit**

```powershell
uv run pytest tests\test_validate_identity_coherence_8raw.py -q
uv run ruff check scripts\validate_identity_coherence_8raw.py tests\test_validate_identity_coherence_8raw.py
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset add scripts\validate_identity_coherence_8raw.py tests\test_validate_identity_coherence_8raw.py
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset commit -m "feat: propose identity coherence decoy controls"
```

## Task 3: Add CLI Flag For Proposal Output

**Files:**

- Modify: `scripts/validate_identity_coherence_8raw.py`
- Modify: `tests/test_validate_identity_coherence_8raw.py`

- [ ] **Step 1: Add failing CLI test**

Append:

```python
def test_main_passes_controls_manifest_proposal_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    batch = tmp_path / "batch.csv"
    raw_dir = tmp_path / "raw"
    dll_dir = tmp_path / "dll"
    proposal = tmp_path / "proposal.tsv"
    batch.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir.mkdir()
    dll_dir.mkdir()
    seen: dict[str, object] = {}

    def fake_run_validation(**kwargs) -> ValidationResult:
        seen.update(kwargs)
        return ValidationResult(
            rows=(
                ValidationRow(
                    check_name="decisions_tsv_exact",
                    status="pass",
                    serial_value="1",
                    process_value="1",
                    details="same",
                ),
            )
        )

    monkeypatch.setattr(validation_script, "run_validation", fake_run_validation)

    code = validation_script.main(
        [
            "--discovery-batch-index",
            str(batch),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--output-root",
            str(tmp_path / "out"),
            "--write-controls-manifest-proposal",
            str(proposal),
        ]
    )

    assert code == 0
    assert seen["controls_manifest_proposal"] == proposal


def test_main_rejects_proposed_controls_manifest(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    batch = tmp_path / "batch.csv"
    raw_dir = tmp_path / "raw"
    dll_dir = tmp_path / "dll"
    proposed = tmp_path / "identity_coherence_controls_manifest.proposed.tsv"
    batch.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    proposed.write_text("control_id\n", encoding="utf-8")
    raw_dir.mkdir()
    dll_dir.mkdir()

    code = validation_script.main(
        [
            "--discovery-batch-index",
            str(batch),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--output-root",
            str(tmp_path / "out"),
            "--controls-manifest",
            str(proposed),
        ]
    )

    assert code == 2
    assert "must be reviewed and renamed" in capsys.readouterr().err
```

- [ ] **Step 2: Run test to verify RED**

```powershell
uv run pytest tests\test_validate_identity_coherence_8raw.py::test_main_passes_controls_manifest_proposal_path -q
```

Expected: fail because the CLI flag is not recognized or not forwarded.

- [ ] **Step 3: Implement CLI flag**

In `main()`, add:

```python
    parser.add_argument("--write-controls-manifest-proposal", type=Path)
```

Before accepting `--controls-manifest`, reject proposal paths:

```python
    if (
        args.controls_manifest is not None
        and ".proposed." in args.controls_manifest.name
    ):
        print(
            "proposal manifests must be reviewed and renamed before use as "
            "--controls-manifest",
            file=sys.stderr,
        )
        return 2
```

When calling `run_validation(...)`, pass:

```python
            controls_manifest_proposal=args.write_controls_manifest_proposal,
```

After the existing PASS print, add. The proposal line must never print for failed
parity runs, and the expected stdout order is PASS first, proposal second.

```python
        if args.write_controls_manifest_proposal is not None:
            print(
                "Controls manifest proposal: "
                f"{args.write_controls_manifest_proposal}"
            )
```

- [ ] **Step 4: Verify and commit**

```powershell
uv run pytest tests\test_validate_identity_coherence_8raw.py -q
uv run ruff check scripts\validate_identity_coherence_8raw.py tests\test_validate_identity_coherence_8raw.py
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset add scripts\validate_identity_coherence_8raw.py tests\test_validate_identity_coherence_8raw.py
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset commit -m "feat: expose identity controls proposal output"
```

## Task 4: Real 8RAW Validation Run

**Files:** none required. This task writes to `output\`.

- [ ] **Step 1: Regenerate discovery batch index if missing**

Run:

```powershell
$rawCount = (Get-ChildItem "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" -Filter *.raw | Measure-Object).Count
if ($rawCount -ne 8) {
  throw "Expected exactly 8 RAW files for this validation subset, got $rawCount"
}
if (-not (Test-Path output\discovery\timing_phase0_8raw\discovery_batch_index.csv)) {
  uv run python scripts\run_discovery.py `
    --raw-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" `
    --dll-dir "C:\Xcalibur\system\programs" `
    --output-dir output\discovery\timing_phase0_8raw `
    --timing-output output\diagnostics\timing_phase0_8raw\discovery_timing.json `
    --resolver-mode local_minimum
}
$indexCount = (Import-Csv output\discovery\timing_phase0_8raw\discovery_batch_index.csv | Measure-Object).Count
if ($indexCount -ne 8) {
  throw "Expected discovery_batch_index.csv to contain 8 rows, got $indexCount"
}
```

Expected if RAW/DLL are available:

```text
Discovery batch index: ...\output\discovery\timing_phase0_8raw\discovery_batch_index.csv
Timing JSON: ...\output\diagnostics\timing_phase0_8raw\discovery_timing.json
```

If discovery fails due to RAW/DLL environment, stop and report the failure. Do not synthesize a fake batch index.

- [ ] **Step 2: Run serial/process parity and write decoy proposal**

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
Controls manifest proposal: output\identity_coherence_8raw_validation\identity_coherence_controls_manifest_8raw.proposed.tsv
```

Interpretation:

- This proves serial/process parity for frozen identity coherence sidecars.
- This does not prove positive-control sensitivity unless a reviewed positive-control manifest is supplied.
- This does not validate final matrix filtering.

- [ ] **Step 3: Inspect proposal row count**

```powershell
Import-Csv `
  output\identity_coherence_8raw_validation\identity_coherence_controls_manifest_8raw.proposed.tsv `
  -Delimiter "`t" | Group-Object control_type | Select-Object Name,Count
```

Expected:

- `identity_decoy` rows may be present when coherent seed sources exist.
- A header-only proposal is acceptable if no coherent seed source exists; report that no decoy specificity evidence can be run yet.

- [ ] **Step 4: Optional reviewed-manifest run**

Only run this when the proposal has been reviewed and copied/renamed to a
reviewed manifest path. Never pass a `.proposed.tsv` file to
`--controls-manifest`; the CLI rejects it by design.

```powershell
$reviewedManifest = "output\identity_coherence_8raw_validation\identity_coherence_controls_manifest_8raw.reviewed.tsv"
if (-not (Test-Path $reviewedManifest)) {
  throw "Reviewed controls manifest not found: $reviewedManifest"
}
uv run python scripts\validate_identity_coherence_8raw.py `
  --discovery-batch-index output\discovery\timing_phase0_8raw\discovery_batch_index.csv `
  --raw-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" `
  --dll-dir "C:\Xcalibur\system\programs" `
  --output-root output\identity_coherence_8raw_validation_controls `
  --controls-manifest $reviewedManifest
```

If the manifest contains only decoys, the report must show positive controls as `not_assessed` and decoy rows as assessed. Do not call this full method validation.

## Task 5: Scope Guard And Verification

**Files:** no new files expected beyond Task 1-3 code changes.

- [ ] **Step 1: Run focused tests**

```powershell
uv run pytest tests\test_validate_identity_coherence_8raw.py tests\test_run_alignment.py tests\test_alignment_identity_coherence_adapter.py tests\alignment\identity_coherence\test_controls_evaluation.py -q
uv run ruff check scripts\validate_identity_coherence_8raw.py tests\test_validate_identity_coherence_8raw.py
```

Expected: tests and lint pass.

- [ ] **Step 2: Run boundary searches**

```powershell
rg -n "owner_backfill|primary_matrix|final_matrix|workbook|raw_reader|open_raw|extract_xic" scripts\validate_identity_coherence_8raw.py tests\test_validate_identity_coherence_8raw.py
rg -n "from xic_extractor\.alignment|import xic_extractor\.alignment|owner_matrix|pipeline\.run_alignment" scripts\validate_identity_coherence_8raw.py tests\test_validate_identity_coherence_8raw.py
rg -n "run_identity_coherence_diagnostic|identity_coherence_adapter|process_backend" scripts\validate_identity_coherence_8raw.py
```

Expected:

- No imports from RAW, Backfill, workbook, matrix, or alignment internals.
- Literal explanatory matches in report text are acceptable only if they are not imports or direct internal calls.

- [ ] **Step 3: Check changed files**

```powershell
$baseCommit = Get-Content output\identity_coherence_8raw_validation\.base_commit.txt
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset diff --name-only $baseCommit..HEAD
```

Expected code changes:

```text
scripts/validate_identity_coherence_8raw.py
tests/test_validate_identity_coherence_8raw.py
```

Expected output artifacts may exist under `output\`; do not stage them unless the user explicitly asks.

## Self-Review Checklist

- [ ] The validator still calls public `scripts/run_alignment.py`, not internal adapter functions.
- [ ] Controls interpretation reads frozen TSV outputs only.
- [ ] `CONTROL_MANIFEST_COLUMNS` covers every `controls.py:REQUIRED_MANIFEST_FIELDS` column and every optional field read by `_entry_from_row`; generated proposals round-trip through the real manifest reader.
- [ ] A controls manifest being present no longer means controls passed; the report uses actual `controls.tsv` rows.
- [ ] Positive controls remain `not_assessed` when no `positive_targeted_istd` rows exist.
- [ ] Decoy false promotion is a `fail` via `decoy_seed_gate_coherent`.
- [ ] The decoy proposal is clearly marked as review-required.
- [ ] Passing a `.proposed.tsv` path to `--controls-manifest` is rejected.
- [ ] The real 8RAW run regenerates missing discovery input instead of faking it.
- [ ] The real 8RAW run checks RAW file count and discovery index row count are both exactly 8.
- [ ] No final matrix, downstream filtering, or 85RAW readiness claim is introduced.

## Handoff

After this plan lands, the next decision is methodological rather than plumbing:

- If decoys are correctly rejected but positive controls are absent, choose targeted ISTD/stable rows for a reviewed positive-control manifest.
- Review proposal semantics before use: `expected_mapping_status=not_applicable` means identity decoys are not positive mapping controls; `seed_rt_outside_owner_peak` is the expected rt-shift audit reason, while `decoy_seed_gate_coherent` remains the false-promotion failure signal.
- 8RAW readiness remains `not_assessed` unless both reviewed positive controls and reviewed decoys pass.
- If any decoy reaches `coherent_seed`, stop and fix seed-gate/request-candidate identity handling before expanding to 85RAW.
- If serial/process parity fails, fix deterministic ordering at the adapter/writer source, not by sorting inside this validator.
