"""Human review gallery renderer for selected-envelope diagnostic plots."""

from __future__ import annotations

import html
import re
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

_URL_SCHEME_RE = re.compile(r"^([A-Za-z][A-Za-z0-9+.-]*):")

_TABLE_HEADERS = (
    ("rank", "排序"),
    ("sample", "樣本"),
    ("target", "目標"),
    ("role", "角色"),
    ("group", "分組"),
    ("decision", "決策"),
    ("boundary", "邊界"),
    ("stop", "停止原因"),
    ("area delta", "Area 變化"),
    ("active interval", "active interval"),
    ("PNG action", "PNG 操作"),
)

_LEGEND_ITEMS = (
    ("active", "綠色 = ACTIVE selected/product interval；深綠線 = final edges"),
    ("envelope", "橘色 = selected envelope legacy/debug"),
    ("selected-chrom", "紅色 = selected chrom segment"),
    ("chrom", "淺藍色 = other chrom peak segments"),
    ("target", "琥珀色 = target RT window"),
    ("oracle", "紫色 = manual/expert oracle when present"),
)


def write_review_gallery_html(
    path: Path,
    rows: Iterable[Mapping[str, str]],
    *,
    index_tsv: Path,
) -> None:
    """Write the diagnostic-only selected-envelope human review gallery."""

    materialized = [dict(row) for row in rows]
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "<!doctype html>",
        '<html lang="zh-Hant">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>Selected Envelope 邊界審閱</title>",
        "<style>",
        _gallery_css(),
        "</style>",
        "</head>",
        "<body>",
        "<main>",
        "<h1>Selected Envelope 邊界審閱</h1>",
        *_gallery_summary(materialized, index_tsv=index_tsv, gallery_path=path),
        "<div class=\"legend\" aria-label=\"plot 圖例\">",
        *[_legend_item(css_class, text) for css_class, text in _LEGEND_ITEMS],
        "</div>",
    ]
    if not materialized:
        lines.append('<p class="empty-state">沒有選出需要審閱的 plot。</p>')
    else:
        lines.extend(_gallery_table(materialized, gallery_path=path))
        lines.extend(_lightbox_html())
    lines.extend(["</main>", _lightbox_script(), "</body>", "</html>"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _gallery_css() -> str:
    return """
:root {
  --bg: #f3f5f7;
  --surface: #ffffff;
  --surface-muted: #f8fafc;
  --text: #17202a;
  --muted: #5b6876;
  --line: #cbd5e1;
  --line-soft: #e2e8f0;
  --green: #16855b;
  --green-bg: #eaf7f0;
  --amber: #a76400;
  --amber-bg: #fff6da;
  --red: #a12b2b;
  --red-bg: #fff0f0;
  --blue: #1d6fa3;
  --blue-bg: #e8f3fb;
  --purple: #6f46c7;
  --purple-bg: #ede9fe;
  --shadow: 0 8px 28px rgba(23, 32, 42, 0.08);
}
* {
  box-sizing: border-box;
}
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: Segoe UI, Arial, sans-serif;
  line-height: 1.45;
}
main {
  max-width: 1480px;
  margin: 0 auto;
  padding: 28px 30px 44px;
}
h1 {
  margin: 0 0 12px;
  font-size: 28px;
}
a {
  color: #155e9f;
}
button,
a {
  outline-offset: 3px;
}
button:focus-visible,
a:focus-visible,
summary:focus-visible {
  outline: 3px solid #7db3dc;
}
.summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(220px, 100%), 1fr));
  gap: 10px;
  margin: 0 0 18px;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
  box-shadow: var(--shadow);
}
.summary-item {
  min-width: 0;
  padding: 10px 12px;
  border: 1px solid var(--line-soft);
  border-left: 5px solid var(--blue);
  border-radius: 6px;
  background: var(--surface-muted);
}
.summary-item.wide {
  grid-column: span 2;
}
.summary-item.authority {
  border-left-color: var(--red);
  background: var(--red-bg);
}
.summary-item span {
  display: block;
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}
.summary-item strong {
  display: block;
  margin-top: 4px;
  overflow-wrap: anywhere;
  word-break: break-word;
}
.summary-item a {
  overflow-wrap: anywhere;
  word-break: break-word;
}
.authority-note {
  grid-column: 1 / -1;
  margin: 0;
  padding: 10px 12px;
  border: 1px solid #e0a1a1;
  border-radius: 6px;
  background: #fff7f7;
  color: #742525;
  font-weight: 700;
  overflow-wrap: anywhere;
  word-break: break-word;
}
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin: 16px 0 18px;
}
.key {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  max-width: 100%;
  min-height: 32px;
  padding: 7px 10px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: var(--surface);
  font-size: 13px;
  overflow-wrap: anywhere;
  word-break: break-word;
}
.swatch {
  display: inline-block;
  width: 18px;
  height: 12px;
  border: 2px solid currentColor;
  border-radius: 2px;
}
.active {
  color: var(--green);
  background: var(--green-bg);
}
.envelope {
  color: #e55d1d;
  background: #ffedd5;
}
.selected-chrom {
  color: #c31d45;
  background: #ffe4e6;
}
.chrom {
  color: #0879b7;
  background: #e0f2fe;
}
.target {
  color: var(--amber);
  background: var(--amber-bg);
}
.oracle {
  color: var(--purple);
  background: var(--purple-bg);
}
.empty-state {
  padding: 16px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
}
.table-wrap {
  overflow-x: auto;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
  box-shadow: var(--shadow);
}
.review-table {
  width: 100%;
  min-width: 1180px;
  border-collapse: collapse;
  font-size: 13px;
}
.review-table th,
.review-table td {
  padding: 9px 10px;
  border-bottom: 1px solid var(--line-soft);
  text-align: left;
  vertical-align: top;
  overflow-wrap: anywhere;
}
.review-table th {
  position: sticky;
  top: 0;
  z-index: 2;
  background: #e9eef4;
  color: #273747;
  font-size: 12px;
  text-transform: uppercase;
}
.review-table th span {
  display: block;
}
.header-sub {
  margin-top: 2px;
  color: var(--muted);
  font-size: 11px;
  font-weight: 600;
  text-transform: none;
}
.review-row:hover td {
  background: #fbfdff;
}
.sample-cell,
.target-cell {
  font-weight: 700;
}
.numeric-cell {
  font-variant-numeric: tabular-nums;
}
.badge {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  max-width: 100%;
  padding: 2px 9px;
  border: 1px solid var(--line);
  border-left-width: 5px;
  border-radius: 999px;
  background: var(--surface-muted);
  color: #314151;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.25;
  overflow-wrap: anywhere;
  word-break: break-word;
}
.badge-ok {
  border-color: #9fd0bb;
  border-left-color: var(--green);
  background: var(--green-bg);
  color: #116444;
}
.badge-warn {
  border-color: #e0c178;
  border-left-color: var(--amber);
  background: var(--amber-bg);
  color: #795200;
}
.badge-risk {
  border-color: #e0a1a1;
  border-left-color: var(--red);
  background: var(--red-bg);
  color: #8f2727;
}
.png-cell {
  min-width: 150px;
}
.png-actions {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  gap: 8px;
  align-items: center;
}
.plot-thumb {
  display: block;
  width: 72px;
  max-width: 72px;
  height: 46px;
  object-fit: cover;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: #ffffff;
}
.lightbox-trigger {
  min-height: 38px;
  cursor: pointer;
  border: 1px solid #9fb7cb;
  border-radius: 6px;
  background: var(--blue-bg);
  color: #164c75;
  font: inherit;
  font-weight: 700;
}
.lightbox-trigger:hover {
  background: #d7eaf7;
}
.secondary-row > td {
  padding: 0 10px 10px;
  background: #fbfcfd;
}
.secondary-details {
  border: 1px solid var(--line-soft);
  border-radius: 6px;
  background: var(--surface-muted);
}
.secondary-details summary {
  cursor: pointer;
  padding: 9px 10px;
  color: #273747;
  font-weight: 700;
}
.secondary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: 8px 14px;
  margin: 0;
  padding: 0 10px 10px;
}
.secondary-grid div {
  min-width: 0;
}
.secondary-grid dt {
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
}
.secondary-grid dd {
  margin: 2px 0 0;
  overflow-wrap: anywhere;
}
.missing-plot {
  color: var(--red);
  font-weight: 700;
}
.lightbox[hidden] {
  display: none;
}
.lightbox {
  position: fixed;
  inset: 0;
  z-index: 20;
  display: grid;
  place-items: center;
  padding: 24px;
}
.lightbox-backdrop {
  position: absolute;
  inset: 0;
  background: rgba(15, 23, 42, 0.74);
}
.lightbox-panel {
  position: relative;
  display: grid;
  max-width: min(1120px, 94vw);
  max-height: 92vh;
  padding: 16px;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 20px 80px rgba(0, 0, 0, 0.36);
}
.lightbox-panel h2 {
  margin: 0 0 4px;
  font-size: 18px;
}
.lightbox-panel p {
  margin: 0 0 10px;
  color: var(--muted);
}
.lightbox-panel img {
  max-width: 100%;
  max-height: 72vh;
  object-fit: contain;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: #ffffff;
}
.lightbox-close {
  justify-self: end;
  min-height: 36px;
  cursor: pointer;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: #ffffff;
  color: var(--text);
  font: inherit;
  font-weight: 700;
}
.has-lightbox {
  overflow: hidden;
}
@media (max-width: 820px) {
  main {
    padding: 18px 12px 32px;
  }
  .summary-item.wide {
    grid-column: span 1;
  }
  .lightbox {
    padding: 10px;
  }
}
"""


def _lightbox_html() -> list[str]:
    return [
        (
            '<div class="lightbox" id="png-lightbox" role="dialog" '
            'aria-modal="true" aria-labelledby="lightbox-title" '
            'aria-describedby="lightbox-caption" hidden>'
        ),
        '<div class="lightbox-backdrop" data-lightbox-close></div>',
        '<section class="lightbox-panel">',
        (
            '<button type="button" class="lightbox-close" '
            'data-lightbox-close aria-label="關閉 PNG lightbox">關閉</button>'
        ),
        '<h2 id="lightbox-title">PNG 審閱</h2>',
        '<p id="lightbox-caption"></p>',
        '<img id="lightbox-image" alt="">',
        '<p><a id="lightbox-direct" href="">直接開啟 PNG</a></p>',
        "</section>",
        "</div>",
    ]


def _lightbox_script() -> str:
    return """<script>
(function(){
  var modal = document.getElementById('png-lightbox');
  if (!modal) { return; }
  var image = document.getElementById('lightbox-image');
  var caption = document.getElementById('lightbox-caption');
  var direct = document.getElementById('lightbox-direct');
  var closeButton = modal.querySelector('.lightbox-close');
  var previousTrigger = null;

  function focusableItems() {
    return modal.querySelectorAll('a[href], button:not([disabled])');
  }

  function openLightbox(trigger) {
    previousTrigger = trigger;
    var src = trigger.getAttribute('data-lightbox-src') || '';
    var text = trigger.getAttribute('data-lightbox-caption') || '';
    image.setAttribute('src', src);
    image.setAttribute('alt', text);
    caption.textContent = text;
    direct.setAttribute('href', src);
    modal.hidden = false;
    document.body.classList.add('has-lightbox');
    closeButton.focus();
  }

  function closeLightbox() {
    modal.hidden = true;
    image.removeAttribute('src');
    caption.textContent = '';
    direct.setAttribute('href', '');
    document.body.classList.remove('has-lightbox');
    if (previousTrigger && document.contains(previousTrigger)) {
      previousTrigger.focus();
    }
  }

  document.addEventListener('click', function(event) {
    var trigger = event.target.closest('[data-lightbox-open]');
    if (trigger) {
      event.preventDefault();
      openLightbox(trigger);
      return;
    }
    if (!modal.hidden && event.target.closest('[data-lightbox-close]')) {
      event.preventDefault();
      closeLightbox();
    }
  });

  document.addEventListener('keydown', function(event) {
    var trigger = event.target.closest('[data-lightbox-open]');
    if (trigger && (event.key === 'Enter' || event.key === ' ')) {
      event.preventDefault();
      openLightbox(trigger);
      return;
    }
    if (modal.hidden) { return; }
    if (event.key === 'Escape') {
      event.preventDefault();
      closeLightbox();
      return;
    }
    if (event.key === 'Tab') {
      var items = focusableItems();
      if (!items.length) {
        event.preventDefault();
        return;
      }
      var first = items[0];
      var last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  });
})();
</script>"""


def _gallery_summary(
    rows: Sequence[Mapping[str, str]],
    *,
    index_tsv: Path,
    gallery_path: Path,
) -> list[str]:
    index_link = _html_link(index_tsv, label=str(index_tsv), gallery_path=gallery_path)
    return [
        '<section class="summary" aria-label="審閱摘要">',
        (
            '<div class="summary-item">'
            "<span>圖數</span>"
            f"<strong>{len(rows)}</strong>"
            "</div>"
        ),
        (
            '<div class="summary-item wide">'
            "<span>Index TSV</span>"
            f"<strong>{index_link}</strong>"
            "</div>"
        ),
        (
            '<div class="summary-item authority">'
            "<span>審閱權限</span>"
            "<strong>decision_authority=diagnostic_only / review-only</strong>"
            "</div>"
        ),
        (
            '<div class="summary-item wide">'
            "<span>訊號來源</span>"
            "<strong>"
            "signal_rendering_source=RAW XIC + AsLS + Gaussian15 morphology"
            "</strong>"
            "</div>"
        ),
        (
            '<p class="authority-note">'
            "診斷審閱用，不會改 selected IntegrationResult、CSV/workbook Area "
            "或 production selection。"
            "</p>"
        ),
        "</section>",
    ]


def _gallery_table(
    rows: Sequence[Mapping[str, str]],
    *,
    gallery_path: Path,
) -> list[str]:
    lines = [
        '<div class="table-wrap">',
        '<table class="review-table">',
        "<thead><tr>",
        *[_table_header_html(field, label) for field, label in _TABLE_HEADERS],
        "</tr></thead>",
        "<tbody>",
    ]
    for row in rows:
        lines.extend(_gallery_table_rows(row, gallery_path=gallery_path))
    lines.extend(["</tbody>", "</table>", "</div>"])
    return lines


def _gallery_table_rows(
    row: Mapping[str, str],
    *,
    gallery_path: Path,
) -> list[str]:
    png_path = row.get("png_path", "")
    pdf_path = row.get("pdf_path", "")
    title = _gallery_row_title(row)
    image_src = _relative_gallery_path(png_path, gallery_path)
    pdf_link = _html_link(pdf_path, label="PDF", gallery_path=gallery_path)
    action = _png_action_html(image_src, title)
    active_interval = _interval_text(row, "resolver_rt_start", "resolver_rt_end")
    lines = [
        '<tr class="review-row">',
        _table_cell(row.get("plot_rank", "")),
        _table_cell(row.get("sample_name", ""), "sample-cell"),
        _table_cell(row.get("target_label", ""), "target-cell"),
        _table_cell(row.get("role", "")),
        _table_cell(_badge_html(row.get("plot_group", "")), raw_html=True),
        _table_cell(
            _badge_html(row.get("row_boundary_decision", "")),
            raw_html=True,
        ),
        _table_cell(_badge_html(row.get("boundary_change_class", "")), raw_html=True),
        _table_cell(row.get("boundary_stop_reason", "")),
        _table_cell(row.get("area_delta_ratio", ""), "numeric-cell"),
        _table_cell(active_interval),
        _table_cell(action, "png-cell", raw_html=True),
        "</tr>",
        '<tr class="secondary-row">',
        '<td colspan="11">',
        '<details class="secondary-details">',
        "<summary>次要 metadata</summary>",
        '<dl class="secondary-grid">',
        _fact_html(
            "legacy envelope 區間",
            _interval_text(row, "envelope_rt_start", "envelope_rt_end"),
        ),
        _fact_html(
            "chrom segment 區間",
            _interval_text(
                row,
                "selected_chrom_peak_segment_rt_start",
                "selected_chrom_peak_segment_rt_end",
            ),
        ),
        _fact_html(
            "chrom class 分類",
            row.get("selected_chrom_peak_segment_class", ""),
        ),
        _fact_html(
            "chrom projection",
            row.get("selected_chrom_peak_segment_projection", ""),
        ),
        _fact_html(
            "chrom stop 停止原因",
            row.get("selected_chrom_peak_segment_stop_reason", ""),
        ),
        _fact_html(
            "oracle 區間",
            _interval_text(row, "oracle_rt_start", "oracle_rt_end"),
        ),
        _fact_html("oracle status", row.get("oracle_status", "")),
        _fact_html("PDF", pdf_link, raw_html=True),
        _fact_html("PNG artifact path", row.get("png_path", "")),
        _fact_html("PDF artifact path", row.get("pdf_path", "")),
        "</dl>",
        "</details>",
        "</td>",
        "</tr>",
    ]
    return lines


def _gallery_row_title(row: Mapping[str, str]) -> str:
    return (
        f"{row.get('plot_rank', '')}. {row.get('sample_name', '')} | "
        f"{row.get('target_label', '')} | {row.get('role', '')} | "
        f"decision={row.get('row_boundary_decision', '')}"
    )


def _png_action_html(image_src: str, title: str) -> str:
    if not image_src:
        return '<span class="missing-plot">PNG path 缺失或無法安全連結。</span>'
    escaped_src = html.escape(image_src, quote=True)
    escaped_title = html.escape(title, quote=True)
    open_label = f"開啟 PNG：{escaped_title}"
    return (
        '<div class="png-actions">'
        f'<a class="png-fallback" href="{escaped_src}" '
        'data-lightbox-open '
        f'data-lightbox-src="{escaped_src}" '
        f'data-lightbox-caption="{escaped_title}" '
        f'aria-label="{open_label}">'
        f'<img class="plot-thumb" src="{escaped_src}" loading="lazy" '
        f'alt="{escaped_title}">'
        "</a>"
        f'<button type="button" class="lightbox-trigger" data-lightbox-open '
        f'data-lightbox-src="{escaped_src}" '
        f'data-lightbox-caption="{escaped_title}" '
        f'aria-label="{open_label}">'
        "開啟 PNG"
        "</button>"
        "</div>"
    )


def _table_header_html(field: str, label: str) -> str:
    return (
        '<th scope="col">'
        f'<span lang="en">{html.escape(field, quote=True)}</span>'
        f'<span class="header-sub">{html.escape(label, quote=True)}</span>'
        "</th>"
    )


def _table_cell(
    value: object,
    class_name: str = "",
    *,
    raw_html: bool = False,
) -> str:
    class_attr = f' class="{html.escape(class_name, quote=True)}"' if class_name else ""
    content = str(value) if raw_html else html.escape(str(value), quote=True)
    return f"<td{class_attr}>{content or '&nbsp;'}</td>"


def _fact_html(
    label: str,
    value: object,
    *,
    raw_html: bool = False,
) -> str:
    content = str(value) if raw_html else html.escape(str(value), quote=True)
    return (
        "<div>"
        f"<dt>{html.escape(label, quote=True)}</dt>"
        f"<dd>{content or '&nbsp;'}</dd>"
        "</div>"
    )


def _badge_html(value: object) -> str:
    text = str(value).strip()
    if not text:
        return ""
    return (
        f'<span class="badge {_badge_class(text)}">'
        f"{html.escape(text, quote=True)}"
        "</span>"
    )


def _badge_class(text: str) -> str:
    normalized = text.lower()
    if any(token in normalized for token in ("externalize", "conflict", "rejected")):
        return "badge-risk"
    if any(token in normalized for token in ("accept", "review_only")):
        return "badge-ok"
    if any(token in normalized for token in ("high_risk", "warning", "shoulder")):
        return "badge-warn"
    return "badge-neutral"


def _legend_item(css_class: str, text: str) -> str:
    return (
        f'<span class="key"><span class="swatch {css_class}"></span>'
        f"{html.escape(text)}</span>"
    )


def _html_link(path_value: str | Path, *, label: str, gallery_path: Path) -> str:
    href = _relative_gallery_path(str(path_value), gallery_path)
    if not href:
        return ""
    return (
        f'<a href="{html.escape(href, quote=True)}">'
        f"{html.escape(label)}</a>"
    )


def _relative_gallery_path(path_value: str, gallery_path: Path) -> str:
    value = path_value.strip()
    if not value:
        return ""
    scheme_match = _URL_SCHEME_RE.match(value)
    if scheme_match is not None and len(scheme_match.group(1)) > 1:
        return ""
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    try:
        candidate_resolved = candidate.resolve()
        gallery_resolved = gallery_path.parent.resolve()
    except OSError:
        return ""
    try:
        relative = candidate_resolved.relative_to(gallery_resolved)
        return relative.as_posix()
    except ValueError:
        return candidate_resolved.as_posix()


def _interval_text(
    row: Mapping[str, str],
    start_field: str,
    end_field: str,
) -> str:
    start = row.get(start_field, "").strip()
    end = row.get(end_field, "").strip()
    if not start and not end:
        return ""
    return f"{start}-{end}"
