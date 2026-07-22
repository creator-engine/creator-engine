---
slug: ce642-notice-autogen
date: 2026-07-22
kind: changed
scope: dependency-notice
---

Generate NOTICE's third-party name/version inventory from `validators/uv.lock`
instead of maintaining version rows by hand. The generator owns only the
marked inventory block and provides `--write`/`--check` modes; the registered
sync check fails closed when the committed block drifts from the lock.

License terms deliberately remain outside the generated projection: the lock
does not provide authoritative licensing data, while each distributed wheel's
metadata and license text do. This keeps the legal attribution boundary honest
while making version inventory updates deterministic.
