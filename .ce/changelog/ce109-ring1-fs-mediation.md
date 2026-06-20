---
slug: ce109-ring1-fs-mediation
date: 2026-06-20
kind: fixed
scope: runner / Ring-1 Section-8c filesystem mediation
base: 707e440d8c4b04cb743498c63e94b80d7e513aee
---

Fixes the Ring-1 tool-guard default install directory so runner launches no
longer collide on a shared `/tmp/ce-ring1-tool-guard` path across governed seats
or parallel runner processes. The default shim directory is now scoped by the
current uid and process id while the explicit `shim_dir` API remains unchanged.

This preserves the ce-ops#109 Section-8c Landlock mediation path and makes the
local OpenShell-style runner integration green on multi-seat and parallel-test
hosts where another seat or worker may already own the legacy global shim
directory.

Rebuilds `creator_engine_validator-0.2.0-py3-none-any.whl` and refreshes
`validators/wheelhouse/SHA256SUMS` with digest
`98186ddabe75442d01819e13a4d43aeeb9a02e566c65e83d892d17ce9a5b0738`.
