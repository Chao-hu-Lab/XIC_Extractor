from pathlib import Path

from xic_extractor.rt_prior_library import LibraryEntry, load_library


def test_load_empty_returns_empty(tmp_path: Path) -> None:
    p = tmp_path / "lib.csv"
    p.write_text(
        "config_hash,target_label,role,istd_pair,median_delta_rt,"
        "sigma_delta_rt,median_abs_rt,sigma_abs_rt,n_samples,updated_at\n",
        encoding="utf-8",
    )
    assert load_library(p, "anyhash") == {}


def test_load_missing_file_returns_empty(tmp_path: Path) -> None:
    assert load_library(tmp_path / "does_not_exist.csv", "h") == {}


def test_load_filters_by_config_hash(tmp_path: Path) -> None:
    p = tmp_path / "lib.csv"
    p.write_text(
        "config_hash,target_label,role,istd_pair,median_delta_rt,"
        "sigma_delta_rt,median_abs_rt,sigma_abs_rt,n_samples,updated_at\n"
        "aaaa1111,A,analyte,d3-A,0.10,0.02,,,10,2026-01-01T00:00:00\n"
        "bbbb2222,B,analyte,d3-B,0.05,0.01,,,8,2026-01-01T00:00:00\n"
        "aaaa1111,d3-A,ISTD,,,,9.03,0.18,10,2026-01-01T00:00:00\n",
        encoding="utf-8",
    )
    lib = load_library(p, "aaaa1111")
    assert set(lib.keys()) == {("A", "analyte"), ("d3-A", "ISTD")}
    entry = lib[("A", "analyte")]
    assert isinstance(entry, LibraryEntry)
    assert entry.median_delta_rt == 0.10
    assert entry.sigma_delta_rt == 0.02
    assert entry.n_samples == 10
    istd_entry = lib[("d3-A", "ISTD")]
    assert istd_entry.median_abs_rt == 9.03
    assert istd_entry.sigma_abs_rt == 0.18
