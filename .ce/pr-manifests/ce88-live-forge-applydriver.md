# PR path manifest — ce-ops#88 · production live-forge `ApplyDriver` (Phase 1)

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base 3666706 --manifest-dir .ce/pr-manifests --head-ref ce88-live-forge-applydriver
```

and requires this PR's `base..HEAD` diff (`creator-engine` `main@3666706`..HEAD) to equal
exactly the authorized path-set below (the carrier lists itself); the repo-wide
`path_manifest_fidelity` scan requires the declared count and SHA256 to match the fenced block.

Ratified gate:
Operator-RATIFIED ce-ops#88 live-forge gate-spec (ce-ops@`33777df`, amended `338c98f`
ceiling-driven minter + `33331e7` verify_app_installation→Phase-1); ratified Scope
`ce88-live-forge-applydriver` (`ratified_scope_sha ce8fca61…`, `approver_ref 3a4dd8ec…`).
The wheelhouse wheel rebuild + `SHA256SUMS` re-pin is the declared mechanical co-move (the
edited driver/minter source is wheel-shipped; the packaging contract byte-checks the bundled
`.py` against source). `_versions.py` + `test_version_boundary.py` move because Phase-1 adds
the new `onboard_apply_live` v3 module (V3_RUNTIME 42→43).

Per-file purpose (the closed path-set — 18 paths):
- **`.ce/pr-manifests/ce88-live-forge-applydriver.md`** *(A)* — this carrier (self-inclusive).
- **`.ce/changelog/ce88-live-forge-applydriver.md`** *(A)* — the per-PR changelog fragment.
- **`validators/creator_engine_validator/onboard_apply_live.py`** *(A)* — `LiveForgeApplyDriver`
  (forge read legs + verify-first plain-join apply) + the fail-closed `live_forge_select` factory
  + the host-side PEM signer.
- **`validators/creator_engine_validator/forge/scoped_token.py`** *(M)* — the ceiling-driven
  three-tier minter (never-list / escalation-gated default-deny / read-mostly baseline) +
  `escalation_authority` on `TokenRequest`.
- **`validators/creator_engine_validator/v3_forge_join.py`** *(M)* — declares its pre-existing
  `contents:write` escalation authority under the new single enforcement point.
- **`validators/creator_engine_validator/v3_cli.py`** *(M)* — wires `live_forge_select` at the
  zero-arg `_onboard_apply_driver` seam call sites + revoke-on-finish.
- **`validators/creator_engine_validator/_versions.py`** *(M)* — registers `onboard_apply_live`
  in the v3 module taxonomy.
- **`validators/tests/unit/test_onboard_apply_live.py`** *(A)* — Mode-B acceptance (#44).
- **`validators/tests/unit/fixtures/ce88_live_forge/*`** *(A, 6 files)* — VERBATIM `gh api`
  captures + `CAPTURE.md` (capture commands/date) + the derived already-CE contents envelope.
- **`validators/tests/unit/test_scoped_token.py`** *(M)* — re-scoped to policy-ceiling semantics.
- **`validators/tests/unit/test_version_boundary.py`** *(M)* — V3_RUNTIME count 42→43.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* — rebuilt
  from this branch's source (the driver/minter modules are wheel-shipped).
- **`validators/wheelhouse/SHA256SUMS`** *(M)* — re-pinned for the rebuilt wheel.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=18

AUTHORIZED_PATHS_SHA256=a99e26f4ea49be377a80f794c6b1470b332deb954e8837a0d017303dae59071f

```text
.ce/changelog/ce88-live-forge-applydriver.md
.ce/pr-manifests/ce88-live-forge-applydriver.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/forge/scoped_token.py
validators/creator_engine_validator/onboard_apply_live.py
validators/creator_engine_validator/v3_cli.py
validators/creator_engine_validator/v3_forge_join.py
validators/tests/unit/fixtures/ce88_live_forge/CAPTURE.md
validators/tests/unit/fixtures/ce88_live_forge/contents_ce_validate_yml_already_ce.json
validators/tests/unit/fixtures/ce88_live_forge/contents_validate_yml.json
validators/tests/unit/fixtures/ce88_live_forge/protection.json
validators/tests/unit/fixtures/ce88_live_forge/repo.json
validators/tests/unit/fixtures/ce88_live_forge/user_response_headers.txt
validators/tests/unit/test_onboard_apply_live.py
validators/tests/unit/test_scoped_token.py
validators/tests/unit/test_version_boundary.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
