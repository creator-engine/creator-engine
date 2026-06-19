# PR path manifest - ce113-openbao-p3 - OpenBao SecretIdentityBackend Phase 3

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce113-openbao-p3
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. The carrier lists itself.

Ratified base:
PR #265 merged Phase 0/1/2 on 2026-06-19. This branch takes main as the base
for ADR-0005, the SecretIdentityBackend substrate, schemas,
`secret_identity.py`, and Phase 1/2 tests.

Operator P3 ratification:
B.1-B.5 are ratified by the Operator on 2026-06-19. Phase 3 build scope is
local-only deployment automation and live-adapter integration against a
disposable loopback OpenBao instance. Production controller-VPS provisioning,
production secret-zero injection, production unseal/root custody, backup custody,
emergency revocation, and B.6 migration remain Operator-side and are not executed
by this branch.

Per-file purpose (closed P3 path-set - 10 paths):
- **`.ce/pr-manifests/ce113-openbao-p3.md`** *(A)* - this fresh P3 carrier.
- **`.ce/changelog/ce113-openbao-design.md`** *(M)* - P3-only changelog delta on the existing ce-ops#113 changelog.
- **`.ce/state/research/DESIGN_ce113_openbao_20260619T031542Z.md`** *(M)* - Phase 3 local-build boundary added to the ratified design; B.6 held.
- **`validators/creator_engine_validator/cli.py`** *(M)* - non-executing `openbao-p3-plan` value-free plan renderer.
- **`validators/creator_engine_validator/openbao_p3.py`** *(A)* - Phase 3 local deployment plan, response-wrapped AppRole bootstrap, stdlib HTTPS runner, co-tenancy guard, and audit-fail-closed probe helpers.
- **`validators/tests/integration/test_openbao_p3_live.py`** *(A)* - opt-in local OpenBao 2.5.5 live test for wrapped AppRole, adapter materialization, and audit fail-closed behavior.
- **`validators/tests/unit/test_cli.py`** *(M)* - CLI coverage for `openbao-p3-plan`.
- **`validators/tests/unit/test_openbao_p3.py`** *(A)* - unit coverage for Phase 3 B.1-B.5 automation boundaries.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* - rebuilt app wheel containing reviewer triage plus the P3 helpers.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* - re-pinned app wheel digest only.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=10

AUTHORIZED_PATHS_SHA256=49e3db2c80a3ec67a5669a3169eeb9835da70271deeb62a76e17f425745b821f

```text
.ce/changelog/ce113-openbao-design.md
.ce/pr-manifests/ce113-openbao-p3.md
.ce/state/research/DESIGN_ce113_openbao_20260619T031542Z.md
validators/creator_engine_validator/cli.py
validators/creator_engine_validator/openbao_p3.py
validators/tests/integration/test_openbao_p3_live.py
validators/tests/unit/test_cli.py
validators/tests/unit/test_openbao_p3.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
