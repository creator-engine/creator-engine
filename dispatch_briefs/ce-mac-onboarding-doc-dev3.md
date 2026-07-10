# BRIEF — dev-3 — Mac-via-container onboarding runbook (product-lens)

Born-foreman, contained/no-egress (DO NOT push — controller harvests). Fresh branch `ce-mac-container-onboarding` off CURRENT origin/main (git fetch origin main first). Drive to READY-FOR-HARVEST GREEN.

## Goal
Write a clear, PRODUCT-LENS onboarding runbook that lets a macOS user run CE TODAY via a Linux container — because CE's installer + isolation backends are Linux-native, but a Mac user with a container/VM runtime (Docker Desktop / Podman / colima) gets a real Linux kernel inside the container, so the installer sees `uname=Linux` and our EXISTING Linux wheels work (no Mac-native build needed).

## CRITICAL — ground it in the ACTUAL installer, not aspiration
Read `install.sh` (and any install docs) FIRST. Confirm + document the REAL behavior:
- The platform gate (uname checks; what makes it accept linux-x86_64 / linux-aarch64 and refuse Darwin) — cite the actual logic.
- The real install one-liner / command and its prerequisites.
- That running it INSIDE a Linux container (uname=Linux) passes the gate and uses the shipped wheelhouse.
Do NOT invent flags or steps. If something can't be confirmed from the code, mark it "to verify" rather than asserting it.

## Content (the runbook)
A new doc under `docs/guide/` (e.g. `docs/guide/onboarding-macos-container.md`):
1. Who this is for + the one prerequisite: a container/VM runtime on the Mac (Docker Desktop, or Podman/colima). Note Apple Silicon → use linux/arm64 image; Intel Mac → linux/amd64.
2. Step-by-step: start a Linux container (a concrete `docker run` with a maintained base image + a persistent volume for the workspace), run the CE installer inside it, launch the CE controller (the single contained/os-native controller — the solo-dev path, CEO/strangeLoop), verify it works.
3. Where files live + how to get the user's repo into the container (bind-mount their project dir).
4. Caveats: needs the runtime; this is the container path (native-Mac, no-container support is a later option); resource/perf notes.
5. A short "why this works" note: the container provides a Linux kernel → CE's Linux isolation + wheels apply. Keep it accurate.

## Framing accuracy (do NOT get this wrong)
- This is the Docker/Podman/VM container path. Do NOT claim CE ships a Mac-native build. Do NOT call NVIDIA NemoClaw a "harness" or claim it provides the container — OpenShell (NVIDIA's zero-trust sandbox runtime) is the on-platform isolation; this runbook is the simpler standalone Docker-Desktop path. Keep this runbook to the standalone Docker/Podman path; do NOT document OpenShell here.
- PRODUCT-LENS ONLY: no internal infra refs, no ce-ops# numbers, no fleet/seat/controller-internal jargon — write for an external solo developer.

## Scope / allowed paths
The new `docs/guide/onboarding-macos-container.md` + any nav/index file that must list it (check test_v1_docs_reconciliation expectations — a new guide doc may need a README/index entry) + the two carriers (`.ce/changelog/...`, `.ce/pr-manifests/...`). Nothing else.

## On READY
`rm -rf validators/*.egg-info validators/build` then `TMPDIR=/var/tmp PYTHONPATH=validators python -m creator_engine_validator.ce_cli validate-pr --head-ref ce-mac-container-onboarding` GREEN (docs-reconciliation must pass). Report the doc path, what you grounded vs marked to-verify, and `commit && echo SHA`. Do NOT push. NOTE for controller: an end-to-end smoke test (actually run the installer in a fresh Linux container) should follow before handing to a real user.
