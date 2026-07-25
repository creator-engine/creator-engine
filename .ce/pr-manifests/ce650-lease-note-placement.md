# PR path manifest — queue daemon lease note placement

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path set for this PR. CI verifies that the base-to-head diff equals
exactly this set; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=b3a3b45729799896bd8ab3f593c43f1d2b1e270f035ddde4afe3753d61dfad3c

```text
.ce/changelog/ce650-lease-note-placement.md
.ce/pr-manifests/ce650-lease-note-placement.md
validators/creator_engine_validator/daemon_lease.py
```
