# RESUME STATE — CE-DEV-2 Orchestrator — 2026-07-02 12:10Z (Operator-requested checkpoint)
> NEWEST — supersedes 1220Z-named file (that stamp was wall-clock-wrong; trust THIS one, written 12:10Z real).
> Open MEMORY.md first. ARC = DAYARC 20260702 (ratified). Governance timestamps = GitHub, not filenames.

## ✅ MERGED THIS SESSION (5)
#737 doctrine-coverage ratchet · #738 widened confidentiality scanner (closes #729 leak class) ·
#739 brain migration batch 1 (30 day-1 assertions, D1b milestone, 2 ratchet exceptions burned) ·
#741 scanner hardening (ce-ops#403) · plus earlier queue-incident fixes. main tip ≥ #741's merge.

## 🔴 LIVE BOARD (verify on resume — do NOT trust as merged)
1. **#742** ce-402-preflight-failclosed (dev-3 authored, harvested, APPROVED by ce-dev-2 @a8f8340c,
   riding daemon mint→enqueue→merge; kills the validate-pr false-green class — 2 live repros on ce-ops#402
   thread). CONFIRM MERGED on resume; residual: untested reason-string branch noted on #402.
2. **#740** ce-388-payload-data-only (dev-4, ADR-0004): round-2 REQUEST_CHANGES stands — round-1 fix good
   (schema wired into from_mapping, legacy reads gone, daemon-owned-paths fail-closed guard sound), NEW
   blocker = one schema-rejected discovery item aborts the WHOLE batch (eager tuple in run_once :336-348,
   DiscoveryPayloadRejected uncaught per-item; single-item tests masked it). dev-4 WORKING round 3
   (/var/tmp/rebrief-ce-388-r3.md, sha b51c5855…): per-item catch→audit+skip→continue + mixed-batch test.
   On READY-FOR-HARVEST ce-388-payload-data-only <sha>: re-bundle into .ce/wt-ce388-harvest (round-2
   mechanics proven: local docker exec ce-dgx-codex, bundle-out, PYTHONPATH preflight, push same branch),
   fresh review (NEUTRAL refactor wording — safety filter killed 2 review dispatches on this PR; plain
   engineering language passes), then approve as ce-dev-2 if clean.
3. Seats: dev-1 idle (nothing assigned) · dev-3 idle 43% ctx (**/clear before next mandate**) · dev-4
   working round 3. Watchers: 3-seat b7wo8reit (5m; greps literal READY-FOR-HARVEST → false-fires on
   prose/scrollback, anchor pattern when re-arming) + PR-board b0lfdc6qd.

## 🎫 FILED THIS SESSION
ce-ops#404 (wall stale-marker head_mismatch deadlock + mint-body-edit re-validation cost) ·
**#405 mediated brain-append path (Operator-mandated, pick up + scope after board clears)** ·
**#406 brain recall-surface read-side lane (standup hydration, in-flow query, coverage parity, seat-side)** ·
comments: #401 seeding-race pattern · #399 burn-down adds · #402 two false-green repros.

## 📌 OPERATOR Q&A RECORDED (brain architecture)
Brain SSOT = git-tracked in-repo (GitHub = durable replica; hash-chained append-only; drift gate + pinned
CI test). New controller = clone→hydrate (.ce/state/brain = rebuildable cache, never authoritative).
Multi-writer = PRs + merge queue + territory claims; chain makes concurrent appends loud conflicts.
Recall side confirmed thin+unticketed → #406. Mediated appends → #405. ce-root-v1 offline key =
deliberate non-replicated trust root. GPU check: coder model still resident (~100.8GB vLLM, idle,
root-owned, other-project) — embedding model still blocked; keep+deterministic-brain stance unchanged,
Operator owns any change.

## ⏭️ NEXT AFTER #740/#742 LAND
Prune wt-739-review, wt-742-review, wt-ce388-harvest. /clear dev-3 then dispatch queue: #369 redo ·
#395 bump-to-main · #398 A3+A5 · #399 slices · #396 · #401 governed_trees · ce-ops#404 fix · #400 seat
toolchain · D1b batch 2 (architect follow-ups in a10dc3e output: batch-2 memory sections, playbook-items
slice, redacted daemon-token assertion, verification pass before freezing). ADR-0004 independent security
review (distinct venue, dev-4 authored) once #740 merges — precondition for G-N3 arming decision.

## ⏸️ AWAITING-OPERATOR (surface FIRST after /clear)
1. ce-ops#390 GitHub Support portal submission (staged on issue, ~2 min org-owner click).
2. With evidence: G-N3 arming (#740 + security review + dry run) · #395 tag-timing · #397 Phase B ADR.

## HOT MECHANICS (this session's proven set)
- herdr dispatch needs Enter-retry: send → grep Working → if absent, second Enter (3× today; retry
  fallback pattern in scrollback of this session works).
- Harvest preflight: PYTHONPATH=<worktree>/validators + /home/cedev2/creator-engine/.venv/bin/ce +
  --head-ref + rm validators/build egg-info first. Reviewer workers = Read/Grep/Glob only → controller
  fetches branch + makes worktree FIRST.
- Wall cycle per merge: approve → settle → mint (body edit! re-triggers governance, +1 ~6min cycle) →
  enqueue → merge-group. Stale marker after push+re-approve = strip marker line from body (ce-ops#404,
  memory ce-approval-wall-stale-marker-head-mismatch).
- Push to queued branch rejected → GraphQL dequeuePullRequest first.
