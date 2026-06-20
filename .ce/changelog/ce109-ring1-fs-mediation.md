---
slug: ce109-ring1-fs-mediation
date: 2026-06-20
kind: fixed
scope: runner / Ring-1 Section-8c filesystem mediation
base: 707e440d8c4b04cb743498c63e94b80d7e513aee
---

Fixes the Ring-1 tool-guard shim root so runner launches no longer allow-list a
predictable `/tmp` path that can be pre-created as a symlink to a
credential-bearing directory. The default shim path now lives under a
process-scoped current-uid private parent, the runtime validates owner/mode and
rejects symlink path components before adding the resolved path to Landlock read
roots, and the installer creates shims through exclusive temp files inside the
private root.

This preserves the ce-ops#109 Section-8c Landlock mediation path while closing
the reviewed symlink-TOCTOU escape: a hostile shim root pointing at
out-of-workspace `.ssh/id_rsa` is rejected before Landlock setup, and a safe
resolved shim root still denies arbitrary secret reads.

Rebuilds `creator_engine_validator-0.2.0-py3-none-any.whl` and refreshes
`validators/wheelhouse/SHA256SUMS` with digest
`a47466ed1e1035e2e68ae7fbc807f50c5ad51ecf7d9cc3d963e1c164838f2a66`.
