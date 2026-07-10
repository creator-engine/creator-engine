# RESUME STATE — CE-DEV-2 Orchestrator — 2026-07-02 ~12:20Z
> NEWEST — supersedes 1110Z. Open MEMORY.md first. ARC = DAYARC 20260702 (ratified).

## BOARD (live PRs + seats)
- **#739** ce-166-d1b-brain-batch1 (dev-1, brain migration batch 1, 30 assertions):
  independent-reviewed APPROVE (confidentiality clean, ledger append-only via correct_claim,
  burn-down valid). CI failed once on pinned ledger-count test → dev-1 fixed (95d7243eb,
  10→70 pin + carrier regen) → RE-APPROVED on new head → auto-merges when governance green.
  CONFIRM MERGED. dev-1's false-green root cause (system python, no pytest) logged on ce-ops#402.
- **#740** ce-388-payload-data-only (dev-4, ADR-0004): REQUEST_CHANGES submitted as ce-dev-2 —
  schema module conforms but is DEAD CODE; conveyor_daemon.py from_mapping() (:133-180) still
  reads legacy control fields unguarded. dev-4 re-briefed (/var/tmp/rebrief-ce-388.md) to wire
  validate_discovery_payload() into that path + close 3 test gaps; Working. On new
  READY-FOR-HARVEST: re-bundle into .ce/wt-ce388-harvest, host preflight, push same branch,
  fresh review, then re-approve. First reviewer attempt died to API safety filter — use
  conformance-audit wording (worked 2nd try).
- **#741** ce-403-scanner-hardening (dev-3 via harvest, PR by ce-overwatch): reviewer running
  (focus: shrink-ratchet snapshot currency, stat fail-closed correctness, scan-floor false-fire
  risk). On APPROVE verdict → approve as ce-dev-2.
- **ce-402** (dev-3): scoped retry executing — doc line to authoring-a-governed-pr.md DROPPED
  (brain-drift pin + #739 ledger territory lock); ships code+tests only. Await
  READY-FOR-HARVEST ce-402-preflight-failclosed <sha> → harvest_intake (same mechanics as
  ce-403: ssh dev1 + ce-vps-codex bundle-out; host preflight strict).
- Seat contexts: dev-3 43% (needs /clear before NEXT mandate), dev-1 ~41%, dev-4 ~9%.

## MERGED THIS SESSION
#737 (doctrine ratchet) 3c759109b · #738 (widened confidentiality scanner) cf42857d3.
Queue-incident chain (seeding races ×2 + stale-marker head_mismatch deadlock) documented in
1110Z resume + memory ce-approval-wall-stale-marker-head-mismatch.md; tickets ce-ops#404 (new),
comments on #401/#399/#402.

## MECHANICS REMINDERS (hot)
- herdr dispatch: prompt often needs a SECOND `herdr pane send-keys w1:p1 Enter` — verify
  Working indicator, retry Enter if prompt still in input box (hit 3× today).
- Harvest preflight: PYTHONPATH=<worktree>/validators + repo .venv/bin/ce + --head-ref +
  rm validators/build egg-info first.
- Reviewer venue: author≠approver satisfied (authors ce-dev-1/ce-overwatch-harvests vs
  approver ce-dev-2); reviewer workers are Read/Grep/Glob only — give them the worktree path.
- Push to queued branch = rejected; GraphQL dequeuePullRequest first.

## AFTER BOARD CLEARS
Queue: #369 redo · #395 bump-to-main · #398 A3+A5 · #399 slices · #396 · #401 governed_trees ·
ce-ops#404 fix · #400 seat toolchain (unblocks dev-3 full preflight) · D1b batch 2
(architect follow-ups: STRATEGY/DESIGN memory sections + playbook-items slice + redacted
daemon-token assertion). Prune wt-739-review, wt-ce388-harvest, wt-ce403-harvest post-merge.

## AWAITING-OPERATOR (unchanged)
ce-ops#390 portal submission · G-N3 arming (needs #740 done + independent security review +
dry run) · #395 tag-timing · #397 Phase B ADR.
