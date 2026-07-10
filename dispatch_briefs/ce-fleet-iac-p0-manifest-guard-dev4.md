# SEED BRIEF — Fleet-IaC P0: fleet-manifest schema + CE-internal-identifier CI guard — SEAT: dev-4 (contained)

**Program:** Fleet-IaC deployment (Operator-authorized start 2026-06-30). **Phase:** P0 (decision-independent, buildable now). **Branch:** `ce-fleet-iac-p0-manifest-guard`. **Role:** implementer. **Work class:** declare by floor (likely `story`/`feature`).
Context report (readable in this repo): `.ce/briefs/fleet-deployment-iac-REPORT-20260630.md`.

## Why P0 (self-contained)
CE will deploy its Autonomous-Fleet to OTHER projects on fresh isolated cloud VMs. The hard requirement is **zero mixing** between CE-internal development and a deployed per-project fleet. P0 is the cheapest, strongest mixing-prevention and is independent of the 3 open architecture decisions: (1) a **fleet-manifest schema** (the per-project deployment descriptor) and (2) a **CI guard that REJECTS any CE-internal identifier appearing in a fleet manifest**.

## Deliverable 1 — fleet-manifest schema
Define the per-project fleet manifest (YAML) + a loader/validator. Mirror the existing manifest→config pattern (study `surfaces/render.py` and how it reads a manifest into build-args/env). Fields (minimum):
- `project`: name/slug, target repo (owner/repo), description.
- `tier`: enum `solo-ceo` | `fleet` (the tier knob).
- `seats`: list (id, role, isolation backend, model-account REF as a pointer — never an inline secret).
- `isolation`: backend selection (os-native | container | gvisor).
- `secrets`/`identity`: POINTERS ONLY (e.g. OpenBao refs / KMS refs) — schema must FORBID inline secret material.
- `egress`: policy.
Keep it a SPEC + schema validation only — the cloud-VM provisioner/wrapper is a later P-tier, NOT P0.

## Deliverable 2 — CE-internal-identifier guard (the load-bearing piece)
A validator check under `validators/creator_engine_validator/checks/` that loads a fleet manifest and **FAILS closed** if it contains ANY CE-internal identifier. Maintain a denylist of internal tokens + regex patterns covering at least:
- The internal code/issue repos: `creator-engine/creator-engine`, `creator-engine/ce-ops`, `ce-ops#`.
- Internal seat/host identifiers: `dev-1`/`dev-2`/`dev-3`/`dev-4`, `ce-dgx-codex`, `ce-vps-codex`, `DGX`, `spark-b824`, `dgx-spark`, Hetzner, the internal tailnet IPs (`100.` tailnet range used internally), `cedev2`/`cedev4`.
- Internal infra: `OpenBao` mount/path prefixes used internally (`ce-kv/`, `forge/`), internal App names (`ce-overwatch`, the internal shared App), `herdr` socket paths.
- The internal brain/model endpoints (the internal vLLM host:port).
(Put the denylist in a well-documented constant so it's auditable/extensible.) Wire the guard into `ce validate-pr` so any PR adding a fleet manifest with an internal identifier fails.

## Deliverable 3 — tests
Unit tests under `validators/tests/unit/`: a clean per-project manifest PASSES; a manifest containing each category of internal identifier FAILS (one case per category); inline-secret in the secrets field FAILS; tier enum validation.

## Contained-seat mechanics (FOLLOW EXACTLY)
- Worktree under **/var/tmp**: `git worktree add -b ce-fleet-iac-p0-manifest-guard /var/tmp/wt-fleet-p0 origin/main` (branch off **origin/main** — your repo at /workspace is the shared checkout, origin/main is current; do NOT `git fetch` (no egress)).
- venv: `.venv/bin/python -m pytest ...`; validator via `ce validate-pr` (TMPDIR=/var/tmp).
- If you add a new `ce` subcommand or documented surface, update the docs the reconciliation test expects (run full suite).
- Add changelog `.ce/changelog/ce-fleet-iac-p0-manifest-guard.md` + regen carrier via `carrier_gen.write_carriers(base=<merge-base>)` (stem == branch slug; rm build/egg-info first).
- Run FULL `ce validate-pr` GREEN in one pass. Compute floor for the work-class line.
- You are no-egress: COMMIT and report `git rev-parse HEAD` + branch (controller harvests/pushes). Do NOT push.

## Stop line
Committed + preflight GREEN + schema + guard wired into validate-pr + tests for every denylist category + carrier/changelog. Report the SHA. Controller harvests.
