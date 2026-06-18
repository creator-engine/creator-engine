# DGX Codex Under runsc/gVisor

This directory authors the DGX-side container wrapper for running the Codex CLI
controller inside Docker with the `runsc` gVisor runtime. It is authoring only:
the Controller applies these steps on the DGX.

The image contains only OS runtime basics: Debian slim, CA certificates for
HTTPS model API egress, `git` for repo inspection, and a non-root seat user.
It does not bake Codex auth, config, or the Codex binary. The runner bind-mounts
the repo, `~/.codex`, and the standalone Codex binary from the DGX host.

## Apply Steps On The DGX

1. Confirm local prerequisites:

   ```bash
   command -v docker
   command -v runsc
   test -x /home/cedev4/.codex/packages/standalone/releases/0.141.0-aarch64-unknown-linux-musl/bin/codex
   test -f /home/cedev4/.codex/auth.json
   test -f /home/cedev4/.codex/config.toml
   ```

2. Register `runsc` as a Docker runtime if Docker does not already list it:

   ```bash
   docker info --format '{{json .Runtimes}}' | grep -q '"runsc"'
   ```

   If missing, merge this entry into `/etc/docker/daemon.json`:

   ```json
   {
     "runtimes": {
       "runsc": {
         "path": "/usr/bin/runsc"
       }
     }
   }
   ```

   Then reload or restart Docker:

   ```bash
   sudo systemctl reload docker || sudo systemctl restart docker
   docker info --format '{{json .Runtimes}}' | grep -q '"runsc"'
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

4. Verify the runtime is actually `runsc`:

   ```bash
   docker run --rm --runtime=runsc creator-engine/codex-runsc:0.141.0-aarch64 uname -a
   docker run --rm --runtime=runsc creator-engine/codex-runsc:0.141.0-aarch64 \
     sh -lc 'cat /proc/version; (dmesg 2>/dev/null || true) | head -40'
   ```

   Confirm the output shows the gVisor/runsc kernel signature, commonly via
   `gVisor` in `dmesg` or a gVisor-style `/proc/version`/kernel string. If the
   signature is absent, stop and re-check Docker runtime registration.

5. Check the runner arguments without launching Codex:

   ```bash
   CE_DGX_DRY_RUN=1 \
     CE_DGX_REPO="$PWD" \
     ./deploy/dgx-runsc/run-codex-runsc.sh exec "print working tree status"
   ```

   The printed argv must include `docker run`, `--runtime=runsc`, the repo bind
   mount, the `.codex` bind mount, the Codex binary bind mount, and `codex exec`.

6. Start the interactive Codex TUI in the repo:

   ```bash
   CE_DGX_REPO="$PWD" ./deploy/dgx-runsc/run-codex-runsc.sh tui
   ```

7. Run the non-interactive `codex exec` form:

   ```bash
   CE_DGX_REPO="$PWD" \
     ./deploy/dgx-runsc/run-codex-runsc.sh exec "Summarize the current git status."
   ```

## Runner Defaults

The script is parameterized through environment variables:

```text
CE_DGX_IMAGE=creator-engine/codex-runsc:0.141.0-aarch64
CE_DGX_RUNTIME=runsc
CE_DGX_NETWORK=bridge
CE_DGX_REPO=$(pwd)
CE_DGX_CODEX_HOME=/home/cedev4/.codex
CE_DGX_CODEX_HOME_MODE=rw
CE_DGX_CODEX_BIN=/home/cedev4/.codex/packages/standalone/releases/0.141.0-aarch64-unknown-linux-musl/bin/codex
CE_DGX_TTY_FLAGS=-it
```

Set `CE_DGX_CODEX_HOME_MODE=ro` only after confirming Codex does not need to
write session state. The default is `rw` because the TUI commonly records local
session data under `~/.codex`.

## Validation Notes

Local authoring checks:

```bash
bash -n deploy/dgx-runsc/run-codex-runsc.sh
CE_DGX_DRY_RUN=1 deploy/dgx-runsc/run-codex-runsc.sh exec "hello" | grep -- '--runtime=runsc'
command -v hadolint >/dev/null && hadolint deploy/dgx-runsc/Dockerfile || true
```

DGX apply checks:

```bash
docker build -f deploy/dgx-runsc/Dockerfile -t creator-engine/codex-runsc:0.141.0-aarch64 deploy/dgx-runsc
docker run --rm --runtime=runsc creator-engine/codex-runsc:0.141.0-aarch64 uname -a
CE_DGX_DRY_RUN=1 CE_DGX_REPO="$PWD" ./deploy/dgx-runsc/run-codex-runsc.sh tui
```

## Caveats

- Run the interactive form from a real TTY, including inside tmux. If a caller
  is non-interactive, set `CE_DGX_TTY_FLAGS=-i` or use the dry-run check.
- Docker bridge networking must allow HTTPS egress to the model API. If egress
  fails, inspect Docker networking and any `gvproxy`/host firewall policy.
- This wrapper does not grant GPU access and does not touch NVIDIA runtime
  plumbing. It is only for containing the Codex controller process.
- Auth and config stay on the host and enter the container only through the
  `~/.codex` bind mount. Do not copy them into the image.
- The repo mount is read-write by design so Codex can author files. The process
  runs as the seat UID/GID, not root.
