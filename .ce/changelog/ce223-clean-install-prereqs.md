### ce-ops#223 — clean-room install auto-provisions or remediates missing prereqs

- New `install_prereqs.py`: pure detect→plan/remediate decisions for `uv`, CPython 3.14, and `ssh-keygen` (package-manager-aware plans + actionable remediation text).
- `docs/install.sh` + `bootstrap_runtime.py` now auto-provision where safe (uv installer; `uv python install 3.14`; ssh-keygen via the host package manager) and otherwise emit a precise remediation and fail closed — instead of an opaque refusal on a fresh host. Idempotent (detect-then-act).
- Closes the PILOT-CRITICAL dead-end where a clean-room install refused on a fresh machine.
