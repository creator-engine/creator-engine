# RESUME STATE — CE-DEV-2 · 2026-06-24 · 🏭 AUTONOMOUS FLEET DRIVE (triage owned) · V8

**WHERE:** CE-DEV-2 controller, `cedev2` on DGX `spark-b824` (GB10 aarch64), cwd `/home/cedev2/creator-engine`, Opus 4.8 high. **SUPERSEDES V7.** READ THIS + MEMORY.md + `~/HERDR_CONNECT_REFERENCE.md` FIRST. Discipline: **verify-don't-trust** every seat "done"; **codify, don't rediscover** ([[ce-controller-verified-bootstrap]] [[ce-codified-actions-not-rediscovery]]).

## 🔴 STANDING DIRECTIVES (Operator, 2026-06-24)
- **Morning arc is BATCH-RATIFIED → drive autonomously, no per-action nods.** Ping only for genuine ratification.
- **I AM the forge triage system** until it's autonomous: keep EVERY controller in parallel lanes (foreman model); never let a dev sit idle; stock the queue from the backlog.
- **Poll every dev periodically** — my job now, not the Operator's to relay.
- **No band-aids** (no "paste this") — drive seats programmatically.

## ⚙️ THE CODIFIED PLAYBOOK (this session's hard-won primitives — in ~/HERDR_CONNECT_REFERENCE.md)
- **Dispatch a task to a CONTAINED seat** = `codex exec` (RELIABLE), NOT herdr TUI keystrokes (unreliable: composer fills, Enter never commits; codex not registered as herdr agent). Pattern: deliver brief via exec-cat → `docker exec -d <CID> bash -lc "cd /workspace/creator-engine && CODEX_HOME=<home> codex exec --dangerously-bypass-approvals-and-sandbox -m gpt-5.5 \"$(cat /tmp/brief.md)\" > /tmp/task.out 2>&1; echo DONE_EXIT=$? >> ..."` then poll DONE_EXIT.
- **Deliver a file to a gVisor seat** = `docker exec -i <CID> sh -c 'cat > /tmp/x' < host` + sha-verify. **NEVER `docker cp`** (silent no-op into runsc sandbox — every cp this session failed invisibly).
- **Dispatch to dev-1 (NON-contained tmux codex)** = tmux send-keys to `ce-dev1-orchestrator:2.0` works fine (C-u C-u → send-keys -l "$MSG" → Enter).
- **Contained codex MUST launch** with `--dangerously-bypass-approvals-and-sandbox` (else inner bwrap nests in gVisor → exec dies).
- **Launch readiness** = check agent ALIVE (process + DONE marker), never grep the screen (`-m gpt-5.5` substring false-passes).
- **Seats branch off DIRTY checkouts** (systemic): both Track B-attempt-1 and Track C committed onto branches carrying unrelated commits. Tell seats to branch off fresh `origin/main`; controller extracts the clean commit if not.
- **Relaunch a contained seat** = scripts on each box: DGX `ssh cedev4@localhost -i ~/.ssh/id_ed25519 bash ~/ce-relaunch-dev4.sh`; VPS `ce-dev-3` runs `~/ce-relaunch-dev3.sh`. Container is `docker run --rm -it` FOREGROUND in a detached tmux (interim until detached-launch PR lands — NEVER kill that tmux or you kill the seat; I did, caused an outage).

## 🖥️ FLEET (CIDs rotate — re-derive via `docker ps --filter ancestor=...`)
- **dev-4 (DGX, contained codex)** CID was `925e1350194b` (img `creator-engine/codex-runsc:0.141.0-aarch64`). CODEX_HOME=/home/cedev4/.codex.
- **dev-3 (VPS, contained codex)** CID was `dbebe1841521` (img `:x86_64`), via `ssh dev3`. CODEX_HOME=/home/ce-dev-3/.codex.
- **dev-1 (VPS, NON-contained tmux codex)** `ssh dev1`, pane `ce-dev1-orchestrator:2.0`. ⚠️ at ~59% context used (3 tasks back-to-back) — watch for needed reset.
- **me (cedev2, DGX)** non-contained controller. Tokens host-side: `~/.ce-keys/ce-dev-2.pat` (login ce-dev-2, MY reviewer identity, independent of dev-1/3/4 authors), `ce-dev-4.pat`, overwatch (merge mechanics).

## 📋 LANES IN FLIGHT (verify each before trusting "done")
1. **#397 / Track A** → ✅ QUEUED TO MERGE (ce-dev-2 approved, CI green, stale ce-dev-3 reviews dismissed). Done.
2. **Track B (OpenBao) — dev-4** → ✅ PUSHED + **PR #404 OPEN** (branch `track-b-openbao-completion`, 5 commits incl `36ec60a`; proof commit absent; NO deploy edits; secrets value-free; 46 tests). Authored as ce-dev-4, **APPROVED by ce-dev-2** (secrets value-free confirmed, bring-up fail-closed, no deploy edits, carriers present). **AUTO-MERGE LATCHED** (`autoMerge:true`) → merges when CI green. ✅ LANE DONE from controller side. **⚠️ HELD: the PRIVILEGED live bao bring-up** (init/unseal, root-token custody, loading REAL secrets from Operator custody, snapshot/restore/audit/revocation drills, migration ratification) — do this ONLY at FRESH context WITH explicit Operator confirmation. High-consequence + real credentials = never at stretched context.
3. **Track C (onboarding) — dev-3** → VERIFIED. Result **FAIL (honest+valuable)**: clean-room install refuses — host lacks `ssh-keygen` (+python3.14, uv). Fix commit `13e3ed4` (install.sh/README/installer.md/test) is CLEAN but on DIRTY branch `track-c-clean-room-onboarding` (carries 2 ce128 commits incl deploy/vps-runsc/README.md). **NEXT: extract 13e3ed4 onto fresh main → push → review.** 🔴 **PILOT-CRITICAL PUNCH-LIST (Friday first-users):** (1) clean pilot images lack ssh-keygen/python3.14/uv → install blocked; (2) signed `docs/llms-install.md` needs same prereq via release-signing; (3) offline/clone path needs py3.14+uv; (4) need one zero→E1→apply→seat quickstart. **Verdict: NOT first-user-ready yet.** → file as ce-ops tickets + queue fixes.
4. **dev-1 — carrier-gates #214+#213** (inject PR work-class/carrier scaffold + CI fail-on-missing-carrier) → 🟢 WORKING. Brief `~/ce-briefs/brief-dev1-carrier-gates.md`.
5. **dev-1 — VPS-TUI-fix** → DONE local, branch `ce128-vps-tui-launch-fix` commit `92cf0f9` (worktree `/home/ce-dev-1/.cache/ce128-vps-tui-launch-fix`). 29 tests pass but **live 60s TUI probe NOT run (no docker in seat)**. **NEXT: I live-verify the probe → push.**
6. **Detached-launch PR** → ready, branch `feat/runsc-detached-launch-mode` commit `17d07cc` (worktree `.claude/worktrees/agent-a58a55ef24c44c56b`). `docker run -d --name` + readiness poll + tmux→legacy. **NEXT: push → review.** Retires the tmux crutch + relaunch fragility.

## 🔀 DEPLOY-SCRIPT MERGE SEQUENCE (conflict prevention — all touch deploy/)
**detached-launch PR (#6) FIRST → then dev-1 VPS-fix (#5) rebased on it → then W5 (Track-B fast-follow).** That's why Track B was told NOT to touch deploy scripts.

## 🎛️ MY CONTROLLER QUEUE (drive in order, verify each, ratify-only pings)
1. Push+review **Track B** (`track-b-openbao-completion`) → merge → live bao bring-up.
2. Extract+push+review **Track C** install-docs fix; **file the pilot punch-list as ce-ops tickets**.
3. Push+review **detached-launch PR**; then dev-1 VPS-fix (live-probe→push, rebased); then W5.
4. Verify dev-1 **carrier-gates** when done; keep **stocking lanes** from backlog (avoid deploy/OpenBao/install/_versions.py contention); **poll devs periodically**.

## 🧰 REVIEW MECHANIC (proven on #397)
Dispatch an Agent worker that reads the PR diff at head, verifies, and submits `gh pr review` **as ce-dev-2** (`GH_TOKEN=$(cat ~/.ce-keys/ce-dev-2.pat)`, verify login==ce-dev-2 first) — independent of authors ce-dev-1/3/4. Dismiss stale reviews via overwatch; enqueue with `gh pr merge <n> --auto` (repo uses a merge QUEUE; "already queued to merge" = success even though autoMergeRequest stays null).

## ✅ DOCTRINE BANKED THIS SESSION (memory)
[[ce-controller-verified-bootstrap]] (boot from verified SSOT, outer-layer-enforced; the WHY behind SSOT+playbooks+OpenBao) · [[ce-codified-actions-not-rediscovery]] · gVisor/dispatch playbook in HERDR_CONNECT_REFERENCE.md.
