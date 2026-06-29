# Run Creator Engine on macOS with a Linux Container

Creator Engine does not ship a Mac-native installer today. The supported path
from macOS is to run CE inside a Linux container or VM and bind-mount your Mac
workspace into that Linux environment.

This guide is for a Mac user who wants a local CE session for solo development
without waiting for native macOS support. You need a container or VM runtime on
the Mac first. Docker Desktop works; Podman with Colima or another Linux-backed
runtime works too.

Use the native Linux architecture for your Mac:

| Mac | Container platform |
| --- | --- |
| Apple Silicon | `linux/arm64` |
| Intel Mac | `linux/amd64` |

## Why a Container Works

The CE installer gates on `uname`: it accepts `Linux/x86_64` or `Linux/amd64`
as `linux-x86_64-cp314`, and `Linux/aarch64` or `Linux/arm64` as
`linux-aarch64-cp314`. macOS reports `Darwin/<arch>` and falls through to the
installer's `unsupported_platform` refusal because there is no signed Darwin
wheelhouse.

A Linux container on macOS runs inside a Linux VM. From inside the container,
CE sees the Linux userspace and Linux kernel interface that its installer,
CPython 3.14 wheelhouse, and isolation path are built for. This is still a Linux
install; it is not a Mac-native CE build.

The public installer command is:

```bash
curl --proto '=https' --tlsv1.2 -fsSL https://creator-engine.dev/install.sh | bash
```

The agent-native install spec is published at
`https://creator-engine.dev/llms-install.md`.

## Start a Linux Container

Create a host directory for workspaces if you do not already have one:

```bash
mkdir -p "$HOME/ce-workspaces"
```

Start an Ubuntu container with a persistent CE install volume and a bind-mounted
workspace. Replace `linux/arm64` with `linux/amd64` on Intel Macs, and replace
`$HOME/path/to/your-repo` with the repo you want CE to work on.

```bash
docker run --rm -it \
  --platform linux/arm64 \
  --name ce-mac \
  -v ce-home:/root/.local/share/creator-engine \
  -v "$HOME/ce-workspaces:/workspace" \
  -v "$HOME/path/to/your-repo:/workspace/your-repo" \
  -w /workspace \
  ubuntu:24.04 \
  bash
```

With Podman, use the same shape if your runtime supports `--platform`:

```bash
podman run --rm -it \
  --platform linux/arm64 \
  --name ce-mac \
  -v ce-home:/root/.local/share/creator-engine \
  -v "$HOME/ce-workspaces:/workspace" \
  -v "$HOME/path/to/your-repo:/workspace/your-repo" \
  -w /workspace \
  ubuntu:24.04 \
  bash
```

The examples run as `root` inside the container so package installation is
straightforward. If you run as a non-root Linux user instead, mount the CE volume
at that user's `$HOME/.local/share/creator-engine`.

## Install CE Inside the Container

Inside the container, install the bootstrap tools the installer expects on a
Debian/Ubuntu base image:

```bash
apt-get update && apt-get install -y \
  ca-certificates curl git openssh-client tar coreutils sed gawk grep
```

Then run the CE installer inside the container:

```bash
curl --proto '=https' --tlsv1.2 -fsSL https://creator-engine.dev/install.sh | bash
```

After the installer completes, reload the user-local CLI path in the current
shell:

```bash
. ~/.profile && hash -r
```

The installer verifies the signed install spec before persistent mutation. It
then parses the signed manifest, downloads and verifies `SHA256SUMS` and the
answers schema, filters the required wheels for the Linux platform tag, stages a
wheelhouse, and installs `creator-engine-validator` offline with:

```text
pip install --no-index --find-links "$WHEELHOUSE_DIR" creator-engine-validator==<manifest version>
```

The default install state lives under:

```text
/root/.local/share/creator-engine/bootstrap
```

because the example container runs as `root` and mounts
`ce-home:/root/.local/share/creator-engine`.

## Bind-Mount Your Repo

The `docker run` example mounts your Mac repo here:

```text
/workspace/your-repo
```

That means edits CE makes inside `/workspace/your-repo` are edits to your Mac
working copy. Keep source code under bind-mounted workspace paths such as
`/workspace/your-repo`; keep CE's install/cache state on the named volume
`ce-home`.

For multiple projects, either mount a parent directory:

```bash
-v "$HOME/ce-workspaces:/workspace"
```

or add another repo-specific bind mount:

```bash
-v "$HOME/another-repo:/workspace/another-repo"
```

## Verify and Launch

From inside the container, confirm you are on the Linux platform CE supports:

```bash
uname -s
uname -m
```

Expected values are `Linux` plus one of `aarch64`, `arm64`, `x86_64`, or
`amd64`.

Confirm the CLIs are on `PATH`:

```bash
command -v ce
command -v cev3
ce --help
```

Then launch your CE session from the mounted repo:

```bash
cd /workspace/your-repo
ce launch
```

`ce hud` is documented as an alias for the same launcher. The full governed
pilot path also documents `cev3 session` after its plan/apply setup, but the
solo container path should start with the everyday `ce launch` flow.

## Caveats

- This is a container path only. Running the public installer directly in macOS
  Terminal reports `Darwin/<arch>` and refuses because CE has no signed
  Mac-native wheelhouse today.
- You need a Linux-backed runtime such as Docker Desktop, Podman, Colima, or a
  VM. If that runtime is stopped, CE in the container is stopped too.
- Use the native platform for your Mac. Running the wrong architecture through
  emulation can be much slower and may produce confusing package behavior.
- Allocate enough CPU, memory, and disk to the runtime VM. The CE install volume,
  Python runtime, verified artifacts, and project dependencies all consume space
  inside the runtime's storage.
- Bind-mounted files may use Mac-side ownership and permissions. If a tool
  inside the container cannot write a repo file, adjust the mount, user, or file
  ownership rather than reinstalling CE.
- Native macOS support is a later path. Do not treat this guide as evidence that
  CE ships a Mac-native build.
