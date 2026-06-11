# PR path manifest - CE-DEV-1 trust root

CI passes this to `verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; the
fidelity scan requires the declared count and SHA256 to match the fenced block.

Ratified gate:
Operator-authorized ce-ops#6 item ②, escalation `esc-dev1-trust-root`,
2026-06-11. Adds the CE-DEV-1-held team-mode trust-root public key; private
key custody remains CE-DEV-1 encrypted `~/.ce-keys` and never enters the repo
or a governed seat.

Base:
`2ca377d2e381501b848f2754099f5c91c4d2a2fb` (origin/main, re-derived live).

Per-file purpose (the closed path-set - 6 paths, as ratified):
- **`.ce/pr-path-manifest.md`** *(M)* - this carrier: authorized path-set count,
  hash, fenced block, base, and ratification note.
- **`docs/keys/ce-root-v1`** *(M)* - append the `ce-dev1-root-v1` allowed-signers
  principal and custody note.
- **`validators/creator_engine_validator/v3_installer.py`** *(M)* - mirror the
  served trust-root line in `PINNED_KEYS`.
- **`validators/tests/unit/test_v3_installer.py`** *(M)* - assert both trust-root
  principals parse and mirror the served file byte-for-byte.
- **`validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl`**
  *(M)* - rebuilt from final branch source.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* - re-pinned for the rebuilt wheel.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=c57669c5f3d8f6c36b9fa8aba8babea599d5cb2f63d62ba9c076d356c36ecfcd

```text
.ce/pr-path-manifest.md
docs/keys/ce-root-v1
validators/creator_engine_validator/v3_installer.py
validators/tests/unit/test_v3_installer.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.1.0-py3-none-any.whl
```
