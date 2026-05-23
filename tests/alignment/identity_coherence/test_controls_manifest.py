import pytest

from xic_extractor.alignment.identity_coherence.controls import (
    read_identity_controls_manifest,
)
from xic_extractor.alignment.identity_coherence.schema import (
    ControlType,
    DecoyGenerationMethod,
    FragmentObservationMode,
    PositiveControlMappingStatus,
)

MANIFEST_HEADER = (
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
    "decoy_generation_method",
    "decoy_fragment_tags",
    "positive_control_target_name",
    "positive_control_target_mz",
    "positive_control_target_rt_sec",
    "positive_control_mapping_error_ppm",
    "positive_control_mapping_delta_rt_sec",
)


def _write_manifest(tmp_path, rows):
    path = tmp_path / "identity_controls.tsv"
    lines = ["\t".join(MANIFEST_HEADER)]
    lines.extend("\t".join(row) for row in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _positive_row():
    return (
        "PC-ISTD-1",
        "positive_targeted_istd",
        "Targeted ISTD mapped control",
        "mapped",
        "must map targeted ISTD identity",
        "cid_neutral_loss",
        "10",
        "10",
        "15",
        "30",
        "positive_control_missed",
        "",
        "",
        "d3-N6-medA",
        "285.1",
        "421.2",
        "0.2",
        "1.5",
    )


def _decoy_row(decoy_generation_method="rt_shift"):
    return (
        "DEC-1",
        "identity_decoy",
        "RT shifted identity decoy",
        "not_applicable",
        "must not map coherent identity",
        "cid_neutral_loss",
        "10",
        "10",
        "15",
        "30",
        "decoy_matched",
        decoy_generation_method,
        "dR;MeR",
        "",
        "",
        "",
        "",
        "",
    )


def test_read_manifest_tsv_preserves_control_enum_types(tmp_path):
    path = _write_manifest(tmp_path, [_positive_row(), _decoy_row()])

    positive, decoy = read_identity_controls_manifest(path)

    assert positive.control_type is ControlType.POSITIVE_TARGETED_ISTD
    assert positive.expected_mapping_status is PositiveControlMappingStatus.MAPPED
    assert positive.fragment_observation_mode is (
        FragmentObservationMode.CID_NEUTRAL_LOSS
    )
    assert positive.positive_control_target_mz == 285.1
    assert positive.positive_control_target_rt_sec == 421.2
    assert decoy.control_type is ControlType.IDENTITY_DECOY
    assert decoy.expected_mapping_status is (
        PositiveControlMappingStatus.NOT_APPLICABLE
    )
    assert decoy.decoy_generation_method is DecoyGenerationMethod.RT_SHIFT
    assert decoy.decoy_fragment_tags == ("MeR", "dR")


def test_downstream_control_type_is_rejected(tmp_path):
    row = list(_positive_row())
    row[1] = "blank"
    path = _write_manifest(tmp_path, [tuple(row)])

    with pytest.raises(ValueError, match="unsupported identity control_type"):
        read_identity_controls_manifest(path)


def test_identity_decoy_requires_decoy_generation_method(tmp_path):
    path = _write_manifest(tmp_path, [_decoy_row(decoy_generation_method="")])

    with pytest.raises(ValueError, match="decoy_generation_method"):
        read_identity_controls_manifest(path)


def test_yaml_manifest_path_has_clear_error(tmp_path):
    path = tmp_path / "identity_controls.yaml"
    path.write_text("", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="YAML controls manifests are not implemented in this slice",
    ):
        read_identity_controls_manifest(path)


def test_nonpositive_tolerance_is_rejected(tmp_path):
    row = list(_positive_row())
    row[6] = "0"
    path = _write_manifest(tmp_path, [tuple(row)])

    with pytest.raises(ValueError, match="precursor_tolerance_ppm"):
        read_identity_controls_manifest(path)


@pytest.mark.parametrize(
    ("field_index", "field_name", "bad_value"),
    [
        (14, "positive_control_target_mz", "nan"),
        (16, "positive_control_mapping_error_ppm", "inf"),
    ],
)
def test_optional_numeric_fields_reject_nonfinite_values(
    tmp_path,
    field_index,
    field_name,
    bad_value,
):
    row = list(_positive_row())
    row[field_index] = bad_value
    path = _write_manifest(tmp_path, [tuple(row)])

    with pytest.raises(ValueError, match=field_name):
        read_identity_controls_manifest(path)


@pytest.mark.parametrize("extra_value", ["surplus", ""])
def test_tsv_rows_with_extra_columns_are_rejected(tmp_path, extra_value):
    path = _write_manifest(tmp_path, [(*_positive_row(), extra_value)])

    with pytest.raises(ValueError, match="unexpected extra fields"):
        read_identity_controls_manifest(path)
