# Product Priority Reset Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce the Phase 1 qualitative selection gate note with exactly one
classification: `GO_FOR_NEXT_NARROW_BEHAVIOR_PR`,
`GO_FOR_NEXT_PRODUCT_DECISION_PR`, `NO_GO_FIX_SELECTION_OR_BOUNDARY_FIRST`, or
`INCONCLUSIVE_NEEDS_NAMED_MINIMAL_EVIDENCE`.

**Architecture:** This is a decision / validation artifact pass, not a behavior
change. It consumes existing validation notes, stable discovery indexes, and
existing diagnostic contracts; it writes one gate note and does not create new
diagnostic infrastructure.

**Tech Stack:** Markdown specs / notes, PowerShell, Python standard library,
existing XIC Extractor validation artifacts.

---

## File Structure

- Read:
  `docs/superpowers/specs/2026-05-28-product-priority-reset-decision-spec.md`
- Read:
  `docs/agent-parameter-settings.md`
- Read:
  `docs/superpowers/notes/2026-05-28-pr70-alignment-matrix-handoff-raw-validation-note.md`
- Read:
  `docs/superpowers/notes/2026-05-24-resolver-default-switch-validation-note.md`
- Read:
  `docs/superpowers/validation/identity_coherence_v04_8raw_acceptance_handoff.md`
- Read:
  `docs/superpowers/notes/2026-05-27-asls-minimal-closeout-note.md`
- Read:
  `tools/diagnostics/INDEX.md`
- Create:
  `docs/superpowers/notes/2026-05-28-qualitative-selection-acceptance-gate-note.md`

Do not modify production code, resolver defaults, baseline behavior, boundary
selection, matrix schema, or diagnostic CLIs in Phase 1.

Use `C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe` for RAW /
alignment commands unless the active worktree has a verified `.venv` junction.
Do not use `Start-Process` for RAW validation.

## Task 1: Preflight Artifact Freshness

**Files:**
- Read:
  `C:\Users\user\Desktop\XIC_Extractor\local_validation_artifacts\discovery\accepted_p8b\8raw\discovery_batch_index.csv`
- Read:
  `C:\Users\user\Desktop\XIC_Extractor\local_validation_artifacts\discovery\accepted_p8b\85raw\discovery_batch_index.csv`

- [ ] **Step 0: Record current diff scope and oracle-note cleanliness**

Run:

```powershell
git status --short
git diff -- docs/superpowers/notes/2026-05-27-asls-minimal-closeout-note.md docs/superpowers/notes/2026-05-28-handoff-productization-phase-closeout.md docs/superpowers/specs/2026-05-24-peak-pipeline-cleanup-roadmap-overview-spec.md
```

Expected: dirty tracked docs are limited to this reset PR's supersession /
backlink wording. If an oracle fact, validation result, row identity, or command
result has been modified outside this plan, stop and list the diff scope instead
of building a gate decision on drifted evidence.

- [ ] **Step 1: Verify 8RAW index count and stale references**

Run:

```powershell
& "C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe" -c "import csv, pathlib, sys; p=pathlib.Path(r'C:\Users\user\Desktop\XIC_Extractor\local_validation_artifacts\discovery\accepted_p8b\8raw\discovery_batch_index.csv'); rows=list(csv.DictReader(p.open(newline='', encoding='utf-8-sig'))); stale=[r for r in rows if '.worktrees' in r.get('candidate_csv','') or '.worktrees' in r.get('review_csv','')]; print(f'8raw rows={len(rows)} stale_refs={len(stale)} path={p}'); sys.exit(1 if len(rows)!=8 or stale else 0)"
```

Expected: `8raw rows=8 stale_refs=0`.

- [ ] **Step 2: Verify 85RAW index count and stale references**

Run:

```powershell
& "C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe" -c "import csv, pathlib, sys; p=pathlib.Path(r'C:\Users\user\Desktop\XIC_Extractor\local_validation_artifacts\discovery\accepted_p8b\85raw\discovery_batch_index.csv'); rows=list(csv.DictReader(p.open(newline='', encoding='utf-8-sig'))); stale=[r for r in rows if '.worktrees' in r.get('candidate_csv','') or '.worktrees' in r.get('review_csv','')]; print(f'85raw rows={len(rows)} stale_refs={len(stale)} path={p}'); sys.exit(1 if len(rows)!=85 or stale else 0)"
```

Expected: `85raw rows=85 stale_refs=0`.

- [ ] **Step 3: Record index hashes**

Run:

```powershell
Get-FileHash "C:\Users\user\Desktop\XIC_Extractor\local_validation_artifacts\discovery\accepted_p8b\8raw\discovery_batch_index.csv" -Algorithm SHA256
Get-FileHash "C:\Users\user\Desktop\XIC_Extractor\local_validation_artifacts\discovery\accepted_p8b\85raw\discovery_batch_index.csv" -Algorithm SHA256
```

Expected: command succeeds. Copy the hashes into the gate note.

## Task 2: Generate 8RAW Row Evidence

**Files:**
- Write:
  `output/product_priority_reset_phase1/alignment_8raw_validation_minimal_superwindow/`
- Write:
  `output/product_priority_reset_phase1/phase1_review_matrix.tsv`

- [ ] **Step 1: Verify Python runtime**

Run:

```powershell
Test-Path "C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe"
& "C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe" -c "import sys; print(sys.executable)"
```

Expected: `True`, then
`C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe`.

- [ ] **Step 2: Run foreground 8RAW validation-minimal alignment**

Run:

```powershell
& "C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe" -m scripts.run_alignment `
  --discovery-batch-index "C:\Users\user\Desktop\XIC_Extractor\local_validation_artifacts\discovery\accepted_p8b\8raw\discovery_batch_index.csv" `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R `
  --dll-dir C:\Xcalibur\system\programs `
  --output-dir output\product_priority_reset_phase1\alignment_8raw_validation_minimal_superwindow `
  --expected-sample-count 8 `
  --output-level validation-minimal `
  --resolver-mode region_first_safe_merge `
  --backfill-scope production-equivalent `
  --audit-evidence-mode none `
  --performance-profile validation-fast `
  --owner-backfill-window-strategy super-window `
  --owner-backfill-superwindow-span-factor 2 `
  --timing-output output\product_priority_reset_phase1\alignment_8raw_validation_minimal_superwindow\timing.json `
  --timing-live-output output\product_priority_reset_phase1\alignment_8raw_validation_minimal_superwindow\timing.live.json
```

Expected: exit code `0`; `alignment_matrix.tsv`, `alignment_review.tsv`, and
`alignment_cells.tsv` exist in the output directory. If this fails, stop and
classify according to the failure; do not run 85RAW.

The command requests `region_first_safe_merge`, but the run metadata is expected
to record production `resolver_mode=local_minimum`. `scripts.run_alignment` keeps
safe-merge out of production matrix metadata by design; treat that metadata as
contract confirmation, not a rerun trigger.

- [ ] **Step 3: Extract per-row decision matrix**

Run:

```powershell
New-Item -ItemType Directory -Force output\product_priority_reset_phase1 | Out-Null
@'
import csv
import pathlib
import sys

out = pathlib.Path("output/product_priority_reset_phase1/alignment_8raw_validation_minimal_superwindow")
cells = list(csv.DictReader((out / "alignment_cells.tsv").open(newline="", encoding="utf-8-sig"), delimiter="\t"))
review = list(csv.DictReader((out / "alignment_review.tsv").open(newline="", encoding="utf-8-sig"), delimiter="\t"))
matrix = list(csv.DictReader((out / "alignment_matrix.tsv").open(newline="", encoding="utf-8-sig"), delimiter="\t"))
index = list(csv.DictReader(pathlib.Path(r"C:\Users\user\Desktop\XIC_Extractor\local_validation_artifacts\discovery\accepted_p8b\8raw\discovery_batch_index.csv").open(newline="", encoding="utf-8-sig")))
targets = list(csv.DictReader(pathlib.Path("config/MixSTDs.csv").open(newline="", encoding="utf-8-sig")))

manifest = [
    ("positive_istd", "BenignfatBC1151_DNA", "d3-5-hmdC", "ICD000285", "ICF000285", "BenignfatBC1151_DNA#5012"),
    ("positive_istd", "BenignfatBC1055_DNA", "d3-5-medC", "ICD000092", "ICF000092", "BenignfatBC1055_DNA#9537"),
    ("positive_istd", "BenignfatBC1055_DNA", "15N5-8-oxodG", "ICD000206", "ICF000206", "BenignfatBC1055_DNA#13111"),
    ("positive_istd", "TumorBC2312_DNA", "d3-N6-medA", "ICD002276", "ICF002276", "TumorBC2312_DNA#21195"),
    ("positive_istd", "NormalBC2263_DNA", "d3-dG-C8-MeIQx", "ICD001456", "ICF001456", "NormalBC2263_DNA#35245"),
    ("prior_blocker", "NormalBC2312_DNA", "15N5-8-oxodG", "", "FAM000538", ""),
    ("prior_warning", "NormalBC2312_DNA", "d3-N6-medA", "", "", ""),
]

review_by_family = {row.get("feature_family_id", ""): row for row in review}
matrix_families = {row.get("feature_family_id", "") for row in matrix}
index_by_sample = {row.get("sample_stem", ""): row for row in index}
target_by_label = {row.get("label", ""): row for row in targets}
rows = []
missing = []

def _float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def _target_seed_ids(sample, label):
    target = target_by_label.get(label)
    index_row = index_by_sample.get(sample)
    if not target or not index_row:
        return [], "missing_target_or_index"
    candidate_path = pathlib.Path(index_row.get("candidate_csv", ""))
    if not candidate_path.exists():
        return [], "missing_candidate_csv"
    mz = _float(target.get("mz"))
    rt_min = _float(target.get("rt_min"))
    rt_max = _float(target.get("rt_max"))
    ppm_tol = _float(target.get("ppm_tol")) or 20.0
    nl_ppm_max = _float(target.get("nl_ppm_max")) or 50.0
    if mz is None or rt_min is None or rt_max is None:
        return [], "invalid_target_contract"
    seed_ids = []
    with candidate_path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            row_mz = _float(row.get("precursor_mz"))
            row_rt = _float(row.get("ms1_apex_rt")) or _float(row.get("best_seed_rt"))
            nl_error = _float(row.get("neutral_loss_mass_error_ppm"))
            if row_mz is None or row_rt is None:
                continue
            mz_ppm = abs(row_mz - mz) / mz * 1_000_000.0
            if mz_ppm <= ppm_tol and rt_min <= row_rt <= rt_max and (nl_error is None or abs(nl_error) <= nl_ppm_max):
                seed_ids.append(row.get("candidate_id", ""))
    return sorted({seed for seed in seed_ids if seed}), ""

for kind, sample, label, decision, family, seed in manifest:
    if kind == "prior_warning":
        target_seed_ids, seed_error = _target_seed_ids(sample, label)
        matched = [
            row
            for row in cells
            if row.get("sample_stem") == sample
            and row.get("source_candidate_id") in target_seed_ids
        ]
    else:
        target_seed_ids, seed_error = [], ""
        matched = [
            row
            for row in cells
            if (not sample or row.get("sample_stem") == sample)
            and (
                (seed and row.get("source_candidate_id") == seed)
                or (family and row.get("feature_family_id") == family)
            )
        ]
    best = matched[0] if matched else {}
    family_id = best.get("feature_family_id") or family
    review_row = review_by_family.get(family_id, {})
    go_blocker = ""
    if kind == "prior_warning":
        if seed_error:
            go_blocker = seed_error
        elif len(matched) != 1:
            go_blocker = f"prior_warning_requires_unique_current_row_key:matched={len(matched)}"
    rows.append(
        {
            "kind": kind,
            "sample": sample,
            "label": label,
            "decision_id": decision,
            "expected_family_or_seed": family or seed,
            "target_derived_seed_ids": ";".join(target_seed_ids),
            "matched_cell_count": str(len(matched)),
            "matched_feature_family_id": family_id,
            "cell_status": best.get("status", ""),
            "apex_rt": best.get("apex_rt", ""),
            "peak_start_rt": best.get("peak_start_rt", ""),
            "peak_end_rt": best.get("peak_end_rt", ""),
            "rt_delta_sec": best.get("rt_delta_sec", ""),
            "source_candidate_id": best.get("source_candidate_id", ""),
            "review_identity_decision": review_row.get("identity_decision", ""),
            "review_include_in_primary_matrix": review_row.get("include_in_primary_matrix", ""),
            "review_reason": review_row.get("reason", "")
            or (
                "Same-surface warning handled by resolver note; no row-addressable key, no broad sample match."
                if kind == "prior_warning"
                else ""
            ),
            "matrix_family_present": str(family_id in matrix_families),
            "target_key_required": str(kind == "prior_warning"),
            "go_blocker": go_blocker,
        }
    )
    if kind != "prior_warning" and not matched:
        missing.append(f"{label} / {sample}")

path = pathlib.Path("output/product_priority_reset_phase1/phase1_review_matrix.tsv")
fields = list(rows[0])
with path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
    writer.writeheader()
    writer.writerows(rows)

print(f"wrote {path} rows={len(rows)} missing_required={len(missing)}")
go_blockers = [row for row in rows if row.get("go_blocker")]
print(f"go_blockers={len(go_blockers)}")
if missing:
    print("missing_required_rows=" + ";".join(missing))
    sys.exit(1)
'@ | Set-Content -Path output\product_priority_reset_phase1\extract_phase1_review_matrix.py -Encoding UTF8
& "C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe" output\product_priority_reset_phase1\extract_phase1_review_matrix.py
```

Expected: `rows=7 missing_required=0`. The `prior_warning` row must never use a
broad sample-only match. It derives candidate seeds from `config/MixSTDs.csv`
(`d3-N6-medA` m/z / RT / NL) and the accepted 8RAW discovery candidates, then
matches the current alignment row by `source_candidate_id`. If it does not match
exactly one current row, the script prints `go_blockers=1` and the final gate
classification cannot be a GO state. The decoy aggregate is not in this TSV; it
is handled by the V0.4 acceptance oracle.

- [ ] **Step 4: If direct row keys are stale, extract the resolved row matrix**

If the first pass exposes duplicate-assigned, stale prior-run family ids, or
target-derived candidates that do not map directly to `alignment_matrix.tsv`,
write a consolidation-aware resolved matrix:

```text
output/product_priority_reset_phase1/phase1_review_matrix_resolved.tsv
```

This file is allowed to use the already-written 8RAW `alignment_cells.tsv`,
`alignment_review.tsv`, and `alignment_matrix.tsv`; it must not rerun RAW
extraction. It is the authoritative blocker-count artifact when present. A row
passes only if the target-derived or fixed-row evidence resolves to a selected
family with `include_in_primary_matrix=TRUE` and a corresponding matrix row.

## Task 3: Assemble Fixed Review Manifest

**Files:**
- Read:
  `docs/superpowers/validation/identity_coherence_v04_8raw_acceptance_handoff.md`
- Create:
  `docs/superpowers/notes/2026-05-28-qualitative-selection-acceptance-gate-note.md`

- [ ] **Step 1: Copy the fixed Phase 1 row manifest**

Create the gate note with a `Fixed Review Manifest` table containing the exact
rows from the decision spec:

- `d3-5-hmdC / BenignfatBC1151_DNA / ICD000285 / ICF000285`
- `d3-5-medC / BenignfatBC1055_DNA / ICD000092 / ICF000092`
- `15N5-8-oxodG / BenignfatBC1055_DNA / ICD000206 / ICF000206`
- `d3-N6-medA / TumorBC2312_DNA / ICD002276 / ICF002276`
- `d3-dG-C8-MeIQx / NormalBC2263_DNA / ICD001456 / ICF001456`
- `identity_decoy_specificity / reviewed manifest hash A08F197E31E5F33C35035AB082488DC9F0B5494075BF6930CF9F4EBA42DE1FC6`
- `15N5-8-oxodG / NormalBC2312_DNA / FAM000538`
- `d3-N6-medA / NormalBC2312_DNA / same-surface evidence-spine warning row`

Expected: no new row is invented outside the decision spec.

- [ ] **Step 2: State decoy limitation honestly**

Add this sentence to the gate note:

```markdown
The reviewed decoy manifest row IDs are not available in the active worktree;
this gate uses the accepted V0.4 aggregate decoy oracle (`3/3 rejected`,
`0 promoted`) and does not invent decoy IDs.
```

Expected: decoy evidence is not overclaimed as row-level evidence.

## Task 4: Classify Existing Oracles

**Files:**
- Read:
  `docs/superpowers/notes/2026-05-28-pr70-alignment-matrix-handoff-raw-validation-note.md`
- Read:
  `docs/superpowers/notes/2026-05-24-resolver-default-switch-validation-note.md`
- Read:
  `docs/superpowers/validation/identity_coherence_v04_8raw_acceptance_handoff.md`
- Read:
  `docs/superpowers/notes/2026-05-27-asls-minimal-closeout-note.md`
- Read:
  `tools/diagnostics/INDEX.md`
- Modify:
  `docs/superpowers/notes/2026-05-28-qualitative-selection-acceptance-gate-note.md`

- [ ] **Step 1: Add oracle status table**

The gate note must classify these oracles:

| Oracle | Required status |
| --- | --- |
| PR70 matrix handoff | 8RAW and 85RAW primary artifacts byte-identical for matrix/review/cells |
| Resolver hotfix | strict ISTD hotfix PASS and `15N5-8-oxodG` boundary restored |
| Identity coherence V0.4 | sidecar parity PASS, 5/5 positive controls PASS, 3/3 decoys rejected |
| `d3-N6-medA` warning | same-surface evidence explains mixed-surface mismatch |
| ASLS area interpretation | area shift alone is not a qualitative blocker when identity/RT/boundary/output are accepted |
| Diagnostic inventory | existing relevant tools considered; no new diagnostic required for this gate |

Expected: each row links to an existing note, not to a new diagnostic.

- [ ] **Step 2: Add 8RAW / 85RAW escalation result**

Use the freshness checks, the new 8RAW per-row matrix, and the existing PR70
validation note:

```markdown
8RAW delivery freshness: <GO/NO_GO/INCONCLUSIVE based on index preflight and run>.
8RAW row evidence: <GO/NO_GO/INCONCLUSIVE based on phase1_review_matrix_resolved.tsv when present; otherwise phase1_review_matrix.tsv>.
GO blocker count: <0 for GO; >0 forces INCONCLUSIVE or NO_GO>.
85RAW status: reused accepted PR70 parity evidence only after 8RAW row evidence is GO; no new 85RAW run required.
```

Expected: if freshness check failed, stop and mark `INCONCLUSIVE` or `NO_GO`
according to the decision spec instead of running 85RAW.
If the accepted 85RAW evidence is stale and a refresh would be decision-changing,
first verify the active worktree `.venv` runner exists and can run the
`--expected-sample-count 85` command shape. If that preflight is missing, do not
launch a known-bad 85RAW run; classify `INCONCLUSIVE` and name the missing
runner preflight as the blocker.

## Task 5: Write Gate Decision

**Files:**
- Modify:
  `docs/superpowers/notes/2026-05-28-qualitative-selection-acceptance-gate-note.md`

- [ ] **Step 1: Apply the decision contract**

Choose exactly one classification and write it as the authoritative
machine-readable field:

```markdown
Final Classification: <GO_FOR_NEXT_NARROW_BEHAVIOR_PR | GO_FOR_NEXT_PRODUCT_DECISION_PR | NO_GO_FIX_SELECTION_OR_BOUNDARY_FIRST | INCONCLUSIVE_NEEDS_NAMED_MINIMAL_EVIDENCE>
```

Expected: the note explains why the other classification states do not apply.
Mentioning the other full status tokens in prose is allowed; only the
`Final Classification:` line is authoritative.

- [ ] **Step 2: If GO, name the next product decision**

If the decision is `GO`, write one recommendation:

```markdown
Recommended next PR target: <ASLS/linear-edge behavior | boundary ownership behavior | CWT productization decision>
Reason: <one paragraph tied to fixed review rows and known quantitative defects>
```

Expected: no broad roadmap, no multiple equal choices, no new scaffold. If a
different target seems necessary, classify the gate as `INCONCLUSIVE` or update
the decision spec before selecting that target.

- [ ] **Step 3: If NO_GO or INCONCLUSIVE, name the blocker list**

If the decision is `NO_GO` or `INCONCLUSIVE`, list each blocker with:

- sample;
- target label or family / decision id;
- m/z or RT / window when available;
- status;
- missing or failing evidence;
- cheapest allowed next action.

Expected: no open-ended "continue investigating" language.

## Task 6: Review And Verify

**Files:**
- Read:
  `docs/superpowers/specs/2026-05-28-product-priority-reset-decision-spec.md`
- Read:
  `docs/superpowers/notes/2026-05-28-qualitative-selection-acceptance-gate-note.md`

- [ ] **Step 1: Run Markdown smoke check**

Run:

```powershell
python -c "from pathlib import Path; paths=[Path('docs/superpowers/specs/2026-05-28-product-priority-reset-decision-spec.md'), Path('docs/superpowers/notes/2026-05-28-qualitative-selection-acceptance-gate-note.md')]; bad=[str(p) for p in paths if sum(1 for line in p.read_text(encoding='utf-8').splitlines() if line.startswith(chr(96)*3)) % 2]; raise SystemExit('Unbalanced markdown fences: '+', '.join(bad) if bad else 0)"
```

Expected: exit code `0`.

- [ ] **Step 2: Run placeholder scan**

Run:

```powershell
Select-String -Path "docs\superpowers\specs\2026-05-28-product-priority-reset-decision-spec.md","docs\superpowers\notes\2026-05-28-qualitative-selection-acceptance-gate-note.md" -Pattern "TBD","TODO","placeholder","sufficient evidence" -CaseSensitive
```

Expected: no matches.

- [ ] **Step 3: Verify gate note contract fields**

Run:

```powershell
@'
from pathlib import Path
import re

p = Path("docs/superpowers/notes/2026-05-28-qualitative-selection-acceptance-gate-note.md")
text = p.read_text(encoding="utf-8")
statuses = [
    "GO_FOR_NEXT_NARROW_BEHAVIOR_PR",
    "GO_FOR_NEXT_PRODUCT_DECISION_PR",
    "NO_GO_FIX_SELECTION_OR_BOUNDARY_FIRST",
    "INCONCLUSIVE_NEEDS_NAMED_MINIMAL_EVIDENCE",
]
found = re.findall(r"(?m)^Final Classification:\s*([A-Z0-9_]+)\s*$", text)
errors = []
if len(found) != 1 or found[0] not in statuses:
    errors.append("invalid_final_classification=" + (";".join(found) if found else "<missing>"))

common_terms = [
    "Fixed Review Manifest",
    "Per-row Decision Matrix",
    "Oracle Status",
    "8RAW",
    "85RAW",
    "GO blocker count",
    "Subagent Review Resolution",
]
errors.extend("missing:" + term for term in common_terms if term not in text)

if found in (["GO_FOR_NEXT_NARROW_BEHAVIOR_PR"], ["GO_FOR_NEXT_PRODUCT_DECISION_PR"]):
    for term in ["GO blocker count: 0", "Recommended next PR target"]:
        if term not in text:
            errors.append("missing_go_term:" + term)
else:
    for term in ["Blocker", "cheapest allowed next action"]:
        if term not in text:
            errors.append("missing_blocker_term:" + term)
    if "Recommended Phase 2 PR target:" in text or "Recommended next PR target:" in text:
        errors.append("unexpected_target_for_non_go")

print("classification_count=" + str(len(found)) + " classifications=" + ";".join(found))
print("errors=" + ";".join(errors))
raise SystemExit(1 if errors else 0)
'@ | & "C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe" -
```

Expected: `classification_count=1` and `errors=`.

- [ ] **Step 4: Subagent implementation review**

Dispatch read-only reviewers against the completed gate note:

- product/strategy: verify the note closes exactly one decision and recommends
  one next product decision only when justified;
- engineering/validation: verify freshness checks, artifact references, and
  escalation rules;
- skeptical/challenge: verify the note does not hide scaffold or push decisions
  into audit.

Expected: blocking findings are fixed before closeout.
Record reviewer roles, blocker findings, and resolution status in a `Subagent
Review Resolution` section of the gate note so this gate remains auditable
outside the chat transcript.

- [ ] **Step 5: User acceptance gate**

Report the gate note classification to the user. Do not start a
behavior-changing Phase 2 PR until the user accepts the classification.
