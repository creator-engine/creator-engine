---
slug: ce124-cli-shims
date: 2026-06-18
kind: fixed
scope: public installer / CLI exposure
issue: ce-ops#124
base: 02c3f0d
---

Fixes the public CE v3 installer bootstrap so a successful install leaves the
expected user-local commands on PATH-capable locations.

- Creates or repairs `~/.local/bin/cev3` and `~/.local/bin/ce` after the
  verified venv entrypoints pass their health check.
- Keeps the shim step idempotent: reruns update stale symlinks to the current
  verified venv and refuse to overwrite non-symlink user files.
- Warns when `~/.local/bin` is not already on `PATH`, since the installer cannot
  permanently mutate the caller's parent shell environment.
- Adds regression coverage proving fresh install and rerun both leave the shims
  present and resolving to the verified venv entrypoints.
- Leaves `docs/downloads/` untouched and does not edit validator package source,
  so no wheelhouse rebuild is part of this fix.
