import re
from pathlib import Path

import pytest

from xic_extractor.presets import list_presets


def test_pyinstaller_spec_includes_dynamic_raw_reader_imports() -> None:
    spec_text = Path("xic_extractor.spec").read_text(encoding="utf-8")
    hiddenimports_match = re.search(
        r"hiddenimports=\[(?P<body>.*?)\],",
        spec_text,
        flags=re.DOTALL,
    )
    assert hiddenimports_match is not None
    hiddenimports = set(re.findall(r'"([^"]+)"', hiddenimports_match.group("body")))

    assert {"pythonnet", "clr"} <= hiddenimports


def test_pyinstaller_spec_includes_builtin_preset_tomls() -> None:
    spec_text = Path("xic_extractor.spec").read_text(encoding="utf-8")

    assert "collect_data_files" in spec_text
    assert '"xic_extractor.presets"' in spec_text
    assert '"data/*.toml"' in spec_text
    assert "+ preset_datas" in spec_text


def test_pyinstaller_collects_builtin_preset_tomls() -> None:
    hooks = pytest.importorskip("PyInstaller.utils.hooks")
    datas = hooks.collect_data_files("xic_extractor.presets", includes=["data/*.toml"])
    collected = {
        (Path(source).name, Path(destination).as_posix())
        for source, destination in datas
    }

    expected_names = {f"{preset}.toml" for preset in list_presets()}
    collected_names = {name for name, _destination in collected}

    assert expected_names <= collected_names
    assert all(
        destination == "xic_extractor/presets/data"
        for name, destination in collected
        if name in expected_names
    )
