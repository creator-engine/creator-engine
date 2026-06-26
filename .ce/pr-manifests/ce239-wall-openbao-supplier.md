# PR path manifest - ce-ops#239 - approval wall OpenBao supplier gate

This per-PR carrier lists the closed authorized path-set for this branch. The
implementation wiring already exists on `origin/main`; this residual unit records
the explicit production arming gate required by ce-ops#239 without arming the
approval wall or touching any credential material.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=2

AUTHORIZED_PATHS_SHA256=fc1110f6db0b5ede82aeab6b013fc8cbb78ffaec51150211e164ee44c1164043

```text
.ce/changelog/ce239-wall-openbao-supplier.md
.ce/pr-manifests/ce239-wall-openbao-supplier.md
```
