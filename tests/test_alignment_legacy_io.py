from pathlib import Path

import pytest
from openpyxl import Workbook

from xic_extractor.alignment.legacy_io import (
    load_combine_fix_xlsx,
    load_fh_alignment_tsv,
    load_metabcombiner_tsv,
    load_xic_alignment,
    normalize_sample_name,
)


def test_normalize_sample_name_strips_known_wrappers() -> None:
    assert normalize_sample_name("program2_DNA_program1_TumorBC2312_DNA.raw") == (
        "TumorBC2312_DNA"
    )
    assert normalize_sample_name("NormalBC2257_DNA.mzML") == "NormalBC2257_DNA"
    assert normalize_sample_name("NormalBC2257_DNA.mzML Peak area") == (
        "NormalBC2257_DNA"
    )
    assert normalize_sample_name("Breast_Cancer_Tissue_pooled_QC_1") == (
        "Breast_Cancer_Tissue_pooled_QC1"
    )


def test_load_xic_alignment_joins_review_and_matrix_by_cluster_id(tmp_path: Path):
    review = tmp_path / "alignment_review.tsv"
    matrix = tmp_path / "alignment_matrix.tsv"
    review.write_text(_XIC_REVIEW_TEXT, encoding="utf-8")
    matrix.write_text(_XIC_MATRIX_TEXT, encoding="utf-8")

    loaded = load_xic_alignment(review, matrix)

    assert loaded.source == "xic_alignment"
    assert loaded.sample_order == ("TumorBC2312_DNA",)
    assert len(loaded.features) == 1
    feature = loaded.features[0]
    assert feature.feature_id == "ALN000001"
    assert feature.mz == 242.1144
    assert feature.rt_min == 12.35
    assert feature.sample_areas == {"TumorBC2312_DNA": 1000.0}
    assert feature.metadata["neutral_loss_tag"] == "DNA_dR"


def test_load_xic_alignment_rejects_duplicate_matrix_cluster_id(tmp_path: Path):
    review = tmp_path / "alignment_review.tsv"
    matrix = tmp_path / "alignment_matrix.tsv"
    review.write_text(_XIC_REVIEW_TEXT, encoding="utf-8")
    matrix.write_text(
        _XIC_MATRIX_TEXT + "ALN000001\tDNA_dR\t242.1144\t12.35\t2000\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate.*cluster_id"):
        load_xic_alignment(review, matrix)


def test_load_fh_alignment_tsv_reads_program2_columns(tmp_path: Path):
    path = tmp_path / "fh.tsv"
    path.write_text(
        "alignment_id\tMz\tRT\tprogram2_DNA_program1_TumorBC2312_DNA\t"
        "program2_DNA_program1_NormalBC2257_DNA\n"
        "ALN00001\t242.1144\t12.3515\t661257\t0\n"
        "ALN00002\t242.1337\t19.5400\t\tNaN\n",
        encoding="utf-8",
    )

    loaded = load_fh_alignment_tsv(path)

    assert loaded.source == "fh_alignment"
    assert loaded.sample_order == ("TumorBC2312_DNA", "NormalBC2257_DNA")
    assert loaded.features[0].feature_id == "ALN00001"
    assert loaded.features[0].sample_areas == {
        "TumorBC2312_DNA": 661257.0,
        "NormalBC2257_DNA": None,
    }
    assert loaded.features[1].sample_areas == {
        "TumorBC2312_DNA": None,
        "NormalBC2257_DNA": None,
    }


def test_load_metabcombiner_tsv_returns_fh_and_mzmine_blocks(tmp_path: Path):
    path = tmp_path / "metabcombiner.tsv"
    path.write_text(
        "Mz\tRT\tTumorBC2312_DNA\tMZmine ID\tMZmine m/z\tMZmine RT (min)\t"
        "TumorBC2312_DNA.mzML Peak area\n"
        "242.1144\t12.35\t100\tmz1\t242.1145\t12.36\t200\n"
        "300.0000\t20.00\t0\t\t300.0001\t20.01\t\n",
        encoding="utf-8",
    )

    fh_block, mzmine_block = load_metabcombiner_tsv(path)

    assert fh_block.source == "metabcombiner_fh_block"
    assert mzmine_block.source == "metabcombiner_mzmine_block"
    assert fh_block.sample_order == ("TumorBC2312_DNA",)
    assert mzmine_block.sample_order == ("TumorBC2312_DNA",)
    assert fh_block.features[0].sample_areas["TumorBC2312_DNA"] == 100.0
    assert fh_block.features[1].sample_areas["TumorBC2312_DNA"] is None
    assert mzmine_block.features[0].feature_id == "metabcombiner_mzmine:mz1"
    assert mzmine_block.features[0].sample_areas["TumorBC2312_DNA"] == 200.0
    assert mzmine_block.features[1].sample_areas["TumorBC2312_DNA"] is None


def test_load_combine_fix_xlsx_reads_first_sheet_and_missing_values(tmp_path: Path):
    path = tmp_path / "combine_fix.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Mz", "RT", "TumorBC2312_DNA", "NormalBC2257_DNA", "MZmine ID"])
    sheet.append([242.1144, 12.35, 1000, 0, "mz1"])
    sheet.append([300.0, 20.0, "", -5, "mz2"])
    workbook.save(path)

    loaded = load_combine_fix_xlsx(path)

    assert loaded.source == "combine_fix"
    assert loaded.sample_order == ("TumorBC2312_DNA", "NormalBC2257_DNA")
    assert loaded.features[0].feature_id == "combine_fix:000002"
    assert loaded.features[0].sample_areas == {
        "TumorBC2312_DNA": 1000.0,
        "NormalBC2257_DNA": None,
    }
    assert loaded.features[1].sample_areas == {
        "TumorBC2312_DNA": None,
        "NormalBC2257_DNA": None,
    }


_XIC_REVIEW_TEXT = (
    "cluster_id\tneutral_loss_tag\tcluster_center_mz\tcluster_center_rt\t"
    "cluster_product_mz\tcluster_observed_neutral_loss_da\thas_anchor\t"
    "member_count\tdetected_count\trescued_count\tabsent_count\tunchecked_count\t"
    "present_rate\trescued_rate\trepresentative_samples\t"
    "representative_candidate_ids\twarning\treason\n"
    "ALN000001\tDNA_dR\t242.1144\t12.35\t126.067\t116.047\tTRUE\t1\t1\t0\t"
    "0\t0\t1\t0\tTumorBC2312_DNA\tC1\t\tanchor cluster\n"
)

_XIC_MATRIX_TEXT = (
    "cluster_id\tneutral_loss_tag\tcluster_center_mz\tcluster_center_rt\t"
    "TumorBC2312_DNA\n"
    "ALN000001\tDNA_dR\t242.1144\t12.35\t1000\n"
)
