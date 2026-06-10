# PR path manifest — v3.5-E.3 E3 wave: the two-mode installer engine (E3-G1 → E3-G2 → E3-G3)

CI passes this to `verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; the
fidelity scan requires the declared count + SHA256 to match the fenced block.

ONE combined branch carrying the three serial gates of the ratified E3 wave mandate
(`.hermes/launch/v35e-e3-wave-20260610T114156Z/E3_WAVE_GATE_MANDATE.md`, sha256 `6fd8ec27…`),
per the batch-collapse lesson. One engine, two modes: the answers file (IaC) + the
operator-input inventory (E3-G1, pure) · the decomposed GitHub-leg planners (E3-G2, pure) ·
the `ce onboard --answers/--inventory/--plan/--non-interactive` CLI + playbook upgrade
(E3-G3). **Check registry 51 → 52 (`install_answers`, declared in-gate E3-G1); V1_RUNTIME 22 /
V3_RUNTIME 32 unchanged; live drive stays the deferred E.4 seam.**

Per-file purpose:
- **`schemas/install-answers.schema.yaml`** *(A · G1)* — the answers-file schema = the single
  source of truth (x-ce-* inventory annotations; SecretRef + ratification-binding $defs; the
  protection reference floor as `x-ce-reference-posture` data); declared in `V3_SCHEMAS`.
- **`validators/creator_engine_validator/v3_installer.py`** *(M · G1+G2)* — the pure engine:
  answers load/validate (fail-closed) · SecretRef · `valid_ratification` · precedence merge ·
  missing-list/`require_complete` · `sudo_grant_diff` · `inventory_emission` (G1); the GitHub-leg
  planners `plan_repo` / `bootstrap_scope_table` / `plan_github_app` / `plan_branch_protection` /
  `plan_actions_workflow` / `reviewer_identity_floor` / `build_github_leg_plan` (G2).
- **`validators/creator_engine_validator/checks/install_answers.py`** *(A · G1)* — the Ring-1
  answers-file check (`VAL-IA-*`). **`checks/__init__.py`** *(M · G1)* — registers it.
- **`validators/creator_engine_validator/_versions.py`** *(M · G1)* — `V3_SCHEMAS` + the new schema.
- **`validators/creator_engine_validator/v3_cli.py`** *(M · G3)* — `ce onboard` grows
  `--answers / --answers-schema / --inventory / --plan / --non-interactive` (verify-first preserved).
- **`docs/contracts/installer.md`** *(M · G2)* — the one-engine answers model + the decomposed
  GitHub leg + boundary refresh.
- **`docs/install.sh`** *(M · G3)* — `CE_ANSWERS` / `--answers` passthrough.
- **`docs/llms-install.md`** *(M · G3)* — regenerated to teach inventory→answers→plan→apply;
  re-signed (sha256-content digest published with the gate report).
- **`docs/guide/pilot-runbook.md`** *(M · G3)* — §1–2: the IaC door + the re-run-convergent GitHub leg.
- **`validators/tests/unit/test_v3_installer.py`** *(M · G1+G2)*, **`test_install_answers.py`**
  *(A · G1)*, **`test_v3_cli.py`** *(M · G3)* — the gates' test surfaces (+85 tests).
- **`validators/tests/unit/test_version_boundary.py · test_evidence_sink.py ·
  test_app_jwt_runner.py · test_change_status.py · test_credential_runner.py · test_merge.py ·
  test_open_change.py · test_redact.py`** *(M · G1)* — the 8 registry-count pins 51 → 52.
- **`validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl` + `SHA256SUMS`**
  *(M · per-gate)* — shipped wheel rebuilt from the combined source + re-pinned (oracle green).
- **`.ce/pr-path-manifest.md`** *(this carrier — composed LAST, union of the three gates)*.

- **base:** `4b2566d` (current `main`, post-#187).
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=24

AUTHORIZED_PATHS_SHA256=0420dce2b6e350631299ef358b5ab8ec56c36441a4fa170d873557a42c06a37e

```text
.ce/pr-path-manifest.md
docs/contracts/installer.md
docs/guide/pilot-runbook.md
docs/install.sh
docs/llms-install.md
schemas/install-answers.schema.yaml
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/checks/__init__.py
validators/creator_engine_validator/checks/install_answers.py
validators/creator_engine_validator/v3_cli.py
validators/creator_engine_validator/v3_installer.py
validators/tests/unit/test_app_jwt_runner.py
validators/tests/unit/test_change_status.py
validators/tests/unit/test_credential_runner.py
validators/tests/unit/test_evidence_sink.py
validators/tests/unit/test_install_answers.py
validators/tests/unit/test_merge.py
validators/tests/unit/test_open_change.py
validators/tests/unit/test_redact.py
validators/tests/unit/test_v3_cli.py
validators/tests/unit/test_v3_installer.py
validators/tests/unit/test_version_boundary.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl
```
