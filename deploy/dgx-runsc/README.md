# DGX Codex Under runsc/gVisor

This directory authors the DGX-side container wrapper for running the Codex CLI
controller inside Docker with the `runsc` gVisor runtime. It is authoring only:
the Controller applies these steps on the DGX.

The nested DGX must not use the plain Docker networking path:

```bash
docker run --runtime=runsc --network=bridge ...
docker run --runtime=runsc --network=none ...
```

Both forms can hand `runsc` the DGX root network namespace and fail with
`cannot run with network enabled in root network namespace`. CE's own runner
does not rely on Docker bridge networking for this posture. It translates the
runtime policy to a gVisor plan whose Docker argv omits Docker networking flags.
The DGX Stage-1 `gvproxy`/`gvisor-tap-vsock` path provides routing/transport
only; it is not proof of per-policy allowlist egress confinement.

The first DGX pass confirmed that `runsc --platform=systrap --network=host`
fixes networking for a basic container, but Codex itself panics at startup in
Rust's alternate signal stack setup:

```text
failed to set up alternative stack guard page: Out of memory (os error 12)
```

That panic is raised after Rust allocates an alternate signal stack and calls
`mprotect(..., PROT_NONE)` on the guard page. For Codex on this DGX, prefer the
gVisor `ptrace` platform over `systrap`: it keeps the process contained by
`runsc` and preserves the working `gvproxy` egress route, while avoiding the
systrap signal/page-fault path that trips the Rust guard-page setup.

## Runner Network Model

The local runner evidence is in
`validators/creator_engine_validator/runner/gvisor_proxy_backend.py`:

- `translate_to_runsc_plan()` renders the same Docker shape used by
  `run-codex-runsc.sh`: `docker run --runtime=runsc-gvproxy-ptrace`.
- A policy with egress is still recorded as `network="proxy"` in the CE plan,
  but that is only the policy label; the rendered Docker argv omits
  `--network` by default.
- The plan renders `--security-opt=no-new-privileges`, `--cap-drop=ALL`, the
  seat `--user uid:gid`, the policy bind mounts, the host `CODEX_HOME` bind
  mount, the Codex binary bind mount, and the digest-pinned image reference.
- `SubprocessContainerRunner.egress_enforceable()` does not treat the DGX
  `gvproxy`/`runsc` route as allowlist enforcement. That route proves
  containment/routing only; a non-empty `egress_allowlist` must refuse unless a
  real allowlist enforcement primitive is proven.

The portable CE CLI/validator image lives in `deploy/oci`. It is not a
replacement for this herdr/Codex seat image; use it as a validator/preflight
payload under the same `runsc-gvproxy-ptrace` runtime when DGX evidence needs
the packaged `ce` and `creator-engine-validator` commands.

On the DGX, mirror that deployment shape by registering a dedicated Docker
runtime named `runsc-gvproxy-ptrace`. That runtime keeps the process under
`runsc`, uses `ptrace` for Codex compatibility, and tells `runsc` to use the DGX
host network stack. On this host, that stack is already the Stage-1
`gvproxy`/`gvisor-tap-vsock` egress route, not proof of per-policy allowlist
confinement. The wrapper does not pass Docker `--network` by default and refuses
the old plain `runsc` runtime unless the operator explicitly overrides it for
diagnostics.

## Apply Steps On The DGX

1. Confirm local prerequisites:

   ```bash
   command -v docker
   command -v runsc
   test -x /home/cedev4/.codex/packages/standalone/releases/0.141.0-aarch64-unknown-linux-musl/bin/codex
   test -f /home/cedev4/.codex/auth.json
   test -f /home/cedev4/.codex/config.toml
   ```

2. Register the dedicated `runsc-gvproxy-ptrace` Docker runtime:

   ```bash
   docker info --format '{{json .Runtimes}}' | grep -q '"runsc-gvproxy-ptrace"'
   ```

   If missing, merge this entry into `/etc/docker/daemon.json`:

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

   Then reload or restart Docker:

   ```bash
   sudo systemctl reload docker || sudo systemctl restart docker
   docker info --format '{{json .Runtimes}}' | grep -q '"runsc-gvproxy-ptrace"'
   ```

3. Build the seat-matched image from the repo root:

   ```bash
   cd /path/to/creator-engine
   docker build \
     -f deploy/dgx-runsc/Dockerfile \
     -t creator-engine/codex-runsc:0.141.0-aarch64 \
     --build-arg CE_DGX_USER="$(id -un)" \
     --build-arg CE_DGX_UID="$(id -u)" \
     --build-arg CE_DGX_GID="$(id -g)" \
     deploy/dgx-runsc
   ```

   The image builds `herdr` from the pinned herdr-ce source revision in a
   Debian bookworm builder stage and copies that binary into the matching
   bookworm runtime image. Do not stage or copy a host-built `herdr` binary
   into the image; host glibc drift is intentionally excluded from this path.

4. Verify the runtime is actually `runsc` and HTTPS egress follows the DGX
   `gvproxy`/`gvisor-tap-vsock` path:

   ```bash
   docker run --rm --runtime=runsc-gvproxy-ptrace \
     creator-engine/codex-runsc:0.141.0-aarch64 \
     sh -lc 'cat /proc/version; git ls-remote https://github.com/github/gitignore.git HEAD >/dev/null'
   ```

   If this fails with the root-netns error, stop and re-check that Docker is
   using the `runsc-gvproxy-ptrace` runtime and that the runtime has
   `--network=host` in `runtimeArgs`.

5. Check the runner arguments without launching Codex:

   ```bash
   CE_DGX_DRY_RUN=1 \
     CE_DGX_REPO="$PWD" \
     ./deploy/dgx-runsc/run-codex-runsc.sh exec "print working tree status"
   ```

   The printed argv must include `docker run`, `--runtime=runsc-gvproxy-ptrace`, the
   repo bind mount, the `.codex` bind mount, the Codex binary bind mount, and
   the image followed by `exec`. It must include a runtime-owned tmpfs at
   `/run/creator-engine` for herdr substrate state. It must not include a Docker
   `--network=` flag, a raw `HERDR_SOCKET_PATH=` container env, or a host bind
   mount under `/run/creator-engine/herdr`. The launcher passes
   `CE_DGX_HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock` only as
   entrypoint configuration; the entrypoint uses `HERDR_SOCKET_PATH` privately
   for `herdr` CLI calls and starts the governed harness with a clean explicit
   environment that excludes raw and CE_DGX-prefixed socket carriers.

   To expose the contained-seat SELF-PUSH broker, set only the per-seat host Unix
   socket and the explicit broker seat id:

   ```bash
   CE_DGX_EGRESS_BROKER_SOCKET=/run/user/$UID/creator-engine/egress-broker/dev-4.sock \
   CE_DGX_SEAT_ID=dev-4 \
   CE_DGX_DRY_RUN=1 \
     CE_DGX_REPO="$PWD" \
     ./deploy/dgx-runsc/run-codex-runsc.sh exec "print broker env"
   ```

   The dry-run argv must include a bind mount from that host socket to
   `/run/ce-egress-broker.sock`, plus `CE_EGRESS_BROKER_SOCKET=/run/ce-egress-broker.sock`
   and `CE_SEAT_ID=dev-4`. It must not include `CE_DGX_EGRESS_BROKER_SOCKET` as a container
   env, GitHub/OpenBao tokens, App keys, SSH agent sockets, Docker sockets, or the host broker
   config path.

   The launcher also fails closed if any contained Docker argv/spec attempts to
   pass credential-bearing env names or values such as `GH_TOKEN`,
   `GITHUB_TOKEN`, `CLAUDE_CODE_OAUTH_TOKEN`, `BAO_TOKEN`, or
   `OPENAI_API_KEY` via Docker `--env`/`-e`, opaque env files, or OCI
   `Config.Env`. Credential delivery to contained seats is broker/transport
   deputy work; onecli transport-deputy delivery is follow-on scope and is not
   implemented by this DGX launcher.

6. Start the interactive Codex TUI in the repo:

   ```bash
   CE_DGX_REPO="$PWD" ./deploy/dgx-runsc/run-codex-runsc.sh tui
   ```

7. Run the non-interactive `codex exec` form:

   ```bash
   CE_DGX_REPO="$PWD" \
     ./deploy/dgx-runsc/run-codex-runsc.sh exec "Summarize the current git status."
   ```

8. Dogfood the herdr terminalized launch and containment probe:

   ```bash
   docker build \
     -f deploy/dgx-runsc/Dockerfile \
     -t creator-engine/codex-runsc:0.141.0-aarch64 \
     --build-arg CE_DGX_USER="$(id -un)" \
     --build-arg CE_DGX_UID="$(id -u)" \
     --build-arg CE_DGX_GID="$(id -g)" \
     deploy/dgx-runsc

   CE_DGX_REPO="$PWD" \
     ./deploy/dgx-runsc/run-codex-runsc.sh exec "printf 'herdr runsc dogfood\n'; sleep 300"

   ce containment-probe <container-or-harness-pid> --json
   ```

   Expected probe result: JSON with `"contained": true` and
   `"backend": "gvisor"`. Expected terminal marker: the launcher dry-run and
   harness environment carry `CE_DGX_TERMINAL_KIND=herdr` /
   `CE_TERMINAL_KIND=herdr`.

## Detached launch (canonical)

The canonical way to drive a DGX Codex seat is a detached, named-persistent
container. Foreground `tui`/`exec` blocks the caller's terminal and uses
`docker run --rm`; detached mode instead runs `docker run -d`, names the
container deterministically, polls for herdr readiness, prints the
attach/teardown commands, and returns so the operator drives the seat through
herdr.

Launch detached with the flag or the env var:

```bash
CE_DGX_REPO="$PWD" ./deploy/dgx-runsc/run-codex-runsc.sh --detach tui
# or
CE_DGX_DETACH=1 CE_DGX_REPO="$PWD" ./deploy/dgx-runsc/run-codex-runsc.sh tui
```

What detached mode changes versus foreground:

- The docker argv drops `--rm` and adds `-d --name "${CE_DGX_CONTAINER_NAME}"`
  (default `ce-dgx-codex`, overridable via `CE_DGX_CONTAINER_NAME`). Every other
  posture invariant is unchanged: `--runtime`, `--security-opt=no-new-privileges`,
  `--cap-drop=ALL`, `--user`, `--workdir`, `--tmpfs`, all `--env`, all `--mount`,
  the TTY flags (`-it`, kept so the Codex TUI renders into the herdr pane), and
  the network-refusal logic.
- **Deliberate `--rm` decision:** detached containers are NOT removed with
  `--rm`. A crashed or stopped seat must stay inspectable — `docker logs` and the
  recorded exit code are the forensic record. A live outage was worsened because
  `--rm` deleted that state on exit. Foreground mode keeps `--rm` unchanged.
- **Readiness poll:** after `docker run -d` returns, the script polls
  `docker exec "${CE_DGX_CONTAINER_NAME}" herdr pane read w1:p1` in a bounded loop
  (up to ~60 tries, 0.5s apart). If herdr never responds, the script fails loudly,
  names the container, and prints the teardown command. The poll is skipped under
  `CE_DGX_DRY_RUN=1`.

Attach to the running seat (the canonical drive path):

```bash
docker exec -it ce-dgx-codex herdr
```

Retire the seat when done:

```bash
docker stop ce-dgx-codex && docker rm ce-dgx-codex
```

### Host-config pre-trust prerequisite (REQUIRED for detached)

This launcher bind-mounts the host `~/.codex` directory **read-write**
(`CE_DGX_CODEX_HOME`), so the host's own `config.toml` is the source of trust and
sandbox configuration. Unlike the VPS launcher, this script does NOT generate a
contained config and must NOT clobber the host one. For a detached,
non-interactive launch to avoid a trust-write loop, the operator must ensure the
host `~/.codex/config.toml` already pre-trusts the workspace before launching:

```toml
[projects."/workspace/creator-engine"]
trust_level = "trusted"

approval_policy = "never"
sandbox_mode = "danger-full-access"
```

Codex running inside gVisor MUST use `sandbox_mode = "danger-full-access"`
(bypass): the inner bubblewrap sandbox cannot nest inside gVisor, so attempting
to sandbox inside the container deadlocks the harness. gVisor IS the sandbox
boundary here. Without this pre-trust + bypass, a detached seat will block on a
trust/approval prompt that no one is attached to answer, and the readiness poll
will fail.

## Runner Defaults

The script is parameterized through environment variables:

```text
CE_DGX_IMAGE=creator-engine/codex-runsc:0.141.0-aarch64
CE_DGX_RUNTIME=runsc-gvproxy-ptrace
CE_DGX_DOCKER_NETWORK=
CE_DGX_REPO=$(pwd)
CE_DGX_CODEX_HOME=/home/cedev4/.codex
CE_DGX_CODEX_HOME_MODE=rw
CE_DGX_CODEX_BIN=/home/cedev4/.codex/packages/standalone/releases/0.141.0-aarch64-unknown-linux-musl/bin/codex
CE_DGX_HARNESS=codex
CE_DGX_HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock
CE_DGX_SUBSTRATE_RUN_DIR=/run/creator-engine
CE_DGX_TERMINAL_KIND=herdr
CE_DGX_TTY_FLAGS=-it
CE_DGX_DETACH=0
CE_DGX_CONTAINER_NAME=ce-dgx-codex
CE_DGX_EGRESS_BROKER_SOCKET=
CE_DGX_CONTAINER_EGRESS_BROKER_SOCKET=/run/ce-egress-broker.sock
```

`CE_DGX_NETWORK` remains as a deprecated alias for `CE_DGX_DOCKER_NETWORK`.
Leave both unset on the nested DGX. The wrapper refuses any Docker network value
unless `CE_DGX_ALLOW_DOCKER_NETWORK=1` is set for an operator-directed
diagnostic.

The wrapper also refuses `CE_DGX_RUNTIME=runsc-gvproxy` by default because that
name is the previously tested Systrap runtime that triggers Codex's Rust
guard-page panic. Set `CE_DGX_ALLOW_SYSTRAP_CODEX=1` only to rerun that failure
path intentionally.

`RUST_MIN_STACK` is not set by default. It changes the stack size for Rust
spawned threads; it does not disable Rust's alternate signal stack guard-page
setup, which is the panic observed on DGX. Docker memory flags are also not set
by default because this wrapper was not imposing a memory cap; adding a cap here
would be more likely to reduce available memory than fix the guard-page failure.

Set `CE_DGX_CODEX_HOME_MODE=ro` only after confirming Codex does not need to
write session state. The default is `rw` because the TUI commonly records local
session data under `~/.codex`.

## Contained SELF-PUSH Broker Socket

The wrapper can bind-mount one host-side ce-egress-broker Unix socket into the
container. This is intentionally narrow:

- `CE_DGX_EGRESS_BROKER_SOCKET` is the host socket source, for example
  `/run/user/$UID/creator-engine/egress-broker/dev-4.sock`.
- `CE_DGX_CONTAINER_EGRESS_BROKER_SOCKET` defaults to `/run/ce-egress-broker.sock`.
- When the broker socket is set, `CE_DGX_SEAT_ID` must be set explicitly to the
  `dev-N` broker seat id (`dev-4`, not the launcher default `ce-dgx-codex`).
- Non-dry-run launches preflight `[ -S "$CE_DGX_EGRESS_BROKER_SOCKET" ]` and fail closed if
  the host daemon socket is absent.
- The container receives only `CE_EGRESS_BROKER_SOCKET` and `CE_SEAT_ID`. The host socket env
  name, host broker config, GitHub tokens, App keys, OpenBao tokens, SSH agent, and Docker
  socket are not passed through.

The clean herdr harness environment propagates only `CE_EGRESS_BROKER_SOCKET` and
`CE_SEAT_ID` for this path. The host daemon owns `~/.ce-egress/broker.json`, the trusted host
repo path, the host signature trust store, and `/dev/shm/ce-devN` App PEMs.

Live SELF-PUSH smoke is a host-daemon apply path. Start the broker on the host,
then let the contained seat send only the value request over the mounted socket:

```bash
# host terminal
install -d -m 0700 "/run/user/$UID/creator-engine/egress-broker"
python tools/egress-broker/ce_egress_self_push_broker.py \
  --seat dev-4 \
  --socket "/run/user/$UID/creator-engine/egress-broker/dev-4.sock" \
  --host-repo-path "$PWD" \
  --config "$HOME/.ce-egress/broker.json"

# contained seat
python3 - <<'PY'
import json
import os
import socket

branch = "ce-ops-242-smoke"  # replace with the signed branch to publish
req = {"seat_id": os.environ["CE_SEAT_ID"], "branch": branch}
with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
    sock.connect(os.environ["CE_EGRESS_BROKER_SOCKET"])
    sock.sendall((json.dumps(req, separators=(",", ":")) + "\n").encode())
    print(sock.recv(65536).decode(), end="")
PY
```

The contained environment is intentionally zero-credential: it cannot run
`tools/egress-broker/ce_egress_broker.py --apply` itself because it has no
broker config, App key, mint token, SSH agent, Docker socket, or forge token.
Only the host daemon can perform the live apply.

## Validation Notes

Local authoring checks:

```bash
bash -n deploy/dgx-runsc/herdr-harness-entrypoint.sh
bash -n deploy/dgx-runsc/run-codex-runsc.sh
CE_DGX_DRY_RUN=1 deploy/dgx-runsc/run-codex-runsc.sh exec "hello" | grep -- '--runtime=runsc-gvproxy-ptrace'
! CE_DGX_DRY_RUN=1 deploy/dgx-runsc/run-codex-runsc.sh exec "hello" | grep -- '--network='
command -v hadolint >/dev/null && hadolint deploy/dgx-runsc/Dockerfile || true
```

DGX apply checks:

```bash
docker build -f deploy/dgx-runsc/Dockerfile -t creator-engine/codex-runsc:0.141.0-aarch64 deploy/dgx-runsc
docker run --rm --runtime=runsc-gvproxy-ptrace creator-engine/codex-runsc:0.141.0-aarch64 \
  sh -lc 'cat /proc/version; git ls-remote https://github.com/github/gitignore.git HEAD >/dev/null'
CE_DGX_REPO="$PWD" ./deploy/dgx-runsc/run-codex-runsc.sh --dry-run exec --version
CE_DGX_DRY_RUN=1 CE_DGX_REPO="$PWD" ./deploy/dgx-runsc/run-codex-runsc.sh tui
```

## Caveats

- The canonical launch is detached (`--detach` / `CE_DGX_DETACH=1`): the seat
  runs in a named-persistent container and the operator drives it through
  `docker exec -it ce-dgx-codex herdr`. Detached mode removes the need for tmux.
  **tmux is legacy/DEPRECATED** for this path; do not start the seat inside tmux.
- For the legacy foreground form, run from a real TTY. If a caller is
  non-interactive, set `CE_DGX_TTY_FLAGS=-i` or use the dry-run check.
- Do not use Docker bridge, Docker none, or the plain `runsc` runtime on the
  nested DGX. The `runsc-gvproxy-ptrace` runtime owns networking, and egress
  should prove out with the HTTPS `git ls-remote` check above.
- Keep the earlier `runsc-gvproxy` Systrap runtime only as a basic-container
  diagnostic. Codex should use `runsc-gvproxy-ptrace` unless the DGX test proves
  the Rust guard-page panic is fixed upstream; the wrapper requires
  `CE_DGX_ALLOW_SYSTRAP_CODEX=1` to use that old runtime.
- This wrapper does not grant GPU access and does not touch NVIDIA runtime
  plumbing. It is only for containing the Codex controller process.
- Auth and config stay on the host and enter the container only through the
  `~/.codex` bind mount. Do not copy them into the image.
- The repo mount is read-write by design so Codex can author files. The process
  runs as the seat UID/GID, not root.
