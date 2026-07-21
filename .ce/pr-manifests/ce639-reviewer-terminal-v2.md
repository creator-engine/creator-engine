# PR path manifest — ce-ops#639 · reviewer terminal v2 enforcement

This carrier lists the closed authorized path-set for the reviewer-terminal v2
fail-closed evidence admission change. It lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=26

AUTHORIZED_PATHS_SHA256=0744872f1c3f02c1b3d027466ffe0bac1386d373ce58fa9cb488d4ba97da3def

```text
.ce/changelog/ce639-reviewer-terminal-v2.md
.ce/pr-manifests/ce639-reviewer-terminal-v2.md
.claude/agents/reviewer.md
.claude/commands/code-review.md
tools/egress-broker/ce_egress_self_review_broker.py
validators/creator_engine_validator/forge/cred_injection_proxy.py
validators/creator_engine_validator/forge/review_acting.py
validators/creator_engine_validator/forge/review_submission_receipt.py
validators/creator_engine_validator/forge/review_submit.py
validators/creator_engine_validator/forge/reviewer_terminal.py
validators/creator_engine_validator/forge/transport_deputy_policy.py
validators/creator_engine_validator/hook_check.py
validators/creator_engine_validator/v3_cli.py
validators/creator_engine_validator/v3_forge_join.py
validators/creator_engine_validator/v3_seat_bridge.py
validators/tests/unit/test_claude_code_review_wrapper.py
validators/tests/unit/test_cred_injection_proxy.py
validators/tests/unit/test_egress_self_review_broker.py
validators/tests/unit/test_hook_check_reviewer_authority.py
validators/tests/unit/test_review_submission_receipt.py
validators/tests/unit/test_review_submit.py
validators/tests/unit/test_reviewer_terminal.py
validators/tests/unit/test_transport_deputy_policy.py
validators/tests/unit/test_v3_cli.py
validators/tests/unit/test_v3_forge_join.py
validators/tests/unit/test_v3_seat_bridge.py
```
