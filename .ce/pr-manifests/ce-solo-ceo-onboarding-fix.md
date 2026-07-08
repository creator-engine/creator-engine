# PR path manifest -- ce-solo-ceo-onboarding-fix

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs `verify-path-manifest --base <sha>
--manifest-dir .ce/pr-manifests --head-ref ce-solo-ceo-onboarding-fix` and
requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=07882f78b44b0fa36a94128646e7ee40c00789f33dbaebca685f4ef7c017054e

```text
.ce/changelog/ce-solo-ceo-onboarding-fix.md
.ce/pr-manifests/ce-solo-ceo-onboarding-fix.md
docs/guide/solo-ceo-onboarding.html
docs/guide/solo-ceo-onboarding.md
```
