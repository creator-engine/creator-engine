# RESUME STATE — CE-DEV-2 — 2026-07-09 ~17:35 UTC — STRANGELOOP1F (EMERGENCY MIGRATION)
# Supersedes STRANGELOOP1E. Written during EMERGENCY CONTROLLER MIGRATION DGX→VPS
# (Operator directive: DGX crashed again — dev-4 container down, launcher toml wiped from /tmp.
# Move ce-dev-2 controller to the VPS with every piece of controller identity data.)
# A controller resuming from this file may be running ON THE VPS (dev1). Verify host first: `hostname`.

## WHY THIS CHECKPOINT EXISTS
Second DGX incident of 2026-07-09 (first: 12:54 host reboot). dev-4 container exited(255) at 17:28;
`docker start` fails: bind source `/tmp/creator-engine-dgx-runsc-codex-config-1002-cedev4.toml` missing
(the /tmp launcher-toml footgun AGAIN — regen recipe: deploy/dgx-runsc/run-codex-runsc.sh lines ~287-315,
UNQUOTED env values in hook command, rewrite via `sed -i` never `tee`). Operator ordered immediate
controller migration to VPS instead of another in-place recovery.

## BOARD at cut (~17:35 UTC)
- **21 merged today** (#908–#929 minus #912). Merge queue EMPTY. Only open PR: **#912** (Operator-held design preview).
- Gate ce-queue-daemon: systemd on DGX, active, failed_count=0. ⚠️ Gate runs ON THE DGX — if DGX fully dies,
  gate redeploy per ce-ops#895 script from ~/ce-daemon-main (memory: ce-queue-daemon-systemd-dgx-deployment).
- Brain-ledger window: OPEN (freed by #929), held by ce-516 Item-3 worker (in flight, will die with this session).
  Serialized queue after it: ce-478 pyproject pin → ce-453 Part A → #500 slices a/d.

## IN-FLIGHT CONTROLLER WORKERS at cut — ALL DIE with this session; transcripts under
`/tmp/claude-1003/-home-cedev2-creator-engine/*/tasks/` on the DGX (salvage copy included in migration bundle)
| Worker | State at cut | Post-migration action |
|---|---|---|
| Harvest ce-490 (dev-4) @221c8bd8 | resumed, running — BLOCKED anyway: dev-4 container is DOWN (bundle extraction impossible) | Re-run AFTER dev-4 restored; manifest .ce/pr-manifests/ce-490-contained-launch-preflight-s1.md |
| Harvest ce-497 @4871b899 + ce-506 @b845d9f0 (dev-3) | resumed, running | Re-dispatch fresh from VPS controller (extraction via local docker exec on dev1 — simpler from there). ce-506 caveat: seat venv broken (ce-ops#521), controller preflight is sole attestation; docs boundary lens |
| ce-496 rescue (dev-1 branch, unpushed 6f85f4de) | resumed, running | Re-dispatch: scrub confidentiality literals, NEVER weaken tests, gap-honesty lens |
| ce-516 Item-3 brain-window (worktree on DGX) | resumed, running | Re-dispatch: workflow Fail-open comment fix + record-65 fresh precompute (byte-change rule); holds exclusive ledger window |
| ops_triage | DONE — ce-ops#521 filed (dev-3 venv defect) | none |

## SEATS at cut
- **dev-4 (DGX ce-dgx-codex): DOWN** — exited(255) 17:28, start blocked on missing /tmp toml. Pane was w4:p1.
  ce-490 committed work is SAFE in its overlay img (committed = survives). Its NEW unit WIP (ce239-wall-openbao-supplier)
  possibly lost if uncommitted. Restore per gotchas: regen toml → mv stale .gvisor.overlay.img.<cid> aside if start still fails → start →
  `herdr pane list` FIRST → re-dispatch current unit brief.
- **dev-3 (VPS ce-vps-codex, pane w1:p1): IDLE + MALFORMED DISPATCH PENDING** — queued prompt is literal
  `Implement {feature}` (template placeholder bug — composer/dispatch defect, ledger it). Seat has NOT started it.
  Correct brief exists: `.ce/briefs/BRIEF_portability_guard_hygiene.md`. Re-dispatch properly (pointer+SHA, self-contained).
  Two un-harvested READYs: ce-497 @4871b899, ce-506 @b845d9f0.
- **dev-1 (VPS tmux ce-dev1-orchestrator:2.0): WORKING** ce-followups-20260708, validate-pr on 11cea6e9, 19% ctx left —
  compact at boundary ordered. ce-496 branch parked unpushed at 6f85f4de (rescue pending).
- **Arad-install codex controller (DGX tmux ce-orchestrator:arad-install): idle/complete** — T5.1 pack delivered+verified.
  Mythos LIVE on 0.3.4; tenant feedback loop open; her defects → tenant-class ce-ops tickets.

## SESSION INFRA to recreate on the new host (dies with DGX session)
1. Dev-check cron 21,51 * * * * (full board pass; act don't report).
2. Fleet signal watcher (probe 3 seats for READY/BLOCKED, dedup, 180s).
3. Gate/PR watch as needed.

## MIGRATION BUNDLE CONTENTS (this checkpoint travels inside it)
memory/ (full controller memory, ~150 topic files + MEMORY.md) · .ce/state/research/ · .ce/briefs/ · .ce/claims/ ·
.ce/envelopes/ · .claude/agents/ (incl. uncommitted role edits) · repo-uncommitted.patch + git-status snapshot ·
salvaged /tmp task transcripts. EXCLUDED by denylist: ~/.ce-keys, *.pat, *.pem, *.pass — SECRETS DO NOT TRAVEL.
New controller needs Operator-provisioned creds on the VPS (overwatch PAT, ce-dev-2 PAT, ce-root-v1 stays where
Operator decides — signing authority is persistent-controller-only and key custody is ce-ops#442/OpenBao lane).

## OPERATOR MANDATES ACTIVE (unchanged, priority order)
1. MAIN-CONTROLLER INDEPENDENCE — this migration IS the mandate executing live.
2. NO IDLE SEATS (159-ticket backlog).
3. Subagents: never Sonnet 5; omit model on pinned roles.

## AWAITING-OPERATOR (absolute paths)
1. PR #912 — https://github.com/creator-engine/creator-engine/pull/912
2. Arc report — /home/cedev2/creator-engine/.ce/state/research/ARC_STRANGELOOP1_REPORT_20260709.md (unwritten)
3. Nitzan D6
4. STRANGELOOP-2 mandate (must fold in: today's TWO DGX incidents as evidence, controller→VPS migration completion,
   SSOT acceleration, 8 mechanization lessons from 1E + new ones: /tmp toml footgun recurrence, composer `{feature}`
   placeholder bug, dev-3 venv gap ce-ops#521)
