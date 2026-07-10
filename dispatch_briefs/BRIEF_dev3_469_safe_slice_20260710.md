# DISPATCH — dev-3 BATCH — 2026-07-10 — ce-469 safe slice (3 units, canary UX findings)
Role: implementer foreman. One signal per unit:
`READY-FOR-HARVEST <branch> <full-40-hex-sha>` / `BLOCKED <branch> <one-line-reason>`

## Environment change — read first
Your repo venv was REPAIRED (editable install registered; `.venv/bin/ce` and pytest work).
FULL `ce validate-pr` in-seat is now EXPECTED to run — the environmental-BLOCKED path no
longer applies unless something newly breaks (if it does, name the exact failure class).
Preconditions per unit: `git fetch origin main`, branch off fetched origin/main, worktree
/var/tmp/wt-<branch>, never touch .ce/brain/assertions.yaml.

## UNIT 1 — branch `ce-469-verify-install-root` — class S
Canary finding (embedded): `verify-install` with a non-default `--install-root` reports
against the DEFAULT root — false-green/false-red depending on which root is populated.
Fix: propagate the supplied root to EVERY probe; add a `checking root: <path>` header line
so the effective root is always visible. Locate the verify-install implementation in the
validator package (search for the subcommand registration); tests must cover: non-default
root with populated default root (the false-green case), non-default root missing (true
red), header line present. Files: the verify-install module + its test module + changelog +
carrier (slug=branch). Carrier line: `- **Declared work class:** S`

## UNIT 2 — branch `ce-469-shim-clobber-guard` — class S
Canary finding (embedded, most consequential): installing with a non-default
`--install-root` still writes `~/.local/bin/ce` + `~/.local/bin/cev3` shims unconditionally,
silently clobbering a production install's entry points. Fix, smallest-good: when the
target root is non-default, do NOT write the default-location shims unless explicitly
requested (e.g. an opt-in flag), and when a shim WOULD overwrite an existing file pointing
at a DIFFERENT root, refuse with a message naming both roots and the override. FIRST
diagnose where shim writes happen: if the writing code lives in `install.sh` or any file
whose hash is pinned in the signed `docs/llms-install.md`, STOP and signal
`BLOCKED ce-469-shim-clobber-guard release-class-signed-file` — that variant is a
controller release-op, not seat work. Python-side fix only. Tests for: non-default root
skips default shims, clobber refusal, opt-in override. Files: the installer/onboard module
that writes shims + tests + changelog + carrier (slug=branch). `- **Declared work class:** S`

## UNIT 3 — branch `ce-469-install-root-docs` — class XS
Canary finding (embedded): `CE_INSTALL_ROOT` is respected by tooling but undocumented.
Document it in the NON-SIGNED docs only: the installer reference page and the env-vars
section (locate under docs/ — but NOT docs/llms-install.md and NOT install.sh; those are
signed and get their update in a separate controller release-op). Also add it to relevant
`--help` text if the flag surface lives in the validator package. Files: the non-signed
docs page(s) + optional argparse help string + changelog + carrier (slug=branch).
`- **Declared work class:** XS`

## Stop lines (all units)
install.sh, docs/llms-install.md, ce_cli.py, v3_cli.py, conveyor*.py, daemon_lease.py,
validation_sandbox_*, forge/**, deploy/**, .github/**, launch_runtime.py, seat_reaper.py,
doctor_runtime.py, ticket_reconcile.py, checks/signed_artifact_pins.py,
.ce/brain/assertions.yaml, any file in another unit's carrier. Product lens: zero internal
ticket references in changelog/carrier prose. COMMIT each unit before its signal.
