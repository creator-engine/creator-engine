# Creator Engine — Agent Bootstrap Policy

Any agent (controller, foreman, or worker) opening a session in this repository
MUST read these pointers before doing any substantive work.

## Role Definitions

Worker role policies are in `.claude/agents/`:
- `architect_research.md` — read-only research; returns findings only.
- `implementer.md` — write-capable; one worktree; scoped PAT only.
- `verification.md` — read-only test execution; no egress by default.
- `reviewer.md` — read-only review; returns verdict for controller submission.

Controllers MUST spawn one of these roles when dispatching workers.
Controllers MUST NOT improvise ad hoc roles or broaden a role's boundaries.

## Dispatch Discipline

Before dispatching any worker:
1. Read `playbooks/controller/briefs/dispatch.md` — the SSOT for what a brief must name.
2. Check the in-flight territory map (memory: `ce-dispatch-territory-map-before-dispatch`).
3. Write the seed brief to `.ce/briefs/<slug>.md`, compute `sha256sum`, and send
   the worker the file pointer plus hash — never inline the brief.
4. Record the work claim before the worker starts.

## Hard-Stop Rules (applies to ALL agents)

- NEVER approve a pull request.
- NEVER merge a pull request.
- NEVER self-merge or enqueue without controller confirmation.
- NEVER edit outside the allocated worktree or assigned task scope.
- NEVER use controller-key material, broad host credentials, or SSH keys from
  a worker role.

If a task requires authority outside these limits, STOP and report the missing
authority to the controller. Do not expand scope.

## Where to Find More

- Spec 005 §d.2 (worker isolation runtime): `specs/005-pco-parallel-controller-orchestration/worker-isolation-runtime.md`
- Playbooks index: `playbooks/README.md`
- Skills index: `.claude/skills/`

Auto-review: before PR open and before merge, auto-fire `/code-review` in a fresh-context reviewer worker using `.claude/agents/reviewer.md`; post reviewer evidence only as PR `COMMENT` or `REQUEST_CHANGES`, never `APPROVE`.
