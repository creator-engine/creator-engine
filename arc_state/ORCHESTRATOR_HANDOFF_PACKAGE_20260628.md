# 🔁 CE ORCHESTRATOR — RESPONSIBILITY HANDOFF PACKAGE
**Authored:** 2026-06-28 ~12:40Z by CE-DEV-2 (Claude Opus orchestrator) · **Reason:** Claude Max weekly limit near-exhaustion → a **codex seat takes over the orchestrator role** until limits reset. · **Audience:** the incoming codex orchestrator seat (DGX-local codex, or dev-1).

> Read this top-to-bottom ONCE, then keep §3 (live state) + §4 (immediate actions) open as your working board. Everything you need to BE the orchestrator is here or pointed-to. The role is real and load-bearing; drive it, don't narrate it.

---

## 0. ⚠️ AUTH PREREQUISITE — pick the right host (read first)
The full orchestrator role = **drive the fleet + hold the merge gate**. Gating (approve as `ce-dev-2`, merge as `overwatch`, sign releases as `ce-root-v1`) requires credentials that live **only on the DGX host** at `~/.ce-keys/` (user `cedev2`).
- **DGX-local codex seat (RECOMMENDED):** has host access → full controller auth → can dispatch AND gate. Choose this for the complete role.
- **dev-1 (VPS, non-contained):** has its OWN `ce-dev-1` GitHub creds (can author/self-push/file issues) but **NOT** the DGX `~/.ce-keys` → can drive seats + harvest + run preflight, but **cannot approve/merge others' PRs**. If the handoff lands on dev-1, the merge GATE stays with the Operator (or waits for the Claude seat) — surface PRs as "READY-TO-GATE" and let the Operator approve/merge, OR have the Operator transfer the reviewer/overwatch tokens to dev-1.
- **Recommendation to Operator: launch the orchestrator on the DGX** so the gate isn't orphaned.

---

## 1. WHAT THE ROLE IS (the job you're inheriting)
You are the **CE-DEV-2 Orchestrator** — the overarching coordinator of the dev fleet. You do NOT write product code inline. You **drive work through seats and workers** and **hold the merge gate**. The loop:

**intake → territory-map → dispatch (born-foreman fan-out) → progress/stall watch → harvest → independent review → gate/merge → conveyor next lane → checkpoint → surface decisions to Operator.**

Core tenets:
- **NO seat idle** (born-foreman: each seat drives multiple file-disjoint tickets). A non-contained seat parked at READY-TO-PUSH looks idle but is blocked on YOUR confirm — catch it fast. Don't rationalize idle.
- **Never inline build work.** Harvest/push/gate ARE your job (not "inlining"); writing features is NOT.
- **Controller holds the gate.** Author ≠ approver. Route reviews to an INDEPENDENT venue (a seat that didn't author the PR).
- **Token/model discipline** (see §8): the whole reason for this handoff — Claude Max is exhausted; the codex fleet (GPT pool) has ample weekly budget (~72% left). Drive everything through codex.
- **Surface to Operator only 🔒 + genuine decisions.** Stay token-lean.

The role was being canonized in a design doc (see §3 dev-1 lane) — once that lands it becomes the authoritative role contract.

---

## 2. THE FLEET (seats you drive)
| Seat | Host / substrate | Reach | Push? |
|---|---|---|---|
| **dev-1** | Hetzner VPS, NON-contained codex, tmux `ce-dev1-orchestrator:2.0` | `ssh dev1`; pane: `ssh dev1 'tmux capture-pane -p -t ce-dev1-orchestrator:2.0 \| tail -N'`; dispatch: `tmux send-keys ... ; send-keys ... Enter` (DOUBLE-Enter — flaky) | self-push (own `ce-dev-1` creds) |
| **dev-3** | VPS, CONTAINED container `ce-vps-codex` (herdr-PTY) | `ssh dev1 'sudo docker exec -e HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock ce-vps-codex herdr pane read w1:p1'` | NO direct push → controller HARVESTS via git-bundle |
| **dev-4** | DGX-LOCAL container `ce-dgx-codex` (herdr-PTY) — strongest machine | `sudo docker exec -e HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock ce-dgx-codex herdr pane read w1:p1` (no ssh — local) | broker self-push STAGED (see §3); today: controller harvests |

**herdr dispatch to a contained seat:** `... herdr agent send w1:p1 "<msg>"` then `... herdr pane send-keys w1:p1 Enter`. ⚠️ **herdr submit is FLAKY** — the input box clears on submit (looks idle even when it didn't land). VERIFY via a `Working` indicator + context-% growth; re-send `Enter`. If the codex main loop is hard-blocked "Waiting for <agent>", an injected message QUEUES until that returns — send **`Escape`** to interrupt the current tool call and deliver immediately (Escape ≠ C-c; it does NOT kill the session/break bwrap; worktree files persist). **NEVER C-c dev-4's pane.**

**Seat brief delivery (pointer+SHA discipline, NEVER inline-paste):** write the brief to a file, copy it INTO the seat's fs, send a SHORT pointer + sha256.
- dev-3 (contained): `ssh dev1 'sudo docker exec -i ce-vps-codex tee /workspace/creator-engine/.ce/briefs/<name>.md > /dev/null' < localfile` ; verify `sha256sum` inside container.
- dev-4 (DGX-local): can read host `~/creator-engine/.ce/briefs/` directly, or `sudo docker exec -i ce-dgx-codex tee ...`.
- dev-1 (non-contained): `ssh dev1 'cat > ~/creator-engine/.ce/briefs/<name>.md'`.
- **Contained = NO EGRESS:** briefs MUST be self-contained (embed any private ticket content; the seat can't fetch ce-ops or URLs). It CAN read its own in-repo files.

---

## 3. 🔴 CURRENT LIVE STATE (your working board — as of 12:40Z)
**Today: 14 PRs merged. Board: 1 open PR (#615).**

### In-flight lanes
| Lane | Seat/where | State | Next action (YOURS) |
|---|---|---|---|
| **#615 slice-2** (controller-bootstrap-ssot checklist) | PR open, authored ce-dev-3 | ✅ harvested, validate-pr PASS (17 gates), `REVIEW_REQUIRED` | Route to INDEPENDENT review (not dev-3) → on APPROVE verdict, gate+merge |
| **#344 slice-3** (skill-ify ce-dispatch + ce-harvest) | dev-4, claimed branch `ce-344-slice3-skillify` SHA `ce395c9d` | 🛑 **PHANTOM COMMIT — harvest BLOCKED.** A harvest_intake worker checked dev-4's container `/workspace/creator-engine` (1027 reachable + 260 dangling objs + stashes + worktrees) and the host: `ce395c9d` and branch `ce-344-slice3-skillify` **exist NOWHERE.** dev-4 reported a done-state + SHA but never actually created the commit ("seat done ≠ committed"). The work product (skills/ce-dispatch SKILL.md edit, new ce-harvest SKILL.md, playbooks/controller/briefs/harvest.md, test_skill_antidrift_guard.py) is most likely **uncommitted** in a dev-4 session worktree. | **Drive dev-4 LIVE** (you're DGX-local): have it run `git worktree list && git -C <slice3-wt> status -sb && git stash list` to locate its actual slice-3 worktree + uncommitted changes; then make it `git add -A && git commit && echo <SHA>` and VERIFY the SHA resolves before harvesting. If unrecoverable, re-dispatch slice-3 fresh (brief must require `commit && echo SHA`). |
| **BRAIN PR** (Qwen3-8B vLLM embedder) | branch `ce-brain-vllm-embedder` HEAD `91748dc8`, committed+rebased onto #614, **NOT pushed** | 🛑 **STOP-LINE: validate-pr RED.** Root cause: CE check `ce_brain_assertions` returns `ok:false` on this branch → cascades to 36 check-examples-sweep failures (baseline=0, head=36). | FIX `ce_brain_assertions` (the new `vllm-openai`/`openai-endpoint` backend likely needs registration in the check's expected set or an example/assertion update) → re-validate GREEN → push+PR. Host-local (corpus+endpoint on DGX). |
| **Orchestrator design** | dev-1, **PR #616 OPEN** (`docs(design): CE Orchestrator Agent role canon + epic prop`) | ✅ dev-1 scrubbed the confidentiality markers + self-pushed. `REVIEW_REQUIRED`. | Independent review (author=ce-dev-1) + G1-gate. Then surface the epic proposal (`docs/design/ce-orchestrator-agent-epic.md`) for **Operator** ratification before filing to ce-ops. |
| **#34 forge-side design** | dev-3, brief in its fs `/workspace/creator-engine/.ce/briefs/brief-34-forge-design.md` (sha `10b66d5c…`) | ⚠️ **dispatch DID NOT LAND** (herdr Enter flakiness) — dev-3 IDLE. | RE-DISPATCH: `herdr agent send w1:p1 "<pointer+sha>"` + `Enter`; verify `Working`. Design-only lane (doc + epic proposal). |

### dev-4 broker deploy (RATIFIED, STAGED) — execute when dev-4 IDLE (after slice-3 harvest)
Lets dev-4 self-push (converts it fully to contained-with-broker). Prep done (broker.json/env/systemd units created + config-valid in `deploy/dgx-runsc/`). REMAINING (needs **sudo** — Operator may need to run, see §10):
1. Add `--host-uds=open` to `runsc-gvproxy-ptrace` runtime in `/etc/docker/daemon.json` → `sudo systemctl reload docker` (RELOAD does NOT kill containers; restart does — use reload).
2. PEM group-read: `sudo chown cedev4:docker /dev/shm/ce-dev4/ce-forge-dev4.pem && sudo chmod 640` (Operator OK'd).
3. `sudo loginctl enable-linger cedev2` + `systemctl --user enable ce-egress-broker.socket/.service` + create `/run/ce-egress`.
4. Relaunch dev-4 via `ce launch` with `CE_EGRESS_BROKER_SOCKET=/run/ce-egress/dev-4.sock` + smoke-test.
5. FILE vault-migration ticket: `ce-kv/forge/dev-4` (PEM currently tmpfs `/dev/shm` = ephemeral; vault needs Operator vault token). Operator OK'd vault-as-durable-followup.

### Brain serving (priority #2 — LIVE)
vLLM serving **Qwen3-Embedding-8B** at `http://127.0.0.1:8989/v1/embeddings` (OpenAI-compat, dim 4096, GPU/SM121, ~111ms warm). Restart: `/home/cedev2/vllm-qwen3-embed-start.sh`; log `/home/cedev2/vllm-qwen3-embed.log`. ⚠️ reboot-durability NOT yet enabled (needs `sudo loginctl enable-linger cedev2` + enable `~/.config/systemd/user/vllm-qwen3-embed.service` — Operator/sudo, ⏸️ pending). Embedder choice fully grounded in `EMBEDDER_DECISION_THREAD_20260628.md`.

---

## 4. ✅ IMMEDIATE ACTION QUEUE (do these first, in order)
1. **Re-dispatch dev-3 → #34** (brief already in its fs; herdr Enter didn't land). Verify `Working`.
2. **Recover dev-4 slice-3 (PHANTOM COMMIT)** → its claimed SHA `ce395c9d` does NOT exist; drive dev-4 live to locate/commit the real work (or re-dispatch) — §3 row has the exact recovery steps. Do NOT trust the reported SHA.
3. **Review + G1-gate the 3 open PRs** (route each to an INDEPENDENT venue ≠ its author): **#615** slice-2 (author ce-dev-3, validate PASS) · **#616** orchestrator design docs (author ce-dev-1) · plus brain when pushed (#5).
4. **Brain → push + PR** (host-local, DGX): branch `ce-brain-vllm-embedder` @ `986c880d` is READY-TO-PUSH (NOT blocked — earlier "ce_brain_assertions RED" was a concurrency artifact; worker verified the 37 baseline-diff failures are env-only from the 3 repo-root worktrees `mcheck-wt/`,`wt-ce259-harvest/`,`wt-ce293-harvest/`, absent in CI). Either push and let CI gate, or move those 3 worktrees aside for a local GREEN first. Then review + gate. Priority #2 — semantic lift confirmed.
6. Keep **NO seat idle** — as each frees, conveyor the next lane (territory-map first).
7. **Renew OpenBao wall token before 15:42Z** (G4 — ~3h buffer from 12:40Z).

---

## 5. SKILLS / CAPABILITIES NEEDED
- **Git harvest mechanics:** git-bundle from a contained seat (stale origin/main → bundle the single commit `<sha> --not <merge-base>`, NOT `--not origin/main`); host worktree; rebase onto current `origin/main`; conflict-aware territory-mapping.
- **CE preflight:** `TMPDIR=/var/tmp PYTHONPATH=<repo>/validators python3 -m creator_engine_validator.ce_cli validate-pr` (the installed `ce`/`creator-engine-validator` CLIs are STALE — they lack `validate-pr`/`brain`; ALWAYS run the **source module** via `PYTHONPATH=validators`). Add `--allow-dirty` ONLY when the failure is unrelated untracked host clutter (validates committed base..HEAD regardless). Must be GREEN in ONE pass before push.
- **Carriers:** regen via `carrier_gen.write_carriers(base=<merge-base>)` API (DASHED branch slug) — NEVER hand-list carrier filenames; `rm -rf validators/*.egg-info validators/build` first.
- **G5 work-class line:** PR body needs exactly one `- **Declared work class:** <tiny|story|feature|epic>` (the gate reads the EVENT body; a push dismisses approval → re-approve on new head; body-edit-alone won't re-trigger → close+reopen). The line must be in the **pr-manifest carrier** too (a harvest worker had to fix this on #615).
- **gh CLI gate ops** (DGX auth): approve/merge/enqueue.
- **herdr / tmux seat driving** (§2) + flakiness handling.
- **Territory-mapping:** intersect every candidate's paths vs in-flight work (INCLUDING active worktrees) before dispatch — Haiku recon reports the MAIN checkout branch and can MISS active worktrees.
- **Codex sub-thread fan-out:** as a codex orchestrator you spawn your OWN codex sub-agent threads / worktrees for parallel work (the Claude `harvest_intake`/`reviewer`/`implementer` Agent-subagents are the Claude harness's — you replicate their FUNCTION via your own shell + sub-threads).

---

## 6. AUTH & ACCESS (DGX host)
```
overwatch:  set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT
approve as ce-dev-2:  GH_TOKEN=$(cat ~/.ce-keys/ce-dev-2.pat) gh pr review <n> --approve
merge:  gh pr merge <n> --auto --merge   (NOT --squash)
reviewer identity:  GITHUB_REVIEWR_TOKEN (reviewer = ubuntuaws745-cmyk)
release signing:  ce-root-v1 = ~/.ce-keys/ce-root-v1{,.pass,.pub}  (offline, DGX-only, the one non-delegable act)
```
ISSUES repo = **ce-ops** (private). CODE/PRs repo = **creator-engine** (public). Cross-repo `Closes` is a NO-OP (different repos) — code-PR→ce-ops# is mention-only.

---

## 7. SSOT / PLAYBOOKS / RUNBOOKS (durable pointers)
- **📋 AUTHORITATIVE SSOT** = repo `ce-ops : infra/identity-registry.yaml` — canonical topology + identities + credential pointers (OpenBao-ref'd). Registry WINS on conflict.
- **This package's companions (DGX `.ce/state/research/`):** newest `RESUME_STATE_CE_DEV2_DAYARC_*.md` (12:10Z is latest pre-handoff) · `EMBEDDER_DECISION_THREAD_20260628.md` · `ADR_DRAFT_substrate_independent_authority_20260628.md` (sha f47f6ec0).
- **Controller playbooks (in repo):** `playbooks/controller/briefs/dispatch.md` (consult BEFORE spinning a worker) · `playbooks/controller/briefs/harvest.md` (NEW, in dev-4 slice-3, landing now) · `playbooks/controller/`.
- **Skills (in repo `.claude/skills/`):** `ce-dispatch` (compose a governed dispatch brief + record claim) · `ce-harvest` (NEW, slice-3). Worker roles in `.claude/agents/`.
- **Worker roles:** `architect_research` (READ-ONLY, returns brief CONTENT only) · `implementer` (one worktree, no gate authority) · `verification` · `reviewer` (READ-ONLY, returns verdict; has NO Bash/gh → must be handed a LOCAL worktree of the PR).
- **CLAUDE.md** → points to `specs/001-v0-1-governance-substrate/plan.md` (+ research.md/data-model.md/contracts/quickstart.md).
- **Distilled doctrine** (the Claude orchestrator's auto-memory, DGX `~/.claude/projects/-home-cedev2-creator-engine/memory/MEMORY.md`) — a DGX seat can read it; key facts are distilled into §8–§10 here so you don't depend on it.

---

## 8. MODEL / TOKEN ROUTING (the reason for this handoff)
- **Claude Max = EXHAUSTED.** Route ALL substantive work to **codex seats** (dev-1/3/4, GPT pool, OFF Claude quota). The codex fleet has ample weekly budget.
- If you ARE a codex seat: you don't burn Claude quota at all — work freely within the GPT weekly pool (codex effort DEFAULT = high).
- Do NOT spawn Claude subagents (they burn the same exhausted quota). The functions those workers performed (harvest/review/verify/implement) you now perform via codex sub-threads or directly.
- HOST-LOCAL exceptions (work needing the DGX host that no other seat can reach, e.g. brain re-ingest against `localhost:8989` + DGX corpus) are done by whoever is ON the DGX.

---

## 9. PENDING OPERATOR DECISIONS (⏸️ surface these; do NOT self-resolve)
1. **ce-ops#348 — ADR-0013** (Authority is substrate-independent: containment ≠ authority; APPROVE gated by role + ratified run-mode, NOT substrate) — **awaiting ratification.** Keystone; gates ce-ops#349 (decouple APPROVE-refusal from containment in `ce_egress_self_review_broker.py` + `cred_injection_proxy.py`, preserve author≠approver wall) → #350 (wire reviewer-authority-envelope to broker/herdr).
2. **Vault token** for `ce-kv/forge/dev-4` (durable PEM migration; broker deploy follow-up).
3. **sudo** for `loginctl enable-linger cedev2` — needed for vLLM reboot-durability AND the dev-4 broker linger.
4. **Orchestrator epic** (dev-1's `ce-orchestrator-agent-epic.md`) — Operator ratifies before filing to ce-ops.
5. **Onboarding** first test user/contributor (~today) — opportunistic; Operator will direct.
- HALT ⏸️ R-reserved (NEVER auto-do): 0.3.0 re-sign · #592 strangeLoop arming · fleet-wide flips · history-scrub · external release.

---

## 10. DISCIPLINE & GOTCHAS (hard-won — don't relearn the hard way)
1. **FULL validate-pr GREEN one-pass before ANY push** (incl. controller-authored). Two strikes → consult SSOT, never reactive whack-a-mole. Use the source-module invocation (§5). Host `/tmp/.git` trap → keep `TMPDIR=/var/tmp`.
2. **reviewer role has NO Bash/gh** → fetch EVERY PR (even self-pushed) into a LOCAL worktree (`git worktree add --detach .ce/wt-ce<N>-review FETCH_HEAD`) before review; re-verify on the ACTUAL PR head (stale `/var/tmp` worktree caused a #613 false-positive). Clean review worktrees after gating.
3. **public_docs_confidentiality:** `docs/` is PUBLIC product-lens — ZERO ce-ops# refs, no internal seat paths/markers (this just stopped dev-1's design PR).
4. **New top-level `ce` CLI group → 3-file docs coupling** (trips `test_v1_docs_reconciliation`; manifest must name README.md + that test).
5. **Changelog obligation:** every PR needs `.ce/changelog/<slug>.md`.
6. **Path-manifest carrier REQUIRED:** every PR needs `.ce/pr-manifests/<slug>.md` matching base..HEAD (regen via API, §5).
7. **Dismiss ≠ approve;** verify `reviewDecision==APPROVED` on current head before enqueue. A push dismisses approval.
8. **Harvest contained seats via git-bundle** (their origin/main is STALE — reconcile vs authoritative `origin/main` before pushing).
9. **dev-4 container `check-examples` FAIL = environmental** (ce-ops#339 libsodium) — non-blocking; `surfaces_manifest_python_digest` (#272) is warning-only.
10. **Seat "done" ≠ committed** — require a verifiable commit SHA; verify the ref.
11. **Persist a checkpoint** each natural pause (newest `RESUME_STATE_CE_DEV2_DAYARC_*` by mtime; dual-write to CE-DEV-1). Strike completed items.

---

## 11. WATCHERS / HOUSEKEEPING
- **OpenBao wall token: renew before 15:42Z** (G4).
- A PR-board Monitor was running on the Claude side — it dies with this session; the codex seat should poll `gh pr list --repo creator-engine/creator-engine --state open` on its loop.
- Filed today: ce-ops#345 (merged via #614) · #347 (run_mode CLI, deferred) · #348/#349/#350 (authority grounding).
- New memory: `ce-containment-not-authority.md` (the Operator's correction: containment is an isolation SUBSTRATE, not an authority tier; agents do ~100% of code+reviews+APPROVALS autonomously; human ratification moves UP to the policy level).

---
**END OF HANDOFF.** The fleet is healthy and saturated; the work is mid-stream, not blocked. Pick up §4, keep seats non-idle, hold the gate (if DGX-hosted), surface only 🔒+decisions. Good hunting.
