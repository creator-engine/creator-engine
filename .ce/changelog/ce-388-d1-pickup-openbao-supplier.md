---
slug: ce-388-d1-pickup-openbao-supplier
date: 2026-07-05
kind: story
scope: review-pickup OpenBao token supplier
issue: ce-388
work_class: story
---

**Review-pickup can refresh its GitHub token from SecretIdentity/OpenBao per pass.**

- Added review-pickup token SecretRef defaults for the reviewer GitHub token.
- Added the `--pickup-token-secret-*` flag family and file-only target refusal
  so configured daemon runs use the SecretIdentity materialize/read/revoke path.
- Added per-pass token refresh plus bounded retry when a supplier is configured,
  while preserving the existing static-token path when it is not.
- Added focused offline smoke coverage for unconfigured compatibility, env-target
  refusal, backend defaults, per-pass refresh, and bounded supplier failure.
