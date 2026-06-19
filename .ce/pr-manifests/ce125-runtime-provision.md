# PR path manifest - ce125-runtime-provision

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce125-runtime-provision

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

Ratified:
Controller relay for ce-ops#125 on 2026-06-19: the install runtime-provisioning
leg must auto-install the gVisor runtime deps (`runsc` + `gvproxy`) with pinned
versions, verification, and fail-closed behavior. This pairs with the ce-ops#128
containment work. Use strict TDD, rebuild the validator wheelhouse if validator
source changes, do not touch `docs/downloads/`, commit locally, and do not push.

The changes:
- The live apply driver now auto-ensures pinned `runsc` `20260608.0` and
  `gvproxy` `v0.8.9` for the `gvisor-proxy` runtime-provisioning leg.
- Runtime tool installation is digest-checked before install and version-checked
  after install, refusing unsupported architectures and every fetch/hash/install
  or version failure.
- The dependency planner, answer schema, docs, and tests now name the concrete
  sudo-scoped runtime binary as `gvproxy` instead of the placeholder `proxy`.
- The validator wheelhouse was rebuilt and `SHA256SUMS` refreshed.

Trust-root note:
- `docs/install.sh` was not touched.
- `docs/downloads/` was not touched.
- The signed `docs/llms-install.md` bundle was intentionally left untouched.

Per-file purpose (the closed path-set - 17 paths; `(A)` add):
- **`.ce/changelog/ce125-runtime-provision.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce125-runtime-provision.md`** *(A)* - this carrier.
- **`docs/contracts/installer.md`** - dependency contract wording for
  `runsc`/`gvproxy`.
- **`docs/guide/pilot-runbook.md`** - answer example sudo grant update.
- **`docs/schemas/install-answers.schema.yaml`** - published answer schema
  sudo-grant enum update.
- **`schemas/install-answers.schema.yaml`** - source answer schema sudo-grant
  enum update.
- **`validators/creator_engine_validator/onboard_apply.py`** - base runtime
  verification now checks `gvproxy`.
- **`validators/creator_engine_validator/onboard_apply_live.py`** - pinned
  runtime binary install, digest verification, version verification, and runtime
  provisioning auto-install.
- **`validators/creator_engine_validator/v3_cli.py`** - dependency wording
  update.
- **`validators/creator_engine_validator/v3_installer.py`** - dependency plan
  and sudo tool set use `gvproxy`.
- **`validators/tests/unit/test_install_answers.py`** - schema fixture update.
- **`validators/tests/unit/test_onboard_apply.py`** - runtime verification and
  sudo grant expectations update.
- **`validators/tests/unit/test_onboard_apply_live.py`** - strict TDD coverage
  for pinned `runsc`/`gvproxy` auto-install, digest mismatch, stale PATH binary,
  and version mismatch fail-closed behavior.
- **`validators/tests/unit/test_v3_cli.py`** - CLI dependency/sudo expectations
  update.
- **`validators/tests/unit/test_v3_installer.py`** - planner dependency/sudo
  expectations update.
- **`validators/wheelhouse/SHA256SUMS`** - refreshed wheelhouse checksums.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** -
  rebuilt validator wheel.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=17

AUTHORIZED_PATHS_SHA256=d3ee72c69e0d9f07f2db935e82d8d49ecd99fc921e2dee3174c3ed9f13fb4d7f

```text
.ce/changelog/ce125-runtime-provision.md
.ce/pr-manifests/ce125-runtime-provision.md
docs/contracts/installer.md
docs/guide/pilot-runbook.md
docs/schemas/install-answers.schema.yaml
schemas/install-answers.schema.yaml
validators/creator_engine_validator/onboard_apply.py
validators/creator_engine_validator/onboard_apply_live.py
validators/creator_engine_validator/v3_cli.py
validators/creator_engine_validator/v3_installer.py
validators/tests/unit/test_install_answers.py
validators/tests/unit/test_onboard_apply.py
validators/tests/unit/test_onboard_apply_live.py
validators/tests/unit/test_v3_cli.py
validators/tests/unit/test_v3_installer.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
