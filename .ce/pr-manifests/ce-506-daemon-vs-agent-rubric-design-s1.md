# PR path manifest — ce-506 · Add the daemon-vs-agent routing rubric

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-506-daemon-vs-agent-rubric-design-s1` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=d62b64c5939dec4aa2cc80daa4276d1dcd4af546167039c28127f44c461be31d

```text
.ce/changelog/ce-506-daemon-vs-agent-rubric-design-s1.md
.ce/pr-manifests/ce-506-daemon-vs-agent-rubric-design-s1.md
docs/design/daemon-vs-agent-rubric.md
```
