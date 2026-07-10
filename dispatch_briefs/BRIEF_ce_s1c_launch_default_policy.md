# BRIEF — ce-s1c-launch-default-policy — onboarding emits runtime-policy-record; `ce launch` resolves it by default, fail-closed (QUEUED UNIT, dev-4)

Role: implementer (dev-4, contained, foreman mode). START CONDITION (all true): (1) your ce-434
unit has signaled, (2) `git fetch origin` shows origin/main contains a commit titled with
"ce-s1a-docker-runner-backend" (or its PR # suffix) — this unit consumes that unit's `docker`
backend key + `controller` role enum; poll fetch until true. Branch `ce-s1c-launch-default-policy`
off that freshly-fetched origin/main. Worktree /var/tmp; venv `.venv/bin/python -m pytest`,
PYTHONPATH=validators, TMPDIR=/var/tmp. (Your ce-445-c5prep-daemon-smoke unit is file-disjoint —
run it as a parallel thread, not serialized behind this.)

## Why (embedded; Operator-ratified day-arc: contained-by-default tenant launch)
Bare `ce launch` today spawns the harness RAW on the host: launch_runtime.py launch() at
runtime_policy=None goes straight to TmuxVisibilityBackend.ensure_surface (~line 1033) — the
container machinery is reached ONLY with an explicit --runtime-policy. Onboarding writes only a
posture note (.ce/state/onboard/runtime/posture.json, onboard_apply.py provision_runtime
~308-331) that NOTHING reads at launch. Ratified design decisions (controller, under the
2026-07-05 day-arc mandate):
- D-i FAIL-CLOSED: bare `ce launch` with no runtime-policy-record REFUSES with a crisp remediation
  message (how to re-run onboarding to emit the record) AND a visible explicit opt-out flag
  (e.g. `ce launch --backend host` or equivalent existing spelling) that preserves today's raw
  behavior for users/fleet who explicitly ask. No silent raw fallback.
- D-ii the record's image_ref points at the canonical SEAT image (ghcr
  .../ce-seat, manifest-LIST digest pin; a placeholder pin constant is acceptable until first
  publish — wire it through surfaces/manifest.yaml or the release-manifest seam, follow how
  ce-runtime pins are plumbed).

## Deliverables
1. onboard_apply.py provision_runtime: for the container-first default, write a REAL
   `kind: runtime-policy-record` at a well-known path (recommend
   .ce/state/onboard/runtime/runtime-policy.yaml): isolation_backend=docker, role=controller
   (both exist on main once your start-condition is met), image_ref=<digest-pinned seat image>,
   mount_manifest = tenant workspace + EXPLICITLY ENUMERATED agent config dirs (claude + codex
   config/auth dirs) — nothing else; forbidden-mount rules stay authoritative. Keep writing
   posture.json for back-compat.
2. launch_runtime.py launch(): default-resolution seam — when runtime_policy is None, load the
   well-known path; found → validate + proceed via the existing runtime_backend_bridge path;
   missing → REFUSE (fail-closed, D-i) with remediation + the explicit opt-out documented in the
   message. Dry-run branch (~887-896) stays side-effect-free.
3. Contract/docs: docs/contracts/runtime-policy.md — document the well-known path + default
   resolution + opt-out. If `ce launch --help` text changes, remember the docs-reconciliation
   test coupling (README may need the same touch).
4. Tests: behavioral — record emitted by provision_runtime validates against the schema; launch
   with record present composes the docker backend (mock runner); launch with record absent
   refuses with the remediation text; explicit opt-out still works; dry-run unchanged. Hermetic.

SEMANTIC NOVELTY CHECK FIRST: confirm on your fetched main that launch() still has no default
policy resolution; if it does, signal BLOCKED already-resolved with evidence.

## STOP lines
- ⛔ Do NOT touch runner/*, runtime_backend_bridge.py, checks/ce_runtime_policy.py, or the schema
  file — that unit is merged before you start; if you need a change THERE, signal BLOCKED with the
  exact need instead of editing.
- ⛔ Do NOT weaken forbidden-mount rules or any refusal path. No secrets/credentials in any
  emitted artifact — the record carries refs and paths only.
- ⛔ Never sign anything; signed-artifact gate failure = STOP and report bytes.
- ⛔ No review/approve/merge/enqueue. Do not revert others' edits.

## Evidence bar
Full `ce validate-pr` GREEN one pass before commit-for-harvest (carrier-gate-only failure = known
contained-seat gap, say so). Changelog + carrier. Declared work class: feature.
Signal: `READY-FOR-HARVEST ce-s1c-launch-default-policy <40-hex sha>`.
