# PR path manifest - codex-ce177-brain-drift-ci

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref codex/ce177-brain-drift-ci
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Scope:
ce-ops#177 Knowledge-SSOT drift CI on top of the ce-ops#167 brain assertion
ledger and ce-ops#176 capability probes. This adds drift verification only:
no auto-correction, MCP, recall/vector surface, bootstrap, or migration.

The changes:
- Adds `ce_brain_drift`, a registered governance check that re-verifies active
  brain assertions against `evidence_ref`.
- Treats `probe:<name>` assertions through the F2 probe seam and compares
  claimed `claim.verdict` to the observed probe verdict.
- Treats non-probe evidence as a local artifact reference; missing/unreadable
  artifacts fail closed, and explicit hash/value claim fields are compared
  against observed artifact bytes/text.
- Adds `ce brain verify --drift` for on-demand drift checks.
- Adds a narrow CI invocation over `.ce/state` so the drift check runs on every
  validation job without broadening unrelated scans.
- Adds offline unit/integration coverage for pass, drift, fail-closed, and
  deterministic output behavior.

Per-file purpose (closed path-set - 16 paths):
- **`.ce/changelog/ce177-brain-drift-ci.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/codex-ce177-brain-drift-ci.md`** *(A)* - this carrier.
- **`.github/workflows/validate.yml`** *(M)* - narrow brain drift CI step.
- **`validators/creator_engine_validator/ce_cli.py`** *(M)* - wires `ce brain verify --drift`.
- **`validators/creator_engine_validator/checks/__init__.py`** *(M)* - imports the drift check for registration.
- **`validators/creator_engine_validator/checks/ce_brain_drift.py`** *(A)* - active assertion drift checker.
- **`validators/tests/integration/test_ce_brain_cli.py`** *(M)* - CLI drift pass/non-zero coverage.
- **`validators/tests/unit/test_app_jwt_runner.py`** *(M)* - registered check count update.
- **`validators/tests/unit/test_ce_brain_drift.py`** *(A)* - drift checker unit coverage.
- **`validators/tests/unit/test_change_status.py`** *(M)* - registered check count update.
- **`validators/tests/unit/test_credential_runner.py`** *(M)* - registered check count update.
- **`validators/tests/unit/test_evidence_sink.py`** *(M)* - registered check count update.
- **`validators/tests/unit/test_merge.py`** *(M)* - registered check count update.
- **`validators/tests/unit/test_open_change.py`** *(M)* - registered check count update.
- **`validators/tests/unit/test_redact.py`** *(M)* - registered check count update.
- **`validators/tests/unit/test_version_boundary.py`** *(M)* - registered check count update.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=16

AUTHORIZED_PATHS_SHA256=9486a08bfa2c2a3893b631ec669fd0d136940e54f8aca882e71779ff20149f91

```text
.ce/changelog/ce177-brain-drift-ci.md
.ce/pr-manifests/codex-ce177-brain-drift-ci.md
.github/workflows/validate.yml
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/checks/__init__.py
validators/creator_engine_validator/checks/ce_brain_drift.py
validators/tests/integration/test_ce_brain_cli.py
validators/tests/unit/test_app_jwt_runner.py
validators/tests/unit/test_ce_brain_drift.py
validators/tests/unit/test_change_status.py
validators/tests/unit/test_credential_runner.py
validators/tests/unit/test_evidence_sink.py
validators/tests/unit/test_merge.py
validators/tests/unit/test_open_change.py
validators/tests/unit/test_redact.py
validators/tests/unit/test_version_boundary.py
```
