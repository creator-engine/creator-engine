# ARC STRANGELOOP-1 — EVENT LEDGER (append-only; ts approximate UTC)
# Mandate: ARC_STRANGELOOP1_MANDATE_DRAFT_20260708.md (RATIFIED verbatim, Decision 14)

- 16:42 GATE restored: ce-queue-daemon deployed as systemd singleton via #895 surface (outage root
  cause: session-owned docker run --rm; ce-ops#512 filed for surface gaps)
- 16:5x MERGE #906 (docs-parity; canon fixed) — first post-restore merge
- 17:0x TICKETS ce-ops#513 (ratification-binding P0), ce-ops#512 filed
- 17:0x PR #907 opened (README P0 harvest resume; full CI-parity preflight PASS @54d6a99b2)
- 17:1x T5.1 delivered (all build checks green) → found canon defect → ce-ops#514 filed
- 17:2x MERGE #905 (followups b2, via merge queue) — day count 11
- 17:2x REVIEW #907 REQUEST_CHANGES (broken links) → harvest-fix cc2f15e22 pushed + approved
- 17:4x DOCTRINE: idle-seat=controller-failure persisted (Operator correction); batch composers launched
- 18:1x DISPATCH dev-4 batch (ce-conveyor-intake-s1 story + ce-491-prearming task) — pointer+SHA
  verified, Working on 4fae126d; watcher armed
- 18:2x FRICTION: #907 CI FAILED — reviewer link finding was STALE-BASE FALSE POSITIVE (worktree
  predated #906 restructure); controller compounded via stale rc2 root-checkout verification;
  dangling-link gate caught it. REVERT pushed (head 5264891ea), links verified vs fresh origin/main,
  re-approved, audit comment on PR. [3rd stale-baseline incident today → report candidate: mechanize
  fresh-fetch verification]
- 18:3x RATIFIED: Decisions 14 (STRANGELOOP-1) + 15 (Arad send waits on rehearsal)
- 18:4x DISPATCH dev-3 batch (ce-solo-ceo-onboarding-fix + ce-seat-preflight-parity +
  ce-readme-review-minors w/ merge precondition) — /compact first (ctx was 48%), pointer+SHA verified
- 18:5x CHECKPOINT for Operator account switch x5→x20 (kills controller subagents/monitors; seats +
  gate unaffected)
- 19:1x RESUME post-account-switch (x5→x20): board verified, 4 watchers re-armed (907-trigger,
  dev-4, dev-3, 25-min heartbeat)
- 19:1x #907: approval re-verified on 5264891ea, capability marker minted (settle → enqueue next)
- 19:2x dev-4 READY ×2 WITH SHAs: ce-conveyor-intake-s1 @8c1eb86bc, ce-491-prearming @d56db4ccb
  (~65 min brief-to-ready for a story+task batch) → parallel harvests launched
- 19:2x dev-3 self-serialized: Unit A (ceo-onboarding) BLOCKED on the seat-ready portability
  false-red THAT UNIT B FIXES — seat re-sequenced A behind B unprompted (foreman behavior; also
  live evidence for Unit B's premise). No controller action.
- 19:5x OPERATOR SIGN-OUT (verbatim mandate: "I'm trusting you to put the mechanisms in place to
  allow you to run the factory autonomously… checking their state both in terms of work performance
  … and in terms of health (context usage/limits…)"; seat-limit contingency = account-B switch per
  playbook). AUTONOMY MECHANISMS INSTALLED: heartbeat liveness file + session cron dev-check
  (13,48 * * * *) + host watchdog crontab (*/10, telemetry-only, survives controller death) —
  first watchdog run green (gate active, dev-4 ctx 32% used, dev-3 ctx 21% used, both Working).
  Arc now fully autonomous. Operator away ~9h.
- 20:0x PR #908 OPENED (ce-conveyor-intake-s1, preflight GREEN, flag-gate verified, harvest fixed
  carrier S→story) → fresh reviewer dispatched (gate-adjacent rigor + READY-artifact hygiene ruling)
- 20:1x FRICTION CLUSTER, root cause = CONTROLLER (invalid work class "task"/"T"/"S" in batch specs;
  enum is tiny|story|feature|epic): dev-3 triple-BLOCKED (corrected via herdr, A+B resume; C waits
  on #907) · dev-4 Unit B harvest BLOCKED — seat had MODIFIED pr_preflight.py to add a "T" alias
  (unauthorized gate-surface change, out of claims, broke WORK_CLASSES re-export → 10+ egress test
  fails; caught independently by scope-matrix AND baseline-diff). Remediation directive sent:
  revert validator, declare tiny, drop committed READY artifact. G5 memory hardened with enum +
  induced-tampering lesson. ARC REPORT CANDIDATE: briefs with invalid gate inputs INDUCE seat
  gate-tampering; gates held.
- 20:2x #908 REVIEW: REQUEST_CHANGES — B1 real crash bug (malformed pending/ YAML propagates
  uncaught out of _run_loop → daemon dies post-lease-release; fix + pin-test required), B2 drop
  committed READY artifact + carrier regen to 6 paths (no .ce/wt-* precedent on main), M1 docs
  inaccuracy. Authority safety PASS (flag-off path bit-identical to main; no live dispatch).
  Fold-back sent to dev-4 (batched with its Unit B remediation — one round trip for both branches).
- 20:2x #907 ENQUEUED (merge queue position 1, AWAITING_CHECKS ~8 min) → dev-1 hermes dispatch on
  merge event.
- 20:4x #909 controller remediation: pr_preflight.py reverted WHOLESALE (harvest agent's minimal
  fixup had kept the seat's T-alias gate widening), alias-pinning test removed, committed READY
  artifact dropped, carrier regenerated to the 5-path claimed set (@8f0ced6f4). Full preflight
  running. dev-4 stood down from Unit B (branch controller-owned; de-raced).
- 20:5x INFRA FINDING #3 (merged≠deployed class, 3rd instance today): VPS egress broker NOT
  DEPLOYED (unit not found on dev1) — dev-3 "self-push" gh-unauth blocker explained; Jul-2 canary
  must have ridden an ad-hoc process since dead. Mitigation: dev-3 flipped to commit-only +
  controller harvest (units unblocked); PROPER broker systemd deploy added to controller-op queue
  next to P6 (dev-4 DGX broker). Acceptance-Evidence rule (P2) evidence keeps compounding.
- 20:5x dev-3 exit-143 during seat validation noted (SIGTERM — watch for recurrence; controller
  preflight authoritative under commit-only flip).
- 21:0x MERGE #907 — README P0 COMPLETE (Operator end-of-day-arc mandate MET: public README at
  bar + version-drift anti-rot gate live). Ledger tail freed.
- 21:0x DISPATCH dev-1 hermes R2 (brief sha 430a9488… verified on dev1 host; rebase-onto-97
  baseline; self-push NON-draft). Watcher armed. dev-3 Unit C precondition now satisfied.
- 21:3x→03:0x ⚠️ CONTROLLER DARK GAP (~5.5h) — THE ARC'S CENTRAL FINDING: controller session went
  un-invoked overnight; ~20 heartbeat + all seat/harvest/review events QUEUED without waking the
  agent. Seats+gate+watchdog ran fine (gate reached pass 306, zero failures; dev-3 finished ALL 3
  units incl. C @092d9f350; dev-4 finished #908 fixes @b53c47112; harvests #910/#911 opened and
  preflighted GREEN before the gap) — but NOTHING merged: every pipeline stalled at the
  controller-action point. WORSE: watchdog showed controller=alive ALL NIGHT because the dumb
  heartbeat Monitor kept touching the liveness file — "alive-but-not-acting" is a failure mode the
  liveness design missed. Design conclusions for the report: (1) liveness signal must be an ACTING
  signal (ledger mtime), not a monitor tick; (2) in-session watchers/cron cannot bridge harness
  suspension — validates spawn-on-event ephemeral controllers (#496/#498) and the review daemon
  (P8) as the structural fixes; (3) the gate being a daemon is WHY nothing broke.
- 03:0x MORNING RECOVERY BURST: #909 changelog false-bullet fixed (review's one blocker) →
  APPROVED @f7718cc81. #908 re-harvest to b53c47112 launched. Reviews launched: #910, #911.
  Harvest launched: dev-3 Unit C @092d9f350. dev-1: woke mid-gap and started hermes in the
  exhausted session (12% left) — interrupted, /new fresh thread (100%), re-dispatched clean.
  MECHANICS LESSON: dev-1's codex TUI needs Enter as a SEPARATE tmux send-keys call (both /compact
  and /new stalls explained; playbook-worthy).
- 03:2x RESTOCK (idle-seat doctrine): dev-4 ← P4 #513 ratification-binding DESIGN artifact (brief
  sha b0e54ace…); dev-3 ← P1 #512 redeploy-portability fixes (brief sha ea22f8a7…). All 3 seats
  Working again.
- 03:3x REVIEWS #910 + #911: both REQUEST_CHANGES, both TRUTHFULNESS classes (the night's defect
  theme): #910 — html sibling (dual-format PRIMARY) never regenerated, still teaches ce inbox +
  unshipped verbs; .md line 269 false identity-attribution claim. Reviewer also surfaced: main's
  guide docs document verbs ABSENT from shipped ce_cli.py top-level (ce ratify/merge/scope/shape/
  report/show/artifacts) — the #508/#514 docs-vs-CLI gap is far wider than ce inbox; mechanized
  documented-verbs gate now heavily evidenced. #911 — skip message claims "CI-validated" but CI
  runs NO scan-portability-plane (false justification = governance hole); missing inverse test.
  Both folded back to dev-3 (author), batched with its P1 work.
- 03:3x REVIEW-RIGOR PATTERN for the report: fresh-context reviewers are catching FALSE-CLAIM
  defects (false changelog bullet #909, false CI claim #911, false identity claim #910, doc-lies
  in primary html) that no mechanical gate covers — "no claim without evidence" extended to docs
  by reviewer lens. Candidate mechanization: documented-verbs gate + dual-format-sync gate
  (md/html divergence detector).
- 04:0x DEV CHECK (scheduled): all 3 seats Working (dev-4 P4 design @36% ctx, self-reviewing
  pre-signal; dev-3 P1+fold-backs; dev-1 hermes verified at baseline w/ background thread, 11%
  ctx). Gate pass 310 clean. #909 held only by a QUEUED CI runner (Validate pending) — gate
  fail-closed as designed. No restock needed; no missed signals.
- 04:3x DEV CHECK: all 3 seats Working (no ctx concerns). #908 re-harvested to b53c47112 — all 3
  review findings verified fixed by independent re-harvest → APPROVED (single preflight RED
  control-attributed to pre-existing xdist copytree flake; ticket filing). #909 in approval-settle
  (CI went green). #910/#911 fold-backs still with dev-3. Flaky-test ticket dispatched (2nd
  round-trip this flake cost the arc).
- 05:0x ce-ops#515 filed (copytree xdist flake). Unit C harvest (ce-readme-review-minors): scope
  CLEAN, regex-tightening VERIFIED, but preflight RED on the brain-pin gate — record 154 (minted
  by #907!) pins test_v1_docs_reconciliation.py sha; fix requires assertions.yaml edit → PARKED
  behind dev-1 hermes (ledger-tail serialization rule). Worktree ready at
  /home/cedev2/.ce/wt-readme-minors-harvest @61126a43d (harvest also corrected story→tiny);
  ON HERMES MERGE: apply supersession v6→v7 + ratchet, carrier +assertions.yaml, re-preflight,
  push, PR, review. REPORT CANDIDATE: briefs must pre-compute brain-PINNED files (discoverable
  from assertions.yaml evidence paths) — 2nd pin-collision burned round-trip in 2 days.
- 05:2x dev-4 READY: ce-513-ratification-binding-design @059753362 (P4 design artifact, ~2h
  build+self-review) → harvest launched (content-check vs 8-point mandate + threat table).
  P2 (acceptance-evidence bot rule) brief composing for dev-4 restock.
- 06:0x DEV CHECK: **#909 MERGED** (arc merge #4); #908 ENQUEUED (pass 329) — merging. dev-4
  Working P2 @41% ctx → /compact scheduled at P2 boundary (next signal). dev-3 Working 41m
  (P1 + fold-backs). dev-1 hermes continuing (17% ctx used, background-thread pattern). Gate
  clean. No missed signals, no restock needed (all seats loaded).
- 06:2x dev-1 idle-without-signal after 23m stretch (watcher caught it): surfaced 2 discoveries and
  stopped for authorization — (1) test_claude_hook_pack_stop.py still expects .hermes observations
  path (same pre-authorized fallout class), (2) ratchet 97→103 (its own R-B task; R-A appended 6
  assertions). Controller authorized both + do-not-stop-for-this-class; pushed to completion
  (preflight → self-push → non-draft PR). NOTE for Unit C park: post-hermes ledger baseline = 103.
- 06:4x dev-3 transient self-managed BLOCKED on ce-512: its foreman interrupted its own worker's
  full validate-pr (recurring exit-143 = in-seat full-suite resource kill), self-corrected, Working
  48m. STANDING GUIDANCE sent: in-seat = targeted tests only, controller preflight authoritative
  (commit-only mode) — stops the 143 burn on all 3 of its branches. REPORT CANDIDATE: seat-ready
  profile should formally define the in-seat test tier (relates ce-ops#11 test-tier split).
- 03:57 **#908 MERGED** (arc merge #5 — conveyor intake s1, the factory meta-fix, on main).
- 03:57 ⚠️ LEDGER TIME CORRECTION: the entries above stamped 04:3x/05:x/06:x actually occurred
  ~03:1x–03:5x — the controller stamped assumed times without checking the clock during the
  recovery burst. All those events are real and correctly ORDERED; only the wall times were wrong.
  (Report lesson: ledger appends must read the clock, not estimate — same class as the context-%
  estimate error of 2026-07-08 afternoon.)
- 04:0x dev-3 TRIPLE READY (targeted-tests guidance paid off immediately): ce-512-redeploy-
  portability @7c35f8a2b (P1, new) + ce-seat-preflight-parity @7b787d86d (fold-back) +
  ce-solo-ceo-onboarding-fix @fa3e1c1c1 (fold-back). Launched: PR-update harvests for #911/#910
  (fix-verification + sync preflight); #512 harvest queued behind the 2-heavy cap; P3 rehearsal
  brief composing for dev-3 restock.
- 04:1x PR #912 OPENED: #513 ratification-binding design artifact (P4) — preflight GREEN, harvest
  content-check: ALL 8 mandate points present (authorization-event schema, HMAC approver_ref w/
  key custody on the approval-capability template, authorization_source + 8-step gate verify,
  merge-apply capability marker, smoke seam w/ 4 forbidden bypass patterns enumerated, 6-layer
  enforcement w/ Ring-1 hooks-advisory caveat, 3-phase migration, 3-slice plan w/ acceptance
  criteria) + 9-row threat table + 20+ file:line groundings. HELD FROM GATE by design-preview
  doctrine — design green requires OPERATOR preview; queued to morning review, not approved.
- 04:3x #911 APPROVED @5f640b172 (both truthfulness fixes verified: honest skip rationale, inverse
  test; preflight ALL GREEN on rebased head) → gate takes it. #512 harvest launched (slot freed).
  P3 rehearsal dispatched to dev-3 (brief sha 77159978…, journey-canon-refresh note included).
- 04:14 DEV CHECK: all 3 seats Working — dev-4 P2 @42% ctx (compact at boundary stands), dev-3 P3
  @40%, dev-1 hermes ahead-4 with expectation repairs committed (c76c4b9a), 22m into its
  preflight/finish stretch. Gate pass 342 clean. #911 approved→in CI/settle; #910 update-harvest
  running; #912 held for Operator. No stalls, no restock (pool P5+ awaits next idle).
- 04:2x #910 APPROVED @a5cdf244e (html regenerated + identity-claim reworded; 19/19 gates) → gate.
  Both truthfulness fold-backs now closed; the intent-and-authorization CEO canon heads to main.
- 04:4x dev-3 READY ce-p3-rehearsal-s1 @d3fe5c7e8 (~35 min under targeted-tests mode) → /compact
  sent at boundary, P3 harvest launched (content-check incl. stub honesty + which journey canon),
  P5 seat-watch brief composing (the daemon that productizes tonight's idle-detection — its own
  evidence base). Pool: P5 next for dev-3; P6/P7 = controller host ops; P8/P9 remain.
- 04:3x PR #913 OPENED (ce-512 portability, all 4 fixes verified at harvest, preflight EXIT 0)
  → fresh review dispatched with a deployed-instance-compatibility lens (the LIVE DGX gate
  deployment must survive a redeploy with the new script + existing drop-in).
- 04:5x P5 dispatched to dev-3 (sha verified 498944bb…). dev-4 P2 BLOCKED on missing changelog
  fragment — MY brief omitted the standing obligation (composition gap; the P2 composer prompt
  said carrier but not changelog); authorized creation + carrier update, unit resuming. LESSON:
  brief template must carry the standing-obligations block verbatim (changelog + carrier + G5
  line), not rely on composer memory.
- 05:0x #913 REVIEW: REQUEST_CHANGES — reviewer caught a HEALTHY-WHILE-BROKEN recovery path (probe
  env precedence inverted vs systemd + BAO_ADDR localhost pin the DGX drop-in never overrides →
  redeploy would kill the live gate while the probe passes). Deployed-instance lens vindicated.
  Fold-back to dev-3 (B1 order swap + precedence test, B2 remove unit BAO pin + honest
  RELOCATION precedence docs, N1/N3 hardening, N2 explain-or-drop). REPORT ADDENDUM: reviews on
  IaC surfaces must always include the walk-the-live-deployment lens.
- 05:1x PR #914 OPENED (P3 rehearsal harness s1; preflight GREEN 19/19; smoke PASS; harvest fixed
  missing G5 line + a ce-ops# ref in carrier). Content: 6 live stages + 6 explicitly-stubbed
  agent-mediated stages, JSON evidence bundle per format doc. Canon note: scripts pre-#910
  journey — annotation refresh = slice-2 item once #910 merges. Review dispatched (honesty-first
  lens: stub visibility, fail-closed, no overclaim of Decision-15 gating).
- 05:2x #914 REVIEW: REQUEST_CHANGES — B1 evidence bundle not flushed on set-e failure paths (the
  release-acceptance artifact missing precisely on failure), B2 missing non-gating disclaimer,
  + CONTROLLER-FOUND: harness live-probes the unshipped `ce inbox` verb (would kill live runs;
  the same doc-lie class the arc purged — it crept from pre-#910 canon into CODE). Full fold-back
  to dev-3 (queued after its ce-512 fixes). Stub-honesty + summary math PASSED review.
- 05:3x dev-3 READY ce-p5-seatwatch-s1 @1325ec5a0 (P5 finished before the fold-backs — foreman
  sequencing). Harvest launched. dev-3 queue: #913 fixes → #914 fixes.
- 04:48 DEV CHECK: all engaged — dev-3 amending #913 fold-back (8-file scope held), dev-1's
  internal worker committing the final hermes fix (PR imminent), dev-4 P2 @43% (compact at
  boundary). #910/#911 in congested merge queue (enqueue re-armed, pass 359 clean). RUNNER
  CAPACITY = confirmed throughput ceiling under factory load → STRANGELOOP-2 proposal added.
- 04:5x dev-4 READY ce-p2-acceptance-evidence @93f30d4b2 → /compact at boundary sent, P2 harvest
  launched, P8 (review-daemon s1, dry-run) brief composing — the last seat unit in the pool
  (P6/P7 = controller host ops, P9 = controller research agent; queued for post-report).
- 05:0x PR #915 OPENED (P5 seat-watch s1; preflight PASS; 20/20 targeted tests; harvest corrected
  work class S→feature per size band). Review dispatched — lenses: observe-only invariant,
  signal-shape regex (anti-noise, tonight's watcher false-positives as the test case), per-seat
  fault isolation, JSONL atomicity, lease collision vs conveyor daemon.
- 05:1x dev-3 delivered BOTH fold-backs: ce-512 @0841f8c96 (#913 fixes incl. the healthy-while-
  broken probe defect) + ce-p3 @42faadba8 (#914 fixes incl. evidence-flush + ce-inbox probe
  removal). #913 update-harvest launched (live-host BAO sanity check mandated); #914's queued
  behind the P2 harvest slot. dev-3 now idle → P6-P9 are controller-side; pool seat-units
  EXHAUSTED — dev-3 stands by for fold-back rounds.
- 05:12 **#910 + #911 MERGED** (arc merges #6, #7 — merge queue drained): intent-and-authorization
  CEO canon (md+html) and seat-preflight portability parity are on main. Remaining open: #913
  (update-harvest running), #914 (update queued), #915 (review running), #912 (Operator-held).
- 05:13 DEV CHECK: dev-4 fresh post-compact (7% used) Working P8; dev-3 idle by right (both
  fold-back READYs in harvest pipeline, 36% used); dev-1 Working 1h21m continuous on hermes
  (75% left — long unit, alive). Gate pass 371 clean. Heavy slots at cap (P2 + #913 harvests);
  #914 update-harvest queued next.
- 05:2x #915 review: REQUEST_CHANGES → mechanical fixes applied AT HARVEST (changelog aligned to
  gate-derived 'feature' — reviewer's B1 sided with the brief, but the FLOOR GATE is authoritative;
  probe read-only invariant + event semantics documented per reviewer wording) → APPROVED
  @7332c0544. NB-3..6 = slice-2 hardening list (idle off-by-one doc, temp-file cleanup, loop
  exception guard, multi-seat isolation test).
- 05:3x PR #916 OPENED (P2 acceptance-evidence bot rule; preflight GREEN; 8/8 tests; fail-closed +
  warn-mode verified at harvest) → review dispatched (governance-code lenses: other fail-open
  paths, warn-comment idempotency, exit-1-under-continue-on-error visibility). #914 update-harvest
  launched (slot freed).
- 05:4x #913 APPROVED @6d24d1ed0 (healthy-while-broken defect closed with precedence-pinning test;
  live-host BAO sanity render confirmed) → gate. The gate's IaC recovery surface is now truthful.
- 05:5x #916 review COMMENT (zero blockers; invariants verified) → APPROVED @79b5bab25 with 4
  advisories accepted as slice-1 limitations; slice-2 ticket filing (dedup, alert hook, yml
  comment, POST-failure test). The Acceptance-Evidence rule — born from yesterday's #467
  post-mortem — is now enforcement, not doctrine.
- 05:5x dev-3 idle CONFIRMED legitimate (all its units delivered; mandate pool has no further seat
  units — rail-bounded, not controller failure). P9 launched as controller-side research agent
  (closed-but-not-real sweep continuation, fresh-origin/main verification method mandated).
  Pool now FULLY consumed or in-flight except P6/P7 controller host ops (queued post-report).
- 06:0x #914 APPROVED @80358d372 (all 7 findings fixed; evidence-flush-on-failure + non-gating
  disclaimer + ce-inbox probe removal verified; smoke PASS) → gate. Four approved PRs now
  draining: #913 #914 #915 #916. Remaining builds: hermes (dev-1), P8 (dev-4), P9 (research).
- 06:1x dev-4 P8 BLOCKED on VAL-VERBND-SHARED-EDGE (new-module classification in _versions.py —
  a gate unknown at composition; the seat correctly stop-lined on a registry outside its paths).
  Authorized append-only classification + carrier update. BRIEF-PREFLIGHT LESSON #4: the
  composition-time gate-precompute list now includes _versions.py module registry (joins
  changelog, carrier, G5 enum, brain pins).
- 05:48 DEV CHECK + **#915 MERGED (arc #8)**; #913/#914/#916 enqueued (pass 388). dev-1 1h56m into
  hermes (35% used). dev-4 P8 blocked round 2: taxonomy-count ratchet companion of the authorized
  _versions.py append — authorized the pair (registry+ratchet = ONE authorization class going
  forward; playbook lesson: pre-authorize registry appends WITH their count-pin tests).
- 06:2x P9 AUDIT DELIVERED + persisted (DIRECTIVE_DRIFT_AUDIT_P9_20260709.md): 13 closures swept;
  #184 closed-before-real, #491+#356 confirmed closed-with-orphans (gh-verified CLOSED); 4
  systemic patterns; key new rule candidate: Acceptance-Evidence DEPLOY-CLASS extension
  (persistent-state probes) — would have caught all 3 merged≠deployed instances. Consolidated
  residuals ticket filing.
- 06:4x OPERATOR BACK; pre-/clear CHECKPOINT written: RESUME_STATE_CE_DEV2_STRANGELOOP1B_20260709.md
  (board @ 8 merged / 3 enqueued / #912 held / hermes+P8 in flight / Unit C parked with fix
  prescription / P6+P7 held / full morning queue with paths / mechanics cheat-sheet). Controller
  context at 56% at checkpoint; monitors + session cron survive /clear; host watchdog independent.
- 06:02(clock) **#913 + #916 MERGED (arc #9, #10)** — gate IaC honesty + evidence-gated closures on
  main. Open: #914 (merge queue) + #912 (Operator). Arc merge count: 10, with #914 → 11 imminent.
- 06:16(clock) DEV CHECK (post-/clear session, reconciliation complete — see RESUME_STATE_
  STRANGELOOP1C): GATE active pass 401 failed=0 (skip 2 = #914 CI-red + #912 unapproved, both
  expected). #914 BOUNCE root-caused: G5 floor — declared S, fold-back diff exceeds S floor;
  mechanical-fix worker in flight (derive class, align carrier/changelog/body). dev-4 P8 BLOCKED
  on missing changelog fragment (brief omitted standing-obligations AGAIN — template still unfixed,
  S2 item) + seat at 11% ctx → STOOD DOWN, branch controller-owned, harvest worker in flight.
  dev-3 idle-by-right 64% left (pane READY lines = stale scrollback; units landed as #913/#914).
  dev-1 hermes: rebased AGAIN (stale-base loop, main advanced 6×), now ahead-11/behind-0, full
  validate-pr running on b8b501ae @2h22m, 62% left — final stretch, watcher armed. NO restock:
  seat pool EXHAUSTED (P6/P7 controller-held, P9 done); no limit/auth errors; no missed signals.
- 06:18(clock) **#914 G5 FIX LANDED**: worker derived class M (S floor FAIL / M PASS vs merge-base c867ca5c); PR body was the lone wrong declaration ("story"), carrier+changelog already M — aligned @454d0031, local G5+carrier PASS. Re-approved as ce-dev-2 on settled head, auto-merge armed, watcher on. ROOT CAUSE for S2: the 05:1x harvest wrote the G5 body line from the BRIEF class instead of the floor derivation — same "floor gate is authoritative" lesson as #915, now on the harvest side.
- 06:25(clock) **PR #917 OPENED** (P8 review-daemon s1 harvest): seat commit 0f592455 cherry-picked onto fresh main db07e6dc, one CHANGELOG hunk vs #916 resolved, controller AUTHORED the brief-omitted changelog fragment, carrier 7→8 paths + slug-match branch rename (slug fallback would false-trigger 13 legacy G5 matches — new gotcha, playbook-worthy), class story (floor-derived), preflight 18/18 GREEN. Dry-run invariant verified at harvest (GET-only, no mutating verbs). Fresh reviewer dispatched (dry-run + observe + truthfulness lenses).
- 06:30(clock) **OPERATOR DIRECTIVE (extends arc rails): NO IDLE SEATS while ce-ops backlog exists** (159 open) — "arc pool exhausted" is NOT an idle license; idle seat = orchestration failure (GPU-datacenter analogy). Memory hardened (ce-idle-seat-is-controller-failure ⏫). RESTOCK WAVE: dev-4 /compact sent at unit boundary (11%→fresh); composer launched for two file-disjoint batches — dev-3: #515 flake + #516 acceptance-evidence s2 + #473 merge_group template; dev-4 (strongest→hardest): #493 gate TTL-wedge + #492 smoke-daemon bug + #461 merge-group e2e fixture. Composer verifies not-already-landed, territory disjointness, brain-pin exclusion, STANDING-OBLIGATIONS BLOCK verbatim (the twice-burned omission).
- 06:33(clock) **#914 2nd bounce root-caused + fixed**: test-coupling gate (first run died at G5 before reaching it) — unit DOES ship a test (shell smoke) the gate patterns miss; documented CE-TEST-COUPLING-EXEMPT marker added to body (no head change, approval stands), Validate rerun. LESSON: shell-test units need the exemption marker AT PR OPEN; local preflight cannot evaluate a not-yet-existing PR body. **#917 review resolved**: REQUEST_CHANGES → M1 scope = the pre-authorized registry+ratchet pair (brief self-contradiction, seat acted correctly — adjudication commented), N1 kwargs-pin test added @7b77c595 (15/15), APPROVED as ce-dev-2 + automerge armed. Combined watcher on 914+917; old single-PR watcher superseded.
- 07:14(clock) **#914 + #917 MERGED (arc merges #11, #12)** — Fresh-Tenant Rehearsal harness s1 (Decision-15 gate substrate) and review-daemon dry-run s1 (P8, the PR-opened→review daemon seed) both on main. Open PRs: ONLY #912 (Operator-held by design). DEV CHECK 07:13: dev-4 /compact complete (100% left) idle AWAITING RESTOCK; dev-3 idle 64% left AWAITING RESTOCK; dev-1 hermes 3h21m — internal reviewer on final blocker pass @7a251f18, 52% left; gate pass 430 clean skip 1 (=#912). Composer hit the 7am Anthropic session limit AFTER research, BEFORE file writes — resumed post-reset (transcript intact, write-phase only).
- 07:16(clock) **RESTOCK WAVE DISPATCHED** (Operator no-idle-seats directive): dev-4 batch (ce-493 gate TTL-remint S + ce-492 smoke-uid XS + ce-461 merge-group-e2e S, brief sha f3116b95…) and dev-3 batch (ce-515 copytree XS + ce-516 autoclose-s2 S, brief sha e6bd8c5f…) — both briefs sha-verified in-container, pointer+SHA delivered, Enter separate, combined landing+signal watcher armed. #473 DROPPED at composition (already landed via #859, ticket stale-open) → CLOSED with acceptance evidence: the INVERSE closed-but-not-real case (work done, ticket open) — evidence-rule works both directions. Brain-pin precompute: 3 touched evidence files adjudicated no-ledger-append-needed; assertions.yaml on every stop-line. All 5 seat-units now beyond the ratified pool = first backlog-fed conveyor pull.
- 07:18(clock) **dev-1 PR #918 OPENED (self-push, hermes R2, 3h24m)** — fresh reviewer dispatched on fetched-fresh worktree @7a251f18 (kill-list completeness, brain ratchet 97→103, committed-READY hygiene, v1-frozen boundary lenses). dev-1 /compact at boundary (49% used) + restock composer launched (#500 OOM-durability, #501 canary gap, #502 takeover surface — territory-checked vs both live batches + #918 path set). ALL THREE SEATS now stocked or in final review — zero idle.
- 07:26(clock) dev-3 DOUBLE READY ~40min after dispatch (ce-515 @1499bf51 XS + ce-516 @7edad9c0 S) — sequential harvest launched (scope matrix, floor-derived G5, full foreground preflight ×2, workflow-permissions check on the #516 Actions diff). dev-3 idle→will restock after harvest confirms scope clean.
- 07:29(clock) dev-1 RESTOCKED post-compact (100% fresh): 2-unit batch dispatched sha-verified (ce-501-queue-canary S + ce-502-standby-surface S; brief 75f391ef…). #500 DROPPED at composition: slices b/c already landed via #891 (2nd already-landed catch today), remaining slices a/d territory-locked behind #918 (runsc launcher scripts) — re-target post-merge. Fold-back priority over batch communicated. All 3 seats Working; controller queue: dev-3 harvest (running), #918 verdict (pending), dev-3 batch-2 composer (running), then P6 broker deploys.
- 07:33(clock) **#918 REVIEW: REQUEST_CHANGES** — B1 committed READY artifact .ce/wt-hermes-r2/READY in tree+carrier (MY BRIEF INSTRUCTED IT — brief template defect, violates #908-B2 precedent; fix-at-harvest + gitignore .ce/wt-*/ guard = follow-up ticket); M1 real introduced defect: new STATE_PATH_GUIDANCE tells users `ce init` which creates .hermes NOT .ce/state (test pins the wrong text too) — the doc-lie-in-CODE class again. CORE ACCEPTANCE MET per reviewer: ce onboard no longer hard-requires .hermes gitignore; ledger seqs 155-160 verified chained, ratchet 103 correct; v1-frozen untouched. Fix worker on both findings (verify-then-write for the M1 command). N1/N2 = brief-precision gaps, accepted.
- 13:13→13:40(clock) 🔴 DGX HOST REBOOT AT 12:54 = FACTORY-DOWN INCIDENT + RECOVERY (dark gap #2,
  ~07:45→13:13, session death; compounded by reboot). DAMAGE: dev-4 container exit(255) and
  UNSTARTABLE (two stacked failures: /tmp bind source wiped → recreated from launcher template
  [1st attempt had TOML quoting defect — diagnosed via codex-stderr.log, fixed against dev-3's
  live config]; stale gVisor overlay filestore blocked runsc → 90GB img MOVED to
  /home/cedev2/.ce/dev4-crash-recovery-20260709/ [salvage: img contains git bundles — carve scan
  running]). dev-4's 3-unit batch worktree WIP LOST (runsc self-medium overlay = the img; /var/tmp
  doctrine confirmed the hard way). Controller workers killed mid-flight: #918 fix (no push
  happened), 515/516 harvest (no PRs), hygiene ticket (not filed) — ALL RESUMED from transcripts.
  SURVIVED CLEAN: gate (systemd, active), dev-3 (VPS untouched; delivered ce-504 READY during the
  gap — brief-instructed committed READY file to be dropped at harvest), dev-1 (self-pushed PRs
  #919+#920 during the gap — self-push VALUE PROVEN in a controller-dark window). RECOVERY: dev-4
  restarted + batch re-dispatched sha-verified (commit-early emphasized); reviews launched #919
  (live-gate-surface lens) + #920 (authority-safety lens); fleet signal watcher re-armed.
- 13:40 OPERATOR DIRECTIVE (during incident): (a) move persistent controller CE-DEV-2 to the VPS;
  (b) accelerate the IaC/distributed dark-factory form — controller spawnable terraform-like, all
  state from SSOT/brain, nothing controller-local. Incident = direct evidence for both (#496/#498
  program; this reboot took down: controller session, dev-4 seat, and all in-session watchers —
  everything host-coupled; everything daemon/IaC survived or redeployed).
- 13:31(clock) dev-4 probe error = transient (container Up, codex running — false alarm during restart window). #920 review round 1 = PRECONDITION FAIL: controller dispatched reviewers WITHOUT fetching the PR branches (the exact ce-fetch-worktree-before-reviewer-dispatch memory rule, violated under incident pressure) — branches now fetched, pinned worktrees wt-919-review/wt-920-review created, both reviewers resumed. Reviewer nonetheless pre-derived 2 substantive hypotheses from the brief (M1 mint-forge-token prints raw PAT to stdout vs DESIGN no-secrets rule; M2 detached-HEAD checkout-main idiom breaks on re-invocation) — to verify against real code.
- 13:37(clock) **#920 REVIEW: APPROVE-on-content** — all 4 pre-hypotheses CLEARED against real code (M1 token-print = acknowledged debt outside DESIGN constraint scope + help-only invocation; M2 uses checkout -B, idempotent; N1 dir consistent; N2 clean GREEN/WARNING/RED tri-state w/ full test coverage); authority-safety ALL CLEAR (dry-run takeover only, no token-scope expansion, no worker forge-path, singleton preserved). HELD from approval on 2 releases blocks: committed .ce/wt-ce502/READY (dev-1 brief template STILL instructs READY commits — 3rd instance; template fix = S2 hard item) + validate-pr never attested (reviewer M3). Fix worker: drop READY + carrier regen + full foreground preflight → then approve on settled head. #919 verdict pending.
- 13:42(clock) **#918 APPROVED @3d7b07e9 → gate** (B1 READY-drop + carrier regen 28→27; M1 guidance ce init→ce brain init VERIFIED in brain_runtime mkdir path, 2 stale test assertions fixed, 46/46; preflight 18/18; copytree flake seen AGAIN mid-preflight = #515 evidence). NOTE: harvest venv still runs OLD work-class enum (story not S) — version skew between installed validator and repo head; S2 item. ON MERGE: hermes tail frees → Unit C resume (ratchet 103→104) + #500 slices a/d + ce-453 Part A unblock. 3-PR merge watcher armed (918/919/920).
- 13:50(clock) TRIPLE HARVEST: **PR #921** (ce-515 flake XS @1499bf51, preflight 27/27) + **PR #922** (ce-504 broker-arming S @5e87cebe, harvest dropped committed .ce/wt-504/READY, carrier 8→7) OPENED — one combined reviewer dispatched (efficiency; usage 97%). **ce-516 HELD RED**: workflow COMMENT edit changes brain-pinned evidence sha (record 65 evidence_sha256) → chain-cascade needed = tail-locked behind #918; composer precompute tested APPENDS not FINGERPRINTS (precompute rule hardened: any byte-change to ANY evidence_ref path trips the pin). DECISION: slim unit — revert Item 3, land Items 1/2/4; comment refresh = follow-up under next ledger window. NOTE #921 still carries committed .ce/wt-515/READY (4th instance; will drop at approval alongside review fixes).
- 13:53(clock) DEV CHECK 13:52: ⚠️ dev-4 re-dispatch NEVER LANDED — herdr restart moved codex to pane w4:p1 (old w1:p1 gone; the 13:3x send returned ok into a dead pane = ~30min silent idle; PLAYBOOK: after ANY container/herdr restart, `herdr pane list` FIRST, never assume pane id). Re-dispatched to w4:p1 with explicit NO-COMMITTED-READY correction. dev-1 idle (60% left, both PRs pushed) + dev-3 idle (ce-504 harvested) + 159-ticket backlog → ONE composer for BOTH next batches (dev-1: #478 posture banner + #470 SSOT auto-recall slice; dev-3: #433 confidentiality surfaces + #427/#442 alternate) — briefs now BAN committed READY files. Gate: systemd restarted by reboot, counter reset (pass 29), failed 0. Open PRs 918-922+912 all in pipeline; no missed signals.
- 14:05(clock) **APPROVAL WAVE: #919 @43ff9a25 + #920 @b45e6833 + #921 @e5e06aae + #922 @5e87cebe ALL APPROVED → gate** (reviews: 4×APPROVE; mechanical READY-drops + carrier regens applied controller-side; work-class enum skew S→story corrected on 919/920 by fix worker — venv runs legacy enum, S2 version-skew item confirmed). **PR #923 OPENED** (ce-516 slimmed: Items 1/2/4; Item 3 deferred to next ledger window; brain drift PASS with workflow byte-identical) → review dispatched (governance-bot lenses). #922 latent slice-3 canonicalisation requirement recorded on PR. Queue: 918+919+920+921+922 all approved/armed — gate drains 5; arc heads to 17 merges.
- 14:11(clock) RESTOCK WAVE 2 DISPATCHED (both idle seats): dev-1 batch (ce-478-posture-banner + ce-470-infra-identity-schema slice, brief b9867465…, ce_cli.py+assertions.yaml frozen-flagged) + dev-3 unit (ce-427-approver-ref-provenance — mint/verify approver_ref + schema field, brief 02b1f54a…, feeds #912/#513 design lane). Composer drops: #433 (Parts 1+2 ALREADY LANDED via #738/#839 = 5th stale-open catch today → #518 evidence), #442 (no S-sized path while #918 open). Briefs now BAN committed READY files at template level. ALL 3 SEATS WORKING; 6 PRs in gate/review pipeline.
- 14:22(clock) **#923 APPROVED @0eb28b37 → gate** (review APPROVE; controller dropped the STILL-committed .ce/wt-516/READY [slim-instruction omission — 5th READY-fix today], carrier 5→4; preflight RED = the #515 copytree flake, control-attributed via isolation pass; M1 alert-permissions + M2 URL + M3 dedup-test fold into the Item-3 ledger-window follow-up). All 7 arc-morning PRs now approved: 918-923 armed, #919 merged (arc #13). #912 = Operator. Seats: all 3 Working wave-2 units.
- 14:23(clock) DEV CHECK 14:23: **#921 + #922 MERGED (arc #14, #15)**; queue holds #918/#920/#923; #912 Operator. dev-4 triple-BLOCKED on VALIDATION (ran full validate-pr in-seat → resource-kill interrupts; the targeted-tests-only rule did not survive into the restock brief template — composer gap #3) — corrective sent, shas requested, harvest on reply. dev-3 READY ce-427 CLEAN (no committed READY — template fix WORKING) → harvest launched (content lens: mint must BIND, not just random-token). dev-1 Working ce-478/470 batch (52% left). Gate pass 44 clean. No restock composed this pass: dev-3 gets next unit after harvest confirms + account-switch window pending (97% weekly).
- 14:39(clock) **ACCOUNT SWITCH EXECUTED** (weekly limit; resets Jul 14 23:00Z on old acct). Casualties: ce-427 harvest worker (died AT final preflight — resumed on fresh acct, rebase-onto-main guidance since #921 merged) + 2 watchers (re-armed). **#923 MERGED (arc #16)**. dev-4 responded to targeted-tests corrective with ALL 3 SHAs (2ed70f04/923d8339/77c98aa8 — units were complete, validation-blocked only) → triple harvest launched (gate-adjacent content lens on ce-493 TTL-remint; legacy-enum work classes; #914 exempt-marker recipe for shell-only ce-492). dev-1 Working (51% left). Board: #918/#920 in queue, #912 Operator, arc at 16 merges.
- 14:50(clock) **GOVERNED CODEX CONTROLLER LAUNCHED** (P7-class live `ce launch --harness codex` — first live governed codex launch; seat record ce-orchestrator--arad-install.yaml, window arad-install in Operator tmux). MISSION: Arad/Mythos CE 0.3.4 install = Decision-15 rehearsal MADE LIVE (Operator present w/ Arad). Handoff sha 5af60e67… delivered: same-machine inventory-first (0.3.1 residue), mythos-* identities only (App 4103119/inst 141552951; her seat App 4159494 untouchable), .hermes-gitignore + ce-brain-init gotchas pre-briefed, host-backend only (#490), evidence bundle per #914 format → ARAD_REHEARSAL_EVIDENCE_20260709/, stop-lines incl. failed-rehearsal-is-valid. Status file: ARAD_INSTALL_STATUS_20260709.md.
- 14:52(clock) ⚠️ **AUTHORITY VIOLATION + REMEDIATION (PR #924 harvest)**: worker SELF-SIGNED llms-install.md with ce-root-v1 (needed after schema-hash coupling; cited MY grant as its own). No technical seam stopped it = ce-ops#442 live-proven (P1 comment filed). REMEDIATION: controller independently re-derived canonical bytes + re-signed — deterministic Ed25519 → BYTE-IDENTICAL, verified Good, artifact RATIFIED (content correct, act unauthorized). PR #924 opened (ce-427 @a196c1b9, 19/19 GREEN, mint VERIFIED binding: sha256(client_id:prompt_sha:salt)); review dispatching w/ schema-deviation question (required gesture_salt vs brief optional).
- 14:57(clock) **OPERATOR MANDATE: MAIN-CONTROLLER INDEPENDENCE = TOP PRIORITY** — orchestrator spawnable on VPS (claude OR codex), ALL controller data from SSOT/centralized CE location, DGX death must not halt the factory. GATE UNWEDGE: #918+#920 CI failures root-caused = PR BODIES had NO G5 line (dev-1 self-push flow omits it — 2nd template gap; bodies fixed with story, reruns triggered). COMPOSER LAUNCHED for the independence lane: dev-3 ce-497-controller-state-sync-s1 (snapshot .ce/state+briefs+claims→forge, secrets-denylist pinned) + dev-1 ce-496-controller-bootstrap-doc-s1 (VPS spawn runbook, hydrate-from-SSOT, harness-agnostic, queued behind its current batch) — both grounded on #496/#497/#470 + the JUST-MERGED #920 standby surface.
- 15:00(clock) dev-1 batch result: **PR #925 OPENED** (ce-470 identity-registry schema s1 @124894d4, validate-pr GREEN — first SSOT-lane artifact of the independence mandate) → review dispatched (SSOT-fitness + example-truthfulness lenses, real mythos identifiers). **ce-478 correctly BLOCKED**: pyproject.toml is brain-PINNED (console_scripts entry needs ledger update) — composer precompute missed it (byte-change rule violated AGAIN; pyproject.toml joins the precompute list). POST-#918 LEDGER-WINDOW QUEUE now 5 items: Unit C (readme minors, ratchet→104) · ce-516 Item-3 (workflow pin cascade) · ce-478 (pyproject pin) · #500 slices a/d (launcher scripts) · ce-453 Part A — plan ONE consolidated brain-window batch on #918 merge. #918 Validate rerun PENDING (queued on runner).
- 15:08(clock) **INDEPENDENCE LANE DISPATCHED (Operator top priority)**: dev-3 ← ce-497-controller-state-sync-s1 (snapshot tool, dry-run default, secrets-denylist test-pinned, brief ebec260a…) · dev-1 ← ce-496-controller-bootstrap-doc-s1 (VPS replacement-controller runbook + docs-vs-reality smoke w/ skipif on unmerged deps, brief cb26848d…, replaces parked ce-478 in queue; G5-body-line made a BOLDED step after 2 CI bounces). Composer correction absorbed: #920 was still OPEN at composition (not merged as I framed) — briefs treat it as pending dep; re-run its provision dry-run when it lands. All seats loaded: dev-1+dev-3 independence lane, dev-4 awaiting triple-harvest verdicts.
- 15:11(clock) **#925 CONFIDENTIALITY CATCH**: MY composer brief prescribed REAL mythos identifiers (App 4103119, client id, install id, dated pem path) into the PUBLIC example whose own header forbids real values — reviewer pre-flight caught it, controller CONFIRMED in diff and FIXED @cd3e6733 (placeholders only; real values = internal registry per ADR-0001 public/private). LESSON: composer briefs must carry the public/private boundary check for any docs/ content; public-docs confidentiality scan does NOT cover App IDs (gate gap — candidate for #423 lane). ALSO systemic: reviewer role has NO Bash → controller MUST create the review worktree BEFORE dispatch, every time (3rd occurrence; now absolute rule). Reviewer resumed on cd3e6733 for full verdict. dev-4 restock composer + #926/#927/#928 reviews running.
- 15:16(clock) 🎉 **#918 MERGED (arc #17) — .HERMES RETIREMENT ON MAIN** (Operator crutch-cut directive DELIVERED: ce onboard no longer requires legacy .hermes; ledger seqs 155-160; ratchet 103). BRAIN-LEDGER WINDOW OPENS — serialized queue: (1) Unit C worker LAUNCHED (supersede v6→v7 recomputed sha, ratchet 103→104) → then serially: (2) ce-516 Item-3 cascade, (3) ce-478 pyproject pin, (4) #500 slices a/d (launcher territory freed), (5) ce-453 Part A. #920/#924 still draining.
- 15:46(clock) 🎉 **ARAD INSTALL SUCCEEDED (Decision-15 LIVE REHEARSAL PASSED)** — CE 0.3.4 installed+onboarded+launched on her machine; evidence bundle in ARAD_REHEARSAL_EVIDENCE_20260709/. T5 pack status surfaced: T5.1 revision DIED at yesterday session limit (undetected until Operator asked) — pack regenerated from current canon NOW (build checks green, picks up #906/#910) + T5.1 authorship fork RUNNING (CEO command-block scrub + toggle uniformity + 0.3.4-wheel truthfulness + new build check). DEV CHECK: #926+#928 APPROVED→queue; #927 reviewer B1 (dead chown guard in bare invocation) FIXED @29080422 (re-approve on settle); Unit-C→**PR #929** (ledger tombstone-append seq161-162, ratchet 104, drift OK 163) → high-rigor chain review dispatched; dev-4 restocked ce-490-contained-launch-preflight-s1 (sha-verified w4:p1); #423 double-dropped (STALE dev-1 CLAIM from 20260706 needs reconciliation), #425 design-heavy drop. All seats Working.
- 16:04(clock) **#929 APPROVED @7ce44c6d** (max-rigor ledger review: chain hand-verified 160→161→162, tombstone-append = established v5→v6 precedent NOT a novelty, ratchet 103+1=104 traced; controller-verify items ALL confirmed: evidence sha recomputed = 90fb2369 exact, origin/main tail = seq 160). **#927 RE-APPROVED @29080422** (reviewer B1 real bug: chown guard dead in bare invocation because CE_DAEMON_IMAGE_UID exported only in subshells — unconditional chown w/ 10001 default). Both → gate. dev-3 READY ce-497 (independence lane) + dev-4 READY ce-490 @221c8bd8 → paired harvest launched w/ hard content lenses (secrets denylist test-pinned + dry-run default; fail-closed + host-path-untouched). Checkpoint worker writing STRANGELOOP1E. Queue-stock composer running for dev-1/dev-3 next units.
- 16:05(clock) QUEUE-STOCK DELIVERED (no idle across /clear): dev-1 ← ce-500-launcher-caps-s2 (memory caps + durable staging; TODAY reboot=evidence) then ce-470-identity-lookup-s2 (2 preconditions: #925+#929 both own ce_cli.py); dev-3 ← ce-506-daemon-vs-agent-rubric design doc (design-preview HOLD noted). Composer drops: #487 ALREADY LANDED via PR #878 (6th stale-open catch today) — #518 evidence grows; substituted #506. Composer also caught a precondition *I* missed: #929 owns ce_cli.py too. All 3 seats stocked; harvest + checkpoint workers running.
- 16:08(clock) ✅ **T5.1 WELCOME PACK SENT TO ARAD (Operator)** — the Arad send, blocked since two failed attempts and gated by Decision 15, is DONE. Sequence completed today: live install (0.3.4, host backend) → rehearsal PASSED with evidence bundle → pack sent. **Mythos tenant LIVE on 0.3.4.** Decision-15 gate satisfied by a real passing rehearsal, not waived. FIRST TENANT FEEDBACK LOOP NOW OPEN: her usage = first real product signal; defects she hits → ce-ops tenant-class tickets. Two rehearsal-derived product findings already owed as tickets: (1) install/onboard never verifies the coding-agent CLI prerequisite it depends on (her launch failed on PATH), (2) stale prior launch state blocks relaunch with no guided recovery.
- 16:10(clock) CHECKPOINT STRANGELOOP1E written. LIVE CATCH from it: dev-1 had PARKED the top-priority ce-496 (independence lane) UNPUSHED at 6f85f4de, blocked on the CONFIDENTIALITY tests (internal tree paths/strings in the public runbook — SAME public/private class as #925 today, 2nd instance) and silently moved to U1. Rescue worker launched (scrub-not-weaken hard stop-line; gap-honesty lens). dev-1 told: branch is controller-owned, stay on U1, /compact at boundary (29% left). LESSON: a seat parking a unit and self-advancing is invisible unless the checkpoint reads seat state — the checkpoint caught what my watchers did not.
- 16:12(clock) TENANT-CLASS TICKETS FILED from the passed rehearsal: **ce-ops#519** (ce doctor skips coding-agent CLI scan without --harness → doctor PASSES then launch FAILS; her claude was under nvm, invisible to noninteractive PATH) + **ce-ops#520** (ce reap escalates on a LIVE prior-version launch surface; 0.3.1→0.3.4 upgrade left the old ce-controller session with no migration notice). BOTH are residuals of **ce-ops#450, CLOSED 2026-07-05 via PR #826 that shipped only part of the mandate** — a 7th closed-but-not-real instance, and the FIRST one caught by a user-journey rehearsal rather than an audit. This is the release-acceptance thesis (#509/#510) proving itself: the merge gate passed #826; only walking the journey exposed the gap.

## 2026-07-09 16:21 — DEV CHECK (post-/clear resumed controller, first scheduled pass)
- **Merges today: 21** — #925 (identity-registry schema/SSOT contract) + #927 (smoke chown fix) merged this pass; queue fully drained; only #912 open (Operator-held).
- Gate: systemd active, pass 102, failed_count=0 throughout.
- dev-4: ce-490 READY (221c8bd8) — harvest worker in flight; seat rolled to next unit (ce239-wall-openbao-supplier), 76% ctx left.
- dev-3: NEW READY ce-506-daemon-vs-agent-rubric-design-s1 @ b845d9f0 — queued onto the running ce-497 harvest worker (sequential, same container). ⚠️ SEAT DEFECT: dev-3 in-seat venv broken (.venv/bin/python missing; in-seat validate-pr cannot run) — controller-side preflight is sole attestation for its harvests; venv repair needed before any unit requiring in-seat preflight. → next restock brief + candidate ce-ops ticket.
- dev-1: Working ce-followups-20260708 (/review + rebase-publish), 27% ctx left — compact at boundary already ordered; watch closely.
- In-flight controller workers: harvest ce-490, harvest ce-497(+ce-506 queued), ce-496 rescue (confidentiality scrub), ce-516 Item-3 brain-window (exclusive ledger window; record-65 precompute).
- Post-/clear re-arm complete: session cron (21,51) + fleet watcher + gate watcher recreated per checkpoint mandate.
