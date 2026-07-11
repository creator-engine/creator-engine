# PR path manifest — ce-sl3-ready-attestation-nudge

This carrier lists the closed authorized path-set for the pure SL-3 READY
attestation reducer.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=f2832932a864e60c2f44635b6488602f86de41939a804ec70f58e388c56a96ca

```text
.ce/changelog/ce-sl3-ready-attestation-nudge.md
.ce/pr-manifests/ce-sl3-ready-attestation-nudge.md
validators/creator_engine_validator/forge/ready_attestation_nudge.py
validators/tests/unit/test_ready_attestation_nudge.py
```
