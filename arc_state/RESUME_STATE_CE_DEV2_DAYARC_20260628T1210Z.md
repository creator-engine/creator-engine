# RESUME STATE — CE-DEV-2 Orchestrator — 2026-06-28 ~12:10Z — 14 MERGED; brain SERVING; orchestrator-design + authority-grounding in flight

> NEWEST. Open this + MEMORY.md FIRST. Supersedes 1020Z. Companion: EMBEDDER_DECISION_THREAD_20260628.md.
> ⭐ ROLE: OVERARCHING ORCHESTRATOR — drive via seats/workers, NEVER inline. Each seat = born-foreman (multiple file-disjoint tickets; controller ensures parallel-safety via territory-map). NO seat idle (don't rationalize idle — a non-contained seat parked at READY-TO-PUSH looks idle but is blocked on controller confirm).

## 🔻 TOKEN DIRECTIVE (Operator, 12:0xZ — EXTREME Claude-token efficiency)
EXTREMELY low on Claude Max tokens. Route ALL substantive work to **CODEX SEATS** (dev-1/3/4 — GPT pool, OFF Claude quota). Only SIMPLE tasks or HOST-LOCAL-ONLY tasks (can't reach a codex seat) → Sonnet/Haiku subagents (still Claude quota — minimize). Opus main-loop = minimal, short turns. Claude subagents (architect_research/implementer/reviewer/harvest_intake) DO burn the same Claude Max quota → prefer codex seats. Host-local exception = work needing the DGX host (e.g. brain re-ingest needs localhost:8989 + DGX corpus; no codex seat can reach it).

## AUTH
overwatch: `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. Approve ce-dev-2: `GH_TOKEN=$(cat ~/.ce-keys/ce-dev-2.pat) gh pr review <n> --approve`. Merge: `gh pr merge <n> --auto`. ce-root-v1=~/.ce-keys/ce-root-v1{,.pass,.pub}.

## ✅ MERGED TODAY (14): #604/#605/#606/#592/#603/#607/#608/#609(ce244 relaunch-gate)/#610(CEO-mode classifier)/#611(agent-AGENTS.md)/#612(ce342 CI-retrigger)/#613(ce341 AutoReview run_mode)/#614(ce345 path-manifest D-status + orphan cleanup — merging)

## 🎯 OPERATOR PRIORITIES (engine-first; onboarding ~later today, opportunistic)
1. Forge/fleet automation (Steinberger): #291✅ #341✅ #295✅ #342✅ #345✅ done. Next big = #34 forge-side (design-first).
2. **CE ORCHESTRATOR AGENT** (NEW priority) — formalize/canonize the ad-hoc orchestrator role. IN FLIGHT on dev-1 (codex; design-only). brief `.ce/briefs/brief-ce-orchestrator-agent-design.md`. → produces docs/design/ce-orchestrator-agent.md + ce-ops epic proposal. ON report: review + file the epic.
3. Company brain (UTMOST): SERVING (see below). Re-ingest in flight.
4. Contained-parity → convert dev-1/dev-4 to contained: parity = GO-WITH-CONDITIONS (assessment done). dev-4 switch RATIFIED (broker deploy staged — below).
5. Relaunch dev-2 governed: GREEN-LIT (ce244 merged); resume from this checkpoint.
6. Authority grounding (Operator directive): containment≠authority; agents do ~100% reviews+APPROVALS autonomously; APPROVE gated by role+run-mode NOT substrate → ADR-0013 + tickets (below). [[ce-containment-not-authority]]

## 🧠 BRAIN STATE (priority #3 — big progress)
- Embedder DECIDED = **Qwen3-Embedding-8B** (Apache-2.0). Eval: Qwen3-8B beat KaLM-12B(ceiling)/Harrier/BGE-M3; NVIDIA Llama-Embed-Nemotron-8B + Jina-v3 + NV-Embed-v2 DISQUALIFIED (non-commercial). Full eval in EMBEDDER_DECISION_THREAD_20260628.md.
- **vLLM SERVING Qwen3-8B LIVE** at `http://127.0.0.1:8989/v1/embeddings` (OpenAI-compat, dim 4096, GPU/SM121 not eager, ~111ms warm). TRUSTED path (official vllm 0.23.0 aarch64 wheel + official pytorch cu129 — NO untrusted images). Restart: `/home/cedev2/vllm-qwen3-embed-start.sh`; log `/home/cedev2/vllm-qwen3-embed.log`. ⚠️ reboot-durability needs `sudo loginctl enable-linger cedev2` + enable `~/.config/systemd/user/vllm-qwen3-embed.service` (Operator/sudo).
- BRAIN RE-INGEST IN FLIGHT: implementer a11e0fa (Claude, HOST-LOCAL — justified exception). Builds a vLLM-OpenAI-endpoint embedder adapter (Slice A only had deterministic/sentence-transformers) + re-ingests conservative corpus (memory/*.md + .ce/state/research/*.md excl TRANSCRIPT) + verifies SEMANTIC lift vs keyword baseline. Branch ce-brain-vllm-embedder, preflight GREEN → READY-TO-PUSH. → ON report: gate the adapter PR (it's product code) + note semantic-lift result. Slice A keyword recall still LIVE at .ce/state/brain/recall.sqlite.
- Posture RATIFIED = product feature (F5 MCP surface downstream).

## SEATS (12:10Z)
- **dev-1** (VPS non-contained, tmux ce-dev1-orchestrator:2.0, self-push, NO auto-notify→poll, double-Enter): WORKING **CE Orchestrator Agent design** (codex). → on READY: review design + file epic.
- **dev-3** (contained ce-vps-codex; poll `ssh dev1 'sudo docker exec -e HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock ce-vps-codex herdr pane read w1:p1'`): WORKING **#344-slice2** (controller-bootstrap-ssot checklist content; branch ce-344-slice2-checklist; story). → READY-FOR-HARVEST: harvest_intake(git-bundle)→reviewer(needs LOCAL worktree!)→gate.
- **dev-4** (contained ce-dgx-codex DGX-local; poll `sudo docker exec -e HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock ce-dgx-codex herdr pane read w1:p1`): WORKING **#344-slice3** (skill-ify ce-dispatch+ce-harvest under .claude/skills/; branch ce-344-slice3-skillify; story) — was fighting Python-dep/carrier-gen friction, watch. → READY-FOR-HARVEST: harvest_intake→reviewer→gate.

## 🔴 AUTHORITY GROUNDING (Operator-directed; ADR + 3 tickets filed)
- **ADR-0013 DRAFT** at `.ce/state/research/ADR_DRAFT_substrate_independent_authority_20260628.md` (sha f47f6ec0) → **ce-ops#348 AWAITING OPERATOR RATIFICATION** ⏸️. On ratify → promote to docs/decisions/ADR-0013-*.md via governance PR (verify no overlap w/ private ce-ops ADR-0003/0004 first).
- **ce-ops#349** (engineering): decouple APPROVE-refusal from containment in `ce_egress_self_review_broker.py` (L59/170/225) + `cred_injection_proxy.py` (L44/122/374) — gate APPROVE by run-mode + reviewer-authority-envelope; PRESERVE author≠approver wall (broker L237-244). GATED on #348 ratification → then dispatch to a seat.
- **ce-ops#350**: G2.007.3 — wire reviewer-authority-envelope to broker/herdr path. Depends on #349.

## ⚙️ dev-4 SWITCH (RATIFIED) — broker deploy STAGED
Prep done: broker.json/env/units created + config-valid (canonical deploy/dgx-runsc/). REMAINING when dev-4 IDLE (after slice3 harvest):
1. `sudo systemctl reload docker` after adding `--host-uds=open` to runsc-gvproxy-ptrace in /etc/docker/daemon.json (RELOAD does NOT kill containers; restart does — use reload).
2. PEM group-read: `sudo chown cedev4:docker /dev/shm/ce-dev4/ce-forge-dev4.pem && sudo chmod 640` (Operator OK'd group-read).
3. `sudo loginctl enable-linger cedev2` + `systemctl --user enable ce-egress-broker.socket/.service` + create /run/ce-egress.
4. Relaunch dev-4 via ce launch w/ CE_EGRESS_BROKER_SOCKET=/run/ce-egress/dev-4.sock + smoke-test.
5. FILE vault-migration ticket: ce-kv/forge/dev-4 (PEM currently tmpfs /dev/shm/ce-dev4/ — ephemeral; vault needs Operator vault token; wall token lacks ce-kv read).

## REVIEW CAPABILITY (answered)
Contained seats CAN post COMMENT/REQUEST_CHANGES via broker (ce-ops#243 shipped). APPROVE currently controller-only (3 hard-refusals coupling to containment) — WRONG per ADR-0013; being corrected via #349. Today: reviewer worker returns verdict → controller submits APPROVE.

## DISCIPLINE (hard-won)
1. FULL `ce validate-pr` GREEN one-pass before push; carriers via `carrier_gen.write_carriers(base=)` DASHED branch slug — DON'T hand-list carrier filenames in briefs (ce-ops#345 codifies; caused #341/#342 stop-lines). G5 body line. New `ce` group = 3-file coupling. baseline-diff = regression authority. TMPDIR=/var/tmp.
2. ⚠️ **reviewer role has NO Bash/gh** → MUST fetch EVERY PR (even self-pushed) into a LOCAL worktree (`git worktree add --detach .ce/wt-ce<N>-review FETCH_HEAD`) before dispatching reviewer; point reviewer at the worktree path. (Caused a wasted #614 review cycle.) Re-verify on ACTUAL PR head, not stale /var/tmp.
3. Seat injections = file+pointer+SHA; contained/VPS briefs COPIED INTO seat fs (dev-3/VPS: `ssh dev1 'sudo docker exec -i ce-vps-codex tee <path>'`; dev-1/VPS: `ssh dev1 'cat > ~/creator-engine/.ce/briefs/...'`; dev-4/DGX-local CAN read host .ce/briefs). herdr submit flaky — verify `Working` + context-growth; re-send Enter if not landed. tmux double/triple-Enter.
4. Every subagent sets model (Haiku/Sonnet/Opus-controller-only); ZERO forks/Opus-subagents. PREFER CODEX SEATS (token directive).
5. Harvest contained via git-bundle→host worktree→validate-pr→push. dev-1 self-pushes (confirm-to-self-push — catch READY-TO-PUSH promptly). Controller holds gate; independent reviewer venue. Clean review worktrees after gating.
6. dev-4 container check-examples FAIL = environmental (ce-ops#339 libsodium) non-blocking; WARN surfaces_manifest_python_digest (#272) warning-only.

## WATCHERS / HOUSEKEEPING
- PR-board Monitor **boamzqs8y** persistent. /loop heartbeat self-paced (last ~12:24Z).
- **OpenBao wall token renew before 15:42Z** (G4, ~3.5h buffer).
- Filed today: ce-ops#345(done), #347(run_mode CLI deferred to strangeLoop arming), #348/#349/#350(authority).
- New memory: ce-containment-not-authority.md (+ MEMORY.md indexed).
- ⏸️ AWAITING-OPERATOR: #348 ADR-0013 ratification; vault token for ce-kv/forge/dev-4; sudo for linger (vLLM durability).
- HALT⏸️ R-reserved: 0.3.0 sign / #592 arming / strangeLoop arming / fleet-wide flips.

## ON RESUME (after /clear)
1. Read this + MEMORY.md + EMBEDDER_DECISION_THREAD. 2. Poll PR board + 3 seat panes (catch READY states). 3. In-flight Claude worker at /clear: brain re-ingest a11e0fa (host-local; if it reported, gate the ce-brain-vllm-embedder PR). 4. Codex seats survive /clear (dev-1 orchestrator, dev-3 s2, dev-4 s3) — poll for READY → harvest/gate. 5. Surface to Operator: orchestrator design, brain semantic-lift, #348 ratification reminder. 6. Re-arm /loop heartbeat.
