from __future__ import annotations

from pathlib import Path

from xic_extractor.alignment.identity_coherence_validation import (
    decoy_manifest_proposal,
)
from xic_extractor.alignment.identity_coherence_validation.models import (
    DiagnosticBundle,
)


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _bundle(root: Path) -> DiagnosticBundle:
    return DiagnosticBundle(
        requests_tsv=root / "untargeted_identity_coherence_requests.tsv",
        decisions_tsv=root / "untargeted_identity_coherence_decisions.tsv",
        cell_evidence_tsv=root / "untargeted_identity_coherence_cell_evidence.tsv",
        controls_tsv=root / "untargeted_identity_coherence_controls.tsv",
        summary_md=root / "untargeted_identity_coherence_summary.md",
    )


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

    count = decoy_manifest_proposal.write_decoy_manifest_proposal(
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

    count = decoy_manifest_proposal.write_decoy_manifest_proposal(
        bundle,
        proposal,
        max_decoys=3,
    )

    assert count == 0
    lines = proposal.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert lines[0].startswith("control_id\tcontrol_type\tcontrol_name")


def test_decoy_manifest_writer_preserves_private_contract(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "proposal.tsv"

    decoy_manifest_proposal._write_manifest_rows(
        path,
        [
            {
                "control_id": "IDC-001",
                "control_type": "identity_decoy",
                "control_name": "manual review",
                "extra": "ignored",
            }
        ],
    )

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert lines[0].startswith("control_id\tcontrol_type\tcontrol_name")
    assert lines[1].startswith("IDC-001\tidentity_decoy\tmanual review\t")
    assert "ignored" not in text

    empty_path = tmp_path / "empty" / "proposal.tsv"
    decoy_manifest_proposal._write_manifest_rows(empty_path, [])
    assert len(empty_path.read_text(encoding="utf-8").splitlines()) == 1


def test_write_decoy_manifest_proposal_respects_zero_limit(
    tmp_path: Path,
) -> None:
    bundle = _write_proposal_source_bundle(tmp_path / "serial")
    proposal = tmp_path / "proposal.tsv"

    count = decoy_manifest_proposal.write_decoy_manifest_proposal(
        bundle,
        proposal,
        max_decoys=0,
    )

    assert count == 0
    assert len(proposal.read_text(encoding="utf-8").splitlines()) == 1


def test_write_decoy_manifest_proposal_joins_by_decision_id(
    tmp_path: Path,
) -> None:
    bundle = _write_proposal_source_bundle(tmp_path / "serial")
    original = bundle.requests_tsv.read_text(encoding="utf-8")
    header, row = original.splitlines()
    wrong = row.replace("ICR-1\tICD-1\tC1\tS1", "ICR-WRONG\tICD-OTHER\tC1\tS9")
    right = row.replace("ICR-1\tICD-1\tC1\tS1", "ICR-RIGHT\tICD-1\tC1\tS1")
    bundle.requests_tsv.write_text(
        f"{header}\n{wrong}\n{right}\n",
        encoding="utf-8",
    )
    proposal = tmp_path / "proposal.tsv"

    count = decoy_manifest_proposal.write_decoy_manifest_proposal(
        bundle,
        proposal,
        max_decoys=1,
    )

    assert count == 1
    text = proposal.read_text(encoding="utf-8")
    assert "\tICR-RIGHT\t" in text
    assert "\tICR-WRONG\t" not in text


def test_write_decoy_manifest_proposal_skips_ambiguous_decision_join(
    tmp_path: Path,
) -> None:
    bundle = _write_proposal_source_bundle(tmp_path / "serial")
    original = bundle.requests_tsv.read_text(encoding="utf-8")
    header, row = original.splitlines()
    duplicate = row.replace("ICR-1\tICD-1\tC1\tS1", "ICR-DUP\tICD-1\tC1\tS1")
    bundle.requests_tsv.write_text(
        f"{header}\n{row}\n{duplicate}\n",
        encoding="utf-8",
    )
    proposal = tmp_path / "proposal.tsv"

    count = decoy_manifest_proposal.write_decoy_manifest_proposal(
        bundle,
        proposal,
        max_decoys=1,
    )

    assert count == 0
    assert len(proposal.read_text(encoding="utf-8").splitlines()) == 1


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

    count = decoy_manifest_proposal.write_decoy_manifest_proposal(
        bundle,
        proposal,
        max_decoys=1,
    )

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

    decoy_manifest_proposal.write_decoy_manifest_proposal(
        bundle,
        proposal,
        max_decoys=1,
    )

    entries = read_identity_controls_manifest(proposal)
    assert len(entries) == 1
    assert entries[0].control_type.value == "identity_decoy"
    assert entries[0].expected_mapping_status.value == "not_applicable"
    assert entries[0].decoy_generation_method.value == "rt_shift"
    assert entries[0].decoy_source_request_id == "ICR-1"
