# Claims Lifecycle

`.ce/claims/<slug>.md` files can carry YAML frontmatter so controllers and
watchers can distinguish staged, active, ready, and closed work without scraping
pane output or git history.

## Schema

```yaml
---
slug: ce-476-claim-lifecycle
issue: 476
repo: creator-engine/creator-engine
state: claimed
seat: seat-alpha
controller: CE-DEV-2
claimed_at: 2026-07-06T14:00:00Z
transitioned_at: 2026-07-06T14:00:00Z
pr: null
merge_sha: null
refs:
  - tracker#476
---
```

The body after the frontmatter remains free-form human notes, such as a brief
pointer or closeout evidence pointer.

## States

The ordered lifecycle is:

| State | Meaning |
| --- | --- |
| `claimed` | Work has been dispatched to a seat. |
| `in-build` | The seat has confirmed implementation progress. |
| `ready` | A pull request exists for review. |
| `harvested` | The PR is approved or queued for merge. |
| `landed` | The PR merged to `main`. |
| `released` | The landed SHA is included in a versioned release. |

`landed`, `released`, and `abandoned` are terminal for consumers. The CLI refuses
backward transitions and other state-machine skips unless `--force` is passed.
`--force` does not bypass terminal evidence checks: transitions to `landed` or
`released` must still provide a SHA that is reachable from an accessible `main`
ref.

## CLI

Transition one claim:

```text
ce claim transition <slug> <new-state> [--pr <url>] [--sha <sha>] [--force]
```

The command updates `.ce/claims/<slug>.md`, refreshes `transitioned_at`, stores
`pr` or `merge_sha` when provided, and prints one JSON log line with the event
name `ce_claim_transition`.

`--force` is limited to transition-order and state-machine restrictions. It does
not make unverifiable `landed` or `released` evidence acceptable.

List claims:

```text
ce claim list [--state <state>] [--seat <seat>]
```

The list command reads `.ce/claims/*.md` and prints a compact table. Automation
can pass `--json` for machine-readable rows.

Both commands accept `--repo-root` for tests or workflows that run outside the
repository root.

## Merge Closeout

`.github/workflows/ce-claim-closeout.yml` runs when a pull request closes as
merged into `main`. It derives a claim slug from a `Closes-Claim:` trailer in
the merge commit message, falling back to the merged branch name, and transitions
an existing claim file to `landed` with the merge SHA. If no matching tracked
claim file exists, the workflow exits successfully without weakening the merge.
