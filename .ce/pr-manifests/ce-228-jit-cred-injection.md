# PR path manifest — 228 · feat(broker): add JIT seat credential lane

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-228-jit-cred-injection` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** feature

AUTHORIZED_PATHS_COUNT=10

AUTHORIZED_PATHS_SHA256=2db1b96f77ae945afac09e731cb763007f4733e60a5ba352338442028fa2ef1a

```text
.ce/changelog/ce-228-jit-cred-injection.md
.ce/pr-manifests/ce-228-jit-cred-injection.md
tools/egress-broker/README.md
tools/egress-broker/apps.example.json
tools/egress-broker/egress_broker/__init__.py
tools/egress-broker/egress_broker/config.py
tools/egress-broker/egress_broker/host_broker.py
tools/egress-broker/egress_broker/jit_credential.py
validators/tests/unit/test_egress_host_broker.py
validators/tests/unit/test_jit_credential_broker.py
```
