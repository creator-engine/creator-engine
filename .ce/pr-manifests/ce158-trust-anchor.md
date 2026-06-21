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
Rebased onto `6e2e697504203880bd7aa01580bb794e55c22999` (`origin/main`
after ce-ops#178 brain bootstrap).

Per-file purpose (closed path-set - 15 paths):

- **`.ce/changelog/ce158-trust-anchor.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce158-trust-anchor.md`** *(A)* - this PR's closed path-set carrier.
- **`.ce/state/research/DESIGN_ce158_trust_anchor_20260621T025918Z.md`** *(A)* - topology recommendation, record format, and external binding callout.
- **`docs/contracts/installer.md`** *(M)* - installer contract now requires an out-of-band fingerprint anchor before inventory.
- **`docs/downloads/0.2.0/SHA256SUMS`** *(M)* - refreshed Pages mirror `install.sh` and served app-wheel checksum lines.
- **`docs/downloads/0.2.0/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* - rebuilt served validator app wheel so the public installer can call the new trust-anchor CLI surface.
- **`docs/install.sh`** *(M)* - bootstrap fetches/verifies an out-of-band trust-anchor record and passes it to `cev3 onboard`.
- **`docs/llms-install.md`** *(M)* - signed install spec documents and pins the trust-anchor bootstrap contract.
- **`docs/llms.txt`** *(M)* - public install index reflects the trust-root plus out-of-band-anchor requirement.
- **`validators/creator_engine_validator/_version.py`** *(M)* - regenerated build identity for the served app-wheel rebuild.
- **`validators/creator_engine_validator/v3_cli.py`** *(M)* - authentic onboarding `--trust-anchor SOURCE=PATH` gate and evidence output.
- **`validators/creator_engine_validator/v3_installer.py`** *(M)* - pure key fingerprint, anchor parsing, and anchor agreement checks.
- **`validators/tests/integration/test_install_bootstrap.py`** *(M)* - bootstrap regression coverage for trust-anchor fetch/refusal and inventory handoff.
- **`validators/tests/unit/test_v3_cli.py`** *(M)* - authentic onboarding agreement, same-origin-only, and mismatch coverage.
- **`validators/tests/unit/test_v3_installer.py`** *(M)* - pure anchor parser/verifier coverage.
Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=15

AUTHORIZED_PATHS_SHA256=cd1129654fc820a512ffa4cbb56d7ee919ef7fa6bdac1ff92b2bf517cd99b37a

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
```
