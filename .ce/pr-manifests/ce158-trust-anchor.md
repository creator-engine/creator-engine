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
`d6ba7ee291c882aa865af7e0e32972b3223b5532` (`origin/main` at branch creation).

Per-file purpose (closed path-set - 9 paths):

- **`.ce/changelog/ce158-trust-anchor.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce158-trust-anchor.md`** *(A)* - this PR's closed path-set carrier.
- **`.ce/state/research/DESIGN_ce158_trust_anchor_20260621T025918Z.md`** *(A)* - topology recommendation, record format, and external binding callout.
- **`validators/creator_engine_validator/v3_cli.py`** *(M)* - authentic onboarding `--trust-anchor SOURCE=PATH` gate and evidence output.
- **`validators/creator_engine_validator/v3_installer.py`** *(M)* - pure key fingerprint, anchor parsing, and anchor agreement checks.
- **`validators/tests/unit/test_v3_cli.py`** *(M)* - authentic onboarding agreement, same-origin-only, and mismatch coverage.
- **`validators/tests/unit/test_v3_installer.py`** *(M)* - pure anchor parser/verifier coverage.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* - refreshed app-wheel checksum line.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* - rebuilt validator app wheel from changed source.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=bb4108c6d6fb1086b9b9c704ba7d0d2c80b6197b4203ea15a8365b84732c2eb9

```text
.ce/changelog/ce158-trust-anchor.md
.ce/pr-manifests/ce158-trust-anchor.md
.ce/state/research/DESIGN_ce158_trust_anchor_20260621T025918Z.md
validators/creator_engine_validator/v3_cli.py
validators/creator_engine_validator/v3_installer.py
validators/tests/unit/test_v3_cli.py
validators/tests/unit/test_v3_installer.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
