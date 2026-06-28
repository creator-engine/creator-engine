# PR path manifest — confidentiality-burndown · Public confidentiality burndown

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-confidentiality-burndown` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=11

AUTHORIZED_PATHS_SHA256=3092de6a2e8489172b34f69388a6b0a21cdae8bb1bad3d709059a6691ce75ede

```text
.ce/changelog/ce-confidentiality-burndown.md
.ce/pr-manifests/ce-confidentiality-burndown.md
docs/design/controller-bootstrap-injection.md
docs/keys/ce-root-v1
docs/security/trust-anchors.md
validators/creator_engine_validator/public_docs_confidentiality.py
validators/creator_engine_validator/v3_cli.py
validators/examples/reviewer-authority-envelope/invalid-missing-binding.ce.yml
validators/examples/reviewer-authority-envelope/invalid-secret-value.ce.yml
validators/examples/reviewer-authority-envelope/invalid-unknown-mechanic.ce.yml
validators/examples/reviewer-authority-envelope/valid-pr-review-authority.ce.yml
```
