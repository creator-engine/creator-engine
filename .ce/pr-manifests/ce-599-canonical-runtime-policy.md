---
slug: ce-599-canonical-runtime-policy
date: 2026-07-18
declared_work_class: epic
---

# PR path manifest — canonical runtime policy

This carrier lists the closed 22-path DF-3 L2 implementation territory. It
includes itself and declares the canonical work class `epic`.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** epic

AUTHORIZED_PATHS_COUNT=22

AUTHORIZED_PATHS_SHA256=b8e3946a8f0b4cec8d20135d81834f5ae7e639d017ba7c245d7a911fe110464e

```text
.ce/brain/assertions.yaml
.ce/changelog/ce-599-canonical-runtime-policy.md
.ce/pr-manifests/ce-599-canonical-runtime-policy.md
.ce/reference/cli.generated.md
docs/contracts/runtime-policy.md
docs/reference/cli.md
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
validators/tests/unit/test_ce_brain_drift.py
validators/tests/unit/test_v1_docs_reconciliation.py
validators/tests/unit/test_v3_cli.py
```
