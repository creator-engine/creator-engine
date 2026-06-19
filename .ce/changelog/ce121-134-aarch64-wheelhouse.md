---
slug: ce121-134-aarch64-wheelhouse
date: 2026-06-19
kind: fixed
scope: validator dev wheelhouse
issue: ce-ops#121, ce-ops#134
base: 1d01e097fc44004324fbc5665667eca6cca160ab
---

Prepares the aarch64 developer/test wheelhouse closure for CE installs on
NVIDIA DGX/Grace hosts.

- Confirms the runtime wheelhouse already carries Linux/aarch64 cp314 wheels for
  the only compiled runtime dependencies, `PyYAML` and `rpds-py`; runtime
  publish/sign/install verification remains covered by the existing ce-ops#121
  installer artifacts and operator-gated signing flow.
- Adds Linux/aarch64 cp314 manylinux wheels to `validators/wheelhouse-dev/` for
  the seven native dev/test packages needed by the offline suite:
  `aiohttp`, `frozenlist`, `MarkupSafe`, `multidict`, `propcache`,
  `watchfiles`, and `yarl`.
- Extends the packaging contract tests so the dev wheelhouse must remain
  cp314-only and dual-arch for those native packages.
- Leaves `validators/wheelhouse/SHA256SUMS`, served install docs, public
  downloads, and the runtime app wheel untouched in this hold branch.
