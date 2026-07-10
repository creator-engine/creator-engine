# RESUME STATE — CE-DEV-2 Orchestrator — NIGHT-ARC (autonomous) — 2026-06-28 ~17:48Z

> NEWEST. Operator signed out 17:48Z and handed the factory over: **drive the night-arc to completion autonomously.** Open this + MEMORY.md FIRST. Supersedes the 1557Z day-arc checkpoint.
> ⭐ ROLE: OVERARCHING ORCHESTRATOR — drive via seats/workers, NEVER inline. Author≠approver. NO seat idle.

## AUTONOMOUS MANDATE + HALT LINE
Standing authority (ADR-0013 action-taxonomy, ratified+merged today as #620): **AUTONOMOUS** = dispatch · harvest · route review · submit reviewer verdict (author≠reviewer) · merge/gate (independent review + green CI + declared work-class + ratified + never-red + in-arc) · conveyor next-lane · checkpoint. **RESERVED → HALT + surface, do NOT execute**: any live auto-merge/AutoReview **arming flip**, strangeLoop arming, release sign/publish, deploy, fleet rollout, history scrub, weakening a guard, broadening a worker envelope, irreversible/destructive, new/ambiguous high-consequence scope. Building the CEO-mode/auto-merge machinery is autonomous; ARMING it is reserved.

## AUTH
overwatch: `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. Approve as ce-dev-2: `GH_TOKEN=$(cat ~/.ce-keys/ce-dev-2.pat) gh pr review <n> --approve`. Merge: queue-daemon (pid 43010) auto-merges approved+green — just approve as ce-dev-2; never merge CI-red. Agent routing pinned: reviewer/implementer/architect_research=sonnet, verification=haiku, Opus=controller only.

## IN-FLIGHT (reconcile on resume)
- **dev-1** (VPS, tmux ce-dev1-orchestrator:2.0, SELF-PUSH, double-Enter) → **#350** authority-envelope wiring (branch ce-350-reviewer-authority-envelope-wiring; brief ~/ce-briefs/ce-350-dev1.md on VPS). Self-pushes a PR → independent review + gate.
- **dev-3** (contained ce-vps-codex; poll `ssh dev1 'sudo docker exec -e HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock ce-vps-codex herdr pane read w1:p1'`) → **CEO-A** automerge-decide CI workflow (branch ce-automerge-decide-ci). On READY-FOR-HARVEST → harvest_intake → review → gate.
- **dev-4** (contained ce-dgx-codex DGX-local; poll `sudo docker exec -e HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock ce-dgx-codex herdr pane read w1:p1`) → **BRAIN-A** semantic recall into controller launch (branch ce-brain-hydration-launch). On READY → harvest → review → gate.
- **#624 fix worker** (implementer a817eff7) → fixing the fail-OPEN bug on empty required_checks in `forge/automerge_actuator.py` + adding 3 predicate tests; pushes to branch ce-automerge-actuator. → on land: re-review the delta + gate #624.

## GATE BOARD
- **#624** (dev-1 CEO-B, gated automerge actuator) — REVIEW_REQUIRED, in fix-loop (fail-open #1 real → fixing; "ce-ops# in carriers" #2 was a reviewer FALSE-POSITIVE — carrier metadata ce-ops#NNN is gate-accepted, do NOT scrub). After fix lands → re-review (focus: empty-required_checks now refuses; dormant-in-dev preserved) → gate.
- Everything else this session MERGED: #618/#619/#620(ADR-0013)/#621/#622(#349 keystone)/#623(pins).

## NEXT-WAVE QUEUE (dispatch as seats free — all probed file-disjoint BUILD; verify-not-already-landed first)
From the slice-map (architect_research abaf633d). Each: fresh worktree off origin/main, born-foreman, contained seats emit READY-FOR-HARVEST (no push) / dev-1 self-pushes, full validate-pr GREEN, `- **Declared work class:** <tier>` in manifest+body, stop-line = no arming/flip.
- **BRAIN-B** — recall eval harness (story). Paths: `validators/creator_engine_validator/brain_eval.py` (new), `validators/tests/unit/test_brain_eval.py` (new), `ce_cli.py` brain-group only (~L860-1050, disjoint from automerge ~L1456). Offline-safe.
- **CEO-C** — verify/extend `ce automerge-decide` CLI (tiny). FIRST verify the TODO at automerge_policy.py:375 isn't stale (CLI may already be registered at ce_cli.py:1456 → may be a tiny verify/doc task). Paths: `ce_cli.py` automerge section, `forge/automerge_policy.py`.
- **CEO-D** — `ce automerge-status` decision-log reader (tiny). Paths: `ce_cli.py` (new subcmd), `forge/automerge_policy.py` (add load_decision_records()).
- **#346 AutoReview run_mode `--run-mode` CLI wiring** (couples to broker; UNBLOCKED now #349 merged). Close #347 as dup of #346 first. Touches the broker — DO NOT run concurrently with #350 (both touch ce_egress_self_review_broker.py).
- **ORCH-1..12** (orchestrator epic) + **FORGE-1..6** (forge-side epic) — design docs ARE on main (docs/design/ce-orchestrator-agent*.md, ce-forge-side-automation*.md). Read them to derive each slice's allowed-paths; most are docs/schema/cli additions, file-disjoint. ORCH-9/10 touch ce_cli.py new group; none touch broker/cred-proxy per epic scope. FORGE-1 live-mutation phases (branch-protection apply, App provisioning) are RESERVED — build only the plan/join-PR surface.
- **#137 brain SSOT services-section**, KNOWN_PENDING burndown (controller-bootstrap-injection.md ce-ops#244 — now unblocked, #620 merged) — lower priority hygiene.

## CONVEYOR LOOP (autonomous)
On each seat finishing: contained → harvest_intake worker (own worktree, full preflight, push+PR) ; dev-1 → it self-pushes. Then → independent reviewer (sonnet, sharp lens) → on APPROVE+green CI → approve as ce-dev-2 (daemon merges) → immediately feed that seat the next NEXT-WAVE slice (probe-not-already-landed + territory-map vs in-flight broker/ce_cli.py hotspots). REQUEST_CHANGES → route fix to author seat if free, else an implementer worker. Keep going until next-wave exhausted or context-limited → write a fresh RESUME_STATE_CE_DEV2_NIGHTARC_*.

## WATCHERS / HOUSEKEEPING
- Board Monitor **bh8s12igt** (queue-churn filtered: fires on PR-set + reviewDecision changes). Seat-READY Monitor (polls dev-3/dev-4 for READY-FOR-HARVEST). Hourly cron **0a34687f** (:47 fleet-check). queue-daemon pid 43010 ALIVE. vLLM brain UP (127.0.0.1:8989). Wall token good to ~07-01.
- Stale review worktrees to clean later: .ce/wt-ce620/621/622/624-review, wt-ce624-fix, wt-agent-model-pins, wt-brain-push.

## DISCIPLINE (hard-won, this session)
ls-remote = ground truth (rev-parse origin/X stale). #620 needed THREE confidentiality passes (ce-ops#/URL/hyphen/skynet) — grep ALL forms. Carrier ce-ops#NNN in .ce/ = ACCEPTED (not a leak; gate doesn't scan .ce/). PROBE main+closed-PRs before every dispatch (lost effort today on #322+#326 already-shipped dupes). Territory-map before dispatch (broker + ce_cli.py are hotspots). Contained-seat brief: DGX dev-4 write host .ce/briefs (bind-mounted); VPS dev-3 deliver via `docker exec -i tee`; dev-1 via ssh ~/ce-briefs + tmux double-Enter. Context-gate seats >40% → /clear (codex /clear works, resets to 100%). Reviewer COMMENT on own-org PR = self-fire refusal, not a defect — gate on the substance if controller≠author.

## DELTA @ ~18:13Z (supersedes the IN-FLIGHT/GATE/SEAT sections above)
MERGED since 1748Z: #623(pins), #622(#349), #621, #624(CEO-B actuator). Board now: #625/#626/#627 open.
- **dev-1** → FIXING #350/#625 (branch ce-350-reviewer-authority-envelope-wiring): restrict payload reviewer_authority_ref to repo-root + scrub internal login `ubuntuaws745-cmyk` from integration test. Re-pushes #625. (Its #350 broker work CONFIRMED good, CI green; the review's 2 "blocking" findings were stale-checkout FALSE-positives — #349 IS on main, carrier IS present.)
- **dev-3** → BRAIN-B (ce-brain-eval-harness, offline recall eval + `ce brain eval`). On READY → harvest.
- **dev-4** → ORCH record-schemas (ce-orchestrator-record-schemas, 4 schemas + orchestrator_records.py + tests). On READY → harvest.
- **#625** (#350 broker leg) → AWAITING dev-1 fix re-push → re-review delta (focus: payload-ref now repo-root-restricted; login scrubbed) → gate. Real findings only: F3 file-read-oracle (fixing), F4 login (fixing); gates intact.
- **#626** (CEO-A advisory CI) APPROVED → daemon merging on green.
- **#627** (BRAIN-A hydration) → review in flight (a215e959); validate 17/17 green, endpoint-independent by design. Gate on APPROVE+green.
- ⚠️ RECURRING: my main working tree `/home/cedev2/creator-engine` is on stale branch `ce-brain-vllm-embedder` — workers that grep it as "main" get FALSE results (hit the #625 review + the earlier slice-map). MITIGATE: tell review/research workers to `git show origin/main:<path>` not read the working tree; consider `git checkout main` in the main checkout.
- NEXT-WAVE still queued (after these land, avoiding ce_cli.py collision with dev-3's BRAIN-B + broker collision with #350): CEO-C/D, #346 (close #347 dup first), remaining ORCH-1..12 + FORGE-1..6 (design docs on main), BRAIN-C/D. Watchers: board bh8s12igt, seat-READY bxa44s2dn, hourly cron 0a34687f.
