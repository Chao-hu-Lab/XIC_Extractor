# Identity Coherence Inline Adapter Slice 3: Diagnostic Runner And CLI Wiring

> Execution order: 3 of 3
> Depends on: Slice 1 and Slice 2 committed

## Shared Context

> Shared scope copied from the original monolithic plan. Each slice is executable only in the stated order.


In scope:

- Create an orchestration-edge adapter module outside `xic_extractor/alignment/identity_coherence/`.
- Convert pre-Backfill `DiscoveryCandidate` and `SampleLocalMS1Owner` evidence into `IdentityCoherenceRequest`, `SeedCandidateEvidence`, `CellCandidateEvidence`, and trace payloads.
- Retrieve candidate XIC traces through existing alignment RAW source protocols:
  - `raw_workers=1`: already-open parent `raw_sources`;
  - `raw_workers>1`: process jobs grouped by sample and chunked by `raw_xic_batch_size`.
- Evaluate rows through the existing domain pipeline and write the frozen output bundle.
- Optionally evaluate an existing TSV controls manifest against the generated records.
- Add opt-in `run_alignment()` keyword arguments and matching `scripts/run_alignment.py` flags.
- Preserve deterministic output ordering across serial and process retrieval.

Out of scope:

- No changes to `xic_extractor/raw_reader.py`, `xic_extractor/alignment/raw_sources.py`, `owner_backfill.py`, `ms1_index_source.py`, or any RAW/XIC retrieval implementation.
- No new process backend framework. The identity process worker must follow the existing `process_backend.py` job/result pattern and must not change owner build/backfill semantics.
- No post-hoc `--alignment-dir` report mode.
- No YAML identity-coherence config parsing; this slice uses `IdentityCoherenceConfig()` defaults and CLI-provided controls manifest only.
- No Backfill behavior, production matrix, workbook, report, downstream background/QC filtering, or statistics changes.
- No real 8RAW interpretation claim. This slice only makes the opt-in diagnostic runnable under the same worker/batch policy as alignment.

## Files

- Create: `xic_extractor/alignment/identity_coherence_adapter.py`
  - Own the orchestration adapter.
  - May import alignment ownership/candidate/raw-source/process contracts and identity-coherence domain functions.
  - Must not be imported by modules under `xic_extractor/alignment/identity_coherence/`.
- Modify: `xic_extractor/alignment/process_backend.py`
  - Add identity-trace process jobs/results only; reuse existing process runner helpers.
  - Must not change owner build/backfill worker behavior.
- Modify: `xic_extractor/alignment/pipeline.py`
  - Add opt-in parameters and call the adapter after pre-Backfill owner clustering and before optional pre-Backfill consolidation / owner Backfill.
- Modify: `xic_extractor/alignment/pipeline_outputs.py`
  - Add optional output-dir reporting for the diagnostic bundle.
- Modify: `scripts/run_alignment.py`
  - Add CLI flags and print the diagnostic output directory when emitted.
- Modify: `tests/test_alignment_pipeline.py`
  - Add opt-in pipeline integration tests.
- Create: `tests/test_alignment_identity_coherence_adapter.py`
  - Add adapter unit tests with synthetic candidates, owners, and fake RAW sources.
- Modify: `tests/test_alignment_process_backend.py`
  - Add no-RAW/fake-runner tests for identity trace process job grouping, ordering, and batching.
- Modify: `tests/test_run_alignment.py`
  - Add CLI flag parsing and propagation tests.
- Modify: `tests/alignment/identity_coherence/test_schema_contract.py`
  - Add dependency boundary test proving pure domain modules do not import the adapter.

## Domain Notes

- The adapter emits one seed-level request per pre-Backfill sample-local owner primary identity event.
- The adapter diagnostic input is the sample-local `OwnershipBuildResult`, not consolidated `owner_features`. When `preconsolidate_owner_families=True`, this slice still reports sample-local pre-consolidation identity coherence; it must not be described as the exact production Backfill input surface.
- `decision_id`, `request_id`, and `identity_family_id` are deterministic diagnostic IDs:
  - `ICD000001`, `ICR000001`, `ICF000001`, sorted by seed sample, owner apex RT, and seed candidate ID.
- A seed-gate-failed row must not schedule non-seed trace retrieval.
- Non-seed candidate pools are selected before trace retrieval using cheap pre-Backfill candidate metadata:
  - sample differs from the seed sample;
  - `candidate_id` differs from the seed candidate;
  - precursor m/z is within the request precursor tolerance;
  - candidate `best_seed_rt` is within `alignment_config.identity_rt_candidate_window_sec` of seed `best_seed_rt`;
  - candidate has finite positive MS1 peak morphology fields.
- Candidate traces are requested over each candidate's original `ms1_peak_rt_start..ms1_peak_rt_end` window. Do not crop all candidates to a common RT window.
- Missing RAW source or extraction exception becomes `blocked_infrastructure` at the trace-result layer and a blocked cell in the final diagnostic row.
- Trace retrieval counters are identity diagnostic counters only. They must be reported separately from existing Backfill counters.
- `raw_workers` and `raw_xic_batch_size` are execution policy, not identity evidence. Changing `raw_workers=1` to `raw_workers=8` or `raw_xic_batch_size=64` must not change decisions, row IDs, or TSV ordering. It may only change timing and retrieval counters.
- In process mode, identity trace requests are grouped by sample. Each worker opens that sample RAW once and evaluates request chunks with `extract_xic_many` when available, using the same batch-size semantics as existing owner build/backfill code.
- This implementation slice includes synthetic serial-vs-process parity tests for the orchestration boundary. Real 8RAW parity and interpretation remain follow-on validation work.
- The adapter uses existing `AlignmentConfig` values for identity request tolerances:
  - precursor tolerance: `alignment_config.preferred_ppm`;
  - product tolerance: `alignment_config.product_mz_tolerance_ppm`;
  - CID observed-loss tolerance: `alignment_config.observed_loss_tolerance_ppm`.
- `fragment_profile_hash="unavailable"` is a known adapter-slice caveat. It will add the existing `fragment_profile_hash_unavailable` request-builder flag to every diagnostic request until a follow-on slice passes the real profile hash.
- Diagnostic failure is fatal when the opt-in flag is enabled. The production alignment path is unchanged when the flag is off; when the user explicitly requests the diagnostic, a partial production run without the requested bundle is more misleading than a loud failure.
- Decoy controls only use `coherent_seed` source records. Review-only seed-gate-failed rows are still written and can be audited, but they are not valid decoy sources because they already failed Layer 1 before any synthetic identity perturbation.


## Slice Acceptance Gate

- Build diagnostic records, controls pass-through/evaluation, opt-in pipeline and CLI wiring.
- Keep diagnostic failure fatal only when the opt-in flag is enabled.
- Preserve production alignment behavior when the diagnostic flag is disabled.
- Commit after Task 3, Task 4, and final verification pass.

## Task 3: Diagnostic Record Builder And Controls

**Files:**
- Modify: `xic_extractor/alignment/identity_coherence_adapter.py`
- Test: `tests/test_alignment_identity_coherence_adapter.py`

- [ ] **Step 1: Write record-builder tests**

Append:

```python
from xic_extractor.alignment.identity_coherence_adapter import (
    IdentityCoherenceDiagnosticRun,
    assignment_status_by_candidate_id,
    run_identity_coherence_diagnostic,
)


def test_run_diagnostic_writes_outputs_for_pre_backfill_state(tmp_path) -> None:
    seed = _candidate("CAND-SEED", sample_stem="Sample_A", best_seed_rt=5.0)
    non_seed_1 = _candidate("CAND-B", sample_stem="Sample_B", best_seed_rt=5.02)
    non_seed_2 = _candidate("CAND-C", sample_stem="Sample_C", best_seed_rt=5.03)
    output_dir = tmp_path / "identity"

    result = run_identity_coherence_diagnostic(
        candidates=(seed, non_seed_1, non_seed_2),
        ownership=_ownership(_owner(seed)),
        sample_order=("Sample_A", "Sample_B", "Sample_C"),
        raw_sources={
            "Sample_A": FakeRawSource(),
            "Sample_B": FakeRawSource(),
            "Sample_C": FakeRawSource(),
        },
        raw_paths={},
        dll_dir=tmp_path,
        raw_workers=1,
        raw_xic_batch_size=64,
        output_dir=output_dir,
        alignment_config=AlignmentConfig(),
        fragment_profile_id="dna-cid-v1",
        fragment_profile_hash="hash1",
    )

    assert isinstance(result, IdentityCoherenceDiagnosticRun)
    assert len(result.records) == 1
    assert result.paths.requests_tsv.is_file()
    assert result.paths.decisions_tsv.is_file()
    assert result.paths.cell_evidence_tsv.is_file()
    assert result.paths.controls_tsv.is_file()
    assert result.paths.summary_md.is_file()
    assert result.context.raw_xic_request_count == 3
    assert result.context.xic_point_count == 9
    assert "Backfill" in result.paths.summary_md.read_text(encoding="utf-8")
    assert result.records[0].row_result.decision.seed_candidate_id == "CAND-SEED"


def test_run_diagnostic_does_not_retrieve_non_seed_traces_when_seed_gate_fails(
    tmp_path,
) -> None:
    seed = _candidate(
        "CAND-SEED",
        sample_stem="Sample_A",
        best_seed_rt=5.0,
    )
    bad_owner = replace(
        _owner(seed),
        owner_peak_start_rt=5.10,
        owner_peak_end_rt=5.20,
    )
    non_seed = _candidate("CAND-B", sample_stem="Sample_B", best_seed_rt=5.02)
    source_b = FakeRawSource()

    result = run_identity_coherence_diagnostic(
        candidates=(seed, non_seed),
        ownership=_ownership(bad_owner),
        sample_order=("Sample_A", "Sample_B"),
        raw_sources={"Sample_A": FakeRawSource(), "Sample_B": source_b},
        raw_paths={},
        dll_dir=tmp_path,
        raw_workers=1,
        raw_xic_batch_size=64,
        output_dir=tmp_path / "identity",
        alignment_config=AlignmentConfig(),
        fragment_profile_id="dna-cid-v1",
        fragment_profile_hash="hash1",
    )

    assert result.records[0].row_result.cells == ()
    assert source_b.calls == []
    assert result.context.raw_xic_request_count == 0


def test_run_diagnostic_evaluates_controls_manifest(tmp_path) -> None:
    seed = _candidate("CAND-SEED", sample_stem="Sample_A")
    manifest = tmp_path / "controls.tsv"
    manifest.write_text(
        "\t".join(
            [
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
                "seed_candidate_id",
                "positive_control_target_name",
                "positive_control_target_mz",
                "positive_control_target_rt_sec",
                "positive_control_mapping_error_ppm",
                "positive_control_mapping_delta_rt_sec",
            ]
        )
        + "\n"
        + "\t".join(
            [
                "CTRL-1",
                "positive_targeted_istd",
                "seed positive",
                "mapped",
                "would_primary",
                "cid_neutral_loss",
                "20",
                "20",
                "20",
                "60",
                "review_only_insufficient_support",
                "CAND-SEED",
                "seed positive",
                "500.0",
                "300.0",
                "0.0",
                "0.0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = run_identity_coherence_diagnostic(
        candidates=(seed,),
        ownership=_ownership(_owner(seed)),
        sample_order=("Sample_A",),
        raw_sources={"Sample_A": FakeRawSource()},
        raw_paths={},
        dll_dir=tmp_path,
        raw_workers=1,
        raw_xic_batch_size=64,
        output_dir=tmp_path / "identity",
        alignment_config=AlignmentConfig(),
        controls_manifest_path=manifest,
        fragment_profile_id="dna-cid-v1",
        fragment_profile_hash="hash1",
    )

    assert len(result.control_rows) == 1
    assert result.context.control_manifest_path == str(manifest)
    assert result.control_rows[0]["control_status"] == "assessed"
    assert result.control_rows[0]["control_pass"] in {True, "true"}


def test_run_diagnostic_process_mode_matches_serial_ordering(monkeypatch, tmp_path) -> None:
    seed = _candidate("CAND-SEED", sample_stem="Sample_A", best_seed_rt=5.0)
    non_seed_1 = _candidate("CAND-B", sample_stem="Sample_B", best_seed_rt=5.02)
    non_seed_2 = _candidate("CAND-C", sample_stem="Sample_C", best_seed_rt=5.03)
    candidates = (seed, non_seed_1, non_seed_2)
    ownership = _ownership(_owner(seed))

    serial = run_identity_coherence_diagnostic(
        candidates=candidates,
        ownership=ownership,
        sample_order=("Sample_A", "Sample_B", "Sample_C"),
        raw_sources={
            "Sample_A": FakeRawSource(),
            "Sample_B": FakeRawSource(),
            "Sample_C": FakeRawSource(),
        },
        raw_paths={},
        dll_dir=tmp_path,
        raw_workers=1,
        raw_xic_batch_size=64,
        output_dir=tmp_path / "serial",
        alignment_config=AlignmentConfig(),
        fragment_profile_id="dna-cid-v1",
        fragment_profile_hash="hash1",
    )

    def fake_process(requests, **kwargs):
        return type(
            "ProcessOutput",
            (),
            {
                "results": tuple(
                    IdentityCoherenceTraceResult(
                        request=request,
                        trace=CandidateTrace(
                            rt_min=(
                                request.rt_min,
                                (request.rt_min + request.rt_max) / 2.0,
                                request.rt_max,
                            ),
                            intensity=(0.0, 10.0, 0.0),
                        ),
                        status="pass",
                        raw_xic_request_count=1,
                        xic_point_count=3,
                    )
                    for request in requests
                ),
                "timing_stats": (),
            },
        )()

    monkeypatch.setattr(
        "xic_extractor.alignment.identity_coherence_adapter.run_identity_trace_process",
        fake_process,
    )
    process = run_identity_coherence_diagnostic(
        candidates=candidates,
        ownership=ownership,
        sample_order=("Sample_A", "Sample_B", "Sample_C"),
        raw_sources={},
        raw_paths={
            "Sample_A": tmp_path / "Sample_A.raw",
            "Sample_B": tmp_path / "Sample_B.raw",
            "Sample_C": tmp_path / "Sample_C.raw",
        },
        dll_dir=tmp_path,
        raw_workers=8,
        raw_xic_batch_size=64,
        output_dir=tmp_path / "process",
        alignment_config=AlignmentConfig(),
        fragment_profile_id="dna-cid-v1",
        fragment_profile_hash="hash1",
    )

    def row_signature(result):
        return [
            (
                record.seed_gate.resolved_request.request_id,
                record.row_result.decision.decision_id,
                record.row_result.decision.identity_family_id,
                record.row_result.decision.identity_decision,
            )
            for record in result.records
        ]

    assert row_signature(process) == row_signature(serial)
    assert [
        [cell.candidate_id for cell in record.row_result.cells]
        for record in process.records
    ] == [
        [cell.candidate_id for cell in record.row_result.cells]
        for record in serial.records
    ]
    assert [result.request.candidate_id for result in process.trace_results] == [
        result.request.candidate_id for result in serial.trace_results
    ]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
uv run pytest tests\test_alignment_identity_coherence_adapter.py::test_run_diagnostic_writes_outputs_for_pre_backfill_state tests\test_alignment_identity_coherence_adapter.py::test_run_diagnostic_does_not_retrieve_non_seed_traces_when_seed_gate_fails tests\test_alignment_identity_coherence_adapter.py::test_run_diagnostic_evaluates_controls_manifest tests\test_alignment_identity_coherence_adapter.py::test_run_diagnostic_process_mode_matches_serial_ordering -q
```

Expected: FAIL because `run_identity_coherence_diagnostic()` does not exist.

- [ ] **Step 3: Implement diagnostic runner**

Append imports:

```python
from pathlib import Path

from xic_extractor.alignment.identity_coherence.controls import (
    IdentityControlsConfig,
    IdentityDecoySource,
    evaluate_identity_controls,
    read_identity_controls_manifest,
)
from xic_extractor.alignment.identity_coherence.output import (
    IdentityCoherenceOutputContext,
    IdentityCoherenceOutputPaths,
    IdentityCoherenceOutputRecord,
    write_identity_coherence_outputs,
)
from xic_extractor.alignment.identity_coherence.row_evaluator import (
    evaluate_identity_coherence_row,
)
from xic_extractor.alignment.identity_coherence.schema import SeedGateClass
```

Add:

```python
@dataclass(frozen=True)
class IdentityCoherenceDiagnosticRun:
    records: tuple[IdentityCoherenceOutputRecord, ...]
    control_rows: tuple[Mapping[str, object], ...]
    trace_results: tuple[IdentityCoherenceTraceResult, ...]
    context: IdentityCoherenceOutputContext
    paths: IdentityCoherenceOutputPaths


def run_identity_coherence_diagnostic(
    *,
    candidates: Sequence[DiscoveryCandidate],
    ownership: OwnershipBuildResult,
    sample_order: Sequence[str],
    raw_sources: Mapping[str, IdentityCoherenceRawSource],
    raw_paths: Mapping[str, Path],
    dll_dir: Path,
    raw_workers: int,
    raw_xic_batch_size: int,
    output_dir: Path,
    alignment_config: AlignmentConfig,
    fragment_profile_id: str,
    fragment_profile_hash: str,
    config: IdentityCoherenceConfig = IdentityCoherenceConfig(),
    controls_manifest_path: Path | None = None,
    controls_config: IdentityControlsConfig = IdentityControlsConfig(),
) -> IdentityCoherenceDiagnosticRun:
    sources = build_identity_coherence_seed_sources(
        candidates=candidates,
        ownership=ownership,
        alignment_config=alignment_config,
        fragment_profile_id=fragment_profile_id,
        fragment_profile_hash=fragment_profile_hash,
        config=config,
    )
    assignment_by_candidate_id = assignment_status_by_candidate_id(ownership)
    records: list[IdentityCoherenceOutputRecord] = []
    trace_results: list[IdentityCoherenceTraceResult] = []
    for source in sources:
        record, source_trace_results = _record_for_seed_source(
            source,
            candidates,
            assignment_by_candidate_id=assignment_by_candidate_id,
            sample_order=tuple(sample_order),
            raw_sources=raw_sources,
            raw_paths=raw_paths,
            dll_dir=dll_dir,
            raw_workers=raw_workers,
            raw_xic_batch_size=raw_xic_batch_size,
            alignment_config=alignment_config,
            config=config,
        )
        records.append(record)
        trace_results.extend(source_trace_results)

    decoy_sources = tuple(
        IdentityDecoySource(
            source_record=record,
            seed_evidence=source.seed_evidence,
            owner_like=source.owner,
            owner_assignment_status=source.owner_assignment_status,
        )
        for source, record in zip(sources, records, strict=True)
        if record.seed_gate.seed_gate_class == SeedGateClass.COHERENT_SEED
    )
    if controls_manifest_path is None:
        control_rows: tuple[Mapping[str, object], ...] = ()
        manifest_path = "not_provided"
    else:
        entries = read_identity_controls_manifest(controls_manifest_path)
        evaluation = evaluate_identity_controls(
            entries,
            records=records,
            decoy_sources=decoy_sources,
            config=controls_config,
            seed_gate_config=config.seed_gate,
        )
        control_rows = evaluation.rows
        manifest_path = str(controls_manifest_path)

    context = IdentityCoherenceOutputContext(
        command="xic-align-cli",
        mode=(
            "inline_pre_backfill_process"
            if raw_workers > 1
            else "inline_pre_backfill_serial"
        ),
        input_source="run_alignment.pre_backfill_ownership",
        control_manifest_path=manifest_path,
        raw_xic_request_count=sum(
            result.raw_xic_request_count for result in trace_results
        ),
        xic_point_count=sum(result.xic_point_count for result in trace_results),
        projected_85raw_identity_request_count=None,
        max_projected_85raw_identity_xic_requests=(
            config.engineering.max_projected_85raw_identity_xic_requests
        ),
        max_infrastructure_blocked_fraction=(
            config.engineering.max_infrastructure_blocked_fraction
        ),
        firewall_fixture_status="not_assessed",
        spawn_payload_smoke_status="not_assessed",
    )
    paths = write_identity_coherence_outputs(
        output_dir,
        records,
        context=context,
        control_rows=control_rows,
    )
    return IdentityCoherenceDiagnosticRun(
        records=tuple(records),
        control_rows=control_rows,
        trace_results=tuple(trace_results),
        context=context,
        paths=paths,
    )


def _record_for_seed_source(
    source: IdentityCoherenceSeedSource,
    candidates: Sequence[DiscoveryCandidate],
    *,
    assignment_by_candidate_id: Mapping[str, str],
    sample_order: tuple[str, ...],
    raw_sources: Mapping[str, IdentityCoherenceRawSource],
    raw_paths: Mapping[str, Path],
    dll_dir: Path,
    raw_workers: int,
    raw_xic_batch_size: int,
    alignment_config: AlignmentConfig,
    config: IdentityCoherenceConfig,
) -> tuple[IdentityCoherenceOutputRecord, tuple[IdentityCoherenceTraceResult, ...]]:
    if source.seed_gate.seed_gate_class != SeedGateClass.COHERENT_SEED:
        row = evaluate_identity_coherence_row(
            source.seed_gate,
            source.seed_evidence,
            None,
            (),
            config,
            identity_family_id=source.identity_family_id,
            assessed_sample_count=len(sample_order),
        )
        return IdentityCoherenceOutputRecord(source.seed_gate, row), ()

    candidate_pool = tuple(
        candidate
        for candidate in candidates
        if candidate_is_non_seed_pool_member(
            source.request,
            candidate,
            seed_candidate=source.seed_candidate,
            config=alignment_config,
        )
    )
    trace_requests = [
        trace_request_for_candidate(
            source=source,
            candidate=source.seed_candidate,
            ppm_tolerance=alignment_config.preferred_ppm,
        )
    ]
    trace_requests.extend(
        trace_request_for_candidate(
            source=source,
            candidate=candidate,
            ppm_tolerance=alignment_config.preferred_ppm,
        )
        for candidate in candidate_pool
    )
    trace_results = list(
        retrieve_identity_coherence_traces(
            tuple(trace_requests),
            raw_sources=raw_sources,
            raw_paths=raw_paths,
            dll_dir=dll_dir,
            raw_workers=raw_workers,
            raw_xic_batch_size=raw_xic_batch_size,
        )
    )
    trace_by_candidate_id = {
        result.request.candidate_id: result for result in trace_results
    }
    seed_trace_result = trace_by_candidate_id[source.seed_candidate.candidate_id]
    seed_cell = build_cell_candidate_evidence(
        source.seed_candidate,
        owner_assignment_status=source.owner_assignment_status,
        trace_result=seed_trace_result,
    )
    non_seed_cells: list[CellCandidateEvidence] = []
    for candidate in candidate_pool:
        trace_result = trace_by_candidate_id[candidate.candidate_id]
        non_seed_cells.append(
            build_cell_candidate_evidence(
                candidate,
                owner_assignment_status=assignment_by_candidate_id.get(
                    candidate.candidate_id,
                    "unresolved",
                ),
                trace_result=trace_result,
            )
        )
    row = evaluate_identity_coherence_row(
        source.seed_gate,
        source.seed_evidence,
        seed_cell,
        tuple(non_seed_cells),
        config,
        identity_family_id=source.identity_family_id,
        assessed_sample_count=len(sample_order),
    )
    return IdentityCoherenceOutputRecord(source.seed_gate, row), tuple(trace_results)
```

- [ ] **Step 4: Run record-builder tests**

Run:

```powershell
uv run pytest tests\test_alignment_identity_coherence_adapter.py::test_run_diagnostic_writes_outputs_for_pre_backfill_state tests\test_alignment_identity_coherence_adapter.py::test_run_diagnostic_does_not_retrieve_non_seed_traces_when_seed_gate_fails tests\test_alignment_identity_coherence_adapter.py::test_run_diagnostic_evaluates_controls_manifest tests\test_alignment_identity_coherence_adapter.py::test_run_diagnostic_process_mode_matches_serial_ordering -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor\alignment\identity_coherence_adapter.py tests\test_alignment_identity_coherence_adapter.py
git commit -m "feat: run identity coherence diagnostic records"
```

Use the `git -c safe.directory=...` prefix from Task 1 Step 0 if plain `git` is rejected in this worktree.

## Task 4: Opt-In Pipeline And CLI Wiring

**Files:**
- Modify: `xic_extractor/alignment/pipeline_outputs.py`
- Modify: `xic_extractor/alignment/pipeline.py`
- Modify: `scripts/run_alignment.py`
- Test: `tests/test_alignment_pipeline.py`
- Test: `tests/test_run_alignment.py`

- [ ] **Step 1: Write pipeline tests**

Before adding these tests, verify the existing test helpers still exist in `tests/test_alignment_pipeline.py`: `_write_batch`, `_patch_owner_pipeline_to_matrix`, `FakeRawOpener`, `_peak_config`, `pipeline_module`, `AlignmentConfig`, and `OwnershipBuildResult`. They exist in the current worktree; if any are renamed before implementation, update this plan's snippets rather than creating duplicate helpers.

Append to `tests/test_alignment_pipeline.py`:

```python
def test_run_alignment_emits_identity_coherence_diagnostic_when_opted_in(
    tmp_path,
    monkeypatch,
):
    batch_index = _write_batch(tmp_path, ("Sample_A",))
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "Sample_A.raw").write_text("raw", encoding="utf-8")
    _patch_owner_pipeline_to_matrix(monkeypatch)
    calls = {}

    def fake_build_owners(candidates, **kwargs):
        candidate = tuple(candidates)[0]
        from xic_extractor.alignment.ownership import OwnershipBuildResult
        from xic_extractor.alignment.ownership_models import (
            IdentityEvent,
            OwnerAssignment,
            SampleLocalMS1Owner,
        )

        event = IdentityEvent(
            candidate_id=candidate.candidate_id,
            sample_stem=candidate.sample_stem,
            raw_file=str(candidate.raw_file),
            neutral_loss_tag=candidate.neutral_loss_tag,
            precursor_mz=candidate.precursor_mz,
            product_mz=candidate.product_mz,
            observed_neutral_loss_da=candidate.observed_neutral_loss_da,
            seed_rt=candidate.best_seed_rt,
            evidence_score=candidate.evidence_score,
            seed_event_count=candidate.seed_event_count,
        )
        owner = SampleLocalMS1Owner(
            owner_id="OWN-1",
            sample_stem=candidate.sample_stem,
            raw_file=str(candidate.raw_file),
            precursor_mz=candidate.precursor_mz,
            owner_apex_rt=float(candidate.ms1_apex_rt),
            owner_peak_start_rt=float(candidate.ms1_peak_rt_start),
            owner_peak_end_rt=float(candidate.ms1_peak_rt_end),
            owner_area=float(candidate.ms1_area),
            owner_height=float(candidate.ms1_height),
            primary_identity_event=event,
            supporting_events=(),
            identity_conflict=False,
            assignment_reason="primary_identity_event",
        )
        return OwnershipBuildResult(
            owners=(owner,),
            assignments=(
                OwnerAssignment(
                    candidate_id=candidate.candidate_id,
                    owner_id="OWN-1",
                    assignment_status="primary",
                    reason="primary_identity_event",
                ),
            ),
            ambiguous_records=(),
        )

    def fake_diagnostic(**kwargs):
        calls.update(kwargs)

        class Result:
            records = ()
            context = type(
                "Context",
                (),
                {"raw_xic_request_count": 0, "xic_point_count": 0},
            )()

        return Result()

    monkeypatch.setattr(pipeline_module, "build_sample_local_owners", fake_build_owners)
    monkeypatch.setattr(
        pipeline_module,
        "run_identity_coherence_diagnostic",
        fake_diagnostic,
    )

    outputs = pipeline_module.run_alignment(
        discovery_batch_index=batch_index,
        raw_dir=raw_dir,
        dll_dir=tmp_path,
        output_dir=tmp_path / "out",
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
        raw_opener=FakeRawOpener(),
        emit_identity_coherence_diagnostic=True,
        identity_coherence_output_dir=tmp_path / "identity",
    )

    assert calls["output_dir"] == tmp_path / "identity"
    assert calls["fragment_profile_id"] == "alignment-cid-neutral-loss-v0.4"
    assert outputs.identity_coherence_output_dir == tmp_path / "identity"


def test_run_alignment_passes_identity_coherence_worker_policy(
    tmp_path,
    monkeypatch,
):
    batch_index = _write_batch(tmp_path, ("Sample_A",))
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "Sample_A.raw").write_text("raw", encoding="utf-8")

    calls = {}

    def fake_build_owners(*args, **kwargs):
        return type(
            "OwnerBuildOutput",
            (),
            {
                "ownership": OwnershipBuildResult(
                    owners=(),
                    assignments=(),
                    ambiguous_records=(),
                ),
                "timing_stats": (),
            },
        )()

    def fake_backfill(*args, **kwargs):
        return type("BackfillOutput", (), {"cells": (), "timing_stats": ()})()

    def fake_diagnostic(**kwargs):
        calls.update(kwargs)

        class Result:
            records = ()
            context = type(
                "Context",
                (),
                {"raw_xic_request_count": 0, "xic_point_count": 0},
            )()

        return Result()

    monkeypatch.setattr(pipeline_module, "run_owner_build_process", fake_build_owners)
    monkeypatch.setattr(pipeline_module, "run_owner_backfill_process", fake_backfill)
    monkeypatch.setattr(
        pipeline_module,
        "run_identity_coherence_diagnostic",
        fake_diagnostic,
    )

    pipeline_module.run_alignment(
        discovery_batch_index=batch_index,
        raw_dir=raw_dir,
        dll_dir=tmp_path,
        output_dir=tmp_path / "out",
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
        raw_workers=8,
        raw_xic_batch_size=64,
        emit_identity_coherence_diagnostic=True,
    )

    assert calls["raw_workers"] == 8
    assert calls["raw_xic_batch_size"] == 64


def test_identity_coherence_diagnostic_does_not_change_backfill_inputs(
    tmp_path,
    monkeypatch,
):
    batch_index = _write_batch(tmp_path, ("Sample_A",))
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "Sample_A.raw").write_text("raw", encoding="utf-8")
    captured_features = []

    _patch_owner_pipeline_to_matrix(monkeypatch)

    def fake_backfill(features, *, sample_order, raw_sources, **kwargs):
        captured_features.append(tuple(feature.feature_family_id for feature in features))
        return ()

    monkeypatch.setattr(pipeline_module, "build_owner_backfill_cells", fake_backfill)
    monkeypatch.setattr(
        pipeline_module,
        "run_identity_coherence_diagnostic",
        lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("diagnostic must not run when disabled")
        ),
    )

    disabled = pipeline_module.run_alignment(
        discovery_batch_index=batch_index,
        raw_dir=raw_dir,
        dll_dir=tmp_path,
        output_dir=tmp_path / "disabled",
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
        raw_opener=FakeRawOpener(),
    )
    disabled_features = captured_features[-1]
    monkeypatch.setattr(
        pipeline_module,
        "run_identity_coherence_diagnostic",
        lambda **kwargs: type(
            "DiagnosticRun",
            (),
            {
                "records": (),
                "context": type(
                    "Context",
                    (),
                    {"raw_xic_request_count": 0, "xic_point_count": 0},
                )(),
            },
        )(),
    )
    enabled = pipeline_module.run_alignment(
        discovery_batch_index=batch_index,
        raw_dir=raw_dir,
        dll_dir=tmp_path,
        output_dir=tmp_path / "enabled",
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
        raw_opener=FakeRawOpener(),
        emit_identity_coherence_diagnostic=True,
    )

    assert captured_features[-1] == disabled_features
    assert disabled.identity_coherence_output_dir is None
    assert enabled.identity_coherence_output_dir == tmp_path / "enabled" / "identity_coherence"


def test_run_alignment_propagates_identity_coherence_diagnostic_errors(
    tmp_path,
    monkeypatch,
):
    batch_index = _write_batch(tmp_path, ("Sample_A",))
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "Sample_A.raw").write_text("raw", encoding="utf-8")
    _patch_owner_pipeline_to_matrix(monkeypatch)

    def failing_diagnostic(**kwargs):
        raise RuntimeError("identity diagnostic failed")

    monkeypatch.setattr(
        pipeline_module,
        "run_identity_coherence_diagnostic",
        failing_diagnostic,
    )

    with pytest.raises(RuntimeError, match="identity diagnostic failed"):
        pipeline_module.run_alignment(
            discovery_batch_index=batch_index,
            raw_dir=raw_dir,
            dll_dir=tmp_path,
            output_dir=tmp_path / "out",
            alignment_config=AlignmentConfig(),
            peak_config=_peak_config(),
            raw_opener=FakeRawOpener(),
            emit_identity_coherence_diagnostic=True,
        )
```

Add to `tests/test_run_alignment.py`:

```python
def test_run_alignment_cli_passes_identity_coherence_flags(monkeypatch, tmp_path):
    batch = tmp_path / "batch.csv"
    raw_dir = tmp_path / "raw"
    dll_dir = tmp_path / "dll"
    out_dir = tmp_path / "out"
    controls = tmp_path / "controls.tsv"
    batch.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir.mkdir()
    dll_dir.mkdir()
    controls.write_text("control_id\n", encoding="utf-8")
    seen = {}

    def fake_run_alignment(**kwargs):
        seen.update(kwargs)
        return AlignmentRunOutputs(
            identity_coherence_output_dir=out_dir / "identity",
        )

    monkeypatch.setattr(run_alignment, "run_alignment", fake_run_alignment)

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(batch),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--output-dir",
            str(out_dir),
            "--emit-identity-coherence-diagnostic",
            "--identity-coherence-output-dir",
            str(out_dir / "identity"),
            "--identity-coherence-controls-manifest",
            str(controls),
        ]
    )

    assert code == 0
    assert seen["emit_identity_coherence_diagnostic"] is True
    assert seen["identity_coherence_output_dir"] == out_dir / "identity"
    assert seen["identity_coherence_controls_manifest"] == controls


def test_run_alignment_cli_ignores_identity_manifest_when_diagnostic_disabled(
    monkeypatch,
    tmp_path,
):
    batch = tmp_path / "batch.csv"
    raw_dir = tmp_path / "raw"
    dll_dir = tmp_path / "dll"
    out_dir = tmp_path / "out"
    missing_controls = tmp_path / "missing-controls.tsv"
    batch.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir.mkdir()
    dll_dir.mkdir()
    seen = {}

    def fake_run_alignment(**kwargs):
        seen.update(kwargs)
        return AlignmentRunOutputs()

    monkeypatch.setattr(run_alignment, "run_alignment", fake_run_alignment)

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(batch),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--output-dir",
            str(out_dir),
            "--identity-coherence-controls-manifest",
            str(missing_controls),
        ]
    )

    assert code == 0
    assert seen["emit_identity_coherence_diagnostic"] is False
    assert seen["identity_coherence_controls_manifest"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
uv run pytest tests\test_alignment_pipeline.py::test_run_alignment_emits_identity_coherence_diagnostic_when_opted_in tests\test_alignment_pipeline.py::test_run_alignment_passes_identity_coherence_worker_policy tests\test_alignment_pipeline.py::test_identity_coherence_diagnostic_does_not_change_backfill_inputs tests\test_alignment_pipeline.py::test_run_alignment_propagates_identity_coherence_diagnostic_errors tests\test_run_alignment.py::test_run_alignment_cli_passes_identity_coherence_flags tests\test_run_alignment.py::test_run_alignment_cli_ignores_identity_manifest_when_diagnostic_disabled -q
```

Expected: FAIL because pipeline/CLI wiring does not exist.

- [ ] **Step 3: Add output path surface**

Modify `AlignmentRunOutputs` in `pipeline_outputs.py`:

```python
@dataclass(frozen=True)
class AlignmentRunOutputs:
    workbook: Path | None = None
    review_html: Path | None = None
    review_tsv: Path | None = None
    matrix_tsv: Path | None = None
    cells_tsv: Path | None = None
    integration_audit_tsv: Path | None = None
    backfill_seed_audit_tsv: Path | None = None
    status_matrix_tsv: Path | None = None
    event_to_owner_tsv: Path | None = None
    ambiguous_owners_tsv: Path | None = None
    edge_evidence_tsv: Path | None = None
    identity_coherence_output_dir: Path | None = None
```

- [ ] **Step 4: Wire the pipeline opt-in hook**

In `pipeline.py`, import:

```python
from xic_extractor.alignment.identity_coherence_adapter import (
    run_identity_coherence_diagnostic,
)
```

Extend `run_alignment()` signature:

```python
    emit_identity_coherence_diagnostic: bool = False,
    identity_coherence_output_dir: Path | None = None,
    identity_coherence_controls_manifest: Path | None = None,
```

Add this call after the `alignment.cluster_owners` stage and before optional `pre_backfill_consolidation` / `alignment.owner_backfill`:

```python
        identity_output_dir = (
            identity_coherence_output_dir
            if identity_coherence_output_dir is not None
            else output_dir / "identity_coherence"
        )
        identity_diagnostic_emitted = False
        if emit_identity_coherence_diagnostic:
            with recorder.stage("alignment.identity_coherence_diagnostic") as stage:
                diagnostic_run = run_identity_coherence_diagnostic(
                    candidates=candidates,
                    ownership=ownership,
                    sample_order=batch.sample_order,
                    raw_sources=raw_sources,
                    raw_paths=raw_paths,
                    dll_dir=dll_dir,
                    raw_workers=raw_workers,
                    raw_xic_batch_size=raw_xic_batch_size,
                    output_dir=identity_output_dir,
                    alignment_config=alignment_config,
                    controls_manifest_path=identity_coherence_controls_manifest,
                    fragment_profile_id="alignment-cid-neutral-loss-v0.4",
                    fragment_profile_hash="unavailable",
                )
                identity_diagnostic_emitted = True
                stage.metrics["record_count"] = len(diagnostic_run.records)
                stage.metrics["raw_xic_request_count"] = (
                    diagnostic_run.context.raw_xic_request_count or 0
                )
                stage.metrics["xic_point_count"] = (
                    diagnostic_run.context.xic_point_count or 0
                )
```

Before returning `outputs`, replace it with:

```python
        if identity_diagnostic_emitted:
            outputs = replace(
                outputs,
                identity_coherence_output_dir=identity_output_dir,
            )
        return outputs
```

Also import `replace` from `dataclasses` at the top of `pipeline.py`.

- [ ] **Step 5: Add CLI flags**

In `scripts/run_alignment.py`, add parser args:

```python
    parser.add_argument(
        "--emit-identity-coherence-diagnostic",
        action="store_true",
        help=(
            "Opt-in non-mutating pre-Backfill identity coherence diagnostic. "
            "Uses the same raw-workers/raw-xic-batch-size execution policy as alignment."
        ),
    )
    parser.add_argument(
        "--identity-coherence-output-dir",
        type=Path,
        help=(
            "Output directory for untargeted identity coherence TSV/summary bundle. "
            "Defaults to <output-dir>/identity_coherence when diagnostic is enabled."
        ),
    )
    parser.add_argument(
        "--identity-coherence-controls-manifest",
        type=Path,
        help="Optional TSV controls manifest for the identity coherence diagnostic.",
    )
```

After existing input validation, add:

```python
    if args.emit_identity_coherence_diagnostic:
        identity_controls_manifest = (
            args.identity_coherence_controls_manifest.resolve()
            if args.identity_coherence_controls_manifest is not None
            else None
        )
    else:
        identity_controls_manifest = None
    if (
        identity_controls_manifest is not None
        and not identity_controls_manifest.is_file()
    ):
        print(
            (
                f"{identity_controls_manifest}: "
                "identity coherence controls manifest does not exist"
            ),
            file=sys.stderr,
        )
        return 2
```

Pass the flags into `run_alignment()`:

```python
            emit_identity_coherence_diagnostic=(
                args.emit_identity_coherence_diagnostic
            ),
            identity_coherence_output_dir=(
                args.identity_coherence_output_dir.resolve()
                if args.identity_coherence_output_dir is not None
                else None
            ),
            identity_coherence_controls_manifest=(
                identity_controls_manifest
            ),
```

Print the output path:

```python
    if outputs.identity_coherence_output_dir is not None:
        print(f"Identity coherence diagnostic: {outputs.identity_coherence_output_dir}")
```

- [ ] **Step 6: Run pipeline/CLI tests**

Run:

```powershell
uv run pytest tests\test_alignment_pipeline.py::test_run_alignment_emits_identity_coherence_diagnostic_when_opted_in tests\test_alignment_pipeline.py::test_run_alignment_passes_identity_coherence_worker_policy tests\test_alignment_pipeline.py::test_identity_coherence_diagnostic_does_not_change_backfill_inputs tests\test_alignment_pipeline.py::test_run_alignment_propagates_identity_coherence_diagnostic_errors tests\test_run_alignment.py::test_run_alignment_cli_passes_identity_coherence_flags tests\test_run_alignment.py::test_run_alignment_cli_ignores_identity_manifest_when_diagnostic_disabled -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add xic_extractor\alignment\pipeline_outputs.py xic_extractor\alignment\pipeline.py scripts\run_alignment.py tests\test_alignment_pipeline.py tests\test_run_alignment.py
git commit -m "feat: wire opt-in identity coherence diagnostic"
```

Use the `git -c safe.directory=...` prefix from Task 1 Step 0 if plain `git` is rejected in this worktree.

## Task 5: Verification And Scope Guard

**Files:**
- Modify: `tests/alignment/identity_coherence/test_schema_contract.py`
- Test: multiple

- [ ] **Step 1: Add scope guard test**

Append to `tests/alignment/identity_coherence/test_schema_contract.py`:

```python
def test_inline_adapter_does_not_modify_raw_or_backfill_modules() -> None:
    root = Path(__file__).resolve().parents[3]
    adapter_text = (
        root
        / "xic_extractor"
        / "alignment"
        / "identity_coherence_adapter.py"
    ).read_text(encoding="utf-8")
    forbidden = (
        "from xic_extractor.raw_reader import",
        "import xic_extractor.raw_reader",
        "from xic_extractor.alignment.owner_backfill import",
        "from xic_extractor.alignment.backfill import",
        "source_for_owner_backfill_backend",
        "timed_owner_backfill_sources",
    )
    assert not any(token in adapter_text for token in forbidden)
```

- [ ] **Step 2: Run focused identity coherence tests**

Run:

```powershell
uv run pytest tests\alignment\identity_coherence tests\test_alignment_identity_coherence_adapter.py tests\test_alignment_process_backend.py -q
```

Expected: PASS.

- [ ] **Step 3: Run pipeline and CLI focused tests**

Run:

```powershell
uv run pytest tests\test_alignment_pipeline.py tests\test_run_alignment.py -q
```

Expected: PASS.

- [ ] **Step 4: Run lint**

Run:

```powershell
uv run ruff check xic_extractor\alignment\identity_coherence_adapter.py xic_extractor\alignment\process_backend.py xic_extractor\alignment\pipeline.py xic_extractor\alignment\pipeline_outputs.py scripts\run_alignment.py tests\test_alignment_identity_coherence_adapter.py tests\test_alignment_process_backend.py tests\test_alignment_pipeline.py tests\test_run_alignment.py tests\alignment\identity_coherence\test_schema_contract.py
```

Expected: PASS.

- [ ] **Step 5: Run full suite**

Run outside the sandbox if Windows process-spawn tests hit named-pipe permission errors:

```powershell
uv run pytest --tb=short -q
```

Expected: PASS or known Windows sandbox process-spawn permission error followed by a successful escalated rerun.

- [ ] **Step 6: Scope diff guard**

Run:

```powershell
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset diff --name-only
```

Expected changed files are limited to:

```text
scripts/run_alignment.py
tests/alignment/identity_coherence/test_schema_contract.py
tests/test_alignment_identity_coherence_adapter.py
tests/test_alignment_process_backend.py
tests/test_alignment_pipeline.py
tests/test_run_alignment.py
xic_extractor/alignment/identity_coherence_adapter.py
xic_extractor/alignment/pipeline.py
xic_extractor/alignment/pipeline_outputs.py
xic_extractor/alignment/process_backend.py
```

This command must only show the pending Task 5 guard test before the final commit. If the diff contains RAW reader implementations, Backfill behavior modules, workbook/report renderers, output workbook code, downstream filters, or discovery algorithms, stop and justify before continuing.

- [ ] **Step 7: Final commit**

```powershell
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset add tests\alignment\identity_coherence\test_schema_contract.py
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset commit -m "test: guard identity coherence adapter boundaries"
```

- [ ] **Step 8: Final slice diff guard**

Run:

```powershell
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset diff --name-only <base_commit_before_task1>..HEAD
```

Expected: the committed slice is limited to the files listed above. If the diff contains RAW reader implementations, Backfill behavior modules, workbook/report renderers, output workbook code, downstream filters, or discovery algorithms, stop and justify before continuing.

## Self-Review Checklist

- [ ] The adapter is opt-in and does not run unless explicitly requested.
- [ ] The diagnostic hook runs before owner Backfill.
- [ ] `raw_workers=8` and `raw_xic_batch_size=64` are accepted and passed into identity trace retrieval.
- [ ] No pure domain module under `xic_extractor/alignment/identity_coherence/` imports the orchestration adapter.
- [ ] The adapter may import `process_backend` only for identity trace retrieval, and does not import `raw_reader`, `owner_backfill`, `backfill`, workbook, report, or downstream filter modules.
- [ ] Process workers convert identity trace requests to `XICRequest` before calling RAW batch APIs.
- [ ] Process-mode extraction failures become per-request `blocked_infrastructure` results, not whole-diagnostic crashes.
- [ ] Seed-gate-failed rows do not schedule non-seed trace retrieval.
- [ ] Candidate traces use each candidate's original MS1 peak boundaries.
- [ ] Trace counters in the summary are identity diagnostic counters, not Backfill counters.
- [ ] Controls are validation-only and cannot mutate identity decisions.
- [ ] This slice is not described as 8RAW-interpreted, 85RAW-ready, or production-mutating.

## Follow-On Slice

After this plan lands, the next implementation plan should prove real-data serial-vs-process diagnostic parity on the agreed 8RAW subset with `raw_workers=8` and `raw_xic_batch_size=64`, then review the opt-in diagnostic bundle. This plan already includes synthetic serial-vs-process ordering parity; the follow-on must treat 8RAW output as diagnostic evidence only, not as a final Backfill or matrix behavior change.
