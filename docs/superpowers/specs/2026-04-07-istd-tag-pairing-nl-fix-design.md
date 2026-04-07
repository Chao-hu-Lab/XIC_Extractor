# Design: ISTD Tag, ISTD Pairing & NL Scroll Fix

**Date:** 2026-04-07
**Branch:** feat/istd-tag-pairing-nl-fix
**Status:** Approved

---

## Overview

Three coordinated changes to the XIC Extractor:

1. **ISTD Tag** — mark targets as internal standards; warn in GUI and Excel if any ISTD is not detected in all samples.
2. **ISTD Pairing** — link an analyte to its paired ISTD; compute RT Δ% in the Excel Summary sheet for NL-confirmed samples only.
3. **NL Scroll Fix** — prevent the NL(Da) combo box from changing value when the user scrolls the main window.

---

## 1. Data Layer — `config/targets.csv` + `gui/config_io.py`

### New fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `is_istd` | `true` / `false` | `false` | Marks this target as an Internal Standard |
| `istd_pair` | string (label name) | empty | Set on the **analyte** row; value is the label of its paired ISTD (e.g. `5-hmdC.istd_pair = d3-5-hmdC`) |

### `config_io.py` changes
- Append `is_istd` and `istd_pair` to `_TARGETS_FIELDS`.
- `write_targets()` already iterates `_TARGETS_FIELDS`, so it picks up the new fields automatically.
- `read_targets()` returns raw dicts; callers that need the new fields read them by key.

### Backward compatibility
Existing `targets.csv` files without the new columns are safe: `dict.get("is_istd", "false")` and `dict.get("istd_pair", "")` are used everywhere as fallbacks.

---

## 2. UI Layer — `gui/sections/targets_section.py`

### New columns

Inserted **after Label** (shift all existing column indices right by 2):

| Col | Header | Width | Widget |
|-----|--------|-------|--------|
| `_COL_ISTD` | `ISTD` | 55 px | `QCheckBox` (centred) |
| `_COL_PAIR` | `ISTD Pair` | 130 px | Editable `QTableWidgetItem` |

Total columns: 9 (Label, ISTD, ISTD Pair, m/z, RT min, RT max, ppm, NL(Da), ✕).

### Behaviour
- `_append_row()` creates a `QCheckBox` for `_COL_ISTD`; checking it sets dirty.
- `_COL_PAIR` is a plain editable item; only meaningful when the row is **not** an ISTD (analyte side of the pair).
- `get_targets()` reads both new fields and includes them in the returned dict.
- `load()` populates both widgets from the incoming dict.

### NL Scroll Fix (also in this file)

Add an internal subclass:

```python
class _NoScrollComboBox(QComboBox):
    def wheelEvent(self, event):
        if not self.hasFocus():
            event.ignore()  # propagate to parent scroll area
        else:
            super().wheelEvent(event)
```

Replace `QComboBox()` with `_NoScrollComboBox()` in `_make_nl_combo()`.

---

## 3. Analysis Layer — `scripts/csv_to_excel.py`

### `_load_column_meta()` additions
Both new fields are stored **inside the existing `col_meta` dict** under the analyte's `_RT` key, so no API change is needed for `_build_data_sheet` or `_build_summary_sheet`:

```python
meta[f"{label}_RT"]["is_istd"] = row.get("is_istd", "false").lower() == "true"
meta[f"{label}_RT"]["istd_pair"] = row.get("istd_pair", "").strip()
```

- `nl_col` logic unchanged.

### Data sheet — ISTD ND highlight
- When rendering a cell for an ISTD target (column type `ms1_rt` or `ms1_int`) where `raw_val in ND_ERROR`:
  - Use fill `#FF7043` (deep orange) instead of the standard `#FFE0B2` (light orange) used for non-ISTD ND.
- Non-ISTD ND cells remain unchanged.

### `run()` — ISTD ND warning print
After the existing per-target detection prints, iterate all ISTD targets:

```
ISTD_ND: d3-5-hmdC 18/20
```

Printed only when `detected < total` for an ISTD. The format is machine-readable so `pipeline_worker._parse_summary()` can parse it.

### Summary sheet — `RT Δ vs ISTD (%)` metric row

Added as a new row in `_build_summary_sheet()`, after the existing metric rows.

**Algorithm for each analyte column that has `istd_pair` set:**
1. Identify qualifying samples: both `{analyte}_NL` and `{istd}_NL` are `OK` or `WARN_*`.
2. For each qualifying sample: `delta = abs(RT_analyte - RT_istd) / RT_istd * 100`.
3. Compute mean and SD across all qualifying samples.
4. Cell value: `{mean:.2f}±{sd:.2f}% (n={k})`. If no qualifying samples: `—`.

**For ISTD columns** (i.e. columns where `is_istd=true`): display `—` (ISTDs are not compared against themselves).

---

## 4. Pipeline Layer — `gui/workers/pipeline_worker.py`

### `_parse_summary()` — new parsing block

```python
if istd_nd := re.search(r"ISTD_ND:\s+(\S+)\s+(\d+)/(\d+)", line):
    label = istd_nd.group(1)
    detected = int(istd_nd.group(2))
    total = int(istd_nd.group(3))
    istd_warnings.append({"label": label, "detected": detected, "total": total})
```

### Summary dict additions

```python
return {
    ...existing keys...,
    "istd_warnings": istd_warnings,   # list[dict]: label, detected, total
}
```

---

## 5. Results Layer — `gui/sections/results_section.py`

### Warning banner

In `update_results()`, after clearing the grid, before adding cards:

- If `summary.get("istd_warnings")` is non-empty, build and show a `QLabel` warning banner:
  - Style: orange background (`#FF7043`), white bold text.
  - Text: `⚠ ISTD 未全偵測：d3-5-hmdC (18/20)、[13C,15N2]-8-oxo-Guo (19/20)`
  - Inserted at the top of `_body_layout`, above the card grid.
- If empty or absent, hide/clear the banner.

---

## Files Changed

| File | Change |
|------|--------|
| `config/targets.csv` | Add `is_istd`, `istd_pair` columns |
| `config/targets.example.csv` | Same |
| `gui/config_io.py` | Extend `_TARGETS_FIELDS` |
| `gui/sections/targets_section.py` | New columns, `_NoScrollComboBox`, load/get updates |
| `scripts/csv_to_excel.py` | ISTD ND highlight, RT Δ metric, ISTD_ND print |
| `gui/workers/pipeline_worker.py` | Parse `ISTD_ND` lines, add `istd_warnings` to summary |
| `gui/sections/results_section.py` | ISTD warning banner |

---

## Out of Scope

- No changes to `01_extract_xic.ps1` (PS1 script remains unchanged).
- No per-sample RT Δ column in the Data sheet (Summary sheet only).
- No UI for editing `nl_ppm_warn` / `nl_ppm_max` (already hidden in `_row_meta`).
