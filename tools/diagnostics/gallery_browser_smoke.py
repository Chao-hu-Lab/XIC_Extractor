from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

SETUP_HINT = (
    "Playwright is not ready. Run:\n"
    "$env:UV_CACHE_DIR='.uv-cache'; uv sync --extra dev --group dev\n"
    "$env:UV_CACHE_DIR='.uv-cache'; uv run python -m playwright install chromium"
)


@dataclass(frozen=True)
class SmokeResult:
    name: str
    status: str
    detail: str = ""
    screenshot: str = ""


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    html_path = args.html.resolve()
    if not html_path.exists():
        raise SystemExit(f"HTML not found: {html_path}")
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit(SETUP_HINT) from exc

    results: list[SmokeResult] = []
    try:
        with sync_playwright() as playwright:
            browser = _launch_browser(
                playwright,
                args.browser_channel,
                launch_timeout_ms=args.launch_timeout_ms,
            )
            try:
                results.extend(
                    _run_viewport_smoke(
                        browser,
                        html_path=html_path,
                        output_dir=output_dir,
                        name="desktop",
                        viewport={"width": 1440, "height": 900},
                        timeout_ms=args.timeout_ms,
                    ),
                )
                results.extend(
                    _run_viewport_smoke(
                        browser,
                        html_path=html_path,
                        output_dir=output_dir,
                        name="mobile",
                        viewport={"width": 390, "height": 844},
                        timeout_ms=args.timeout_ms,
                    ),
                )
                results.extend(
                    _run_viewport_smoke(
                        browser,
                        html_path=html_path,
                        output_dir=output_dir,
                        name="zoom200",
                        viewport={"width": 1440, "height": 900},
                        timeout_ms=args.timeout_ms,
                        css_zoom=2,
                    ),
                )
            finally:
                browser.close()
    except Exception as exc:
        message = str(exc)
        if "Executable doesn't exist" in message or "playwright install" in message:
            raise SystemExit(SETUP_HINT) from exc
        raise

    report_path = output_dir / "gallery_browser_smoke_summary.json"
    report_path.write_text(
        json.dumps([asdict(result) for result in results], indent=2),
        encoding="utf-8",
    )
    print(f"gallery browser smoke summary: {report_path}")
    for result in results:
        print(f"{result.status.upper()}: {result.name} {result.detail}".rstrip())
    failed = [result for result in results if result.status != "pass"]
    return 1 if failed else 0


def _launch_browser(
    playwright: Any,
    channel: str,
    *,
    launch_timeout_ms: int,
) -> Any:
    attempts: tuple[tuple[str, dict[str, str]], ...] = (("bundled Chromium", {}),)
    if channel == "auto":
        attempts = (
            ("bundled Chromium", {}),
            ("system Chrome", {"channel": "chrome"}),
            ("system Edge", {"channel": "msedge"}),
        )
    elif channel != "bundled":
        attempts = tuple(
            (name, kwargs)
            for name, kwargs in (
                ("system Chrome", {"channel": "chrome"}),
                ("system Edge", {"channel": "msedge"}),
            )
            if kwargs.get("channel") == channel
        )
    errors: list[str] = []
    for name, kwargs in attempts:
        try:
            return playwright.chromium.launch(
                headless=True,
                timeout=launch_timeout_ms,
                **kwargs,
            )
        except Exception as exc:  # pragma: no cover - host browser dependent
            errors.append(f"{name}: {exc}")
    raise RuntimeError(SETUP_HINT + "\n\nLaunch attempts:\n" + "\n".join(errors))


def _run_viewport_smoke(
    browser: Any,
    *,
    html_path: Path,
    output_dir: Path,
    name: str,
    viewport: dict[str, int],
    timeout_ms: int,
    css_zoom: int = 1,
) -> list[SmokeResult]:
    page = browser.new_page(viewport=viewport)
    page.set_default_timeout(timeout_ms)
    results: list[SmokeResult] = []
    try:
        page.goto(html_path.as_uri(), wait_until="domcontentloaded")
        if css_zoom != 1:
            page.evaluate(
                "(zoom) => { document.body.style.zoom = String(zoom); }",
                css_zoom,
            )
        screenshot = output_dir / f"gallery_browser_smoke_{name}.png"
        try:
            _assert_gallery_chrome(page)
        except Exception as exc:
            page.screenshot(path=str(screenshot), full_page=False)
            return [
                SmokeResult(
                    name=f"{name}:chrome",
                    status="fail",
                    detail=_format_error(exc),
                    screenshot=str(screenshot),
                ),
            ]
        page.screenshot(path=str(screenshot), full_page=False)
        results.append(
            SmokeResult(
                name=f"{name}:chrome",
                status="pass",
                detail=f"{viewport['width']}x{viewport['height']}",
                screenshot=str(screenshot),
            ),
        )
        for check_name, check in (
            ("filters", _exercise_filters),
            ("details", _exercise_details),
            ("lightbox", _exercise_lightbox),
            ("overlap", _check_overlaps),
        ):
            try:
                results.extend(check(page, name))
            except Exception as exc:
                results.append(
                    SmokeResult(
                        name=f"{name}:{check_name}",
                        status="fail",
                        detail=_format_error(exc),
                        screenshot=str(screenshot),
                    ),
                )
        return results
    finally:
        page.close()


def _assert_gallery_chrome(page: Any) -> None:
    page.locator("table.review-table").first.wait_for(state="visible")
    page.locator("[data-filter-control]").first.wait_for(state="visible")
    page.locator("[data-search-control]").first.wait_for(state="visible")
    sticky = page.locator("table.review-table thead th").first.evaluate(
        """
        (element) => ({
          position: getComputedStyle(element).position,
          top: getComputedStyle(element).top,
        })
        """,
    )
    if sticky["position"] != "sticky" or sticky["top"] == "auto":
        raise AssertionError(f"review table header is not sticky: {sticky}")


def _format_error(exc: Exception) -> str:
    message = str(exc).replace("\r", " ").replace("\n", " ")
    return message[:800]


def _exercise_filters(page: Any, viewport_name: str) -> list[SmokeResult]:
    results = []
    filter_control = page.locator("[data-filter-control]").first
    option_values = filter_control.locator("option").evaluate_all(
        "(options) => options.map((option) => option.value)",
    )
    if "projection_accepts" in option_values:
        filter_control.select_option("projection_accepts")
        page.wait_for_timeout(100)
        visible = _visible_family_count(page)
        has_projected_writes = page.evaluate(
            "() => document.documentElement.outerHTML.includes('projected_new_write')",
        )
        if has_projected_writes and visible <= 0:
            raise AssertionError("Projection accepts filter hid all projected writes")
        results.append(
            SmokeResult(
                name=f"{viewport_name}:projection-filter",
                status="pass",
                detail=f"visible_families={visible}",
            ),
        )
    search = page.locator("[data-search-control]").first
    search.fill("projection_accept")
    page.wait_for_timeout(100)
    results.append(
        SmokeResult(
            name=f"{viewport_name}:search",
            status="pass",
            detail=f"visible_families={_visible_family_count(page)}",
        ),
    )
    search.fill("")
    filter_control.select_option("product_rows")
    return results


def _exercise_details(page: Any, viewport_name: str) -> list[SmokeResult]:
    _reset_review_controls(page, preferred_filter="product_rows")
    button = page.locator("[data-detail-toggle]:visible").first
    if button.count() == 0:
        return [SmokeResult(f"{viewport_name}:details", "pass", "no detail toggle")]
    detail_id = button.get_attribute("aria-controls")
    button.click()
    expanded = button.get_attribute("aria-expanded")
    hidden = page.locator(f"#{detail_id}").get_attribute("hidden")
    if expanded != "true" or hidden is not None:
        raise AssertionError("detail drawer did not open")
    button.click()
    return [SmokeResult(f"{viewport_name}:details", "pass", f"opened={detail_id}")]


def _exercise_lightbox(page: Any, viewport_name: str) -> list[SmokeResult]:
    _reset_review_controls(page, preferred_filter="")
    if page.locator("[data-lightbox-src]").count() == 0:
        return [SmokeResult(f"{viewport_name}:lightbox", "pass", "no PNG links")]
    href = page.evaluate(
        """
        () => {
          const link = document.querySelector('[data-lightbox-src]');
          if (!link) return '';
          link.scrollIntoView({ block: 'center', inline: 'center' });
          return link.getAttribute('href') || '';
        }
        """,
    )
    if not href:
        raise AssertionError("PNG link has no href fallback")
    page.evaluate(
        """
        () => {
          const link = document.querySelector('[data-lightbox-src]');
          if (!link) return;
          link.click();
        }
        """,
    )
    modal = page.locator(".lightbox").first
    if modal.get_attribute("hidden") is not None:
        raise AssertionError("lightbox did not open")
    active_class = page.evaluate("document.activeElement.className")
    if "lightbox-close" not in str(active_class):
        raise AssertionError("lightbox did not focus the close button")
    image_loaded = page.wait_for_function(
        """
        () => {
          const image = document.querySelector('.lightbox-image');
          return Boolean(
            image &&
            image.complete &&
            image.naturalWidth > 0 &&
            image.naturalHeight > 0
          );
        }
        """,
    )
    if not image_loaded:
        raise AssertionError("lightbox image did not load")
    page.keyboard.press("Escape")
    if modal.get_attribute("hidden") is None:
        raise AssertionError("lightbox did not close on Escape")
    return [SmokeResult(f"{viewport_name}:lightbox", "pass", "fallback+esc")]


def _reset_review_controls(page: Any, *, preferred_filter: str) -> None:
    filter_control = page.locator("[data-filter-control]").first
    option_values = filter_control.locator("option").evaluate_all(
        "(options) => options.map((option) => option.value)",
    )
    if preferred_filter in option_values:
        filter_control.select_option(preferred_filter)
    elif "" in option_values:
        filter_control.select_option("")
    elif "all" in option_values:
        filter_control.select_option("all")
    elif "product_rows" in option_values:
        filter_control.select_option("product_rows")
    search = page.locator("[data-search-control]").first
    search.fill("")
    page.wait_for_timeout(100)


def _check_overlaps(page: Any, viewport_name: str) -> list[SmokeResult]:
    _reset_review_controls(page, preferred_filter="product_rows")
    overlap_count = page.evaluate(
        """
        () => {
          const cells = Array.from(
            document.querySelectorAll('.review-table th, .review-table td')
          ).filter((el) => {
            if (el.closest('[hidden]')) return false;
            const rect = el.getBoundingClientRect();
            return (
              rect.width > 0 &&
              rect.height > 0 &&
              rect.bottom > 0 &&
              rect.right > 0 &&
              rect.top < window.innerHeight &&
              rect.left < window.innerWidth
            );
          });
          let overlaps = 0;
          for (let i = 0; i < cells.length; i += 1) {
            const a = cells[i].getBoundingClientRect();
            for (let j = i + 1; j < cells.length; j += 1) {
              const b = cells[j].getBoundingClientRect();
              const intersects = !(
                a.right <= b.left ||
                b.right <= a.left ||
                a.bottom <= b.top ||
                b.bottom <= a.top
              );
              if (intersects && cells[i].parentElement !== cells[j].parentElement) {
                overlaps += 1;
              }
            }
          }
          return overlaps;
        }
        """,
    )
    return [
        SmokeResult(
            name=f"{viewport_name}:overlap-scan",
            status="pass" if int(overlap_count) == 0 else "fail",
            detail=f"overlaps={overlap_count}",
        ),
    ]


def _visible_family_count(page: Any) -> int:
    return int(
        page.locator(".review-table > tbody > tr[data-family-row]").evaluate_all(
            "(rows) => rows.filter((row) => !row.hidden).length",
        ),
    )


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a headless Playwright smoke test against a gallery HTML.",
    )
    parser.add_argument("--html", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--timeout-ms", type=int, default=15000)
    parser.add_argument(
        "--launch-timeout-ms",
        type=int,
        default=8000,
        help=(
            "Browser launch timeout. Keep short so missing browser installs "
            "fail fast."
        ),
    )
    parser.add_argument(
        "--browser-channel",
        choices=("auto", "bundled", "chrome", "msedge"),
        default="bundled",
        help=(
            "Use bundled Playwright Chromium only by default. Pass auto or an "
            "explicit channel to opt into system Chrome/Edge fallback."
        ),
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
