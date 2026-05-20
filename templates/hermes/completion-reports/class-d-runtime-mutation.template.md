# Completion Report — Class D (Non-Git runtime / config / provider / credential / tooling mutation)

**Gate class**: D — environment, provider account, secret store, MCP config, Hermes profile, tmux session, or external service mutation.
**Controller**: `<controller_id>`
**Lane**: `<lane_id>`
**Envelope**: `<envelope_ref>` (SHA256 `<envelope_sha256>`)
**Outcome**: `<completed|partial>`
**Opened**: `<gate_opened_at>` · **Closed**: `<gate_closed_at>`

Contract: `docs/operations/COMPLETION_REPORT_PROTOCOL.md` (§d.1, §g — class D, §m redaction).

## Summary

<one to four sentences summarising what runtime/config surface was
mutated. Repo validators cannot see this surface; the
`mutation_descriptors` and side-effect pointer below are the only
substrate-visible trace.>

## Recommended immediate next step

- **Description**: <what the next action is>
- **Rationale**: <why this action follows>
- **Next-action kind**: `<source_ratifiable_prompt|backlog_refresh_and_source_escalation|blocker_resolution|no_next_gate>`

## Exact next Source prompt pointer+SHA256

- **Kind**: `<present|none>`
- **Prompt path** (when `present`): `<path>`
- **Prompt SHA256** (when `present`): `<64-lower-hex>`
- **Canonical ratification line** (when `present`): `<the line Source will use>`
- **None rationale** (when `none`): `<one of the canonical absence reasons>`

---

**Side-effect pointer** (one of):

- `side_effect_ledger_ref`: `<repo-relative-path>` (preferred once Feature 005 Slice 4/7 lands)
- OR `interim_side_effect_note_ref` + `interim_side_effect_note_sha256`

**Mutation descriptors** (each entry redacted per §m):

- `target_class`: `<class>`, `target_identifier_redacted`: `<redacted-ref>`, `change_summary`: `<summary>`
