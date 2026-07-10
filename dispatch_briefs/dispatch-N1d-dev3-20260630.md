# DISPATCH — N1d: bootstrap ssh-keygen preflight — dev-3

LANE: make the openssh-client requirement fail EARLY and ACTIONABLY for external users installing CE. Today the signed-spec verification needs `ssh-keygen` (from openssh-client); if it's absent the failure is late/opaque. `docs/install.sh` already has a Debian/Ubuntu remediation hint — surface it earlier and add an actionable error on the §0 manual path too.

WORKTREE: under **/var/tmp** off **origin/main** (NOT /workspace). venv: `.venv/bin/python -m pytest` (no activate). Branch: **ce-n1d-sshkeygen-preflight**. STOP before push; commit + `echo <SHA>`; controller harvests.

## Scope
1. `docs/install.sh`: at the TOP of the bootstrap (before any signed-spec verification step), add a preflight that checks `command -v ssh-keygen`. If missing: print an actionable error naming the package per-distro (Debian/Ubuntu: `sudo apt-get install -y openssh-client`; Fedora/RHEL: `sudo dnf install -y openssh-clients`; macOS: preinstalled/`brew install openssh`) and EXIT non-zero BEFORE attempting verification. Reuse/move the existing remediation hint rather than duplicating it.
2. The §0 MANUAL verification path in `docs/llms-install.md` already documents the openssh-client prereq (just landed in #695) — do NOT touch llms-install.md (it is the signed spec; changing it breaks the signature). Instead ensure the *script* path matches that prose.
3. If there is a Python bootstrap/verify entrypoint that shells out to `ssh-keygen` (search `validators/creator_engine_validator/` for `ssh-keygen` / `shutil.which("ssh-keygen")`), make it raise a clear, actionable error (name the package) instead of a raw CalledProcessError — fail-closed with a good message.

## Evidence required
- A test asserting the preflight triggers the actionable error when ssh-keygen is absent (mock/PATH-strip) — add to the relevant existing test module (e.g. test_install_bootstrap.py or a unit test for install.sh shape).
- `TMPDIR=/var/tmp .venv/bin/python -m creator_engine_validator.ce_cli validate-pr` GREEN.
- Add carrier+changelog via `carrier_gen.write_carriers` (CarrierSpec head_ref='ce-n1d-sshkeygen-preflight', issue='ce-ops#197', kind='fix', scope='install') + a `- **Declared work class:** tiny` (or `story`) line in the carrier.
- ⚠️ Do NOT base work on the `ce-release-0.3.1-rc2` branch. Verify against origin/main.

Report: branch, commit SHA, validate-pr PASS line, files touched.
