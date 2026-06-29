# PR path manifest — ce-ops#358 · Fix installer uv trust boundary

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-358-installer-trust-fixes` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=364ab9d35603930f9d32218a8b0d109275b9dd95f3df3313dec654c709b942b9

```text
.ce/changelog/ce-358-installer-trust-fixes.md
.ce/pr-manifests/ce-358-installer-trust-fixes.md
docs/downloads/0.2.0/SHA256SUMS
docs/downloads/0.2.0/install.sh
docs/downloads/0.3.0/SHA256SUMS
docs/downloads/0.3.0/install.sh
docs/install.sh
docs/llms-install.md
validators/tests/integration/test_install_bootstrap.py
```
