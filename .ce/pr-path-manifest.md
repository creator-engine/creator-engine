# PR path manifest — v3 G-1.0 (plane-C runtime-policy substrate)

This file is the **carrier** for this PR's ratified closed manifest (the
convention defined in `docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`).
CI (`.github/workflows/validate.yml`) passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`,
which enforces that this PR's `base..HEAD` diff equals exactly the authorized
path-set below (the diff-gate runs *active*, not neutral). The fidelity scan
(`scan-path-manifest`) additionally requires the declared count and SHA256 to
match the fenced block.

This PR stands up the v3 **G-1.0** runtime-policy substrate — the declarative
`schemas/runtime-policy.schema.yaml` contract plus the `ce_runtime_policy`
dogfood check. Substrate / record-shape only: no container, no gVisor /
OpenShell, no egress proxy, no network, no live runtime (those land in
G-1.1 / G-1.2 / G-1.3).

- **base:** `6ecf9a5997a1d1b3f6be8fdda5651dd324180375`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=13

AUTHORIZED_PATHS_SHA256=13ddc11fa6ade66b56d7fc0680c8221d9efe450e1c141021317ae69991951bb0

```text
.ce/pr-path-manifest.md
docs/contracts/runtime-policy.md
examples/malformed/runtime-policy/controller-key-secret.yml
examples/malformed/runtime-policy/forbidden-mount.yml
examples/malformed/runtime-policy/unpinned-image.yml
examples/well-formed/runtime-policy/example-runtime-policy.yml
schemas/runtime-policy.schema.yaml
validators/creator_engine_validator/checks/__init__.py
validators/creator_engine_validator/checks/ce_runtime_policy.py
validators/creator_engine_validator/cli.py
validators/tests/integration/test_ce_runtime_policy_examples.py
validators/tests/unit/test_ce_runtime_policy.py
validators/tests/unit/test_cli.py
```
