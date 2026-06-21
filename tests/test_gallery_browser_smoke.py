from __future__ import annotations

import pytest

from tools.diagnostics import gallery_browser_smoke


def test_gallery_browser_smoke_defaults_to_bundled_browser_only() -> None:
    args = gallery_browser_smoke._parse_args(
        ["--html", "gallery.html", "--output-dir", "smoke"],
    )

    assert args.browser_channel == "bundled"
    assert args.launch_timeout_ms == 8000


def test_launch_browser_bundled_does_not_fall_back_to_system_chrome() -> None:
    playwright = _FakePlaywright(
        failures={"bundled Chromium": RuntimeError("missing bundled browser")},
    )

    with pytest.raises(RuntimeError) as exc_info:
        gallery_browser_smoke._launch_browser(
            playwright,
            "bundled",
            launch_timeout_ms=1234,
        )

    assert playwright.chromium.calls == [
        {"headless": True, "timeout": 1234},
    ]
    message = str(exc_info.value)
    assert "bundled Chromium" in message
    assert "system Chrome" not in message


def test_launch_browser_auto_is_the_only_path_that_falls_back_to_chrome() -> None:
    playwright = _FakePlaywright(
        failures={"bundled Chromium": RuntimeError("missing bundled browser")},
    )

    browser = gallery_browser_smoke._launch_browser(
        playwright,
        "auto",
        launch_timeout_ms=5678,
    )

    assert browser == "system Chrome"
    assert playwright.chromium.calls == [
        {"headless": True, "timeout": 5678},
        {"channel": "chrome", "headless": True, "timeout": 5678},
    ]


class _FakePlaywright:
    def __init__(self, *, failures: dict[str, Exception] | None = None) -> None:
        self.chromium = _FakeChromium(failures=failures or {})


class _FakeChromium:
    def __init__(self, *, failures: dict[str, Exception]) -> None:
        self._failures = failures
        self.calls: list[dict[str, object]] = []

    def launch(self, **kwargs: object) -> str:
        self.calls.append(kwargs)
        name = _attempt_name(kwargs)
        if name in self._failures:
            raise self._failures[name]
        return name


def _attempt_name(kwargs: dict[str, object]) -> str:
    channel = kwargs.get("channel")
    if channel == "chrome":
        return "system Chrome"
    if channel == "msedge":
        return "system Edge"
    return "bundled Chromium"
