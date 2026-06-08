# PR path manifest — feat(v3.5-A.2a): register the OpenShell backend + wire the subprocess-CLI SandboxClient (CI-green)

This file is the carrier for this PR's closed path manifest under
`docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`. CI passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below. The fidelity scan (`scan-path-manifest`) requires the declared count and
SHA256 to match the fenced block.

Scope: **CODE — v3.5-A.2a, the second slice of the OpenShell-integration cluster
(the NVIDIA-partnership arc).** A.1 (PR #172, `280e927`) DEFINED but did NOT
register the `OpenShellBackend`. A.2a closes the loop, all green-now in CI (no
live gateway, no new dependency):

- **register the backend** (`register_backend(BACKEND_KEY, OpenShellBackend)`) under
  the `openshell` key the G-1.1 registry reserved → `available_backends()` becomes the
  sorted 3-tuple `("gvisor-proxy", "local-noop", "openshell")`;
- **wire a live `SubprocessSandboxClient`** over the `openshell sandbox` CLI, kept IN
  the existing `runner/openshell_backend.py` module (mirroring how the gVisor backend
  keeps `SubprocessContainerRunner` in `gvisor_proxy_backend.py`) so **no new
  `runner.*` module** enters the v3 runtime surface — the live shell-outs all carry
  `# pragma: no cover` and CI runs none of them;
- add the pure `render_sandbox_policy_yaml` serializer (the `--policy` wire form,
  design-of-record §3) + the pure `parse_ocsf_jsonl` line-to-dict parser
  (design-of-record §5), both unit-tested; export the two new public symbols;
- update the ~10 registry-pinning tests A.1 deferred (2-tuple to the 3-tuple + the two
  unregistered-to-registered conversions).

**Version-boundary impact = ZERO** (the A.1 lesson, applied up front): A.2a adds **no
new module**, so it needs **NO `_versions.py` edit and NO `test_version_boundary.py`
count bump** — `runner.openshell_backend` is already baselined and `V3_RUNTIME` stays
**28**. Neither file appears in this manifest. **No `grpcio` / `openshell` SDK / new
dependency / module-level network**; the live `SandboxClient` rides the same gateway
the gRPC surface does, with zero new deps. `--list-checks` stays byte-identical
(`register_backend` is the backend registry, not the `@register` check registry).
A.2b (the recorded real run + replayable evidence-bundle fixture + offline replay test)
is a SEPARATE follow-on, composed + ratified after A.2a merges.

- **base:** `48be1aae50f693463b68c5f808c2fae87fc5ce91`. (The ratified prompt pinned
  `df85fe0`; `main` has since advanced to `48be1aa` via the **docs-only** PR #177 —
  roadmap-row SHA fill, zero A.2a paths — a benign base-only advance; base re-pinned
  here, no content re-ratification.)
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=14

AUTHORIZED_PATHS_SHA256=9e44ae4f8d02bdf8decf3ba6581fab994220fc766d7121db825975103196952d

```text
.ce/pr-path-manifest.md
validators/creator_engine_validator/runner/__init__.py
validators/creator_engine_validator/runner/openshell_backend.py
validators/tests/unit/test_app_jwt_runner.py
validators/tests/unit/test_audit_overlay.py
validators/tests/unit/test_change_status.py
validators/tests/unit/test_credential_runner.py
validators/tests/unit/test_evidence_sink.py
validators/tests/unit/test_merge.py
validators/tests/unit/test_open_change.py
validators/tests/unit/test_openshell_backend.py
validators/tests/unit/test_orchestrator.py
validators/tests/unit/test_redact.py
validators/tests/unit/test_runner_backend.py
```
