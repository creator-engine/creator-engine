# PR path manifest - ce217-ulauncher-herdr-runsc - U-LAUNCHER herdr runsc

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce217-ulauncher-herdr-runsc
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. The carrier lists itself.

Ratified gate:
ce-ops#217 U-LAUNCHER herdr runsc dogfood path. The container owns the herdr
server/socket substrate; the governed harness runs inside a herdr root pane and
does not receive the raw `HERDR_SOCKET_PATH` carrier.

The change:
Add a DGX runsc herdr harness entrypoint, bake it and a staged herdr binary into
the Codex runsc image, route Codex and Controller launchers through the image
entrypoint with narrow harness-selection env, document exact dogfood commands,
and add focused dry-run/static tests.

Per-file purpose (the closed path-set - 10 paths):
- **`.ce/changelog/ce217-ulauncher-herdr-runsc.md`** *(A)* - per-PR changelog fragment.
- **`.ce/pr-manifests/ce217-ulauncher-herdr-runsc.md`** *(A)* - this carrier (self-inclusive).
- **`deploy/dgx-controller-runsc/README.md`** *(M)* - documents the Controller variant reusing the shared herdr entrypoint image with a Claude binary mount.
- **`deploy/dgx-controller-runsc/run-controller-runsc.sh`** *(M)* - selects the Claude harness through image-default entrypoint env/args without exposing a host herdr socket.
- **`deploy/dgx-runsc/Dockerfile`** *(M)* - installs entrypoint dependencies, copies staged `herdr` and the entrypoint, pre-creates the socket dir, and runs through `tini`.
- **`deploy/dgx-runsc/README.md`** *(M)* - documents herdr staging, Docker build, launcher, dry-run, and containment-probe dogfood commands.
- **`deploy/dgx-runsc/herdr-harness-entrypoint.sh`** *(A)* - fail-closed in-container herdr server/workspace/root-pane harness launcher.
- **`deploy/dgx-runsc/run-codex-runsc.sh`** *(M)* - selects the Codex harness through image-default entrypoint env/args without exposing a host herdr socket.
- **`validators/tests/unit/test_dgx_controller_runsc.py`** *(M)* - updates Controller dry-run expectations for the herdr image-entrypoint shape.
- **`validators/tests/unit/test_dgx_runsc.py`** *(A)* - adds Codex dry-run, Dockerfile, and entrypoint contract coverage.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=10

AUTHORIZED_PATHS_SHA256=cd184adb5831228f311aa2a2c262be31a3832d1940aa770d62b50e3872124a0f

```text
.ce/changelog/ce217-ulauncher-herdr-runsc.md
.ce/pr-manifests/ce217-ulauncher-herdr-runsc.md
deploy/dgx-controller-runsc/README.md
deploy/dgx-controller-runsc/run-controller-runsc.sh
deploy/dgx-runsc/Dockerfile
deploy/dgx-runsc/README.md
deploy/dgx-runsc/herdr-harness-entrypoint.sh
deploy/dgx-runsc/run-codex-runsc.sh
validators/tests/unit/test_dgx_controller_runsc.py
validators/tests/unit/test_dgx_runsc.py
```
