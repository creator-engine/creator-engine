# Completion Report — Class A (Source-ratified saved prompt execution)

**Gate class**: A — Source-ratified saved prompt execution (universal case)
**Controller**: `<controller_id>`
**Lane**: `<lane_id>`
**Envelope**: `<envelope_ref>` (SHA256 `<envelope_sha256>`)
**Outcome**: `<completed|partial>`
**Opened**: `<gate_opened_at>` · **Closed**: `<gate_closed_at>`

Contract: `docs/operations/COMPLETION_REPORT_PROTOCOL.md` (§d.1, §g — class A).

## Summary

<one to four sentences summarising what the gate did. 1–4096 chars
total in the YAML sidecar `summary` field.>

## Recommended immediate next step

- **Description**: <what the next action is>
- **Rationale**: <why this action follows>
- **Next-action kind**: `<source_ratifiable_prompt|backlog_refresh_and_source_escalation|blocker_resolution|no_next_gate>`

## Exact next Source prompt pointer+SHA256

- **Kind**: `<present|none>`
- **Prompt path** (when `present`): `<path>`
- **Prompt SHA256** (when `present`): `<64-lower-hex>`
- **Canonical ratification line** (when `present`): `<the line Source will use>`
- **None rationale** (when `none`): `<roadmap_milestone_complete|source_paused_program|awaiting_external_dependency|backlog_refresh_required>`

---

**Evidence artifacts** (optional but recommended):

- `<evidence_artifact_pointer_1>`
- `<evidence_artifact_pointer_2>`
