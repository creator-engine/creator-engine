# Creator Engine Instance Session State

<!--
This file is the template for a Creator Engine instance's local
`.hermes/session-state/STATE.md`. Each deployed instance copies this template
into its own ignored `.hermes/session-state/STATE.md` and fills the
placeholders with instance-local values.

Upstream Creator Engine MUST NOT track an instance's filled-in copy. Keep
`.hermes/` ignored. Do not commit live PR numbers, absolute local paths,
runtime pane identifiers, active role assignments, or instance-specific
next steps to upstream.

See `docs/operations/session-continuity-protocol.md` for the full protocol,
checklists, and ratification rules.
-->

## Repository snapshot

- Repository path: `<repo-path>`
- Active worktree (if any): `<worktree-path-or-none>`
- Branch at snapshot: `<branch>`
- Base branch: `<base-branch>`
- Base HEAD at snapshot: `<commit-sha>` — `<commit-subject>`
- Working tree expectation: `<short-description-of-expected-cleanliness>`

## Root-worktree invariant status

Snapshot from `<iso-8601-timestamp>` of the four root-invariant
conditions in
`docs/operations/ROOT_WORKTREE_INVARIANT.md` §c against the root
checkout (distinct from any per-gate worktree above). This block is a
template field; the deployed instance fills it with its own observed
state at session start and after every merge-close gate.

- Root checkout branch: `<branch-name>` (expected `main` unless a
  Source-ratified reassignment is in force).
- Root checkout HEAD vs live `origin/main` after `git fetch origin
  main`: `<equal | ahead | behind | diverged>`.
- Root working-tree cleanliness: `<clean | staged-paths-present |
  unstaged-tracked-modifications | untracked-top-level-scratch |
  multiple>` (`clean` means no staged paths, no unstaged tracked
  modifications, and no untracked top-level scratch outside
  `.gitignore`).
- Root in-flight authoring: `<none | present-from-prior-envelope |
  present-untracked>` (substantive authoring belongs in an isolated
  per-gate worktree or clone per
  `docs/delivery/WORKTREE_RUNTIME_PROTOCOL.md`, not on the root).
- Invariant holds: `<yes | no>`. If `no`, the remediation posture is
  shape-the-next-prompt per
  `docs/operations/ROOT_WORKTREE_INVARIANT.md` §e; the instance MUST
  NOT opportunistically clean the root from the controller seat.
- Last invariant check: `<iso-8601-timestamp>` by
  `<operator-role-or-pane-label>`.

## PR state

List PRs relevant to the instance's current work. Use one entry per PR. If
none, write `None`.

- PR `<pr-number-or-id>`: `<status: DRAFT|OPEN|MERGED|CLOSED>`
  - URL: `<pr-url-or-none>`
  - Merge commit (if merged): `<merge-commit-sha-or-none>`
  - Landed or proposed: `<short-description-of-scope>`

## Ratification state

Record ratification decisions that bound the current instance work. One
bullet per decision. Use `<authority>` for the instance's Source authority
role, not a personal name.

- `<authority>` ratified `<decision-summary>`.
- `<authority>` ratified `<decision-summary>`.

## Controller attestation

Snapshot from `<iso-8601-timestamp>`; restate the controller / pane
boundary in force at this instant.

- Controller role: `<controller-role-or-coordinator-name>`. Authorized
  actions: relay handoffs (pointer-only), recompute path-manifest
  count/SHA256, archive implementer-pane transcripts, run independent
  scope-audit, perform mechanics only under a separately Source-
  ratified envelope. See
  `docs/operations/CONTROLLER_BOUNDARY_POLICY.md`.
- Controller MUST NOT author tracked files inside the implementer's
  envelope; the controller-seat-edit anti-pattern in
  `docs/operations/CONTROLLER_BOUNDARY_POLICY.md` §e is in force.
- Last controller-asserted attestation: `<iso-8601-timestamp>` —
  `<short-attestation-text>`.

## Active handoffs

List handoff files currently in flight (or recently closed and not
yet retired). One entry per handoff. If none, write `None`.

- `<repo-relative-or-absolute-handoff-path>`
  - kind: `<hermes-handoff | hermes-recommended-prompt>`
  - role: `<architect | implementer | controller | reviewer>`
  - expected sha256 (byte-level): `<64-lowercase-hex>`
  - state: `<open | awaiting-stop-line | closed>`
  - transcript archive: `<.hermes/transcripts/<file>.txt or none>`
  - transcript expected sha256 (byte-level): `<64-lowercase-hex or none>`

The expected SHA256 values are recomputed by the verifier per
`docs/operations/NO_COPY_PASTE_PATTERN.md` §g and
`docs/operations/TRANSCRIPT_ARCHIVE_PROTOCOL.md` §e.

## Active roles and panes

Snapshot from `<iso-8601-timestamp>`; verify live runtime state at session
start.

- `<pane-id-or-none>` / `<session-or-context-label>`: `<role: idle|architect|doc-writer|repo-writer|control|other>`, `<short-note>`.

Repeat per active pane or agent. If no terminal multiplexer is in use, write
`Not applicable`.

## Immediate next step

`<immediate-next-step>`

State exactly one next step. If the instance is paused or awaiting
ratification, say so explicitly and name what is required to resume.

## Carry-forward queue

- `<date>`: `<carry-forward-item>`.

List unresolved items that future sessions must not lose. Keep entries short
and link to instance-local handoffs for detail.

## Last updated

- `<iso-8601-timestamp>` by `<operator-role>` during `<short-context>`.
