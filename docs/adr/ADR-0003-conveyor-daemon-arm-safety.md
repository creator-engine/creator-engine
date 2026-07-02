# ADR-0003 — Conveyor daemon arm-safety by construction

- **Status:** Proposed — awaiting Operator ratification of the arm-safety model.
- **Date:** 2026-07-02
- **Gate:** G-N3 — conveyor daemon go-live arming model.
- **Mutation class:** docs/governance documentation only. This ADR changes no
  validator behavior, no conveyor helper behavior, no forge transport behavior,
  and no install/download artifact.
- **Authority basis:** conveyor daemon security-redesign task brief,
  SHA256 `164ee5d82d04eb6ea4e810c6900b91eef0d28419cb97505afeb94cb15b0e9e5f`.

> This ADR proposes the conveyor daemon arming model. It does not arm the
> daemon and does not authorize implementation without Operator ratification and
> independent security review.

---

## 1. Context

The conveyor harvest-to-push path is intended to mechanize the loop from a
contained seat's READY branch through bundle landing, validation, push, and PR
creation. The current design document, `.ce/design/conveyor-harvest-push.md`,
keeps push, PR creation, approval, reviewer actions, and daemon-loop harvesting
behind later Operator arming. The checked-in
`creator_engine_validator.conveyor` module exposes `prepare_harvest()` for
local carrier regeneration and validation, and `land_bundle()` for bundle
verify, fetch, switch, rebase, and landed-head reporting. The checked-in
`creator_engine_validator.conveyor_daemon` module adds a disarmed-by-default
`ConveyorDaemon` loop: `ConveyorDaemonItem.from_mapping()` coerces discovery
payloads, `run_once()` plans or dispatches items, `_process_armed()` calls
`prepare_runner`, `land_runner`, `git push`, and `gh pr create`, and
`_path_confinement_violations()` currently confines payload paths before those
sinks.

Security review of the go-live daemon design found four distinct
command-execution or escape classes:

- r1: payload `validate_command` became subprocess argv.
- r2: payload `base` reached `git rebase --exec`, and payload `remote` reached
  a dangerous `git push ext::` transport.
- r3: payload `bundle_path` reached `git fetch ext::`, while
  `repo_path`/`worktree_path` let an attacker stage a repository whose local
  git config reintroduced a dangerous remote.
- r4: the path-confinement repair resolved a path, then downstream git used the
  raw payload path, allowing a symlink-swap time-of-check/time-of-use escape.

The deeper design issue is that both discovery payloads and bundle contents are
authored by a contained harvest seat. The seat is contained, but it is capable
and must be treated as potentially compromised. The daemon runs on a trusted
host with push and PR authority, so command execution in the daemon is a full
fleet compromise.

## 2. Decision

The conveyor daemon must be arm-safe by construction. The daemon may consume
seat output only as untrusted data and untrusted repository content; it must not
consume seat output as execution control, filesystem control, remote control,
or base-ref control.

Recommended default: G-N3 arming is refused until the daemon is redesigned so
every authority-bearing choice is derived from daemon-owned configuration and a
daemon-owned checkout, not from the harvest payload.

## 3. Payload is data only

The discovery payload accepted from a contained seat is limited to these data
fields:

- `issue`: the issue or ticket identifier, such as `388` or `PROJECT-388`.
- `branch_name`: the requested carrier branch name or already-normalized
  branch slug.
- `pr_title`: PR title text.
- `pr_body`: PR body text.

These fields are still untrusted input and must be parsed, length-limited,
encoded for the target API, and rejected on schema mismatch. They do not grant
authority.

The payload must not contain fields that steer execution or authority. The
daemon must reject, ignore, and audit any payload field that supplies commands,
argv, environment, remotes, base refs, repository paths, worktree paths, bundle
paths, checkout paths, validation timeouts, credentials, git config, git
options, gh options, hook paths, or publish/approval policy.

Recommended default: define an allowlist schema for the four accepted fields
and fail closed on unknown fields. Do not retain compatibility shims for the
previous `validate_command`, `base`, `remote`, `repo_path`, `worktree_path`, or
`bundle_path` control fields.

## 4. Daemon-owned working directories and bundle import

The daemon creates and owns all working and staging directories. A harvest seat
never supplies a directory in which the daemon runs git, gh, validation, or
cleanup.

Recommended default flow:

1. The daemon allocates a fresh, private staging root under a daemon-owned
   runtime directory with restrictive permissions.
2. The daemon creates a fresh clone or worktree from a daemon-pinned repository
   and daemon-pinned remote.
3. The seat exports a bundle through a brokered transfer channel. The payload
   may identify the work item and branch text, but the transfer channel chooses
   the received object location; the seat never chooses the daemon's local path.
4. The daemon verifies the received object as a git bundle from that
   daemon-owned staging location, then imports it into the daemon-owned
   checkout using daemon-derived refs.
5. All later `git` and `gh` invocations run only with the daemon-owned checkout
   as the current working directory.

The current `ConveyorDaemonItem.from_mapping()` plus `land_bundle()` flow is
useful as a behavioral sketch for discovery coercion and bundle
verify/fetch/switch/rebase reporting, but its arming-safe successor must not
accept raw `bundle_path`, `base_ref`, `repo_path`, or `worktree_path` values
from discovery payloads. Those values must come from daemon allocation,
brokered receipt, and pinned daemon configuration.

## 5. Untrusted content handling

The bundle's tracked files are untrusted input after import. Confining the
checkout location proves only that the filesystem location is daemon-owned; it
does not make the landed tree trusted.

Recommended default:

- Run git with repo-local hooks disabled, for example `-c
  core.hooksPath=/dev/null`, and with controlled config/environment such as
  `GIT_CONFIG_NOSYSTEM=1`, a daemon-owned global config, and no inherited
  untrusted git config.
- Do not trust repo-local `.git/config`, attributes, hooks, aliases, filters,
  clean/smudge drivers, includes, worktree config, or any path from the landed
  tree to steer daemon execution.
- Run validation in a sandbox with no push credentials, no forge token, no
  ambient daemon secrets, bounded filesystem access, bounded network policy,
  bounded time, and a clean environment.
- Treat build scripts, test scripts, package scripts, generated command files,
  and repository-local tool configuration as attacker-controlled. If the
  validator executes them, that execution happens only inside the validation
  sandbox and never in the privileged daemon process.
- Separate verification results from transport authority. A landed tree that
  passes validation is eligible for daemon-owned push/PR consideration; it is
  not allowed to mutate the daemon's configuration, remotes, base refs, gh
  options, or credentials.

A malicious tracked file can still achieve code execution if the validator
intentionally runs project build or test scripts. The design answer is not to
pretend the file is safe; the answer is to make that execution unprivileged,
sandboxed, credentialless, audited, and unable to alter the daemon's later
git/gh authority decisions.

## 6. Pinned remotes and base refs

The daemon resolves remotes and base refs only inside the daemon-owned checkout
and only from daemon-owned configuration.

Recommended default:

- Pin the canonical repository URL, push remote, and target base ref in daemon
  config approved by the Operator.
- Resolve `origin/main` or any successor base ref with explicit fetch refspecs
  in the daemon-owned checkout.
- Refuse protocol helpers and dangerous transports for all daemon git network
  operations unless explicitly approved in daemon config.
- Re-derive the push target from the pinned remote and normalized branch slug;
  do not accept a remote name, remote URL, refspec, or base ref from the seat.
- Before push or PR creation, verify that the imported branch is based on the
  daemon-resolved base and that the path manifest matches the final diff.

The current `ConveyorDaemon.__init__()` pins `validate_command`, `base`,
`remote`, `repo_root`, and `bundle_root`, and `_process_armed()` uses
`self.base` and `self.remote` for rebase, push, and PR creation. The arm-safe
daemon should preserve that pinning intent while moving checkout creation,
bundle placement, validation environment, and all git/gh authority into
daemon-owned policy rather than payload-derived locations.

## 7. G-N3 arming criteria

G-N3 arming requires an independent security review by a reviewer who did not
author the daemon redesign or its implementation.

The review must explicitly attest that:

- The discovery payload schema is data-only and fails closed on unknown or
  execution-control fields.
- All daemon git/gh operations run in daemon-owned directories allocated from a
  trusted source.
- Bundle transfer and import do not let the seat choose local daemon paths,
  remotes, refs, commands, or credentials.
- Validation of landed content is sandboxed, credentialless, audited, and
  unable to mutate daemon authority.
- Remotes, push targets, and base refs are pinned in daemon-owned config and
  resolved only from the daemon-owned checkout.
- Regression tests reproduce the r1-r4 classes and prove they fail closed.
- The daemon emits audit records for payload rejection, bundle import,
  validation, push, and PR creation decisions.
- No auto-approve, merge, enqueue, review-dismissal, or reviewer-authority
  action is included unless a separate Operator-ratified policy authorizes it.

G-N3 remains disarmed until all criteria pass in CI and in an operator-visible
dry run on the target host.

## 8. Migration note

The current disarmed safeguards are valuable as interim defense-in-depth but
are not sufficient for arming.

Reusable:

- Payload validation and fail-closed rejection patterns.
- `ConveyorDaemon.__init__()` pinning intent for `validate_command`, `base`,
  `remote`, `repo_root`, and `bundle_root`.
- `_path_confinement_violations()` fail-closed rejection patterns and the r4
  TOCTOU repair pattern in `_process_armed()` of using resolved paths
  downstream.
- Existing local-prep behavior from `prepare_harvest()`: carrier regeneration,
  validator artifact cleanup, base alignment, and validation result reporting.
- Existing bundle-reporting behavior from `land_bundle()`: bundle verification,
  import status, head resolution, and ahead/behind reporting.

Must be replaced for arming:

- Any `ConveyorDaemonItem.from_mapping()` design where `validate_command`,
  `base`, `remote`, `bundle_path`, `repo_path`, or `worktree_path` arrives
  from the seat payload.
- Any git/gh invocation whose current working directory, remote, base ref,
  refspec, config, hook path, or environment can be influenced by seat-authored
  payload fields or landed repository content.
- Any validation path that runs build scripts with daemon credentials,
  daemon-local config authority, or unsandboxed host access.

The migration target is not "patch the current payload controls"; it is a
daemon-owned authority model where seat output is only data and content.

## 9. Consequences

- The daemon's trusted computing base becomes smaller and explicit: daemon
  config, daemon checkout allocation, transfer broker, validation sandbox, and
  forge credentials.
- The contained seat can still author code and PR text, but it cannot choose
  how the daemon executes, where it executes, what it pushes to, or what base it
  resolves.
- Some conveyor convenience is intentionally removed. Operators must configure
  pinned remotes, bases, validation profiles, and sandbox profiles outside the
  harvest payload.
- The current conveyor remains disarmed until this model is ratified and
  implemented.

## 10. References

- `.ce/design/conveyor-harvest-push.md` — current conveyor harvest-to-push
  helper design and autonomy-arming gates.
- `validators/creator_engine_validator/conveyor.py` — current
  `prepare_harvest()` and `land_bundle()` helper flow.
- `validators/creator_engine_validator/conveyor_daemon.py` — current
  `ConveyorDaemon`, `ConveyorDaemonItem.from_mapping()`, `_process_armed()`,
  and `_path_confinement_violations()` flow.
- Conveyor daemon security-redesign task brief — r1-r4 findings and
  required design scope.
