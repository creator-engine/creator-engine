# DGX Controller Under runsc/gVisor

This directory is the C1 contained-controller deployment scaffold for running a
Controller harness under Docker with the DGX `runsc-gvproxy-ptrace` runtime.
It mirrors the `deploy/dgx-runsc/` seat posture: gVisor containment, herdr
operator attach, tmpfs substrate state, no Docker network by default, dropped
capabilities, `no-new-privileges`, and a dedicated controller home.

The detailed architecture, credential-injection seam, C3 parity plan, and C4
cutover plan live in `deploy/dgx-controller-runsc/DESIGN.md`.

C1 is intentionally a credential seam stub. The launcher does not pass
`CLAUDE_CODE_OAUTH_TOKEN`, token values, token env names, secret refs, host auth
files, or private-key material through Docker env, argv, or mounts. It only
sets the non-secret marker
`CE_DGX_CREDENTIAL_INJECTION=SEAM-STUB` and
`CE_TRANSPORT_DEPUTY_SEAM_STATUS=stub-ce-ops-239-no-secret-injection`.

C2 is blocked on ce-ops#239 / the transport-deputy path. Until that lands, this
scaffold validates containment and operator flow but does not provide durable
Claude auth.

## Containment Posture

The wrapper defaults to:

- Docker runtime `runsc-gvproxy-ptrace`.
- No Docker `--network` flag unless explicitly allowed for diagnostics.
- `--security-opt=no-new-privileges` and `--cap-drop=ALL`.
- A runtime-owned tmpfs at `/run/creator-engine` for herdr and XDG state.
- A writable controller harness log tmpfs at
  `/run/creator-engine/controller-log`, passed through `CE_SEAT_LOG_DIR` and
  `CE_CODEX_STDERR_LOG` so the shared herdr entrypoint never falls back to
  `/var/log/ce-seat`.
- A dedicated controller home mounted at container `HOME`, never the host
  `HOME`.
- Operator attach through the in-container herdr server:
  `docker exec -it ce-dgx-controller herdr`.
- `PYTHONPATH=/workspace/creator-engine/validators`, so the mounted repo exposes
  `creator_engine_validator` to controller subprocesses.

The wrapper does not mount host tmux sockets, host herdr sockets, SSH agent
sockets, Docker sockets, Podman sockets, containerd sockets, browser profiles,
OpenBao root tokens, GitHub App private keys, or `ce-root-v1` private keys.

An optional `CE_DGX_SUPERVISOR_SOCKET` remains as non-secret future plumbing and
is mounted at `/run/ce-supervisor.sock` when supplied. The launcher refuses
Docker, Podman, containerd, herdr, and tmux socket paths for that seam.

## Build Image

Build from the repository root. The Dockerfile intentionally uses root build
context so it can copy the shared herdr harness entrypoint from
`deploy/dgx-runsc/`.

```bash
cd /path/to/creator-engine
docker build \
  -f deploy/dgx-controller-runsc/Dockerfile \
  -t creator-engine/claude-controller-runsc:c1 \
  --build-arg CE_DGX_USER="$(id -un)" \
  --build-arg CE_DGX_UID="$(id -u)" \
  --build-arg CE_DGX_GID="$(id -g)" \
  .
```

The image builds `herdr` from the same pinned herdr-ce source revision as the
DGX Codex seat image, installs `git`, `gh`, `python3`, and `tini`, sets
`PYTHONPATH=/workspace/creator-engine/validators`, and exposes the shared herdr
harness entrypoint. Herdr is configured to execute
`/usr/local/bin/ce-controller-harness`; that wrapper restores `PYTHONPATH`,
exports the non-secret C1 seam markers, and then execs the mounted Claude binary
at `/usr/local/bin/claude`.

Provide a Claude binary with `CE_DGX_CLAUDE_BIN=/path/to/claude`; it is mounted
read-only at `/usr/local/bin/claude`. Do not bake auth into the image.

## Runtime Registration

Use the same Docker runtime family as `deploy/dgx-runsc/`:

```json
{
  "runtimes": {
    "runsc-gvproxy-ptrace": {
      "path": "/usr/bin/runsc",
      "runtimeArgs": [
        "--platform=ptrace",
        "--network=host"
      ]
    }
  }
}
```

After Docker reload/restart:

```bash
docker info --format '{{json .Runtimes}}' | grep -q '"runsc-gvproxy-ptrace"'
```

Do not pass Docker `--network=bridge`, `--network=none`, or `--network=host` to
the launcher for normal operation. The registered runtime owns the DGX gvproxy /
gvisor-tap-vsock egress route.

## Dry-Run Validation

Render the TUI command line without executing Docker:

```bash
CE_DGX_DRY_RUN=1 \
CE_DGX_REPO=/path/to/creator-engine \
CE_DGX_CONTROLLER_HOME=/home/cedev4/.ce/controller-home \
CE_DGX_CLAUDE_BIN=/home/cedev4/.local/bin/claude \
deploy/dgx-controller-runsc/run-controller-runsc.sh tui
```

Render Claude print mode for automation checks:

```bash
CE_DGX_DRY_RUN=1 \
CE_DGX_REPO=/path/to/creator-engine \
CE_DGX_CONTROLLER_HOME=/home/cedev4/.ce/controller-home \
CE_DGX_CLAUDE_BIN=/home/cedev4/.local/bin/claude \
deploy/dgx-controller-runsc/run-controller-runsc.sh exec "summarize status"
```

The printed argv should include `docker run`, `--runtime=runsc-gvproxy-ptrace`,
`--security-opt=no-new-privileges`, `--cap-drop=ALL`, `--tmpfs
/run/creator-engine:...`, `--tmpfs
/run/creator-engine/controller-log:...`, the repo mount, the dedicated
controller-home mount, the optional Claude binary mount,
`CE_DGX_HARNESS_BIN=/usr/local/bin/ce-controller-harness`,
`CE_SEAT_LOG_DIR=/run/creator-engine/controller-log`,
`CE_CODEX_STDERR_LOG=/run/creator-engine/controller-log/controller-stderr.log`,
`CE_DGX_TERMINAL_KIND=herdr`, and `CE_DGX_CREDENTIAL_INJECTION=SEAM-STUB` /
`CE_TRANSPORT_DEPUTY_SEAM_STATUS=stub-ce-ops-239-no-secret-injection`.

The printed argv must not include a Docker `--network=` flag, `HERDR_SOCKET_PATH`,
`CLAUDE_CODE_OAUTH_TOKEN`, token-looking values, Docker/Podman/containerd socket
mounts, host herdr socket mounts, or host tmux socket mounts.

## Detached Launch

Detached mode is the canonical operator path:

```bash
CE_DGX_REPO=/path/to/creator-engine \
CE_DGX_CONTROLLER_HOME=/home/cedev4/.ce/controller-home \
CE_DGX_CLAUDE_BIN=/home/cedev4/.local/bin/claude \
deploy/dgx-controller-runsc/run-controller-runsc.sh --detach tui
```

Detached mode runs `docker run -d --name ce-dgx-controller` and deliberately
drops `--rm`, leaving a crashed or stopped controller inspectable through
`docker logs`, `docker inspect`, and the recorded exit code. After start, the
wrapper polls the in-container herdr socket and pane list. On success it prints
the attach and retire commands:

```bash
docker exec -it ce-dgx-controller herdr
docker stop ce-dgx-controller && docker rm ce-dgx-controller
```

Foreground mode keeps `docker run --rm` and `exec`s Docker in the calling
terminal.

## Forward Pointers

- C2: transport-deputy credential delivery from ce-ops#239. This is where
  Claude auth becomes available without env/argv/mount secret exposure.
- C3: parity validation against the existing DGX Codex runsc seat posture.
- C4: cutover from scaffolded controller launch to the governed controller
  deployment path once C2/C3 evidence is ratified.

## Tests

Run the controller shell dry-run checks from the repository root:

```bash
deploy/dgx-controller-runsc/test-controller-dry-run.sh
```

Run the validator unit coverage from the repository root:

```bash
python -m pytest validators/tests/unit
```
