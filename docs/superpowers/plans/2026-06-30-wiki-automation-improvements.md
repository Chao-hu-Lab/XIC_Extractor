# Wiki Automation Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate the three biggest manual bottlenecks in the repo↔Obsidian doc lifecycle: stub generation from blocker TSV, promotion metadata validation, and staging queue triage.

**Architecture:** One new Python script (`generate_stubs.py`) handles stub generation with dry-run support. The `wiki-stage-commit` SKILL.md is enhanced with two new capabilities: a metadata validation gate before promotion, and configurable auto-accept rules based on `doc_class` + confidence. Config for auto-accept goes in `~/.obsidian-wiki/config`.

**Tech Stack:** Python 3.11+, `csv` module, `pathlib`, `pytest`

## Global Constraints

- All Python functions must have type hints
- No mutable default arguments
- Functions < 50 lines; files < 400 lines
- Tests use pytest; run with `uv run pytest --tb=short -q`
- Repo-side metadata uses inline `Marker: value` format (parsed by `marker_value()` in `docs_policy.py`)
- Vault-side metadata uses YAML `---` frontmatter
- Stub body must have ≤ 5 non-empty lines (enforced by `is_stub()` in `docs_policy.py`)
- Valid repo-side placements: `formal_repo_doc`, `repo_subcontract_doc`, `repo_support_doc`, `repo_active_stub`, `branch_closeout_summary`, `repo_stub_plus_obsidian`, `repo_stub_plus_formal_doc`, `private_obsidian_note`, `ignored_artifact`, `throwaway_scratch`
- Valid vault-side lifecycles: `draft`, `reviewed`, `verified`, `disputed`, `archived`
- Valid vault-side tiers: `core`, `supporting`, `peripheral`
- Existing stub format uses inline markers (not YAML frontmatter), see `docs/superpowers/plans/2026-06-28-family-abstraction-removal.md` for reference

---

### Task 1: Link Stub Auto-Generator

**Files:**
- Create: `tools/diagnostics/generate_stubs.py`
- Test: `tests/test_generate_stubs.py`
- Read-only reference: `tools/diagnostics/docs_policy.py` (import `marker_value`, `DOC_KIND_VALUES`, `DOC_PLACEMENT_VALUES`)

**Interfaces:**
- Consumes: Link Stub Blockers TSV at `C:\Vaults\Research Vault\XIC\01 Indexes\Migration Control Tables\XIC Extractor Link Stub Blockers.tsv` (columns: `target_source_path`, `target_note`, `target_doc_class`, `target_line_count`, `reference_type`, `referrer_path`, `referrer_kind`, `referrer_line`, `referrer_text`, `suggested_resolution`, `evidence_terms`, `strong_risk_terms`)
- Consumes: existing target files in repo (to extract current `Doc kind` via `marker_value`)
- Produces: stub `.md` files at each `target_source_path` with proper metadata; stdout report of generated/skipped/errors

- [ ] **Step 1: Write the failing test for TSV parsing**

```python
# tests/test_generate_stubs.py
from __future__ import annotations

from tools.diagnostics.generate_stubs import parse_blocker_tsv, BlockerRow


def test_parse_blocker_tsv_extracts_fields(tmp_path: object) -> None:
    tsv = tmp_path / "blockers.tsv"  # type: ignore[union-attr]
    tsv.write_text(
        '"target_source_path"\t"target_note"\t"target_doc_class"\t"target_line_count"'
        '\t"reference_type"\t"referrer_path"\t"referrer_kind"\t"referrer_line"'
        '\t"referrer_text"\t"suggested_resolution"\t"evidence_terms"\t"strong_risk_terms"\n'
        '"docs/notes/example.md"\t"Example Note.md"\t"development-history"\t"100"'
        '\t"name_title"\t"docs/agent/contract.md"\t"agent_runtime_doc"\t"42"'
        '\t"some text"\t"keep_target_or_leave_stub_first"\t"85RAW"\t""\n',
        encoding="utf-8",
    )
    rows = parse_blocker_tsv(tsv)
    assert len(rows) == 1
    assert rows[0].target_source_path == "docs/notes/example.md"
    assert rows[0].target_note == "Example Note.md"
    assert rows[0].target_doc_class == "development-history"
    assert rows[0].suggested_resolution == "keep_target_or_leave_stub_first"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_generate_stubs.py::test_parse_blocker_tsv_extracts_fields -v`
Expected: FAIL — `ModuleNotFoundError` or `ImportError`

- [ ] **Step 3: Write TSV parser and BlockerRow dataclass**

```python
# tools/diagnostics/generate_stubs.py
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BlockerRow:
    target_source_path: str
    target_note: str
    target_doc_class: str
    target_line_count: int
    reference_type: str
    referrer_path: str
    referrer_kind: str
    referrer_line: int
    referrer_text: str
    suggested_resolution: str
    evidence_terms: str
    strong_risk_terms: str


def parse_blocker_tsv(tsv_path: Path) -> list[BlockerRow]:
    rows: list[BlockerRow] = []
    with open(tsv_path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t", quotechar='"')
        for record in reader:
            rows.append(
                BlockerRow(
                    target_source_path=record["target_source_path"],
                    target_note=record["target_note"],
                    target_doc_class=record["target_doc_class"],
                    target_line_count=int(record["target_line_count"]),
                    reference_type=record["reference_type"],
                    referrer_path=record["referrer_path"],
                    referrer_kind=record["referrer_kind"],
                    referrer_line=int(record["referrer_line"]),
                    referrer_text=record["referrer_text"],
                    suggested_resolution=record["suggested_resolution"],
                    evidence_terms=record.get("evidence_terms", ""),
                    strong_risk_terms=record.get("strong_risk_terms", ""),
                )
            )
    return rows
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_generate_stubs.py::test_parse_blocker_tsv_extracts_fields -v`
Expected: PASS

- [ ] **Step 5: Write failing test for stub content generation**

```python
# tests/test_generate_stubs.py (append)
from tools.diagnostics.generate_stubs import generate_stub_content


def test_generate_stub_content_produces_valid_stub() -> None:
    content = generate_stub_content(
        target_source_path="docs/notes/example.md",
        target_note="Example Note.md",
        doc_kind="note",
        repo_owner="docs/product/discovery.md",
    )
    assert "Doc placement: repo_stub_plus_obsidian" in content
    assert "Doc kind: note" in content
    assert "Doc lifecycle: retired" in content
    assert "Repo owner: docs/product/discovery.md" in content
    assert "Doc exit rule:" in content
    assert "[[Example Note.md]]" in content
    non_marker_lines = [
        line
        for line in content.strip().splitlines()
        if line.strip()
        and not line.startswith("Doc ")
        and not line.startswith("Repo owner:")
    ]
    assert len(non_marker_lines) <= 5
```

- [ ] **Step 6: Run test to verify it fails**

Run: `uv run pytest tests/test_generate_stubs.py::test_generate_stub_content_produces_valid_stub -v`
Expected: FAIL — `ImportError`

- [ ] **Step 7: Implement stub content generation**

```python
# tools/diagnostics/generate_stubs.py (append)

def generate_stub_content(
    target_source_path: str,
    target_note: str,
    doc_kind: str,
    repo_owner: str,
) -> str:
    lines = [
        f"Doc placement: repo_stub_plus_obsidian",
        f"Doc kind: {doc_kind}",
        f"Doc lifecycle: retired",
        f"Repo owner: {repo_owner}",
        (
            f"Doc exit rule: Remove after confirming vault note"
            f" [[{target_note}]] is promoted and no repo referrers"
            f" depend on this path."
        ),
        "",
        "Canonical content migrated to Research Vault.",
        f"See: [[{target_note}]]",
    ]
    return "\n".join(lines) + "\n"
```

- [ ] **Step 8: Run test to verify it passes**

Run: `uv run pytest tests/test_generate_stubs.py::test_generate_stub_content_produces_valid_stub -v`
Expected: PASS

- [ ] **Step 9: Write failing test for kind extraction from existing file**

```python
# tests/test_generate_stubs.py (append)
from tools.diagnostics.generate_stubs import extract_doc_kind


def test_extract_doc_kind_from_existing_content() -> None:
    text = "# Plan\n\nDoc kind: plan\nDoc lifecycle: active\n"
    assert extract_doc_kind(text) == "plan"


def test_extract_doc_kind_defaults_to_note() -> None:
    assert extract_doc_kind("# No metadata here\n") == "note"
```

- [ ] **Step 10: Implement kind extraction**

```python
# tools/diagnostics/generate_stubs.py (append)
from tools.diagnostics.docs_policy import marker_value, DOC_KIND_MARKER


def extract_doc_kind(text: str) -> str:
    kind = marker_value(text, DOC_KIND_MARKER)
    return kind if kind else "note"
```

- [ ] **Step 11: Run tests**

Run: `uv run pytest tests/test_generate_stubs.py -v`
Expected: all PASS

- [ ] **Step 12: Write failing test for repo owner inference**

```python
# tests/test_generate_stubs.py (append)
from tools.diagnostics.generate_stubs import infer_repo_owner


def test_infer_repo_owner_from_existing_content() -> None:
    text = "Repo owner: docs/product/discovery.md\n"
    assert infer_repo_owner(text, "docs/notes/x.md") == "docs/product/discovery.md"


def test_infer_repo_owner_falls_back_to_self() -> None:
    assert infer_repo_owner("# No owner\n", "docs/notes/x.md") == "docs/notes/x.md"
```

- [ ] **Step 13: Implement repo owner inference**

```python
# tools/diagnostics/generate_stubs.py (append)
from tools.diagnostics.docs_policy import DOC_REPO_OWNER_MARKER


def infer_repo_owner(text: str, source_path: str) -> str:
    owner = marker_value(text, DOC_REPO_OWNER_MARKER)
    return owner if owner else source_path
```

- [ ] **Step 14: Run tests**

Run: `uv run pytest tests/test_generate_stubs.py -v`
Expected: all PASS

- [ ] **Step 15: Write failing test for the full generate-stubs pipeline**

```python
# tests/test_generate_stubs.py (append)
from tools.diagnostics.generate_stubs import generate_stubs


def test_generate_stubs_dry_run_does_not_write(tmp_path: object) -> None:
    repo_root = tmp_path / "repo"  # type: ignore[union-attr]
    repo_root.mkdir()
    target = repo_root / "docs" / "notes"
    target.mkdir(parents=True)
    (target / "example.md").write_text(
        "# Example\n\nDoc kind: note\nDoc lifecycle: active\n"
        "Repo owner: docs/product/discovery.md\n",
        encoding="utf-8",
    )
    tsv = tmp_path / "blockers.tsv"  # type: ignore[union-attr]
    tsv.write_text(
        '"target_source_path"\t"target_note"\t"target_doc_class"\t"target_line_count"'
        '\t"reference_type"\t"referrer_path"\t"referrer_kind"\t"referrer_line"'
        '\t"referrer_text"\t"suggested_resolution"\t"evidence_terms"\t"strong_risk_terms"\n'
        '"docs/notes/example.md"\t"Example Note.md"\t"development-history"\t"50"'
        '\t"name_title"\t"docs/agent/c.md"\t"agent_runtime_doc"\t"1"'
        '\t"ref"\t"keep_target_or_leave_stub_first"\t""\t""\n',
        encoding="utf-8",
    )
    result = generate_stubs(tsv, repo_root, dry_run=True)
    assert len(result.planned) == 1
    assert result.planned[0].target_source_path == "docs/notes/example.md"
    original = (target / "example.md").read_text(encoding="utf-8")
    assert "repo_stub_plus_obsidian" not in original


def test_generate_stubs_execute_writes_stub(tmp_path: object) -> None:
    repo_root = tmp_path / "repo"  # type: ignore[union-attr]
    repo_root.mkdir()
    target = repo_root / "docs" / "notes"
    target.mkdir(parents=True)
    (target / "example.md").write_text(
        "# Example\n\nDoc kind: note\nDoc lifecycle: active\n"
        "Repo owner: docs/product/discovery.md\n",
        encoding="utf-8",
    )
    tsv = tmp_path / "blockers.tsv"  # type: ignore[union-attr]
    tsv.write_text(
        '"target_source_path"\t"target_note"\t"target_doc_class"\t"target_line_count"'
        '\t"reference_type"\t"referrer_path"\t"referrer_kind"\t"referrer_line"'
        '\t"referrer_text"\t"suggested_resolution"\t"evidence_terms"\t"strong_risk_terms"\n'
        '"docs/notes/example.md"\t"Example Note.md"\t"development-history"\t"50"'
        '\t"name_title"\t"docs/agent/c.md"\t"agent_runtime_doc"\t"1"'
        '\t"ref"\t"keep_target_or_leave_stub_first"\t""\t""\n',
        encoding="utf-8",
    )
    result = generate_stubs(tsv, repo_root, dry_run=False)
    assert len(result.written) == 1
    stub_text = (target / "example.md").read_text(encoding="utf-8")
    assert "Doc placement: repo_stub_plus_obsidian" in stub_text
    assert "Doc kind: note" in stub_text
    assert "[[Example Note.md]]" in stub_text
```

- [ ] **Step 16: Implement the full pipeline function**

```python
# tools/diagnostics/generate_stubs.py (append)
import argparse
import sys

@dataclass(frozen=True)
class StubPlan:
    target_source_path: str
    target_note: str
    doc_kind: str
    repo_owner: str
    stub_content: str


@dataclass
class GenerateResult:
    planned: list[StubPlan]
    written: list[StubPlan]
    skipped: list[tuple[str, str]]
    errors: list[tuple[str, str]]


def generate_stubs(
    tsv_path: Path,
    repo_root: Path,
    *,
    dry_run: bool = True,
) -> GenerateResult:
    rows = parse_blocker_tsv(tsv_path)
    result = GenerateResult(planned=[], written=[], skipped=[], errors=[])

    for row in rows:
        if row.suggested_resolution != "keep_target_or_leave_stub_first":
            result.skipped.append(
                (row.target_source_path, f"resolution={row.suggested_resolution}")
            )
            continue

        target_file = repo_root / row.target_source_path
        if not target_file.exists():
            result.errors.append(
                (row.target_source_path, "target file does not exist")
            )
            continue

        existing_text = target_file.read_text(encoding="utf-8")

        if "Doc placement: repo_stub_plus_obsidian" in existing_text:
            result.skipped.append(
                (row.target_source_path, "already a stub")
            )
            continue

        doc_kind = extract_doc_kind(existing_text)
        repo_owner = infer_repo_owner(existing_text, row.target_source_path)
        stub_content = generate_stub_content(
            target_source_path=row.target_source_path,
            target_note=row.target_note,
            doc_kind=doc_kind,
            repo_owner=repo_owner,
        )

        plan = StubPlan(
            target_source_path=row.target_source_path,
            target_note=row.target_note,
            doc_kind=doc_kind,
            repo_owner=repo_owner,
            stub_content=stub_content,
        )
        result.planned.append(plan)

        if not dry_run:
            target_file.write_text(stub_content, encoding="utf-8")
            result.written.append(plan)

    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate repo stubs from link stub blockers TSV",
    )
    parser.add_argument("tsv_path", type=Path, help="path to blockers TSV")
    parser.add_argument(
        "--repo-root", type=Path, default=Path("."),
        help="repo root directory (default: cwd)",
    )
    parser.add_argument(
        "--execute", action="store_true",
        help="actually write stubs (default: dry-run only)",
    )
    args = parser.parse_args(argv)
    result = generate_stubs(args.tsv_path, args.repo_root, dry_run=not args.execute)

    for plan in result.planned:
        action = "WRITE" if not args.execute else "WROTE"
        if plan in result.written:
            action = "WROTE"
        print(f"  {action}: {plan.target_source_path} → stub for [[{plan.target_note}]]")

    for path, reason in result.skipped:
        print(f"  SKIP: {path} ({reason})")

    for path, reason in result.errors:
        print(f"  ERROR: {path} ({reason})")

    total = len(result.planned) + len(result.skipped) + len(result.errors)
    print(
        f"\nSummary: {len(result.written)} written,"
        f" {len(result.planned) - len(result.written)} planned,"
        f" {len(result.skipped)} skipped,"
        f" {len(result.errors)} errors"
        f" (of {total} rows)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 17: Run all tests**

Run: `uv run pytest tests/test_generate_stubs.py -v`
Expected: all PASS

- [ ] **Step 18: Run against real TSV in dry-run mode to verify**

Run: `uv run python tools/diagnostics/generate_stubs.py "C:\Vaults\Research Vault\XIC\01 Indexes\Migration Control Tables\XIC Extractor Link Stub Blockers.tsv" --repo-root .`
Expected: prints planned stubs for ~88 rows without writing anything

- [ ] **Step 19: Commit**

```bash
git add tools/diagnostics/generate_stubs.py tests/test_generate_stubs.py
git commit -m "feat: add link stub auto-generator from blocker TSV"
```

---

### Task 2: Promotion Metadata Gate in wiki-stage-commit

**Files:**
- Create: `tools/diagnostics/validate_vault_page.py`
- Test: `tests/test_validate_vault_page.py`
- Modify: `C:\Users\user\.claude\skills\wiki-stage-commit\SKILL.md` (add validation step)

**Interfaces:**
- Consumes: vault page `.md` file path
- Produces: list of validation errors (empty = pass); exit code 0 = pass, 1 = fail
- The `wiki-stage-commit` skill calls this script before accepting any page

- [ ] **Step 1: Write failing test for vault page validation**

```python
# tests/test_validate_vault_page.py
from __future__ import annotations

from tools.diagnostics.validate_vault_page import validate_vault_page


def test_valid_page_passes() -> None:
    text = "\n".join([
        "---",
        "title: Test Page",
        "summary: A test page for validation",
        "lifecycle: draft",
        "tier: supporting",
        "tags: visibility/internal",
        "base_confidence: 0.8",
        "---",
        "",
        "# Test Page",
        "",
        "Content here.",
    ])
    errors = validate_vault_page(text)
    assert errors == []


def test_missing_summary_fails() -> None:
    text = "\n".join([
        "---",
        "title: Test Page",
        "lifecycle: draft",
        "tier: supporting",
        "tags: visibility/internal",
        "---",
        "",
        "Content.",
    ])
    errors = validate_vault_page(text)
    assert any("summary" in e for e in errors)


def test_invalid_lifecycle_fails() -> None:
    text = "\n".join([
        "---",
        "title: Test Page",
        "summary: A test page",
        "lifecycle: active",
        "tier: supporting",
        "tags: visibility/internal",
        "---",
        "",
        "Content.",
    ])
    errors = validate_vault_page(text)
    assert any("lifecycle" in e for e in errors)


def test_missing_visibility_tag_fails() -> None:
    text = "\n".join([
        "---",
        "title: Test Page",
        "summary: A test page",
        "lifecycle: draft",
        "tier: supporting",
        "tags: ml architecture",
        "---",
        "",
        "Content.",
    ])
    errors = validate_vault_page(text)
    assert any("visibility" in e for e in errors)


def test_missing_tier_fails() -> None:
    text = "\n".join([
        "---",
        "title: Test Page",
        "summary: A test page",
        "lifecycle: draft",
        "tags: visibility/internal",
        "---",
        "",
        "Content.",
    ])
    errors = validate_vault_page(text)
    assert any("tier" in e for e in errors)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_validate_vault_page.py -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement vault page validator**

```python
# tools/diagnostics/validate_vault_page.py
from __future__ import annotations

import argparse
import sys
from pathlib import Path

VALID_LIFECYCLES = {"draft", "reviewed", "verified", "disputed", "archived"}
VALID_TIERS = {"core", "supporting", "peripheral"}


def _frontmatter(text: str) -> dict[str, str]:
    """Parse YAML frontmatter between --- delimiters."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    values: dict[str, str] = {}
    current_key: str | None = None
    for line in text[3:end].splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if line.startswith((" ", "\t")) or stripped.startswith("- "):
            if current_key and stripped.startswith("- "):
                item = stripped[2:].strip().strip('"').strip("'")
                values[current_key] = " ".join(
                    part for part in (values.get(current_key, ""), item) if part
                )
            continue
        if ":" not in line:
            current_key = None
            continue
        key, value = line.split(":", 1)
        current_key = key.strip()
        values[current_key] = value.strip().strip('"').strip("'")
    return values


def validate_vault_page(text: str) -> list[str]:
    """Return a list of validation errors. Empty list means valid."""
    fm = _frontmatter(text)
    errors: list[str] = []

    if not fm:
        errors.append("missing YAML frontmatter (no --- delimiters)")
        return errors

    summary = fm.get("summary", "").strip()
    if not summary:
        errors.append("missing required field: summary")

    lifecycle = fm.get("lifecycle", "").strip()
    if not lifecycle:
        errors.append("missing required field: lifecycle")
    elif lifecycle not in VALID_LIFECYCLES:
        errors.append(
            f"invalid lifecycle '{lifecycle}'"
            f" — valid: {', '.join(sorted(VALID_LIFECYCLES))}"
        )

    tier = fm.get("tier", "").strip()
    if not tier:
        errors.append("missing required field: tier")
    elif tier not in VALID_TIERS:
        errors.append(
            f"invalid tier '{tier}'"
            f" — valid: {', '.join(sorted(VALID_TIERS))}"
        )

    tags = fm.get("tags", "")
    if "visibility/" not in tags:
        errors.append(
            "missing visibility tag — tags must include a visibility/ prefix"
            " (e.g., visibility/internal, visibility/public)"
        )

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate vault page metadata before promotion",
    )
    parser.add_argument("page_path", type=Path, help="path to vault page .md file")
    args = parser.parse_args(argv)

    text = args.page_path.read_text(encoding="utf-8")
    errors = validate_vault_page(text)

    if errors:
        print(f"BLOCKED — {len(errors)} validation error(s):")
        for err in errors:
            print(f"  • {err}")
        return 1

    print("PASS — page metadata is valid for promotion")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_validate_vault_page.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add tools/diagnostics/validate_vault_page.py tests/test_validate_vault_page.py
git commit -m "feat: add vault page metadata validator for promotion gate"
```

- [ ] **Step 6: Modify wiki-stage-commit SKILL.md to add metadata gate**

Edit `C:\Users\user\.claude\skills\wiki-stage-commit\SKILL.md`. Insert a new **Step 2.5: Metadata Validation Gate** between current Step 2 (Per-File Review) and Step 3 (Apply Decisions).

Add this section after Step 2 and before Step 3:

```markdown
## Step 2.5: Metadata Validation Gate (before accepting)

Before accepting any staged page (new or patch), validate its metadata by running:

```
uv run python tools/diagnostics/validate_vault_page.py <staged_file_path>
```

**If the validator returns errors:**

1. Display the errors to the user:
   ```
   ⛔ Cannot accept — metadata validation failed:
     • missing required field: summary
     • missing visibility tag — tags must include a visibility/ prefix
   ```
2. Offer options:
   - **Fix [f]**: Edit the staged file to add missing metadata, then re-validate
   - **Skip [s]**: Leave in staging for later
   - **Reject [r]**: Move to _raw/ as usual

3. Do NOT allow accepting a page that fails validation. This gate is mandatory.

**If the validator returns PASS:** proceed with the accept action from Step 3.

**For `--all` mode:** Run validation on every file. Auto-accept only those that pass. Print a summary of blocked files at the end:
```
Auto-accept blocked by validation:
  _staging/concepts/foo.md — missing summary, missing tier
  _staging/entities/bar.md — invalid lifecycle 'active'

Accepted: 12 | Blocked: 2 | Total: 14
```
```

- [ ] **Step 7: Verify the skill modification**

Read back `C:\Users\user\.claude\skills\wiki-stage-commit\SKILL.md` and confirm:
1. Step 2.5 exists between Step 2 and Step 3
2. The `uv run python` command path is correct
3. The `--all` mode behavior is documented
4. Original steps are unchanged

- [ ] **Step 8: Commit**

```bash
git add -f "C:\Users\user\.claude\skills\wiki-stage-commit\SKILL.md"
```

Note: The skill file is outside the repo. If it's not tracked by git, just note the modification was made. Do not force-add files outside the repo root.

---

### Task 3: Auto-Accept Policy for Staging Queue

**Files:**
- Create: `tools/diagnostics/auto_accept_policy.py`
- Test: `tests/test_auto_accept_policy.py`
- Modify: `C:\Users\user\.claude\skills\wiki-stage-commit\SKILL.md` (add auto-accept logic)
- Modify: `C:\Users\user\.obsidian-wiki\config` (add config keys)

**Interfaces:**
- Consumes: vault page `.md` frontmatter (fields: `doc_class` or staging subdirectory, `base_confidence`), config from `~/.obsidian-wiki/config`
- Produces: `AutoAcceptDecision` — `auto_accept`, `manual_review`, or `always_manual` with reason string

- [ ] **Step 1: Write failing test for config parsing**

```python
# tests/test_auto_accept_policy.py
from __future__ import annotations

from tools.diagnostics.auto_accept_policy import parse_auto_accept_config


def test_parse_config_extracts_classes_and_threshold(tmp_path: object) -> None:
    config = tmp_path / "config"  # type: ignore[union-attr]
    config.write_text(
        'OBSIDIAN_VAULT_PATH="C:\\Vaults\\Research Vault"\n'
        "WIKI_STAGED_WRITES=true\n"
        "WIKI_AUTO_ACCEPT_CLASSES=development-history,command-narratives,branch-diaries\n"
        "WIKI_AUTO_ACCEPT_MIN_CONFIDENCE=0.8\n",
        encoding="utf-8",
    )
    classes, threshold = parse_auto_accept_config(config)
    assert classes == {"development-history", "command-narratives", "branch-diaries"}
    assert threshold == 0.8


def test_parse_config_defaults_when_missing(tmp_path: object) -> None:
    config = tmp_path / "config"  # type: ignore[union-attr]
    config.write_text(
        'OBSIDIAN_VAULT_PATH="C:\\Vaults\\Research Vault"\n'
        "WIKI_STAGED_WRITES=true\n",
        encoding="utf-8",
    )
    classes, threshold = parse_auto_accept_config(config)
    assert classes == set()
    assert threshold == 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_auto_accept_policy.py::test_parse_config_extracts_classes_and_threshold -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement config parser**

```python
# tools/diagnostics/auto_accept_policy.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


def parse_auto_accept_config(
    config_path: Path,
) -> tuple[set[str], float]:
    """Parse auto-accept settings from wiki config file.

    Returns (auto_accept_classes, min_confidence_threshold).
    """
    values: dict[str, str] = {}
    for line in config_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"')

    raw_classes = values.get("WIKI_AUTO_ACCEPT_CLASSES", "")
    classes = {c.strip() for c in raw_classes.split(",") if c.strip()}

    try:
        threshold = float(values.get("WIKI_AUTO_ACCEPT_MIN_CONFIDENCE", "1.0"))
    except ValueError:
        threshold = 1.0

    return classes, threshold
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_auto_accept_policy.py -v`
Expected: PASS

- [ ] **Step 5: Write failing test for auto-accept decision logic**

```python
# tests/test_auto_accept_policy.py (append)
from tools.diagnostics.auto_accept_policy import (
    decide_auto_accept,
    AutoAcceptDecision,
)


def test_matching_class_and_confidence_auto_accepts() -> None:
    decision = decide_auto_accept(
        doc_class="development-history",
        base_confidence=0.85,
        staging_subdir="ready",
        auto_accept_classes={"development-history", "command-narratives"},
        min_confidence=0.8,
    )
    assert decision.action == "auto_accept"


def test_low_confidence_requires_manual() -> None:
    decision = decide_auto_accept(
        doc_class="development-history",
        base_confidence=0.5,
        staging_subdir="ready",
        auto_accept_classes={"development-history"},
        min_confidence=0.8,
    )
    assert decision.action == "manual_review"
    assert "confidence" in decision.reason


def test_needs_merge_subdir_always_manual() -> None:
    decision = decide_auto_accept(
        doc_class="development-history",
        base_confidence=0.95,
        staging_subdir="needs-merge",
        auto_accept_classes={"development-history"},
        min_confidence=0.8,
    )
    assert decision.action == "always_manual"
    assert "needs-merge" in decision.reason


def test_unrecognized_class_requires_manual() -> None:
    decision = decide_auto_accept(
        doc_class="research",
        base_confidence=0.9,
        staging_subdir="ready",
        auto_accept_classes={"development-history"},
        min_confidence=0.8,
    )
    assert decision.action == "manual_review"
    assert "class" in decision.reason


def test_empty_config_never_auto_accepts() -> None:
    decision = decide_auto_accept(
        doc_class="development-history",
        base_confidence=0.99,
        staging_subdir="ready",
        auto_accept_classes=set(),
        min_confidence=1.0,
    )
    assert decision.action == "manual_review"
```

- [ ] **Step 6: Implement decision logic**

```python
# tools/diagnostics/auto_accept_policy.py (append)

ALWAYS_MANUAL_SUBDIRS = {"needs-merge", "needs-split", "needs-review"}


@dataclass(frozen=True)
class AutoAcceptDecision:
    action: str  # "auto_accept" | "manual_review" | "always_manual"
    reason: str


def decide_auto_accept(
    doc_class: str,
    base_confidence: float,
    staging_subdir: str,
    auto_accept_classes: set[str],
    min_confidence: float,
) -> AutoAcceptDecision:
    if staging_subdir in ALWAYS_MANUAL_SUBDIRS:
        return AutoAcceptDecision(
            action="always_manual",
            reason=f"staging subdir '{staging_subdir}' requires manual review",
        )

    if not auto_accept_classes:
        return AutoAcceptDecision(
            action="manual_review",
            reason="no auto-accept classes configured",
        )

    if doc_class not in auto_accept_classes:
        return AutoAcceptDecision(
            action="manual_review",
            reason=f"doc class '{doc_class}' not in auto-accept list",
        )

    if base_confidence < min_confidence:
        return AutoAcceptDecision(
            action="manual_review",
            reason=(
                f"confidence {base_confidence:.2f} below"
                f" threshold {min_confidence:.2f}"
            ),
        )

    return AutoAcceptDecision(
        action="auto_accept",
        reason=(
            f"class '{doc_class}' in auto-accept list"
            f" and confidence {base_confidence:.2f} >= {min_confidence:.2f}"
        ),
    )
```

- [ ] **Step 7: Run all tests**

Run: `uv run pytest tests/test_auto_accept_policy.py -v`
Expected: all PASS

- [ ] **Step 8: Write failing test for extracting doc_class and confidence from page text**

```python
# tests/test_auto_accept_policy.py (append)
from tools.diagnostics.auto_accept_policy import extract_page_metadata


def test_extract_metadata_from_frontmatter() -> None:
    text = "\n".join([
        "---",
        "title: Test Page",
        "summary: test",
        "lifecycle: draft",
        "tier: supporting",
        "tags: visibility/internal",
        "base_confidence: 0.85",
        "doc_class: development-history",
        "---",
        "",
        "Content.",
    ])
    doc_class, confidence = extract_page_metadata(text)
    assert doc_class == "development-history"
    assert confidence == 0.85


def test_extract_metadata_defaults() -> None:
    text = "\n".join([
        "---",
        "title: Test Page",
        "summary: test",
        "---",
        "",
        "Content.",
    ])
    doc_class, confidence = extract_page_metadata(text)
    assert doc_class == ""
    assert confidence == 0.0
```

- [ ] **Step 9: Implement metadata extraction**

```python
# tools/diagnostics/auto_accept_policy.py (append)

def _frontmatter(text: str) -> dict[str, str]:
    """Parse YAML frontmatter between --- delimiters."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    values: dict[str, str] = {}
    current_key: str | None = None
    for line in text[3:end].splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if line.startswith((" ", "\t")) or stripped.startswith("- "):
            if current_key and stripped.startswith("- "):
                item = stripped[2:].strip().strip('"').strip("'")
                values[current_key] = " ".join(
                    part for part in (values.get(current_key, ""), item) if part
                )
            continue
        if ":" not in line:
            current_key = None
            continue
        key, value = line.split(":", 1)
        current_key = key.strip()
        values[current_key] = value.strip().strip('"').strip("'")
    return values


def extract_page_metadata(text: str) -> tuple[str, float]:
    """Extract doc_class and base_confidence from vault page frontmatter."""
    fm = _frontmatter(text)
    doc_class = fm.get("doc_class", "")
    try:
        confidence = float(fm.get("base_confidence", "0.0"))
    except ValueError:
        confidence = 0.0
    return doc_class, confidence
```

- [ ] **Step 10: Run all tests**

Run: `uv run pytest tests/test_auto_accept_policy.py -v`
Expected: all PASS

- [ ] **Step 11: Commit Python code**

```bash
git add tools/diagnostics/auto_accept_policy.py tests/test_auto_accept_policy.py
git commit -m "feat: add auto-accept policy engine for staged wiki pages"
```

- [ ] **Step 12: Add auto-accept config keys to wiki config**

Append to `C:\Users\user\.obsidian-wiki\config`:

```
WIKI_AUTO_ACCEPT_CLASSES=development-history,command-narratives,branch-diaries
WIKI_AUTO_ACCEPT_MIN_CONFIDENCE=0.8
```

- [ ] **Step 13: Modify wiki-stage-commit SKILL.md to add auto-accept logic**

Edit `C:\Users\user\.claude\skills\wiki-stage-commit\SKILL.md`. Add a new **Step 1.5: Auto-Accept Triage** between Step 1 (Inventory) and Step 2 (Per-File Review).

Add this section:

```markdown
## Step 1.5: Auto-Accept Triage

After inventorying staged files, check for auto-accept eligibility using the policy engine:

1. Read the wiki config file (`~/.obsidian-wiki/config`) for these keys:
   - `WIKI_AUTO_ACCEPT_CLASSES` — comma-separated list of doc classes eligible for auto-accept
   - `WIKI_AUTO_ACCEPT_MIN_CONFIDENCE` — minimum `base_confidence` threshold (default: 1.0 = never auto-accept)

2. If neither key is set, skip this step entirely (all files go to manual review).

3. For each staged file, run:
   ```
   uv run python -c "
   from tools.diagnostics.auto_accept_policy import parse_auto_accept_config, decide_auto_accept, extract_page_metadata
   from pathlib import Path
   text = Path('<staged_file>').read_text(encoding='utf-8')
   doc_class, confidence = extract_page_metadata(text)
   classes, threshold = parse_auto_accept_config(Path.home() / '.obsidian-wiki' / 'config')
   decision = decide_auto_accept(doc_class, confidence, '<staging_subdir>', classes, threshold)
   print(f'{decision.action}|{decision.reason}')
   "
   ```

4. **Partition the inventory into three buckets:**
   - 🟢 **Auto-accept** — passes both class and confidence check, not in `needs-*` subdir
   - 🟡 **Manual review** — doesn't match auto-accept criteria
   - 🔴 **Always manual** — in `needs-merge`/`needs-split`/`needs-review` subdir

5. Display the triage summary:
   ```
   Auto-accept triage:
   🟢 Auto-accept (5):
     _staging/concepts/feature-discovery-v2.md  (development-history, confidence=0.92)
     _staging/concepts/alignment-gate.md        (development-history, confidence=0.88)
     ...

   🟡 Manual review (3):
     _staging/references/backfill-paper.md      (research, confidence=0.75 — class not in auto-accept list)
     ...

   🔴 Always manual (1):
     _staging/needs-merge/duplicate-pages.md    (needs-merge subdir)

   Proceed with auto-accepting 5 files? [y/n]
   ```

6. If the user confirms, run metadata validation (Step 2.5) on each auto-accept candidate. Only actually accept those that pass validation. Then proceed to Step 2 for the remaining manual-review files.

7. For `--all` mode: auto-accept triage still runs, but auto-accepted files skip the per-file prompt. Files in `needs-*` subdirs are still shown for manual review even with `--all`.
```

- [ ] **Step 14: Verify the complete skill**

Read back `C:\Users\user\.claude\skills\wiki-stage-commit\SKILL.md` and confirm:
1. Step 1.5 (auto-accept triage) exists between Step 1 and Step 2
2. Step 2.5 (metadata validation gate) exists between Step 2 and Step 3
3. Auto-accept feeds into metadata validation before actual promotion
4. `needs-*` subdirs are always manual
5. `--all` respects auto-accept triage
6. Original steps 1, 2, 3, 4, 5 are intact

- [ ] **Step 15: Run full test suite to verify nothing broken**

Run: `uv run pytest --tb=short -q`
Expected: all existing tests + new tests pass

- [ ] **Step 16: Commit skill modifications (note in commit message)**

```bash
git commit --allow-empty -m "docs: wiki-stage-commit skill enhanced with metadata gate and auto-accept policy

Modified C:\Users\user\.claude\skills\wiki-stage-commit\SKILL.md (outside repo):
- Added Step 1.5: Auto-accept triage based on doc_class + confidence
- Added Step 2.5: Mandatory metadata validation gate before promotion
- Auto-accept config in ~/.obsidian-wiki/config:
  WIKI_AUTO_ACCEPT_CLASSES and WIKI_AUTO_ACCEPT_MIN_CONFIDENCE"
```
