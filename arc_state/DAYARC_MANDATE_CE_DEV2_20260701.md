# 🌅 DAY-SHIFT ARC MANDATE — CE-DEV-2 Orchestrator — 2026-07-01

> Operator ENGAGED + ratified 2026-07-01 ~06:40Z. Follows the completed night-arc (#692–708 shipped). Resume anchor for the day shift.

## Thesis
Flip the night-arc's built-but-inert autonomy **LIVE and prove each with a real event**, land the contributor + test-user onboardings, and harden the infra the fleet now depends on. Protect the live install/demo path (NVIDIA pitch) throughout. Drive via workers; never inline.

## Ratified priority (lead lanes) + authority
- **Lead lanes (saturate seats here):** D1 Forge autonomy · D2 Seats autonomy · D5 Infra resilience.
- **Autonomous R-class flips (Operator-granted 2026-07-01):** L3 triage apply-mode · Surface-B autonomous-approve demo · Conveyor arming. (I build+verify then flip; no per-flip re-ask.)
- **D0 Onboarding** runs (contributing-guide in flight on dev-1) but is coordination-bound (external humans) — not a seat-saturation lead.

## Lanes
- **D0 Onboarding (today, coordination-bound):** D0a contributing-guide fix (dev-1 WORKING, branch ce-contributing-guide-ci-steps) → merge → Nitzan first-PR ready. D0b first test user (Arad) live-install + first governed PR. D0c #304 ce-ops#63 scrub in contributing guide; #367 speckit-init if her project needs it.
- **D1 Forge autonomy (LEAD):** L3 triage apply-mode now unblocked (CROSS_REPO_TOKEN fixed 06:35Z; run 28498562998 read 8 queue entries). Confirm apply actually POSTED/labeled (not just counted); close-bot proven (#377/#381 retro-closed); build auto-labeling + lane-config YAML (P1).
- **D2 Seats autonomy (LEAD):** prove first real L2 auto-merge + audit; build `ce automerge kill-switch` CLI; Surface-B autonomous-approve demo (end of arc — deploy broker w/ --run-mode, throwaway docs PR, observe mint+APPROVE, tear down); ce-ops#347 `--run-mode` CLI wiring.
- **D5 Infra resilience (LEAD):** ce-ops#351 relocate merge-queue/wall daemon DGX→VPS (single-point risk); prune ~210 stale worktrees; move main checkout off rc2; dev-4 codex re-auth; dev-3 #337 self-push investigation.
- **D4 Company brain (deferred):** L4 P1 vllm db fix + Knowledge SSOT #166 — GPU-gated (R2); take only if GPU frees.

## Live now / carry-over
L7 auto-releases largely shipped (#698–703; L7-b inert until a release runs). L2 auto-merge LIVE. close-bot proven. CROSS_REPO_TOKEN fixed. ce-ops#378 SSOT merged.

## Seats (at arc start)
dev-1 (non-contained, self-push) — WORKING D0a. dev-3 (contained ce-vps-codex, fetch-egress; #374 stall to re-verify) — idle. dev-4 (contained ce-dgx-codex DGX, strongest; NEEDS codex re-auth) — idle. Launch dev-4 with explicit `CE_DGX_IMAGE=…0.142.4-aarch64`.

## Standing authority (carry-over)
G1–G7 + R1(canary) + R5(re-sign) from prior arcs. Merge gate: ce-dev-2 approval = merge trigger (queue-daemon ~120s). Author≠approver. Signing = non-delegable controller act.
