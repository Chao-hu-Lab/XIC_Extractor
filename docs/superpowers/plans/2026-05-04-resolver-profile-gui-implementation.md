# Resolver Profile GUI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** Make the GUI expose peak resolver choice as two resolver-specific profiles so `legacy_savgol` and `local_minimum` parameters do not appear to be one mixed method.
**Architecture:** Keep the existing single `settings.csv` and `ExtractionConfig` contract, but reorganize `SettingsSection` so the selected resolver controls which parameter panel is visible. Preserve inactive profile values during round-trip, and apply the local minimum preset only when the user clicks an explicit preset button.
**Tech Stack:** Python 3.13, PyQt6, pytest-qt, uv, existing `SettingsSection` tests.
**Spec:** `docs/superpowers/specs/2026-05-04-resolver-profile-gui-spec.md`

---

## Execution Rules

1. Use TDD for every behavior change: write failing test, run it, implement minimal code, rerun.
2. Do not change extraction algorithms in this plan.
3. Do not change workbook output schema.
4. Do not switch default resolver away from `legacy_savgol`.
5. Keep `settings.csv` / `settings.example.csv` as the single config contract.
6. Preserve inactive profile values when the user changes resolver mode in the GUI.
7. Preset application must be an explicit button click, not a side effect of resolver switching.
8. Commit after each task if implementation is being executed task-by-task.

---

## Phase 0 — Orientation

**Purpose:** Confirm current GUI/settings state before edits.

Read:

- `gui/sections/settings_section.py`
- `tests/test_settings_section.py`
- `tests/test_settings_section_advanced.py`
- `xic_extractor/settings_schema.py`
- `config/settings.example.csv`
- `README.md`

Confirm:

- `resolver_mode` currently lives in Advanced.
- `smooth_window`, `smooth_polyorder`, `peak_rel_height`, and `peak_min_prominence_ratio` are visible in the main Signal processing row.
- local minimum resolver parameters are in Advanced.
- `get_values()` round-trips all resolver keys.

No code changes in this phase.

---

## Phase 1 — Profile Visibility Contract

**Purpose:** Add tests that define the target GUI behavior before implementation.

### Task 1.1 — RED: legacy profile hides local controls in main Settings

**Files:**

- Modify: `tests/test_settings_section_advanced.py`

**Step 1: Write the failing test**

Add:

```python
def test_resolver_profiles_show_legacy_controls_for_legacy_mode(qtbot) -> None:
    section = SettingsSection()
    qtbot.addWidget(section)
    section.show()
    section.load({**_canonical_settings(), "resolver_mode": "legacy_savgol"})

    assert section._legacy_resolver_panel.isVisible()
    assert not section._local_minimum_resolver_panel.isVisible()
    assert section._smooth_window_spin.isVisible()
    assert section._peak_min_prominence_ratio_spin.isVisible()
    assert not section._resolver_chrom_threshold_spin.isVisible()
    assert not section._resolver_min_ratio_top_edge_spin.isVisible()
    assert section._resolver_mode_combo.isVisible()
```

**Step 2: Run test to verify it fails**

```powershell
uv run pytest tests\test_settings_section_advanced.py::test_resolver_profiles_show_legacy_controls_for_legacy_mode -v
```

Expected: FAIL because `_legacy_resolver_panel` / `_local_minimum_resolver_panel` do not exist.

### Task 1.2 — RED: local profile hides legacy controls in main Settings

**Files:**

- Modify: `tests/test_settings_section_advanced.py`

**Step 1: Write the failing test**

Add:

```python
def test_resolver_profiles_show_local_controls_for_local_minimum_mode(qtbot) -> None:
    section = SettingsSection()
    qtbot.addWidget(section)
    section.show()
    section.load({**_canonical_settings(), "resolver_mode": "local_minimum"})

    assert not section._legacy_resolver_panel.isVisible()
    assert section._local_minimum_resolver_panel.isVisible()
    assert not section._smooth_window_spin.isVisible()
    assert not section._peak_min_prominence_ratio_spin.isVisible()
    assert section._resolver_chrom_threshold_spin.isVisible()
    assert section._resolver_min_ratio_top_edge_spin.isVisible()
    assert section._apply_local_minimum_preset_button.isVisible()
```

**Step 2: Run test to verify it fails**

```powershell
uv run pytest tests\test_settings_section_advanced.py::test_resolver_profiles_show_local_controls_for_local_minimum_mode -v
```

Expected: FAIL because profile panels do not exist.

### Task 1.3 — GREEN: create profile panels

**Files:**

- Modify: `gui/sections/settings_section.py`

**Implementation:**

1. Add two panel widgets:

```python
self._legacy_resolver_panel = QWidget()
self._local_minimum_resolver_panel = QWidget()
```

2. Move existing Signal processing controls into `_legacy_resolver_panel`.
3. Move local minimum resolver controls into `_local_minimum_resolver_panel`.
4. Add a visible main Settings `Peak resolver` row containing `_resolver_mode_combo`.
5. Add `_apply_local_minimum_preset_button` inside the local panel, but do not wire behavior until Phase 2.
6. Add helper:

```python
def _update_resolver_profile_visibility(self) -> None:
    is_local = self._resolver_mode_combo.currentText() == "local_minimum"
    self._legacy_resolver_panel.setVisible(not is_local)
    self._local_minimum_resolver_panel.setVisible(is_local)
```

7. Call helper after `_load_advanced_values()`.
8. Connect `self._resolver_mode_combo.currentTextChanged` to a mode-change handler that updates visibility and dirty state only.

**Step 4: Run tests**

```powershell
uv run pytest tests\test_settings_section_advanced.py::test_resolver_profiles_show_legacy_controls_for_legacy_mode tests\test_settings_section_advanced.py::test_resolver_profiles_show_local_controls_for_local_minimum_mode -v
```

Expected: PASS.

**Commit:**

```powershell
git add gui/sections/settings_section.py tests/test_settings_section_advanced.py
git commit -m "feat(gui): split resolver-specific settings panels"
```

---

## Phase 2 — Local Minimum Preset Behavior

**Purpose:** Make the explicit preset button apply the tested preset without overwriting loaded or inactive settings during resolver switching.

### Task 2.1 — RED: switching to local preserves inactive custom local values

**Files:**

- Modify: `tests/test_settings_section_advanced.py`

**Step 1: Write the failing test**

Add:

```python
def test_switching_to_local_minimum_preserves_inactive_custom_values(qtbot) -> None:
    section = SettingsSection()
    qtbot.addWidget(section)
    section.show()
    section.load(
        {
            **_canonical_settings(),
            "resolver_mode": "legacy_savgol",
            "resolver_min_search_range_min": "0.123",
            "resolver_min_ratio_top_edge": "2.5",
            "resolver_peak_duration_max": "3.5",
        }
    )

    section._resolver_mode_combo.setCurrentText("local_minimum")

    values = section.get_values()
    assert values["resolver_mode"] == "local_minimum"
    assert values["resolver_min_search_range_min"] == "0.123"
    assert values["resolver_min_ratio_top_edge"] == "2.5"
    assert values["resolver_peak_duration_max"] == "3.5"
```

**Step 2: Run test to verify it fails**

```powershell
uv run pytest tests\test_settings_section_advanced.py::test_switching_to_local_minimum_preserves_inactive_custom_values -v
```

Expected: FAIL until resolver mode switching updates visibility without applying a preset.

### Task 2.2 — RED: preset button applies local preset

**Files:**

- Modify: `tests/test_settings_section_advanced.py`

**Step 1: Write the failing test**

Add:

```python
def test_apply_local_minimum_preset_button_applies_validated_preset(qtbot) -> None:
    section = SettingsSection()
    qtbot.addWidget(section)
    section.show()
    section.load(
        {
            **_canonical_settings(),
            "resolver_mode": "local_minimum",
            "resolver_min_search_range_min": "0.123",
            "resolver_min_ratio_top_edge": "2.5",
            "resolver_peak_duration_max": "3.5",
        }
    )

    section._apply_local_minimum_preset_button.click()

    values = section.get_values()
    assert values["resolver_chrom_threshold"] == "0.05"
    assert values["resolver_min_search_range_min"] == "0.08"
    assert values["resolver_min_relative_height"] == "0"
    assert values["resolver_min_ratio_top_edge"] == "1.7"
    assert values["resolver_peak_duration_min"] == "0"
    assert values["resolver_peak_duration_max"] == "10"
```

**Step 2: Run test**

```powershell
uv run pytest tests\test_settings_section_advanced.py::test_apply_local_minimum_preset_button_applies_validated_preset -v
```

Expected: FAIL because preset button behavior does not exist.

### Task 2.3 — RED: loading existing local settings does not overwrite

**Files:**

- Modify: `tests/test_settings_section_advanced.py`

**Step 1: Write the failing test**

Add:

```python
def test_loading_local_minimum_preserves_existing_local_values(qtbot) -> None:
    section = SettingsSection()
    qtbot.addWidget(section)
    section.show()
    section.load(
        {
            **_canonical_settings(),
            "resolver_mode": "local_minimum",
            "resolver_min_search_range_min": "0.123",
            "resolver_min_ratio_top_edge": "2.5",
            "resolver_peak_duration_max": "3.5",
        }
    )

    values = section.get_values()
    assert values["resolver_min_search_range_min"] == "0.123"
    assert values["resolver_min_ratio_top_edge"] == "2.5"
    assert values["resolver_peak_duration_max"] == "3.5"
```

**Step 2: Run test**

```powershell
uv run pytest tests\test_settings_section_advanced.py::test_loading_local_minimum_preserves_existing_local_values -v
```

Expected: PASS after Phase 1 if `load()` remains signal-blocked; if it fails, fix before continuing.

### Task 2.4 — GREEN: apply preset only on button click

**Files:**

- Modify: `gui/sections/settings_section.py`

**Implementation:**

1. Add constant:

```python
_LOCAL_MINIMUM_GUI_PRESET = {
    "resolver_chrom_threshold": "0.05",
    "resolver_min_search_range_min": "0.08",
    "resolver_min_relative_height": "0",
    "resolver_min_absolute_height": "25.0",
    "resolver_min_ratio_top_edge": "1.7",
    "resolver_peak_duration_min": "0",
    "resolver_peak_duration_max": "10",
    "resolver_min_scans": "5",
}
```

2. Add method:

```python
def _apply_local_minimum_preset(self) -> None:
    self._resolver_chrom_threshold_spin.setValue(0.05)
    self._resolver_min_search_range_min_spin.setValue(0.08)
    self._resolver_min_relative_height_spin.setValue(0.0)
    self._resolver_min_absolute_height_spin.setValue(25.0)
    self._resolver_min_ratio_top_edge_spin.setValue(1.7)
    self._resolver_peak_duration_min_spin.setValue(0.0)
    self._resolver_peak_duration_max_spin.setValue(10.0)
    self._resolver_min_scans_spin.setValue(5)
```

3. Add slot for resolver mode changes:

```python
def _on_resolver_mode_changed(self, mode: str) -> None:
    self._update_resolver_profile_visibility()
    self._set_dirty(True)
```

4. Connect `currentTextChanged` to `_on_resolver_mode_changed`.
5. Ensure `load()` uses `QSignalBlocker(self._resolver_mode_combo)` so loading does not call the slot.
6. Connect `_apply_local_minimum_preset_button.clicked` to `_apply_local_minimum_preset`.
7. `_apply_local_minimum_preset()` sets dirty state after updating spin values.

**Step 4: Run tests**

```powershell
uv run pytest tests\test_settings_section_advanced.py -v
```

Expected: PASS.

**Commit:**

```powershell
git add gui/sections/settings_section.py tests/test_settings_section_advanced.py
git commit -m "feat(gui): apply local minimum resolver preset"
```

---

## Phase 3 — Canonical Defaults And Copy

**Purpose:** Keep config/docs consistent with the new GUI profile model.

### Task 3.1 — RED: canonical local defaults reflect chosen preset

**Files:**

- Modify: `tests/test_config.py` or `tests/test_settings_new_fields.py`

**Step 1: Write failing test**

Add assertions for canonical defaults:

```python
from xic_extractor.settings_schema import CANONICAL_SETTINGS_DEFAULTS


def test_local_minimum_defaults_match_validated_gui_preset() -> None:
    assert CANONICAL_SETTINGS_DEFAULTS["resolver_chrom_threshold"] == "0.05"
    assert CANONICAL_SETTINGS_DEFAULTS["resolver_min_search_range_min"] == "0.08"
    assert CANONICAL_SETTINGS_DEFAULTS["resolver_min_relative_height"] == "0.0"
    assert CANONICAL_SETTINGS_DEFAULTS["resolver_min_ratio_top_edge"] == "1.7"
    assert CANONICAL_SETTINGS_DEFAULTS["resolver_peak_duration_min"] == "0.0"
    assert CANONICAL_SETTINGS_DEFAULTS["resolver_peak_duration_max"] == "10.0"
```

Also add parser tests:

```python
def test_local_minimum_zero_threshold_like_values_are_valid(tmp_path: Path) -> None:
    config_dir = _write_config(
        tmp_path,
        settings_overrides={
            "resolver_min_relative_height": "0.0",
            "resolver_peak_duration_min": "0.0",
            "resolver_peak_duration_max": "10.0",
        },
    )

    config, _targets = load_config(config_dir)

    assert config.resolver_min_relative_height == 0.0
    assert config.resolver_peak_duration_min == 0.0
```

Add GUI range test:

```python
def test_local_minimum_profile_allows_zero_values(qtbot) -> None:
    section = SettingsSection()
    qtbot.addWidget(section)
    section.show()
    section.load({**_canonical_settings(), "resolver_mode": "local_minimum"})

    section._resolver_min_relative_height_spin.setValue(0.0)
    section._resolver_peak_duration_min_spin.setValue(0.0)

    values = section.get_values()
    assert values["resolver_min_relative_height"] == "0"
    assert values["resolver_peak_duration_min"] == "0"
```

**Step 2: Run test**

```powershell
uv run pytest tests\test_config.py tests\test_settings_new_fields.py -v
```

Expected: FAIL until canonical defaults, parser validation, and GUI ranges are updated.

### Task 3.2 — GREEN: update defaults and examples

**Files:**

- Modify: `xic_extractor/settings_schema.py`
- Modify: `xic_extractor/config.py`
- Modify: `gui/sections/settings_section.py`
- Modify: `config/settings.example.csv`
- Modify: `README.md`

**Implementation:**

Update local minimum defaults:

```text
resolver_min_search_range_min = 0.08
resolver_min_relative_height = 0.0
resolver_min_ratio_top_edge = 1.7
resolver_peak_duration_min = 0.0
resolver_peak_duration_max = 10.0
```

Update validation:

```text
resolver_min_relative_height: 0 <= value <= 1
resolver_peak_duration_min: value >= 0
resolver_peak_duration_max: value > 0
resolver_peak_duration_min <= resolver_peak_duration_max
```

Update GUI spin ranges:

```text
resolver_min_relative_height minimum = 0.0
resolver_peak_duration_min minimum = 0.0
```

Keep:

```text
resolver_mode = legacy_savgol
resolver_chrom_threshold = 0.05
resolver_min_absolute_height = 25.0
resolver_min_scans = 5
```

README should state:

- `legacy_savgol` is still default.
- GUI separates resolver-specific parameters.
- `local_minimum` preset is intended for method development / complex matrices.

**Step 4: Run tests**

```powershell
uv run pytest tests\test_config.py tests\test_settings_new_fields.py tests\test_settings_section_advanced.py -v
```

Expected: PASS.

**Commit:**

```powershell
git add xic_extractor/settings_schema.py xic_extractor/config.py gui/sections/settings_section.py config/settings.example.csv README.md tests/test_config.py tests/test_settings_new_fields.py tests/test_settings_section_advanced.py
git commit -m "docs(config): document resolver profile defaults"
```

---

## Phase 4 — Regression And Visual Smoke

**Purpose:** Verify the GUI refactor did not break settings round-trip or execution config.

### Task 4.1 — Run GUI/settings tests

```powershell
uv run pytest tests\test_settings_section.py tests\test_settings_section_advanced.py tests\test_pipeline_worker.py -v
```

Expected: PASS.

### Task 4.2 — Run config and metadata tests

```powershell
uv run pytest tests\test_config.py tests\test_settings_new_fields.py tests\test_output_metadata.py -v
```

Expected: PASS.

### Task 4.3 — Optional GUI manual smoke

If local display is available:

```powershell
uv run python gui_app.py
```

Check:

- Settings loads.
- `Peak resolver` selector is visible.
- `legacy_savgol` shows legacy controls only.
- `local_minimum` shows local controls only.
- Clicking `Apply Local Minimum Preset` applies preset.
- Switching back does not erase saved local values.

### Task 4.4 — Final broader test

```powershell
uv run pytest --tb=short -q
```

If this is too slow in the active environment, run the targeted tests above and document why full suite was skipped.

**Final commit if needed:**

```powershell
git add <changed files>
git commit -m "test(gui): cover resolver profile settings"
```

---

## Implementation Notes

- Prefer QWidget containers over complicated custom widgets unless layout reuse becomes painful.
- Tests should assert behavior and visibility, not exact grid coordinates beyond existing compact-row tests.
- Use `QSignalBlocker` during `load()` to prevent preset application from changing loaded historical settings.
- If exact string formatting differs (`"10"` vs `"10.0"`), choose one canonical format and update tests consistently with existing `_float_setting_text()` behavior.
- Do not remove resolver keys from `_ADVANCED_SETTING_KEYS`; the key list describes config surface, not only visible controls.
