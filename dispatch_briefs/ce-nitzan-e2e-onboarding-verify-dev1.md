# BRIEF — dev-1 — Nitzan e2e onboarding verify (full path, fresh container) + fix only doc drift

Non-contained, SELF-PUSH as ce-dev-1. This is a VERIFY-then-FIX-DOC-DRIFT-ONLY lane. Produce a REPORT; open a PR ONLY if you find DOC/runbook drift to fix (small). Do NOT change product code in this lane.

## Goal
Our first contributor (Nitzan, Mac via Docker-Linux-container) onboards TODAY. Confirm the FULL onboarding path works end-to-end for a real first-time user now that the fixes merged: #651 (ce onboard RED-G-6 unblock), #654 (installer uv trust), #655 (ce onboard RED-G-4 actionable guidance). We need a clean GREEN end-to-end or a precise list of remaining blockers.

## Test (fresh linux/amd64 container — mirrors the Mac-via-Docker-Linux-container path)
Follow the SHIPPED runbook `docs/guide/onboarding-macos-container.md` EXACTLY as a brand-new user would (read it first; the container path it documents is the one Nitzan uses). In a FRESH `ubuntu:24.04` (or the image the runbook specifies) container with no CE preinstalled:
1. **Install** CE via the public one-liner exactly as the runbook says. Confirm it completes, installs the manifest-pinned uv (post-#654 it should hash-verify), and prints correct next steps (no dead temp-file paths).
2. **`ce brain init`** — confirm it works (the runbook step that #652 added).
3. **`ce onboard`** in a realistic first-time-user setup — confirm it NO LONGER hard-blocks: RED-G-6 should not fire (#651), and if RED-G-4 (ungoverned state-path) appears it must now show the actionable guidance (#655) that lets the user proceed (gitignore .hermes/ → ce init → re-run). Walk that guidance and confirm the user can actually get unblocked.
4. **`ce launch`** — confirm it reaches a working launch (or the expected next step).
Capture exact commands, outputs, and the decisive success/failure of each step.

## Report (your final message)
- A step-by-step PASS/FAIL for install → brain init → onboard → launch, with decisive output.
- VERDICT: is the path HANDOFF-READY for Nitzan today? If not, the precise remaining blocker(s).
- Any DOC/runbook DRIFT you hit (a step that's wrong/missing/out-of-order in onboarding-macos-container.md or welcome.md). 

## If (and only if) you find DOC drift
Open a small docs PR fixing ONLY the drift in `docs/guide/onboarding-macos-container.md` / `docs/guide/welcome.md` (e.g. correct a command, add a missing step, fix version text). Fresh branch `ce-onboarding-doc-drift-fix` off current origin/main. Carrier slug == branch. Do NOT touch product code, install.sh, or any support/isolation file. FULL `ce validate-pr` GREEN, carriers + changelog, work-class line. Self-push, report PR #. If NO drift → REPORT ONLY, no PR.

## Do NOT
- Do NOT change product code (onboard/doctor/installer logic) — if you find a CODE bug, REPORT it as a blocker for a separate ticket, do not fix it here.
- Do NOT touch in-flight lanes' files (support adapters, os_native, broker).
