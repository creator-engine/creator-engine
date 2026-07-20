# PR path manifest — DF4-N · Governed author mechanics preconditions

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs `verify-path-manifest --base <sha>
--manifest-dir .ce/pr-manifests --head-ref
arc-full-output-t2-mechanics-preconditions` and requires this PR's `base..HEAD`
diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** XS

This carrier preserves its five-path set while adding programmatic slug and
pinned-document assertion preconditions to the canonical author guidance.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=b3d8ee085bb200cd88e5c4d98b5190f4cc9c14a276c6938eebbcbb425c89d376

```text
.ce/brain/assertions.yaml
.ce/changelog/arc-full-output-t2-mechanics-preconditions.md
.ce/pr-manifests/arc-full-output-t2-mechanics-preconditions.md
docs/contracts/authoring-a-governed-pr.md
docs/operations/AUTHOR_A_CE_VALID_PR.md
```
