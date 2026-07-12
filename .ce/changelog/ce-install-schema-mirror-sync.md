---
slug: ce-install-schema-mirror-sync
date: 2026-07-12
kind: fixed
scope: install / docs schema mirror / parity guard
issue: none
---

**fix(install): sync docs/schemas install-answers mirror to canonical + parity guard.**

- Copy `validators/creator_engine_validator/schemas/install-answers.schema.yaml` (sha256 `621a76f2…`) to `docs/schemas/install-answers.schema.yaml`, restoring byte-parity with the signed spec pin.
- Add `test_docs_schemas_install_answers_mirror_is_byte_identical_to_validators_canonical` to `validators/tests/integration/test_install_bootstrap.py`; the guard fails on drift and passes only when the mirror equals the canonical validators copy.
- Root cause: PR #924 updated the canonical schema but did not sync the docs mirror, leaving the mirror at hash `be67d554…` while the 0.3.5 signed spec pin references `621a76f2…`. Result: INSTALL_REFUSED artifact_hash_mismatch on every fresh install. Reproduced in a clean container 2026-07-12.
- **Declared work class:** story
