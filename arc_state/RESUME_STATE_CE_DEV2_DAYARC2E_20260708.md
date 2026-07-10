# RESUME STATE — CE-DEV-2 — 2026-07-08 ~16:2x — DAY-ARC-2 CLOSING checkpoint

> Supersedes DAYARC2D. READ ORDER: MEMORY.md → .ce/state/decisions/DECISIONS_20260708.md
> (NOW 13 items — 12 dual-format emission, 13 one-face doctrine, both dual-written dev-1)
> → this file. Prior context: DAYARC2D + transcript tmp/08jul2026_1410.md.

## MERGED TODAY (through containerized gate): NINE, #905 imminent = TEN
#895 IaC redeploy · #896 seat-ready · #897 Ring-1 provenance · #898 broker v1 s1 ·
#899 refresh-guard · #900 RELEASE 0.3.4 · #901 followups b1 · #902 materializer s1 ·
#904 materializer s2 (history scan/closeout/runloop/pre-arming remediations, dry-run) ·
#905 followups b2 (APPROVED, CI green, daemon enqueuing — VERIFY merged on resume).

## MATERIALIZER (CE-491) STATE
Slices 1+2 ON MAIN, dry-run only, ARMING_ENABLED=False hard. PRE-ARMING CHECKLIST
(all on PR records #902/#904 + followups ledger): (1) integration test exercising XOR
gate via run_preflight real sequence; (2) ACTOR_VERSION bump; (3) path.resolve()
normalization in _require_state_subtree (SOLE write guard — HARD pre-arming req);
(4) closeout-gate registration decision (deferred to arming slice by design).
Then slice 3 (arming lane) → OPERATOR ARMING CALL (joins awaiting-operator queue).
App ce-materializer 4244593/inst 145152358 provisioned+chain-verified (DAYARC2C).

## SEAT/FLEET STATE
- dev-3: FULL PARITY PROVEN (self-push canary via broker PASS, PR #903 closed per
  hygiene). Recipe+gotchas in memory ce-dev3-selfpush-canary-green. IDLE.
- dev-4: slice 2 harvested+merged. IDLE. Workspace still parked on stale ce239 branch
  (hygiene item in ledger). Image gap: NO libsodium (proven cause of examples false-RED).
- dev-1: followups b2 self-pushed (#905). IDLE after merge. Two clean stop-line saves
  today (dev-4 environmental false-RED, dev-1 out-of-scope test) — discipline WORKING.
- PATTERN TICKET-WORTHY: seat-side preflight diverges from CI on portability gate
  (both archs, proven environmental via clean-main controls) + libsodium — the
  seat-ready profile (#896) can't be trusted RED until fixed. Ledger has evidence.
- Gate daemon healthy (610+ passes). dev-3 broker units: ce-egress-broker-dev3.service.

## RATIFIED TODAY (persisted: memory topic files + DECISIONS 12/13 + MEMORY.md index)
- Dual-format emission (ce-dual-format-emission-doctrine): every user-facing artifact
  ships md/yaml (agent) + offline HTML (human); md-sources INSIDE bundles.
- One-face doctrine (ce-one-face-doctrine): one authority-holding operator-facing
  controller per human; other surfaces emission/proposal-only; POLICY singleton
  (IaC-redeploy bound); per-human AND per-deployment; bottleneck claim era-bound.

## ARAD LANE — send-ready pending Operator preview
T4 pack DRAFT DELIVERED to Operator: tmp/arad-pack-0.3.4/ (191KB offline index.html
+ 18 md sources per dual-format doctrine; ALL render/product-lens/vocab checks PASS;
13 vocab edits logged in the assembly report). 4 judgment items flagged — controller
recs: fix README reading-order contradiction (#1) + budget line in sample report (#3);
#2/#4 acceptable. AWAITING: Operator preview verdict (+patch call) → Operator SEND.
Apply already DONE (55bd315). NO #494 note needed in pack.

## NEXT ACTIONS QUEUE (post-/clear session)
1. Verify #905 merged; sweep .ce/wt-905-review + wt-491s2-harvest worktrees.
2. If Operator greenlit T4 (±items 1/3): patch via utility agent, re-render-check,
   redeliver; send remains Operator-only.
3. Dispatch next wave (seats all idle): (a) seat-preflight-divergence fix unit
   (portability invocation parity + libsodium in both images — needs image rebuild
   coupling); (b) pre-arming checklist batch; (c) Ring-1 live smoke (decision 4b,
   controller-driven); (d) dev-4 DGX egress-broker deploy (last parity item, host op).
4. MEMORY.md compaction agent was finishing (one-face index line handed to it
   mid-flight) — VERIFY the line landed + file <16.9KB + dual-format ref survived.
5. Followups ledger now ~20 items — next batch unit when wave settles.

## ⏸️ AWAITING-OPERATOR (2 + 1 soon)
1. Arad T4 preview verdict (then Operator sends — LAST Arad step).
2. Nitzan D6.
3. (Soon: materializer ARMING after pre-arming checklist + slice 3.)
