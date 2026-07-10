# BRIEF — ce-415-brownfield-enabled-fix — derive brownfield.enabled from real probe signals (QUEUED UNIT 3)

Role: implementer (dev-3, contained, foreman mode). UNIT 3 — start after your D2 unit signals.
⚠️ SAME-FILE SERIALIZATION: touches v3_cli.py (your D1 territory) — branch
`ce-415-brownfield-enabled-fix` off freshly-fetched origin/main; if your D1 has not merged yet
when you start, branch STACKED on your local D1 tip and say STACKED-ON in the signal.
Worktree /var/tmp; venv `.venv/bin/python -m pytest`, PYTHONPATH=validators, TMPDIR=/var/tmp.

## Problem (embedded ticket content — you cannot read ce-ops)
Found by the 2026-07-03 D1a install canary (live one-liner, clean empty non-git env):
`v3_cli.py::_detect_brownfield_project` (~line 583) hardcodes `"enabled": True` unconditionally,
and `v3_installer.py::brownfield_detected_facts` (~line 2826) does
`bool(probe.get("enabled", True))`. Result: inventory in a fully-empty non-git directory reports
`brownfield.enabled → detected:True` while also reporting `brownfield.history.mode →
detected:absent`, 0 workflows, 0 test commands — self-contradictory. A stub never wired to the
real `history.present` signal. Not an install blocker, but --plan/brownfield_adoption docs imply
`enabled` reflects real detection.

## Deliverable (ticket's fix direction)
Derive `enabled` from the real probe signals (history present / workflows / test commands
detected); default paths must not silently flip to True. Unit test: empty non-git dir →
enabled:False; a dir with real signals → enabled:True. Behavioral, follow existing test patterns
for the installer/inventory modules.

Files (closed set): validators/creator_engine_validator/v3_cli.py ·
validators/creator_engine_validator/v3_installer.py · their test module(s), named in carrier ·
changelog · carrier (stem == branch). ⛔ signed-artifact stop-line. Preflight: FULL validate-pr;
known env-gap gates (ssh-keygen, libsodium) may false-RED → if the ONLY failures are those AND
your touched-module tests pass, signal with PREFLIGHT-NOTE. Work class: tiny.
Commit `installer: derive brownfield.enabled from real probe signals`, emit
`READY-FOR-HARVEST ce-415-brownfield-enabled-fix <40-hex sha>` (+ STACKED-ON / PREFLIGHT-NOTE as
applicable). Stop line: no push/PR/review/signing.
