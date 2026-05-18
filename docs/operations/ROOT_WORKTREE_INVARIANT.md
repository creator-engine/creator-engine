# Root-worktree invariant policy

**Status**: Post-Sprint-0 normative protocol. Part of the **minimum
repo-native delivery control plane** and **not a Jira clone**. Layered
onto, and subordinate to, the Feature 001 substrate, the Feature 002
operating model, the
[`./CONTROLLER_BOUNDARY_POLICY.md`](./CONTROLLER_BOUNDARY_POLICY.md)
role boundary, and the
[`../delivery/WORKTREE_RUNTIME_PROTOCOL.md`](../delivery/WORKTREE_RUNTIME_PROTOCOL.md)
worktree-lifecycle contract. A fresh clone is sufficient to apply
this policy; no external tracker credential, network state, or
instance-local runtime is required.

## a. Purpose

The Creator Engine repository is exercised from at least two
filesystem locations during any non-trivial batch: the **root
checkout** that an operator initially clones into, and one or more
**isolated per-gate worktrees or clones** in which substantive
authoring takes place. These two surfaces have very different jobs.
When the root checkout becomes a substantive authoring surface — when
it accumulates staged edits, unstaged tracked modifications, or
untracked top-level scratch from an in-flight batch — the root stops
being a reliable navigation surface, the next-task protocol can no
longer answer "what is next?" from repository state alone, and the
controller / implementer boundary collapses by accident because the
controller seat is the surface that holds the in-flight authoring.

This policy makes one operational fact answerable from a fresh clone:

> What MUST be true of the root checkout at session start and at
> merge-close, and what MUST a controller do when it is not?

This policy is **normative**. Where it overlaps with the role
boundary in
[`./CONTROLLER_BOUNDARY_POLICY.md`](./CONTROLLER_BOUNDARY_POLICY.md),
the role-boundary contract controls for who-does-what; this policy
controls for the filesystem state of the root checkout. Where it
overlaps with the worktree lifecycle in
[`../delivery/WORKTREE_RUNTIME_PROTOCOL.md`](../delivery/WORKTREE_RUNTIME_PROTOCOL.md),
the worktree-lifecycle contract controls for per-gate worktree shape;
this policy controls for the navigation-only invariant on the root
checkout. The two are deliberately separate: role boundary, worktree
lifecycle, and root-state invariant are three different concerns and
this policy does not merge them.

## b. Source-of-truth relationship

| Upstream source of truth | Role |
|---|---|
| Feature 001 FR-007 / FR-008 / FR-016 / FR-020a | Author/approver separation; privileged-class enumeration; ratification flow. |
| Feature 002 FR-005 through FR-011, FR-013, FR-017, FR-018 | Assignment-Envelope contract; verifies-not-ratifies; authority-conflict halt path. |
| [`./CONTROLLER_BOUNDARY_POLICY.md`](./CONTROLLER_BOUNDARY_POLICY.md) | Source / controller / architect / implementer role boundary; controller-seat-edit anti-pattern. |
| [`../delivery/WORKTREE_RUNTIME_PROTOCOL.md`](../delivery/WORKTREE_RUNTIME_PROTOCOL.md) | Per-gate worktree / branch lifecycle and one-driver-per-worktree contract. |
| [`../delivery/NEXT_TASK_PROTOCOL.md`](../delivery/NEXT_TASK_PROTOCOL.md) | Post-merge ten-field completion report and next-task selection rules. |
| [`./session-continuity-protocol.md`](./session-continuity-protocol.md) | Instance-local session-state file (`.hermes/session-state/STATE.md`) policy; the upstream-tracked template is at [`../../templates/hermes/session-state/STATE.template.md`](../../templates/hermes/session-state/STATE.template.md). |

## c. The root invariant

For every governed Creator Engine batch, the root checkout
(equivalently: the top-level working tree the operator opened the
session in, distinct from any per-gate worktree or isolated clone)
MUST satisfy all four conditions at session start and after every
merge-close gate:

1. **Branch.** The root checkout is on the canonical branch (`main`
   unless an explicit Source-ratified branch reassignment is in
   force).
2. **Remote parity.** The root checkout's HEAD on `main` is equal to
   the live `origin/main` HEAD after a `git fetch origin main`. The
   root MUST NOT silently lag the canonical branch.
3. **Clean working tree.** The root checkout has:
   - no staged paths (`git diff --cached --name-only` is empty);
   - no unstaged tracked modifications (`git diff --name-only` is
     empty);
   - no untracked top-level scratch files or directories that are
     not enumerated in `.gitignore`. Instance-local ignored paths
     (`.hermes/`, IDE state, OS metadata) are permitted because they
     are ignored, not because they are tracked.
4. **No in-flight authoring.** Any substantive authoring associated
   with an active envelope lives in an isolated per-gate worktree or
   clone, never in the root checkout. The root checkout is a
   navigation and orchestration surface only.

These four conditions are the **root invariant**. They are a property
of the filesystem state of the root, not a property of any
personality, pane, or model that observes it.

## d. Substantive authoring belongs in an isolated per-gate surface

Substantive tracked-file authoring under any envelope MUST take place
in an isolated per-gate worktree or fresh clone, per
[`../delivery/WORKTREE_RUNTIME_PROTOCOL.md`](../delivery/WORKTREE_RUNTIME_PROTOCOL.md).
The root checkout MUST NOT be promoted into an authoring surface for
convenience. The reasons are downstream of the controller / implementer
boundary in
[`./CONTROLLER_BOUNDARY_POLICY.md`](./CONTROLLER_BOUNDARY_POLICY.md)
§d–§e and the worktree-lifecycle contract in
[`../delivery/WORKTREE_RUNTIME_PROTOCOL.md`](../delivery/WORKTREE_RUNTIME_PROTOCOL.md);
this policy adds only the root-state invariant that those documents
both presuppose:

- The root being clean is what lets the next-task protocol
  ([`../delivery/NEXT_TASK_PROTOCOL.md`](../delivery/NEXT_TASK_PROTOCOL.md))
  answer the ten merge-report fields from repository state alone.
- The root being on `main` and equal to `origin/main` is what lets a
  fresh-clone reader reproduce the controller's view of the canonical
  branch without chat memory.
- The root being non-authoring is what keeps the controller seat from
  silently accumulating in-flight edits that bypass the
  controller-seat-edit anti-pattern.

## e. Dirty-root remediation: shape the next prompt, do not clean opportunistically

A dirty root checkout — staged paths, unstaged tracked modifications,
or untracked top-level scratch left behind by a prior batch — is a
governance signal, not a janitorial annoyance. The controller's
authorized response is to **shape the next remediation prompt**, not
to opportunistically clean the root.

Specifically, when the root invariant is violated:

1. The controller MUST NOT run destructive remediation on the root
   from the controller seat: no `git reset --hard`, no `git checkout
   .`, no `git restore .`, no `git clean -f[d]`, no `git stash`
   purges, no `git switch` of in-flight edits, no deletion of
   tracked-file modifications, and no removal of untracked top-level
   scratch that may be in-flight evidence from a prior implementer
   pane. These actions can destroy unrecorded evidence that the
   controller's role (verify, not author) requires to be preserved.
2. The controller MUST NOT silently stage, commit, or push the dirty
   root's contents. Doing so would simultaneously violate the
   controller-seat-edit anti-pattern in
   [`./CONTROLLER_BOUNDARY_POLICY.md`](./CONTROLLER_BOUNDARY_POLICY.md)
   §e and the worktree-lifecycle contract in
   [`../delivery/WORKTREE_RUNTIME_PROTOCOL.md`](../delivery/WORKTREE_RUNTIME_PROTOCOL.md).
3. The controller's authorized response is to author a remediation
   prompt that names the observed root state, identifies whether the
   in-flight content belongs to a prior envelope (and, if so, which
   one), and routes the cleanup itself to a separately Source-
   ratified envelope. The remediation envelope's authoring belongs
   in an isolated per-gate worktree or clone — the same as any other
   substantive batch — not in the root checkout.
4. Until the remediation envelope is Source-ratified and the root
   invariant is restored, no new substantive authoring envelope
   SHOULD be consumed against this instance's root checkout.

The intent is conservative: a dirty root is a halt-to-shape signal,
not a halt-to-clean signal. Cleaning is itself a tracked-file
mutation and is itself governed.

## f. Session-start and merge-close root-state checks

The controller (or any operator opening a session) MUST verify the
root invariant at the following moments:

1. **Session start.** Before consuming any new envelope, before
   relaying any handoff, and before authoring any next-task
   recommendation per
   [`../delivery/NEXT_TASK_PROTOCOL.md`](../delivery/NEXT_TASK_PROTOCOL.md)
   §b, the controller confirms the four root-invariant conditions in
   §c hold against the root checkout. A failure here is a halt
   condition per §e, not a soft warning.
2. **After every merge-close gate.** Immediately after a merge to the
   canonical branch lands, and again before the post-merge report in
   [`../delivery/NEXT_TASK_PROTOCOL.md`](../delivery/NEXT_TASK_PROTOCOL.md)
   §b.10 ("cleanup state") is finalized, the controller confirms the
   four root-invariant conditions hold. A merge that leaves the root
   dirty MUST be reported as such in the cleanup-state field and MUST
   shape the next remediation prompt per §e.

These two checks are read-only against the root. They MUST NOT mutate
the root in the act of checking. They MAY surface the result in the
instance-local session-state file (`.hermes/session-state/STATE.md`)
per
[`./session-continuity-protocol.md`](./session-continuity-protocol.md),
following the template structure in
[`../../templates/hermes/session-state/STATE.template.md`](../../templates/hermes/session-state/STATE.template.md).

## g. Scope, prohibitions, and what this policy does not authorize

This policy is a docs-and-policy slice. It does not authorize, and
MUST NOT be read as authorizing, any of the following:

- Validator or preflight implementation. A future privileged
  `code`-class envelope MAY author a `root_worktree_state` validator
  check, a CLI preflight, schemas, tests, or check code; that work is
  deferred to its own Source-ratified envelope and is named in the
  backlog as the "checks/preflight" deferred child gate (see
  [`../delivery/BACKLOG.md`](../delivery/BACKLOG.md) §e).
- Reconciliation of a specific instance's currently dirty root. This
  policy is generic and substrate-internal; it does not reach into
  any specific operator's clone, branch, untracked file, in-flight
  worktree, or in-flight handoff. The current-root reconciliation
  work is named as a separate deferred child gate in
  [`../delivery/BACKLOG.md`](../delivery/BACKLOG.md) §e and requires
  its own Source-ratified envelope.
- GitHub repository settings, topics, homepage, branch protection
  rulesets, Actions, secrets, repository visibility, public-launch
  decisions, or any live remote mutation.
- Provider / tool / model / host / account / tenant binding. Tool,
  model, host, and account bindings are deployment-time overlay
  decisions and MUST NOT be hard-coded into this policy per
  [`../delivery/REVIEWER_IDENTITY_REQUIREMENTS.md`](../delivery/REVIEWER_IDENTITY_REQUIREMENTS.md)
  §c.
- Authority-matrix mutation, identity-record mutation, schema
  mutation, template mutation outside the named manifest, or
  validator mutation. None of those are touched.

The §6 public-readiness continuation that depends on this substrate
remains blocked **only** on this policy/docs child gate landing.
Preflight implementation and current-root reconciliation cleanup are
explicitly named as later gates and are not unblocked by this
policy's landing.

## h. Acceptance posture

This document satisfies the post-Sprint-0 root-worktree-invariant
policy/docs child gate:

- §a names the navigation-vs-authoring distinction.
- §b records the upstream source-of-truth relationships and keeps
  role boundary, worktree lifecycle, and root invariant as three
  distinct concerns.
- §c hardcodes the four-condition root invariant: branch, remote
  parity, clean working tree, no in-flight authoring on the root.
- §d restates that substantive authoring belongs in an isolated
  per-gate worktree or clone, not on the root checkout.
- §e names the dirty-root remediation posture (shape the next
  prompt; do not opportunistically clean) and forbids destructive
  root remediation from the controller seat.
- §f names the session-start and merge-close root-state checks and
  routes their reporting through the instance-local session-state
  file via the upstream template.
- §g declares what this policy does not authorize: no validator /
  preflight code, no current-root reconciliation, no GitHub settings
  mutation, no provider / tool / model / host / account / tenant
  binding, no authority / identity / schema mutation.
