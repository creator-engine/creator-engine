---
name: "ce-merge-gate"
description: "Checklist-only merge-gate assertion: confirm independent review, green required checks, and ratification, then STOP. Internal controller ergonomics only. Use when the controller is about to decide whether a PR may merge. This skill never merges and contains no mutating forge command."
argument-hint: "Optional PR number for context"
ce-internal: true
ce-skill-class: "action"
ce-mutating: false
user-invocable: true
disable-model-invocation: true
---

> INTERNAL controller ergonomics. This skill is a **checklist-only thin pointer**
> into the in-tree merge-gate SSOT. It asserts the gates and **stops**. It
> performs **no** merge and embeds **no** mutating forge command. The merge stays
> a separate, explicit, human-ratified act. `disable-model-invocation` is set so
> this gate-touching action is never auto-fired.

## SSOT

- Procedure SSOT (in-tree): `playbooks/controller/briefs/merge-gate.md`
- Doctrine: a dismissed changes-request is **not** an approval
  ([[ce-dismiss-is-not-approve]]); re-sign/merge grants are explicit
  ([[ce-257-resign-merge-grant]]).

## Checklist — assert, then STOP

Confirm all three gates per `playbooks/controller/briefs/merge-gate.md`:

1. **Independent review** — `reviewDecision == APPROVED` on the current head, by a
   non-author seat. A dismissed request does not satisfy this.
2. **Green required checks** — every required check on the current head is
   passing.
3. **Ratification** — the merge is explicitly ratified (standing grant or
   Operator confirmation).

If any gate is missing: **do not merge.** Report which gate failed.

If all three pass: report "gates GREEN — ready for the ratified merge action."
Then **STOP**. The merge itself is a separate explicit step outside this skill.

This skill intentionally contains no merge, approve, or push command. Governance
rides on the `PreToolUse` hook-check seam, never on this skill.
