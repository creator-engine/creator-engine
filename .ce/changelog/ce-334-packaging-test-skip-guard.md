---
slug: ce-334-packaging-test-skip-guard
date: 2026-06-28
kind: fix
scope: validator schema packaging test
issue: ce-ops#334
---

The schema packaging wheel integration test now uses the offline dev wheelhouse
toolchain with `python -m build --no-isolation` and fails loudly in CI strict
mode when build, venv, install, or console-script setup cannot run. GitHub
Actions already exports `CI=true`, and local focused runs can set
`CE_SCHEMA_PACKAGING_STRICT=1`, so missing build-backend coverage cannot hide
behind a skipped integration test.
