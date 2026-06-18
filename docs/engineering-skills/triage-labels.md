# Triage Labels

The engineering skills speak in terms of five canonical triage roles. This file
maps those roles to the label strings used in GitHub Issues for this repo.

| Label in mattpocock/skills | Label in this tracker | Meaning |
| --- | --- | --- |
| `needs-triage` | `needs-triage` | Maintainer needs to evaluate this issue |
| `needs-info` | `needs-info` | Waiting on the reporter for more information |
| `ready-for-agent` | `ready-for-agent` | Fully specified and ready for an AFK agent |
| `ready-for-human` | `ready-for-human` | Requires human implementation or judgment |
| `wontfix` | `wontfix` | Will not be actioned |

When a skill mentions a role, use the corresponding label string from this
table. This repo is currently solo-maintained, so these labels are primarily a
lightweight issue-state vocabulary rather than a multi-person handoff system.

These labels should exist in GitHub repository metadata before issue forms or
automation rely on them.
