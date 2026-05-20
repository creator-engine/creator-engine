# Completion Report — Class C-merge (Git/GitHub mutation, ended at canonical-branch merge)

**Gate class**: C-merge — ten-field post-merge per `docs/delivery/NEXT_TASK_PROTOCOL.md` §b.
**Controller**: `<controller_id>`
**Lane**: `<lane_id>`
**Envelope**: `<envelope_ref>` (SHA256 `<envelope_sha256>`)
**Outcome**: `completed`
**Opened**: `<gate_opened_at>` · **Closed**: `<gate_closed_at>`

Contract: `docs/operations/COMPLETION_REPORT_PROTOCOL.md` (§d.1, §g — class C-merge).
Cross-reference: `docs/delivery/NEXT_TASK_PROTOCOL.md` §b ten-field rule (canonical).

## Summary

<one to four sentences summarising what merged. The structured
`merge_report` object below encodes the ten §b fields in
machine-readable form; this section does not duplicate them.>

## Recommended immediate next step

- **Description**: <what follows the merge — usually the next ratifiable gate>
- **Rationale**: <why that next gate follows>
- **Next-action kind**: `<source_ratifiable_prompt|backlog_refresh_and_source_escalation|blocker_resolution|no_next_gate>`

## Exact next Source prompt pointer+SHA256

- **Kind**: `<present|none>`
- **Prompt path** (when `present`): `<path>`
- **Prompt SHA256** (when `present`): `<64-lower-hex>`
- **Canonical ratification line** (when `present`): `<the line Source will use>`
- **None rationale** (when `none`): `<one of the canonical absence reasons>`

---

**Merge facts** (encoded in `merge_report` in the YAML sidecar):

- PR `<pr_number>` (`<pr_url_or_identifier>`)
- Merge commit `<merge_commit>` · strategy `<squash|rebase|merge>`
- Head `<head_ref>` @ `<head_sha>` → base `<base_ref>` @ `<base_sha>`
- Merged at `<merged_at>` by role `<architect|implementer|controller|reviewer|source>`
- Validator summary: `<validator_summary_ref>`
