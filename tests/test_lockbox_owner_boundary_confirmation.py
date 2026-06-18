import json
from pathlib import Path

from xic_extractor.tabular_io import file_sha256

ROOT = Path(__file__).resolve().parents[1]
CONFIRMATION = (
    ROOT
    / "docs/superpowers/validation/lockbox_owner_boundary_confirmation_v1.json"
)


def test_owner_boundary_confirmation_is_non_authoritative() -> None:
    payload = json.loads(CONFIRMATION.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "lockbox_owner_boundary_confirmation_v1"
    assert payload["scope"]["owner_assessed_plotted_gaussian15_cases"] == 53
    assert payload["scope"]["not_assessable_or_excluded_cases"] == 19
    assert payload["owner_confirmations"] == {
        "available_peak_choices_acceptable": True,
        "available_overlay_boundaries_acceptable": True,
        "gaussian15_smoothed_boundary_is_review_basis": True,
        "raw_trace_boundary_is_reference_only": True,
        "missing_overlay_cases_not_assessable_by_owner": True,
    }
    assert payload["subagent_review_boundary"]["may_satisfy_reviewer_slot_2"] is False
    assert payload["authority_rules"] == {
        "labels_grant_product_authority": False,
        "product_writer_consumption": "forbidden",
        "may_touch_matrix": False,
        "may_touch_workbook": False,
        "may_switch_selected_peak": False,
        "may_change_selected_area": False,
        "may_change_counted_detection": False,
        "may_change_default_extraction": False,
        "may_change_gui": False,
        "broad_backfill_unparked": False,
    }


def test_owner_boundary_confirmation_hashes_match_sources() -> None:
    payload = json.loads(CONFIRMATION.read_text(encoding="utf-8"))
    artifacts = payload["source_artifacts"]

    assert "second_review_summary" not in artifacts

    for key, path_value in artifacts.items():
        if not key.endswith("_sha256"):
            expected_hash = artifacts[f"{key}_sha256"]
            assert file_sha256(ROOT / path_value) == expected_hash
