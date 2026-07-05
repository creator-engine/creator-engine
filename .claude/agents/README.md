# CE Worker Roles

This directory contains CE's governed worker role definitions for Claude-Code
controllers and foremen.

The source of truth is `specs/005-pco-parallel-controller-orchestration/worker-isolation-runtime.md`
§d.2, plus the ce-ops#244 and ce-ops#163 operating decisions. Controllers MUST
spawn these role definitions when dispatching workers. They MUST NOT improvise
ad hoc worker roles or broaden a role's mount, egress, or credential boundary at
spawn time.

## Role Vocabulary

Spec 005 §d.2 ratifies role-shaped worker policies with distinct defaults:

- `architect_research`: read-only research and planning over an allocated
  worktree, with model-provider and ratified documentation/web egress, no write
  tokens, no SSH key, and no controller key.
- `implementer`: write-capable implementation in exactly one allocated
  worktree, with bounded dependency/source-host egress and only the per-task
  scoped PAT for the one granted branch.
- `verification`: read-only verification and test execution, with writable
  build-output scratch space and no egress by default.
- `reviewer`: read-only code review role aligned with the schema/review
  workflow vocabulary; it reports findings or verdicts for the controller to
  submit with controller-scoped credentials.
- `canary_qa`: end-to-end product canary and QA role that validates live
  released artifacts from disposable scratch only, with egress limited to
  released artifact channels and controller-minted sandbox-repository tokens.

Naming reconciliation with Codex `AGENTS.md` vocabulary:

- `explorer` approximates CE `architect_research`.
- `worker` / `implementer` maps to CE `implementer`.
- Read-only review maps to CE `reviewer`.
- Verification maps to CE `verification`.
- Released-artifact canary and QA maps to CE `canary_qa`.

## Scope

These files are additive role definitions only. They do not wire injection into
`CLAUDE.md`, launchers, hooks, or runtime dispatch. Injection and wiring remain
a separate ratified design step.
