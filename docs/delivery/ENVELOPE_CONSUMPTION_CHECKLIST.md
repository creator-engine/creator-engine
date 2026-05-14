# Envelope Consumption Checklist (Consumer-Side)

**Status**: Slice E authored draft. This is the **consumer-side**
checklist run before, during, and after consuming a Source-ratified
Assignment Envelope under
[`./ASSIGNMENT_ENVELOPE_TEMPLATE.md`](./ASSIGNMENT_ENVELOPE_TEMPLATE.md)
and inside an isolated worktree governed by
[`./WORKTREE_RUNTIME_PROTOCOL.md`](./WORKTREE_RUNTIME_PROTOCOL.md).

Part of the **minimum repo-native delivery control plane** and
**not a Jira clone**. Layered onto, and subordinate to, the Feature
001 substrate and the Feature 002 operating model. A fresh clone is
sufficient to apply this checklist; no external tracker credential
or network state is required.

## a. Purpose

The consumer-side checklist makes one operational fact answerable
from a fresh clone:

> Before, during, and after authoring inside an isolated worktree,
> what concrete checks has the visible consumer performed against
> the envelope, the worktree, and the source-of-truth contracts?

The checklist is conservative by design and is itself **verification
evidence**, never Source ratification per
[`./REVIEW_GATE.md`](./REVIEW_GATE.md) §m.1.

## b. Source-of-truth relationship

| Upstream source of truth | Role |
|---|---|
| [`./ASSIGNMENT_ENVELOPE_TEMPLATE.md`](./ASSIGNMENT_ENVELOPE_TEMPLATE.md) | The envelope this checklist is run against. |
| [`./WORKTREE_RUNTIME_PROTOCOL.md`](./WORKTREE_RUNTIME_PROTOCOL.md) | Worktree / branch / preflight rules the consumer obeys. |
| [`./SCOPE_AUDIT_CHECKLIST.md`](./SCOPE_AUDIT_CHECKLIST.md) | The verifier-side counterpart used after this checklist completes. |
| [`./DEFINITION_OF_READY.md`](./DEFINITION_OF_READY.md) §b, §c | Ready criteria; privileged-class rule. |
| [`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §b | Done criteria the consumer's evidence ultimately feeds. |
| [`./REVIEWER_IDENTITY_REQUIREMENTS.md`](./REVIEWER_IDENTITY_REQUIREMENTS.md) | Reviewer identity pattern; named-waiver shape. |
| Feature 001 FR-007 / FR-008 | Author/approver separation; privileged-class enumeration. |
| Feature 002 FR-008 | Hermes-authored envelope is the only authorized entry point. |

## c. Before reading the envelope

The consumer performs these checks before opening the envelope body:

1. Confirm the worktree directory is the one named in the envelope's
   `local_worktree_path` shape. Halt if not.
2. Confirm the branch reported by `git branch --show-current` is
   exactly the envelope's `local_branch`. Halt if not.
3. Confirm `git log -1 --oneline` matches the envelope's
   `base_commit` (or an envelope-authorized parent thereof). Halt if
   not.
4. Confirm `git status --short --branch --untracked-files=all` shows
   only the envelope-author's expected starting state. Halt if the
   working tree is unexpectedly dirty.
5. Confirm `git worktree list` shows no unexpected worktrees on the
   envelope's branch. Halt if it does.
6. Confirm one-driver-per-worktree per
   [`./WORKTREE_RUNTIME_PROTOCOL.md`](./WORKTREE_RUNTIME_PROTOCOL.md)
   §d. If multiple drivers may be active in this worktree, halt and
   escalate.
7. Confirm that no `stash@{0}` (or other unrelated stash entries)
   will be applied, dropped, or inspected; treat unknown stash
   entries as out of scope per §f.

## d. Before editing any file

After preflight, before any mutation, the consumer:

1. **Restates the allowed paths.** Reads the envelope's
   `allowed_create_paths` and `allowed_update_paths` and writes them
   down or quotes them. Edits outside the union of these sets are
   refused.
2. **Restates the prohibited surfaces.** Reads the envelope's
   prohibited-surfaces list (including the standing list in
   [`./ASSIGNMENT_ENVELOPE_TEMPLATE.md`](./ASSIGNMENT_ENVELOPE_TEMPLATE.md)
   §c.6). Mutations to any of these surfaces are refused even if
   they appear mechanically convenient.
3. **Verifies Source ratification exists for the envelope.**
   Confirms the envelope's `ratifier`, `ratification_record_ref`, and
   `ratification_scope` fields are populated. An envelope with empty
   ratification fields is not consumable; the consumer halts and
   escalates per §g.
4. **Verifies reviewer-identity requirements or named waiver.** If
   the batch is reviewable, confirms the envelope cites either a
   ratified reviewer identity record per
   [`./REVIEWER_IDENTITY_REQUIREMENTS.md`](./REVIEWER_IDENTITY_REQUIREMENTS.md)
   or a Source-ratified named waiver under the envelope's
   `waivers_named` field. Silence is not a waiver.
5. **Confirms allowed operations.** Reads the envelope's
   `allowed_operations`; operations beyond this set (delete, rename,
   chmod, mv, force-push, hook bypass) are refused.
6. **Confirms no scope broadening.** If completing the batch
   apparently requires a mutation outside the allowed set, the
   consumer does NOT broaden scope implicitly; the consumer halts
   and escalates per §g.

## e. During authoring

While editing files inside the worktree, the consumer:

1. Edits **only** the paths in `allowed_create_paths` and
   `allowed_update_paths`. A grep / diff sanity check against the
   working tree at every save catches drift early.
2. Uses careful wording for in-flight work. Where a batch lives on a
   branch that has not yet merged, the consumer writes "this Slice
   <id> batch authors..." rather than declaring canonical Done
   prematurely (mirrors
   [`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §b.7).
3. Updates only the **minimum coherence updates** that the envelope
   names. Discoverability fixes, cross-reference repairs, and
   stale-language scans are in scope only where the envelope names
   them.
4. Avoids introducing **instance-local facts**: absolute filesystem
   paths beyond the envelope's `local_worktree_path`, terminal pane
   identifiers, local session identifiers, secrets, credentials,
   tokens, and in-flight PR numbers for work that has not merged.
5. Avoids introducing **deployment-time overlay decisions** into
   upstream constants: reviewer tool/model/CLI bindings, source-host
   installation slugs, durable actor identifiers, account-specific
   strings, and runner identifiers per
   [`./REVIEWER_IDENTITY_REQUIREMENTS.md`](./REVIEWER_IDENTITY_REQUIREMENTS.md)
   §c.
6. Runs the envelope's `validation_commands` locally as the work
   proceeds, captures their exit statuses, and notes any skipped
   check with a rationale.

## f. Stop-and-escalate triggers

The consumer halts and escalates **immediately** on any of the
following:

1. **Ambiguity** in the envelope's allowed paths, prohibited
   surfaces, or stop condition.
2. **Missing prerequisite**: a named dependency that is not at
   `Ratified` or `Done`; an unratified reviewer identity required by
   the batch with no Source-ratified waiver; a missing ratification
   record.
3. **Unexpected dirty tree**: working-tree state that the envelope
   does not predict (untracked files outside the envelope's allowed
   paths; modifications to non-allowed files; unexpected stash
   entries).
4. **Need for a prohibited path**: an apparent requirement to mutate
   a path in the envelope's prohibited-surfaces list, or to perform
   a forbidden Git / GitHub operation under
   [`./WORKTREE_RUNTIME_PROTOCOL.md`](./WORKTREE_RUNTIME_PROTOCOL.md)
   §i.
5. **Cross-project leakage signal**: any indication that the
   worktree is reading or writing state belonging to another
   project, tenant, or workstation per
   [`./WORKTREE_RUNTIME_PROTOCOL.md`](./WORKTREE_RUNTIME_PROTOCOL.md)
   §h.
6. **Two-driver detection**: any signal that a second implementation
   driver may be active in this worktree per
   [`./WORKTREE_RUNTIME_PROTOCOL.md`](./WORKTREE_RUNTIME_PROTOCOL.md)
   §d.
7. **Authority conflict**: an apparent need to act in two
   incompatible roles in the same batch, triggering the halt /
   escalation path in
   [`../governance/AUTHORITY_AND_RATIFICATION_MODEL.md`](../governance/AUTHORITY_AND_RATIFICATION_MODEL.md)
   and Feature 002 FR-018.

Escalation is to the controller (Nefarious / Hermes) and, when the
ambiguity touches a privileged class, to Source. The consumer does
NOT improvise around any of the above.

## g. After authoring — report-back

Before reaching the envelope's stop line, the consumer assembles a
concise report-back. The report-back is **verification evidence**,
never Source ratification, and includes:

1. **Changed files.** Exact repo-relative paths the consumer
   created or updated.
2. **Boundary confirmation.** Explicit statement that only
   envelope-allowed files changed, and that no prohibited surface
   was touched. The list of prohibited surfaces is restated by
   reference to the envelope's `prohibited_surfaces` field or a
   cited line.
3. **Validation commands run and exit statuses.** Each command
   listed individually with its exit status; passing commands
   reported as `exit 0`; failing commands reported with their exit
   status and stdout signal.
4. **Skipped checks and rationale.** Any check the envelope listed
   but the consumer did not run, with a one-sentence rationale
   referencing a Source-ratified waiver or an environmental
   constraint. A skip without rationale fails Definition of Done
   per [`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §b.2.
5. **Negative-evidence confirmations.** Explicit statements that no
   staging, no commit, no push, no PR creation / modification, no
   merge, no branch deletion, no worktree removal, no repository
   settings mutation, no CODEOWNERS mutation, no `.github/`
   mutation, no deploy automation, and no mutation of `specs/`,
   `schemas/`, `validators/`, `templates/`, `examples/`, `tenants/`,
   `docs/contracts/`, `docs/product/`, `docs/architecture/`,
   `docs/governance/`, `docs/quality/`, `docs/devops/`, or
   `docs/security/` occurred — unless the envelope explicitly
   ratified one of these surfaces.
6. **Content-smoke summary.** For each new file, a one-paragraph
   summary of the content smoke criteria it satisfied per the
   envelope's `implementation_instructions`.
7. **Stop line.** The exact stop-line wording specified by the
   envelope's `stop_condition` field, repeated verbatim. The
   consumer's terminal text is this line.

The report-back is delivered to the controller for independent
verification per
[`./SCOPE_AUDIT_CHECKLIST.md`](./SCOPE_AUDIT_CHECKLIST.md). The
controller's verification is itself **verification evidence**, not
Source ratification.

## h. Standing invariants

1. **Allowed paths are a closed set.** Anything not enumerated is
   out of scope.
2. **Prohibited surfaces are a hard list.** A prohibited surface is
   not loosened by mechanical convenience or by silence in the
   envelope body.
3. **Source ratification is distinct from review evidence.** A
   `no_blocking_findings` reviewer verdict is not ratification per
   [`./REVIEW_GATE.md`](./REVIEW_GATE.md) §m.1.
4. **The consumer halts at the envelope's stop line.** Mechanics
   are a separate Source-ratified action.
5. **Instance-local facts stay local.** Workstation paths, pane
   identifiers, secrets, and in-flight PR numbers do not enter
   governed artifacts.
6. **Author/approver separation applies.** The consumer is not the
   verifier of their own batch and is not the ratifier of their own
   batch.

## i. Acceptance posture for Slice E

This document satisfies the Slice E envelope's
`ENVELOPE_CONSUMPTION_CHECKLIST.md` requirements:

- Confirms repo / worktree / branch / HEAD match the envelope (§c).
- Restates allowed files and prohibited surfaces before editing
  (§d.1–§d.2).
- Verifies Source ratification exists for the envelope (§d.3).
- Verifies reviewer-identity requirements or named waiver (§d.4).
- Does not broaden scope implicitly (§d.6, §e.1).
- Names the stop-and-escalate triggers on ambiguity, missing
  prereqs, unexpected dirty tree, need for a prohibited path,
  cross-project leakage, two-driver detection, and authority
  conflict (§f).
- Reports exact changed files, commands run and exit statuses,
  skipped checks and rationale, negative-evidence confirmations,
  content-smoke summary, and stop line (§g).
