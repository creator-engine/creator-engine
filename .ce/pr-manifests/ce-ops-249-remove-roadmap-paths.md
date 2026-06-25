# PR path manifest — ce-ops#249 · fully remove internal roadmap paths from public repo

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-ops-249-remove-roadmap-paths` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=18

AUTHORIZED_PATHS_SHA256=da459bfe716c78cd766500ed4b59064e9b9829a67800770584a83faf153e3542

```text
.ce/changelog/ce-ops-249-remove-roadmap-paths.md
.ce/pr-manifests/ce-ops-249-remove-roadmap-paths.md
README.md
docs/architecture/README.md
docs/architecture/cockpit.md
docs/architecture/pilot-deployment-transport.md
docs/architecture/pilot-roadmap.md
docs/architecture/pilot-uiux-model.md
docs/architecture/session-status-line.md
docs/architecture/shaping-ux.md
docs/architecture/stage-vocabulary.md
docs/guide/pilot-runbook.md
docs/index.html
docs/v3-roadmap.md
docs/v3.5-roadmap.md
site-archive/README.md
site-archive/index-v8-1-full-automation-headline.html
validators/tests/unit/test_site_index_docs_nav.py
```
