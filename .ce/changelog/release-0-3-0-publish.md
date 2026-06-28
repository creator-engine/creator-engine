---
slug: release-0-3-0-publish
date: 2026-06-28
kind: epic
scope: 0.3.0 release publish
issue: ce-ops#315
---

**publish signed 0.3.0 release (ce-root-v1).**

## 0.3.0 release publish — W2 proving release

Operator-authorized sign + publish of the 0.3.0 release (ce-ops#315). Cut manually since the autonomous-release pipeline (W2) is not yet landed; this is its proving run.

### Verified release artifacts
- canonical spec sha256: `9fb30d53eb2b5594e5bf0b05188036a3246ad6be33cd61dee5356bd122a736e1`
- wheel `creator_engine_validator-0.3.0-py3-none-any.whl`: `d3d3dd565921525ee578e8310c389ee054d9b4b91d9baa47b7b6586d2d7d42c1`
- `SHA256SUMS`: `bc6affdb1f67d240b971c6f3d54d1b5a075d241768d2046505e1d9240c945842`
- Detached SSHSIG (namespace `ce-spec-v1`) over the canonical bytes — verified Good against the pinned ce-root-v1 trust anchor.

Signed with `ce-root-v1` held on the controller host under Operator-authorized custody.

- **Declared work class:** epic
