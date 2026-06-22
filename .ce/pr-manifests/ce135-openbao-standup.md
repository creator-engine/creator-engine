# PR path manifest - ce135-openbao-standup - OpenBao micro-unit stand-up

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce135-openbao-standup
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. The carrier lists itself.

Scope:
Design-only OpenBao micro-unit stand-up for ce-ops#135 / ce-ops#113 plus a
minimal compatibility implementation for existing host-local secret references
behind the already-landed `SecretIdentityBackend` seam. No live OpenBao deploy,
server start, secret migration, runtime caller wiring, schema change, wheel
rebuild, push, or PR open is authorized.

Per-file purpose (closed path-set - 5 paths):
- **`.ce/changelog/ce135-openbao-standup.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce135-openbao-standup.md`** *(A)* - this closed carrier.
- **`docs/decisions/ADR-0012-openbao-micro-unit-standup.md`** *(A)* - proposed design ADR.
- **`validators/creator_engine_validator/secret_identity.py`** *(M)* - local compatibility backend behind the existing protocol.
- **`validators/tests/unit/test_secret_identity.py`** *(M)* - focused offline unit tests for the local backend.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=9e8d1c626edb367d7d7b1b8cfe5152582874c38e5ef54524e29dbee4c1bee5a9

```text
.ce/changelog/ce135-openbao-standup.md
.ce/pr-manifests/ce135-openbao-standup.md
docs/decisions/ADR-0012-openbao-micro-unit-standup.md
validators/creator_engine_validator/secret_identity.py
validators/tests/unit/test_secret_identity.py
```
