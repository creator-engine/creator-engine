---
slug: ce276-surfaces-check-updates
date: 2026-06-26
kind: feature
scope: [validators/creator_engine_validator/surfaces, validators/creator_engine_validator/ce_cli.py]
issue: ce-ops#276
---

- **Declared work class:** feature

Added a read-only `ce surfaces check-updates` surface that compares
`surfaces/manifest.yaml` entries with upstream npm, GitHub releases, Zig
download index, and PyPI metadata.

