# PR path manifest — v3 G-1.2 (gVisor + capability-separation egress proxy backend)

This file is the **carrier** for this PR's ratified closed manifest (the
convention defined in `docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`).
CI (`.github/workflows/validate.yml`) passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`,
which enforces that this PR's `base..HEAD` diff equals exactly the authorized
path-set below (the diff-gate runs *active*, not neutral). The fidelity scan
(`scan-path-manifest`) additionally requires the declared count and SHA256 to
match the fenced block.

This PR adds the v3 **G-1.2** first live plane-C backend — a `gvisor-proxy`
backend behind the G-1.1 `RunnerBackend` adapter that translates a runtime-policy
into a hardened gVisor (runsc, Systrap — no KVM) container plan + a
capability-separation egress-proxy deny-by-default config, and fixes the in-repo
egress stub. The translation is pure/unit-tested; live calls go through an
injectable runner seam behind an availability gate (ZERO live subprocess in CI).
NOT a validator check — `--list-checks` is unchanged at 42.

This manifest is REVISION-2 (4 → 5): registering `gvisor-proxy` flipped the
G-1.1 `test_runner_backend.py` assertion that `gvisor-proxy` raises
`UnknownBackend`, so that test is a MODIFY (halt-and-amend).

- **base:** `d4df4bd7326522b5c1b1bb975da151707e8f8a2e`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=bea2344d57725cba72fac3b9cb5e1336b10c550ca42b37af9323689385b5971c

```text
.ce/pr-path-manifest.md
validators/creator_engine_validator/runner/__init__.py
validators/creator_engine_validator/runner/gvisor_proxy_backend.py
validators/tests/unit/test_gvisor_proxy_backend.py
validators/tests/unit/test_runner_backend.py
```
