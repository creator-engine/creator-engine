# Conveyor Security Review - dev1 - 2026-07-02

Review target: PR #740 head `9eb5f2b718d4ad9113a7acab41a7a21b75ecc96b`.
`gh pr view 740` reported `state=OPEN`, `mergedAt=null`; therefore this review used
`/var/tmp/ce-388-conveyor-review` at `origin/pr-740`, not `origin/main`.

Brief verification: `/var/tmp/ce-n3n4-dev1-BRIEF.md` sha256 matched
`8d6c5cea6a25654780e8d5959302c6a9e6448e0df6f80a46111425ff3f57fc0f`.

Scope read: `validators/creator_engine_validator/conveyor_daemon.py`,
`validators/creator_engine_validator/conveyor.py`,
`validators/creator_engine_validator/forge/integrator_belt.py`,
`validators/creator_engine_validator/pickup.py`,
`validators/creator_engine_validator/pickup_payload_schema.py`,
`docs/adr/ADR-0004-conveyor-daemon-arm-safety.md`, and targeted tests.

## Threat-model checks

### 1. Payload-as-data-only: CONFIRMED-SAFE for mapping payloads

Evidence:

- `pickup_payload_schema.py:11-19` allowlists exactly `issue`, `branch_name`,
  `pr_title`, and `pr_body`, with field length caps.
- `pickup_payload_schema.py:21-57` explicitly bans control fields including
  `argv`, `env`, `credentials`, `validate_command`, `base`, `remote`,
  `repo_path`, `worktree_path`, `bundle_path`, `git_options`, and `gh_options`.
- `pickup_payload_schema.py:102-140` fails closed on non-mapping payloads,
  unknown fields, missing fields, non-string fields, oversized fields, and emits
  value-free audit records.
- `conveyor_daemon.py:131-157` calls `validate_discovery_payload()` before
  reading fields and constructs data-only items with local paths set to `.`,
  plus `daemon_owned_paths_allocated=False`.
- `pickup.py:229-236` and `integrator_belt.py:533-540` reuse the same schema.
- Tests cover unknown fields, banned fields, non-string values, missing fields,
  oversized fields, pickup parser reuse, and integrator parser reuse in
  `test_pickup_payload_schema.py:23-146`.

Exploit result: a payload such as
`{"branch_name":"x","issue":"388","pr_title":"x","pr_body":"x","argv":["sh","-c","..."]}`
is rejected before construction; attacker-controlled values are not copied into
audit logs.

### 2. Daemon-owned working directories guard: GAP for arming

Evidence:

- Data-only mapping payloads cannot arm directly: `conveyor_daemon.py:411-416`
  rejects items with `daemon_owned_paths_allocated=False`; test coverage at
  `test_conveyor_daemon.py:397-421` confirms this.
- Armed direct `ConveyorDaemonItem` inputs default
  `daemon_owned_paths_allocated=True` at `conveyor_daemon.py:129`.
- Path confinement only proves `bundle_path`, `repo_path`, and `worktree_path`
  resolve under configured roots (`conveyor_daemon.py:532-589`,
  `conveyor_daemon.py:734-754`). It does not prove the paths were freshly
  allocated by the daemon, private, non-seat-writable, or free of attacker
  repo-local git config.
- ADR-0004 requires daemon-created/owned working and staging directories
  (`docs/adr/ADR-0004-conveyor-daemon-arm-safety.md:90-109`) and says arming
  must not accept local paths from the seat (`docs/adr/...:111-116`,
  `docs/adr/...:220-227`).

Exploit sketch: if an arming integration or broker converts seat output into a
`ConveyorDaemonItem` and leaves the default `daemon_owned_paths_allocated=True`,
an attacker only needs a path that resolves under an overbroad configured root
such as `/var/tmp/ce-conveyor`. They can stage a repo under that root with local
git config or hooks and point `repo_path`/`worktree_path` at it. The current
guard rejects paths outside the root, but it does not verify daemon allocation or
ownership of paths inside the root. This is exactly the ADR class that requires
fresh daemon-owned allocation before arming.

### 3. Per-item isolation: CONFIRMED-SAFE for bad items and item failures

Evidence:

- `conveyor_daemon.py:336-357` catches `DiscoveryPayloadRejected` and unsupported
  item types per item, audits, and continues discovery.
- `conveyor_daemon.py:367-394` processes discovered items independently.
- `conveyor_daemon.py:449-530` wraps armed processing in a per-item `try/except`
  and returns a failed item result instead of aborting the pass.
- Test coverage confirms a schema-rejected discovery item does not drop the
  valid item (`test_conveyor_daemon.py:342-378`) and a prepare failure on one
  item does not block the next item (`test_conveyor_daemon.py:238-261`).

Residual note: if the injected `discovery_runner()` itself raises while
iterating, `conveyor_daemon.py:336-365` returns a whole-pass discovery error.
That is acceptable for a broken discovery provider, but it is not per-record
isolation inside that provider.

### 4. Git/gh argv construction and option-smuggling: CONFIRMED-SAFE for reviewed conveyor sinks, with one arming dependency

Evidence:

- `conveyor_daemon.py:280-299` pins `validate_command`, `base`, and `remote` at
  daemon construction; payloads cannot supply them.
- `_reject_git_argv_gadget()` rejects empty, dash-prefixed, and `::` shaped
  values at `conveyor_daemon.py:705-731`.
- `_process_armed()` uses `self.base` and `self.remote` for prepare, land, push,
  and PR creation (`conveyor_daemon.py:453-499`), not payload fields.
- Branch values sent to push/PR head are derived through `branch_slug()`, whose
  output is constrained to `^[a-z][a-z0-9-]{2,63}$`
  (`path_manifest_fidelity.py:479-505`).
- `conveyor.py:150-179`, `conveyor.py:246-325`, `conveyor.py:469-502`,
  `conveyor_daemon.py:477-499`, `integrator_belt.py:1586-1600`,
  `integrator_belt.py:1627-1640`, and `integrator_belt.py:2183-2193` build argv
  lists and do not invoke a shell.
- Integrator resolved-content paths use `git add -- <path>` and reject absolute
  or `..` paths (`integrator_belt.py:2042-2049`,
  `integrator_belt.py:2330-2332`).

Arming dependency: this remains safe only if `base`, `remote`, `repo_root`,
`bundle_root`, and direct `ConveyorDaemonItem` objects are trusted daemon-owned
configuration/allocation. The gap in check 2 would reintroduce git config based
control even with safe argv arrays.

ce-ops#383 cross-ref: no direct shell/option-smuggling finding in the reviewed
argv construction, but ce-ops#383-style root/working-directory trust is still
the boundary to close before arming.

### 5. No credential exposure in daemon subprocess env: GAP

Evidence:

- `conveyor.py:413-433` builds the validation command as
  `python -m creator_engine_validator.ce_cli validate-pr ...` and sets
  `PYTHONPATH` to the landed worktree's `validators` directory.
- `conveyor.py:484-502` merges `{**os.environ, **env}` into the validation
  subprocess environment. This forwards ambient `GH_TOKEN`, `GITHUB_TOKEN`,
  approval-wall secrets, SSH-related env, and any other daemon process secret.
- `conveyor.py:469-481` runs git subprocesses with inherited environment.
- `integrator_belt.py:505-517` implements `gh_runner_with_token()` by mutating
  process-global `os.environ["GH_TOKEN"]` while running `gh`.
- `integrator_belt.py:522-525` constructs git subprocess env as a copy of
  `os.environ` plus `GH_TOKEN`.
- ADR-0004 requires validation of landed content to be sandboxed,
  credentialless, and unable to access daemon secrets
  (`docs/adr/ADR-0004-conveyor-daemon-arm-safety.md:124-149`,
  `docs/adr/...:181-190`, `docs/adr/...:228-229`).

Exploit sketch: a malicious harvest branch changes
`validators/creator_engine_validator/ce_cli.py` or another imported validator
module. Because validation executes `python -m creator_engine_validator.ce_cli`
with `PYTHONPATH=<landed worktree>/validators`, attacker-controlled code runs
during validation. With the current default env merge, that code can read
`os.environ["GH_TOKEN"]` or other daemon secrets and exfiltrate them through test
output, network, or a later tracked artifact. This is a full credential exposure
class and is not ARM-safe.

### 6. Path traversal in prepare/land/push: CONCERN, bounded but not ARM-safe

Evidence:

- Conveyor item paths are resolved and confined under configured roots at
  `conveyor_daemon.py:532-589` and `conveyor_daemon.py:734-754`.
- The resolved paths, not raw paths, are threaded into prepare/land/push/PR open
  at `conveyor_daemon.py:423-448`; test coverage confirms the symlink/TOCTOU fix
  at `test_conveyor_daemon.py:680-762`.
- `land_bundle()` accepts `bundle_path` and `repo_path` as already-vetted inputs
  and then uses them in git argv/cwd (`conveyor.py:223-265`).
- Integrator resolved file paths reject absolute paths and `..` before writing
  or staging (`integrator_belt.py:2042-2049`, `integrator_belt.py:2330-2332`).

Concern: the traversal checks are technically correct for "under trusted root",
including `..` and symlink collapse, but they rely on the root itself being a
daemon-private allocation boundary. If the trusted root is broad or seat-writable,
an attacker can stay inside the root and still influence the repo/bundle/worktree
the daemon uses. This overlaps with the daemon-owned-working-dirs gap.

Exploit sketch: configure `repo_root=/var/tmp` or another shared writable root.
An attacker creates `/var/tmp/seat-owned/repo` and `/var/tmp/seat-owned/b.bundle`;
both pass `relative_to(repo_root)` / `relative_to(bundle_root)`. The current
path traversal guard prevents `/var/tmp/seat-owned/../../etc`, but it does not
prevent use of the attacker-owned in-root repo. That is not a path traversal bug
in `_confine_path`; it is an arming boundary bug if roots are not daemon-private.

## Overall verdict

DO-NOT-ARM.

Required fixes before arming:

1. Wire real daemon-owned allocation/receipt for worktree, repo, and bundle
   paths. Direct `ConveyorDaemonItem` objects must carry an unforgeable daemon
   allocation/provenance check, or armed mode must only consume allocation records
   created by the daemon.
2. Run validation in a credentialless sandbox with a scrubbed allowlist
   environment. Do not merge `os.environ`; do not run attacker-controlled
   validator code with daemon secrets, forge token, SSH agent, credential helper,
   or privileged network.
3. Keep git/gh transport authority separate from validation. Only push/PR
   subprocesses should receive the forge credential, and only after validation
   completes in the unprivileged environment.
4. Require daemon-private, restrictive roots rather than broad writable roots;
   the current `_confine_path()` check is useful defense-in-depth but not a
   substitute for daemon-owned allocation.

