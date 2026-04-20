from pathlib import Path

from xic_extractor.config import compute_config_hash


def test_same_bytes_same_hash(tmp_path: Path) -> None:
    targets = tmp_path / "targets.csv"
    settings = tmp_path / "settings.csv"
    targets.write_bytes(b"label,mz\nA,100\n")
    settings.write_bytes(b"key,value\ndata_dir,C:/x\n")
    assert compute_config_hash(targets, settings) == compute_config_hash(
        targets, settings
    )


def test_different_targets_different_hash(tmp_path: Path) -> None:
    targets_a = tmp_path / "a.csv"
    targets_b = tmp_path / "b.csv"
    settings = tmp_path / "s.csv"
    targets_a.write_bytes(b"label\nA\n")
    targets_b.write_bytes(b"label\nB\n")
    settings.write_bytes(b"key\ndata_dir\n")
    assert compute_config_hash(targets_a, settings) != compute_config_hash(
        targets_b, settings
    )


def test_hash_is_8_hex_chars(tmp_path: Path) -> None:
    t = tmp_path / "t.csv"
    s = tmp_path / "s.csv"
    t.write_bytes(b"x")
    s.write_bytes(b"y")
    h = compute_config_hash(t, s)
    assert len(h) == 8
    assert all(c in "0123456789abcdef" for c in h)
