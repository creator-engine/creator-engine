# PR path manifest — ce-388-d2-pickup-openbao-deploy-tests

Per-PR carrier for the review-pickup OpenBao deployment surface and D1 behavior
coverage slice. The diff is constrained to the deployment unit/docs, the two
required unit test modules, and this branch's carrier files.

- **Declared work class:** story

Per-file purpose:
- **`.ce/changelog/ce-388-d2-pickup-openbao-deploy-tests.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce-388-d2-pickup-openbao-deploy-tests.md`** *(A)* - this carrier.
- **`deploy/systemd/README.md`** *(M)* - gate env documentation for OpenBao review-pickup token supply and fallback rollout.
- **`deploy/systemd/ce-review-pickup-daemon.service`** *(M)* - commented-ready pickup token secret flags while preserving static fallback.
- **`deploy/systemd/install-gate-daemons-systemd.sh`** *(M)* - missing-env guidance for OpenBao review-pickup variables.
- **`validators/tests/unit/test_review_pickup.py`** *(M)* - loop retry, refresh, and bounded-failure coverage.
- **`validators/tests/unit/test_v3_cli.py`** *(M)* - CLI supplier construction and target-ref validation coverage.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=c73a337574eb1711ce377fa80cb994e25ae98ff478e7ecc96cf0afe24b548424

```text
.ce/changelog/ce-388-d2-pickup-openbao-deploy-tests.md
.ce/pr-manifests/ce-388-d2-pickup-openbao-deploy-tests.md
deploy/systemd/README.md
deploy/systemd/ce-review-pickup-daemon.service
deploy/systemd/install-gate-daemons-systemd.sh
validators/tests/unit/test_review_pickup.py
validators/tests/unit/test_v3_cli.py
```
