# PR path manifest — v3 G-2.0 (thin orchestrator + approved-plan ratification gate)

This file is the **carrier** for this PR's ratified closed manifest (the
convention defined in `docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`).
CI (`.github/workflows/validate.yml`) passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`,
which enforces that this PR's `base..HEAD` diff equals exactly the authorized
path-set below (the diff-gate runs *active*, not neutral). The fidelity scan
(`scan-path-manifest`) additionally requires the declared count and SHA256 to
match the fenced block.

This PR opens the v3 **G-2** milestone with **G-2.0**: the **thin orchestrator**
`run_plan(...)` — pure glue that gate-checks an `ApprovedPlan`, resolves an
isolation backend (injected, else `get_backend(runtime_policy["isolation_backend"])`),
wraps it in the G-1.3b `AuditOverlayBackend`, and drives
`provision -> run -> collect -> teardown`, returning the collected hash-chained
evidence — and the **approved-plan ratification gate** (`PlanNotRatified`), which
refuses to provision BEFORE any side effect unless a human-ratified plan, bound
to the exact `policy_sha` and `run_id`, is present.

The orchestrator is pure-in-process Python behind the G-1.1 adapter: it registers
NO validator check and NO `isolation_backend`, so `--list-checks` is **unchanged
at 43** (source-tree count) and `available_backends()` stays
`('gvisor-proxy','local-noop')`. CI exercises the full lifecycle against the
inert `LocalNoopBackend` with zero live subprocess. The concrete backends, the
G-1.0 deny surface, and the evidence spine are byte-untouched. No `ce_cli.py`/
wheel change (stdlib only). Forge-native `plan_approved()`/`mint_scoped_token`
and OpenShell remain deferred G-2 hardening.

- **base:** `fe0b54c82b91faad6eab375619708a81470fcb22`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=4ab2992e9d9bab7d18b11311ec7aba8dc007feda3807d51677fad95f20371ed3

```text
.ce/pr-path-manifest.md
docs/contracts/orchestrator.md
validators/creator_engine_validator/orchestrator.py
validators/tests/unit/test_orchestrator.py
```
