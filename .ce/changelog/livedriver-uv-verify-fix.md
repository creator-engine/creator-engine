---
slug: livedriver-uv-verify-fix
date: 2026-06-17
kind: fixed
scope: install / onboard --apply / live-forge driver
issue: ce-ops#90
---

**Fix the userspace-tool verify so a plain-join `onboard --apply` no longer refuses
`userspace_tool_verify_failed` after a correct `uv` install — and resolve the same
PATH-visibility class at the next leg (`cli_exposure`).**

dev-3 hit this on a REAL `--apply`: the #244 driver installs `uv` correctly (the
mirror wheel is sha-verified and `pip install --no-index --find-links … uv` lands
`uv` at `<venv>/bin/uv`, running `uv 0.11.21`), but the verify was broken —
`verify_tool('uv')` fell through to the inherited base `probe_tool` →
`shutil.which('uv')`, which searches only `os.environ['PATH']`; the venv bin is NOT
on PATH, so `which` returned `None` → `userspace_tool_verify_failed` and the join
legs never ran. The install was fine; only the verify's PATH visibility was wrong.

- **`LiveForgeApplyDriver.verify_tool`** now branches by tool class. A **userspace**
  tool (`uv`, in `MIRROR_USERSPACE_WHEELS`) is verified at its ACTUAL install
  location: the absolute `<scripts>/uv` (the interpreter's `sysconfig` scripts dir /
  `dirname(sys.executable)`) is probed and run (`uv --version`, pinned-version match)
  — NOT a PATH search. **System** tools (`git`/`python`/`runsc`/`proxy`) keep the
  inherited base PATH probe unchanged. Fail-closed (missing / non-runnable / wrong
  version → still refuses).
- **Audit (break the whack-a-mole):** the legs after `host_dependencies` had never
  run in a real userspace onboard. The next one, `cli_exposure`, had the SAME class
  of bug — the base `expose_cli` does `shutil.which('cev3')` to target the `ce` shim,
  and `cev3` is a venv console script off PATH. **Fixed** with a
  `LiveForgeApplyDriver.expose_cli` override that resolves `cev3` at its install
  location (falling back to PATH for non-venv layouts). The remaining legs were
  audited and are clean: the forge legs + workspace clone spawn `gh`/`git`/`openssl`
  via runners that inherit `os.environ` (PATH present; system tools), and
  `first_project_smoke` runs the v3 CLI in-process (no PATH dependency).

The validator wheel is rebuilt from this source into both the dev wheelhouse and the
mirror copy; both `SHA256SUMS` + the manifest's `sha256s_sha256` + validator
`required_wheels` sha are re-pinned (reproduced). The `uv` wheel is UNCHANGED
(`b9ecdefa…`). `docs/llms-install.md`'s signature is left at the canonical placeholder
for the dev-2 in-PR `ce-root-v1` re-sign (the `required_wheels` edit forces it).
