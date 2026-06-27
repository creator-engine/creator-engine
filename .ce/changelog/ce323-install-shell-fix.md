# ce-ops#323 — install one-liner must pipe to `bash`, not `sh`

- Fixed the Arad pilot runbook install one-liner to pipe `install.sh` to `bash`
  instead of `sh`. `install.sh` is bash-only (`#!/usr/bin/env bash`,
  `set -o pipefail`, `[[ ]]`); piped to `sh` (dash on Ubuntu 24.04) it dies with
  `set: illegal option -o pipefail` then `curl (23) failure writing output`,
  which broke a real test user on Ubuntu 24.04.
- Adopted the canonical hardened form everywhere:
  `curl --proto '=https' --tlsv1.2 -fsSL https://creator-engine.dev/install.sh | bash`.
- Doc half of the published-vs-`main` drift only; the `install.sh` self-recovery
  hardening (re-exec under bash when invoked via `sh`) and the
  `verify-install`/`onboard` command-reference reconciliation are separate
  follow-ups.
