# RESUME STATE — CE-DEV-2 controller (Orchestrator) — 2026-06-28 ~05:20Z — DAY-ARC FAN-OUT WAVE 1 LIVE

> NEWEST. Open this + MEMORY.md FIRST. Supersedes 0405Z checkpoint.
> ⭐ I am the OVERARCHING ORCHESTRATOR (Operator 2026-06-28): drive work via codex controllers (dev-1/3/4), never inline build work. See ⭐⭐ directive in 0405Z checkpoint + [[ce-dev2-orchestrator-role]].

## IDENTITY / AUTH (see MEMORY.md header)
CE-DEV-2 on DGX. overwatch: `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. Approve as ce-dev-2: `GH_TOKEN=$(cat ~/.ce-keys/ce-dev-2.pat) gh pr review <n> --approve`. Merge: `gh pr merge <n> --auto --merge`. Issues=ce-ops; PRs=creator-engine.

## OPERATOR LANE THIS SESSION
**Engine fan-out ONLY; onboarding (W10 Nitzan/Arad) HELD** (Operator choice 05:00Z). 0.3.0 sign also deferred (rides onboarding). Drive W1–W9 engine; halt at 🔒 lines.

## PROVEN DISPATCH MECHANISM (repeatable — use for all seats)
- **dev-1** (VPS, NON-contained codex, tmux `ce-dev1-orchestrator:2.0`): `cat brief | ssh dev1 'cat > /tmp/X.md'` → relay: `tmux send-keys -t T C-u` (×3) → `send-keys -t T -l "pointer+sha"` → `send-keys -t T Enter`. Verify `Working` via capture-pane.
- **dev-3** (VPS, CONTAINED `creator-engine/codex-runsc:x86_64`, via `ssh dev3`): `cat brief | ssh dev3 '...docker exec -i $CID tee /tmp/X.md'` → `docker exec -e HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock $CID herdr agent send w1:p1 "ptr"` + `herdr pane send-keys w1:p1 Enter`. CID via `docker ps -q --filter ancestor=creator-engine/codex-runsc:x86_64`.
- **dev-4** (DGX-LOCAL, CONTAINED `ce-dgx-codex`): `cat brief | sudo docker exec -i ce-dgx-codex tee /tmp/X.md` → `sudo docker exec -e HERDR_SOCKET_PATH=... ce-dgx-codex herdr agent send w1:p1 "ptr"` + `... herdr pane send-keys w1:p1 Enter`.
- ALWAYS: pointer+sha (brief content via stdin→tee, never argv — quoting). Verify landing via `Working`/`esc to interrupt`, NOT the input box (clears on submit; shows greyed suggestion when idle). Briefs saved in `.ce/briefs/`.

## WAVE 1 — DISPATCHED & WORKING (as of 05:20Z)
- **dev-3 ← W4a** (#592 / ce-ops#292): rebase `ce-292-autoreview` onto main (#596 guard `ca496fb1`) + behavioral never-APPROVE test. Brief: `.ce/briefs/brief-ce292-w4a-autoreview-rebase.md`. dev-3 originally authored #592. 🔒-next = ARM (#592).
- **dev-1 ← W2** (Autonomous Release Phase A): release-bump/changelog/orchestrator/release.yml. WRAP existing `release_publish.py stage_signed_release` (don't reimplement). NO publish/auto-sign. Brief: `.ce/briefs/brief-w2-autorelease-phase-a.md`. 🔒-next = release/* tag ruleset + offline ce-root-v1 sign.
  - ✅ SEAM RULED (05:35Z): dev-1 correctly STOPPED at stop-line (found release-stage in `cli.py` not `ce_cli.py`). RULING = release family → **`cli.py`** (creator-engine-validator), alongside release-stage; wrap release_publish by import; **ce_cli.py NOT touched**. dev-1 resumed Working. ⇒ **ce_cli.py is now FREE — W6a/W8 NO LONGER blocked behind W2** (they still serialize vs each other on ce_cli.py).
- **dev-4 ← W3** (evidence-bundle press-merge): aggregator+renderer, REUSE fanin_runtime.py, has_authority:false, PROPOSE-don't-freeze schema, DON'T edit ce_cli.py (stub). Brief: `.ce/briefs/brief-w3-evidence-bundle-press-merge.md`. OPEN DESIGN Q deferred to me: new schema vs extend `ce fanin` (seat will surface in PR body).

## KEY CONSTRAINT (governs all sequencing)
**`ce_cli.py` = universal collision point** (every `ce` subcommand registers there). RULE: **dev-1 owns ALL ce_cli.py edits**; feature seats build logic in own modules + leave TODO stub. W6a/W8 CLI work REBASES on dev-1's W2. Don't run two ce_cli.py editors concurrently.

## NEXT WAVE — PREPPED / QUEUED (dispatch as seats free)
- **W1a CEO-mode dry-run** (TOP BET): design+brief worker RUNNING (agent ab481b0c). classify-only, NO merge; DoD classify ≥3 recent PRs + log. Dispatch to first free seat.
- **W6a `ce push`**: needs a LIVE broker to prove 200 → route to **dev-3 after W4a** (dev-3 broker live; dev-4 broker = 🔒 W6b not up). ce_cli.py → after dev-1's W2.
- **W8** triage planner (#187) + #42 `ce dispatch plan` + labels: ce_cli.py → dev-1 after W2; needs #187 design (fetch).
- **W9a/c brain** (MEMORY→SSOT migrate + ingest): need HOST-LOCAL MEMORY.md/corpus → route to MY OWN host implementer worker, NOT a contained seat. W9b (hydrate wiring) = code, can be a seat (ce_cli.py → after dev-1).
- **W5** annoyance→tool: HOLD until W4 arms.
- **Follow-up tickets** (strangeLoop run_mode, G5 body-line auto-emit, dev-4 libsodium, #602 SSOT app-ids, empty-commit-no-CI): file via ops_triage or inline gh.

## GATE / WATCHERS
- Merge gate (queue-daemon) HEALTHY — recon's wall alarm was a misread; enqueue_count=0 = correct idle-skip of unapproved PRs. Wall token valid to **15:42Z** (G4 renew before then). Canary the enqueue path on next approved+green PR (#600 candidate).
- Only open PRs at dispatch: #592 (dev-3's W4a target), #600 (dev-1 ce-ops#334, CI in-progress).
- Crons live: seat-check :00, poll-devs :05, belt-canary :03/5m, conveyor-tend :30, controller :47.

## HARVEST/GATE RHYTHM
As each seat finishes (READY-FOR-HARVEST or pushed PR): harvest if needed (harvest_intake worker) → review (as ce-dev-2 or reviewer worker) → hold gate → dispatch next lane. I hold the merge gate; seats never approve/merge/enqueue.

## ORCHESTRATION LEARNINGS (capture → brain W9, per role directive)
- Brief-distillation via architect_research workers keeps MY context lean while producing drop-in self-contained briefs — strong pattern for design-open or host-local-doc-dependent lanes.
- `.ce/state/research/` is gitignored/host-local → any lane depending on it MUST embed content (seats can't read it). MEMORY.md likewise.
- Proving ONE dispatch (dev-3, the contained/hardest path) before fanning out de-risked the whole wave.
