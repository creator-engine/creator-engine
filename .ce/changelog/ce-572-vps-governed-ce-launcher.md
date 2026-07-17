---
slug: ce-572-vps-governed-ce-launcher
date: 2026-07-17
kind: fix
scope: deploy
issue: ce-ops#572
---

**bake the governed `ce` launcher into the VPS runsc image.**

The image now installs a root-owned, non-writable `/usr/local/bin/ce` wrapper
that invokes the offline validator venv with repository validator sources on
`PYTHONPATH`. This changes image capability only; it does not deploy or relaunch
any live seat.
