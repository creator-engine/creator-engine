---
slug: ce642-notice-autogen
date: 2026-07-22
kind: changed
scope: dependency-notice
---

Generate NOTICE's distributed-dependency name/version inventory instead of
maintaining version rows by hand. The runtime table follows only the ordinary
`validators/uv.lock` dependency closure (not optional extras); the development
table follows `requirements-dev.txt` and is self-checked against actual
`wheelhouse-dev` filenames. The generator owns only the marked inventory block
and provides `--write`/`--check` modes; the registered sync check fails closed
when the committed block drifts or a displayed version is not vendored.

License terms deliberately remain in the restored hand-maintained,
per-package attribution section: the lock does not provide authoritative
licensing data, while each distributed wheel's metadata and license text do.
This keeps the legal attribution boundary honest while making only the
name/version inventory deterministic.
