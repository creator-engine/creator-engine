# PR path manifest - ce123-scanner-mirror - scanner mirror commissioning

Root closed-manifest carrier for ce-ops#123. CI/path review should compare this
branch's `base..HEAD` diff to the authorized path set below. This carrier lists
itself.

Ratified:
Operator dispatch for ce-ops#123 on 2026-06-18: commission sha256-pinned
Gitleaks and TruffleHog mirror artifacts for Linux x86_64 and Linux arm64,
wire the live brownfield secret-preflight verifier, commit locally only, and do
not push, sign, or publish the mirror.

Base:
`8d2a83be700d9337aeaaa7b704e6306da79744c8` (`origin/main` at branch creation).

The changes:
- Four extracted scanner binaries are staged under the 0.2.0 Pages mirror path:
  Gitleaks 8.30.1 and TruffleHog 3.95.6 for Linux x86_64 and Linux arm64.
- `scanner-mirror.fragment.yaml` carries the unsigned signing fragment with
  `{name, version, platform, url, sha256}` for each scanner/platform pair.
- The live driver selects commissioned scanner pins for the host platform and
  continues to refuse unsupported/unpinned/fetch-failed/sha-mismatched scanners.
- Tests cover pinned x86_64 clean, sha mismatch refusal, fetch/unpinned
  fail-closed behavior, env commissioning, and arm64 manifest/hash resolution.

Per-file purpose (the closed path-set - 9 paths; `(A)` add, `(M)` modify):
- **`.ce/changelog/ce123-scanner-mirror.md`** *(A)* - changelog fragment.
- **`.ce/pr-path-manifest.md`** *(A)* - this root closed-manifest carrier.
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

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=4d12552190f8b56f4144ebd7002437b5d749faada2ed8924106475d951ecb716

```text
.ce/changelog/ce123-scanner-mirror.md
.ce/pr-path-manifest.md
docs/downloads/0.2.0/scanners/gitleaks-8.30.1-linux-arm64
docs/downloads/0.2.0/scanners/gitleaks-8.30.1-linux-x86_64
docs/downloads/0.2.0/scanners/scanner-mirror.fragment.yaml
docs/downloads/0.2.0/scanners/trufflehog-3.95.6-linux-arm64
docs/downloads/0.2.0/scanners/trufflehog-3.95.6-linux-x86_64
validators/creator_engine_validator/onboard_apply_live.py
validators/tests/unit/test_onboard_apply_live.py
```
