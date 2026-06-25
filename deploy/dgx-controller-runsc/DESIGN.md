# Contained Controller C1 Design Note

**Scope**: ce-ops#240 C1. This note records the architecture intent and
security boundaries for moving the gate-holding Controller out of a raw host
process and into the same contained runtime family used by governed seats.

## Problem

The gate-holding Controller can run as a raw host process with ambient host
credentials, host home state, and host terminal/session sockets. That is the
wrong default for a process that can hold merge-gate context, dispatch work,
run daemons, and eventually exercise source-host authority.

C1 scaffolds a contained Controller under `runsc`/gVisor and `herdr`. It is a
runtime posture change, not a credential-transport completion. The C1 result is
a dry-runable, auditable launch shape that mirrors contained seat containers
and keeps the operator attach path outside host tmux/herdr state.

## Architecture

C1 provides the Controller as a sibling of the contained seat launchers:

- The image/run-script mirrors the seat container posture: repo bind mount at
  `/workspace/creator-engine`, non-root container user, `runsc`/gVisor runtime,
  dropped capabilities, `no-new-privileges`, runtime-owned tmpfs under
  `/run/creator-engine`, and a dedicated controller home instead of host
  `$HOME`.
- The operator attaches through `herdr` inside the named container, for example
  with `docker exec -it ce-dgx-controller herdr`. Host tmux is not part of the
  Controller keepalive path.
- The image makes `git`, `gh`, and the mounted `creator_engine_validator`
  package available through `PYTHONPATH=/workspace/creator-engine/validators`
  so controller subprocesses can inspect repo state, coordinate on GitHub, and
  run repository-local governance checks.
- The launch path is shaped to let the same contained process later run gate
  daemons, dispatch to governed seats, and host future controller supervision.
  C1 may mount an explicitly supplied non-secret future supervisor socket, but
  does not implement that supervisor.

## Credential-Injection Seam

C1 is a stub-only credential seam. The scaffold exposes only two non-secret
markers: `CE_DGX_CREDENTIAL_INJECTION=SEAM-STUB` and
`CE_TRANSPORT_DEPUTY_SEAM_STATUS=stub-ce-ops-239-no-secret-injection`.

The C1 image and wrapper must not:

- bake source-host, model-provider, OpenBao, signing, or setup tokens into the
  image;
- mount host token files or private keys into the container;
- pass secrets through environment variables, argv, dry-run output, detached
  container metadata, or any durable launch record;
- treat a copied host `$HOME`, SSH agent, browser profile, or existing host
  auth directory as an acceptable credential source.

Real controller credential transport is blocked on ce-ops#239. The intended C2
shape is transport-deputy injection: the host-side authority holder resolves
short grant handles and injects only the scoped credential material required for
the controller action, with TTL and audit records. That transport lands in C2,
not C1.

## Security Boundaries

The target boundary is rootless container execution with gVisor/runsc as the
syscall boundary. The current DGX wrapper is Docker-backed because it needs the
registered `runsc-gvproxy-ptrace` runtime, but the C1 artifact avoids host
authority surfaces that would defeat containment.

The contained Controller must not receive:

- Docker, Podman, or containerd host sockets;
- host `herdr` or tmux sockets;
- host `$HOME` or broad home-directory bind mounts;
- SSH agent sockets, browser profiles, OpenBao root tokens, GitHub App private
  keys, `ce-root-v1`, or equivalent durable authority material.

The only expected operator attach surface is the contained `herdr` instance
owned by the controller container. The controller process may see its own
container-local herdr socket; governed seats must not receive host control
sockets.

## C3 Parity Plan

C3 is the parity gate. It must prove the contained Controller can perform the
Controller's normal operational duties from inside containment:

- inspect repo state and branch status;
- run `gh` for GitHub coordination through the transport-deputy credential path;
- run `python -m pytest validators/tests/unit` and other validator entrypoints;
- run gate daemons and dispatch logic without host tmux/herdr sockets;
- dispatch governed seats while preserving author/reviewer separation and
  existing seat containment rules.

C1 does not claim this live parity. It only provides the image, launcher,
documentation, and dry-run/static tests needed for the later parity exercise.

## C4 Cutover Plan

C4 is the cutover gate. It must make the contained Controller the default
gate-holding controller path only after C2 credential injection and C3 parity
evidence are ratified.

Cutover must include:

- an operator runbook for build, launch, attach, teardown, and rollback;
- a default launch path that uses the contained Controller instead of a raw host
  Controller;
- telemetry/evidence that gate daemons and dispatch are running from inside the
  contained process;
- rollback criteria for returning to a prior controller path during an outage;
- removal or explicit break-glass labeling for raw-host Controller launch.

C1 does not perform this binding cutover.

## Verification Posture

C1 verification is dry-run/static only:

- render the controller launch argv and inspect it for the required `runsc`
  runtime, contained `herdr` configuration, repo mount, dedicated controller
  home, dropped capabilities, and absence of forbidden mounts/sockets;
- run static wrapper tests for refusal paths such as host `$HOME`, plain
  `runsc`, Docker network overrides, and forbidden host control sockets;
- confirm the image/wrapper documentation states that credential injection is a
  stub and that C2 is blocked on ce-ops#239.

C1 does not claim live DGX proof, live merge-gate operation, successful
source-host mutation from inside containment, or completed credential deputy
injection.
