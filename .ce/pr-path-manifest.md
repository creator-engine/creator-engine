# PR path manifest — feat(v3.5-A.2b-ii): OpenShell LIVE governed-run harness + daemon-free replay + attested bundle

This file is the carrier for this PR's closed path manifest under
`docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`. CI passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below. The fidelity scan (`scan-path-manifest`) requires the declared count and
SHA256 to match the fenced block.

Scope: the **A.2b-ii** half of the OpenShell A.2b split — the live-proof harness,
its recorded replayable evidence bundle, and the daemon-free offline replay test —
landing on the **A.2b-i-corrected backend surface** (already on `main` in #185).
A real governed run was driven end-to-end through
`AuditOverlayBackend(OpenShellBackend(SubprocessSandboxClient()))` against a
connected OpenShell v0.0.57 gateway; the recorded bundle carries the attested,
hash-chained `provision -> run -> collect -> teardown` spine plus the real OCSF
ALLOWED/DENIED governance decisions, and CI re-verifies them offline.

- **`examples/openshell_live_run.py`** *(NEW)* — the availability-gated live harness
  (runs only when `openshell` is on PATH and `openshell status` is Connected, so CI
  never executes it). Lives in `examples/`, NOT `runner/`, so it adds no baselined
  `runner.*` module. The egress policy is scoped to the calling binary
  (`binary_identity`) and grants the base image's standard Landlock read paths —
  both expressed through the EXISTING runtime-policy contract; the backend is
  unchanged.
- **`validators/tests/unit/fixtures/openshell_live_bundle.json`** *(NEW)* — the
  recorded, sanitized evidence bundle from the real run (attested spine chain +
  the mapped OCSF records, >=1 ALLOWED + >=1 DENIED + the deny reason + the exec
  exits). Host-specific PIDs / epoch timestamps are normalized; the OCSF decision
  fields are kept verbatim-real.
- **`validators/tests/unit/test_openshell_live_replay.py`** *(NEW)* — daemon-free,
  no-network offline replay: asserts `verify_chain(chain) == []`, that the OCSF
  text maps through the backend collect path to both ALLOWED and DENIED, that the
  lifecycle order `provision -> run -> collect -> teardown` is attested, and that
  the DENIED counterfactual carries its reason. Spawns no subprocess, opens no
  socket (mirrors `test_openshell_backend.py::test_no_network_during_lifecycle`).
- **`.ce/pr-path-manifest.md`** *(this carrier)*.

**Version-boundary impact = ZERO.** No new `runner.*` module, no schema change,
no check registration, no `runner/__init__.py` export; `V3_RUNTIME` stays **28**
and `--list-checks` stays byte-identical.

- **base:** `2f572c8` (current `main`).
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=c5c96cd7af9fbe6c583a3e066eaa38ae250e32f4ce8618094060ff2ec975d755

```text
.ce/pr-path-manifest.md
examples/openshell_live_run.py
validators/tests/unit/fixtures/openshell_live_bundle.json
validators/tests/unit/test_openshell_live_replay.py
```
