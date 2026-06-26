# PR path manifest - ce219-ring1-codex-enforcement

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce219-ring1-codex-enforcement
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Base:
`origin/main` at branch handoff.

- **Declared work class:** feature

Diagnostic findings:
- Codex PreToolUse registration already exists and keeps
  `allow_managed_hooks_only = true`.
- The generated matcher omitted `Read`, so credential reads could bypass the
  Ring-1 credential-path deny in contained Codex seats.
- The managed hook command did not receive container-visible
  `CE_LEDGER_ROOT` / `CE_REVIEWER_AUTHORITY_REF`; the hook could fire but lose
  governed-posture and reviewer-authority context inside the clean harness
  environment.
- The adapter/validator bridge already denies restricted mechanics without a
  matching reviewer-authority envelope and already avoids logging credential
  values in deny output.

Per-file purpose:
- **`.ce/changelog/ce219-ring1-codex-enforcement.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce219-ring1-codex-enforcement.md`** *(A)* - this closed path-set carrier.
- **`.codex/requirements.toml`** *(M)* - require `Read` in the committed managed Codex PreToolUse matcher.
- **`deploy/dgx-runsc/run-codex-runsc.sh`** *(M)* - generate a managed hook command with `Read` coverage and container-visible governance refs.
- **`deploy/vps-runsc/run-vps-runsc.sh`** *(M)* - same managed hook hardening for VPS runsc seats.
- **`validators/creator_engine_validator/hook_pack_confirm.py`** *(M)* - make Codex managed-hook confirmation require `Read` coverage.
- **`validators/tests/integration/test_codex_hook_pack_pretooluse.py`** *(M)* - cover restricted mechanic deny, credential read deny without secret echo, manifest advisory allow, and permitted allow through the real Codex hook wrapper.
- **`validators/tests/unit/test_dgx_runsc.py`** *(M)* - pin DGX generated config matcher and governance-ref command binding.
- **`validators/tests/unit/test_hook_pack_confirm.py`** *(M)* - update Codex managed-hook confirmation fixtures for `Read`.
- **`validators/tests/unit/test_vps_runsc_launcher.py`** *(M)* - pin VPS generated config matcher and governance-ref command binding.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=10

AUTHORIZED_PATHS_SHA256=8e75e56b976a0a0e70441377ac55b227dd312071fa80862d083292283dadf058

```text
.ce/changelog/ce219-ring1-codex-enforcement.md
.ce/pr-manifests/ce219-ring1-codex-enforcement.md
.codex/requirements.toml
deploy/dgx-runsc/run-codex-runsc.sh
deploy/vps-runsc/run-vps-runsc.sh
validators/creator_engine_validator/hook_pack_confirm.py
validators/tests/integration/test_codex_hook_pack_pretooluse.py
validators/tests/unit/test_dgx_runsc.py
validators/tests/unit/test_hook_pack_confirm.py
validators/tests/unit/test_vps_runsc_launcher.py
```
