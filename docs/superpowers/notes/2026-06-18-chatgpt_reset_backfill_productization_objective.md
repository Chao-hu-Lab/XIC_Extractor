# Reset the Backfill Productization Objective

The goal is **NOT** to make all 4613 candidate rows writable.

The goal is to mechanically adjudicate all 4613 candidate rows with auditable, non-black-box evidence, and to minimize human judgment by turning unresolved rows into explicit review items.

---

# Mechanical Adjudication Layer

## 1. Candidate Output Requirements

For every candidate row, emit:

- `candidate_value` (if available)
- `decision`
  - `write_ready`
  - `review_ready`
  - `blocked`
  - `rejected`
- `write_authority` (`true` / `false`)
- `evidence_grade`
  - `A`
  - `B`
  - `C`
  - `D`
  - `E`
- `blocker_tokens`
- `next_required_evidence`
- `review_question`
- `artifact_paths`
- `code_hashes`
- `input_hashes`

---

## 2. ProductWriter Authority Rules

Only **ProductWriter** may write matrix cells.

ProductWriter may write only rows satisfying **all** of the following conditions:

- `decision == write_ready`
- `write_authority == true`
- `evidence_grade ∈ {A, B}`
- `expected_diff_status == pass`
- `explanation_only == false`
- Scope approved by `authority_manifest`

---

## 3. Quality Sidecar Restrictions

Quality sidecar tokens must remain **explanation-only**.

They may:

- Create review tasks
- Create evidence collection tasks

They must **never**:

- Activate writes
- Escalate write authority

---

## 4. Backfill Authority Scope

Do **not** broaden current Backfill authority.

Current production authority remains limited to:

- Generated-policy
- `write_ready` rows

Current writable production scope:

- **511 matrix cells**

---

## 5. Negative Evidence as Regression Tests

Treat the following results as **regression tests**, not production approval signals.

The following are **not production-ready**:

- All-stability writer
- Apex-delta clean
- Width-only clean
- Shape-margin clean

Additionally:

- `shape-clean`
- `reintegration-stable`
- `oracle_pass`

do **not** imply writer readiness.

---

## 6. Human Intervention Policy

Human intervention must be:

> Approval of explicit machine-generated candidates.

Human intervention must **not** be:

> Free-form value filling.

Manual overrides:

- Must be stored separately
- Must not become product-rule evidence
- Require later oracle validation before promotion into product evidence

---

# Productization Principle

The system should evolve toward:

```text
candidate
    ↓
mechanical adjudication
    ↓
write_ready / review_ready / blocked / rejected
    ↓
(ProductWriter authority gate)
    ↓
matrix write
```

Rather than:

```text
candidate
    ↓
human fills value
    ↓
matrix write
```

The objective is:

- Maximize machine adjudication
- Minimize human judgment
- Preserve auditability
- Preserve explainability
- Preserve authority boundaries
- Avoid black-box write decisions
