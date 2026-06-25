# herdr Operator Reach Plane

**Status**: Design note for ce-ops#237.
**Scope**: Operator attach path for contained seats.
**Related boundary**:
[`../architecture/HERDR_GOVERNANCE_BOUNDARY.md`](../architecture/HERDR_GOVERNANCE_BOUNDARY.md)

## Problem

Operator attach to a contained seat pane currently depends on host-root or
container-runtime paths such as:

```bash
docker exec -it <container-name> herdr
```

That path is local to the host that owns the container runtime. It also
over-couples two concerns that should stay independent:

- **Reach**: how an authenticated Operator reaches the live pane.
- **Isolation**: how the seat process is contained by Docker, runsc/gVisor,
  rootless Podman, or another runtime.

Using `docker exec` as the attach mechanism means the Operator needs local
container-runtime authority for an operation that should only require
authenticated pane reach. It also makes remote operation depend on SSHing to
the container host and then using the runtime as an attach transport.

## Design

The reach plane is herdr itself:

```bash
herdr --remote <ssh-target> [--session <name>]
```

The remote client authenticates to `<ssh-target>` with the deployment's
Operator-approved SSH identity, then speaks to the herdr server over the
server-side Unix socket. The herdr client/server Unix-socket protocol remains
the control surface for panes, workspaces, reads, and sends. The optional
`--session <name>` selects a named herdr server/session when the target hosts
more than one attachable CE surface.

Runtime isolation remains independent. The contained seat may be running under
Docker+runsc/gVisor, rootless Podman, rootless Docker, or a future CE-native
jail. None of those runtimes is the reach API. They are only the process,
filesystem, network, and credential-isolation envelope.

This is distinct from prohibited harness-native remote-control flags such as
Codex or Claude remote-control surfaces. `herdr --remote` is the CE reach plane:
it attaches to the CE-owned herdr surface and must preserve the socket
ownership, attribution, and evidence-spine rules recorded in the herdr
governance boundary.

## Operator Attach Flow

For a contained seat, launch still creates a herdr server inside the substrate
boundary. The server owns a Unix socket such as:

```text
/run/creator-engine/herdr/herdr.sock
```

The governed seat runs inside a herdr pane. The seat does not receive
`HERDR_SOCKET_PATH`, does not receive the socket as a bind mount, and cannot
spawn or steer panes through the control socket.

The Operator attach path becomes:

```bash
herdr --remote ce-vps-1 --session ce-vps-codex
```

The remote command resolves the named session to the server-side Unix socket,
authenticates the Operator through SSH, and forwards only the herdr client/server
operation needed to attach or inspect the pane. The Operator no longer needs
host root, Docker group membership, `docker exec`, or local runtime access to
view the contained seat pane.

The container/runtime host still owns lifecycle actions such as start, stop,
garbage collection, image policy, and containment probes. Those remain governed
operations. Attaching to a pane is not a container-runtime operation.

## Podman Posture

Rootless Podman is defense in depth, not the reach fix.

Rootless Podman reduces the blast radius of the runtime envelope by avoiding a
rootful daemon and placing container execution in a user namespace. That is
valuable for isolation. It does not by itself solve Operator reach: an Operator
would still need some host-local attach path unless herdr provides the
authenticated remote reach plane.

Therefore:

- Rootless Podman can improve the isolation layer.
- `herdr --remote <ssh-target> [--session <name>]` fixes the reach layer.
- The two layers must remain separately testable and separately replaceable.

## Implementation References

The current in-repo substrate already has the local herdr socket client seam:

- `validators/creator_engine_validator/runner/herdr_session.py`
  (`HerdrSession`, `HERDR_SOCKET_PATH`, `spawn_pane`, `send`, `observe`)
- `validators/tests/unit/test_herdr_session.py`
- `validators/tests/integration/test_herdr_live.py`
- `deploy/dgx-runsc/herdr-harness-entrypoint.sh`
- `deploy/vps-runsc/herdr-harness-entrypoint.sh`

The CE-side remote attach prototype now validates, plans, and invokes the
reach-plane command without `docker exec`, host root, or local container-runtime
attach:

- `validators/creator_engine_validator/runner/herdr_session.py`
  (`HerdrRemoteAttachPlan`, `build_remote_attach_command`,
  `plan_remote_attach`, `remote_attach`)
- `validators/creator_engine_validator/ce_cli.py`
  (`ce herdr remote-attach`)
- `validators/tests/unit/test_herdr_session.py`
- `validators/tests/unit/test_ce_herdr_cli.py`

The true `herdr --remote <ssh-target> [--session <name>]` transport remains a
herdr-ce responsibility. CE's prototype is the governed wrapper around that
transport: it rejects privileged/container-runtime attach shapes, carries
contained-pane metadata for auditability, and invokes the authenticated herdr
remote reach command as the Operator attach path.

Tests for the remote reach unit should cover at least:

- the CLI shape above and session-name resolution;
- SSH-authenticated reach without requiring host root or `docker exec`;
- preservation of the server-side Unix-socket boundary;
- refusal to expose `HERDR_SOCKET_PATH` or equivalent socket handles to the
  governed seat;
- continued compatibility with the existing `HerdrSession` socket commands and
  pane identifiers.
