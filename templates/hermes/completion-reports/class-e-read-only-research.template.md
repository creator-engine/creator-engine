# Completion Report — Class E (Read-only research gate)

**Gate class**: E — read-only research that consumed a Source-ratified prompt.
**Controller**: `<controller_id>`
**Lane**: `<lane_id>`
**Envelope**: `<envelope_ref>` (SHA256 `<envelope_sha256>`)
**Outcome**: `<completed|partial>`
**Opened**: `<gate_opened_at>` · **Closed**: `<gate_closed_at>`

Contract: `docs/operations/COMPLETION_REPORT_PROTOCOL.md` (§d.1, §g — class E).

## Summary

<one to four sentences summarising the research outputs. Class E
reports MAY set `exact_next_source_prompt.kind == none` when the
research run does not point at a next ratifiable gate.>

## Recommended immediate next step

- **Description**: <what the next action is, or that no next gate follows>
- **Rationale**: <why this action follows the research>
- **Next-action kind**: `<source_ratifiable_prompt|backlog_refresh_and_source_escalation|blocker_resolution|no_next_gate>`

## Exact next Source prompt pointer+SHA256

- **Kind**: `<present|none>`
- **Prompt path** (when `present`): `<path>`
- **Prompt SHA256** (when `present`): `<64-lower-hex>`
- **Canonical ratification line** (when `present`): `<the line Source will use>`
- **None rationale** (when `none`): `<one of the canonical absence reasons>`

---

**Research archive**: `<research_archive_path>`
**Evidence index**: `<evidence_index_path>`
**Evidence artifacts** (at least one required):

- `<evidence_artifact_pointer_1>`
- `<evidence_artifact_pointer_2>`
