# SEED BRIEF — ADR-0004 payload-as-data-only implementation (dev-4)

- **Ticket**: ce-ops#388 residual (conveyor daemon arm-safety redesign,
  implementation slice). Ratified design = `docs/adr/ADR-0004-conveyor-daemon-arm-safety.md`,
  MERGED on origin/main (PR #727). This brief is self-sufficient for the core
  requirements, but your FIRST step is: `git fetch origin main` and read the
  full ADR from your checkout at that path (§3–§7 are the implementation
  contract). If fetch fails, say so in the done-report and proceed from the
  embedded summary below.
- **Role**: implementer (governed seat). Build, test, commit. You do NOT push,
  approve, merge, enqueue, or touch any gate. You do NOT arm anything: G-N3
  arming stays REFUSED until an independent security review + operator-visible
  dry run (ADR §7) — out of scope here. Controller harvests.
- **Branch**: `ce-388-payload-data-only` off `origin/main`, worktree under
  `/var/tmp` (NOT /workspace). venv has no activate — use
  `.venv/bin/python -m pytest`.
- **Declared work class**: M.

## Implementation contract (ADR §3, embedded)

The discovery payload accepted from a contained seat is limited to FOUR data
fields: `issue`, `branch_name`, `pr_title`, `pr_body`. All are untrusted:
parse, length-limit, encode for the target API, reject on schema mismatch.
Define an allowlist schema and FAIL CLOSED on unknown fields. The daemon must
reject, ignore, AND AUDIT any payload field that supplies commands, argv,
environment, remotes, base refs, repository/worktree/bundle/checkout paths,
validation timeouts, credentials, git config/options, gh options, hook paths,
or publish/approval policy. Do NOT retain compatibility shims for the previous
`validate_command`, `base`, `remote`, `repo_path`, `worktree_path`,
`bundle_path` control fields — remove them.

Per ADR §4–§6 (read in-repo): daemon-owned working directories allocated from
a trusted source (never seat-chosen paths); bundle import must not let the
seat choose local paths/remotes/refs/commands/credentials; landed-content
validation is sandboxed, credentialless, audited; remotes/push-targets/base
refs pinned in daemon-owned config, resolved only from the daemon-owned
checkout.

## Scope

- Target modules: the conveyor/pickup payload path —
  `validators/creator_engine_validator/pickup.py` and the daemon-side consumer
  in `validators/creator_engine_validator/forge/integrator_belt.py` (payload
  parsing/dispatch only — do NOT touch the approval-capability wall, marker,
  or merge-gate logic in that file), plus a new payload-schema module under
  `validators/creator_engine_validator/` if that keeps the diff cleaner.
- Tests REQUIRED (these become the §7 review's regression evidence): unknown
  field → fail-closed + audit record; each banned control field
  (validate_command, base, remote, repo_path, worktree_path, bundle_path) →
  rejected + audited; oversized field → rejected; well-formed 4-field payload
  → accepted; audit records emitted for payload rejection decisions.
- Changelog fragment `.ce/changelog/ce-388-payload-data-only.md` + carrier
  `.ce/pr-manifests/ce-388-payload-data-only.md` regenerated via the
  carrier_gen API (fetch fresh main before regen; rm validators/build +
  egg-info first).

## Gates and done

- **Standing preflight directive (ce-ops#303)**: FULL `ce validate-pr`
  (CI-parity) GREEN before commit-for-harvest; do not discover gates via CI.
- **Done = commit SHA**: `git commit && git rev-parse HEAD` in the done-report;
  emit `READY-FOR-HARVEST ce-388-payload-data-only <sha>` when preflight is
  green.
- **Stop line**: no arming, no daemon config/service changes on the host, no
  edits to approval-wall/merge-gate/queue logic, no new CLI surface beyond the
  payload schema, nothing outside the named modules + tests + changelog +
  carrier. If the redesign seems to require more, STOP and report the design
  question instead.
