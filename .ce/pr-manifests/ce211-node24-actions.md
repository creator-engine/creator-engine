# PR path manifest - ce211-node24-actions

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce211-node24-actions
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

- **Declared work class:** story

Scope:
ce-ops#211 maintenance update for GitHub Actions runtime deprecation warnings.
The PR only advances SHA-pinned `actions/checkout` and `actions/setup-python`
references to Node 24-capable upstream releases; it does not change workflow
triggers, job permissions, scripts, or validator behavior.

Per-file purpose:
- **`.ce/changelog/ce211-node24-actions.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce211-node24-actions.md`** *(A)* - this closed path-set carrier.
- **`.github/workflows/ce-ops-autoclose.yml`** *(M)* - update `actions/checkout` pin.
- **`.github/workflows/validate.yml`** *(M)* - update `actions/checkout` and `actions/setup-python` pins.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=da65e718de34cbbb9def44a80f63e319f159fa8a752d3444a6a2610b56efb71c

```text
.ce/changelog/ce211-node24-actions.md
.ce/pr-manifests/ce211-node24-actions.md
.github/workflows/ce-ops-autoclose.yml
.github/workflows/validate.yml
```
