# RESUME STATE — CE-DEV-2 · 2026-06-25 DAY-SHIFT · 🏗️ AUTONOMY (BLOCKED) + RELEASE-PAYLOAD · V17

**WHERE:** CE-DEV-2 controller, `cedev2` on DGX `spark-b824`, cwd `/home/cedev2/creator-engine`, Opus 4.8 high. **SUPERSEDES V16.** READ FIRST: this + MEMORY.md + [[ce-controllers-proactive-pickup]] (no seat in reserve) + [[ce-fork-credential-drift-approval-leak]] + [[ce-release-to-traction-doctrine]].

## 🔴 RESUME ACTIONS (in order)
1. **Re-sync:** `tail -40 ~/poll-devs.log` (cron) or `bash ~/poll-devs.sh`; `git -C ~/creator-engine fetch origin`. main tip was `daf65c25` (#443) at checkpoint; manifest worker noted main moved to `bb58f22e` — re-verify.
2. **VERIFY dev-1 dispatch LANDED** — I sent dev-1 the #446-rework pointer via tmux but the pane still showed an empty prompt after (`Explain this codebase` rotating hint, "Worked for"=idle). Check `ssh dev1 'tmux capture-pane -t ce-dev1-orchestrator:2.0 -p | tail -6'`; if still idle, RE-DISPATCH (pointer below).
3. **dev-3 is IDLE** (finished #243, committed locally `ce243-seat-self-review` ahead 1, parked — contained). Dispatch it onto **N5** (manifest below) immediately — no reserve.
4. Drive the rest of the N1–N6 wave (manifest below) + the dev-mode trio + extract parked Leg C.

## 🚨 THE BIG DELTA THIS SESSION — ARM IS BLOCKED, NOT SAFE TODAY
**#446 (B1 / ce-ops#239, OpenBao wiring) reviewed (read-only worker) → VERDICT: NEEDS-WORK.** It fails CLOSED (safe — won't allow forgery) but is **NOT arm-functional**, with a latent fork-leak trap. **DO NOT ARM until reworked + reviewed + merged + verified.** 3 MAJOR findings (dev-1 re-dispatched to fix; brief on VPS `/tmp/brief-446-rework.md` sha256 `02c3331136bf3046`):
- **MAJOR 1 — silent env downgrade:** `v3_cli.py` ~4615-4627 `_approval_wall_primary_then_env_supplier`: configured backend returns falsy WITHOUT raising (prod default materializer = NO-OP) → `if value:` false → `return fallback_env()` → wall arms on **fork-readable env secret** while reporting OpenBao. FIX: configured backend + empty result = misconfig → REFUSE; env fallback ONLY when no backend configured.
- **MAJOR 2 — no openbao backend registered in prod:** `secret_identity.py` `_REGISTRY` empty; nothing registers an `openbao` factory (only tests; `openbao_p3.py` only builds deploy plan). So `--approval-wall-secret-backend openbao` raises → refuse (safe but NON-FUNCTIONAL). FIX: register real `openbao` factory + materializer that ACTUALLY writes secret to target_ref.
- **MAJOR 3 — env: target fork-unsafe:** `v3_cli.py` ~4574, `secret_identity.py` ~962/971: `env:NAME` target writes secret into os.environ → fork-readable. FIX: enforce `file:` 0600 tmpfs; reject/warn `env:` for wall secret.
- minor: partial backend config (backend flag set, SecretRef missing) silently env-fallbacks → make it a hard arg error.
- **ARM AUTH (unchanged from V16):** Operator's "finish autonomy/land it" = authorization to ARM ONCE (a) reworked #446 lands, (b) verify armed+missing-secret → refuse, (c) secret OpenBao-sourced/not-fork-readable. Mint cmd `ce approval-capability mint`. **Report at flip.**
- **dev-1 re-dispatch pointer (if needed):** `Read /tmp/brief-446-rework.md (sha256 02c3331136bf3046) and execute as FOREMAN: rework PR #446 per the 3 arm-safety MAJOR findings (verify-then-fix + named tests). Push to ce239-approval-wall-openbao (self-push), report SHA when green. Do NOT approve/merge.` Mechanic: `ssh dev1 "tmux send-keys -t ce-dev1-orchestrator:2.0 C-u C-u C-u; sleep .4; tmux send-keys -t ce-dev1-orchestrator:2.0 -l '<P>'; sleep .4; tmux send-keys -t ce-dev1-orchestrator:2.0 Enter"`.

## 🛰️ FLEET STATE @ checkpoint
- **dev-1** (VPS, tmux `ce-dev1-orchestrator:2.0`, self-pushes, ~48% ctx) → **#446 rework** (re-dispatched; VERIFY it landed).
- **dev-4** (DGX, container `ce-dgx-codex`, contained, local `sudo docker exec`, ACTIVE 2 procs) → **#242 self-push** (building the capability; commits local → I extract; NOT live until arm).
- **dev-3** (VPS, container `0008529f5a0a`, contained, `ssh dev3`, **IDLE**) → finished #243 (`ce243-seat-self-review` ahead 1, parked). **DISPATCH → N5.**
- Gate daemons healthy (integrator + review-pickup, 1 proc each).
- **Q clarified for Operator:** dev-4 does NOT self-push now — it BUILDS the self-push consumer (#242), commits in-container, I extract+push. Only live after cred-injection transport armed (Leg B → #446 → arm).

## 📦 N1–N6 RELEASE-PAYLOAD CLOSED MANIFEST (grounded by worker @ daf65c25; branch off current main after re-verify)
Ships **v0.3.0 iff N6 clean-room rehearsal green** (fail-closed). DoD D1–D6 ratified on ce-ops#191. Code/PRs=creator-engine; issues=ce-ops.

- **N1** `ce191-n1-install-dep-soft-inventory` — **dev-1** — install dep soft-inventory + re-source profile. partial(#223 did ssh-keygen/uv/CPython/curl-preflight). GAP: git never probed in default `--inventory` path (`v3_cli.py` `_cmd_onboard` ~L2977-3028 returns before dep-probe at L3044); add `_which` WARN rows for git/curl to `--inventory` branch (~before L3025, NO fail); `docs/install.sh` emit re-source `. ~/.profile`/`hash -r` line. Acceptance D1/D2. Buildable now.
- **N2** `ce191-n2-docs-cev3-quickstart` — **controller/dev-1** — sweep `ce `→`cev3 ` in `docs/guide/zero-to-governed-seat-quickstart.md`, `docs/guide/pilot-runbook.md`, `docs/operations/GREENFIELD_FIRST_PROJECT_PROTOCOL.md`; add quickstart card to `docs/index.html` (~L671-701) + curl/git prereq note. **⚠️ `docs/llms-install.md` OFF-LIMITS (signed — release-signing path only); file separate signing task.** Website-versioning: snapshot `site-archive/`+ledger SAME PR ([[ce-website-versioning-policy]]). Buildable now.
- **N3** `ce191-n3-first-value-mythos` — **dev-1** — thin documented `scripts/first-value.sh` wrapping `cev3 scope→ratify→drive --spawn→pr --apply→review --spawn→collect→merge --apply` on `chmod735-dor/mythos` (PAT `~/.ce-keys/mythos-overwatch.pat`, login `ce-overwatch`; NO embedded PAT; `--dry-run`). Build+dry-run now; LIVE-verify after N4.
- **N4** `ce191-n4-app-install-probe` — **controller** (credential-sensitive — shared-App PEM, do NOT hand to worker) — live probe: shared `creator-engine` App (`~/.ce-keys/creator-engine-shared-app.env`, PEM `openbao-ref:ce-kv/forge/github-apps/creator-engine-shared/private-key`) installed on mythos? resolve `installation_id`, ephemeral mint+revoke scoped token (contents:write, pull_requests:write). **D4 long-pole; gates N3-live + N6.** Buildable now.
- **N5** `ce191-n5-fault-injection-failsafe` — **dev-3** (contained, offline) — guard git-invoking entrypoints (`v3_cli.py` L288/L300/L4345/L4518) → clean `InstallRefused` not raw FileNotFoundError; ensure `INSTALL_REFUSED <class>` single-line refusal (no Python traceback to user). Fault-injection test matrix (missing git/curl/tampered-spec). **⚠️ COLLIDES with N1 in v3_cli.py — serialize: land N1 first, N5 rebases.** Buildable now.
- **N6** `ce191-n6-clean-room-rehearsal` — **controller** (the GATE, run LAST) — scaffold buildable now (dev-3 could scaffold offline); LIVE run blocked-on N1–N5 merged + N4. Fresh `ubuntu:24.04`+Claude-Code container → live one-liner install → onboard inventory → plan → apply → first governed merged PR on mythos → one `cev3 update` cycle sig-verified → teardown, ALL green = SHIP; any non-zero = SLIP. New `validators/tests/integration/test_clean_room_rehearsal.py` or `scripts/clean-room-rehearsal.sh` + `docs/operations/CLEAN_ROOM_REHEARSAL.md`.
- **DISPATCH ORDER:** Wave A parallel: N4(ctrl) + N2(ctrl/dev-1) + N1(dev-1) + N5(dev-3). Wave B: N3(dev-1) build now, live after N4. Wave C LAST: N6(ctrl) gate.
- **COLLISIONS:** N1↔N5 (v3_cli.py — serialize N1 first). N2↔N1/N3/N4 (pilot-runbook.md — N2 sweep first, others add sections after). N2↔site-archive (single-author index.html). Each N writes own `.ce/changelog/ce191-n<k>-*.md`. **Out-of-band:** signed `llms-install.md` ce→cev3 fix = separate signing-path ticket (file it).

## 🔀 DEV-MODE TRIO (mine — credentialed-mechanical until injection lands)
- **#443** A5 steer lock — **MERGED** (main daf65c25).
- **#445** (#233 verify-by-reaction) — green but **CONFLICTING → rebase onto current main**, then enqueue.
- **#444** (A4 reach plane) — **CI FAIL** (Validate governance artifacts — `ce herdr` README/as-built-inventory reconciliation, `test_v1_docs_reconciliation`) **+ behind → doc-fix + rebase together.**
- Order **#445 → #444**, rebase+regen-carrier-deterministically+re-green between each. Diffs cached: `~/creator-engine/tmp/pr444.diff`, `pr445.diff`.

## 🅿️ PARKED (extract → carrier → PR, batched)
- **C1** `23d14d5` (dev-4, `ce240-contained-controller-c1`) — contained-controller runsc scaffold (ce-ops#240).
- **C3** `29d8563` (dev-3, `ce241-contained-controller-parity`) — parity harness + 2 design docs (ce-ops#241).
- **#243** (dev-3, `ce243-seat-self-review` ahead 1) — seat opinion-review via injected transport (COMMENT/REQUEST_CHANGES allowed, APPROVE denied pre-mint); 50 impl + 49 verifier tests pass; extract → PR.
- **#242** (dev-4) — when dev-4 reports SHA, extract → PR.

## 🛠️ OPS ESSENTIALS (condensed — see V16 for full)
- **gh:** `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. Tokens `~/.ce-keys/`: overwatch.env (merge+ce-ops issues+push), `ce-dev-2.pat` (MY reviewer id—approvals), `ce-dev-4.pat`, no ce-dev-3.pat, `mythos-overwatch.pat`.
- **Review model (PROVEN):** delegate review-READ to a read-only general-purpose worker (no-mutation mandate, verdict only); I make+submit approval w/ ce-dev-2.pat; verify forge state after. **NEVER credentialed `fork` for gate-adjacent work** ([[ce-fork-credential-drift-approval-leak]]).
- **Contained dispatch:** stage `cat brief | ssh devN sudo docker exec -i <ctr> bash -lc 'cat >/tmp/brief.md'` → `sudo docker exec -e HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock <ctr> herdr pane send-text w1:p1 '<pointer>'` → `herdr pane send-keys w1:p1 Enter` → verify fresh rollout. dev-4 ctr=`ce-dgx-codex` (local); dev-3 ctr=`0008529f5a0a` (via `ssh dev3`, sudo -n docker). dev-1=`tmux send-keys -t ce-dev1-orchestrator:2.0` (C-u×3, -l literal, Enter).
- **Extraction (contained→PR):** `format-patch $(merge-base origin/main <branch>)..<branch>` out of ctr → `git worktree add <scratch> -b <branch> origin/main` (NEVER work in ~/creator-engine main — daemons reset it) → `git am` → carrier DETERMINISTIC (changelog + manifest; sha256 over sorted-unique paths incl 2 carrier files) → push → `gh pr create` (body needs `- **Declared work class:** <class>` ≥ floor). `ce carrier` unavailable (stale venv); gen deterministically.
- **Gate daemons:** `bash ~/.ce/bin/launch-gate-daemons.sh` (BARE). Integrator enqueues approved+green+carrier+mergeable via `gh pr merge --auto`; only `--disable-auto` dequeues (draft does NOT).
- **Monitor seats:** read-only `sudo docker exec ... herdr pane read w1:p1 --source recent-unwrapped --lines N`.
- **Bg forks/timers DIE on /clear**; hourly cron `~/poll-devs.sh` survives.

## 🎫 OPEN TICKETS snapshot (ce-ops)
#239 B1 arm-blocker (#446 NEEDS-WORK, dev-1) · #242 self-push (dev-4) · #243 self-review (dev-3, built) · #240/#241 Leg C (parked) · #237=#444 #238=#443(merged) · #233=#445 · #191 Release epic (DoD ratified → N1–N6) · #198 dogfooding · #228 cred-injection parent · #230 Wave-D canary.
