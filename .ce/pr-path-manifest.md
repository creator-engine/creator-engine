# PR path manifest - v3.5-E.4-fix served trust root + real detached signature

CI passes this to `verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; the
fidelity scan requires the declared count + SHA256 to match the fenced block.

Ratified gate:
`/home/nefarious/projects/creator-engine-canonical/.hermes/research/v35e-e4fix-trustroot-gate-20260610T211500Z/GATE_E4FIX_TRUSTROOT_composed.md`
(sha256 `f6246d0a7bca3537b80611f47871036d93245d07336d8bc3d7b25accddc36b02`; key-custody Fork A,
Operator-ratified 2026-06-10).

Per-file purpose:
- **`docs/keys/ce-root-v1`** *(NEW)* - the served trust root: one OpenSSH `allowed_signers`
  line (`ce-root-v1 ssh-ed25519 <pubkey>`) + custody header (Fork A, Operator-held offline).
- **`docs/llms-install.md`** *(M)* - real detached SSHSIG signature block (`algo: ssh-ed25519`,
  `namespace: ce-spec-v1`, base64 `value`, retained `content_sha256` floor) + §0 stock-`ssh-keygen`
  verify recipe + §0.5 bootstrap leg.
- **`docs/llms.txt`** *(M)* - list `/keys/ce-root-v1`.
- **`docs/contracts/installer.md`** *(M)* - trust-root + bootstrap contract (custody = Fork A,
  canonical-bytes rule, fixed namespace, validator seam).
- **`validators/creator_engine_validator/v3_installer.py`** *(M)* - the `ssh-ed25519`
  injected-runner verifier + `parse_allowed_signers` pinned-key loader + `canonical_spec_bytes` +
  `sign_spec` algo recipe + real `PINNED_KEYS`; the sha256-content floor is unchanged.
- **`validators/tests/unit/test_v3_installer.py`** *(M)* - verifier tests (fake runner:
  pass/reject/missing-binary-fail-closed/runner-exception/bad-base64/wrong-namespace/unknown-key),
  canonical round-trip vs the §0 sed rule, floor regression, and the stock-`ssh-keygen` E2E
  (positive + tampered) through `require_verified`.
- **`validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl`** *(M)* -
  rebuilt from this branch source so the wheel oracle stays green (#185 oracle).
- **`validators/wheelhouse/SHA256SUMS`** *(M)* - re-pinned to the rebuilt app wheel.
- **`.ce/pr-path-manifest.md`** *(M)* - this carrier.

- **base:** `f5be2f6` (origin/main, head of #193).
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=34006efb6feab2b19ff5eced71bce445a98db0c74571ee44d99ca893dada42b7

```text
.ce/pr-path-manifest.md
docs/contracts/installer.md
docs/keys/ce-root-v1
docs/llms-install.md
docs/llms.txt
validators/creator_engine_validator/v3_installer.py
validators/tests/unit/test_v3_installer.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl
```
