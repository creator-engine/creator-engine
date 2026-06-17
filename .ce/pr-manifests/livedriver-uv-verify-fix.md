# PR path manifest — livedriver-uv-verify-fix · userspace-tool verify probes install location (not PATH)

Per-PR carrier (`.ce/pr-manifests/<branch_slug(head_ref)>.md`, the ce-ops#21 convention). CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref livedriver-uv-verify-fix

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below (the carrier
lists itself); the repo-wide fidelity scan requires the declared count and SHA256 to match the fenced block.

> Carrier filename is locked to `branch_slug(head_ref)`. This file is named for branch
> `livedriver-uv-verify-fix` (`branch_slug("livedriver-uv-verify-fix") == "livedriver-uv-verify-fix"`).

Ratified:
Operator/orchestrator-mandated 2026-06-17 (ce-ops#90, 4th PR in the #241→#244 live-driver lineage) —
fix the #244 uv verify-PATH defect dev-3 hit on a live `--apply` + audit the remaining unexecuted legs.
Built by a §7 governed CE seat on base `45bad95`; push/merge + the dev-2 ce-root-v1 re-sign are gated.

Base:
`45bad95` (`main` = #244, live-driver userspace deps — uv-from-mirror design A + 0.2.0 republish).

The defect (dev-3, reproduced):
`uv` installs to `<venv>/bin/uv` (mirror wheel sha-verified, `pip --no-index --find-links … uv`), but
`verify_tool('uv')` fell through to the inherited base `shutil.which('uv')` which searches only
`os.environ['PATH']`; the venv bin is NOT on PATH → `None` → `userspace_tool_verify_failed` at the host
leg → the join legs never ran. Install fine; only the verify's PATH visibility was wrong.

The change (driver-only fix + audit):
`LiveForgeApplyDriver.verify_tool` now branches by tool class — a USERSPACE tool (`uv`) is verified at its
ACTUAL install location (absolute `<scripts>/uv` from the interpreter scripts dir; `uv --version` +
pinned-version match), NOT a PATH search; SYSTEM tools keep the inherited base PATH probe. AUDIT of the
post-`host_dependencies` legs found the SAME class at `cli_exposure` (base `expose_cli` →
`shutil.which('cev3')`, a venv console script off PATH) → fixed with an `expose_cli` override resolving
`cev3` at its install location (PATH fallback preserved). All other legs audited clean (forge/clone
runners inherit `os.environ`/PATH for system `gh`/`git`/`openssl`; `first_project_smoke` runs in-process).
Validator wheel rebuilt from this source into both wheelhouse + mirror copies; both `SHA256SUMS` +
`sha256s_sha256` + validator `required_wheels` sha re-pinned. **uv wheel UNCHANGED** (`b9ecdefa…`).

GREEN-EXCEPT-THE-SIG (by design): `docs/llms-install.md` `value` + `content_sha256` reset to the canonical
placeholder for the dev-2 in-PR `ce-root-v1` re-sign (the `required_wheels` edit forces it — the #244 shape).
Every other content field is correct + reproduced, so the full unit suite is green and the real-SSHSIG
verify test SKIPS on the placeholder (flips to PASS once dev-2 signs).

Per-file purpose (the closed path-set — 9 paths):
- **`.ce/changelog/livedriver-uv-verify-fix.md`** *(A)* — ce-ops#65 release-surface fragment (kind: fixed).
- **`.ce/pr-manifests/livedriver-uv-verify-fix.md`** *(A)* — this carrier (self-inclusive).
- **`docs/downloads/0.2.0/SHA256SUMS`** *(M)* — re-pinned the rebuilt validator-wheel line (uv + all other
  lines byte-unchanged).
- **`docs/downloads/0.2.0/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* — mirror copy of the
  rebuilt validator wheel (byte-identical to the dev wheelhouse copy).
- **`docs/llms-install.md`** *(M)* — updated `sha256s_sha256` (served-mirror SHA256SUMS hash) + the
  validator `required_wheels` sha (rebuilt wheel); RESET `value` + `content_sha256` to the canonical
  placeholder for the dev-2 `ce-root-v1` re-sign (NOT signed). uv `required_wheels` entry UNCHANGED.
- **`validators/creator_engine_validator/onboard_apply_live.py`** *(M)* — `verify_tool` branch +
  `_verify_userspace_tool`/`_userspace_scripts_dirs` (install-location probe), `expose_cli` override +
  `_resolve_console_script`, `scripts_dir` config seam, `version` field on `MirrorUserspaceWheel`.
- **`validators/tests/unit/test_onboard_apply_live.py`** *(M)* — verify-fix regression tests: uv off PATH
  resolves via install-location; fail-closed (absent, version-mismatch); system tool uses base PATH probe;
  end-to-end install→verify PATH-independent; `expose_cli` resolves `cev3` off PATH. Offline.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* — re-pinned the rebuilt validator-wheel line (no uv here;
  design A serves uv from the mirror).
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* — rebuilt 0.2.0 app
  wheel from this source (source parity: `verify_wheel_matches_source`). Clean rebuild, no `build/` leak;
  `_version.py` unchanged.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=2741a390416af70f30e60d43ea6df0ef520436bb5a9baf41da522bc4d27a3b22

```text
.ce/changelog/livedriver-uv-verify-fix.md
.ce/pr-manifests/livedriver-uv-verify-fix.md
docs/downloads/0.2.0/SHA256SUMS
docs/downloads/0.2.0/creator_engine_validator-0.2.0-py3-none-any.whl
docs/llms-install.md
validators/creator_engine_validator/onboard_apply_live.py
validators/tests/unit/test_onboard_apply_live.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
