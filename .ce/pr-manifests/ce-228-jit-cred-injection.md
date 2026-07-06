# PR path manifest — 228 · feat(broker): add JIT seat credential lane (ce-ops#228 slice 1)

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-228-jit-cred-injection` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=44e7ed4ff5c19129d7a782b660777451836d91bb2c94cb2ff7e6787a5a2390c6

```text
.ce/changelog/ce-228-jit-cred-injection.md
.ce/pr-manifests/ce-228-jit-cred-injection.md
tools/egress-broker/README.md
tools/egress-broker/apps.example.json
tools/egress-broker/egress_broker/__init__.py
tools/egress-broker/egress_broker/config.py
tools/egress-broker/egress_broker/host_broker.py
tools/egress-broker/egress_broker/jit_credential.py
validators/tests/unit/test_jit_credential_broker.py
```
