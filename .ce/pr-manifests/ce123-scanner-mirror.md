# PR path manifest - ce123-scanner-mirror - scanner mirror commissioning

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI/path review should compare this branch's `base..HEAD` diff to the authorized
path set below. This carrier lists itself.

Ratified:
Operator dispatch for ce-ops#123 on 2026-06-18: commission sha256-pinned
Gitleaks and TruffleHog mirror artifacts for Linux x86_64 and Linux arm64,
wire the live brownfield secret-preflight verifier, commit locally only, and do
not push, sign, or publish the mirror.

Base:
`8cc07222a8051b2c3e6804d92036680711928472` (`origin/main` after #265 OpenBao P1 merge rebase).

The changes:
- Four extracted scanner binaries are staged under the 0.2.0 Pages mirror path:
  Gitleaks 8.30.1 and TruffleHog 3.95.6 for Linux x86_64 and Linux arm64.
- `scanner-mirror.fragment.yaml` carries the unsigned signing fragment with
  `{name, version, platform, url, sha256}` for each scanner/platform pair.
- The live driver selects commissioned scanner pins for the host platform and
  continues to refuse unsupported/unpinned/fetch-failed/sha-mismatched scanners.
- Tests cover pinned x86_64 clean, sha mismatch refusal, fetch/unpinned
  fail-closed behavior, env commissioning, and arm64 manifest/hash resolution.
- The validator app wheel is rebuilt from the current branch source and
  `validators/wheelhouse/SHA256SUMS` is refreshed; the signed Pages mirror
  release files outside this PR's scanner staging set are intentionally
  untouched.

Pinned scanner artifact sha256 values:

| Scanner | Version | Platform | sha256 |
|---|---:|---|---|
| Gitleaks | 8.30.1 | linux/x86_64 | `88f91962aa2f93ac6ab281d553b9e125f5197bbbce38f9f2437f7299c32e5509` |
| Gitleaks | 8.30.1 | linux/arm64 | `00e91bbe655bd7c47753e8cfe61cb76ea1a5d7e7702fe161ee40102b46b3823b` |
| TruffleHog | 3.95.6 | linux/x86_64 | `d4414128597485471941f9d03c2aecf072141d84aa5d728b31dfbfe79d64d2b9` |
| TruffleHog | 3.95.6 | linux/arm64 | `c2c5117f305b214f4e07d215d070e51e33479bae87e365c641ba3d9e8b2af0eb` |

Per-file purpose (the closed path-set - 11 paths; `(A)` add, `(M)` modify):
- **`.ce/changelog/ce123-scanner-mirror.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce123-scanner-mirror.md`** *(A)* - this per-PR
  closed-manifest carrier.
- **`docs/downloads/0.2.0/scanners/gitleaks-8.30.1-linux-arm64`** *(A)* -
  staged Gitleaks 8.30.1 Linux arm64 executable.
- **`docs/downloads/0.2.0/scanners/gitleaks-8.30.1-linux-x86_64`** *(A)* -
  staged Gitleaks 8.30.1 Linux x86_64 executable.
- **`docs/downloads/0.2.0/scanners/scanner-mirror.fragment.yaml`** *(A)* -
  unsigned scanner mirror manifest fragment for controller signing.
- **`docs/downloads/0.2.0/scanners/trufflehog-3.95.6-linux-arm64`** *(A)* -
  staged TruffleHog 3.95.6 Linux arm64 executable.
- **`docs/downloads/0.2.0/scanners/trufflehog-3.95.6-linux-x86_64`** *(A)* -
  staged TruffleHog 3.95.6 Linux x86_64 executable.
- **`validators/creator_engine_validator/onboard_apply_live.py`** *(M)* -
  platform-aware scanner pins and fail-closed runtime override handling.
- **`validators/tests/unit/test_onboard_apply_live.py`** *(M)* -
  scanner mirror commissioning and fail-closed regression coverage.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* - refreshed dev wheelhouse
  digest manifest for the rebuilt validator app wheel.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`**
  *(M)* - rebuilt validator app wheel matching this branch's source.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=11

AUTHORIZED_PATHS_SHA256=34639f6376a47f50d3d9f8224d090578ccd0246bf2a3b242c9f7e4fa6a17f97a

```text
.ce/changelog/ce123-scanner-mirror.md
.ce/pr-manifests/ce123-scanner-mirror.md
docs/downloads/0.2.0/scanners/gitleaks-8.30.1-linux-arm64
docs/downloads/0.2.0/scanners/gitleaks-8.30.1-linux-x86_64
docs/downloads/0.2.0/scanners/scanner-mirror.fragment.yaml
docs/downloads/0.2.0/scanners/trufflehog-3.95.6-linux-arm64
docs/downloads/0.2.0/scanners/trufflehog-3.95.6-linux-x86_64
validators/creator_engine_validator/onboard_apply_live.py
validators/tests/unit/test_onboard_apply_live.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
