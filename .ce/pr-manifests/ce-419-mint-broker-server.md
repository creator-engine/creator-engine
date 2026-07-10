# PR path manifest — ce-419-mint-broker-server · mint-broker runnable server

- **Declared work class:** S

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-419-mint-broker-server
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below
(the carrier lists itself); the repo-wide fidelity scan requires the declared count and
SHA256 to match the fenced block.

Per-file purpose (the closed path-set — 6 paths):
- **`.ce/changelog/ce-419-mint-broker-server.md`** *(A)* — CE changelog carrier.
- **`.ce/pr-manifests/ce-419-mint-broker-server.md`** *(A)* — this carrier
  (self-inclusive).
- **`deploy/systemd/ce-mint-broker.service`** *(A)* — deployable systemd unit for the
  loopback-only mint-broker server.
- **`tools/mint-broker/ce_mint_broker_server.py`** *(A)* — stdlib HTTP server wrapper for
  the frozen pure mint-broker service.
- **`tools/mint-broker/config.example.yaml`** *(A)* — placeholder operator config example.
- **`validators/tests/unit/test_mint_broker_server.py`** *(A)* — focused server unit tests.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=59b240ed3f9b154b0daa2f48e2ef09e09dfcb696e1352480b925cee69b440a35

```text
.ce/changelog/ce-419-mint-broker-server.md
.ce/pr-manifests/ce-419-mint-broker-server.md
deploy/systemd/ce-mint-broker.service
tools/mint-broker/ce_mint_broker_server.py
tools/mint-broker/config.example.yaml
validators/tests/unit/test_mint_broker_server.py
```
