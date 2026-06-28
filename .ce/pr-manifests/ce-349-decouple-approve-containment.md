# PR path manifest — ce-ops#349 · Decouple APPROVE authority from containment

- **Declared work class:** story

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-349-decouple-approve-containment` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=585c89cd255850aa0bddb29ca96984c58926e4e2fd7dda2c2fae46dad55b759c

```text
.ce/changelog/ce-349-decouple-approve-containment.md
.ce/pr-manifests/ce-349-decouple-approve-containment.md
tools/egress-broker/ce_egress_self_review_broker.py
validators/creator_engine_validator/forge/cred_injection_proxy.py
validators/creator_engine_validator/forge/transport_deputy_policy.py
validators/tests/unit/test_claude_code_review_wrapper.py
validators/tests/unit/test_cred_injection_proxy.py
validators/tests/unit/test_egress_self_review_broker.py
validators/tests/unit/test_transport_deputy_policy.py
```
