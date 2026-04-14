from pathlib import Path


def test_legacy_ps1_accepts_canonical_smoothing_keys_until_removed() -> None:
    script = Path("scripts/01_extract_xic.ps1").read_text(encoding="utf-8-sig")

    assert "smooth_window" in script
    assert "smooth_points" in script
    assert "smooth_sigma" in script
    assert "3.0" in script
