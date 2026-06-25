# PR path manifest - ce-ops#243 self-review broker

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set
for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests
--head-ref ce243-self-review-broker` and requires this PR's `base..HEAD` diff to equal exactly
the authorized path-set below; this carrier lists itself.

Re-pinned after rebase onto `origin/main` (post #242/#469 merge); the authorized path-set below
is unchanged (the rebase only merged the shared `tools/egress-broker/README.md` section).

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=9392fb4a7860e69feba775d013bb8a6ba6af88bb14ad6ac439dcb94c672e2867

```text
.ce/changelog/ce243-self-review-broker.md
.ce/pr-manifests/ce243-self-review-broker.md
tools/egress-broker/README.md
tools/egress-broker/ce_egress_self_review_broker.py
validators/tests/unit/test_egress_self_review_broker.py
```
