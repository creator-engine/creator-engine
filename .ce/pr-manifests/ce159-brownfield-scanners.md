# PR path manifest - ce159-brownfield-scanners

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce159-brownfield-scanners
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Scope:
ce-ops#159 brownfield scanner provisioning: Gitleaks and TruffleHog are
sha256-pinned from reproduced upstream release archives and the live adoption
driver extracts/runs only verified scanner binaries.

Base:
`d6ba7ee291c882aa865af7e0e32972b3223b5532` (`origin/main` after #291).

Per-file purpose (closed path-set - 7 paths):

- **`.ce/changelog/ce159-brownfield-scanners.md`** *(A)* - per-change changelog fragment.
- **`.ce/pr-manifests/ce159-brownfield-scanners.md`** *(A)* - this PR's closed path-set carrier.
- **`docs/downloads/0.2.0/scanners/scanner-mirror.fragment.yaml`** *(M)* - scanner manifest fragment now records release archive URLs, sha256 pins, and archive members.
- **`validators/creator_engine_validator/onboard_apply_live.py`** *(M)* - built-in scanner pins plus archive verification/extraction before execution.
- **`validators/tests/unit/test_onboard_apply_live.py`** *(M)* - scanner pin shape, default population, manifest parity, archive run, and hash-mismatch tests.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* - refreshed digest for the rebuilt validator app wheel.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* - rebuilt app wheel for source parity.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=721cbe1e4fbaaf4a034419fa439f6422766bfd6a2cb5cabf1d80947ad79cf86a

```text
.ce/changelog/ce159-brownfield-scanners.md
.ce/pr-manifests/ce159-brownfield-scanners.md
docs/downloads/0.2.0/scanners/scanner-mirror.fragment.yaml
validators/creator_engine_validator/onboard_apply_live.py
validators/tests/unit/test_onboard_apply_live.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
