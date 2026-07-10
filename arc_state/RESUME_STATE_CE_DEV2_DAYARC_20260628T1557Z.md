# RESUME STATE — CE-DEV-2 Orchestrator — 2026-06-28 ~15:57Z — 21 MERGED; authority arc ratified; 3 Claude workers in-flight at /clear

> NEWEST. Open this + MEMORY.md FIRST. Supersedes 1210Z. Companions: EMBEDDER_DECISION_THREAD_20260628.md · ADR_DRAFT_substrate_independent_authority_20260628.md (sha 7fec84fc) · ORCHESTRATOR_HANDOFF_PACKAGE_20260628.md.
> ⭐ ROLE: OVERARCHING ORCHESTRATOR — drive via seats/workers, NEVER inline. Controller holds the gate. Author≠approver. NO seat idle.

## AUTH
overwatch: `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. Approve ce-dev-2: `GH_TOKEN=$(cat ~/.ce-keys/ce-dev-2.pat) gh pr review <n> --approve`. Merge: queue auto-merges approved+green (set `gh pr merge <n> --auto --merge`). ce-root-v1=~/.ce-keys/ce-root-v1{,.pass,.pub}. ISSUES=ce-ops, CODE=creator-engine. Agent-model routing: reviewer/implementer/architect_research=sonnet, verification=haiku (now PINNED in defs), harvest_intake/fleet_recon/ops_triage=sonnet, Opus=controller only.

## ✅ IN-FLIGHT WORKERS — ALL 3 RESOLVED (clean stop-line reached)
1. **#616 re-review** → APPROVE → gated → **MERGED** (action-taxonomy now in main).
2. **#322 — RESOLVED: ALREADY SHIPPED, no-op.** ce-ops#322 was done via PR #585 (`ce322-doc-autogen-schema-reference`, merged 2026-06-27); all files already in main. My 2026-06-28 re-dispatch to dev-4 was STALE (verify-not-already-landed miss). ce-ops#322 now CLOSED; NO PR; dev-4's effort wasted. **dev-4 FREE — its next lane MUST be probed-not-already-landed first (check main + closed PRs before briefing).** LESSON: probe main/closed-PRs before every dispatch.
3. **#620 fix** → DONE + verified: head `02242dfd`, 19 ce-ops URLs abstracted to descriptive text (ADR greps ZERO ce-ops refs), gate HARDENED with `re.compile(r"github\.com/creator-engine/ce-ops")` (L52) + test `test_offenses_reports_planted_private_repo_url`, validate-pr PASS (18 checks). **→ ONLY REMAINING GATE ACTION: independent review + gate #620** (it promotes ADR-0013 → `docs/decisions/ADR-0013-substrate-independent-authority.md` + lands the gate-hardening; closes ce-ops#348). Fetch into a review worktree (`git worktree add --detach .ce/wt-ce620-review FETCH_HEAD` after `git fetch origin ce-348-adr-0013-promote`); author=ce-overwatch so ce-dev-2 approve is independent.

## SEATS (codex, survive /clear)
- **dev-1** (VPS non-contained, tmux ce-dev1-orchestrator:2.0, self-push, double-Enter): **FREE** — finished #616 authority-taxonomy revision (pushed 2a373b24, validate PASS, scrub clean). → **NEXT LANE = #349** (queued, keystone — brief NOT yet written; see Authority Arc below). No-idle: dispatch #349 on resume.
- **dev-3** (contained ce-vps-codex; poll `ssh dev1 'sudo docker exec -e HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock ce-vps-codex herdr pane read w1:p1'`): WORKING **#343** (version-agnostic install-spec tests; branch ce-343-installspec-version-agnostic). → on READY-FOR-HARVEST: harvest→review→gate.
- **dev-4** (contained ce-dgx-codex DGX-local; poll `sudo docker exec -e HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock ce-dgx-codex herdr pane read w1:p1`): **FREE** — #322 done (being harvested, worker #2 above). → NEXT LANE TBD on resume (KNOWN_PENDING burndown #304+injection.md, or a forge/#34-epic slice if ratified). dev-4 container env-RED on validate = known #339 libsodium/Python (non-blocking; harvest re-validates host-side).
- **dev-2 codex controller** (tmux ce-controller:dev2-codex): STOOD DOWN (handoff experiment; auth was re-authed by Operator then I resumed Claude control). Leave idle.

## OPEN PRs (board)
- **#616** orchestrator design (REVISED, head 2a373b24) — re-review in flight → gate on APPROVE.
- **#620** ADR-0013 promotion (being fixed: abstract refs + harden gate) — re-review + gate after fix lands.
- (#322 PR incoming from harvest.)

## 🔑 AUTHORITY ARC (ratified today)
- **ADR-0013 RATIFIED** by Operator (chmod735) 2026-06-28 (ce-ops#348). Decision = D1 action-taxonomy (autonomous-vs-reserved verbs, NOT grant-numbers/substrate; retires cryptic G1-G5/#249-wall-canary) + D2 substrate-independence + D3 APPROVE gated by author≠approver+envelope+run-mode not containment. Draft sha 7fec84fc.
- **#620** promotes it to `docs/decisions/ADR-0013-substrate-independent-authority.md` (in fix-loop).
- **#349** (UNBLOCKED, queued for dev-1) = decouple APPROVE-refusal from containment in `ce_egress_self_review_broker.py` (L170/225 hard-refusal, ALLOWED_EVENTS) + `cred_injection_proxy.py` (`_CONTAINED_REVIEW_EVENTS` L44 excludes APPROVE, L122/374 refusals, ContainedSeatReview docstring L124-128). PRESERVE author≠approver wall (broker L237-244). Gate APPROVE by: author≠approver (always, fail-closed) + reviewer-authority-envelope (mechanic=pr_review/role=reviewer/run-mode-compat) + run-mode policy (solo/team keep autonomous-APPROVE OFF; future strangeLoop permits). Substrate NOT checked. Default-deny preserved (fail closed on missing envelope). BUILD is autonomous; the run-mode ARMING flip is R-reserved. → #350 wires the envelope to broker/herdr after.
- **#616 ↔ ADR-0013 consistent**: #616 proposes the taxonomy, ADR ratifies it.

## ⏳ LOOSE ENDS / TO-DO (on resume)
- **COMMIT the agent-model pins**: `.claude/agents/{reviewer,implementer,architect_research,verification}.md` have uncommitted `model:` additions (sonnet/sonnet/sonnet/haiku) — needs a small governance PR (prevents reviewer/implementer silently inheriting Opus; Operator flagged this). [[ce-model-effort-routing-policy]]
- **KNOWN_PENDING burndown**: `docs/design/controller-bootstrap-injection.md` still has `ce-ops#` leak on main + is allowlisted; scrub + drop from KNOWN_PENDING (pattern #615 used). Also ce-ops#304 (ce-ops#63 in contributing guide).
- **#137 infra-SSOT**: commented proposed `host_services` entry for the DGX vLLM-brain service; the comprehensive org-SSOT (machines+accounts+github) is #137/#269 scope. Memory `ce-dgx-brain-vllm-serving` written.
- **Onboarding** (first user, Arad): opportunistic; sync-arad cron live; #320/#329/#191. Not actively driven.
- **Night-shift arc planning**: Operator wants to plan it. Highest unlock = the ratified ADR converts design→dispatchable slices (orchestrator epic #616, forge epic #34) once those EPICS are ratified. Parity (dev-4 broker, needs sudo). Authority eng (#349→#350).

## BRAIN (priority #2 — DONE end-to-end)
vLLM serving Qwen3-Embedding-8B @ 127.0.0.1:8989 (dim 4096, GPU ~80GB, durable systemd-user+linger). Embedder backend MERGED (#619). Recall index `.ce/state/brain/recall-qwen3-8b.sqlite`; query `ce brain recall "<q>" --embedder vllm-openai --db .ce/state/brain/recall-qwen3-8b.sqlite`. Semantic lift confirmed. /docs (Swagger) + /metrics (Prometheus) live; no built-in dashboard (Grafana optional). SSOT-gap tracked #137.

## DAY-ARC SUMMARY (21 merged)
Brain #619 · forge-side design #617(#34) · skill-ify #618 + bootstrap slices #609/#615(#344) · CEO-mode/AutoReview #610/#592/#613 · dispatch planner #607 · 0.3.0 release+hardening #603/#605/#606/#604/#600/#601/#602 · CI/gov #611/#612/#614. This session (post-handoff-return): gated #615/#617/#618/#619; revised+re-reviewing #616; ratified+promoting ADR-0013 (#620); dispatched #322/#343; documented brain.

## DISCIPLINE (hard-won)
FULL validate-pr GREEN one-pass before push (source module: `PYTHONPATH=validators python -m creator_engine_validator.ce_cli validate-pr --head-ref <branch>`; installed `ce` is stale). `--allow-dirty` only for untracked clutter; clean detached worktree avoids the stray-worktree env-FAIL. **ls-remote is ground truth** (rev-parse origin/X can be stale — caused a false "push didn't land" alarm). Carriers via carrier_gen DASHED slug; G5 work-class line in BODY **and** pr-manifest carrier. Public docs = ZERO internal refs incl `ce-ops/issues/N` URL form (gate now catches both after #620). Reviewer has NO Bash/gh → fetch PR into local worktree; review merge-base diff if branch behind main. Harvest contained via git-bundle BRANCH REF (bare-SHA → empty bundle). Seat "done" ≠ pushed (verify ls-remote). Contained-seat brief writes: dev-4 path owned by uid1003 → write on HOST .ce/briefs (bind-mounted, visible in container); container exec is uid1002 (can't write). herdr/tmux double-Enter, verify Working.

## WATCHERS / HOUSEKEEPING
- PR-board Monitor **bhr9g44fk** persistent. Cron **2963feea** (hourly :47 fleet-check). Host crons live (poll-devs/seat-check/conveyor-tend/belt/sync-arad).
- **OpenBao wall token RENEWED → 72h** (valid ~until 2026-07-01; G4 cleared).
- R-reserved HALT: 0.3.0 re-sign / strangeLoop arming / #349 run-mode ARMING flip / fleet-wide flips / external release.

## 🔄 POST-REBOOT DELTA (DGX rebooted 16:10Z; recovered by ~16:35Z)
- **DGX physical reboot** wiped `/tmp` + `/dev/shm`. Recovery: ✅ vLLM brain auto-restored (systemd-user+linger worked); ✅ **wall/merge-queue daemon RESTARTED** (`nohup bash ~/ce-wall-daemon-launch.sh` — it lacked boot-persistence, the proximate bug); ✅ **dev-4 RELAUNCHED** via `sudo CE_DGX_UID=1002 CE_DGX_GID=1002 CE_DGX_REPO=/home/cedev2/creator-engine bash deploy/dgx-runsc/run-codex-runsc.sh --detach tui` (after `docker rm -f ce-dgx-codex` + clearing the stale `/tmp/...config*.toml` — `docker start` fails post-reboot because /tmp config mount is gone). dev-4 authed + ready.
- ⚠️ **dev-4 PEM gone** (`/dev/shm/ce-dev4` wiped) — only needed for broker self-push (not in use; controller harvests). Re-place if broker deploy resumes.
- **NEW ce-ops#351**: relocate wall/merge-queue daemon DGX→VPS (CE-DEV-1) for reboot resilience (OpenBao already on VPS) — Operator-directed. Also: give it Restart=always wherever it lands.
- **NEW in-flight workers** (post-reboot): #349 (dev-1, keystone APPROVE-decoupling) · #343 (dev-3, install-spec) · **#620-fix #2** (implementer a2e7950d — scrub skynet[2x] + ce-ops-N tags + harden gate with both patterns; force-pushes ce-348-adr-0013-promote). #620 re-review #1 was REQUEST_CHANGES (skynet leak); after a2e7950d lands → re-review + gate #620.
- **dev-4 FREE** → queued lane = confidentiality burndown (#304 contributing-guide ce-ops#63 + `controller-bootstrap-injection.md` ce-ops#244 + drop both from KNOWN_PENDING; verified still pending on main). Brief NOT yet written.

## ON RESUME (after /clear)
1. Read this + MEMORY.md. 2. `gh pr list` — reconcile the 3 in-flight workers (§IN-FLIGHT): #616 verdict→gate, #322 PR→review+gate, #620 fixed→review+gate. 3. Poll 3 seat panes (dev-3 #343 working; dev-1 FREE→dispatch #349; dev-4 FREE→next lane). 4. Commit the agent-model pins (PR). 5. Re-arm: Monitor bhr9g44fk + cron 2963feea persist (verify). 6. Surface to Operator: night-arc planning + epic ratifications (orchestrator/forge) as the next unlock.
