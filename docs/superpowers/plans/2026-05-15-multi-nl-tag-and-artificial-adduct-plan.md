# Multi-NL Tag And Artificial Adduct Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add FH-style multi neutral-loss/product-ion tag evidence and artificial adduct annotation without letting extra evidence pollute the primary untargeted matrix.

**Architecture:** Add explicit parser and evidence layers before changing promotion behavior. Discovery emits per-candidate tag evidence, alignment aggregates it at family level, adduct annotation relates co-eluting families, and final matrix identity remains gated by `include_in_primary_matrix`.

**Tech Stack:** Python dataclasses, stdlib `csv`/`json`, existing `xic_extractor.discovery` modules, existing alignment TSV/XLSX writers, diagnostics under `tools/diagnostics/`, `pytest`, 8RAW/85RAW validation scripts.

**Primary spec:** `docs/superpowers/specs/2026-05-15-multi-nl-tag-and-artificial-adduct-contract.md`

**Worktree:** `C:\Users\user\Desktop\XIC_Extractor\.worktrees\algorithm-performance-optimization`

---

## File Map

- Create `xic_extractor/discovery/tag_profiles.py`: parse FH feature-list rows into neutral-loss/product-ion tag profiles and resolve user-selected tags.
- Create `tests/test_discovery_tag_profiles.py`: parser, validation, and selection tests.
- Modify `xic_extractor/discovery/models.py`: add multi-profile settings and tag evidence models while keeping single-profile compatibility.
- Modify `xic_extractor/discovery/ms2_seeds.py`: evaluate MS2 scans against multiple selected profiles and return zero or more seeds.
- Modify `xic_extractor/discovery/grouping.py`: merge compatible seeds while preserving all matched tag evidence.
- Modify `xic_extractor/discovery/csv_writer.py`: add compact tag-evidence columns to candidate/full machine outputs.
- Modify `scripts/run_discovery.py`: add `--feature-list`, `--selected-tags`, `--tag-combine-mode`, and keep legacy `--neutral-loss-*` behavior.
- Create `xic_extractor/alignment/adduct_annotation.py`: parse artificial adduct list and annotate close RT / expected m/z-delta family pairs.
- Create `tests/test_alignment_adduct_annotation.py`: adduct parser, matcher, and representative preference tests.
- Modify `xic_extractor/alignment/matrix_identity.py`: consume adduct annotations only as demotion/annotation inputs when a clear representative winner exists.
- Modify alignment TSV/XLSX writer tests when Review/Audit schemas gain adduct fields: ensure Matrix excludes extra evidence and Review/Audit retain annotations.
- Create `tools/diagnostics/multi_tag_adduct_audit.py`: summarize tag overlap, adduct relationships, and matrix row deltas.
- Create `tests/test_multi_tag_adduct_audit.py`: diagnostic summary contract tests.

## Task 1: FH Tag Profile Parser

**Files:**
- Create: `xic_extractor/discovery/tag_profiles.py`
- Test: `tests/test_discovery_tag_profiles.py`

- [ ] **Step 1: Write parser tests**

Add tests that use a small inline CSV fixture with one `NL: dR`, one `NL: dA`,
and one `PI: dR` row:

```python
from pathlib import Path

import pytest

from xic_extractor.discovery.tag_profiles import (
    FeatureTagProfile,
    load_feature_tag_profiles,
    resolve_selected_tag_profiles,
)


def test_load_feature_tag_profiles_parses_nl_and_pi(tmp_path: Path) -> None:
    csv_path = tmp_path / "Feature_List.csv"
    csv_path.write_text(
        "Tag No.,Tag Category,Tag Parameters (Da or m/z),Mass Tolerance (ppm),"
        "Intensity Cutoff (height),Top N Ion by Intensity (MS2; only for tag category 1-2),"
        "Consecutive Data Points (MS1; only for tag category 3),"
        "Minimum Intensity Ratio (MS1/MS1'; only for tag category 3),"
        "Maximum Intensity Ratio (MS1/MS1'; only for tag category 3),\n"
        "1,1,116.047344,20,10000,0,0,0,0,NL: dR\n"
        "10,1,251.1024,20,10000,0,0,0,0,NL: dA\n"
        "57,2,117.0547,20,10000,0,0,0,0,PI: dR\n",
        encoding="utf-8",
    )

    profiles = load_feature_tag_profiles(csv_path)

    assert profiles[0] == FeatureTagProfile(
        tag_id="1",
        tag_kind="neutral_loss",
        tag_label="NL: dR",
        tag_name="dR",
        parameter_mz_or_da=116.047344,
        mass_tolerance_ppm=20.0,
        intensity_cutoff=10000.0,
    )
    assert profiles[2].tag_kind == "product_ion"
    assert profiles[2].tag_name == "dR"


def test_resolve_selected_tag_profiles_accepts_names_and_labels(tmp_path: Path) -> None:
    csv_path = tmp_path / "Feature_List.csv"
    csv_path.write_text(
        "Tag No.,Tag Category,Tag Parameters (Da or m/z),Mass Tolerance (ppm),"
        "Intensity Cutoff (height),Top N Ion by Intensity (MS2; only for tag category 1-2),"
        "Consecutive Data Points (MS1; only for tag category 3),"
        "Minimum Intensity Ratio (MS1/MS1'; only for tag category 3),"
        "Maximum Intensity Ratio (MS1/MS1'; only for tag category 3),\n"
        "1,1,116.047344,20,10000,0,0,0,0,NL: dR\n"
        "10,1,251.1024,20,10000,0,0,0,0,NL: dA\n",
        encoding="utf-8",
    )
    profiles = load_feature_tag_profiles(csv_path)

    selected = resolve_selected_tag_profiles(profiles, ["dR", "NL: dA"])

    assert [profile.tag_name for profile in selected] == ["dR", "dA"]


def test_load_feature_tag_profiles_rejects_unknown_category(tmp_path: Path) -> None:
    csv_path = tmp_path / "Feature_List.csv"
    csv_path.write_text(
        "Tag No.,Tag Category,Tag Parameters (Da or m/z),Mass Tolerance (ppm),"
        "Intensity Cutoff (height),Top N Ion by Intensity (MS2; only for tag category 1-2),"
        "Consecutive Data Points (MS1; only for tag category 3),"
        "Minimum Intensity Ratio (MS1/MS1'; only for tag category 3),"
        "Maximum Intensity Ratio (MS1/MS1'; only for tag category 3),\n"
        "99,9,123.4,20,10000,0,0,0,0,UNKNOWN\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unsupported Tag Category"):
        load_feature_tag_profiles(csv_path)
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
python -m pytest tests\test_discovery_tag_profiles.py -q
```

Expected: FAIL because `xic_extractor.discovery.tag_profiles` does not exist.

- [ ] **Step 3: Implement parser**

Create `xic_extractor/discovery/tag_profiles.py` with:

```python
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal


TagKind = Literal["neutral_loss", "product_ion"]


@dataclass(frozen=True)
class FeatureTagProfile:
    tag_id: str
    tag_kind: TagKind
    tag_label: str
    tag_name: str
    parameter_mz_or_da: float
    mass_tolerance_ppm: float
    intensity_cutoff: float


def load_feature_tag_profiles(path: Path) -> list[FeatureTagProfile]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    profiles: list[FeatureTagProfile] = []
    for row_number, row in enumerate(rows, start=2):
        category = _required(row, "Tag Category", row_number)
        if category == "1":
            tag_kind: TagKind = "neutral_loss"
        elif category == "2":
            tag_kind = "product_ion"
        else:
            raise ValueError(f"{path}:{row_number}: unsupported Tag Category {category!r}")
        label = _extract_label(row)
        profiles.append(
            FeatureTagProfile(
                tag_id=_required(row, "Tag No.", row_number),
                tag_kind=tag_kind,
                tag_label=label,
                tag_name=_normalize_tag_name(label),
                parameter_mz_or_da=_parse_float(row, "Tag Parameters (Da or m/z)", row_number),
                mass_tolerance_ppm=_parse_float(row, "Mass Tolerance (ppm)", row_number),
                intensity_cutoff=_parse_float(row, "Intensity Cutoff (height)", row_number),
            )
        )
    return profiles


def resolve_selected_tag_profiles(
    profiles: Iterable[FeatureTagProfile],
    selected_tags: Iterable[str],
) -> list[FeatureTagProfile]:
    profile_list = list(profiles)
    selected = [_normalize_selector(value) for value in selected_tags]
    resolved: list[FeatureTagProfile] = []
    for selector in selected:
        matches = [
            profile for profile in profile_list
            if _normalize_selector(profile.tag_name) == selector
            or _normalize_selector(profile.tag_label) == selector
        ]
        if not matches:
            raise ValueError(f"selected tag {selector!r} was not found in feature list")
        resolved.extend(matches)
    return resolved
```

Also implement `_required`, `_parse_float`, `_extract_label`,
`_normalize_tag_name`, and `_normalize_selector` in the same file. `_extract_label`
must read the trailing unlabeled column because FH stores `NL: dR` there.

- [ ] **Step 4: Run parser tests**

Run:

```powershell
python -m pytest tests\test_discovery_tag_profiles.py -q
```

Expected: PASS.

## Task 2: Multi-Profile Discovery Evidence

**Files:**
- Modify: `xic_extractor/discovery/models.py`
- Modify: `xic_extractor/discovery/ms2_seeds.py`
- Modify: `xic_extractor/discovery/grouping.py`
- Test: `tests/test_discovery_ms2_seeds.py`
- Test: `tests/test_discovery_grouping.py`

- [ ] **Step 1: Add failing tests for multiple NL profiles**

Add a test showing one scan can produce tag evidence for `dR` while a different
scan in the same RT/precursor family can add `dA` evidence:

```python
def test_multi_profile_seeds_preserve_all_matched_tag_names() -> None:
    settings = DiscoverySettings(
        neutral_loss_profiles=(
            NeutralLossProfile(tag="dR", neutral_loss_da=116.047344),
            NeutralLossProfile(tag="dA", neutral_loss_da=251.1024),
        )
    )
    seeds = collect_strict_nl_seeds(
        _FakeRaw([scan_for_loss(116.047344), scan_for_loss(251.1024)]),
        raw_file=RAW_FILE,
        settings=settings,
    )

    groups = group_discovery_seeds(seeds, settings=settings)

    assert len(groups) == 1
    assert groups[0].matched_tag_names == ("dR", "dA")
```

If the current test file lacks a scan helper that can express arbitrary neutral
losses, add this file-local helper and use it in the test:

```python
def scan_for_loss(loss_da: float, *, precursor_mz: float = 400.0, rt: float = 5.0) -> Ms2ScanEvent:
    product_mz = precursor_mz - loss_da
    scan_number = int(round(loss_da * 1000))
    return Ms2ScanEvent(
        scan=Ms2Scan(
            scan_number=scan_number,
            rt=rt,
            precursor_mz=precursor_mz,
            masses=np.asarray([product_mz], dtype=float),
            intensities=np.asarray([50000.0], dtype=float),
            base_peak=50000.0,
        ),
        parse_error=None,
        scan_number=scan_number,
    )
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```powershell
python -m pytest tests\test_discovery_ms2_seeds.py tests\test_discovery_grouping.py -q
```

Expected: FAIL because `DiscoverySettings` only carries one
`neutral_loss_profile`.

- [ ] **Step 3: Extend discovery models without breaking legacy callers**

In `xic_extractor/discovery/models.py`, keep `neutral_loss_profile` available
as a compatibility property and add tuple-based multi-profile storage:

```python
@dataclass(frozen=True)
class DiscoverySettings:
    neutral_loss_profile: NeutralLossProfile | None = None
    neutral_loss_profiles: tuple[NeutralLossProfile, ...] = ()
    nl_tolerance_ppm: float = 20.0
    precursor_mz_tolerance_ppm: float = 20.0
    product_mz_tolerance_ppm: float = 20.0
    product_search_ppm: float = 50.0
    nl_min_intensity_ratio: float = 0.01
    seed_rt_gap_min: float = 0.20
    ms1_search_padding_min: float = 0.20

    def __post_init__(self) -> None:
        profiles = self.neutral_loss_profiles
        if self.neutral_loss_profile is not None:
            profiles = (self.neutral_loss_profile,) + profiles
        if not profiles:
            raise ValueError("at least one neutral-loss profile is required")
        object.__setattr__(self, "neutral_loss_profiles", profiles)
        object.__setattr__(self, "neutral_loss_profile", profiles[0])
```

Add immutable tag evidence fields to seed/group/candidate models:

```python
matched_tag_names: tuple[str, ...] = ()
tag_evidence_json: str = "{}"
```

Use deterministic sorted tag names when serializing.

- [ ] **Step 4: Evaluate each MS2 scan against each selected NL profile**

In `xic_extractor/discovery/ms2_seeds.py`, loop over
`settings.neutral_loss_profiles` and append one seed per matching profile. Keep
the existing single-profile behavior identical when only one profile exists.

- [ ] **Step 5: Merge tag evidence in grouping**

In `xic_extractor/discovery/grouping.py`, keep compatibility checks centered on
precursor/product/RT proximity. Do not require identical `neutral_loss_tag` when
multi-profile mode is active and the seeds otherwise represent the same
precursor/RT family. Merge `matched_tag_names` into a sorted tuple.

- [ ] **Step 6: Run discovery tests**

Run:

```powershell
python -m pytest tests\test_discovery_ms2_seeds.py tests\test_discovery_grouping.py tests\test_discovery_feature_family.py -q
```

Expected: PASS.

## Task 3: CLI And Discovery Output Contract

**Files:**
- Modify: `scripts/run_discovery.py`
- Modify: `xic_extractor/discovery/csv_writer.py`
- Test: `tests/test_run_discovery.py`
- Test: `tests/test_discovery_review_csv.py`

- [ ] **Step 1: Add CLI parsing tests**

Add tests that verify:

```python
def test_run_discovery_accepts_feature_list_selected_tags_and_union_mode() -> None:
    args = _parse_args([
        "--raw", "sample.raw",
        "--dll-dir", "C:/Xcalibur/system/programs",
        "--output-dir", "out",
        "--feature-list", "Feature_List.csv",
        "--selected-tags", "dR,dA,dT,dC,dG",
        "--tag-combine-mode", "union",
    ])

    assert args.feature_list == Path("Feature_List.csv")
    assert args.selected_tags == "dR,dA,dT,dC,dG"
    assert args.tag_combine_mode == "union"
```

Also add a negative test for `--tag-combine-mode invalid`.

- [ ] **Step 2: Run CLI tests and verify they fail**

Run:

```powershell
python -m pytest tests\test_run_discovery.py::test_run_discovery_accepts_feature_list_selected_tags_and_union_mode -q
```

Expected: FAIL because the CLI flags do not exist.

- [ ] **Step 3: Add CLI flags**

Add these arguments:

```python
parser.add_argument("--feature-list", type=Path)
parser.add_argument("--selected-tags", help="Comma-separated FH tag names or labels.")
parser.add_argument("--tag-combine-mode", choices=["union", "intersection"], default="union")
```

When `--feature-list` is absent, preserve the current `--neutral-loss-tag` and
`--neutral-loss-da` path exactly.

- [ ] **Step 4: Add output columns**

Add these columns to machine/full discovery outputs:

```text
selected_tag_count
matched_tag_count
matched_tag_names
primary_tag_name
tag_combine_mode
tag_intersection_status
tag_evidence_json
```

Keep `discovery_review.csv` compact. If adding all tag columns makes the review
surface noisy, include only `matched_tag_names`, `matched_tag_count`, and
`tag_intersection_status` in review, while full candidate output carries JSON.

- [ ] **Step 5: Run output contract tests**

Run:

```powershell
python -m pytest tests\test_run_discovery.py tests\test_discovery_review_csv.py -q
```

Expected: PASS.

## Task 4: Artificial Adduct Parser And Matcher

**Files:**
- Create: `xic_extractor/alignment/adduct_annotation.py`
- Test: `tests/test_alignment_adduct_annotation.py`

- [ ] **Step 1: Write adduct parser and matcher tests**

Add:

```python
def test_load_artificial_adducts_parses_fh_list(tmp_path: Path) -> None:
    csv_path = tmp_path / "Artificial_Adduct_List.csv"
    csv_path.write_text(
        "Artificial Adduct No.,Artificial Adduct m/z,Artificial Adduct Name\n"
        "1,21.981945,M+Na-H\n"
        "2,37.955882,M+K-H\n",
        encoding="utf-8",
    )

    adducts = load_artificial_adducts(csv_path)

    assert adducts[0].adduct_id == "1"
    assert adducts[0].mz_delta == 21.981945
    assert adducts[0].adduct_name == "M+Na-H"


def test_match_artificial_adduct_pairs_requires_close_rt_and_delta() -> None:
    families = [
        _family("F001", mz=300.000000, rt=5.000, identity_decision="production_family"),
        _family("F002", mz=321.981945, rt=5.020, identity_decision="provisional_discovery"),
        _family("F003", mz=337.955882, rt=5.300, identity_decision="provisional_discovery"),
    ]
    pairs = match_artificial_adduct_pairs(
        families,
        [ArtificialAdduct(adduct_id="1", mz_delta=21.981945, adduct_name="M+Na-H")],
        rt_window_min=0.05,
        mz_tolerance_ppm=10.0,
    )

    assert [(pair.parent_family_id, pair.related_family_id, pair.adduct_name) for pair in pairs] == [
        ("F001", "F002", "M+Na-H")
    ]
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
python -m pytest tests\test_alignment_adduct_annotation.py -q
```

Expected: FAIL because the module does not exist.

- [ ] **Step 3: Implement parser and pair matcher**

Implement dataclasses:

```python
@dataclass(frozen=True)
class ArtificialAdduct:
    adduct_id: str
    mz_delta: float
    adduct_name: str


@dataclass(frozen=True)
class ArtificialAdductPair:
    parent_family_id: str
    related_family_id: str
    adduct_name: str
    mz_delta_observed: float
    mz_delta_error_ppm: float
    rt_delta_min: float
```

The matcher should use absolute m/z difference and absolute RT difference. It
should not demote or delete rows; it only returns relationship annotations.

- [ ] **Step 4: Run adduct tests**

Run:

```powershell
python -m pytest tests\test_alignment_adduct_annotation.py -q
```

Expected: PASS.

## Task 5: Matrix Identity Integration Without Matrix Inflation

**Files:**
- Modify: `xic_extractor/alignment/matrix_identity.py`
- Modify: alignment TSV/XLSX writer modules that emit Review/Audit fields.
- Test: `tests/test_alignment_matrix_identity.py`
- Test: `tests/test_untargeted_final_matrix_contract.py`
- Test: `tests/test_alignment_tsv_writer.py`
- Test: `tests/test_alignment_xlsx_writer.py`

- [ ] **Step 1: Add contract tests**

Add tests proving:

```python
def test_multi_tag_support_does_not_promote_single_sample_family() -> None:
    row = _identity_row(
        q_detected=1,
        owner_detected_count=1,
        matched_tag_count=3,
        duplicate_assigned_count=0,
    )

    decision = decide_matrix_identity(row)

    assert decision.identity_decision == "provisional_discovery"
    assert decision.include_in_primary_matrix is False


def test_artificial_adduct_loser_stays_out_of_primary_matrix() -> None:
    row = _identity_row(
        q_detected=5,
        owner_detected_count=5,
        artificial_adduct_role="related_loser",
    )

    decision = decide_matrix_identity(row)

    assert decision.identity_decision == "audit_family"
    assert decision.include_in_primary_matrix is False
```

- [ ] **Step 2: Run identity tests and verify they fail**

Run:

```powershell
python -m pytest tests\test_alignment_matrix_identity.py tests\test_untargeted_final_matrix_contract.py -q
```

Expected: FAIL until matrix identity accepts the new evidence fields.

- [ ] **Step 3: Consume multi-tag fields as confidence only**

Keep this invariant:

```python
include_in_primary_matrix = identity_decision == "production_family"
```

Do not let `matched_tag_count > 1` override detected-support, duplicate-pressure,
or backfill/rescue gates.

- [ ] **Step 4: Add adduct relationship fields to Review/Audit**

Add Review/Audit fields:

```text
artificial_adduct_role
artificial_adduct_name
artificial_adduct_related_family_id
artificial_adduct_mz_delta_error_ppm
artificial_adduct_rt_delta_min
```

Primary Matrix TSV/XLSX must not include these fields.

- [ ] **Step 5: Run writer and identity tests**

Run:

```powershell
python -m pytest tests\test_alignment_matrix_identity.py tests\test_untargeted_final_matrix_contract.py tests\test_alignment_tsv_writer.py tests\test_alignment_xlsx_writer.py -q
```

Expected: PASS.

## Task 6: Diagnostic Report Before Real Promotion Changes

**Files:**
- Create: `tools/diagnostics/multi_tag_adduct_audit.py`
- Test: `tests/test_multi_tag_adduct_audit.py`

- [ ] **Step 1: Add diagnostic tests**

Test that the diagnostic consumes:

```text
alignment_review.tsv
alignment_cells.tsv
optional Artificial_Adduct_List.csv
optional baseline alignment_review.tsv
```

and writes:

```text
multi_tag_adduct_summary.tsv
multi_tag_adduct_pairs.tsv
multi_tag_adduct.json
multi_tag_adduct.md
```

The JSON must include:

```json
{
  "selected_tags": ["dR", "dA", "dT", "dC", "dG"],
  "tag_combine_mode": "union",
  "matrix_row_count": 0,
  "review_row_count": 0,
  "tag_overlap": {},
  "artificial_adduct_pair_count": 0,
  "matrix_row_delta_vs_baseline": 0
}
```

- [ ] **Step 2: Run diagnostic tests and verify they fail**

Run:

```powershell
python -m pytest tests\test_multi_tag_adduct_audit.py -q
```

Expected: FAIL because the diagnostic does not exist.

- [ ] **Step 3: Implement diagnostic**

The diagnostic should be read-only. It must not modify alignment outputs. It
should fail clearly if required TSV columns are missing.

- [ ] **Step 4: Run diagnostic tests**

Run:

```powershell
python -m pytest tests\test_multi_tag_adduct_audit.py -q
```

Expected: PASS.

## Task 7: 8RAW Real-Data Validation

**Files:**
- No production file changes expected.
- Output: `output\discovery\multi_tag_8raw_union_20260515`
- Output: `output\alignment\multi_tag_8raw_union_20260515`
- Output: `output\diagnostics\multi_tag_8raw_union_20260515`

- [ ] **Step 1: Run single-tag baseline if no comparable baseline exists**

Run:

```powershell
$env:PYTHONPATH='.'
uv run python scripts\run_discovery.py --raw-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" --dll-dir "C:\Xcalibur\system\programs" --output-dir output\discovery\multi_tag_baseline_8raw_20260515 --neutral-loss-tag DNA_dR --neutral-loss-da 116.0474
```

Expected: `discovery_batch_index.csv` exists.

- [ ] **Step 2: Run multi-tag union discovery**

Run:

```powershell
$env:PYTHONPATH='.'
uv run python scripts\run_discovery.py --raw-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" --dll-dir "C:\Xcalibur\system\programs" --output-dir output\discovery\multi_tag_8raw_union_20260515 --feature-list "C:\Users\user\Desktop\NTU cancer\FeatureHunter_v1.6c\params\Feature_List_urine_Malignancy_R.csv" --selected-tags dR,dA,dT,dC,dG --tag-combine-mode union
```

Expected: discovery outputs contain `matched_tag_names` and
`tag_intersection_status`.

- [ ] **Step 3: Run alignment with existing final matrix identity gates**

Run validation-fast alignment using the multi-tag discovery batch index:

```powershell
$env:PYTHONPATH='.'
uv run python scripts\run_alignment.py --discovery-batch-index output\discovery\multi_tag_8raw_union_20260515\discovery_batch_index.csv --raw-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" --dll-dir "C:\Xcalibur\system\programs" --output-dir output\alignment\multi_tag_8raw_union_20260515 --output-level machine --emit-alignment-cells --performance-profile validation-fast --preconsolidate-owner-families --owner-backfill-min-detected-samples 2 --sample-info "C:\Users\user\Desktop\NTU cancer\Processed Data\DNA\Mzmine\new_test\SampleInfo.xlsx" --targeted-istd-workbook C:\Users\user\Desktop\XIC_Extractor\output\xic_results_20260512_1151.xlsx
```

Expected: `alignment_matrix.tsv`, `alignment_review.tsv`, and
`alignment_cells.tsv` exist.

- [ ] **Step 4: Run multi-tag/adduct diagnostic**

Run:

```powershell
$env:PYTHONPATH='.'
python tools\diagnostics\multi_tag_adduct_audit.py --alignment-dir output\alignment\multi_tag_8raw_union_20260515 --baseline-alignment-dir output\alignment\final_identity_contract_8raw_drift_20260514 --artificial-adduct-list "C:\Users\user\Desktop\NTU cancer\FeatureHunter_v1.6c\params\Artificial_Adduct_List.csv" --output-dir output\diagnostics\multi_tag_8raw_union_20260515\multi_tag_adduct_audit
```

Expected:

- no unexplained Primary Matrix row inflation;
- tag overlap table is populated;
- artificial adduct pairs are annotation-only;
- Review/Audit row count may grow, but Matrix should remain governed by
  `production_family`.

- [ ] **Step 5: Run strict targeted ISTD benchmark**

Run:

```powershell
$env:PYTHONPATH='.'
python tools\diagnostics\targeted_istd_benchmark.py --targeted-workbook C:\Users\user\Desktop\XIC_Extractor\output\xic_results_20260512_1151.xlsx --alignment-dir output\alignment\multi_tag_8raw_union_20260515 --output-dir output\diagnostics\multi_tag_8raw_union_20260515\targeted_istd_benchmark
```

Expected: PASS for the six active DNA ISTDs and no inactive RNA tag primary hit.

## Task 8: 85RAW Validation Gate

**Files:**
- No production file changes expected unless 8RAW reveals a real contract bug.

- [ ] **Step 1: Run 85RAW only after 8RAW passes**

Use the same commands as Task 7, replacing:

```text
validation raw dir -> C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R
targeted workbook -> C:\Users\user\Desktop\XIC_Extractor\output\xic_results_20260512_1200.xlsx
output suffix -> multi_tag_85raw_union_20260515
```

- [ ] **Step 2: Accept or stop**

Accept if:

- targeted ISTD benchmark has no new failures except known targeted-side
  `d3-N6-medA` area mismatch;
- inactive RNA tag has no primary matrix hit in a DNA-only selected-tag run;
- Primary Matrix row count does not inflate without production support;
- adduct annotations explain duplicate-like families without deleting evidence;
- Review/Audit preserve weak and related evidence.

Stop and write a failure report if any criterion fails.

## Self-Review

Spec coverage:

- FH feature-list parser is covered by Task 1.
- selected tags and union/intersection semantics are covered by Tasks 2 and 3.
- artificial adduct parsing and pair annotation are covered by Task 4.
- final matrix identity interaction is covered by Task 5.
- diagnostics and real-data gates are covered by Tasks 6, 7, and 8.

Placeholder scan:

- This plan contains no deferred placeholder markers or unbounded edge-case steps.
- Every implementation task has exact files, test commands, and expected results.

Type consistency:

- `FeatureTagProfile`, `ArtificialAdduct`, and `ArtificialAdductPair` are defined
  before they are used by later tasks.
- `tag_combine_mode`, `matched_tag_names`, and artificial adduct fields match the
  spec names.
