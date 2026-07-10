# RESUME STATE — CE-DEV-2 — 2026-07-05 ~14:00Z (ACCOUNT SWITCH checkpoint — weekly limit)

> MEMORY.md first. Supersedes RESUME_STATE_CE_DEV2_DAYARC_20260705T0950Z.md. Arc SSOT =
> DAYARC_MANDATE_CE_DEV2_20260705.md (execution log current through ~13:45Z).
> ⭐ FULL THREAD SERIALIZATION of this session (design + architecture, per-subject):
> **~/creator-engine/tmp/thread-20260705/** — READ INDEX.md THERE FIRST for anything deeper
> than this checkpoint. Written because we switched Claude Max accounts at weekly limit.

## ⏸️ AWAITING-OPERATOR
1. ce-seat ghcr package visibility click — AFTER its first publish during the 0.3.2 ceremony
   (same click as ce-runtime, which is DONE + verified public).
2. Optional: narrow mythos-ce App back to selected {mythos, ce-canary-sandbox} post-canary
   (Operator granted all-repos; noted, their call).

## STANDING OPERATOR DIRECTIVES (this session)
- NO IDLE CONTROLLERS: if a seat's next unit is blocked on a merge, dispatch disjoint backlog
  work immediately.
- Dark-factory direction RATIFIED-in-conversation → SSOT = ce-ops#454 (5 pieces + all design
  comments). Controller trends toward arc-author; forge automation serves lanes; ephemeral
  spawn-on-event controllers (NanoClaws precedent); gate stays singleton; signing stays here.

## BOARD @ serialization (verify live before acting — fork wrote open-state-handoff.md with exact state)
- #819 s1c: APPROVED on head 37f9e341, MERGEABLE/CLEAN, daemon enqueuing — its merge fires
  dev-4's Unit 6 poll (corrected: git log --grep '#819', NOT branch slugs).
- #822 (dev-3 skew follow-ups, head 899cefd0): Sonnet review was RUNNING at switch — check
  task result / re-dispatch reviewer if lost; then approve-on-green as ce-dev-2.
- dev-1: batch 4 = ce-451-surfaces-checker-hardening (story; KEEP-MAIN-GREEN allowlist
  constraint) + ce-454-dependency-unlock-contract (tiny, docs-only). Brief:
  /var/tmp/BRIEF_dev1_batch4_451_unlock_design.md sha 7978aebb…
- dev-3: ce-runner-helper-dedup (story) + ce-brownfield-refusal-message (tiny, NEW test file
  only). Brief: /var/tmp/BRIEF_dev3_runner_dedup_refusal_msg.md sha 120f2172…
- dev-4: idle-polling for #819 merge → ce-onboard-relaunch-ux (brief on seat).
- Parked: ce-415-followup-tinies at .ce/wt-ce415-followup-harvest (rebased 6a7dd5dc) — merges
  AT the 0.3.2 ceremony (its schema edit needs the re-signed answers_schema_sha256 pin).

## NEXT AFTER SEAT UNITS LAND → 0.3.2 CEREMONY (checklist IN THE MANDATE FILE, incl. seat-image
## publish→pin→click sequencing from #819's review + parked-branch merge + heredoc regen +
## llms-install 239 + wheel unzip-grep + controller-inline ce-root-v1 sign + publish + canary
## re-runs A/B/C + Arad handoff pack). Canary C's PEM apply = controller-inline act, pending.

## WATCHERS at switch (all die with the session — RE-ARM in new session): seat-signals grep
## (READY/BLOCKED, beware false-positives from brief text in panes), daemon-log errors
## (rollback-launch.log in d9bfe94b scratchpad), PR-board diff loop. Wall daemon itself is a
## HOST process (pid ~2009267) — survives, check pgrep queue-daemon.
## Memory files updated this session: ce-canary-dispatch-needs-catchall-agent,
## ce-ephemeral-controllers-nanoclaws-direction, ce-install-sh-coupled-to-signed-release
## (answers_schema pin), ce-herdr-dispatch-landing-misread (lost-Enter signature), MEMORY.md.
