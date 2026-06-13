# PR path manifest — v35e-prime-wave · ce-ops#53 E-wave (Onboarding & Installer)

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref v35e-prime-wave
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below
(the carrier lists itself); the repo-wide fidelity scan requires the declared count and
SHA256 to match the fenced block. This is the **union carrier** named in the E1 scope's
acceptance criteria — one envelope around the four Operator-ratified E-wave scopes shipped
on the combined branch `v35e-prime-wave`.

Ratified gates (four scopes, combined branch, ordered E2→E3→E4→E1):
- `ce53-e2-onboard-apply` — onboard `apply` executor.
- `ce53-e3-brownfield` — brownfield adoption plan.
- `ce53-e4-greenfield` — greenfield first-project read model.
- `ce53-e1-installer` — real installer bootstrap (ratified spec rev-2 sha
  `a8324de6eeae6032bd11122060715e434dbdb8a42d3feaca9834f30b35dc33d3`, scope sha
  `812bbddcc934816f62115db6b8670b1cc95691e5367d04528e817f419ef2685f`), **LAST in order**,
  held at the SSHSIG signing seam. The production signature is the Operator offline-key act
  committed at `ebfacf6` (canonical-bytes SHA-256
  `303ab54167b2d7075977eb6fb5b6b4daf84a57d02d1303205b070baeef51dc93`, namespace `ce-spec-v1`,
  key `ce-root-v1`; verified `Good` against the pinned trust root `docs/keys/ce-root-v1`).

Base:
`f8d1c25065ec7050826d3808d103ecd816dc1a02` (`origin/main` = #219, the ce-ops#57 work-claim
date-bomb test-fix that un-redded `main`). The path-set + hash below are satisfiable at this base.

The change:
The E-wave makes the agent-native onboarding/install path real. **E2** adds the `onboard apply`
executor; **E3** adds the brownfield adoption plan; **E4** adds the greenfield first-project read
model; **E1** replaces the install spec/script with a real, signed bootstrap — `docs/install.sh`
fetches the signed spec and verifies it (trust-root SSHSIG, stock `ssh-keygen`) before executing,
acquires Python user-space via pinned `uv 0.11.21`, installs the offline wheel set from a
hash-gated Pages mirror under `docs/downloads/0.2.0/`, and the install spec `docs/llms-install.md`
now carries the production SSHSIG. Counters and the work-claim/staleness logic are untouched.

Per-file purpose (the closed path-set — 35 paths):
- **`.ce/pr-manifests/v35e-prime-wave.md`** *(A)* — this union carrier (self-inclusive).

E2 — onboard apply executor:
- **`validators/creator_engine_validator/onboard_apply.py`** *(A)* — the `onboard apply` executor.
- **`validators/tests/unit/test_onboard_apply.py`** *(A)* — onboard-apply unit coverage.
- **`validators/tests/integration/test_onboard_apply_greenfield.py`** *(A)* — onboard-apply integration coverage.
- **`docs/operations/ONBOARD_APPLY_PROTOCOL.md`** *(A)* — the onboard-apply protocol doc.

E3 — brownfield adoption plan:
- **`docs/contracts/brownfield-adoption.md`** *(A)* — the brownfield adoption contract.
- **`validators/tests/unit/test_install_answers.py`** *(M)* — install-answers tests extended for brownfield answers.

E4 — greenfield first-project read model:
- **`validators/creator_engine_validator/v3_greenfield.py`** *(A)* — the greenfield first-project read model.
- **`validators/tests/unit/test_v3_greenfield.py`** *(A)* — greenfield read-model unit coverage.
- **`validators/tests/integration/test_greenfield_first_project.py`** *(A)* — greenfield integration coverage.
- **`docs/operations/GREENFIELD_FIRST_PROJECT_PROTOCOL.md`** *(A)* — the greenfield first-project protocol doc.

E1 — real installer bootstrap + signed spec + Pages mirror:
- **`docs/install.sh`** *(M)* — real bootstrap: signed-spec fetch/verify-before-execute, trust-root SSHSIG verification, hash-gated Pages artifacts, user-space `uv 0.11.21` Python acquisition, offline wheel install, lock/idempotence.
- **`docs/llms-install.md`** *(M)* — the signed agent-native install spec (SSHSIG over canonical bytes, namespace `ce-spec-v1`); production `signature.value` + `content_sha256` embedded at `ebfacf6`.
- **`docs/llms.txt`** *(M)* — install entry pointer refreshed for the real installer.
- **`docs/downloads/0.2.0/SHA256SUMS`** *(A)* — Pages mirror checksum manifest (the installer's hash gate).
- **`docs/downloads/0.2.0/creator_engine_validator-0.2.0-py3-none-any.whl`** *(A)* — mirrored CE validator wheel.
- **`docs/downloads/0.2.0/attrs-26.1.0-py3-none-any.whl`** *(A)* — mirrored pinned dependency wheel.
- **`docs/downloads/0.2.0/jsonschema-4.26.0-py3-none-any.whl`** *(A)* — mirrored pinned dependency wheel.
- **`docs/downloads/0.2.0/jsonschema_specifications-2025.9.1-py3-none-any.whl`** *(A)* — mirrored pinned dependency wheel.
- **`docs/downloads/0.2.0/pyyaml-6.0.3-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl`** *(A)* — mirrored pinned dependency wheel.
- **`docs/downloads/0.2.0/referencing-0.37.0-py3-none-any.whl`** *(A)* — mirrored pinned dependency wheel.
- **`docs/downloads/0.2.0/rpds_py-0.30.0-cp314-cp314-manylinux_2_17_x86_64.manylinux2014_x86_64.whl`** *(A)* — mirrored pinned dependency wheel.
- **`validators/tests/integration/test_install_bootstrap.py`** *(A)* — installer-bootstrap integration coverage.
- **`validators/tests/unit/test_packaging_contract.py`** *(M)* — packaging-contract tests (wheel/mirror parity).
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* — rebuilt 0.2.0 wheel (source parity).
- **`validators/wheelhouse/SHA256SUMS`** *(M)* — wheelhouse checksums for the rebuilt wheel.

Cross-cutting (touched by multiple E-steps):
- **`validators/creator_engine_validator/v3_cli.py`** *(M)* — CLI surface for the onboard/brownfield/greenfield/installer flows incl. authentic `--trust-root` / `--require-authentic`.
- **`validators/creator_engine_validator/v3_installer.py`** *(M)* — installer core: canonicalization, SSHSIG verify, manifest/answers, brownfield + greenfield logic.
- **`validators/creator_engine_validator/_versions.py`** *(M)* — version surface (0.2.0) consumed by installer/packaging.
- **`docs/contracts/installer.md`** *(M)* — installer contract updated across the E-wave.
- **`docs/guide/pilot-runbook.md`** *(M)* — pilot runbook updated for onboard/brownfield/greenfield/installer.
- **`schemas/install-answers.schema.yaml`** *(M)* — install-answers schema extended for brownfield/greenfield.
- **`validators/tests/unit/test_v3_cli.py`** *(M)* — CLI tests across the E-steps.
- **`validators/tests/unit/test_v3_installer.py`** *(M)* — installer-core tests across the E-steps.
- **`validators/tests/unit/test_version_boundary.py`** *(M)* — version-boundary tests.

ce-ops#53 amend (xdist isolation):
- **`validators/tests/unit/test_launch_runtime.py`** *(M)* — per-test seat-state isolation (autouse `tmp_path`-chdir). The E-wave's added tests perturbed xdist scheduling and surfaced a latent shared-path collision (`./.ce/state/dispatches/<seat_id>/sentinel-wrapper.sh`) among the `session="s"` launch tests → flaky `StopIteration`. Pre-existing defect, not E-wave content; fix isolates each test's default state root.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=36

AUTHORIZED_PATHS_SHA256=e40fc6103b94fb2f69d17129215db2b94ba2158d353cbd240796edad35c86998

```text
.ce/pr-manifests/v35e-prime-wave.md
docs/contracts/brownfield-adoption.md
docs/contracts/installer.md
docs/downloads/0.2.0/SHA256SUMS
docs/downloads/0.2.0/attrs-26.1.0-py3-none-any.whl
docs/downloads/0.2.0/creator_engine_validator-0.2.0-py3-none-any.whl
docs/downloads/0.2.0/jsonschema-4.26.0-py3-none-any.whl
docs/downloads/0.2.0/jsonschema_specifications-2025.9.1-py3-none-any.whl
docs/downloads/0.2.0/pyyaml-6.0.3-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl
docs/downloads/0.2.0/referencing-0.37.0-py3-none-any.whl
docs/downloads/0.2.0/rpds_py-0.30.0-cp314-cp314-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
docs/guide/pilot-runbook.md
docs/install.sh
docs/llms-install.md
docs/llms.txt
docs/operations/GREENFIELD_FIRST_PROJECT_PROTOCOL.md
docs/operations/ONBOARD_APPLY_PROTOCOL.md
schemas/install-answers.schema.yaml
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/onboard_apply.py
validators/creator_engine_validator/v3_cli.py
validators/creator_engine_validator/v3_greenfield.py
validators/creator_engine_validator/v3_installer.py
validators/tests/integration/test_greenfield_first_project.py
validators/tests/integration/test_install_bootstrap.py
validators/tests/integration/test_onboard_apply_greenfield.py
validators/tests/unit/test_install_answers.py
validators/tests/unit/test_launch_runtime.py
validators/tests/unit/test_onboard_apply.py
validators/tests/unit/test_packaging_contract.py
validators/tests/unit/test_v3_cli.py
validators/tests/unit/test_v3_greenfield.py
validators/tests/unit/test_v3_installer.py
validators/tests/unit/test_version_boundary.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
