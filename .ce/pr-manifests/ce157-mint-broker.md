# PR Path Manifest - ce157-mint-broker

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce157-mint-broker
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Scope:
ce-ops#157 shared-App mint broker repair for PR #351. Enforce the advertised
per-user mint rate cap/window in the broker request handler, add focused unit
coverage, and add the required governance artifacts. Rebase conflict
resolution preserves `main`'s repository-aware binding behavior and
no-committed-first-party-wheel posture.

Base:
`7e6a0d743947c84601a565a5dc83dc61ade99800` (`origin/main` at repair).

Per-file purpose (closed path-set - 4 paths):
- **`.ce/changelog/ce157-mint-broker.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce157-mint-broker.md`** *(A)* - this carrier.
- **`tools/mint-broker/mint_broker/service.py`** *(M)* - enforce the configured per-user mint rate guard before binding/minting.
- **`validators/tests/unit/test_mint_broker_service.py`** *(M)* - cover over-cap refusal, per-caller isolation, and window expiry.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=e0f09d0c482691aa8f2ef2134ce3d47852b3251cc14f2a4201cad675eec5af0b

```text
.ce/changelog/ce157-mint-broker.md
.ce/pr-manifests/ce157-mint-broker.md
tools/mint-broker/mint_broker/service.py
validators/tests/unit/test_mint_broker_service.py
```
