---
slug: ce-599-canonical-runtime-policy
date: 2026-07-18
declared_work_class: epic
---

# PR path manifest — ce-ops#599 canonical runtime policy

This carrier lists the closed 16-path DF-3 L2 implementation territory. It
includes itself and declares the canonical work class `epic`.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** epic

AUTHORIZED_PATHS_COUNT=16

AUTHORIZED_PATHS_SHA256=f0839854a730b4a3186adaa66ef71f65d9f0b32ac3e8bdb1282239618a70ce17

```text
.ce/changelog/ce-599-canonical-runtime-policy.md
.ce/pr-manifests/ce-599-canonical-runtime-policy.md
docs/contracts/runtime-policy.md
governance/policies/codex-one-shot-launch-v1.yaml
governance/policies/runtime/default-controller-v1.yaml
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/checks/ce_runtime_policy.py
validators/creator_engine_validator/codex_worker_launcher.py
validators/creator_engine_validator/onboard_apply.py
validators/creator_engine_validator/onboard_apply_live.py
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_ce_runtime_policy.py
validators/tests/unit/test_ce_worker_cli.py
validators/tests/unit/test_codex_worker_launcher.py
validators/tests/unit/test_onboard_apply.py
validators/tests/unit/test_onboard_apply_live.py
```
