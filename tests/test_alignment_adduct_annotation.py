from pathlib import Path
from types import SimpleNamespace

from xic_extractor.alignment.adduct_annotation import (
    ArtificialAdduct,
    load_artificial_adducts,
    match_artificial_adduct_pairs,
)


def test_load_artificial_adducts_parses_fh_list(tmp_path: Path) -> None:
    csv_path = tmp_path / "Artificial_Adduct_List.csv"
    csv_path.write_text(
        "Artificial Adduct No.,Artificial Adduct m/z,Artificial Adduct Name\n"
        "1,21.981945,M+Na-H\n"
        "2,37.955882,M+K-H\n",
        encoding="utf-8",
    )

    adducts = load_artificial_adducts(csv_path)

    assert adducts[0].adduct_id == "1"
    assert adducts[0].mz_delta == 21.981945
    assert adducts[0].adduct_name == "M+Na-H"


def test_match_artificial_adduct_pairs_requires_close_rt_and_delta() -> None:
    families = [
        _family("F001", mz=300.000000, rt=5.000, identity_decision="production_family"),
        _family(
            "F002",
            mz=321.981945,
            rt=5.020,
            identity_decision="provisional_discovery",
        ),
        _family(
            "F003",
            mz=337.955882,
            rt=5.300,
            identity_decision="provisional_discovery",
        ),
    ]
    pairs = match_artificial_adduct_pairs(
        families,
        [ArtificialAdduct(adduct_id="1", mz_delta=21.981945, adduct_name="M+Na-H")],
        rt_window_min=0.05,
        mz_tolerance_ppm=10.0,
    )

    assert [
        (pair.parent_family_id, pair.related_family_id, pair.adduct_name)
        for pair in pairs
    ] == [("F001", "F002", "M+Na-H")]


def _family(
    family_id: str,
    *,
    mz: float,
    rt: float,
    identity_decision: str,
) -> SimpleNamespace:
    return SimpleNamespace(
        feature_family_id=family_id,
        family_center_mz=mz,
        family_center_rt=rt,
        identity_decision=identity_decision,
    )
