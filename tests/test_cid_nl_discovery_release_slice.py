from __future__ import annotations

from scripts.check_cid_nl_discovery_release_slice import (
    check_cid_nl_discovery_release_slice,
)


def test_current_cid_nl_discovery_release_slice_is_stable() -> None:
    assert check_cid_nl_discovery_release_slice() == []
