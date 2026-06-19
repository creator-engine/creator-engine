# DESIGN: ce-ops#115 Controller Containment

Timestamp: 2026-06-19T04:39:31Z
Revision timestamp: 2026-06-19T05:16:00Z
Authoring seat: dev-4
Scope: design only. Implementation-ready, but no runtime implementation here.

## 1. Mandate and Review Fixes

The mandate is `ce-ops#115 every-agent-contained: CONTAINERIZE THE
CONTROLLER`. The acceptance target is not just "seats contained". The Claude
Code Controller/orchestrator session must also run under a runtime boundary on
the DGX. No sandbox opt-out remains a valid governed posture.

This revision addresses the independent review findings:

- The validate-before-provision precedent is `run_plan` in
  `validators/creator_engine_validator/orchestrator.py`, not a separate
  composition root. `run_plan` checks an `ApprovedPlan`, enforces
  `ApprovedPlan.policy_sha == runtime_policy["policy_sha"]`, enforces
  no-self-approval when `seat_identity` is supplied, and raises before
  `backend.provision` on any mismatch. The Controller Supervisor must copy that
  refusal shape.
- The DGX runsc precedent is the merged `deploy/dgx-runsc/` artifact from
  `#262` / commit `3d9e86a`, not a path tracked at this checkout's current
  `HEAD`. Implementation must use the merged artifact at `3d9e86a` and create a
  sibling controller launcher/image.
- The hard surfaces under containment are now called out as implementation
  contracts: tmux/TUI, remote seat fan-out to dev-1/dev-3/dev-4, controller push
  retention with push-blocked seats, ACP, Claude Code Max auth through
  `claude setup-token -> CLAUDE_CODE_OAUTH_TOKEN`, and `ce-root-v1` signing
  through OpenBao `SecretIdentityBackend`.
- The phased plan now names build artifacts, mount policy, network policy, and
  Supervisor APIs that can be implemented directly.

## 2. Input Ledger and Current Limits

Inputs read:

- `.wave1-containment.md`: first design mandate.
- `.wave1-revision.md`: independent review and revision requirements.
- `validators/creator_engine_validator/orchestrator.py` and
  `docs/contracts/orchestrator.md`: ratification-gated `run_plan` precedent.
- `validators/creator_engine_validator/runner/backend.py`,
  `gvisor_proxy_backend.py`, `openshell_backend.py`, `audit_overlay.py`,
  `cc_hook_adapter.py`, and `ring1_tool_guard.py`: current runtime and guard
  seams.
- `docs/contracts/runtime-policy.md` and `runtime-evidence.md`: policy/evidence
  contracts.
- `docs/operations/CONTROLLER_RUNTIME_CONTRACT_PROTOCOL.md`,
  `CONTROLLER_BOUNDARY_POLICY.md`, `WORKER_CONTAINER_PROTOCOL.md`, and
  `docs/delivery/WORKTREE_RUNTIME_PROTOCOL.md`: current controller/worker
  doctrine.
- `docs/v3-roadmap.md` and `docs/architecture/v3-secure-runtime.md`: v3 plane-C
  and OpenShell/gVisor direction.
- Claude Code authentication docs: `claude setup-token` generates a one-year
  OAuth token for headless use as `CLAUDE_CODE_OAUTH_TOKEN`. Source:
  https://code.claude.com/docs/en/authentication

Access limits:

- `gh` is not installed, so `gh issue view 115 --repo creator-engine/ce-ops`
  could not be used.
- The GitHub app in this seat cannot access `creator-engine/ce-ops`.
- The local `HEAD` does not track `deploy/dgx-runsc/`. The implementation
  baseline is the merged `#262` artifact at `3d9e86a`, and implementers should
  fetch or inspect that commit directly before coding.

## 3. Design Decision

Adopt "Controller as a runtime subject":

```
host ce-supervisor (deterministic, non-agentic)
  -> validate ApprovedPlan + ControllerRuntimePolicy
  -> RunnerBackend.provision(controller)
  -> contained Claude Code Controller under gVisor on DGX
  -> Controller requests seats/push/signing through ce-supervisor RPC
  -> ce-supervisor provisions contained seats and records evidence
```

The contained Controller may coordinate, review, drive mechanics, and push when
ratified. It must not hold:

- Docker/Podman/runsc/OpenShell control sockets;
- host tmux socket;
- host SSH/GPG agents;
- full host `$HOME`;
- GitHub App private key;
- `ce-root-v1` private key;
- raw model/provider credentials outside the intended runtime secret injection
  channel.

The host may still run a small deterministic Supervisor. That Supervisor is not
an agent and does not author product changes. It owns the runtime handles,
credential custody, and evidence writes.

## 4. Precedent: `run_plan` Gate, Applied to the Supervisor

`run_plan` is the pattern to copy:

1. Validate ratification before side effects.
2. Bind approval to the exact run id and exact `policy_sha`.
3. Enforce no self-approval.
4. Resolve the backend only after the gate passes.
5. Let `RunnerBackend.provision` re-validate the runtime policy.
6. Wrap the backend in `AuditOverlayBackend`.
7. Persist or return only value-free evidence.

The Supervisor must have the same shape:

```
start_controller(policy, approved_plan, seat_identity):
  refuse if approved_plan is absent
  refuse if approved_plan.run_id != controller_run_id
  refuse if approved_plan.policy_sha != policy.policy_sha
  refuse if approved_plan.approved_by == seat_identity
  refuse if runtime policy validation fails
  only then call backend.provision(...)
```

There is no separate "trusted Controller launch" path. The Controller launch is
itself a governed run.

## 5. DGX Baseline: Sibling of Merged `deploy/dgx-runsc`

The merged `#262` DGX runsc artifact is the operational precedent:

- dedicated Docker runtime `runsc-gvproxy-ptrace`;
- gVisor `ptrace` platform for Codex compatibility;
- runtime-level `--network=host` paired with DGX Stage-1
  `gvproxy/gvisor-tap-vsock` egress mediation;
- wrapper refuses plain `runsc`, systrap Codex path, and caller-supplied Docker
  `--network` unless explicit diagnostics are enabled;
- UID/GID-preserving non-root container;
- no-new-privileges and `--cap-drop=ALL`;
- bind-mounted repo/tool home/tool binary rather than baked credentials.

Controller implementation should add a sibling, not mutate the seat wrapper:

```
deploy/dgx-controller-runsc/
  Dockerfile
  run-controller-runsc.sh
  README.md
```

The sibling exists because the Controller has different authority than Codex
seats:

- Controller may push when ratified.
- Controller may request remote seat fan-out.
- Controller may request `ce-root-v1` signatures through OpenBao.
- Seats remain push-blocked and never receive signing authority.

The first DGX target is dev-2 Controller running on dev-4/DGX under
`runsc-gvproxy-ptrace`, using the merged `#262` / `3d9e86a`
`deploy/dgx-runsc` artifact as the source posture for the sibling controller
launcher.

## 6. Implementation Artifacts

### 6.1 Controller Image

Proposed build artifact:

```
docker build \
  -f deploy/dgx-controller-runsc/Dockerfile \
  -t creator-engine/claude-controller-runsc:<version>-aarch64 \
  --build-arg CE_DGX_USER="$(id -un)" \
  --build-arg CE_DGX_UID="$(id -u)" \
  --build-arg CE_DGX_GID="$(id -g)" \
  deploy/dgx-controller-runsc
```

Image contents:

- Debian slim or the same base as `#262` runsc image.
- `ca-certificates`, `git`, `openssh-client`, `procps`, `less`, `bash`, `tini`.
- Claude Code CLI pinned by version and artifact hash. For the first DGX pilot,
  a read-only bind of a known host Claude Code binary is acceptable only if the
  binary path and SHA256 are recorded in the controller runtime policy. The
  durable target is a baked, digest-pinned CLI artifact.
- CE wheel installed from the signed local wheelhouse or mounted read-only from
  the repo, not downloaded at controller start.
- Ring-1 `git`/`gh` shims installed first on `PATH`.

The image must not contain:

- `CLAUDE_CODE_OAUTH_TOKEN`;
- GitHub App private key;
- `ce-root-v1`;
- SSH private keys;
- host `.claude`, `.ssh`, `.gnupg`, `.aws`, Docker config, or browser profiles.

### 6.2 Launch Wrapper

Proposed wrapper behavior, sibling to `run-codex-runsc.sh`:

```
CE_DGX_CONTROLLER_IMAGE=creator-engine/claude-controller-runsc:<version>-aarch64
CE_DGX_RUNTIME=runsc-gvproxy-ptrace
CE_DGX_REPO=/workspace/creator-engine
CE_DGX_CONTROLLER_HOME=/home/cedev4/.ce-controller-home
CE_DGX_STATE_ROOT=/workspace/creator-engine/.ce/state
CE_DGX_SUPERVISOR_SOCKET=/run/ce-supervisor/controller-<run-id>.sock
```

Docker run posture:

- `--runtime=runsc-gvproxy-ptrace`;
- no wrapper-supplied Docker `--network`;
- `--security-opt=no-new-privileges`;
- `--cap-drop=ALL`;
- `--user UID:GID`;
- `--workdir /workspace/creator-engine`;
- `--tmpfs /tmp`;
- read-write repo mount only for the controller's governed workspace;
- read-write `.ce/state/controller/<run-id>` mount;
- read-only CE wheelhouse/tooling mounts as needed;
- one allowed host socket: the Supervisor RPC socket, mounted at
  `/run/ce-supervisor.sock`;
- `HOME=/home/<controller-user>`;
- `CLAUDE_CODE_OAUTH_TOKEN` injected by the Supervisor at exec time, never by
  shell history or image layer.

No other host socket is allowed. In particular: no Docker socket, no Podman
socket, no SSH/GPG agent socket, no host tmux socket.

### 6.3 Network Policy

The DGX runtime uses the `#262` `runsc-gvproxy-ptrace` precedent. Because its
runtime args use `--network=host` to survive the nested DGX root-netns issue,
the containment claim depends on the Stage-1 `gvproxy/gvisor-tap-vsock` path and
must be evidenced.

Controller egress allowlist:

- Anthropic/Claude Code endpoints needed for Max OAuth-token use.
- GitHub HTTPS endpoints needed for fetch/push/PR mechanics:
  `github.com:443`, `api.github.com:443`, and package release hosts only when
  explicitly needed by the task.
- Supervisor RPC is local over the mounted Unix socket, not network.
- Remote seat fan-out endpoints only as named host refs:
  `dev-1`, `dev-3`, and `dev-4`, with allowed transport set by the Supervisor.

Default: no direct outbound SSH from the controller. If the first pilot cannot
avoid SSH to dev-1/dev-3, the only allowed SSH form is:

- destination is a named host ref, not arbitrary hostname/IP;
- command is forced to `ce-supervisor remote-rpc`, not shell;
- no agent forwarding;
- no port forwarding;
- `IdentitiesOnly=yes`;
- key material is materialized by the Supervisor for the single operation and
  not persisted in the Controller container;
- the egress proxy logs the connection and the side-effect ledger records the
  remote action.

## 7. Supervisor Interface

The Supervisor is the only host authority exposed to the contained Controller.
It should be a Unix-socket JSON-RPC service for the local DGX pilot; remote
later can tunnel the same protocol over an authenticated, forced-command SSH
endpoint.

Minimum API:

```
StartController(policy_ref, approved_plan_ref, pty_profile) -> ControllerHandle
AttachPty(handle, rows, cols) -> PtyStreamRef
ResizePty(handle, rows, cols) -> Ack
SpawnSeat(controller_handle, host_ref, seat_policy_ref, approved_plan_ref, command) -> SeatHandle
ExecSeat(seat_handle, command_ref, pty_profile?) -> ExecHandle
PushRef(controller_handle, repo_ref, source_ref, target_ref, approved_plan_ref) -> PushResult
MintRunToken(controller_handle, token_request_ref, approved_plan_ref) -> SecretGrantRef
SignWithRoot(controller_handle, key_id, namespace, payload_sha_ref, approved_plan_ref) -> SignatureRef
Collect(handle) -> CollectedEvidenceRef
Teardown(handle, reason) -> TeardownResult
```

Refusal rules:

- No method runs without a controller handle that maps to a live contained
  Controller.
- Any method that creates side effects requires an `ApprovedPlan` bound to the
  relevant policy/run and copied from the `run_plan` predicate shape.
- `SpawnSeat` refuses if the target host is not in the controller policy.
- `PushRef` refuses for non-controller roles. Implementer/architect seats never
  receive push permission.
- `SignWithRoot` refuses unless the payload SHA is already computed and the
  signing action is explicitly ratified.

Evidence:

- Every Supervisor method writes a side-effect-ledger record.
- Runtime lifecycle transitions append to the runtime-evidence spine.
- Secret and key material never appears in request/response bodies, ledgers,
  evidence, argv, or image layers.

## 8. Hard Parts Under Controller Containment

### 8.1 tmux and Interactive TUI

What breaks:

- The host tmux socket cannot be mounted into the Controller container.
- Existing pane registry assumptions based on host tmux pane ids are not enough.
- Claude Code TUI needs a real PTY, resize propagation, TERM, and session state.

Implementation rule:

- Host tmux is display-only. A host tmux pane may run `ce-supervisor attach
  <handle>`, but the contained Controller never receives the tmux socket.
- The Supervisor owns PTY allocation, resize, and attach/detach.
- Pane identity records must use `controller_handle`, `backend_key`,
  `sandbox_ref`, `pty_ref`, and optional host tmux display ref. The host tmux ref
  is not authority.

Acceptance:

- `claude` TUI starts inside the gVisor Controller from a Supervisor PTY.
- `SIGWINCH`/resize is relayed.
- Detach/reattach does not grant host shell access.
- `tmux ls` inside the Controller either shows only container-local tmux or is
  absent; it never sees the host tmux server.

### 8.2 SSH Fan-Out to dev-1/dev-3/dev-4

What breaks:

- A contained Controller cannot rely on ambient SSH agent keys.
- Direct SSH from the agent to VPS seats becomes a broad remote-shell escape.
- dev-1/dev-3 live on the VPS while dev-4 is the DGX local host.

Implementation rule:

- Controller fan-out is Supervisor-mediated. The Controller requests
  `SpawnSeat(host_ref=dev-1|dev-3|dev-4, ...)`.
- For dev-4, Supervisor provisions a local gVisor/OpenShell seat.
- For dev-1/dev-3, Supervisor talks to a remote `ce-supervisor` endpoint. The
  preferred transport is forced-command SSH owned by the Supervisor, not the
  Controller container.
- If the Controller container must initiate the network connection for an early
  pilot, it only reaches a forced-command endpoint through the runsc/gvproxy
  allowlist and receives no reusable private key.

Acceptance:

- `ssh dev-1` from an ordinary Controller shell fails.
- `SpawnSeat(dev-1, ...)` succeeds only when the remote host ref and run policy
  are ratified.
- No SSH agent socket exists in the Controller container.
- Remote fan-out records identify host ref, seat policy SHA, and evidence refs,
  not key material.

### 8.3 Git Push: Controller Retains Push, Seats Are Push-Blocked

What breaks:

- Removing host SSH/GitHub auth would also remove legitimate controller push
  unless a new push path exists.
- Seats must remain unable to push.

Implementation rule:

- The Controller role retains push through `Supervisor.PushRef`, not through
  ambient credentials.
- Controller container `git` is a Ring-1 shim. For `git push`, it calls
  `PushRef` with repo/source/target refs and the approved mechanics plan. The
  Supervisor performs the actual push using a JIT GitHub App installation token.
- The token is injected only into the push child process environment or an
  askpass helper owned by the Supervisor. It is never stored in the repo remote,
  shell history, evidence, or Controller home.
- Seat containers use the same shim posture but with `role != controller`, so
  `git push` returns the CE deny code before network.

Acceptance:

- In a contained implementer seat, `git push` is denied before network.
- In the contained Controller, `git push` without a bound mechanics
  `ApprovedPlan` is denied before network.
- In the contained Controller, a ratified push succeeds through HTTPS JIT token.
- No token value appears in `git remote -v`, process argv, evidence files, or
  `.ce/state`.

### 8.4 ACP Transport

What breaks:

- Local ACP assumes the editor/client spawns the agent subprocess over stdio.
- If the editor is host-local and the Controller is containerized, a naive ACP
  bridge can become an unsandboxed host execution path.

Implementation rule:

- For the DGX pilot, ACP is not the hard boundary. PTY/TUI is the first
  supported control surface.
- If ACP is required, run the ACP agent server inside the Controller container
  and have the host Supervisor bridge JSON-RPC bytes only.
- A host ACP proxy may start/attach to the contained Controller, but it must not
  service tool execution on the host. All tool calls remain inside the container
  and are observed by hooks/Ring-1 shims/Supervisor policy.

Acceptance:

- ACP initialize/version negotiation succeeds through the relay.
- A tool call observed over ACP executes in the Controller container, not on the
  host.
- The ACP relay has no methods for arbitrary host command execution.

### 8.5 Claude Code Max Auth Under Containment

Resolved path:

- Operator runs `claude setup-token` outside the image to generate a one-year
  OAuth token tied to the Claude Code Max subscription.
- The token is stored as a secret, preferably in OpenBao under the same
  SecretIdentityBackend family used for other controller-held identities.
- At Controller start, Supervisor materializes it as
  `CLAUDE_CODE_OAUTH_TOKEN` in the contained Claude Code process environment.
- No browser login, full `.claude` home mount, or subscription cookie is needed.

Implementation details:

- The Controller home may contain Claude Code session/log state, but not the
  OAuth token as a persisted file unless a later policy explicitly permits an
  encrypted secret ref.
- `CLAUDE_CODE_OAUTH_TOKEN` is redacted from all Supervisor logs.
- `claude setup-token` itself is an operator setup step, not a step the
  contained Controller can invoke to broaden authority.

Acceptance:

- `claude --version` and a smoke prompt run headless in the container with only
  `CLAUDE_CODE_OAUTH_TOKEN`.
- Removing the env var causes auth failure without falling back to a mounted
  host `.claude` login.
- Token value does not appear in `.ce/state`, shell history, image layers, or
  evidence.

### 8.6 `ce-root-v1` Signing Through OpenBao SecretIdentityBackend

What breaks:

- Current signing notes often assume an offline controller-held root key.
- Baking `ce-root-v1` into a controller image would permanently compromise the
  containment model.

Implementation rule:

- `ce-root-v1` is stored behind OpenBao `SecretIdentityBackend` as ratified by
  the relevant identity-custody gate.
- The contained Controller never sees the private key.
- For a signing action, Controller calls `SignWithRoot(key_id=ce-root-v1,
  namespace=ce-spec-v1, payload_sha_ref, approved_plan_ref)`.
- Supervisor asks OpenBao for a single-use materialization, signs in a tmpfs or
  signer subprocess, zeroizes the material, and returns only the SSHSIG value and
  metadata.
- Ledger/evidence records contain key id, namespace, payload SHA, signature ref,
  OpenBao lease/accessor ref if safe, and ratification ref. They do not contain
  private key bytes or raw vault tokens.

Acceptance:

- No `ce-root-v1` file exists in the Controller image or container filesystem.
- `SignWithRoot` without Source-ratified signing approval is refused.
- A ratified signing action produces an SSHSIG that verifies with
  `docs/keys/ce-root-v1`.
- OpenBao access is audited and revocation/lease cleanup is recorded.

### 8.7 Interactive TUI Session State

What breaks:

- Claude Code TUI wants durable session state.
- Full host home mounts are forbidden.

Implementation rule:

- Mount a controller-scoped home such as
  `/home/cedev4/.ce-controller-home/<controller-id>`.
- Persist only Claude Code session data, CE controller state, and harmless cache
  explicitly named in the policy.
- Do not persist credentials except via secret refs.

Acceptance:

- Reattach/resume works across container restart when the scoped home is
  mounted.
- Reading `$HOME/.ssh`, `$HOME/.gnupg`, `$HOME/.aws`, or Docker config fails.

## 9. Controller Runtime Policy Shape

Future schema gate should add `role: controller`:

```yaml
kind: runtime-policy-record
record_type: runtime_policy
schema_version: "1"
policy_id: controller-dgx-runsc
policy_sha: "<64-hex>"
role: controller
isolation_backend: gvisor-proxy
image_ref:
  name: creator-engine/claude-controller-runsc:<version>-aarch64
  sha: sha256:<image-digest>
mount_manifest:
  - path: /workspace/creator-engine
    mode: rw
    write_justification: controller workspace for governed mechanics
  - path: /workspace/creator-engine/.ce/state/controller/<run-id>
    mode: rw
    write_justification: controller runtime state and evidence refs
  - path: /run/ce-supervisor.sock
    mode: rw
    write_justification: narrow Supervisor RPC socket
egress_allowlist:
  - host: api.github.com
    port: 443
    protocol: https
    assurance: [l4]
    tls_terminated: false
  - host: github.com
    port: 443
    protocol: https
    assurance: [l4]
    tls_terminated: false
  - host: "<anthropic-claude-endpoint>"
    port: 443
    protocol: https
    assurance: [l4]
    tls_terminated: false
secret_allowlist:
  - CLAUDE_CODE_OAUTH_TOKEN
  - github-app-installation-token
  - ce-root-v1-signing-request
grant_extensible: false
grant_authority: source
```

`github-app-installation-token` and `ce-root-v1-signing-request` are
non-private-key request/handle names. They name Supervisor-mediated capabilities
and pass the `runtime_policy_secret_names_only` predicate; they are not raw token
values, filesystem paths, SSH/GPG private keys, or the `ce-root-v1` private key.

Additional controller-only forbidden surfaces:

- host tmux socket;
- SSH/GPG agent sockets;
- Docker/Podman/containerd sockets;
- full host home;
- host browser profile;
- raw OpenBao token;
- raw GitHub App private key;
- raw `ce-root-v1` private key.

## 10. Build and Launch Steps for DGX Pilot

1. Fetch/verify the merged `#262` `deploy/dgx-runsc` artifact and copy its
   runtime posture into a sibling `deploy/dgx-controller-runsc`.
2. Build `creator-engine/claude-controller-runsc:<version>-aarch64`.
3. Register/verify Docker runtime:

   ```bash
   docker info --format '{{json .Runtimes}}' | grep -q '"runsc-gvproxy-ptrace"'
   ```

4. Start `ce-supervisor` on the host with:

   - OpenBao SecretIdentityBackend config;
   - GitHub App mint/revoke config;
   - host refs for `dev-1`, `dev-3`, and `dev-4`;
   - gVisor/OpenShell backend registry;
   - side-effect/evidence output under `.ce/state`.

5. Generate/store Claude Max token:

   ```bash
   claude setup-token
   # store result as CLAUDE_CODE_OAUTH_TOKEN in OpenBao/secret backend
   ```

6. Start the Controller through the Supervisor:

   ```bash
   ce-supervisor start-controller \
     --policy .ce/state/policies/controller-dgx-runsc.yml \
     --approved-plan .ce/state/ratifications/controller-start.yml \
     --runtime runsc-gvproxy-ptrace \
     --pty
   ```

7. Attach from host tmux as display:

   ```bash
   ce-supervisor attach <controller-handle>
   ```

8. From inside the contained Controller, prove:

   - Claude Code TUI works with Max token;
   - `git push` denied without mechanics ratification;
   - `Supervisor.SpawnSeat(dev-4, ...)` starts a local contained seat;
   - `Supervisor.SpawnSeat(dev-1, ...)` reaches the remote Supervisor path;
   - `SignWithRoot` refuses without signing ratification.

## 11. OpenShell Parity Path

After the gVisor DGX pilot:

- Render the same controller runtime policy through `OpenShellBackend`.
- Use OpenShell because its Gateway/Supervisor model matches this design, but
  keep it behind `RunnerBackend`.
- First parity target is Claude Code, because OpenShell's current supported
  agent docs list Claude Code as full coverage.
- Keep evidence collection version-aware: current repo code is pinned to text
  log parsing for `v0.0.57`; newer OpenShell docs also document OCSF JSONL.
  Implementation must verify the deployed version before switching formats.
- Store Claude Max token and `ce-root-v1` in OpenBao/SecretIdentityBackend, not
  in OpenShell images.

OpenShell is a backend, not the authority. CE evidence remains the system of
record.

## 12. Acceptance Matrix

| Area | Required proof |
|---|---|
| gVisor boundary | Controller process shows runsc/gVisor runtime; no Docker/Podman socket; no host home; no SSH/GPG agent; no host tmux socket. |
| TUI | Claude Code TUI starts, resizes, detaches, and reattaches through Supervisor PTY. |
| Max auth | `CLAUDE_CODE_OAUTH_TOKEN` from `claude setup-token` authenticates headless; no host `.claude` login mounted. |
| Push | Controller push succeeds only through `PushRef` with ratified mechanics; seats are push-blocked. |
| SSH fan-out | dev-1/dev-3/dev-4 seat spawn uses Supervisor host refs; arbitrary `ssh` shell from Controller fails. |
| ACP | ACP relay, if enabled, carries JSON-RPC only and runs tool calls inside the container. |
| Signing | `ce-root-v1` signing goes through OpenBao SecretIdentityBackend; key is never in image/container; signature verifies. |
| Evidence | Controller and child seat runtime chains verify with `verify_chain(records) == []`; side-effect records exist for launch, attach, spawn, push, token mint/revoke, sign, and teardown. |
| No opt-out | Direct host-local Controller launch is refused for governed runs; diagnostics are operator-only and recorded. |

## 13. Implementation Order

1. Schema/protocol gate:
   - add `role: controller`;
   - amend controller runtime contract from host-local-only to contained
     posture;
   - add controller forbidden-surface predicates.
2. DGX controller wrapper gate:
   - add `deploy/dgx-controller-runsc` as sibling of merged `#262`;
   - dry-run argv tests;
   - image build docs.
3. Supervisor MVP:
   - Unix-socket JSON-RPC;
   - `StartController`, `AttachPty`, `SpawnSeat(dev-4)`, `Teardown`;
   - evidence writes.
4. Auth/custody:
   - Claude Max setup-token injection;
   - OpenBao SecretIdentityBackend for `ce-root-v1`;
   - JIT GitHub token push path.
5. Remote fan-out:
   - dev-1/dev-3 remote Supervisor endpoint;
   - forced-command SSH or equivalent restricted transport;
   - egress policy proof through runsc-gvproxy.
6. Push/ACP/TUI hardening:
   - `git`/`gh` role-aware shims;
   - ACP relay if needed;
   - full TUI resize/reattach tests.
7. OpenShell parity:
   - same policy rendered into OpenShell;
   - version-pinned evidence collection.

## 14. One-Line Summary

Move dev-2's Controller onto dev-4/DGX by launching Claude Code under the
`#262`-preceded `runsc-gvproxy-ptrace` posture, with a non-agentic Supervisor
owning PTY, remote seat fan-out, JIT push tokens, Claude Max token injection,
and OpenBao-backed `ce-root-v1` signing.
