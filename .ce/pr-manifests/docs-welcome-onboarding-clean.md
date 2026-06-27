# PR path manifest — ce-ops#321 · Welcome / onboarding front-door package (zero-to-productive for users + collaborators)

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref docs-welcome-onboarding-clean` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=2e4c53048d875447f7be0a28826792c053b4e452bc30a69267f43e1080feff5d

```text
.ce/changelog/docs-welcome-onboarding-clean.md
.ce/pr-manifests/docs-welcome-onboarding-clean.md
README.md
docs/guide/pilot-runbook.md
docs/guide/understanding-ce.md
docs/guide/welcome.md
```
