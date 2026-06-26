# PR path manifest - ce256-retire-tmux-detached-seat-launch

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce256-retire-tmux-detached-seat-launch --require-carrier
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

- **Declared work class:** feature

Scope:
ce-ops#256 retires the host-tmux anchor from Codex seat launch by making the
VPS and DGX runsc launchers default to detached Docker containers, retaining
foreground mode only as an explicit migration path, adding a systemd seat
container template, and documenting deterministic herdr verification without
host tmux.

Per-file purpose:
- **`.ce/changelog/ce256-retire-tmux-detached-seat-launch.md`** *(A)* -
  changelog fragment.
- **`.ce/pr-manifests/ce256-retire-tmux-detached-seat-launch.md`** *(A)* -
  this closed path-set carrier.
- **`deploy/dgx-runsc/README.md`** *(M)* - documents default detached launch,
  explicit foreground mode, no container TTY default, and no-tmux herdr
  verification.
- **`deploy/dgx-runsc/run-codex-runsc.sh`** *(M)* - defaults to detached
  launch, adds `--foreground`, removes implicit detached TTY allocation, and
  supports Docker restart policy.
- **`deploy/systemd/README.md`** *(M)* - documents the Codex seat systemd
  template and env-file examples.
- **`deploy/systemd/ce-codex-seat@.service`** *(A)* - detached Codex seat
  systemd template using the launcher and Docker restart policy.
- **`deploy/vps-runsc/README.md`** *(M)* - documents default detached launch,
  explicit foreground mode, no container TTY default, and no-tmux herdr
  verification.
- **`deploy/vps-runsc/run-vps-runsc.sh`** *(M)* - defaults to detached launch,
  adds `--foreground`, removes implicit detached TTY allocation, and supports
  Docker restart policy.
- **`validators/tests/unit/test_dgx_runsc.py`** *(M)* - covers DGX detached
  default, foreground migration, restart policy, explicit TTY override, and no
  host-tmux launcher dependency.
- **`validators/tests/unit/test_gate_daemons_systemd.py`** *(M)* - covers the
  detached Codex seat systemd template.
- **`validators/tests/unit/test_vps_runsc_launcher.py`** *(M)* - covers VPS
  detached default, foreground migration, restart policy, explicit TTY override,
  and no host-tmux launcher dependency.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=11

AUTHORIZED_PATHS_SHA256=7db23b21d79da40f18c7e5c89df4eb44cd806fbc2de44e9cdc88ba2e5baa6dc4

```text
.ce/changelog/ce256-retire-tmux-detached-seat-launch.md
.ce/pr-manifests/ce256-retire-tmux-detached-seat-launch.md
deploy/dgx-runsc/README.md
deploy/dgx-runsc/run-codex-runsc.sh
deploy/systemd/README.md
deploy/systemd/ce-codex-seat@.service
deploy/vps-runsc/README.md
deploy/vps-runsc/run-vps-runsc.sh
validators/tests/unit/test_dgx_runsc.py
validators/tests/unit/test_gate_daemons_systemd.py
validators/tests/unit/test_vps_runsc_launcher.py
```
