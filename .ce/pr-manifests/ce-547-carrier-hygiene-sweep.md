---
slug: ce-547-carrier-hygiene-sweep
date: 2026-07-18
declared_work_class: S
---

# PR path manifest — dead carrier-manifest hygiene sweep

This carrier lists the closed path territory for the dead carrier-manifest
hygiene sweep: the `ce carrier gc` subcommand plus the immediate purge of two
long-dead carriers. It includes itself and declares the work class `S`.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

Per-file purpose:
- **`.ce/changelog/ce-547-carrier-hygiene-sweep.md`** *(A)* — changelog fragment.
- **`.ce/pr-manifests/ce-547-carrier-hygiene-sweep.md`** *(A)* — this carrier (self-inclusive).
- **`.ce/pr-manifests/ce38-work-claims.md`** *(D)* — dead carrier purged (branch gone).
- **`.ce/pr-manifests/ce57-datebomb-fix.md`** *(D)* — dead carrier purged (branch gone).
- **`docs/reference/cli.md`** *(M)* — document the `ce carrier gc` subcommand.
- **`validators/creator_engine_validator/carrier_gc.py`** *(A)* — the sweep runtime
  (slug parse, liveness classification, dry-run/apply sweep with injectable remover).
- **`validators/creator_engine_validator/public_docs_confidentiality.py`** *(M)* — drop
  the two purged carriers from the `ALLOWED_OFFENSES` ratchet so it stays non-stale.
- **`validators/creator_engine_validator/v3_cli.py`** *(M)* — the `carrier gc` subcommand
  parser + handler; write-mode flags become argparse-optional and are enforced in-handler.
- **`validators/tests/unit/test_carrier_gc.py`** *(A)* — hermetic sweep tests (no network/git).

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=881f92e900ed1da84f11efdded99449890eded30edff0669e999c375acbb41a2

```text
.ce/changelog/ce-547-carrier-hygiene-sweep.md
.ce/pr-manifests/ce-547-carrier-hygiene-sweep.md
.ce/pr-manifests/ce38-work-claims.md
.ce/pr-manifests/ce57-datebomb-fix.md
docs/reference/cli.md
validators/creator_engine_validator/carrier_gc.py
validators/creator_engine_validator/public_docs_confidentiality.py
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_carrier_gc.py
```
