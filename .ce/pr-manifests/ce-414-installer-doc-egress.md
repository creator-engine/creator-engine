# PR path manifest — creator-engine/ce-ops#414 · installer docs: version-symbolic release paths and egress allowlist

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-414-installer-doc-egress` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=7e7ab422a78db8a25d334ae7f7cc295bc85cc7a6e9b218498771b37f1440cce4

```text
.ce/changelog/ce-414-installer-doc-egress.md
.ce/pr-manifests/ce-414-installer-doc-egress.md
docs/contracts/installer.md
docs/guide/pilot-runbook.md
validators/creator_engine_validator/public_docs_confidentiality.py
```
