# DGX Controller Under runsc/gVisor

This directory is the Gate 2 DGX Controller sibling of the merged
`deploy/dgx-runsc/` Codex artifact from ce-ops#128 / `3d9e86a`. It provides an
dry-runable Docker argv wrapper and image notes for running the Claude Code
Controller under the same `runsc-gvproxy-ptrace` containment shape. By default
the wrapper reuses the `deploy/dgx-runsc/` image because that image bakes the
shared herdr harness entrypoint; mount the Claude binary at
`/usr/local/bin/claude`.

This cut does not implement the Gate 3 Controller Supervisor. If
`CE_DGX_SUPERVISOR_SOCKET` is supplied, the wrapper only mounts that existing
socket into the container at `/run/ce-supervisor.sock`.

## Containment Posture

The wrapper defaults to:

- Docker runtime `runsc-gvproxy-ptrace`.
- No Docker `--network` flag unless explicitly allowed for diagnostics.
- `--security-opt=no-new-privileges` and `--cap-drop=ALL`.
- A dedicated controller home mounted at container `HOME`, not the host home.
- No host tmux socket, SSH agent, Docker socket, Podman socket, containerd
  socket, browser profile, OpenBao root token, GitHub App private key, or
  `ce-root-v1` private key mount.
- Claude Code auth passed only as the environment name
  `CLAUDE_CODE_OAUTH_TOKEN`, so dry-runs never print the token value.

The corresponding declarative contract is
`examples/well-formed/controller-runtime-contract/contained.yaml`.

## Build Image

Build the shared herdr entrypoint image from the repo root on the DGX:

```bash
docker build \
  -f deploy/dgx-runsc/Dockerfile \
  -t creator-engine/codex-runsc:0.141.0-aarch64 \
  --build-arg CE_DGX_USER="$(id -un)" \
  --build-arg CE_DGX_UID="$(id -u)" \
  --build-arg CE_DGX_GID="$(id -g)" \
  deploy/dgx-runsc
```

The shared image builds herdr-ce from the pinned source revision inside a
Debian bookworm builder stage. Do not copy a host-built `herdr` binary into the
image; the runtime binary must match the image libc.

The wrapper mounts a runtime-owned tmpfs at `/run/creator-engine` for herdr
socket and XDG state. The substrate entrypoint uses that path to own the herdr
server, while the governed Claude harness starts with a clean environment that
does not inherit socket carriers.

The image intentionally does not bake Claude auth, GitHub auth, OpenBao tokens,
or a private key. Provide a Claude binary through
`CE_DGX_CLAUDE_BIN=/path/to/claude`; the wrapper mounts it at
`/usr/local/bin/claude` and sets `CE_DGX_HARNESS=claude` for the shared
entrypoint.

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

The wrapper refuses `CE_DGX_RUNTIME=runsc`, `CE_DGX_RUNTIME=runsc-gvproxy`, and
Docker `--network` by default. Those overrides exist only for
operator-directed diagnostics and mirror the `deploy/dgx-runsc/` DGX evidence.

## Runtime Registration

Use the same Docker runtime family as the merged Codex DGX artifact:

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

This Gate 2 wrapper does not grant git push authority. Future push/signing
authority must be mediated by the Gate 3+ supervisor path, with Max auth via the
`max-auth-via-setup-token` handle and `ce-root-v1` signing via OpenBao request
handles rather than private-key mounts.
