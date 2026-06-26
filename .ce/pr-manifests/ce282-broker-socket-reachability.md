# PR path manifest — ce-ops#282 · contained-seat broker socket reachability + canonical self-review mount

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce282-broker-socket-reachability` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=87aafd228f94b88531afe40b0d0d7225416326e995f638911e34a58a0e2361d6

```text
.ce/changelog/ce282-broker-socket-reachability.md
.ce/pr-manifests/ce282-broker-socket-reachability.md
deploy/systemd/ce-egress-broker.service
deploy/systemd/ce-egress-self-review.service
deploy/vps-runsc/run-vps-runsc.sh
```
