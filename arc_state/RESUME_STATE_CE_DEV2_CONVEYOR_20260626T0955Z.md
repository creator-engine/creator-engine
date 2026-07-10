# RESUME STATE — CE-DEV-2 Controller · Day-shift arc · 2026-06-26T09:55Z (CHECKPOINT for fresh context)

## ⚠️ SEAT IDENTITY & TOPOLOGY — READ FIRST
THIS host = **DGX Spark** (`spark-b824`, user `cedev2` uid1003, GB10 aarch64). Controller CE-DEV-2 runs ON the DGX, `~/creator-engine`. Foreman model: substantive work → seats; controller holds coordination + merge gate. Full topology/creds: **MEMORY.md READ-FIRST block**.
- **dev-1** = NON-contained codex, tmux `ce-dev1-orchestrator` (%0) on VPS (user ce-dev-1, `~/creator-engine`). Reach `ssh dev1`. Reviews as **ce-dev-1** (its own GH identity = valid peer review).
- **dev-3** = CONTAINED `ce-vps-codex` on VPS (`/workspace/creator-engine`). Reach `ssh dev1 'sudo docker exec -u ce-dev-3 ce-vps-codex bash -lc "…"'`. Dispatch: write packet to its `/workspace/creator-engine/tmp/`, then `HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock herdr pane send-text w1:p1 "<msg>"` + `herdr pane send-keys w1:p1 Enter`. Verify via `herdr pane read w1:p1 --source recent` (look for `Working`).
- **dev-4** = CONTAINED `ce-dgx-codex` LOCAL on DGX. Reach `sudo docker exec ce-dgx-codex bash -lc "…"` (no ssh). Same herdr dispatch pattern (socket inside container, pane w1:p1). Real codex home host path = `/home/cedev4/.codex-contained`.
- Creds: overwatch (`~/.ce-keys/overwatch.env` → `GH_TOKEN=$CE_OVERWATCH_PAT`, author/push/merge); reviewer (`~/.ce-keys/ce-dev-2.pat`). ISSUES=ce-ops repo; CODE/PRs=creator-engine. Repo slug = **creator-engine/creator-engine** (NOT ce-overwatch/...).

## ACCOUNTS
Fleet on **neckar@gmail.com**. Verify by EMAIL ([[ce-openai-account-email-mapping]]), never A/B labels.

## FLEET (all Working on neckar@, foremen) @ 09:55Z
- **dev-1**: ce-ops#166 slice-2 (branch `ce166-knowledge-ssot-slice2`). ALSO peer-reviewing 3 controller-authored PRs — DID #510 (approved 09:54Z); still owes **#509** + **#498**(substance).
- **dev-3**: ce-ops#224 restore dropped `lane` harness row (branch `ce224-restore-lane-harness-row`). Packet: its `tmp/PKT_dev3_ce224.md`.
- **dev-4**: ce-ops#240 contained-controller image scaffolding, Dev Mode Leg C1 (branch `ce240-contained-controller-scaffold`). Packet: its `tmp/PKT_dev4_ce240.md`.

## CONVEYOR / MERGE TRAIN (main HEAD 0966731)
- ✅ MERGED today incl this session: #505(#252 validate-pr), #508(#248 playbook-run), #504(#250 herdr flaky-fix), #506(#253 inbox).
- 🔵 #510 (CI live-base churn-fix): **IN QUEUE pos1**, peer-approved by ce-dev-1 → draining. KEY — ends the currency churn.
- 🟠 #507 (#244 Worker tier): APPROVED + auto-merge; failing on base-CURRENCY (G-ii/live-base), NOT a real test fail. Will drain after #510 lands (re-run or one update-branch). dev-1-authored + controller fix-up 2ecb377 (test fixture).
- 🟡 #509 (#252 validate-pr CI-parity): controller-authored, HELD for dev-1 review (pending).
- 🟡 #511 (#235 dequeue, dev-4-authored): NEW harvest → **controller cross-model review + enqueue** (dev-authored, OK to self-review-as-ce-dev-2). Full-suite NEW=0, forbidden-path PASS, carrier ok.
- 🟡 #512 (#188 belt-reviews claim-bridge, dev-3-authored): NEW harvest → **controller cross-model review + enqueue**. (#188 core already merged via #411; this is the follow-on bridge.) Full-suite NEW=0, carrier ok.
- ⏸️ #498 (#198 dogfood): DIRTY + stale-APPROVED. Needs CONFLICT-REBASE = force-push to existing PR branch → **requires explicit Operator OK** (auto-mode blocked an unprompted attempt). Then dev-1 final review → enqueue.

## ⭐ KEY LEARNINGS THIS SESSION
1. **`ce validate-pr` shipped NARROWER than CI** — default was `validators/tests/unit` (unit-only) vs CI's full `validators/tests/ -m "not wheel_bake_gate" -q -n auto --dist loadgroup`. A preflight weaker than the gate = false-green (let #507's integration failure through harvest). Fix = #509. Banked to [[ce-run-full-preflight-before-push]].
2. **Live-comparison base-currency check resurrected rebase-churn even with strict-off** — `validate.yml`'s "Resolve live comparison base" hard-failed behind-PRs in pull_request context, blocking queue entry. Fix = #510 (scope hard-fail to merge_group). This is the real end of the [[ce-merge-queue-strict-antipattern]] churn.
3. **Harvest baseline-diff MUST run the FULL suite** (unit+integration), not unit-only — now standard in harvest prompts. Use `ce validate-pr` once #509 lands.
4. **The "63-79 baseline failures" are DGX-local-venv/env artifacts** (TMPDIR/wheelhouse) — a clean CI-pinned `.venv` runs 0-failed; CI's container is green. Only NEW=0 (symmetric-diff) matters.
5. #504 = flaky xdist test (`w2`/`w3` substring vs `popen-gw2/3` worker ids), #507 = non-conforming test fixture — both controller fix-ups, test-only, re-approved as ce-dev-2.
6. **Controller fix-up vs controller-AUTHORED:** fix-up commits on top of dev PRs → controller re-approves as ce-dev-2 (OK). Net-new controller-authored PRs (#509, #510, #498) → MUST get dev-1 peer review (no self-approval). dev-1 is the only non-contained reviewer (chokepoint = autonomy #243).

## STANDING AUTHORITY (DAYSHIFT_ARC_20260626_AUTHORITY_MANIFEST)
G1-G5 GRANTED (conveyor merge / queue+dispatch+seat-lifecycle / #249 / OpenBao wall / autonomy canary). R1-R6 RESERVED. Auto-halt → Operator. Operator driving turn-by-turn this session (autonomous /loop NOT armed).

## NEXT ACTIONS
1. Cross-model review + enqueue **#511** (#235) and **#512** (#188) — dev-authored harvests, ready.
2. Watch **#510** merge → then **#507** drains (re-run; one update-branch only if still currency-red). Confirm #509 once dev-1 approves; enqueue.
3. Collect dev-1's **#509 + #498** reviews. #498 also needs Operator OK for conflict-rebase before merge.
4. When **dev-3 #224 / dev-4 #240** stop-line → harvest (FULL-suite baseline) + retask. Open ce-ops units: #233/#234/#236-239/#251/#226/#177.
5. Surface to Operator ONLY: autonomy canary, reserved R1-R6, auto-halt.
