# RESUME STATE — CE-DEV-2 · 2026-06-24 · 🏭 AUTONOMOUS FLEET DRIVE · V9

**WHERE:** CE-DEV-2 controller, `cedev2` on DGX `spark-b824` (GB10 aarch64), cwd `/home/cedev2/creator-engine`, Opus 4.8 high. **SUPERSEDES V8.** READ THIS + MEMORY.md + `~/HERDR_CONNECT_REFERENCE.md` FIRST. Discipline: **verify-don't-trust** every seat "done" + every CI "green"; **inline-only seat dispatch** (no fan-out); **codify, don't rediscover**.

## 🔴 STANDING DIRECTIVES (Operator, 2026-06-24)
- Morning arc BATCH-RATIFIED → drive autonomously; ping only for genuine ratification.
- **I AM the forge triage system** until autonomous: never let a dev idle; restock from backlog after EACH completion (codex exec is ONE-SHOT — no self-pickup until belt-daemon #55/#218 lands).
- Poll devs periodically. No band-aids (drive programmatically).
- **OpenBao live bring-up: Operator GAVE EXPLICIT GO.** Ephemeral rehearsal (init/unseal/snapshot/restore/audit-fail-closed/revocation on a THROWAWAY instance) = autonomous-OK now that #404 is merged. **Real production init/unseal + secret-load = needs Operator AT A KEYBOARD** (generates root/unseal custody material that must land in Operator custody, not controller context). Do NOT mint real key material unattended.

## ✅ DONE THIS SESSION (both merged to main)
- **#405 (ce-ops#223) MERGED** `a409d1a5` — clean-room install fix (Friday blocker): ssh-keygen hard-prereq w/ exact per-distro remediation; python3.14+uv bootstrapped post-trust; zero→governed-seat quickstart. (`docs/llms-install.md` signed-doc prereq update = OPEN FOLLOW-UP on ce-ops#223, needs release-signing path.)
- **#404 (ce-ops#113) MERGED** `ed997ec1` — OpenBao go-live automation (`docs/devops/openbao/bringup-container-openbao.sh` now in main).

## 🔁 IN FLIGHT (seats, inline-only codex exec; watcher `bwe2p7nfn`)
- **dev-4 (DGX, CID 925e1350194b)** → ce-ops#220 ✅ DONE local, branch `ce220-harness-capability-matrix` commit `24fb3ea` (3 files: `validators/creator_engine_validator/harness_matrix.py` + `docs/operations/HARNESS_SUPPORT_CAPABILITY_MATRIX.md` + `validators/tests/unit/test_harness_matrix.py`). ⚠️ **VERIFY BEFORE PUSH:** diff is DELETION-HEAVY (harness_matrix.py ~770 del, net −405 lines) — it REWROTE a pre-existing file, not created one as its report implies. Scrutinize what it deleted; run tests host-side via `.venv`; confirm matrix truths intact. NOT pushed. Brief `~/ce-briefs/brief-dev4-220-matrix.md`.
- **dev-3 (VPS, CID dbebe1841521)** → ce-ops#215 ✅ DONE local, branch `ce215-seat-ceops-readonly` commit `be3fc44` (3 files, +155, all ADDS: `tools/provision-ce-ops-readonly.sh` + `docs/operations/SEAT_CE_OPS_READONLY_CHECKOUT.md` + `.ce/changelog/ce215-seat-ceops-readonly.md`). Clean add, NO contention paths. Its "22 failed" pytest = known in-box env gap (missing yaml/textual/ssh-keygen), outside change surface → confirm host-side via `.venv`. No pr-manifest in diff → G-ii neutral; still needs declared-work-class line in PR body (story). NOT pushed. Brief `~/ce-briefs/brief-dev3-215-ceops-checkout.md`.
- On completion: verify host-side (tests via repo `.venv`), generate path-manifest carrier (see below), push Model-B from seat host, open PR as the seat, review as ce-dev-2, auto-merge.

## ⚠️ CARRIER / CI-GATE PLAYBOOK (learned hard this session — see memory [[ce-g5-work-sizing-gate-pr-body]])
Every PR's "Validate governance artifacts" check has gates that fire in sequence (fix one → next appears). BEFORE opening a PR, satisfy ALL:
1. **G5 work-sizing:** PR body needs exactly one `- **Declared work class:** <tiny|story|feature|epic>` ≥ diff floor. ~180 lines→story/tiny; ~1781 lines→epic. Verify: `PYTHONPATH=validators .venv/bin/python -m creator_engine_validator verify-work-sizing-floor --base origin/main --declared-work-class <c> .`
2. **G-ii path-manifest:** if the diff contains ANY `.ce/pr-manifests/*` file it must be EXACTLY ONE, named `<branch-slug>.md`, path-set == diff. If diff has NO manifest → gate is NEUTRAL (passes). Generator: `/tmp/gen-manifest.py <slug> <issue> <title>` (computes count + `sha256("\n".join(sorted(paths))+"\n")`); two-phase (commit corrected path-set, regen content, amend). Verify: `verify-path-manifest --base origin/main --manifest-dir .ce/pr-manifests --head-ref <slug>`.
3. Fix-without-dismiss for body-only gate fails: edit body + **close/reopen** (gate reads frozen event payload; reopen sends fresh body, preserves head SHA→approval survives). Re-latch auto-merge after (close drops it).
4. **Stale-tracking-ref TRAP:** `git fetch origin <branch>` only updates FETCH_HEAD, NOT `origin/<branch>`. Use `git fetch origin 'refs/heads/X:refs/remotes/origin/X' --force` before reset/rebase, else you branch off an OLD tip and a push would DROP the seat's real commits. Always check carrier-commit parent == real remote tip before push.

## 🎛️ CONTROLLER QUEUE (drive in order, verify each)
1. **OpenBao ephemeral rehearsal** — now unblocked (#404 in main). Run on throwaway instance via `docs/devops/openbao/bringup-container-openbao.sh`. Then **real bring-up = Operator-at-keyboard custody handoff** (GO already granted).
2. **detached-launch PR** (`feat/runsc-detached-launch-mode`, commit `17d07cc`, worktree `.claude/worktrees/agent-a58a55ef24c44c56b`) → push → review. FIRST in deploy-script merge sequence.
3. **dev-1 carrier-gates** (`ce214-pr-open-carrier-scaffold` @142b77e, `ce213-carrier-presence-gate` @40b16c9 — LOCAL on dev-1 host, NOT pushed) → push Model-B + PR + review. **Reset dev-1** (was ~17% context; it self-picked `ce222-egress-honesty`).
4. **dev-1 VPS-TUI-fix** (`ce128-vps-tui-launch-fix` @92cf0f9) → I run live 60s TUI probe (seat couldn't, no docker) → rebase on detached-launch → push.
5. Restock dev-3/dev-4 from backlog after #220/#215 (avoid deploy/OpenBao/install/_versions.py contention). Candidates: #221 containment-probe, #188 belt reviews-pickup, #214 PR-open carrier scaffold (coupled w/ dev-1's work).

## 🧰 MECHANICS
- Tokens host-side: `~/.ce-keys/ce-dev-2.pat` (MY reviewer identity), `ce-dev-4.pat`, overwatch (`~/.ce-keys/overwatch.env`, `GH_TOKEN=$CE_OVERWATCH_PAT`, merge/admin). Repo = `creator-engine/creator-engine`; ISSUES = `creator-engine/ce-ops`.
- Validator tests host-side: `PYTHONPATH=validators /home/cedev2/creator-engine/.venv/bin/python -m pytest ...` (DGX has ssh-keygen, uv, python3.14 — seats DON'T, so seat test-claims are unverifiable in-box; verify host-side).
- Push Model-B: `ssh cedev4@localhost -i ~/.ssh/id_ed25519 'cd ~/ce-workspaces/creator-engine && git push origin <b>'` (dev-4) / `ssh dev3 'cd ~/creator-engine && git push origin <b>'` (dev-3). Or push from local worktree via `https://x-access-token:$CE_OVERWATCH_PAT@github.com/...` with author set to the seat.
- Seat dispatch: deliver brief via `docker exec -i CID sh -c 'cat>/tmp/brief.md'` (NEVER docker cp) + sha-verify → `docker exec -d CID bash -lc 'cd /workspace/creator-engine && CODEX_HOME=<home> codex exec --dangerously-bypass-approvals-and-sandbox -m gpt-5.5 "$(cat /tmp/brief.md)" >/tmp/task.out 2>&1; echo DONE_EXIT=$? >>...'`. **INLINE-ONLY** (the foreman AGENTS.md fan-out STALLS under headless exec — sub-agent hangs zero-output). CHOME4=/home/cedev4/.codex, CHOME3=/home/ce-dev-3/.codex.
