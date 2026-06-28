# Forge Persona Catalog

Status: contract catalog. This document names the governed worker roles that
forge-side automation may route work to. It documents product intent and
least-privilege authority shape only; it does not create schemas, launcher
wiring, credentials, workflow grants, branch protection changes, or live
forge-side automation.

The catalog follows the forge-side automation principle that physical tool
absence is preferred over prompt-only prohibition. A role may do only what its
runtime definition and dispatch envelope grant. If a launcher, connector, or
credential is absent, the role stops at evidence or a recommendation.

## Catalog Rules

- Persona entries are governed artifacts. Changing a role's tool grant,
  writable paths, credential posture, egress, or forge-side authority is a
  separate governed change.
- Author, verifier, reviewer, triage, and operator-facing powers stay
  separated. No worker persona ratifies, approves its own work, merges, deploys,
  or bypasses required checks.
- Read-only means no edits to tracked source paths, no commits, no pushes, no
  issue or pull-request mutation, and no live setting mutation.
- Scratch or build-output write space is not source authority. It is temporary
  evidence space and must not be treated as a tracked repository path.
- Roles without a checked-in agent definition have no standing tool grant. They
  are cataloged so dispatch can choose a fit, not so a launcher can infer broad
  authority.

## Role Matrix

| Role | Purpose | Authority Shape | Explicitly Absent | Best Fit |
| --- | --- | --- | --- | --- |
| `architect_research` | Research architecture, codebase context, documentation, source-host facts, options, risks, and plans. | Read-only allocated worktree and governance context, temporary scratch, read-source-host and ratified documentation or web research surfaces. Checked-in tools: `Read`, `Grep`, `Glob`, `WebFetch`, `WebSearch`. | No `Agent`, `Bash`, `Edit`, `MultiEdit`, or `Write` tool. No write token, source-host mutation, pull-request action, issue mutation, commit, push, approval, merge, deployment, SSH key, controller key, host home, host credential mount, or container engine socket. | Discovery, design comparison, source mapping, dependency or documentation research, risk framing, and implementation plans that need evidence but no mutation. |
| `implementer` | Build the assigned task in one allocated worktree and return implementation evidence. | Read-write authority inside exactly one task-scoped worktree. Checked-in tools: `Read`, `Grep`, `Glob`, `Bash`, `Edit`, `MultiEdit`, `Write`. Egress is limited to model-provider hosts, ratified dependency registries, and source-host write API for the one granted branch when a per-task scoped credential is issued. | No `Agent` tool. No approval, merge, self-merge, gate decision, release decision, policy waiver, controller identity, controller signing material, broad host credentials, SSH key, unscoped source-host credential, host home, credential mount, container engine socket, out-of-worktree edit, or out-of-scope path edit. | Narrow implementation slices, docs changes, test additions, refactors, and branch-local fixes where source mutation is required and review remains separate. |
| `verification` | Run reproducible checks and return verification evidence. | Read-only allocated worktree and governance context, temporary scratch, writable build-output scratch. Checked-in tools: `Read`, `Grep`, `Glob`, `Bash`; shell use is limited to inspection, tests, builds, validators, status, diff, and log collection. | No `Agent`, `Edit`, `MultiEdit`, `Write`, `WebFetch`, or `WebSearch` tool. No tracked-source mutation, formatting, commit, push, pull-request action, issue mutation, approval, merge, package publish, deployment, credentials by default, network egress by default, host home, credential mount, or container engine socket. | Independent reproduction, preflight runs, targeted tests, build checks, log collection, and pass/fail evidence after an implementer has produced a branch. |
| `reviewer` | Inspect changes and return a code-review verdict for a controller to submit. | Read-only allocated worktree and governance context, temporary scratch when explicitly provided. Checked-in tools: `Read`, `Grep`, `Glob`. Returns `APPROVE`, `REQUEST_CHANGES`, or `COMMENT` as evidence only; the controller submits any review action through a separate credential. | No `Agent`, `Bash`, `Edit`, `MultiEdit`, `Write`, `WebFetch`, or `WebSearch` tool. No tracked-file mutation, untracked mutation except explicitly granted runtime scratch, commit, push, pull-request comment, pull-request approval, requested-changes submission, merge, self-approval, write token, source-host credential, host home, credential mount, engine socket, or default egress. | Independent review, policy and regression checks, diff inspection, evidence grading, and self-fire advisory review where approval is not allowed. |
| `harvest_intake` | Intake finished work, check that expected branch, carrier, validation, and completion evidence exist, and package findings for the controller. | Catalog intent is read-mostly intake over submitted worker output, committed diff metadata, carriers, validation logs, and completion reports. Any staging area must be explicit scratch or a controller-owned harvest worktree. No checked-in agent definition currently grants tools or credentials. | No standing `.claude` tool grant. Until formalized, no `Agent`-style fan-out, no source editing, no carrier hand-authoring, no commit, push, pull-request mutation, approval, merge, live forge mutation, branch write token, broad source-host credential, or host credential access. | Post-worker collection, evidence completeness checks, manifest/carrier sanity review, handoff packet assembly, and identifying whether a branch is ready for independent verification or review. |
| `ops_triage` | Triage forge-side signals and route them into claims, queues, or escalation recommendations. | Catalog intent is read and, when separately ratified, bounded comment-only interaction on issue, pull-request, CI, queue, and notification surfaces. It may classify events, deduplicate signals, propose priority, and recommend dispatch. No checked-in agent definition currently grants tools or credentials. | No standing `.claude` tool grant. No source writes, branch token, approval, merge, deploy, live repository setting mutation, ruleset or branch-protection mutation, workflow installation, credential creation, ratification, policy waiver, or unbounded comment authority. | Issue and pull-request intake, CI failure triage, queue hygiene, duplicate detection, escalation preparation, and routing work to the correct governed role. |
| `fleet_recon` | Reconcile visible fleet state and report liveness, occupancy, claims, leases, and stale or conflicting work indicators. | Catalog intent is read-only observation over local seat, worktree, lease, queue, and status read models. It reports facts and anomalies for a controller; it does not repair them. No checked-in agent definition currently grants tools or credentials. | No standing `.claude` tool grant. No source editing, no process control unless separately ratified by an operator-facing mechanism, no issue or pull-request mutation, no queue mutation, no credential access, no approval, no merge, no deploy, no live setting mutation, and no ratification authority. | Fleet inventory, stale-claim detection, lease/read-model comparison, controller inbox preparation, capacity snapshots, and before-dispatch collision checks. |

## Dispatch Guidance

Use the narrowest role that can produce the needed evidence or artifact:

- Pick `architect_research` when the work is understanding, mapping, or
  proposing and does not require shell execution or edits.
- Pick `implementer` only when tracked files must change in a scoped worktree.
- Pick `verification` when the branch already exists and the next need is
  reproducible tests or validator output.
- Pick `reviewer` when the next decision is a review verdict and the reviewer
  must remain unable to submit that verdict directly.
- Pick `harvest_intake` for completion-evidence collection and readiness
  packaging, not for source repair.
- Pick `ops_triage` for forge event classification and routing, not for
  mutation or final decisions.
- Pick `fleet_recon` for read-only operational visibility, not for queue repair
  or seat control.

If a task needs multiple powers, split it across roles. For example, route
research to `architect_research`, source edits to `implementer`, preflight to
`verification`, and review to `reviewer`. Do not expand a role's envelope to
avoid a handoff.
