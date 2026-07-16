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
CE_VPS_CONTAINED_CODEX_CONFIG=$HOME/.ce/logs/seats/<seat-id>/launcher/codex-config.toml
CE_VPS_HOST_WORKTREE_ROOT=$HOME/.ce/logs/seats/<seat-id>/worktrees/<launch-id>
CE_VPS_CONTAINER_WORKTREE_ROOT=/var/tmp
CE_VPS_CODEX_BIN=$(command -v codex)
CE_VPS_CODEX_PACKAGE_ROOT=<autodetected for npm @openai/codex installs>
CE_VPS_CONTAINER_REPO=/workspace/creator-engine
CE_VPS_UID=$(id -u)
CE_VPS_GID=$(id -g)
CE_VPS_TTY_FLAGS=<empty in detached mode, -it in legacy foreground mode>
CE_VPS_DETACH=1
```

`CE_VPS_IMAGE` deliberately defaults to the stable governed x86_64 tag
`creator-engine/codex-runsc:x86_64`, not a launcher-embedded digest. Operators
may supply a specific approved image through `CE_VPS_IMAGE`; the launcher never
inspects, pulls, or publishes that image.

The VPS runtime explicitly allows Docker `--network=host`; the corresponding
Docker runtime still uses `runsc-gvproxy-ptrace` for process containment.

The portable CE CLI/validator image lives in `deploy/oci`. It is not a
replacement for this herdr/Codex seat image; use it as a validator/preflight
payload under the same `runsc-gvproxy-ptrace` runtime when VPS evidence needs
the packaged `ce` and `creator-engine-validator` commands.

The launcher always applies (in both foreground and detached mode):

- `--runtime=runsc-gvproxy-ptrace`
- `--network=host` by default
- `--security-opt=no-new-privileges`
- `--cap-drop=ALL`
- `--user uid:gid`
- repo, Codex home, contained Codex config, and Codex binary/package bind mounts
- a durable host-backed `/var/tmp` worktree-root bind mount
- `CODEX_HOME`, `TERM`, and `CE_DGX_HARNESS` for the image entrypoint

## Building the image

Build from the **repository root** as the Docker context (not this directory):

```bash
deploy/vps-runsc/build-image.sh
```

The repo-root context is required (ce-ops#309) because the image bakes a
CI-parity validator venv: a `python:3.14` builder stage `COPY`s `validators/**`
(pyproject, sources, and the offline `wheelhouse/` + `wheelhouse-dev/`) and
installs the validator runtime and dev/test deps **offline**, matching
`.github/workflows/validate.yml`. The Python-3.14 venv plus its interpreter are
relocated into the runtime stage and put first on `PATH`, and `libsodium23` is
installed so the worktree-lease Ed25519 gate (PCO-024) verifies. This lets a
contained seat self-run the validator preflight and self-push instead of
stranding finished work. This mirrors how `deploy/oci/Dockerfile` consumes
`validators/**` from the repo root.

## Detached launch (canonical)

The canonical way to drive a contained VPS seat is a detached, named-persistent
launch. Detached is the default; `--detach` is accepted as an explicit no-op:

```bash
CE_VPS_REPO="$PWD" deploy/vps-runsc/run-vps-runsc.sh tui
```

Detached mode runs `docker run -d --name <name>` instead of `docker run --rm`:

- The container name is harness-aware and deterministic:
  `CE_VPS_CONTAINER_NAME=ce-vps-<harness>` (so `ce-vps-codex`, `ce-vps-claude`,
  `ce-vps-controller`), overridable via the `CE_VPS_CONTAINER_NAME` env.
- It is deliberately **not** `--rm`. A detached seat is named-persistent so a
  crashed or stopped seat stays inspectable (`docker logs <name>`, exit code).
  An earlier live outage was worsened because `--rm` deleted forensic state on
  exit. Foreground mode keeps `--rm` unchanged.
- All posture invariants (`--runtime`, `--network=host`,
  `--security-opt=no-new-privileges`, `--cap-drop=ALL`, `--user`, every mount
  and non-credential env, the generated contained config) are identical to
  foreground mode.
- Detached mode does not allocate a container-level TTY by default. The herdr
  server creates the in-container PTY used by the harness, so `docker run -d`
  is enough. Set `CE_VPS_TTY_FLAGS=-t` only for an operator-directed diagnostic
  that proves the image entrypoint needs a Docker TTY.
- Legacy foreground mode is available only via `--foreground` or
  `CE_VPS_FOREGROUND=1`; it keeps `docker run --rm` and defaults to `-it`.

After `docker run -d` returns, the launcher polls
`docker exec <name> herdr pane list` against the container-local socket in a
bounded loop (up to ~60 tries, 0.5s apart). If herdr never responds it fails
loudly, naming the container and printing the teardown command. On success it
prints the attach hint and the retire command.

The **canonical drive path** is then to attach to herdr:

```bash
docker exec -it ce-vps-codex herdr
```

No host tmux is part of that path. To verify herdr drive without tmux:

```bash
command -v tmux >/dev/null && echo "tmux present but unused" || echo "tmux absent OK"
CE_VPS_REPO="$PWD" deploy/vps-runsc/run-vps-runsc.sh tui
docker exec --env HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock ce-vps-codex herdr pane list
docker exec --env HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock ce-vps-codex herdr pane read w1:p1
docker exec --env HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock ce-vps-codex herdr pane send w1:p1 $'printf detached-herdr-ok\\n\\n'
```

In workspaces where Docker/runsc/herdr are unavailable, the deterministic
verification is the dry-run argv plus unit coverage:

```bash
CE_VPS_DRY_RUN=1 deploy/vps-runsc/run-vps-runsc.sh tui
PYTHONPATH=validators python -m pytest validators/tests/unit/test_vps_runsc_launcher.py
```

Expected dry-run evidence: `docker run -d --name ce-vps-codex`, no `--rm`, no
container `-t` unless `CE_VPS_TTY_FLAGS` is explicitly set, and no host `tmux`
probe in the launcher.

Retire the seat when done:

```bash
docker stop ce-vps-codex && docker rm ce-vps-codex
```

Detached launch performs an idempotent pre-launch `docker rm -f <name>` for
the exact `CE_VPS_CONTAINER_NAME` immediately before `docker run -d --name`.
This clears a stale stopped or wedged copy of that one seat without touching
other containers. The governed destructive and readiness commands target that
exact name only; they do not select containers by image or image ancestor.

To bound stopped-container buildup from one-off diagnostics, install the tracked
host cron artifact:

```bash
sudo install -m 0644 deploy/vps-runsc/ce-docker-prune.cron /etc/cron.d/ce-docker-prune
```

The cron runs `docker container prune -f --filter "until=24h"` hourly. Docker
container prune removes only stopped/exited containers, never running seats; the
24h grace keeps recent crash/exit evidence available before cleanup.

The generated contained Codex config pre-trusts `/workspace/creator-engine`
(`trust_level = "trusted"`, `approval_policy = "never"`,
`sandbox_mode = "danger-full-access"`), so a detached, non-interactive launch is
fully self-trusting: Codex never prompts and never tries to persist trust into
the readonly config mount. Codex must run with `danger-full-access`/bypass
because its inner bubblewrap/Landlock sandbox cannot nest inside runsc/gVisor;
the gVisor container is the sandbox boundary.

The generated config is staged under the durable seat log root by default:
`${CE_VPS_SEAT_LOG_DIR}/launcher/codex-config.toml`, avoiding host `/tmp` so
stopped containers remain restartable after tmpfiles cleanup. Operators may
override the path for tests or diagnostics; production overrides should stay on
durable host storage.

> **tmux is DEPRECATED/legacy** for driving these seats. The herdr pane via
> `docker exec -it <name> herdr` is the supported attach surface.

## Operations

VPS contained seats need host Docker access before launch. Add the seat user to
the Docker group so new shells inherit the group membership:

```bash
sudo usermod -aG docker <seat-user>
```

Stage a clean home before launching the contained TUI:

```bash
deploy/vps-runsc/run-vps-runsc.sh tui
```

The generated contained config must pre-trust `/workspace/creator-engine` and
set the model and effort. The readonly config overlay shadows the home config
inside the container, so these values must be present in the generated config;
the launcher fix for this is tracked in PR 401.

After launch, the containment probe should report `backend=gvisor` and
`contained=true`. A reported `ns:net:host` value is the documented
`--network=host` egress gap for this recipe; the probe is now fail-closed for
unexpected containment state per PR 402.

For in-box exec acceptance, run `git log` inside the box. It should succeed and
confirms the `danger-full-access` sandbox fix for nested execution under runsc.

Contained seats are currently commit-only. They can create commits, but cannot
submit PR reviews yet.

## Contained Codex Config

The launcher generates a per-seat contained Codex config and bind-mounts it over
`${CODEX_HOME}/config.toml` inside the container:

```toml
model = "gpt-5.6-terra"
model_reasoning_effort = "high"
approval_policy = "never"
sandbox_mode = "danger-full-access"

[projects."/workspace/creator-engine"]
trust_level = "trusted"
```

This is deliberate for the VPS runsc recipe. Codex' default
`workspace-write` mode starts an inner sandbox using bubblewrap/Landlock, and
nested bubblewrap or Landlock cannot run inside runsc/gVisor. The gVisor
container is the sandbox boundary for this recipe, so Codex runs in bypass mode
only inside that containment. Host auth stays in the mounted Codex home; the
contained config is generated separately and can be redirected with
`CE_VPS_CONTAINED_CODEX_CONFIG`. Production overrides should use durable host
storage rather than host `/tmp`.

## Durable Worktree Root

The launcher bind-mounts a host-disk worktree root into the container at
`/var/tmp` by default:

```text
CE_VPS_HOST_WORKTREE_ROOT=${CE_VPS_SEAT_LOG_DIR}/worktrees/<launch-id>
CE_VPS_CONTAINER_WORKTREE_ROOT=/var/tmp
```

This keeps `/var/tmp` unit worktrees on host disk instead of the runsc writable
overlay, so files remain inspectable from the host after sentry or container
death. Operators may override the host or container path. The host path must be
absolute; production overrides should not live under host `/tmp`.

## Codex Binary Mounts

The image installs `nodejs` and provides `/usr/local/bin/codex` as a wrapper for
mounted npm Codex packages. When `CE_VPS_CODEX_BIN` resolves to the common npm
layout:

```text
.../lib/node_modules/@openai/codex/bin/codex.js
```

the launcher mounts that package root read-only at
`/usr/local/lib/node_modules/@openai/codex`, so `/usr/local/bin/codex` can run
the real host package and its platform binary inside the container.

For standalone Codex bundles, leave `CE_VPS_CODEX_PACKAGE_ROOT` unset and point
`CE_VPS_CODEX_BIN` at the executable. The launcher then bind-mounts that binary
directly at `/usr/local/bin/codex`.

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

The VPS launcher does not pass `CLAUDE_CODE_OAUTH_TOKEN`, GitHub tokens,
OpenAI keys, Bao/OpenBao tokens, or other credential-bearing env names through
Docker `--env`/`-e` or the container env spec. Claude/controller auth through a
onecli transport-deputy handoff is follow-on scope; until that exists, the
contained launch remains tokenless at the container boundary.

## Runtime Registration

### Host Docker daemon prerequisites

Contained seats that bind-mount host broker sockets require the
`runsc-gvproxy-ptrace` runtime to allow host Unix-domain socket access. Persist
that requirement in `/etc/docker/daemon.json` so it survives host reprovision:

```json
{
  "runtimes": {
    "runsc-gvproxy-ptrace": {
      "path": "/usr/bin/runsc",
      "runtimeArgs": [
        "--platform=ptrace",
        "--host-uds=open"
      ]
    }
  }
}
```

Reload Docker after updating the daemon config:

```bash
sudo systemctl reload docker
```

Register a Docker runtime named `runsc-gvproxy-ptrace` on the VPS:

```json
{
  "runtimes": {
    "runsc-gvproxy-ptrace": {
      "path": "/usr/bin/runsc",
      "runtimeArgs": [
        "--platform=ptrace",
        "--host-uds=open"
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
`--user uid:gid`, the repo bind mount, the `.codex` bind mount, the contained
Codex config bind mount under the seat log root, the durable `/var/tmp`
worktree-root bind mount, a Codex binary or npm package-root bind mount, and
`CE_DGX_HARNESS=codex`. For `tui`, the image must be the final argv element; no
literal `tui` subcommand is passed to the entrypoint.

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
`CLAUDE_CODE_OAUTH_TOKEN`, `GH_TOKEN`, `GITHUB_TOKEN`, `OPENAI_API_KEY`,
`BAO_TOKEN`, `CE_DGX_HERDR_SOCKET_PATH`, raw `HERDR_SOCKET` carriers, or any
host socket bind mount. The herdr control socket path is substrate-internal and
resolved by the image entrypoint default only.

## Caveats

- Run the interactive form from a real TTY. For non-interactive callers, set
  `CE_VPS_TTY_FLAGS=-i` or use `CE_VPS_DRY_RUN=1`.
- VPS `--network=host` is a deliberate current-host compatibility choice, not
  egress confinement. Process containment is provided by `runsc`; egress
  mediation remains ce-ops#222 follow-on scope.
- The image must provide the herdr harness entrypoint. The launcher passes
  harness markers to that entrypoint; only exec launches pass an `exec`
  subcommand after the image.
- Config stays on the host and enters the container only through explicit
  non-secret mounts. Credential-bearing env forwarding is denied at launch; the
  image has Node plus a Codex package wrapper, but no baked Codex package,
  auth, or user config.
