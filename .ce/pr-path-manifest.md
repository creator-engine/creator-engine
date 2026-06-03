# PR path manifest — v3 G-1.1 (runner-backend adapter interface)

This file is the **carrier** for this PR's ratified closed manifest (the
convention defined in `docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`).
CI (`.github/workflows/validate.yml`) passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`,
which enforces that this PR's `base..HEAD` diff equals exactly the authorized
path-set below (the diff-gate runs *active*, not neutral). The fidelity scan
(`scan-path-manifest`) additionally requires the declared count and SHA256 to
match the fenced block.

This PR stands up the v3 **G-1.1** runner-backend adapter interface — the
`RunnerBackend` lifecycle ABC + the provision/run/collect/teardown data model +
a backend registry + an inert `local-noop` test backend. Pure interface: no
container, no gVisor/OpenShell, no egress proxy, no network, no subprocess, no
live backend (the live gVisor+proxy backend is G-1.2; the classifier/audit
overlay + evidence spine is G-1.3). NEW `runner/` sub-package — NOT a validator
check, so `--list-checks` is unchanged.

- **base:** `813c2dddb3a2619928edd72a5421b03a56cd2710`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=edfe0278b6b028836b300634b146046bca11d011f39d153f33e29dc881d68cd2

```text
.ce/pr-path-manifest.md
validators/creator_engine_validator/runner/__init__.py
validators/creator_engine_validator/runner/backend.py
validators/creator_engine_validator/runner/noop_backend.py
validators/tests/unit/test_runner_backend.py
```
