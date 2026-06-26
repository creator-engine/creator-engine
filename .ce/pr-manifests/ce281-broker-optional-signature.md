# PR path manifest — ce-ops#281 · per-policy commit-signature requirement (off for contained seats)

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce281-broker-optional-signature` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=93bd42b156846d858de1f5fc5f29a8b1cbb08cb10232d80073c4681eb87d30f9

```text
.ce/changelog/ce281-broker-optional-signature.md
.ce/pr-manifests/ce281-broker-optional-signature.md
tools/egress-broker/apps.example.json
tools/egress-broker/egress_broker/config.py
tools/egress-broker/egress_broker/policy.py
validators/tests/unit/test_egress_signature_policy.py
```
