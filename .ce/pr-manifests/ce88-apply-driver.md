# PR path manifest - ce88-apply-driver - wire live forge apply driver seam

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce88-apply-driver
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Ratified:
Controller relay for ce-ops#88 on 2026-06-18: wire a production live-forge
`ApplyDriver` into `_onboard_apply_driver()` so existing-repo `onboard --apply`
can execute the brownfield adoption-apply join-PR flow when explicitly
authorized, while preserving fail-closed scanner/forge behavior.

Base:
`9152727` (`origin/main` at branch creation).

Per-file purpose (closed path-set - 6 paths):
- **`.ce/changelog/ce88-apply-driver.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce88-apply-driver.md`** *(A)* - this carrier.
- **`validators/creator_engine_validator/v3_cli.py`** *(M)* - makes `_onboard_apply_driver()` the context-aware production live-driver selector and routes apply/plan probes through it.
- **`validators/tests/unit/test_v3_cli.py`** *(M)* - TDD coverage that authorized brownfield apply obtains its adoption driver from the seam and that the seam returns the live adoption driver under dual authorization.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* - rebuilt app wheel from this branch source.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* - app-wheel digest re-pinned.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=a347b8764f49e05d9b657ac5d45538d0734400b34326e59bb8eb57e8c336459e

```text
.ce/changelog/ce88-apply-driver.md
.ce/pr-manifests/ce88-apply-driver.md
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_v3_cli.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
