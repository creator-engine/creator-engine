# PR path manifest — ce-ops#351 · queue-daemon launcher arg-parity fix

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-351-launcher-argparity
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below
(the carrier lists itself); the repo-wide fidelity scan requires the declared count and
SHA256 to match the fenced block.

The change (config/infra): wires the missing `--approval-wall-secret-ref-policy-sha` arg
in the queue-daemon relocation launcher, adds it to the required-env validation block, the
usage/help text, and the RELOCATION.md required-keys runbook section. No code logic change.

Per-file purpose (closed path-set — 4 paths):
- **`.ce/changelog/ce-351-launcher-argparity.md`** *(A)* — changelog fragment.
- **`.ce/pr-manifests/ce-351-launcher-argparity.md`** *(A)* — this carrier (self-inclusive).
- **`deploy/queue-daemon/RELOCATION.md`** *(M)* — adds `CE_APPROVAL_WALL_SECRET_REF_POLICY_SHA` to required-keys list.
- **`deploy/queue-daemon/launch-queue-daemon.sh`** *(M)* — adds missing arg + env var.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=4007ec9c8e8a0a08e81c3a85dead141fb764cd420395cc39e3c4c426922f654a

```text
.ce/changelog/ce-351-launcher-argparity.md
.ce/pr-manifests/ce-351-launcher-argparity.md
deploy/queue-daemon/RELOCATION.md
deploy/queue-daemon/launch-queue-daemon.sh
```
