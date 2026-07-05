# PR path manifest — no-ticket · Correct public onboarding command guidance

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-onboarding-docs-accuracy` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=c580ed29047a33ea10a55c63b49c5d698d4c4dc72a02357547e6ac7ddd050322

```text
.ce/changelog/ce-onboarding-docs-accuracy.md
.ce/pr-manifests/ce-onboarding-docs-accuracy.md
docs/contracts/brownfield-adoption.md
docs/contracts/plain-join.md
docs/guide/solo-dev-onboarding.md
docs/guide/welcome.md
docs/guide/zero-to-governed-seat-quickstart.md
validators/creator_engine_validator/public_docs_confidentiality.py
```
