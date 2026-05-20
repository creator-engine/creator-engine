# Completion Report — Class C-pr-only (Git/GitHub mutation without merge)

**Gate class**: C-pr-only — PR opened / edited / reviewed / closed / reopened, no merge.
**Controller**: `<controller_id>`
**Lane**: `<lane_id>`
**Envelope**: `<envelope_ref>` (SHA256 `<envelope_sha256>`)
**Outcome**: `<completed|partial>`
**Opened**: `<gate_opened_at>` · **Closed**: `<gate_closed_at>`

Contract: `docs/operations/COMPLETION_REPORT_PROTOCOL.md` (§d.1, §g — class C-pr-only).

## Summary

<one to four sentences summarising the PR action.>

## Recommended immediate next step

- **Description**: <what the next action is — often review, follow-up PR edit, or eventual merge gate>
- **Rationale**: <why this action follows>
- **Next-action kind**: `<source_ratifiable_prompt|backlog_refresh_and_source_escalation|blocker_resolution|no_next_gate>`

## Exact next Source prompt pointer+SHA256

- **Kind**: `<present|none>`
- **Prompt path** (when `present`): `<path>`
- **Prompt SHA256** (when `present`): `<64-lower-hex>`
- **Canonical ratification line** (when `present`): `<the line Source will use>`
- **None rationale** (when `none`): `<one of the canonical absence reasons>`

---

**PR facts** (encoded in `pr_identifiers` in the YAML sidecar):

- PR `<pr_number>` (`<pr_url_or_identifier>`)
- Head `<head_ref>` @ `<head_sha>` → base `<base_ref>`
- `pr_action`: `<opened|edited|reviewed|closed|reopened>`
