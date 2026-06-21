# PR path manifest - ce158-trust-anchor

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce158-trust-anchor
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Scope:
ce-ops#158 out-of-band trust anchor for `ce-root-v1`, authentic onboarding UX
refusals, and verifier evidence.

Base:
Rebased onto `146272ca82a4c160ddf0a67087381418b43e24eb` (`origin/main`
after ce-ops#23 baseline attestation).

Per-file purpose (closed path-set - 17 paths):

- **`.ce/changelog/ce158-trust-anchor.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce158-trust-anchor.md`** *(A)* - this PR's closed path-set carrier.
- **`.ce/state/research/DESIGN_ce158_trust_anchor_20260621T025918Z.md`** *(A)* - topology recommendation, record format, and external binding callout.
- **`docs/contracts/installer.md`** *(M)* - installer contract now requires an out-of-band fingerprint anchor before inventory.
- **`docs/downloads/0.2.0/SHA256SUMS`** *(M)* - refreshed Pages mirror `install.sh` and app-wheel checksum lines.
- **`docs/downloads/0.2.0/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* - rebuilt served validator app wheel from changed source.
- **`docs/install.sh`** *(M)* - bootstrap fetches/verifies an out-of-band trust-anchor record and passes it to `cev3 onboard`.
- **`docs/llms-install.md`** *(M)* - signed install spec documents and pins the trust-anchor bootstrap contract.
- **`docs/llms.txt`** *(M)* - public install index reflects the trust-root plus out-of-band-anchor requirement.
- **`validators/creator_engine_validator/_version.py`** *(M)* - regenerated
  build identity for the served app-wheel rebuild.
- **`validators/creator_engine_validator/v3_cli.py`** *(M)* - authentic onboarding `--trust-anchor SOURCE=PATH` gate and evidence output.
- **`validators/creator_engine_validator/v3_installer.py`** *(M)* - pure key fingerprint, anchor parsing, and anchor agreement checks.
- **`validators/tests/integration/test_install_bootstrap.py`** *(M)* - bootstrap regression coverage for trust-anchor fetch/refusal and inventory handoff.
- **`validators/tests/unit/test_v3_cli.py`** *(M)* - authentic onboarding agreement, same-origin-only, and mismatch coverage.
- **`validators/tests/unit/test_v3_installer.py`** *(M)* - pure anchor parser/verifier coverage.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* - refreshed local app-wheel checksum after rebuilding from changed source.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* - rebuilt local validator app wheel from changed source for reviewer wheel-parity proof.
Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=17

AUTHORIZED_PATHS_SHA256=55fe94364bd5eb9094ca1601dbd4c9b5a45ea131f3733326ea9702c26ecc62e3

```text
.ce/changelog/ce158-trust-anchor.md
.ce/pr-manifests/ce158-trust-anchor.md
.ce/state/research/DESIGN_ce158_trust_anchor_20260621T025918Z.md
docs/contracts/installer.md
docs/downloads/0.2.0/SHA256SUMS
docs/downloads/0.2.0/creator_engine_validator-0.2.0-py3-none-any.whl
docs/install.sh
docs/llms-install.md
docs/llms.txt
validators/creator_engine_validator/_version.py
validators/creator_engine_validator/v3_cli.py
validators/creator_engine_validator/v3_installer.py
validators/tests/integration/test_install_bootstrap.py
validators/tests/unit/test_v3_cli.py
validators/tests/unit/test_v3_installer.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
