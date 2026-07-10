# BRIEF — dev-1 — `ce onboard` RED-G-4 onboarding-papercut: VERIFY (online) then FIX if real

Non-contained, SELF-PUSH as ce-dev-1. This is a VERIFY-THEN-CONDITIONALLY-FIX lane. Fresh branch only if a fix is warranted: `ce-onboard-state-path-bootstrap` off CURRENT origin/main (`git fetch origin main` first). Drive to a GREEN PR ONLY IF a fix is needed; otherwise produce a clear REPORT and do not open a PR.

## Background (confirmed facts)
- PR #651 (merged) fixed the RED-G-6 packaging blocker: `ce onboard` no longer refuses in a user repo for that reason.
- A follow-up haiku verification found: in a BARE user git repo, run **offline** (`ce onboard --offline --no-launch`), `ce onboard` now refuses **RED-G-4 (ungoverned state-path)** until the user manually creates `.hermes/` AND gitignores it; after that, doctor passes and onboard proceeds to the install step.
- OPEN QUESTION: is RED-G-4 a REAL first-time-user blocker, or just an artifact of `--offline` skipping the install phase (which may itself provision/guide the governed state path)? Our first contributor (Nitzan, Mac-via-container) onboards TODAY, so we must know.

## Step 1 — VERIFY (decisive, in a realistic setup)
Run the FULL onboard path a real first-time user would hit (NOT offline-only) in a fresh user project git repo, mirroring the Mac-container path (linux/amd64 ok). Use the installed `ce` (or `PYTHONPATH=validators .venv/bin/python -m creator_engine_validator.ce_cli`). Determine concretely:
1. Does the NORMAL (online / full) `ce onboard` flow PROVISION or clearly GUIDE the user through the governed state path (`.hermes/`), so a real user is NOT stuck on RED-G-4?
2. Or does a real first-time user hit an OPAQUE RED-G-4 refusal with no actionable guidance → genuinely blocked?
Capture exact commands, CWD, and decisive output (ok status, refused_clauses, reason, any guidance text).

## Step 2 — DECIDE + ACT
- **If NOT a real blocker** (onboard provisions/guides .hermes, or the refusal is clearly actionable): STOP. Write a concise REPORT stating the onboarding path is clean for Nitzan and why. No PR.
- **If it IS a real blocker** (opaque refusal, user stuck): FIX `ce onboard` so a first-time user is not stranded — EITHER have onboard provision the governed state path as part of its flow, OR emit a clear, actionable next-step instruction telling the user exactly what to do (create+gitignore `.hermes/`, or run the specific command). Match the EXISTING onboard/doctor design (read `ce_onboard.py` + `doctor_runtime.py` first). Add a test proving a bare user repo no longer leaves the user stuck (onboard either advances or gives actionable guidance). Do NOT weaken RED-G-4's governance meaning where it legitimately applies.

## Do NOT
- Do NOT touch `install.sh` (your #654 is in review), `os_native_backend.py`, `support_runtime.py`, or the support-agent files — other lanes in flight.
- Do NOT auto-create governed state in a way that bypasses or weakens governance; the fix is about UX/guidance + safe provisioning, not removing the gate.

## Gates (only if you open a fix PR)
- FULL `ce validate-pr` GREEN in ONE pass (`TMPDIR=/var/tmp`). Carriers (manifest via carrier_gen API, rm build/egg-info first) + `.ce/changelog/<slug>.md`. PR body work-class line. Product-lens. Report PR # + head SHA. Self-push, do NOT merge/approve.
- If REPORT-only: just report your findings + the verdict; no PR.
