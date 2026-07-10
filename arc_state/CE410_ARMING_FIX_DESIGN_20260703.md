# CE-410 Conveyor Arming Fix Design

Baseline studied: `origin/main` at `2fdad970691e853e6f0b1a03f1e5b27150df4f9b`.
Brief hashes verified before work:

- `.ce/briefs/ce-410-arming-fix-design.md`: `df1827a0a77086ab5a661d847da03b5f0ebad37c4a088cbed93ef2a5c4a4d201`
- `/var/tmp/BRIEF_ce410_design.md`: `df1827a0a77086ab5a661d847da03b5f0ebad37c4a088cbed93ef2a5c4a4d201`

## Scope

This is a read-only architecture/design report for the three arming blockers named in the CE-410 dispatch brief. It covers both surfaces that carry the conveyor/integrator arming risk:

- Conveyor harvest daemon: `validators/creator_engine_validator/conveyor.py` and `validators/creator_engine_validator/conveyor_daemon.py`.
- Integrator repair belt / queue poller: `validators/creator_engine_validator/forge/integrator_belt.py` and its v3 CLI wiring.

The design preserves fail-closed behavior. It does not waive any existing gate and does not expand merge, approval, reviewer, or queue authority.

## Sources Consulted

- `validators/creator_engine_validator/conveyor.py`
- `validators/creator_engine_validator/conveyor_daemon.py`
- `validators/creator_engine_validator/pickup_payload_schema.py`
- `validators/creator_engine_validator/forge/integrator_belt.py`
- `validators/creator_engine_validator/forge/integrator_runner.py`
- `validators/creator_engine_validator/forge/integrator_executor.py`
- `validators/creator_engine_validator/v3_cli.py`
- `docs/operations/WORKER_CONTAINER_PROTOCOL.md`
- `docs/adr/ADR-0004-conveyor-daemon-arm-safety.md`
- `specs/005-pco-parallel-controller-orchestration/worker-isolation-runtime.md`
- `validators/creator_engine_validator/schemas/worker-container-policy.schema.yaml`
- `examples/well-formed/worker-container-policies/*.yaml`
- `validators/tests/unit/test_conveyor.py`
- `validators/tests/unit/test_conveyor_daemon.py`
- `validators/tests/unit/test_integrator_belt.py`

## Current State Evidence

### What Is Already Good And Should Stay

- Discovery payload shape is now data-only: `pickup_payload_schema.py:11-19` allows only `issue`, `branch_name`, `pr_title`, and `pr_body`; `pickup_payload_schema.py:21-57` explicitly bans execution, path, env, credential, remote, and validation-control fields; `pickup_payload_schema.py:90-147` fails closed and emits value-free audit records.
- `ConveyorDaemonItem.from_mapping()` validates discovery payloads before reading fields and creates placeholder paths with `daemon_owned_paths_allocated=False`: `conveyor_daemon.py:131-157`.
- Armed `ConveyorDaemon` refuses missing injected seams and missing trusted roots: `conveyor_daemon.py:310-327`.
- Existing path confinement resolves bundle, repo, and worktree paths under pinned roots and rejects argv gadget shapes: `conveyor_daemon.py:532-589`; `_confine_path()` resolves symlinks and `..`: `conveyor_daemon.py:734-754`.
- `_process_armed()` replaces raw item paths with resolved paths before downstream use, closing the previous TOCTOU class: `conveyor_daemon.py:423-448`.
- Existing tests cover payload control-field rejection, data-only payload not armed, path confinement, and the TOCTOU regression: `test_conveyor_daemon.py:287-421`, `test_conveyor_daemon.py:518-760`.
- Worker-container policy substrate already has the right vocabulary: protocol role defaults put `verification` on read-only worktree, no egress, no secrets (`WORKER_CONTAINER_PROTOCOL.md:62-69`), container-instance records bind policy/image/mount/secret/egress state (`WORKER_CONTAINER_PROTOCOL.md:70-110`), and PCO-040 through PCO-045 define schema/forbidden-mount/secret predicates (`WORKER_CONTAINER_PROTOCOL.md:134-228`).

### Blocker 1: No Daemon-Owned Path Allocation

Evidence:

- `ConveyorDaemonItem` still carries executable filesystem control fields: `worktree_path`, `bundle_path`, and `repo_path` at `conveyor_daemon.py:105-113`.
- The direct-object path provenance bit defaults to `True`: `conveyor_daemon.py:128-130`. A caller constructing `ConveyorDaemonItem` directly therefore bypasses the intended "allocation is not wired" refusal unless it voluntarily sets the flag false.
- `_process_armed()` checks only that boolean before proceeding: `conveyor_daemon.py:409-416`. There is no unforgeable allocation record, receipt, nonce, or daemon-local registry lookup.
- Data-only mappings correctly set `daemon_owned_paths_allocated=False`: `conveyor_daemon.py:143-157`, and the test proves they are not armed without allocation: `test_conveyor_daemon.py:397-421`. This is a good refusal, but it is not a real allocation mechanism.
- The integrator repair belt allocates predictable scratch paths from a caller-provided root: `LiveGitHubRepairAdapter.__init__()` stores `self.work_root = Path(work_root)` at `integrator_belt.py:2036-2053`; `_prepare_workspace()` uses `work_root / repo_slug / pr-number-head-prefix`, deletes an existing path, then recreates it at `integrator_belt.py:2171-2176`.
- The CLI exposes that root directly as `--work-root`, defaulting to `.ce/integrator-belt`: `v3_cli.py:4488-4490`, and passes it into `LiveGitHubRepairAdapter` at `v3_cli.py:4715-4719`.

Design:

1. Add a daemon allocation layer, not another confinement check.

   Introduce a small allocation module used by both conveyor daemon and integrator belt, for example `creator_engine_validator.forge.daemon_allocation` or a non-forge neutral module if the conveyor side should not import `forge`. The core types should be value objects:

   - `DaemonRuntimeRoots`: configured daemon-private roots, resolved at daemon startup, mode-checked as owned by the daemon user and not group/world-writable.
   - `DaemonPathAllocation`: allocation id, nonce, created_at, repo, branch/pr identity, base sha/head sha where relevant, `repo_path`, `worktree_path`, `bundle_path` or `workspace_path`, and root provenance.
   - `DaemonPathReceipt`: unforgeable in-process token bound to allocation id plus random nonce. This can be HMACed with a daemon process secret or stored in a private registry keyed by allocation id; tests can use deterministic nonce injection.

   The receipt must be generated only by `DaemonPathAllocator.allocate_*()`. Constructors for direct work items should not be able to mark themselves daemon-owned by setting a boolean.

2. Replace `daemon_owned_paths_allocated: bool` with an allocation receipt.

   For conveyor:

   - `ConveyorDaemonItem.from_mapping()` stays data-only and returns an item with no paths/receipt, or a separate `ConveyorDiscoveryItem` that cannot be processed armed directly.
   - Before `_process_armed()` calls `prepare_runner`, it asks the allocator to create a fresh allocation for the item and to place/receive the bundle into the allocated `bundle_path` through a daemon-owned receipt/transfer hook.
   - `_process_armed()` refuses if an item has executable paths but no valid receipt for the current daemon allocator instance.
   - Remove the default-true provenance bit. If backward compatibility is needed for tests, make direct `ConveyorDaemonItem` path use require `allocation_receipt` explicitly.

   For integrator:

   - Replace `_prepare_workspace()` deterministic path construction with `allocator.allocate_integrator_workspace(repo, pr_number, head_sha)`, returning a fresh directory created with `mkdtemp`-style randomness under the daemon-private root.
   - Do not `shutil.rmtree()` a predictable path. Garbage collect only allocator-owned allocations by receipt/registry and only under the private root.
   - Refuse `work_root` that is relative, broad, symlinked through untrusted roots, or not `0700`/daemon-owned. Prefer removing `--work-root` from the armed CLI and replacing it with `--runtime-root` that is checked as daemon-private.

3. Keep confinement as defense-in-depth.

   `_path_confinement_violations()` should remain, but it becomes a secondary assertion that allocated paths resolve under the daemon roots. A confinement pass alone no longer proves provenance.

4. Add audit records.

   Each allocation should emit a secret-free audit record with `allocation_id`, item key, root kind, allocated relative paths, mode checks, and cleanup result. The nonce/HMAC secret must not be logged.

Blast radius:

- `conveyor_daemon.py`: data model, armed path flow, tests and fakes.
- `integrator_belt.py`: `LiveGitHubRepairAdapter` constructor, `_prepare_workspace()`, cleanup behavior, CLI wiring.
- `v3_cli.py`: `queue-poll --work-root` compatibility/deprecation and fail-closed root checks.
- Tests: existing tests that construct direct `ConveyorDaemonItem` with `/tmp` paths must be updated to provide a fake allocator/receipt rather than relying on `daemon_owned_paths_allocated=True`.

Size: M. It touches two arming surfaces and many tests, but the behavior is localized to path setup/provenance rather than the merge/approval logic.

Test plan:

- Unit: direct `ConveyorDaemonItem` with paths and no receipt fails before prepare/land/git/gh.
- Unit: data-only discovery causes allocator to be called exactly once in armed mode; allocated paths, not payload placeholders, flow into prepare/land/push/pr.
- Unit: forged receipt from another allocator instance is refused.
- Unit: allocation root mode checks refuse relative roots, symlinked roots, world/group-writable roots, and roots outside configured daemon runtime root.
- Unit: integrator adapter no longer deletes a predictable path; two allocations for same PR/head create different directories and both carry receipts.
- Regression: existing path confinement and TOCTOU tests remain, but rewritten to use valid allocator-issued paths.

### Blocker 2: Validation Subprocess Inherits Daemon Secrets

Evidence:

- `_run_validation()` constructs a small intended env containing only `PYTHONPATH` and `TMPDIR`: `conveyor.py:413-433`.
- `_default_validate_runner()` then merges that env over the daemon process environment: `conveyor.py:484-494`. This inherits `GH_TOKEN`, approval-wall secrets, SSH agent variables, credential helper config, cloud tokens, shell path config, and any future controller-key material.
- `_default_git_spawn()` has the same ambient fallback shape for integrator git subprocesses: `integrator_belt.py:489-501`.
- `git_env_with_token()` copies all of `os.environ` and adds `GH_TOKEN`: `integrator_belt.py:522-525`.
- `LiveGitHubRepairAdapter` stores `dict(git_env or os.environ)` as its subprocess env: `integrator_belt.py:2036-2053`, and `_git()` passes that env to every git subprocess: `integrator_belt.py:2234-2245`.
- The protocol's verification role is exactly the desired validation posture: no egress and no secrets by default (`WORKER_CONTAINER_PROTOCOL.md:62-69`), and the well-formed verification example declares empty `egress_allowlist` and `secret_allowlist`: `examples/well-formed/worker-container-policies/podman-verification.yaml:20-23`.
- ADR-0004 already requires validation of landed content to be sandboxed with no push credentials, no forge token, no ambient daemon secrets, bounded filesystem/network/time, and a clean environment: `ADR-0004-conveyor-daemon-arm-safety.md:118-149`.

Design:

1. Make credentialless validation a first-class runner.

   Replace `_default_validate_runner()` with a validation sandbox abstraction:

   - `ValidationSandboxSpec`: repo/worktree path to validate, base ref, head ref, declared work class, command tuple, timeout, and artifact/output directories.
   - `ValidationSandboxResult`: returncode/stdout/stderr plus evidence fields: sandbox kind, env allowlist, secret allowlist hash/count, egress policy id, policy sha, allocation id.
   - `ValidationSandboxRunner.run(spec)`: runs validation under a verification policy.

   The existing `ValidateRunner` callable can remain as a test seam, but production armed mode should not use the ambient subprocess runner.

2. Use worker-container/policy primitives where possible.

   The preferred production implementation is a verification worker/container run governed by the existing worker-container policy contract:

   - Role: `verification`.
   - Mounts: read-only repo/landing tree plus writable tmpfs for build outputs and `$TMPDIR`; no host home; no container engine socket.
   - Egress: empty allowlist unless an Operator-ratified validation profile explicitly allows dependency-registry hosts.
   - Secrets: empty allowlist.
   - Records: container-instance evidence should bind policy sha, image sha, mount manifest, secret grants, egress allowlist, start/stop result.

   If the runtime engine is not yet available, armed conveyor must remain refused. A local scrubbed-env subprocess can be kept only for disarmed tests/development; it is not sufficient arming evidence by itself.

3. Scrub the environment explicitly.

   Validation environment should be allowlisted, not inherited. Minimum:

   - `PATH` set to a daemon-owned/minimal path, e.g. `/usr/bin:/bin`, or a configured validation image path.
   - `PYTHONPATH` set only if needed, and only to the validation copy's `validators` path.
   - `TMPDIR`, `HOME`, `XDG_CONFIG_HOME`, `GIT_CONFIG_GLOBAL`, `GIT_CONFIG_NOSYSTEM`, `GIT_TERMINAL_PROMPT=0` set to sandbox-private paths/values.
   - Remove all `GH_*`, `GITHUB_*`, `SSH_*`, `GIT_ASKPASS`, `GIT_SSH*`, `AWS_*`, `GOOGLE_*`, `AZURE_*`, `OPENAI_*`, `ANTHROPIC_*`, approval-wall env names, and credential-helper variables unless specifically allowlisted for the sandbox role. For verification, none should be allowlisted.

4. Do not let validation mutate transport state.

   Run validation against an isolated validation copy or a read-only lowerdir with tmpfs overlay. After validation, discard the sandbox. The transport checkout used for push/PR remains outside the validation sandbox and receives no modifications from validator code.

Blast radius:

- `conveyor.py`: `_default_validate_runner()`, `_run_validation()` interface, result evidence.
- `conveyor_daemon.py`: armed mode must require a production `ValidationSandboxRunner` or a validate runner explicitly marked credentialless; failure to provide one refuses armed construction.
- Worker-runtime integration: may need a narrow adapter around the existing policy/container record substrate.
- Tests must stop asserting that validation simply receives `{"PYTHONPATH", "TMPDIR"}` as a partial env in a fake while production merges ambient env.

Size: M. The subprocess env scrub is S, but arming-grade reuse of worker-container policy/runtime and read-only/overlay mounts makes the full blocker M.

Test plan:

- Unit: with `os.environ` containing `GH_TOKEN`, approval-wall env, `SSH_AUTH_SOCK`, `GIT_ASKPASS`, and model-provider keys, validation runner receives none of them.
- Unit: validation receives only allowlisted env keys and a deterministic minimal `PATH`.
- Unit: sandbox evidence reports verification role, empty secret allowlist, and empty egress allowlist.
- Unit: validator-created `validators/build` or `.egg-info` appears only in sandbox/tmpfs and never in the transport checkout after validation.
- Negative: if armed mode has no production sandbox runner/policy evidence, daemon construction or run refuses before prepare/land/push/pr.
- Regression: existing validation failure behavior remains not-ready and skips push/PR.

### Blocker 3: No Transport/Validation Credential Separation

Evidence:

- Conveyor armed flow runs prepare/validation first, then land/push/pr from the same daemon object and injected runners: `conveyor_daemon.py:449-499`. The code has no typed distinction between validation runner authority and transport runner authority beyond callable names.
- Existing conveyor `GitRunner` has no env parameter, so default git commands inherit ambient git config/credentials from the daemon process (`conveyor.py:469-481`).
- Integrator queue-poll CLI builds one token-bearing `gh_runner` and one token-bearing `git_env` from the same `token`: `v3_cli.py:4712-4720`.
- `make_live_action_runner()` does the same: `integrator_belt.py:2273-2280`.
- `gh_runner_with_token()` temporarily writes `GH_TOKEN` into process-global `os.environ`: `integrator_belt.py:505-519`. That is unsafe around any subprocess/thread boundary and makes accidental validation inheritance more likely.
- `LiveGitHubRepairAdapter._git()` uses the same `self.git_env` for `git init`, config, fetch, merge, checkout, add, commit, and push: `integrator_belt.py:2177-2197`, `integrator_belt.py:2200-2225`, `integrator_belt.py:2234-2245`. Fetch/push need transport credentials; merge/diff/add/commit do not.
- The executor model already has the right logical boundary: resolver is read-only and executor adapter owns the write authority (`integrator_executor.py:1-10`, `integrator_executor.py:55-65`), but the live adapter implementation collapses all git phases into one credentialed environment.

Design:

1. Introduce explicit authority contexts.

   Define typed context objects and runner factories:

   - `TransportCredentialContext`: only for source-host reads/writes (`gh`, `git fetch`, `git push`, `gh pr create`, merge-queue enqueue). It carries a per-action token provider or file-backed credential helper config. It must never be passed to validation.
   - `LocalGitContext`: credentialless local git operations (`init`, `config user`, `checkout`, `merge`, `diff`, `add`, `commit`, `rev-parse`, `rev-list`). It carries scrubbed git env and disables prompts, hooks, inherited config, and global helpers.
   - `ValidationSandboxContext`: verification role, no credentials, no egress by default.

2. Replace process-global token mutation.

   `gh_runner_with_token()` should not write to `os.environ`. Use a runner that passes an explicit env to `subprocess.run()` or invokes `gh` with a prepared credential file/credential helper isolated under the daemon allocation directory. If the `GhRunner` signature cannot change immediately, add a new `EnvGhRunner` for production and keep the old signature only for test compatibility.

3. Split integrator git phases.

   In `LiveGitHubRepairAdapter`:

   - Use transport env only for `fetch` and `push`.
   - Use local credentialless env for `init`, `config`, `checkout`, `merge`, `diff`, `add`, and `commit`.
   - Do not configure `credential.helper = !gh auth git-credential` in repo-local config for the entire workspace as done at `integrator_belt.py:2180-2185`. Instead, pass a temporary credential helper only for transport commands via `git -c credential.helper=... fetch/push`, or use URL/token through a non-logged askpass wrapper in the allocation tmpdir with strict cleanup.
   - Set `GIT_CONFIG_NOSYSTEM=1`, `GIT_TERMINAL_PROMPT=0`, sandbox-private `HOME`/`XDG_CONFIG_HOME`, and `core.hooksPath=/dev/null` for all git commands.

4. Split conveyor phases.

   In conveyor armed flow:

   - Allocation/import/transport phase: daemon-owned checkout and brokered bundle receipt. Uses transport context where needed.
   - Validation phase: validation copy/sandbox. Uses validation context only.
   - Publish phase: after validation passes and final tree/path-manifest checks pass, push/PR uses transport context. The validation sandbox cannot write to transport config, remotes, credentials, or PR args.

5. Add final re-verification before publish.

   Before push/PR, record and verify:

   - final tree sha / head sha expected from daemon-owned checkout;
   - base ancestry (`behind == 0` or equivalent);
   - path manifest fidelity after validation sandbox completion;
   - no repo-local credential helper/hook/config mutation affecting transport commands.

Blast radius:

- `integrator_belt.py`: runner signatures/env handling, `_prepare_workspace()`, `_git()` call sites, tests for env per command.
- `v3_cli.py`: token acquisition should feed only transport runner/context, not general git env.
- `conveyor.py` / `conveyor_daemon.py`: production runners become authority-scoped rather than ambient callables.
- Tests that monkeypatch `git_env_with_token` and `gh_runner_with_token` will need updates.

Size: S/M. The conceptual change is localized, but many tests assert current constructor args and CLI wiring. If done after the allocation abstraction, the implementation is smaller.

Test plan:

- Unit: integrator fetch/push commands receive transport env/token; init/config/checkout/merge/diff/add/commit receive credentialless local env.
- Unit: no command env contains `GH_TOKEN` except fetch/push/gh transport commands.
- Unit: `gh_runner_with_token` successor does not mutate `os.environ`; concurrent sentinel test observes no process-global `GH_TOKEN` change.
- Unit: repo-local `credential.helper` is not permanently configured for validation/local phases.
- Unit: conveyor publish runner cannot be reached if validation runner reports missing credentialless/sandbox evidence.
- Integration-style fake: malicious validator writes `GH_TOKEN`/`SSH_AUTH_SOCK` probes; output proves absent and no network credential file is mounted.

## Sequencing

1. **Allocation/provenance first (M).** This blocks all caller-influenced path execution and gives later sandbox/transport phases private roots to attach temp HOME, XDG, credential helper, validation copy, logs, and cleanup to. Keep current path confinement as defense-in-depth.
2. **Authority-context split second (S/M).** Introduce transport/local/validation contexts and remove process-global token mutation. This reduces blast radius before the sandbox runner lands and makes the env tests crisp.
3. **Credentialless validation sandbox third (M).** Wire the verification worker-container policy/runtime (or refuse armed mode if unavailable), run validation in isolated copy/overlay, and discard all validator side effects.
4. **Final publish re-verification and audit bundle (S).** Add final tree/base/path-manifest checks and structured audit records that prove which context each phase used.

This order is fail-closed at every step: until all three structural fixes are implemented and independently reviewed, armed mode should continue refusing.

## Re-Arming Evidence Bundle Required

Before Operator ratification of arming, the implementer should produce a bundle containing:

1. **Code evidence**
   - Allocation API and receipts replacing boolean provenance.
   - No default-true path provenance field remains.
   - `queue-poll`/integrator workspace allocation uses daemon-private random allocations, not predictable caller-controlled paths.
   - Validation runner no longer merges `os.environ`.
   - `gh`/git token handling does not mutate process-global `os.environ`.
   - Transport, local git, and validation contexts are separate types or otherwise mechanically impossible to confuse.

2. **Test evidence**
   - New allocation receipt/forgery/root-permission tests.
   - New env-scrub sentinel tests with `GH_TOKEN`, approval-wall secret env, `SSH_AUTH_SOCK`, `GIT_ASKPASS`, and model-provider env values present in the daemon process and absent from validation.
   - New per-command env tests proving only fetch/push/gh transport commands receive forge credentials.
   - Existing r1-r4 regression tests still pass: banned discovery control fields, dangerous base/remote/bundle path shapes, path confinement, and TOCTOU realpath use.
   - Existing queue-daemon approval-wall and merge-gate tests still pass; no approval/merge/queue authority is widened.

3. **Runtime/sandbox evidence**
   - Verification sandbox evidence with policy id/sha, role `verification`, `secret_allowlist=[]`, `egress_allowlist=[]` or ratified equivalent, no host home mount, no engine socket mount.
   - Container-instance or equivalent runtime record binding image sha, mount manifest, secret grants (names only), egress policy, start/stop status, and exit code.
   - Proof that validator-created build artifacts land in sandbox/tmpfs and are discarded.

4. **Dry-run/live-adjacent evidence**
   - Operator-visible dry run on target host showing allocation, validation, publish-decision audit records without pushing or opening PRs.
   - Negative dry run where sandbox runtime/policy is absent and armed mode refuses before any source-host mutation.
   - Negative dry run where root permissions are too broad and daemon refuses.

5. **Independent review evidence**
   - A reviewer who did not implement the fix signs off with COMMENT or REQUEST_CHANGES only; no approval from automation.
   - Review explicitly attests: daemon-owned allocation; credentialless sandbox; transport/validation separation; no weakening of existing gates; no auto-approve/merge/self-merge expansion.

## Open Questions / Implementation Notes

- The checked-in worker-container protocol is partly substrate/record oriented. If a production worker runtime entry point is already available outside the files studied, the implementer should adapt it. If not, CE-410 cannot honestly arm until that runtime exists or an Operator ratifies a narrower local sandbox primitive as equivalent.
- Existing `GitRunner` in `conveyor.py` lacks an env parameter. That is acceptable for tests, but production transport/local git runners should take explicit env/context and never inherit ambient config by default.
- Existing `LiveGitHubRepairAdapter` writes resolved content and commits in the same workspace it fetched. That can remain if local git env is credentialless and push credentials are injected only for the push command; it does not require validation sandbox unless future integrator phases execute untrusted tests/builds.
- Existing deterministic path and cleanup behavior in integrator may be convenient for debugging. Replace with audit records rather than predictable paths; expose allocation id in logs for diagnosis.
