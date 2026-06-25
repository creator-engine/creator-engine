# PR path manifest — 243 · contained-seat self-submit PR review via injected credential

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce243-seat-review-transport-deputy-pr` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=c574d423b574915e9c442ab0aa6104af77c75d9a000383e6f1ba88798fd8fd68

```text
.ce/changelog/ce243-seat-review-transport-deputy-pr.md
.ce/pr-manifests/ce243-seat-review-transport-deputy-pr.md
validators/creator_engine_validator/forge/__init__.py
validators/creator_engine_validator/forge/cred_injection_proxy.py
validators/creator_engine_validator/forge/transport_deputy_policy.py
validators/tests/unit/test_cred_injection_proxy.py
validators/tests/unit/test_transport_deputy_policy.py
```
