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
