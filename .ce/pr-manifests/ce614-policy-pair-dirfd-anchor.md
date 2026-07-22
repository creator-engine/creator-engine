---
slug: ce614-policy-pair-dirfd-anchor
date: 2026-07-22
declared_work_class: XS
---

# PR path manifest — runtime-policy pair dirfd anchor

This carrier lists the closed 4-path security slice. Runtime-policy pair
mutations now remain anchored to the directory descriptor that completed the
no-follow walk.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** XS

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=6387c598abf6f260be0047212e405ecbf0f18f6a3c870511b4a73d92d8c881ab

```text
.ce/changelog/ce614-policy-pair-dirfd-anchor.md
.ce/pr-manifests/ce614-policy-pair-dirfd-anchor.md
validators/creator_engine_validator/onboard_apply.py
validators/tests/unit/test_onboard_apply.py
```
