# Identity Coherence Inline Adapter Slice 1: Source Mapping

> Execution order: 1 of 3
> Depends on: Committed identity-coherence domain/output/controls slices

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

- Build and test seed source mapping without reading RAW files.
- Commit after Task 1 passes.
- Do not start Slice 2 until this slice is committed.

## Task 1: Adapter Source Mapping Without RAW

**Files:**
- Create: `xic_extractor/alignment/identity_coherence_adapter.py`
- Test: `tests/test_alignment_identity_coherence_adapter.py`
- Test: `tests/alignment/identity_coherence/test_schema_contract.py`

- [ ] **Step 0: Capture base commit and verify git safety**

Run:

```powershell
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset status --short
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset rev-parse HEAD
```

Expected: no unrelated tracked changes. Save the base commit for the Task 5 scope diff guard. Use `git -c safe.directory=...` in this worktree if normal `git` commands hit Windows dubious-ownership checks.

- [ ] **Step 1: Write source-mapping tests**

Create `tests/test_alignment_identity_coherence_adapter.py` with these imports and helpers:

```python
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.identity_coherence_adapter import (
    IdentityCoherenceSeedSource,
    build_identity_coherence_seed_sources,
    candidate_identity_family_id,
    candidate_is_non_seed_pool_member,
)
from xic_extractor.alignment.ownership import OwnershipBuildResult
from xic_extractor.alignment.ownership_models import (
    IdentityEvent,
    OwnerAssignment,
    SampleLocalMS1Owner,
)
from xic_extractor.discovery.models import DiscoveryCandidate


def _candidate(
    candidate_id: str,
    *,
    sample_stem: str = "Sample_A",
    precursor_mz: float = 500.0,
    product_mz: float = 384.0,
    observed_loss: float = 116.0,
    best_seed_rt: float = 5.0,
    apex_rt: float | None = 5.0,
    start_rt: float | None = 4.95,
    end_rt: float | None = 5.05,
    area: float | None = 1000.0,
    height: float | None = 100.0,
    matched_tags: tuple[str, ...] = ("MeR", "dR"),
) -> DiscoveryCandidate:
    return DiscoveryCandidate(
        review_priority="HIGH",
        evidence_score=80,
        evidence_tier="A",
        ms2_support="seed",
        ms1_support="owner",
        rt_alignment="local",
        family_context="single",
        candidate_id=candidate_id,
        precursor_mz=precursor_mz,
        product_mz=product_mz,
        observed_neutral_loss_da=observed_loss,
        best_seed_rt=best_seed_rt,
        seed_event_count=2,
        ms1_peak_found=apex_rt is not None,
        ms1_apex_rt=apex_rt,
        ms1_area=area,
        ms2_product_max_intensity=10000.0,
        reason="test candidate",
        raw_file=Path(f"{sample_stem}.raw"),
        sample_stem=sample_stem,
        best_ms2_scan_id=101,
        seed_scan_ids=(101,),
        neutral_loss_tag="dR",
        configured_neutral_loss_da=116.0,
        neutral_loss_mass_error_ppm=0.0,
        rt_seed_min=best_seed_rt,
        rt_seed_max=best_seed_rt,
        ms1_search_rt_min=best_seed_rt - 0.2,
        ms1_search_rt_max=best_seed_rt + 0.2,
        ms1_seed_delta_min=0.0,
        ms1_peak_rt_start=start_rt,
        ms1_peak_rt_end=end_rt,
        ms1_height=height,
        ms1_trace_quality="clean",
        ms1_scan_support_score=0.9,
        matched_tag_count=len(matched_tags),
        matched_tag_names=matched_tags,
        primary_tag_name="dR",
    )


def _event(candidate: DiscoveryCandidate) -> IdentityEvent:
    return IdentityEvent(
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


def _owner(candidate: DiscoveryCandidate) -> SampleLocalMS1Owner:
    return SampleLocalMS1Owner(
        owner_id=f"OWN-{candidate.candidate_id}",
        sample_stem=candidate.sample_stem,
        raw_file=str(candidate.raw_file),
        precursor_mz=candidate.precursor_mz,
        owner_apex_rt=float(candidate.ms1_apex_rt),
        owner_peak_start_rt=float(candidate.ms1_peak_rt_start),
        owner_peak_end_rt=float(candidate.ms1_peak_rt_end),
        owner_area=float(candidate.ms1_area),
        owner_height=float(candidate.ms1_height),
        primary_identity_event=_event(candidate),
        supporting_events=(),
        identity_conflict=False,
        assignment_reason="primary_identity_event",
    )


def _ownership(*owners: SampleLocalMS1Owner) -> OwnershipBuildResult:
    assignments = tuple(
        OwnerAssignment(
            candidate_id=owner.primary_identity_event.candidate_id,
            owner_id=owner.owner_id,
            assignment_status="primary",
            reason="primary_identity_event",
        )
        for owner in owners
    )
    return OwnershipBuildResult(
        owners=owners,
        assignments=assignments,
        ambiguous_records=(),
    )
```

Add these tests:

```python
def test_build_seed_sources_uses_primary_pre_backfill_owners() -> None:
    seed = _candidate("CAND-SEED")
    source = build_identity_coherence_seed_sources(
        candidates=(seed,),
        ownership=_ownership(_owner(seed)),
        alignment_config=AlignmentConfig(),
        fragment_profile_id="dna-cid-v1",
        fragment_profile_hash="hash1",
    )[0]

    assert isinstance(source, IdentityCoherenceSeedSource)
    assert source.request.request_id == "ICR000001"
    assert source.decision_id == "ICD000001"
    assert source.identity_family_id == "ICF000001"
    assert source.seed_candidate.candidate_id == "CAND-SEED"
    assert source.seed_evidence.candidate_id == "CAND-SEED"
    assert source.owner.owner_id == "OWN-CAND-SEED"
    assert source.owner_assignment_status == "primary"
    assert source.seed_gate.seed_gate_class.value == "coherent_seed"


def test_build_seed_sources_skips_owner_without_candidate_join() -> None:
    seed = _candidate("CAND-SEED")
    sources = build_identity_coherence_seed_sources(
        candidates=(),
        ownership=_ownership(_owner(seed)),
        alignment_config=AlignmentConfig(),
        fragment_profile_id="dna-cid-v1",
        fragment_profile_hash="hash1",
    )

    assert sources == ()


def test_build_seed_sources_skips_owner_without_assignment() -> None:
    seed = _candidate("CAND-SEED")
    sources = build_identity_coherence_seed_sources(
        candidates=(seed,),
        ownership=OwnershipBuildResult(
            owners=(_owner(seed),),
            assignments=(),
            ambiguous_records=(),
        ),
        alignment_config=AlignmentConfig(),
        fragment_profile_id="dna-cid-v1",
        fragment_profile_hash="hash1",
    )

    assert sources == ()


def test_candidate_pool_member_uses_metadata_before_trace_retrieval() -> None:
    seed = _candidate("CAND-SEED", sample_stem="Sample_A", best_seed_rt=5.0)
    request = build_identity_coherence_seed_sources(
        candidates=(seed,),
        ownership=_ownership(_owner(seed)),
        alignment_config=AlignmentConfig(),
        fragment_profile_id="dna-cid-v1",
        fragment_profile_hash="hash1",
    )[0].request
    nearby = _candidate("CAND-NEAR", sample_stem="Sample_B", best_seed_rt=5.5)
    far_rt = _candidate("CAND-FAR", sample_stem="Sample_B", best_seed_rt=9.0)
    same_sample = _candidate("CAND-SAME", sample_stem="Sample_A", best_seed_rt=5.1)
    bad_morphology = _candidate(
        "CAND-BAD",
        sample_stem="Sample_B",
        apex_rt=None,
        start_rt=None,
        end_rt=None,
        area=None,
        height=None,
    )

    assert candidate_is_non_seed_pool_member(
        request,
        nearby,
        seed_candidate=seed,
        config=AlignmentConfig(),
    )
    assert not candidate_is_non_seed_pool_member(
        request,
        far_rt,
        seed_candidate=seed,
        config=AlignmentConfig(),
    )
    assert not candidate_is_non_seed_pool_member(
        request,
        same_sample,
        seed_candidate=seed,
        config=AlignmentConfig(),
    )
    assert not candidate_is_non_seed_pool_member(
        request,
        bad_morphology,
        seed_candidate=seed,
        config=AlignmentConfig(),
    )


def test_candidate_identity_family_id_is_diagnostic_only() -> None:
    assert candidate_identity_family_id(3) == "ICF000003"
```

Add this domain-boundary test to `tests/alignment/identity_coherence/test_schema_contract.py`:

```python
def test_identity_coherence_domain_does_not_import_inline_adapter() -> None:
    root = Path(__file__).resolve().parents[3]
    package_dir = root / "xic_extractor" / "alignment" / "identity_coherence"
    forbidden = (
        "identity_coherence_adapter",
        "from xic_extractor.alignment.identity_coherence_adapter",
    )
    for path in package_dir.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not any(token in text for token in forbidden), path
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
uv run pytest tests\test_alignment_identity_coherence_adapter.py::test_build_seed_sources_uses_primary_pre_backfill_owners tests\alignment\identity_coherence\test_schema_contract.py::test_identity_coherence_domain_does_not_import_inline_adapter -q
```

Expected: FAIL because `identity_coherence_adapter.py` and its public helpers do not exist.

- [ ] **Step 3: Implement mapping helpers**

Create `xic_extractor/alignment/identity_coherence_adapter.py`:

```python
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.identity_coherence.models import (
    IdentityCoherenceConfig,
    IdentityCoherenceRequest,
    SeedCandidateEvidence,
    SeedGateResult,
)
from xic_extractor.alignment.identity_coherence.request_builder import (
    build_identity_coherence_request,
    build_seed_candidate_evidence,
)
from xic_extractor.alignment.identity_coherence.seed_gate import evaluate_seed_gate
from xic_extractor.alignment.ownership import OwnershipBuildResult
from xic_extractor.alignment.ownership_models import SampleLocalMS1Owner
from xic_extractor.discovery.models import DiscoveryCandidate


@dataclass(frozen=True)
class IdentityCoherenceSeedSource:
    request_id: str
    decision_id: str
    identity_family_id: str
    request: IdentityCoherenceRequest
    seed_candidate: DiscoveryCandidate
    seed_evidence: SeedCandidateEvidence
    owner: SampleLocalMS1Owner
    owner_assignment_status: str
    seed_gate: SeedGateResult


def build_identity_coherence_seed_sources(
    *,
    candidates: Sequence[DiscoveryCandidate],
    ownership: OwnershipBuildResult,
    alignment_config: AlignmentConfig,
    fragment_profile_id: str,
    fragment_profile_hash: str,
    config: IdentityCoherenceConfig = IdentityCoherenceConfig(),
) -> tuple[IdentityCoherenceSeedSource, ...]:
    candidates_by_id = {candidate.candidate_id: candidate for candidate in candidates}
    assignment_by_candidate_id = assignment_status_by_candidate_id(ownership)
    joined_sources: list[tuple[SampleLocalMS1Owner, DiscoveryCandidate]] = []
    for owner in sorted(ownership.owners, key=_owner_sort_key):
        seed_id = owner.primary_identity_event.candidate_id
        seed_candidate = candidates_by_id.get(seed_id)
        if seed_candidate is None:
            continue
        if seed_id not in assignment_by_candidate_id:
            continue
        joined_sources.append((owner, seed_candidate))

    sources: list[IdentityCoherenceSeedSource] = []
    for index, (owner, seed_candidate) in enumerate(joined_sources, start=1):
        seed_id = owner.primary_identity_event.candidate_id
        request_id = candidate_request_id(index)
        decision_id = candidate_decision_id(index)
        request = build_identity_coherence_request(
            seed_candidate,
            request_id=request_id,
            decision_id=decision_id,
            precursor_tolerance_ppm=alignment_config.preferred_ppm,
            product_tolerance_ppm=alignment_config.product_mz_tolerance_ppm,
            cid_observed_loss_tolerance_ppm=(
                alignment_config.observed_loss_tolerance_ppm
            ),
            fragment_profile_id=fragment_profile_id,
            fragment_profile_hash=fragment_profile_hash,
        )
        seed_evidence = build_seed_candidate_evidence(seed_candidate)
        owner_assignment_status = assignment_by_candidate_id.get(seed_id, "primary")
        seed_gate = evaluate_seed_gate(
            request,
            seed_evidence,
            owner,
            owner_assignment_status=owner_assignment_status,
            config=config.seed_gate,
        )
        sources.append(
            IdentityCoherenceSeedSource(
                request_id=request_id,
                decision_id=decision_id,
                identity_family_id=candidate_identity_family_id(index),
                request=seed_gate.resolved_request,
                seed_candidate=seed_candidate,
                seed_evidence=seed_evidence,
                owner=owner,
                owner_assignment_status=owner_assignment_status,
                seed_gate=seed_gate,
            )
        )
    return tuple(sources)


def assignment_status_by_candidate_id(
    ownership: OwnershipBuildResult,
) -> dict[str, str]:
    return {
        assignment.candidate_id: assignment.assignment_status
        for assignment in ownership.assignments
    }


def candidate_request_id(index: int) -> str:
    return f"ICR{index:06d}"


def candidate_decision_id(index: int) -> str:
    return f"ICD{index:06d}"


def candidate_identity_family_id(index: int) -> str:
    return f"ICF{index:06d}"


def candidate_is_non_seed_pool_member(
    request: IdentityCoherenceRequest,
    candidate: DiscoveryCandidate,
    *,
    seed_candidate: DiscoveryCandidate,
    config: AlignmentConfig,
) -> bool:
    if candidate.candidate_id == seed_candidate.candidate_id:
        return False
    if candidate.sample_stem == seed_candidate.sample_stem:
        return False
    if not _has_complete_candidate_morphology(candidate):
        return False
    precursor = request.identity.precursor_mz
    tolerance = request.identity.precursor_tolerance_ppm
    if precursor is None or tolerance is None:
        return False
    error = _ppm_error(candidate.precursor_mz, precursor)
    if error is None or abs(error) > tolerance:
        return False
    rt_delta_sec = abs(candidate.best_seed_rt - seed_candidate.best_seed_rt) * 60.0
    return rt_delta_sec <= config.identity_rt_candidate_window_sec


def _owner_sort_key(owner: SampleLocalMS1Owner) -> tuple[str, float, str]:
    return (
        owner.sample_stem,
        owner.owner_apex_rt,
        owner.primary_identity_event.candidate_id,
    )


def _has_complete_candidate_morphology(candidate: DiscoveryCandidate) -> bool:
    values = (
        candidate.ms1_apex_rt,
        candidate.ms1_peak_rt_start,
        candidate.ms1_peak_rt_end,
        candidate.ms1_area,
        candidate.ms1_height,
    )
    if any(not _finite_number(value) for value in values):
        return False
    return (
        float(candidate.ms1_peak_rt_start)
        < float(candidate.ms1_apex_rt)
        < float(candidate.ms1_peak_rt_end)
        and float(candidate.ms1_area) > 0.0
        and float(candidate.ms1_height) > 0.0
    )


def _ppm_error(observed: float, expected: float) -> float:
    return (observed - expected) / expected * 1_000_000.0


def _finite_number(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, int | float)
        and math.isfinite(value)
    )
```

- [ ] **Step 4: Run tests to verify mapping passes**

Run:

```powershell
uv run pytest tests\test_alignment_identity_coherence_adapter.py::test_build_seed_sources_uses_primary_pre_backfill_owners tests\test_alignment_identity_coherence_adapter.py::test_build_seed_sources_skips_owner_without_candidate_join tests\test_alignment_identity_coherence_adapter.py::test_build_seed_sources_skips_owner_without_assignment tests\test_alignment_identity_coherence_adapter.py::test_candidate_pool_member_uses_metadata_before_trace_retrieval tests\test_alignment_identity_coherence_adapter.py::test_candidate_identity_family_id_is_diagnostic_only tests\alignment\identity_coherence\test_schema_contract.py::test_identity_coherence_domain_does_not_import_inline_adapter -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor\alignment\identity_coherence_adapter.py tests\test_alignment_identity_coherence_adapter.py tests\alignment\identity_coherence\test_schema_contract.py
git commit -m "feat: map pre-backfill identity coherence seed sources"
```

Use the `git -c safe.directory=...` prefix from Step 0 if plain `git` is rejected in this worktree.
