# PR path manifest — ce-ops#249 · redact live-infra identifiers from public repo

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce249-redact-live-infra` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=22

AUTHORIZED_PATHS_SHA256=ef64bbce2aae93b1cf653cbb18a3ab8fab6889313f0c3d597286a389c03f40a6

```text
.ce/changelog/ce113-openbao-golive.md
.ce/changelog/ce133-adr0006-design.md
.ce/changelog/ce249-redact-live-infra.md
.ce/changelog/v35-roadmap-plan.md
.ce/pr-manifests/ce113-openbao-golive.md
.ce/pr-manifests/ce249-redact-live-infra.md
.ce/pr-manifests/g2f-spawn-hardening.md
.ce/pr-manifests/v35-roadmap-plan.md
docs/architecture/ADR-0006-derived-artifacts-out-of-trust-path.md
docs/architecture/README.md
docs/decisions/0005-openbao-secret-identity-backend.md
docs/decisions/ADR-0007-egress-gateway-publish-broker.md
docs/decisions/ADR-0008-web-control-ui.md
docs/devops/openbao-approval-wall-arming.md
docs/devops/openbao-operator-bringup.md
docs/devops/openbao-production-golive.md
docs/devops/openbao/provision-openbao.sh
docs/index.html
site-archive/README.md
site-archive/index-v8-2-roadmap-card-removal.html
validators/tests/unit/fixtures/ce88_live_forge/CAPTURE.md
validators/tests/unit/test_public_docs_confidentiality.py
```
