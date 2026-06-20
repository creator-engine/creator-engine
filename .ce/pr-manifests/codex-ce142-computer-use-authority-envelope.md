# PR path manifest - codex-ce142-computer-use-authority-envelope

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref codex/ce142-computer-use-authority-envelope
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Scope:
ce-ops#142 Phase 1 only. Add a computer-use/UI side-effect authority envelope
substrate for account rename, app rename, and console setting mechanics; add
the authenticated-browser worker harness contract; add validator enforcement
and examples. Live Ring-2 hook honoring is deferred to Phase 2.

Base:
`a42c0aa2a567a6debf61eb81fc1f197a86cdee42` (`origin/main` at branch creation).

Per-file purpose (closed path-set - 29 paths):
- **`.ce/changelog/ce142-computer-use-authority-envelope.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/codex-ce142-computer-use-authority-envelope.md`** *(A)* - this carrier.
- **`docs/contracts/README.md`** *(M)* - index the two new computer-use contracts.
- **`docs/contracts/computer-use-authority-envelope.md`** *(A)* - prose contract for the UI authority envelope.
- **`docs/contracts/computer-use-worker-harness.md`** *(A)* - worker-harness contract for the validated authenticated-browser substrate.
- **`schemas/computer-use-authority-envelope.schema.yaml`** *(A)* - machine schema for the authority envelope.
- **`validators/creator_engine_validator/checks/__init__.py`** *(M)* - register the new check.
- **`validators/creator_engine_validator/checks/ce_computer_use_authority_envelope.py`** *(A)* - validator semantics for mechanic/target, ratification, DoR, target closure, roles, mode, and secret boundaries.
- **`validators/examples/computer-use-authority-envelope/invalid-mechanic-target.ce.yml`** *(A)* - mismatch fixture.
- **`validators/examples/computer-use-authority-envelope/invalid-missing-dor.ce.yml`** *(A)* - DoR fixture.
- **`validators/examples/computer-use-authority-envelope/invalid-open-target.ce.yml`** *(A)* - closed target fixture.
- **`validators/examples/computer-use-authority-envelope/invalid-ratification-binding.ce.yml`** *(A)* - ratified-prompt binding fixture.
- **`validators/examples/computer-use-authority-envelope/invalid-secret-value.ce.yml`** *(A)* - token/2FA boundary fixture.
- **`validators/examples/computer-use-authority-envelope/invalid-secret-value-numeric.ce.yml`** *(A)* - unquoted numeric OTP/2FA boundary fixture.
- **`validators/examples/computer-use-authority-envelope/valid-account-rename.ce.yml`** *(A)* - valid account rename fixture.
- **`validators/examples/computer-use-authority-envelope/valid-app-rename.ce.yml`** *(A)* - valid app rename fixture.
- **`validators/examples/computer-use-authority-envelope/valid-console-setting.ce.yml`** *(A)* - valid console setting fixture.
- **`validators/tests/integration/test_computer_use_authority_examples.py`** *(A)* - focused integration and CLI registration tests.
- **`validators/tests/integration/test_install_bootstrap.py`** *(M)* - prevent pytest `PYTHONPATH` from leaking into the signed-wheel installer subprocess.
- **`validators/tests/unit/test_app_jwt_runner.py`** *(M)* - registered-check count update for the new check.
- **`validators/tests/unit/test_change_status.py`** *(M)* - registered-check count update for the new check.
- **`validators/tests/unit/test_credential_runner.py`** *(M)* - registered-check count update for the new check.
- **`validators/tests/unit/test_evidence_sink.py`** *(M)* - registered-check count update for the new check.
- **`validators/tests/unit/test_merge.py`** *(M)* - registered-check count update for the new check.
- **`validators/tests/unit/test_open_change.py`** *(M)* - registered-check count update for the new check.
- **`validators/tests/unit/test_redact.py`** *(M)* - registered-check count update for the new check.
- **`validators/tests/unit/test_version_boundary.py`** *(M)* - registered-check count update for the new check.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* - app wheel digest re-pinned after rebuild.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* - rebuilt app wheel containing the new validator check.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=29

AUTHORIZED_PATHS_SHA256=fd74bf71ae50f809c97b3b6f726f812dd8bd7f624cdf07c780117e12e7e7d18c

```text
.ce/changelog/ce142-computer-use-authority-envelope.md
.ce/pr-manifests/codex-ce142-computer-use-authority-envelope.md
docs/contracts/README.md
docs/contracts/computer-use-authority-envelope.md
docs/contracts/computer-use-worker-harness.md
schemas/computer-use-authority-envelope.schema.yaml
validators/creator_engine_validator/checks/__init__.py
validators/creator_engine_validator/checks/ce_computer_use_authority_envelope.py
validators/examples/computer-use-authority-envelope/invalid-mechanic-target.ce.yml
validators/examples/computer-use-authority-envelope/invalid-missing-dor.ce.yml
validators/examples/computer-use-authority-envelope/invalid-open-target.ce.yml
validators/examples/computer-use-authority-envelope/invalid-ratification-binding.ce.yml
validators/examples/computer-use-authority-envelope/invalid-secret-value-numeric.ce.yml
validators/examples/computer-use-authority-envelope/invalid-secret-value.ce.yml
validators/examples/computer-use-authority-envelope/valid-account-rename.ce.yml
validators/examples/computer-use-authority-envelope/valid-app-rename.ce.yml
validators/examples/computer-use-authority-envelope/valid-console-setting.ce.yml
validators/tests/integration/test_computer_use_authority_examples.py
validators/tests/integration/test_install_bootstrap.py
validators/tests/unit/test_app_jwt_runner.py
validators/tests/unit/test_change_status.py
validators/tests/unit/test_credential_runner.py
validators/tests/unit/test_evidence_sink.py
validators/tests/unit/test_merge.py
validators/tests/unit/test_open_change.py
validators/tests/unit/test_redact.py
validators/tests/unit/test_version_boundary.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
