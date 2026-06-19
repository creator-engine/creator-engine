# PR path manifest - ce94-127-forge-identity

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce94-127-forge-identity
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Ratified controller relay:
Wave-A fixes ce-ops#94 and ce-ops#127 on one branch, one PR, cross-linking both
tickets. Commit-local only; no push. Rebase onto current `origin/main`, rebuild
the validator app wheel, run the full offline `validators/tests/` suite green,
then signal `DEV3 94-127-DONE <sha>`.

Base:
`b7980e6c849200bcf77cf6547a0511843da194b9` (`origin/main` at branch creation,
post OpenBao P3 #268).

Per-file purpose (closed path-set - 9 paths):
- **`.ce/changelog/ce94-127-forge-identity.md`** *(A)* - changelog fragment cross-linking ce-ops#94 and ce-ops#127.
- **`.ce/pr-manifests/ce94-127-forge-identity.md`** *(A)* - this carrier.
- **`docs/contracts/installer.md`** *(M)* - fixes forge identity binding wording to the bootstrap token `GET /user` source.
- **`validators/creator_engine_validator/onboard_apply.py`** *(M)* - right-sized bootstrap leg now refuses unknown tokens before identity-only and defers fine-grained greenfield capability to fail-closed write legs.
- **`validators/creator_engine_validator/onboard_apply_live.py`** *(M)* - prefix-based PAT classification, fine-grained identity-only probe, and adoption commit identity cache from the bootstrap token `GET /user` login.
- **`validators/tests/unit/test_onboard_apply.py`** *(M)* - #94 coverage for fine-grained pass/defer and unknown-token fail-closed matrix.
- **`validators/tests/unit/test_onboard_apply_live.py`** *(M)* - live probe coverage for identity-only fine-grained PATs and #127 bootstrap-token author binding.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* - app-wheel digest re-pinned after rebuild.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* - rebuilt app wheel from this branch source.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=3e1ee2d0d1caffe09dbf6aac077587f7f2e47033e84797298f59a2365b77c4bd

```text
.ce/changelog/ce94-127-forge-identity.md
.ce/pr-manifests/ce94-127-forge-identity.md
docs/contracts/installer.md
validators/creator_engine_validator/onboard_apply.py
validators/creator_engine_validator/onboard_apply_live.py
validators/tests/unit/test_onboard_apply.py
validators/tests/unit/test_onboard_apply_live.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
