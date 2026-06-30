# Source-Copy Stub Removal Approval Packet

Doc placement: repo_support_doc
Doc kind: approval_packet
Doc lifecycle: active
Repo owner: docs/agent/obsidian-handoff-contract.md
Doc exit rule: Retire after branch or PR closeout records this deletion batch
and no future cleanup reviewer needs the exact approval set.

Status: `deletion_applied`
Validation status: `diagnostic_only`

This packet records the destructive approval and applied deletion batch. It does
not authorize any further `git rm`, archive moves, or same-path stub deletion.

## Decision Boundary

The docs-compression queue is currently closed for these files. Their remaining
question is not "what does this historical body mean?" but "does this same-path
compatibility stub still need to exist in the tracked repo?"

Post-deletion audit evidence:

- `docs_management_audit.py` reports blockers `0` and warnings `0`.
- `docs/superpowers` route candidates: `0`.
- Active docs/referrer follow-up rows in the routing TSV: `0`.
- `source_copy_stub_retained`: `1`.
- `formal_doc_stub_retained`: `0`.
- `exact_referrer_bound_support`: `0`.
- Obsidian vault manifest source count: `115`.

The applied source-copy deletions have live private source-copy notes recorded
through vault manifest `original_repo_path` metadata. The applied formal-doc
stub deletion is different: its durable payload was formalized into a repo
product owner, so no private source copy was required for that path.

## Control-Plane Impact

No productization control-plane update is needed. This deletion changes only the
docs-management retention surface for historical stubs. It does not
change any maturity tier, active lane, product writer authority, output schema,
review/replay behavior, selected area/counting, matrix authority, runtime
behavior, validation acceptance state, or product default.

## Applied Deletion Set

The user approved this exact deletion set on 2026-06-30. These tracked same-path
stubs were removed from the repo; their stable public claims remain in the
listed repo owners and private source copies remain in the Obsidian vault where
applicable.

```text
docs/superpowers/closeouts/2026-06-26_codex-docs-cleanup_branch-closeout-summary.md
docs/superpowers/file-management/docs-cleanup/2026-06-25_codex-docs-cleanup_source-of-truth-queue.md
docs/superpowers/fixtures/diagnostic_ledger_2026_05_28/targeted_gt_alignment_audit_default_5medc_current_8raw_failure_mode_report.md
docs/superpowers/fixtures/diagnostic_ledger_2026_05_28/targeted_gt_alignment_audit_default_5medc_primary_delivery_fix_failure_mode_report.md
docs/superpowers/notes/2026-06-04-targeted-expected-diff-bc1055-closeout.md
docs/superpowers/productization/evidence/2026-06-22_cc-framework-improvements_dna-dr-performance-pass.md
docs/superpowers/notes/2026-06-02-selected-hypothesis-model-selection-characterization-map.md
```

## Deferred Path

Do not include this path in the first deletion batch while this branch or its PR
may still use the plan as a compatibility stub:

```text
docs/superpowers/plans/2026-06-28-family-abstraction-removal.md
```

It can be reconsidered after branch PR closeout covers the implementation
summary and the exact-referrer scan remains clean.

## Classification Inventory

| path_or_family | doc_kind | lifecycle | route | classification | durable_payload | duplicate_or_stale_parts | surviving_repo_owner | support_or_stub_role | obsidian_action | referrer_action | destructive_gate | risk | next_step |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `docs/superpowers/closeouts/2026-06-26_codex-docs-cleanup_branch-closeout-summary.md` | closeout | archived | repo_distilled_plus_obsidian_original | historical_progress | Docs-cleanup branch separated public repo docs from private history. | Long branch diary and command chronology. | `docs/agent/obsidian-handoff-contract.md`; `docs/project-layout.md` | removed same-path source-copy stub | Source note `XIC Docs Cleanup Branch Closeout Source`; manifest `original_repo_path` match. | exact referrers `0` before approval packet | approved and applied | Low if old branch/PR references are no longer needed. | removed |
| `docs/superpowers/file-management/docs-cleanup/2026-06-25_codex-docs-cleanup_source-of-truth-queue.md` | manifest | archived | repo_distilled_plus_obsidian_original | historical_progress | Current docs routing belongs to formal owners and generated manifests. | Old queue body and routing chronology. | `docs/agent/obsidian-handoff-contract.md`; `docs/project-layout.md`; `docs/product/README.md` | removed same-path source-copy stub | Source note `XIC Docs Cleanup Source-Of-Truth Queue Source`; manifest `original_repo_path` match. | exact referrers `0` before approval packet | approved and applied | Low if current manifests remain authoritative. | removed |
| `docs/superpowers/fixtures/diagnostic_ledger_2026_05_28/targeted_gt_alignment_audit_default_5medc_current_8raw_failure_mode_report.md` | validation_fixture_report | archived | repo_distilled_plus_obsidian_original | stale_or_superseded | Historical 5-medC current 8RAW alignment fixture verdict. | Old per-run narrative. | `docs/product/alignment.md`; `docs/diagnostic-ledger.md` | removed same-path source-copy stub | Source note `XIC Targeted GT Alignment 5-medC Current 8RAW Source`; manifest `original_repo_path` match. | exact referrers `0` before approval packet | approved and applied | Low; keep only if historical exact path matters. | removed |
| `docs/superpowers/fixtures/diagnostic_ledger_2026_05_28/targeted_gt_alignment_audit_default_5medc_primary_delivery_fix_failure_mode_report.md` | validation_fixture_report | archived | repo_distilled_plus_obsidian_original | stale_or_superseded | Historical 5-medC primary-delivery-fix alignment fixture verdict. | Old per-run narrative. | `docs/product/alignment.md`; `docs/diagnostic-ledger.md` | removed same-path source-copy stub | Source note `XIC Targeted GT Alignment 5-medC Primary Delivery Fix Source`; manifest `original_repo_path` match. | exact referrers `0` before approval packet | approved and applied | Low; keep only if historical exact path matters. | removed |
| `docs/superpowers/notes/2026-06-04-targeted-expected-diff-bc1055-closeout.md` | validation_closeout | archived | repo_distilled_plus_obsidian_original | historical_progress | Row-specific BC1055/8-oxodG activation lesson and count impact. | Long closeout body and reviewer chronology. | `docs/product/targeted-selection.md`; `docs/lcms-msms-evidence-rules.md` | removed same-path source-copy stub | Source note `XIC Targeted Expected-Diff BC1055 Closeout Source`; manifest `original_repo_path` match. | exact referrers `0` before approval packet | approved and applied | Medium-low because it records a product-ready historical row; owner doc must remain the authority. | removed |
| `docs/superpowers/productization/evidence/2026-06-22_cc-framework-improvements_dna-dr-performance-pass.md` | performance_evidence | archived | repo_distilled_plus_obsidian_original | historical_progress | Exact-output-preserving 8RAW performance lesson for `dna_dr_product_ready`. | Old timing narrative and run detail. | `docs/product/presets.md`; `docs/agent/product-validation-contract.md` | removed same-path source-copy stub | Source note `XIC DNA DR Product Ready Performance Pass Source`; manifest `original_repo_path` match. | exact referrers `0` before approval packet | approved and applied | Medium-low because it is useful performance history but not preset authority. | removed |
| `docs/superpowers/notes/2026-06-02-selected-hypothesis-model-selection-characterization-map.md` | note | archived | repo_product_doc | duplicate_boilerplate | Historical map formalized into peak model-selection product docs. | Notes-path duplicate of formal owner. | `docs/product/peak-model-selection.md`; `docs/lcms-msms-evidence-rules.md` | removed formal-doc compatibility stub | No source copy required; formal owner carries durable rules. | exact referrers `0` before approval packet | approved and applied | Low if historical exact path is no longer needed. | removed |
| `docs/superpowers/plans/2026-06-28-family-abstraction-removal.md` | plan | implemented | repo_distilled_plus_obsidian_original | historical_progress | Family-abstraction-removal implementation summary and product owner pointers. | Original implementation plan body. | `docs/product/discovery.md`; `docs/product/family-hypothesis-boundary.md`; `docs/architecture-contract.md` | same-path source-copy stub | Source note `XIC Family Abstraction Removal Source`; manifest `original_repo_path` match. | exact referrers `0` | explicit approval after branch/PR closeout | Medium while this branch is still active. | defer until PR closeout |

## Deletion Rule

Before any future tracked-file deletion:

1. Rerun docs-management audit and confirm blockers `0`, warnings `0`, and
   route candidates `0`.
2. Confirm the exact path set approved by the user.
3. Use explicit staging for only the approved paths.
4. Do not remove the deferred family-abstraction plan stub until branch/PR
   closeout has replaced its compatibility role.

Verdict: `deletion_applied`.
