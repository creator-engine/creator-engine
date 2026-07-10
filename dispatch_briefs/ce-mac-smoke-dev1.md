# BRIEF — dev-1 — Smoke-test the Mac-via-container onboarding path (verification + report)

Non-contained, VPS. This is a VERIFICATION lane → produce a REPORT (not necessarily a PR). Do NOT push code unless you find a clear installer bug worth fixing (and even then, report FIRST).

## Goal
Verify end-to-end that a macOS user can install + run CE via a Linux container TODAY using our existing Linux wheels. We will hand a runbook to a real first user (Nitzan, on a Mac), so we must confirm the path actually works and capture exact steps/errors. The VPS is x86_64 — you'll test the linux/amd64 path (an Apple-Silicon Mac would use linux/arm64; note that as a caveat, don't test it here).

## STEP 0 — confirm you can run containers
Check you have a container runtime: `docker info` (or `podman info`). If you do NOT have access, STOP and report exactly that (so I redirect this to a seat that does) — do not work around it.

## Steps (if you have a runtime)
1. Read `install.sh` (+ any install docs) to find the REAL canonical install command / one-liner + prerequisites. Do not invent it.
2. Start a clean Linux container (a maintained base image, linux/amd64, with a workspace volume; e.g. an ubuntu image). Confirm `uname -s -m` inside = Linux x86_64.
3. Run the CE installer inside the container exactly as a real user would (the published path). Capture: does the platform gate pass (uname=Linux)? do the Linux wheels install? any missing prereqs (python version, system packages, runsc/bwrap for the default backend)?
4. Attempt to bring up the solo-dev controller as a real user would (the documented `ce launch` / controller path, os-native or gvisor as appropriate inside a container — note which backend is reachable in a plain container and whether it needs extra flags/privileges).
5. Capture every error verbatim.

## Report (back to controller)
- Whether a runtime was available.
- The exact install command used + result (success/fail + verbatim errors).
- Whether the contained/os-native controller came up, and any privilege/flag requirements (e.g. does gvisor need --privileged? does os-native fail-closed as expected without bwrap/Landlock?).
- A concrete list of corrections/additions the Mac-via-container runbook (branch `ce-mac-container-onboarding`, in flight on dev-3) needs to match reality.
- Any installer bug you found (describe; do NOT fix unless trivial+obvious, and report first).

Keep it factual and reproducible — this gates a real user's onboarding.
