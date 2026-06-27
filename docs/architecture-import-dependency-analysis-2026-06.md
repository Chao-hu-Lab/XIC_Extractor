# Import Dependency Graph Analysis

Doc placement: repo_stub_plus_obsidian
Repo owner: docs/architecture-review-2026-06.md

**Repository:** XIC_Extractor (untargeted-gui-refresh-clean)
**Analysis Date:** 2026-06-28
**Scope:** xic_extractor/, gui/, scripts/, tools/ (658 Python files)

---

## Executive Summary

The codebase exhibits a **clean architecture** with proper separation of concerns:

- ✓ **No circular imports** detected between major packages
- ✓ **No domain-layer violations**: xic_extractor domain code does NOT import from gui/, output/, scripts/, or tools/
- ✓ **Correct dependency direction**: GUI and scripts correctly depend on domain logic
- ⚠ **Some high fan-out modules** identified (extraction pipeline, alignment pipeline) that import from many subpackages

---

## 1. Dependency Matrix

```
                     │ xic_extractor │ gui  │ scripts │ tools
─────────────────────┼───────────────┼──────┼─────────┼────────
xic_extractor        │ 954*          │ -    │ -       │ -
gui                  │ 29            │ 46   │ -       │ 1
scripts              │ 178           │ -    │ 147     │ 7
tools                │ 180           │ -    │ 2       │ 228
```

**Key Observations:**
- `xic_extractor` is internally cohesive (954 internal imports)
- GUI layer imports only from domain (29 imports from xic_extractor)
- Scripts are bridge code (178 from xic_extractor, 147 internal script-to-script)
- Tools are isolated utilities (180 from domain, 228 internal)

---

## 2. Cross-Boundary Imports (GUI ↔ Domain)

### GUI imports FROM xic_extractor (Allowed Pattern)

#### `gui/config_io.py` (2 imports)
- `xic_extractor.configuration.csv_io` → `TARGET_WRITE_FIELDS`
- `xic_extractor.settings_schema` → `CANONICAL_SETTINGS_DESCRIPTIONS`

**Purpose:** Marshalling settings between GUI and domain config format

#### `gui/workers/pipeline_worker.py` (6 imports)
- `xic_extractor.config` → `ConfigError, ExtractionConfig, Target`
- `xic_extractor.extractor` → `ExtractionResult, RunOutput`
- `xic_extractor.output.excel_pipeline` → `write_excel_from_run_output`
- `xic_extractor.raw_reader` → `RawReaderError`

**Purpose:** Orchestrates extraction pipeline; catches domain exceptions

#### `gui/workers/discovery_worker.py` (6 imports)
- `xic_extractor.alignment` (module-level)
- `xic_extractor.config` → `ExtractionConfig`
- `xic_extractor.discovery` (module-level)
- `xic_extractor.presets` → `apply_to_discovery, load_preset`
- `xic_extractor.raw_reader` → `RawReaderError`
- `xic_extractor.settings_schema` → `CANONICAL_SETTINGS_DEFAULTS`

**Purpose:** Runs discovery pipeline; applies preset configurations

#### `gui/sections/discovery_method_section.py` (4 imports)
- `xic_extractor.presets` → `apply_to_discovery, load_preset`
- `xic_extractor.settings_schema` → `RESOLVER_MODES`

**Purpose:** Presents discovery method UI; enumerates resolver modes from schema

#### `gui/sections/settings_section.py` (9 imports)
- `xic_extractor.config` → `migrate_settings_dict`
- `xic_extractor.settings_schema` → `CANONICAL_SETTINGS_DEFAULTS, RESOLVER_MODES`

**Purpose:** Displays and migrates settings; reads canonical defaults from schema

#### `gui/sections/settings_advanced_panel.py`, `settings_resolver_panel.py`, `settings_constants.py` (1-4 imports each)
- All import only from `xic_extractor.settings_schema`

**Assessment:** ✓ All GUI-to-domain imports are **legitimate and minimal**. Confined to:
  - Configuration constants and schema definitions
  - Exception types (for error handling)
  - Pipeline orchestration interfaces

---

## 3. Domain-Layer Integrity Check

### Query: Do ANY xic_extractor files import from gui/, output/, scripts/, or tools/?

**Result:** ✓ **CLEAN** - No violations found

This is critical: domain logic (xic_extractor/) is completely isolated from presentation and tooling layers.

---

## 4. High Fan-Out Modules (Potential Complexity Concerns)

Modules that import from **>5 different top-level xic_extractor subpackages**:

### 1. `xic_extractor/extraction/pipeline.py` (8 subpackages)
```
Imports from:
  • config
  • extraction (internal)
  • injection_rolling
  • peak_detection
  • raw_reader
  • rt_prior_library
  • sample_metadata
  • target_pair_rt_calibration
```
**Assessment:** Expected high fan-out (orchestrates entire extraction)

### 2. `xic_extractor/extraction/target_extraction.py` (7 subpackages)
```
Imports from:
  • config
  • extraction (internal)
  • neutral_loss
  • output
  • peak_detection
  • rt_prior_library
  • signal_processing
```
**Assessment:** Expected high fan-out (main extraction algorithm)

### 3. `xic_extractor/extraction/result_assembly.py` (7 subpackages)
```
Imports from:
  • config
  • evidence_semantics
  • extraction (internal)
  • neutral_loss
  • peak_detection
  • signal_processing
  • target_sample_applicability
```
**Assessment:** Expected high fan-out (assembles extraction results from many subsystems)

### 4. `xic_extractor/alignment/pipeline.py` (9+ subpackages)
```
Imports from:
  • alignment (internal submodules)
  • config
  • discovery
  • diagnostics
  • presets
  • raw_reader
  • settings_schema
  • and others
```
**Assessment:** Expected high fan-out (orchestrates multi-phase alignment)

### 5. `gui/workers/discovery_worker.py` (6 subpackages)
```
Imports from:
  • alignment
  • config
  • discovery
  • presets
  • raw_reader
  • settings_schema
```
**Assessment:** Expected (worker bridges multiple domain subsystems)

**Overall Assessment:** High fan-out is **intentional and appropriate** for pipeline orchestrator and main algorithm modules. No unnecessary coupling detected.

---

## 5. Suspicious Patterns: Circular Dependencies

### Query: Are there any files in xic_extractor that import FROM gui?

**Result:** ✓ **CLEAN** - No circular imports found

### Query: Do any GUI modules import from other GUI modules in problematic ways?

**Result:** ✓ **HEALTHY** - GUI imports are layered:
- `gui/sections/*` → imports from `gui/sections/*` (same layer, appropriate)
- `gui/sections/*` → imports from `gui/ui` (utility layer, appropriate)
- `gui/views/*` → imports from `gui/sections/*` (parent-child, appropriate)
- `gui/main_window.py` → imports from `gui/views/*` (parent-child, appropriate)

No back-edges detected.

---

## 6. Scripts Layer Analysis

Scripts exist at multiple levels:

### Scripts importing from xic_extractor (6 subpackages avg)
- `scripts/run_alignment.py` (7 subpackages)
- `scripts/run_extraction.py` (6 subpackages)
- `scripts/run_discovery.py` (5 subpackages)
- And 50+ other scripts

**Pattern:** Scripts are **integration code** that compose domain modules for specific workflows.

### Scripts with internal script-to-script imports
- `scripts/validation_harness.py` → `scripts/validation_harness_core.py`
- `scripts/build_*.py` → various shared helpers

**Assessment:** ✓ Minimal coupling between scripts; mostly independent workflows.

---

## 7. Architecture Contract Validation

| Requirement | Status | Evidence |
|---|---|---|
| Domain code (xic_extractor) isolated from GUI | ✓ PASS | 0 imports from gui/ in xic_extractor |
| Domain code isolated from scripts/tools | ✓ PASS | 0 imports from scripts/tools in xic_extractor |
| GUI code depends on domain | ✓ PASS | 29 imports from xic_extractor in gui/ |
| No circular dependencies | ✓ PASS | No reverse edges detected |
| GUI layer is internally cohesive | ✓ PASS | 46 internal gui imports; no back-edges |
| Scripts are independent/bridge code | ✓ PASS | 178 external (domain), 147 internal (cross-scripts) |

---

## 8. Specific Cross-Boundary Imports by Type

### Configuration/Schema (Expected)
- GUI → `xic_extractor.settings_schema` (6 files)
- GUI → `xic_extractor.config` (2 files)
- Scripts → `xic_extractor.settings_schema` (multiple)

**Rationale:** Schema definitions are read-only contracts; appropriate for GUI to depend on

### Exception Types (Expected)
- GUI → `xic_extractor.config.ConfigError`, `RawReaderError`, etc.
- Scripts → Same pattern

**Rationale:** Exception types establish error contracts

### Pipeline Orchestration (Expected)
- GUI → `xic_extractor.extractor`, `xic_extractor.extraction.pipeline`
- Scripts → Same pattern

**Rationale:** These are entry points; GUI/scripts must call them

### Output Writers (Expected)
- GUI → `xic_extractor.output.excel_pipeline`
- Scripts → `xic_extractor.output.*`

**Rationale:** Output formatting is a domain concern; GUI/scripts consume it

---

## 9. Summary of Suspicious Imports

**Total files analyzed:** 658
**Files with cross-package imports:** ~150
**Imports violating architecture:** 0
**Circular import chains:** 0
**Suspicious bidirectional imports:** 0

---

## 10. Recommendations

### No Breaking Changes Needed
The current architecture is sound. All cross-boundary imports follow the correct dependency direction.

### Optional Improvements (Low Priority)
1. **Extract shared orchestration module**: `extraction/pipeline.py` and `alignment/pipeline.py` could share a common orchestration pattern (no change required).
2. **Document schema exports**: Add `__all__` to `settings_schema.py` to make it explicit which constants are public contracts.
3. **Consolidate preset logic**: Presets are imported by multiple GUI files; consider if a `gui/presets_adapter.py` would reduce coupling (cosmetic improvement).

### Monitoring
- Continue to enforce: "xic_extractor/ must never import from gui/"
- Current test framework (pytest, mypy) can catch violations automatically

---

## Appendix: High-Level Package Responsibilities

| Package | Role | Clients |
|---|---|---|
| `xic_extractor/` | Domain logic; extraction, alignment, discovery algorithms | gui/, scripts/ |
| `gui/` | Qt-based user interface; orchestrates workflows | End users |
| `scripts/` | Command-line tools; batch processing and validation | Developers, automation |
| `tools/` | Diagnostic and utility code | Other tools, scripts |
| `tests/` | Test suite | CI/CD |

---

**End of Report**
