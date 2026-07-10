# PR path manifest - ce-509-release-acceptance-design

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs `verify-path-manifest --base <sha>
--manifest-dir .ce/pr-manifests --head-ref ce-509-release-acceptance-design`
and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=6fdff353f45f5b74d085fca144ea588e573da58cbac773deace3b9510c564546

```text
.ce/changelog/ce-509-release-acceptance-design.md
.ce/pr-manifests/ce-509-release-acceptance-design.md
docs/design/release-acceptance-stage.md
```

## Evidence / Preflight Summary

Docs-only design unit. Validation evidence is recorded in the worker report and
may be copied here by the controller after harvest if desired.
