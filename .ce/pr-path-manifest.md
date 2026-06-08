# PR path manifest — feat(v3.5-A.1): OpenShell `RunnerBackend` (pure/green-now, defines-not-registers)

This file is the carrier for this PR's closed path manifest under
`docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`. CI passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below. The fidelity scan (`scan-path-manifest`) additionally requires the
declared count and SHA256 to match the fenced block.

Scope: **v3.5-A.1 — the OpenShell `RunnerBackend` (first slice of the
OpenShell-integration cluster / NVIDIA-partnership arc)**. Pure / green-now: it
DEFINES a second live-capable runner backend behind the G-1.1 `RunnerBackend`
adapter — the inner kernel-level runtime grader composed under CE's outer SDLC
grader — WITHOUT a live daemon, gRPC wire, network, or new heavy deps. The live
gRPC client is A.2; registration + spend metering are A.2 / A.3.

Closed 5-file functional manifest (+ this carrier = 6 authorized paths):

- **`runner/openshell_backend.py`** (NEW) — pure `translate_to_sandbox_policy` →
  frozen `SandboxPolicy` (filesystem / landlock / process / `network_policies`,
  deny-by-default preserved); `SandboxClient` Protocol named after the OpenShell
  RPCs + in-memory `FakeSandboxClient` + inert `_UnwiredSandboxClient` (refuses
  until A.2); `OpenShellBackend(RunnerBackend)` provision→run→collect→teardown,
  `PolicyRejected` at the boundary, OCSF→`CollectedEvidence`;
  `OPENSHELL_PINNED_VERSION = "v0.0.57"`. **Deliberately does NOT
  `register_backend`** (→ A.2, consistent with `backend.py:187-189`).
- **`runner/__init__.py`** — export-only (`OPENSHELL_BACKEND_KEY` + surface).
- **`_versions.py`** — adds `"runner.openshell_backend"` to `V3_RUNTIME`
  (clears the `version_boundary` `VAL-VERBND-SHARED-EDGE` guard).
- **`tests/unit/test_openshell_backend.py`** (NEW) — 21 tests; the backend is
  exercised DIRECTLY (unregistered in A.1; no `get_backend` /
  `available_backends` assertions — those move to A.2).
- **`tests/unit/test_version_boundary.py`** — paired count-bump for the
  `_versions.py` baseline entry: `len(V3_RUNTIME)` 26 → 27.

`openshell` stays **UNREGISTERED** (`available_backends() == ("gvisor-proxy",
"local-noop")`; `get_backend("openshell")` raises `UnknownBackend`) → the ~10
existing registry-pinning tests stay green, untouched. The runner package
registers **no validator check**, so the check surface stays **47** and
`--list-checks` is byte-identical to base. No network, no gRPC, no `grpcio`.

Standing requirements honored: **v1↔v3 coexistence** (ADDITIVE; **v1 deleted = ∅**);
**G-4.1 naming hygiene** (`v3_naming_hygiene` GREEN — the new v3 module + tests
carry no bootstrapping-harness residue). `pytest validators/` is green save the
pre-existing local-umask `test_hook_scripts_are_executable_posix_sh` artifact
(present on `main`; git tracks the script `100755`; CI is green).

- **base:** `5ffc28d`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=08efb19cbf73d54a1e497f4014d535fca5c6ff47ca1379f7b1139feec5c9012a

```text
.ce/pr-path-manifest.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/runner/__init__.py
validators/creator_engine_validator/runner/openshell_backend.py
validators/tests/unit/test_openshell_backend.py
validators/tests/unit/test_version_boundary.py
```
