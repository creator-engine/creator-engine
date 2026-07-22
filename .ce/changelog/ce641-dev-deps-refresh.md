---
slug: ce641-dev-deps-refresh
date: 2026-07-22
kind: changed
scope: validators/development-dependencies
---

**Refresh the validator development dependency closure to setuptools 83.0.0.**

- Raise the build-backend floor and the offline development requirement from
  `setuptools==82.0.1` to `setuptools==83.0.0`, and replace the corresponding
  vendored wheel in `validators/wheelhouse-dev/`. This is ordinary dependency
  acquisition; no signed-release artifact or signing action is involved.
- Regenerate `uv.lock` and retain the runtime-only `requirements.txt` export.
  Its lockstep verifier now follows the runtime dependency closure rather than
  treating declared optional extras as runtime requirements; CI installs that
  export before the development wheelhouse is available.
- Upstream 83.0.0 requires Python 3.10+, makes `MANIFEST.in` matching Unicode-
  normalization-insensitive (GHSA-h35f-9h28-mq5c), and removes `dry_run` in its
  synced distutils implementation. The project target remains Python 3.14+;
  no use of the removed option exists in this change.

The regenerated lock has no removed pins. Its added optional-extra pins are
intentionally absent from the runtime export and continue to belong to the
development-extra closure:

| Pin | Previous export | New export |
| --- | --- | --- |
| aiohappyeyeballs | absent | 2.7.1 |
| aiohttp | absent | 3.14.2 |
| aiohttp-jinja2 | absent | 1.6 |
| aiosignal | absent | 1.4.0 |
| anyio | absent | 4.14.2 |
| frozenlist | absent | 1.8.0 |
| idna | absent | 3.18 |
| jinja2 | absent | 3.1.6 |
| linkify-it-py | absent | 2.1.0 |
| markdown-it-py | absent | 4.2.0 |
| MarkupSafe | absent | 3.0.3 |
| mdit-py-plugins | absent | 0.6.1 |
| mdurl | absent | 0.1.2 |
| multidict | absent | 6.7.1 |
| platformdirs | absent | 4.11.0 |
| propcache | absent | 0.5.2 |
| Pygments | absent | 2.20.0 |
| rich | absent | 15.0.0 |
| textual | absent | 8.2.7 |
| textual-serve | absent | 1.1.3 |
| typing-extensions | absent | 4.16.0 |
| uc-micro-py | absent | 2.0.0 |
| watchfiles | absent | 1.2.0 |
| yarl | absent | 1.24.5 |
