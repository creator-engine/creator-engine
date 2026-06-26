---
slug: ce166-knowledge-ssot-slice3
date: 2026-06-26
kind: pr-manifest
scope: knowledge-ssot self-identity
issue: ce-ops#166
---

# PR path manifest - ce166-knowledge-ssot-slice3

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce166-knowledge-ssot-slice3 --require-carrier
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

- **Declared work class:** story

Scope:
ce-ops#166 slice 3 makes self-identity a live Knowledge-SSOT primitive and
fails controller bootstrap when remembered self-identity assertions drift from
fresh runtime probes.

Per-file purpose:
- **`.ce/brain/assertions.yaml`** *(M)* - authoritative self-identity and worker-spawn runtime probe assertions.
- **`.ce/changelog/ce166-knowledge-ssot-slice3.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce166-knowledge-ssot-slice3.md`** *(A)* - this closed path-set carrier.
- **`validators/creator_engine_validator/brain_bootstrap.py`** *(M)* - bootstrap-time self-identity probe reconciliation with fail-closed logging.
- **`validators/creator_engine_validator/brain_probe.py`** *(M)* - live self-identity and worker-spawn runtime probes.
- **`validators/creator_engine_validator/checks/ce_brain_drift.py`** *(M)* - skip other-seat self-identity assertions during live probe drift checks.
- **`validators/tests/unit/test_brain_bootstrap.py`** *(M)* - bootstrap drift-detect coverage for matching and mutated self-identity.
- **`validators/tests/unit/test_brain_probe.py`** *(M)* - deterministic self-identity and runtime capability probe coverage.
- **`validators/tests/unit/test_ce_brain_drift.py`** *(M)* - authoritative ledger expectation updated for the added probe assertions.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=75145a94ea34ef78f6bde52477c04703691c2a80c7a388b1687f83320d66caa3

```text
.ce/brain/assertions.yaml
.ce/changelog/ce166-knowledge-ssot-slice3.md
.ce/pr-manifests/ce166-knowledge-ssot-slice3.md
validators/creator_engine_validator/brain_bootstrap.py
validators/creator_engine_validator/brain_probe.py
validators/creator_engine_validator/checks/ce_brain_drift.py
validators/tests/unit/test_brain_bootstrap.py
validators/tests/unit/test_brain_probe.py
validators/tests/unit/test_ce_brain_drift.py
```
