---
slug: ce197-install-robustness
ticket: ce-ops#197
type: fix
scope: install.sh robustness
---

Hardens the bootstrap installer against two fleet-observed install footguns.

- Probes the selected temp staging target before creating the installer
  wheelhouse, honors `TMPDIR`, and falls back to a user cache staging directory
  when free space is below the installer threshold.
- Keeps the disk-space test override behind `CE_INSTALLER_TEST_MODE=1`.
- Expands install-lock refusals with the holder PID, lock path, and copy-paste
  `ps` / `rm -rf` remediation commands.
- Adds focused subprocess coverage for low-temp fallback and lock-held UX.
