# CE Controller Playbook

Status: SSOT recipes for common Controller actions.
Audience: governed Controllers and foremen.
Rule: prefer these commands over ad hoc probing when driving CE work.

## Recipe: Spawn A Governed Reviewer Venue

Purpose: dispatch a distinct non-author review seat for an author run's opened PR.

Command:

```bash
cev3 review <scope-id> \
  --run <author-run-id> \
  --reviewer-actor <reviewer-login> \
  --spawn \
  --venue-root <out-of-repo-venue-root> \
  --ledger-root <active-work-ledger-root> \
  --controller-id cev3-review \
  --ticket <owner/repo#issue>
```

Inputs:

| Input | Source | Constraint |
| --- | --- | --- |
| `<scope-id>` | Scope created by `cev3 scope` and driven by author run | Must identify the author run's Scope. |
| `<author-run-id>` | `cev3 drive --spawn` dispatch record | Must be the run that opened the PR. |
| `<reviewer-login>` | Host-bound reviewer actor | Login only; never pass a token. |
| `<out-of-repo-venue-root>` | Controller execution zone | Must be outside the source repo. |
| `<active-work-ledger-root>` | Active-Work ledger root | Usually `.hermes/active-work-ledger` for the governed lane set. |
| `--seat-env-file` | Optional owner-only env file | Required only when reviewer credential contract needs a per-seat env file; secret value never enters argv. |

Behavior:

| Step | Effect |
| --- | --- |
| Assemble | Builds reviewer dispatch from collected author evidence. |
| Claim | With `--ticket`, acquires and verifies work claim before side effects. |
| Allocate | Provisions the reviewer venue worktree/lane. |
| Launch | Calls the lane-launch surface for a governed reviewer seat. |

Refusals:

| Refusal | Resolution |
| --- | --- |
| Missing `--venue-root` with `--spawn` | Supply an out-of-repo venue root. |
| Missing `--ledger-root` with `--spawn` | Supply the Active-Work ledger root. |
| `--harness codex` refused | Use default `claude` unless the Codex reviewer venue gate has landed. |
| Foreign active claim | Do not overwrite; pick another ticket or coordinate release. |

## Recipe: Allocate A Lane

Purpose: create a governed worktree lane, write the claim/lease/event, and bind it to a controller.

Command:

```bash
PYTHONPATH=validators python3 -m creator_engine_validator pco-allocate \
  --lane-id <lane-id> \
  --worktree-path <worktree-path> \
  --branch <branch-name> \
  --envelope-ref <assignment-envelope-path-or-none> \
  --controller-id <controller-id> \
  --ledger-root <active-work-ledger-root> \
  --repo-root <repo-root> \
  --lease-seconds 3600 \
  --pane-label <architect|implementer|controller|reviewer>
```

Required fields:

| Field | Purpose |
| --- | --- |
| `--lane-id` | Stable lane identifier; use a role/task slug. |
| `--worktree-path` | Target path for `git worktree add`. |
| `--branch` | Branch to create in the worktree. |
| `--envelope-ref` | Assignment Envelope path; use `none` only with `--no-write-authority`. |

Operational notes:

| Invariant | Detail |
| --- | --- |
| Root checkout refusal | Allocation must not run from the main/root checkout when the allocator detects unsafe posture. |
| Write authority | `--envelope-ref none` provisions no tracked-file write authority unless `--no-write-authority` is explicit. |
| Ledger | The allocator writes claim, lease, and event records. |

## Recipe: Release A Lane

Purpose: retire a lane after completion, abort, lapse, or handoff.

Command:

```bash
PYTHONPATH=validators python3 -m creator_engine_validator pco-release \
  --lane-id <lane-id> \
  --controller-id <controller-id> \
  --ledger-root <active-work-ledger-root> \
  --repo-root <repo-root> \
  --release-reason <completed|aborted|lapsed|handed_off>
```

Release reasons:

| Reason | Use when |
| --- | --- |
| `completed` | Work finished and closeout is captured. |
| `aborted` | Work stopped before completion. |
| `lapsed` | Lease expired or lane is stale. |
| `handed_off` | Ownership moved to another lane/seat. |

Checklist:

| Check | Command or evidence |
| --- | --- |
| Closeout captured | `ce lane verify ...` or completion report path. |
| Worktree clean/committed | `git status --short` in the lane. |
| Claim release | `pco-release` exits zero and emits release event. |

## Recipe: Launch A Seat

Purpose: start a governed visible seat for a controller, implementer, architect, or reviewer role.

Command:

```bash
ce lane launch \
  --controller-id <controller-id> \
  --lane-id <lane-id> \
  --role <role> \
  --prompt <prompt-file> \
  --prompt-sha <sha256> \
  --repo-root <repo-root> \
  --ledger-root <active-work-ledger-root> \
  --worktree-path <worktree-path> \
  --branch <branch-name> \
  --claim-ticket <owner/repo#issue> \
  --purpose "<short purpose>" \
  --json
```

Role choices:

| Role | Purpose |
| --- | --- |
| `controller` | Plan, dispatch, monitor, triage. |
| `implementer` | Build assigned source/doc changes. |
| `reviewer` | Review author output in distinct venue. |
| `architect` | Design or investigation lane. |

Credential and policy flags:

| Flag | Purpose |
| --- | --- |
| `--seat-env-file` | Owner-only env file for per-seat credential contract. |
| `--reviewer-authority-ref` | Reviewer authority envelope for review lanes. |
| `--runtime-policy` | Ratified runtime policy that bounds resources. |
| `--backend` | Runtime backend selector carried by runtime policy. |
| `--operating-mode` | Defaults to `strict`; elevated modes require `--tenant-policy`. |

## Recipe: Run Local PR Preflight

Purpose: validate committed `base..HEAD` before PR handoff.

Preferred command:

```bash
ce validate-pr \
  --repo-root . \
  --base origin/main \
  --head-ref <branch-name> \
  --declared-work-class <tiny|story|feature|epic>
```

Fallback command when `ce` is unavailable:

```bash
PYTHONPATH=validators python3 -m creator_engine_validator verify-path-manifest \
  --base origin/main \
  --manifest-dir .ce/pr-manifests \
  --head-ref <branch-name> \
  --require-carrier
```

Preflight components:

| Gate | Command |
| --- | --- |
| Path manifest | `creator-engine-validator verify-path-manifest --base origin/main --manifest-dir .ce/pr-manifests --head-ref <branch> --require-carrier` |
| Work sizing | `creator-engine-validator verify-work-sizing-floor --base origin/main --declared-work-class <class>` |
| Tests | Use the ticket/brief test command; for validator work this is often a pytest marker slice. |
| Whitespace | `git diff --check` |

## Recipe: Author Governance Carriers

Purpose: make PR validation self-contained and machine-checkable.

Carrier files:

| File | Required content |
| --- | --- |
| `.ce/changelog/<branch-slug>.md` | YAML front matter with `slug`, `date`, `kind`, `scope`, and `issue`, followed by concise human-readable change summary. |
| `.ce/pr-manifests/<branch-slug>.md` | Self-inclusive authorized path list, count, and canonical SHA-256. |

Path hash algorithm:

```python
sha256("\n".join(sorted(unique_paths)) + "\n")
```

Carrier checklist:

| Check | Requirement |
| --- | --- |
| Self-inclusive | The PR manifest path itself appears in the authorized paths. |
| Exact path set | The manifest lists every changed path and no unmodified extras. |
| Count | `AUTHORIZED_PATHS_COUNT` equals the number of unique sorted paths. |
| Hash | `AUTHORIZED_PATHS_SHA256` matches the canonical path list. |
| Work class | Commit message or PR body declares `tiny`, `story`, `feature`, or `epic` as required by the gate. |
| Changelog | Changelog fragment exists when `--require-carrier` is used. |

Template:

```markdown
---
slug: <branch-slug>
date: YYYY-MM-DD
kind: <added|changed|fixed|feat>
scope: <area>
issue: ce-ops#NN
---

**short summary.**

- Machine-readable bullet.
- Another concise bullet.
```

## Recipe: Commit-Only Worker Closeout

Purpose: finish assigned work without pushing.

Commands:

```bash
git status --short
git diff --check
git add <allowed paths>
git commit -m "<subject>

<body>

- Declared work class: <class>"
```

Report fields:

| Field | Include |
| --- | --- |
| Branch | `git branch --show-current`. |
| Commit SHA | `git rev-parse HEAD`. |
| Changed files | `git show --stat --name-only --oneline --no-renames HEAD`. |
| Validation | Each command and pass/fail/blocker. |
| Push | Explicitly state `not pushed` when commit-only. |
