# VPS Codex/Controller Under runsc/gVisor

This directory provides the x86_64 VPS launcher for the ce-ops#128
contained+herdr image recipe. The launcher renders a dry-runable Docker argv for
the image entrypoint; it does not call `codex` or `claude` directly inside the
Docker command. `tui` is a launcher mode only: TUI dry-runs end at the image so
the entrypoint runs the bare selected harness binary. `exec` launches append
`exec` and the user arguments after the image.

## Launcher Defaults

`run-vps-runsc.sh` defaults to the VPS posture:

```text
CE_VPS_IMAGE=creator-engine/codex-runsc:x86_64
CE_VPS_RUNTIME=runsc-gvproxy-ptrace
CE_VPS_DOCKER_NETWORK=host
CE_VPS_HARNESS=codex
CE_VPS_REPO=$(pwd)
CE_VPS_CODEX_HOME=$HOME/.codex
CE_VPS_CODEX_BIN=$(command -v codex)
CE_VPS_CONTAINER_REPO=/workspace/creator-engine
CE_VPS_UID=$(id -u)
CE_VPS_GID=$(id -g)
CE_VPS_TTY_FLAGS=-it
```

The VPS runtime explicitly allows Docker `--network=host`; the corresponding
Docker runtime still uses `runsc-gvproxy-ptrace` for process containment.

The launcher always applies:

- `--runtime=runsc-gvproxy-ptrace`
- `--network=host` by default
- `--security-opt=no-new-privileges`
- `--cap-drop=ALL`
- `--user uid:gid`
- repo, Codex home, and Codex binary bind mounts
- `CODEX_HOME`, `TERM`, and `CE_DGX_HARNESS` for the image entrypoint

## Harness Selection

Codex is the default:

```bash
CE_VPS_REPO="$PWD" deploy/vps-runsc/run-vps-runsc.sh tui
CE_VPS_REPO="$PWD" deploy/vps-runsc/run-vps-runsc.sh exec "summarize status"
```

For the controller/Claude variant, use the same script and select the harness:

```bash
CE_VPS_HARNESS=controller \
CE_VPS_CLAUDE_BIN=/path/to/claude \
CE_VPS_REPO="$PWD" \
deploy/vps-runsc/run-vps-runsc.sh tui
```

`controller` is an alias for the image entrypoint's Claude harness marker:
`CE_DGX_HARNESS=claude`. `--harness claude` is also accepted.

## Runtime Registration

Register a Docker runtime named `runsc-gvproxy-ptrace` on the VPS:

```json
{
  "runtimes": {
    "runsc-gvproxy-ptrace": {
      "path": "/usr/bin/runsc",
      "runtimeArgs": [
        "--platform=ptrace"
      ]
    }
  }
}
```

Reload or restart Docker, then confirm:

```bash
docker info --format '{{json .Runtimes}}' | grep -q '"runsc-gvproxy-ptrace"'
```

## Dry-Run Validation

Render the default Codex launch without executing Docker:

```bash
CE_VPS_DRY_RUN=1 \
CE_VPS_REPO="$PWD" \
CE_VPS_CODEX_BIN="$(command -v codex)" \
deploy/vps-runsc/run-vps-runsc.sh exec "hello"
```

The printed argv must include `docker run`, `--runtime=runsc-gvproxy-ptrace`,
`--network=host`, `--security-opt=no-new-privileges`, `--cap-drop=ALL`,
`--user uid:gid`, the repo bind mount, the `.codex` bind mount, the Codex binary
bind mount, and `CE_DGX_HARNESS=codex`. For `tui`, the image must be the final
argv element; no literal `tui` subcommand is passed to the entrypoint.

Render the controller/Claude variant:

```bash
CE_VPS_DRY_RUN=1 \
CE_VPS_HARNESS=controller \
CE_VPS_REPO="$PWD" \
CE_VPS_CODEX_BIN="$(command -v codex)" \
CE_VPS_CLAUDE_BIN=/path/to/claude \
deploy/vps-runsc/run-vps-runsc.sh tui
```

The printed argv must include `CE_DGX_HARNESS=claude`. It must not include
`CE_DGX_HERDR_SOCKET_PATH`, raw `HERDR_SOCKET` carriers, or any host socket bind
mount. The herdr control socket path is substrate-internal and resolved by the
image entrypoint default only.

## Caveats

- Run the interactive form from a real TTY. For non-interactive callers, set
  `CE_VPS_TTY_FLAGS=-i` or use `CE_VPS_DRY_RUN=1`.
- VPS `--network=host` is a deliberate current-host compatibility choice, not
  egress confinement. Process containment is provided by `runsc`; egress
  mediation remains ce-ops#222 follow-on scope.
- The image must provide the herdr harness entrypoint. The launcher passes
  harness markers to that entrypoint; only exec launches pass an `exec`
  subcommand after the image.
- Auth and config stay on the host and enter the container only through explicit
  mounts or named environment forwarding. Do not bake them into the image.
