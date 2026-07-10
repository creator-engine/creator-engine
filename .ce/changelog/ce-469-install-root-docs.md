---
slug: ce-469-install-root-docs
date: 2026-07-10
kind: changed
scope: installer docs
---

**Document installer root override behavior.**

- Documents `CE_INSTALL_ROOT` in the installer contract as the environment
  equivalent of the bootstrap `--install-root` override.
- Adds `CE_INSTALL_ROOT` to the CLI install/update environment reference with
  the default root fallback.
