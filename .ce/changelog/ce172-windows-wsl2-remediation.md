---
slug: ce172-windows-wsl2-remediation
date: 2026-06-21
kind: changed
scope: installer planner remediation / unsigned docs
issue: ce-ops#172
---

Add a non-release-signing Windows via WSL2/Ubuntu remediation slice to the
Python installer planner and unsigned public install surfaces.

- Native Windows platform names now refuse with a concrete WSL2 + Ubuntu
  remediation instead of a bare unsupported-platform message in the Python
  planner path.
- Public install docs now tell Windows users to install WSL2 with Ubuntu first,
  then run the existing Linux installer inside WSL2.
- `docs/install.sh`, `docs/downloads/0.2.0/SHA256SUMS`, and the signed
  `docs/llms-install.md` bundle remain byte-for-byte unchanged from `origin/main`.
  Native Windows one-liner remediation is deferred to an authorized ce-root-v1
  signing lane.
