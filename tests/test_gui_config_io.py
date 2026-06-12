from __future__ import annotations

from gui import config_io


def test_target_write_fieldnames_preserves_extra_order() -> None:
    fieldnames = config_io._target_write_fieldnames(
        [
            {"Target": "A", "extra_b": "1", "extra_a": "2"},
            {"extra_a": "3", "extra_c": "4"},
        ],
    )

    assert fieldnames[: len(config_io.TARGET_WRITE_FIELDS)] == list(
        config_io.TARGET_WRITE_FIELDS,
    )
    assert fieldnames[-3:] == ["extra_b", "extra_a", "extra_c"]
