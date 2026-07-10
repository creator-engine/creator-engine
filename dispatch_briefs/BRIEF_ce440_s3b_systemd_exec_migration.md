# BRIEF — ce-440-s3b — migrate repo systemd units cev3 → ce (ce-ops#440 slice 3b)

Role: implementer (dev-1 self-push). Branch: `ce-440-s3b-systemd-exec-migration` off freshly-fetched origin/main.

## Deliverable
Migrate the two direct `cev3` callers in repo systemd units to the unified `ce` surface (design SSOT: CE440_CLI_UNIFICATION_DESIGN_20260704.md, "cev3 deprecation path" + S3):
1. `deploy/systemd/ce-integrator-daemon.service:11` — `ExecStart=/usr/bin/env cev3 queue-daemon …` → `/usr/bin/env ce queue-daemon …` (args unchanged).
2. `deploy/systemd/ce-review-pickup-daemon.service:11` — same rename, args unchanged.
3. `validators/tests/unit/test_gate_daemons_systemd.py:39` — prefix assertion `("/usr/bin/env cev3 ", "/usr/bin/env bash ")` → accept `"/usr/bin/env ce "` (drop the cev3 arm; keep the bash arm).

## MANDATORY precondition (verify before editing; BLOCKED-report if it fails)
`ce queue-daemon --help` and `ce review-pickup --help` must resolve through the S1 shim with parity to `cev3` (rc/stdout shape). These are INTERNAL-group verbs (#782 lock-in) — internal marking is fine, absence is a blocker. If either verb is not routable via `ce`, STOP: signal `BLOCKED ce-440-s3b <reason>` — do NOT invent a routing.

## Novelty (controller-verified 2026-07-04 ~16:15Z, semantic check done)
Seam = repo systemd units invoking `ce`. origin/main still has `cev3` in both ExecStart lines and in the test assertion; deploy/queue-daemon/ launcher already landed on main (risk-4 precondition satisfied). No in-flight work touches these paths (A1=deploy/conveyor-daemon+daemons; S3a=docs only, deploy/ excluded).

## Constraints
- ONLY the 3 files above + changelog + carrier. Allowed path set (closed):
  deploy/systemd/ce-integrator-daemon.service · deploy/systemd/ce-review-pickup-daemon.service ·
  validators/tests/unit/test_gate_daemons_systemd.py · .ce/changelog/ce-440-s3b-systemd-exec-migration.md ·
  .ce/pr-manifests/ce-440-s3b-systemd-exec-migration.md
- cev3 console-script stays installed/byte-identical (S2 owns deprecation): do not touch pyproject/v3_cli/ce_cli.
- NEVER add --dry-run or drop-in content to repo units (live-shape, CI-asserted).
- No docs edits (S3a owns them), no install.sh/downloads (signed-release-coupled).
- Changelog `.ce/changelog/ce-440-s3b-systemd-exec-migration.md` required; carrier regenerated via carrier_gen API `write_carriers(base=<merge-base vs origin/main>)`, stem == branch name.

## Preflight (standing ce-ops#303)
Run the FULL local `ce validate-pr` (CI-parity) GREEN in ONE pass before push; do not discover gates via CI.

## PR + evidence
Open PR to main, title `ce-ops#440 slice 3b: migrate repo systemd units cev3 -> ce`. Body: exactly one line `- **Declared work class:** tiny` (enum tiny|story|feature|epic) + "Part of ce-ops#440 (slice 3b)".
Signal when PR is open: `READY-FOR-HARVEST ce-440-s3b-systemd-exec-migration <40-hex head sha> PR #<n>`.

## Stop line
No approve, no merge, no enqueue, no review of your own PR. Controller reviews and holds the gate.
