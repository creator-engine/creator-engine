# Completion Report — Class F (Blocked or aborted gate)

**Gate class**: F — gate opened, then blocked or aborted without completing.
**Controller**: `<controller_id>`
**Lane**: `<lane_id>`
**Envelope**: `<envelope_ref>` (SHA256 `<envelope_sha256>`)
**Outcome**: `<blocked|aborted>`
**Opened**: `<gate_opened_at>` · **Closed**: `<gate_closed_at>`

Contract: `docs/operations/COMPLETION_REPORT_PROTOCOL.md` (§d.1, §g — class F).
A blocked gate without a closure report is undefined runtime state; this report
closes the gate explicitly.

## Summary

<one to four sentences summarising what was attempted, where it
stopped, and why.>

## Recommended immediate next step

- **Description**: <usually a narrow blocker-resolution prompt, or backlog refresh>
- **Rationale**: <why this action follows from the blocker>
- **Next-action kind**: `<blocker_resolution|backlog_refresh_and_source_escalation|source_ratifiable_prompt|no_next_gate>`

## Exact next Source prompt pointer+SHA256

- **Kind**: `<present|none>`
- **Prompt path** (when `present`): `<path>`
- **Prompt SHA256** (when `present`): `<64-lower-hex>`
- **Canonical ratification line** (when `present`): `<the line Source will use>`
- **None rationale** (when `none`): `<one of the canonical absence reasons>`

---

**Blocker description**: `<what blocked the gate>`

**Resumption pointer**:

- `kind`: `<present|none>`
- When `present`: `prompt_path` + `prompt_sha256`.
- When `none`: `none_rationale` (free-text up to 2048 chars).

**Partial side effects** (optional; each entry redacted per §m):

- `target_class`: `<class>`, `target_identifier_redacted`: `<redacted-ref>`, `change_summary`: `<summary>`
