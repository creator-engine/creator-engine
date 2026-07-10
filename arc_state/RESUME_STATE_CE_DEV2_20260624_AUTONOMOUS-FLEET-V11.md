# RESUME STATE — CE-DEV-2 · 2026-06-24 · 🏭 BELT LANDED → PHASE-1 HERDR · V11

**WHERE:** CE-DEV-2 controller, `cedev2` on DGX `spark-b824` (GB10 aarch64), cwd `/home/cedev2/creator-engine`, Opus 4.8 high. **SUPERSEDES V10.** READ THIS + MEMORY.md + `~/HERDR_CONNECT_REFERENCE.md` FIRST. Discipline: **verify-don't-trust** every seat "done"/CI "green"/commit SHA; **inline-only seat dispatch**; **codify don't rediscover**.

## 🟢 HEADLINE: THE BELT IS FULLY LANDED (W2 "activate autonomy" milestone DONE)
- **#412 build belt** (#218 Integrator queue-poll) → MERGED `a8fc557a`.
- **#411 review belt** (#188 review-pickup) → MERGED `1751f231`. dev-1 caught the unscoped-default bug (same class as #412); fixed fail-closed at both layers + test.
- **#410 carrier gate** (#213) → MERGED `385e246c` = **main tip**. `--require-carrier` now ACTIVE fleet-wide (every PR must carry its `.ce/pr-manifests/<slug>.md` + `.ce/changelog/<slug>.md` or CI fails).
- Both peer-review catches (dev-1: #408 secret-retention, #412+#411 unscoped-live-action) = the grader-outside-the-agent working. → generalized into **ce-ops#229** (guard: any live-action CLI building a token-scoped GitHub query MUST declare required scope or fail closed).

## 🔴 STANDING DIRECTIVES (Operator, 2026-06-24)
- Drive batch-ratified arcs autonomously; ping only for genuine ratification. I AM forge triage until fleet self-picks; never idle a dev; parallelize via WORKERS/forks.
- **Peer review:** only **dev-1 (non-contained)** can SUBMIT reviews; contained dev-3/dev-4 can't (no creds). I review dev-authored PRs as ce-dev-2; route ce-dev-2-authored → dev-1.
- **Belt merge AUTHORIZED** — exercised with verify-green + fail-closed-reconfirmed + independent-review. (All 3 belt PRs landed this way.)
- **Merge queue:** strategy set BY the queue (SQUASH); `gh pr merge <n> --auto` ENQUEUES (queue rebases+tests+merges); autoMerge field reads NONE even while queued ("already queued to merge" = it's in).

## 🚀 NEXT ARC = PHASE-1 dev-3 HERDR CANARY (Operator GREENLIT 2026-06-24 — open NOW, belt has landed)
**Goal:** bring dev-3 safely into herdr so contained CE dev-mode is actually functional on attach. Tickets:
- **#217** — herdr fork = contained-PTY substrate (attach surface). dev-4 leading (U1/U2 merged; U3/U4/U-LAUNCHER in flight). Builds the substrate.
- **#227 (AMENDED, Operator-ratified)** — herdr-native dispatch + **END-TO-END INTEGRATION OWNER**. Its Definition of Done = the **6-point acceptance probe** = the canary pass/fail gate: (1) born-contained via U-LAUNCHER (herdr built FROM SOURCE in image — glibc NO-GO if host binary), (2) no `CE_DGX_`-prefixed socket env-leak, (3) dispatch renders in the SAME attach pane (not /tmp log / 2nd invisible codex), (4) operator keystroke COMMITS (Enter submits — b′), (5) denied tool-call BLOCKED per-call + logged (c), (6) brief delivered via verified sha256 path NOT `docker cp` (b″ — the silent no-op that "caused the whole dispatch saga").
- **#219** — codex Ring-1 per-call gate (corrected scope: native managed PreToolUse hook-pack + containment backstop).
- **Containment sequencing (forced order):** workers (dev-3/4) → reviewer (dev-1) → controller (me) LAST. dev-1 stays sole NON-contained reviewer until **#228 cred-injection/OneCLI** ships; controller-containment also gated on #228. **#228 = convergence pin** (dev-1/controller bridge AND Layer-0 JIT-least-priv-tokens = single highest-leverage control of the Excessive-Agency defense).
- **Fold the 3 security quick-wins into this arc:** (1) API-surface classifier in `hook_check.py` (injection via GitHub API dodges the CLI-keyed deny-map = biggest live hole), (2) fail-closed App-grant minimum, (3) Ring-1 **deny raw git/gh/curl from workers + gVisor egress→OneCLI-only** (= same load-bearing work as a SAFE herdr attach).

## 🧠 RESEARCH PERSISTED (this session)
- **Excessive-Agency defense design** → `creator-engine/ce-ops` `designs/DESIGN_excessive_agency_defense_20260624.md` (from workflow `ws657ng74`, 6 lanes). CE ~70% on scaffolding; highest-leverage = Layer-0 JIT tokens (=#228). NVIDIA-pitch NeMo §5. Memory: [[ce-excessive-agency-defense-design]].
- Morning herdr failure reconstruction (6 modes a/a′/b/b′/b″/c/d) → drove the #227 amendment. Coverage: #217 covers a/a′; #227 covers b/b′/b″; #219 covers c; program covers d.

## 🎫 TICKETS (ce-ops) this session: #229 (live-action scope guard, NEW). Prior open: #217/#219/#227(amended)/#228/#206/#208/#115/#128.

## 🖥️ FLEET (re-derive CIDs; verify state before dispatch)
- **dev-1** (VPS, NON-contained tmux codex, `ce-dev1-orchestrator:2.0` pane %64) — sole credentialed reviewer; was on `ce222-egress-honesty` ~52% ctx; reliable review-via-worker.
- **dev-3** (VPS, contained) — the Phase-1 CANARY SUBJECT (not a builder). **dev-4** (DGX, contained) — strongest box, herdr U-stream lead (route #217/#227 build here).
- Tokens: `~/.ce-keys/ce-dev-2.pat` (my reviewer id), `ce-dev-4.pat`, overwatch (`set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`; push/admin). Repo `creator-engine/creator-engine`; ISSUES `creator-engine/ce-ops`.

## 🛠️ PLAYBOOK (carry forward — APPLY EVERY TIME)
- **STALE-REF TRAP:** always `git fetch origin 'refs/heads/X:refs/remotes/origin/X' --force` before reset/rebase/worktree; rebase every branch onto CURRENT origin/main before push. Force-with-lease "stale info" → confirm remote SHA via `gh api .../git/refs/heads/X` then push with explicit `--force-with-lease=branch:SHA`.
- **CARRIER GATES** (now ENFORCED via #410): G5 body needs exactly one `- **Declared work class:** <tiny|story|feature|epic>` BULLET (not `##` heading); G-ii exactly one `.ce/pr-manifests/<branch-slug>.md` (path-set==diff); changelog `.ce/changelog/<slug>.md`. Gen: `/tmp/gen-manifest.py`. Verify: `PYTHONPATH=validators python -m creator_engine_validator verify-path-manifest --base origin/main --manifest-dir .ce/pr-manifests --head-ref <slug>`. Fix-body-without-dismiss: edit body + close/reopen + re-latch.
- **v1⊥v3 BOUNDARY:** decouple don't allowlist; v1 modules must not import `forge.*`; extract forge-coupled→`forge/X.py` (+`V3_RUNTIME`), pure-stdlib→`shared`, route v3 CLI→`v3_cli.py`. Merge-train: each v3 module bumps `_versions V3_RUNTIME` count + matching `test_version_boundary` assertion; second-to-merge collides → resolve in rebase.
- **DGX /tmp ENV ARTIFACT:** run host-side tests under `TMPDIR=/home/cedev2/cetmp`. Raw `ce check` over repo root exits 1 on `examples/malformed/*` negative fixtures — that's BASELINE (identical on main); verify by DIFF vs main, not absolute exit. Host python = `/home/cedev2/creator-engine/.venv/bin/python`. Seats can't run pytest (no venv) → verify host-side.
- **SEAT DISPATCH:** inline-only; brief ends with commit-SHA gate. dev-1 via tmux send-keys to `ce-dev1-orchestrator:2.0` (C-u → send-keys -l → Enter). Cross-host seats can't read DGX files → scp brief or inline. **FORKS** for push/PR/refactor on pushed branches (~300-700k tok); small fixes INLINE in a worktree.
- **WATCHER for re-review:** key off review whose `.commit.oid == fix-head` (a stale CHANGES_REQUESTED on the OLD head false-fires a naive state watcher). jq: `[.reviews[]|select(.commit.oid=="HEAD")]|last as $r|if $r then ... else "" end`.

## 📈 PHASE-1 PROGRESS (live, 2026-06-24 PM)
- **Fresh contained seats launched:** dev-4 `ce-dgx-codex` (DGX, contained gaps:[]), dev-3 `ce-vps-codex` (VPS, gaps:['ns:net:host']). Both via the detached launcher; herdr pane `w1:p1`, socket `/run/creator-engine/herdr/herdr.sock`. Attach: `sudo docker exec -it -e HERDR_SOCKET_PATH=<sock> <name> herdr` (dev-3 via `ssh -t dev3`).
- **Wave 1 BUILT + LANDED via the validated pipeline:** **#417** (#217 launcher hardening: TERM coercion + readiness probe) **MERGED** `27624390` + **PRODUCTION-VALIDATED** (re-launched dev-4 via hardened launcher, NO manual TERM override → TERM=xterm-256color, codex born-clean, readiness OK). **#418** (API-surface classifier in hook_check.py — closes gh-api bypass of Ring-1 deny-map; 118 tests pass) approved+latched, landing behind #417.
- **#219 codex Ring-1 hook** — dev-1 building (`ce219-codex-pretooluse-hook`; ⚠️ dev-1 thin ~24% ctx — watch).
- **PIPELINE VALIDATED (reuse every contained-seat PR):** brief→exec-cat+sha-verify→`codex exec` build→commit-in-box→Model-B push from seat host (`ssh <host> 'cd repo && git push origin <branch>'`)→fetch to my repo→host-side pytest/test (seats have no venv)→`/tmp/gen-manifest.py <slug> <issue> <title>`→commit carrier→verify-path-manifest→push→`gh pr create` (body needs `- **Declared work class:** story`)→ce-dev-2 `--approve`→`gh pr merge --auto`. dev-4 in-container CODEX_HOME=`/home/cedev4/.codex`; dev-3=`/home/ce-dev-3/.codex`; codex exec needs `--dangerously-bypass-approvals-and-sandbox`.
- **NEXT = Wave 2 #227** (herdr-native dispatch, the 6-point DoD, the long pole — herdr internals/keystroke-commit b′, in-pane render b, verified delivery b″). dev-4 freshly relaunched clean on `main`, ready. Bake in the dual-instance-worktree constraint + born-clean (now proven).

## 🎛️ CONTROLLER QUEUE (fresh-me, in order)
1. **OPEN PHASE-1 arc** — dispatch #217 U-LAUNCHER (dev-4) / #227 dispatch-integration (dev-4 or fork) / #219 hook-pack, each gated to the 6-point DoD; dev-3 = canary subject. Verify fleet state first.
2. Sequence **#228 (cred-injection)** design next — the convergence pin for dev-1+controller containment AND Layer-0 security.
3. Belt is live → flip G6-enforce/G8-launch-arm so the fleet self-picks (ends manual intake) when ready.
4. Restock idle seats from backlog (avoid deploy/_versions contention).
