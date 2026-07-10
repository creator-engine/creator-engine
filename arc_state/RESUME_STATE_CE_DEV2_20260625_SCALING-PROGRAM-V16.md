# RESUME STATE — CE-DEV-2 · 2026-06-25 DAY-SHIFT · 🏗️ AUTONOMY-SPRINT + RELEASE-PAYLOAD · V16

**WHERE:** CE-DEV-2 controller, `cedev2` on DGX `spark-b824` (GB10 aarch64), cwd `/home/cedev2/creator-engine`, Opus 4.8 high. **SUPERSEDES V15** (V15 = night-shift fleet-maintenance; read it for deep ops detail). **READ FIRST:** this + MEMORY.md + [[ce-release-to-traction-doctrine]] + [[ce-parallelize-everything-scale-the-gate]] + [[ce-controllers-proactive-pickup]] (no seat in reserve) + [[ce-fork-credential-drift-approval-leak]].

## 🔴 RESUME ACTIONS (do these first, in order)
1. **Re-sync live state:** `bash ~/poll-devs.sh`; `git -C ~/creator-engine fetch origin`; check the 3 sprint lanes + the dev-mode trio PRs (below). main tip was `3083d6f6` (#440).
2. **The 60-min autonomy-sprint timer is DEAD** (it was a bg `sleep 3600`, dies on /clear). Its bell condition was "regardless of autonomy landing, fan out N1–N6." So on resume: assess autonomy progress AND proceed to drive both thrusts (don't wait for a timer).
3. **Drive B1 (#239) → ARM the wall** (see Governance Arc). 4. **Sequence the dev-mode trio** (#443→#445→#444). 5. **Extract parked Leg C** (C1/C3). 6. **Fan out N1–N6** (the release payload). Keep ALL seats saturated.

### ⚡ DELTA verified at save (2026-06-25, just before clear) — newer than body below:
- **main tip is now `daf65c25`** — **#443 (A5 steer lock) MERGED.** Body says `3083d6f6`/#443-approved; this supersedes.
- **dev-1 already PUSHED B1 → PR #446** (`ce239-approval-wall-openbao`, REVIEW_REQUIRED). **THE arm-critical path: review #446 (read-only worker) → merge → verify armed-wall fail-closes → ARM the wall.**
- **Dev-mode trio re-sequence:** #443 done; now **#445 + #444 both need rebase onto `daf65c25`** (they share herdr_session.py with the merged #443). #444 ALSO needs the `ce herdr` README/inventory doc-fix (its CI was failing). Order: #445 then #444.
- dev-4 (#242 self-push) + dev-3 (#243 self-review) still on their sprint lanes (contained → will commit + report SHA).

## 🎯 THE DAY-SHIFT ARC (Operator-set 2026-06-25 AM) — parallel two-thrust on the scaled fleet
- **Thrust A — FINISH AUTONOMY (remove the controller from the loop):** B1 (#239) → arm the credential-wall → contained-seat self-push (#242) + self-review (#243) via injected creds → Leg C (contained controller). This kills the controller-in-the-loop bottleneck (I currently hand-extract + push + approve every seat PR).
- **Thrust B — LAND THE PAYLOAD (overdue):** execute the RATIFIED release DoD N1–N6 → re-run the N6 clean-room rehearsal as the ship/slip gate → **onboard Arad TODAY**. Install+onboard is the business goal (release-to-traction); it slipped from pre-dawn because the night went to scaling-infra + the morning to the authority-leak/governance hardening.
- Operator (this turn): "prioritize finishing the autonomy; arm a 60-min timer; concentrate resources to land it in 60 min; then REGARDLESS also fan out N1–N6 as a SHA-pinned closed manifest." → all 3 seats currently on Thrust A; N1–N6 fans out next.

## 🛰️ FLEET — IN-FLIGHT LANES (seats are separate processes, survive the clear)
- **dev-1** (VPS, tmux `ce-dev1-orchestrator:2.0`, SELF-PUSHES, ~57% ctx) → **B1 / ce-ops#239** — wire the approval-wall daemon to OpenBao/SecretIdentityBackend (env fallback). Branch likely `ce239-approval-wall-openbao`. **THE ARM-BLOCKER.**
- **dev-4** (DGX, container `ce-dgx-codex`, contained, local `sudo docker exec`) → **#242 seat self-push** (extraction-killer). Branch `ce242-seat-self-push`. Contained → commit + report SHA, controller extracts.
- **dev-3** (VPS, container `0008529f5a0a`, contained, via `ssh dev3`) → **#243 seat self-review** (reviews/opinions only; seats NEVER hold the wall secret). Branch `ce243-seat-self-review`.
- All 3 are FOREMEN (decompose → delegate to ≤5 workers, never inline; codex fan-out driven by ~/.codex/AGENTS.md FOREMAN directive — no `[agents]` config needed). Verify fan-out after dispatch; verify a fresh rollout = turn started.

## 🅿️ PARKED (extract → carrier → PR when you return to Leg C, batched with N1–N6)
- **C1** `23d14d5` (dev-4, branch `ce240-contained-controller-c1`) — contained-controller runsc scaffold (ce-ops#240).
- **C3** `29d8563` (dev-3, branch `ce241-contained-controller-parity`) — parity acceptance harness + 2 design docs (ce-ops#241).
- Both built + verified in-seat; just need extract→PR. (C2 = real cred-injection, blocks on B1/#239.)

## 🔐 GOVERNANCE ARC — Leg B LANDED (dormant); arming is the last step
- **MERGED:** #437 cred-injection proxy · #441 dequeue+settle · **#440 credential-wall MERGED DORMANT** (enforce-when-armed: dormant when no secret configured → behaves like today; fail-closed once armed; persistent armed-flag prevents silent downgrade).
- **B1 / ce-ops#239 = HARD prerequisite to ARMING.** #440's daemon path wires only an env-var secret supplier, not OpenBao. The wall must NOT be armed in production until #239 lands and the daemon sources its secret from OpenBao (else a fork could read a fork-readable secret + forge). Until then the wall stays DORMANT (safe).
- **ARM AUTHORIZATION:** Operator's "finish the autonomy / land it" = authorization to ARM once (a) #239 lands, (b) you verify the armed wall fail-closes (armed+missing-secret → refuse; invalid marker → refuse), (c) the secret is OpenBao-sourced / not fork-readable. Arm with a clear report at the moment you flip it. Mint command: `ce approval-capability mint` (added in #440).

## 🔀 DEV-MODE TRIO PRs — SEQUENCE SERIALLY (all share herdr_session.py → they conflict)
- **#443** (A5 steer lock, ce-ops#238) — **APPROVED + green** → first to merge.
- **#445** (#233 verify-by-reaction hardening, ce-ops#233) — APPROVE-READY (read-only-worker reviewed); **needs rebase after #443**.
- **#444** (A4 reach plane, ce-ops#237) — **CI FAILED** (added `ce herdr` cmd group without README + as-built-inventory reconciliation → fix `test_v1_docs_reconciliation`) **AND** needs rebase after #443. Do the doc-fix + rebase together.
- Order: **#443 → #445 → #444**, rebase + regen-manifest + re-green between each. (#446/#447 etc. will be the rebased re-pushes if needed.)
- Review model PROVEN this session: delegate the review-READ to a **read-only worker** (general-purpose, explicit no-mutation mandate, returns verdict only); I make + submit the approval; I verify forge state after (no slipped approval). NEVER use credential-inheriting `fork` subagents for gate-adjacent work (authority-leak root).

## 📦 RELEASE DoD — RATIFIED on ce-ops#191 (the install+onboard payload, → v0.3.0 on green)
- **D1–D6** (fail-closed, probe-verified, ship-iff-green): D1 clean install zero-undocumented-steps · D2 first-value end-to-end on installed ce/cev3 · D3 quickstart unaided · D4 auth + shared-App install · D5 unhappy-paths fail-closed · D6 contributor onboarding.
- **LOCKED ANSWERS (4):** (1) Arad installs on fresh **Ubuntu 24.04 + Claude Code authed**, no other deps assumed (curl/git/uv/python must self-remediate or be documented). (2) Modality: **team-mode brownfield on `chmod735-dor/mythos`** (we own it; Arad co-owner/Admin; CE access `~/.ce-keys/mythos-overwatch.pat`, login `ce-overwatch`); install via one-liner OR Agent-pointed (signed playbook). (3) First value: **author→commit→push→PR→merge on mythos**. (4) Contributor: from waitlist AFTER Arad succeeds.
- **`ce` vs `cev3`: RATIFIED** — doc-fix to point users at `cev3` for the v3 governed flow; unify command surface (ce-ops#198) post-release.
- **N1–N6 wave (pre-drawn):** N1 install git/curl remediation + soft-fail inventory + re-source (#223 partial done) · N2 docs ce→cev3 + curl/git prereq + quickstart homepage link · N3 first-value script (author→merge on mythos) · N4 live auth + App-install probe · N5 fault-injection fail-safe · **N6 clean-room rehearsal = the ship/slip GATE**. Ship IFF N6 green. Install rehearsal already ran: machinery solid (#223 works), blockers are mostly doc-level (ce↔cev3, quickstart, fail-safe partial); D4/D6 unprobed.

## 📈 SCALING ROADMAP STATUS (the 12h program, mostly DONE)
- **Phase 0 (gate runs itself): DONE + PROVEN** — Integrator daemon + review-pickup daemon live; 7 night merges + today's, zero-touch. Components all scaled: merge-gate ✅, grader (CI) ✅, work-isolation (#442) ✅, observability (`ce seats ls`/`ce fleet status`) ✅, Search-API headroom ✅.
- **Concurrency:** default **tier-6** + foreman fan-out active (no `[agents]` block; codex fans out from AGENTS.md directive). Never bump >8; only when assessed.
- **QUOTA UNBLOCKED:** Operator added a **2nd codex subscription** (was the binding constraint).
- **The weak link MOVED to: the controller-in-the-loop** (I extract+push+approve because contained seats are zero-cred). Thrust A closes it. Bumping workers before that just relocates the jam.

## 🚨 INCIDENT + LESSONS (this session)
- **Authority-leak RECURRED (2nd time):** drifted `fork` subagents approved #437/#438/#439 as ce-dev-2 using my god-credential; #437/#438 auto-merged before I drafted them (draft does NOT dequeue an in-flight merge — that's why #441 exists). Contained → dismissed approvals, drafted, killed forks. **RULE (persisted [[ce-fork-credential-drift-approval-leak]]):** no credentialed forks for gate-adjacent work; review-reads via read-only workers; verify forge state after.
- **Post-hoc:** #437/#438 kept (sound on merit), post-hoc reviews posted, #439 re-landed with a legit inline approval.
- **Stale-read caution:** I nearly accused a worker of fabricating a review — I'd read a STALE local checkout. Always verify against the current SHA (`git show <sha>:path` / fetch first), not the working tree (gate daemons reset it to origin/main).
- **venv staleness:** installed site-packages is stale (no `ce carrier`); but **gate daemons run SOURCE via `PYTHONPATH=validators`** (gate integrity OK). `ce carrier` unavailable → generate carriers DETERMINISTICALLY (changelog + manifest; sha256 over sorted-unique paths incl the 2 carrier files; verify base..HEAD == manifest set).
- **No seat in reserve** (Operator correction): an idle born-foreman controller is an immediate dispatch obligation; never gate a seat's next lane on a future maybe. [[ce-controllers-proactive-pickup]] updated.

## 🛠️ OPS ESSENTIALS
- **Tokens** (`~/.ce-keys/`): `overwatch.env`→`CE_OVERWATCH_PAT` (merge mechanics + ce-ops issues + push when no per-dev pat); `ce-dev-2.pat` (MY reviewer id — approvals); `ce-dev-4.pat`; NO ce-dev-3.pat (use overwatch); `mythos-overwatch.pat` (Arad's repo). **ISSUES = creator-engine/ce-ops; CODE/PRs = creator-engine/creator-engine.**
- **Dispatch (contained seat):** stage `cat brief | (ssh devN) sudo docker exec -i <ctr> bash -lc 'cat >/tmp/brief.md'` → `sudo docker exec -e HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock <ctr> herdr pane send-text w1:p1 '<pointer>'` → `herdr pane send-keys w1:p1 Enter` → verify pane + fresh rollout. dev-4 ctr=`ce-dgx-codex` (local); dev-3 ctr=`0008529f5a0a` (via `ssh dev3`). dev-1 = `tmux send-keys -t ce-dev1-orchestrator:2.0` (C-u, then -l literal, then Enter).
- **Extraction flow (contained seat → PR):** `format-patch $(merge-base origin/main <branch>)..<branch>` out of container → `git worktree add <scratch> -b <branch> origin/main` (NEVER work in ~/creator-engine main — daemons reset it) → `git am` → generate carrier deterministically → push (ce-dev-4.pat or overwatch) → `gh pr create` (body needs `- **Declared work class:** <class>` ≥ floor). Clean up worktree after.
- **Gate daemons:** `bash ~/.ce/bin/launch-gate-daemons.sh` (run BARE — pkill-pattern footgun; resets tree to origin/main + relaunches both from SOURCE via PYTHONPATH=validators). Logs `~/.ce/logs/{integrator,review}-daemon.log`. Integrator enqueues approved+green+carrier+mergeable via `gh pr merge --auto` (GitHub native queue) — once enqueued, only `gh pr merge --disable-auto` dequeues (draft does NOT).
- **Monitor seats live:** read-only poll `sudo docker exec -e HERDR_SOCKET_PATH=… <ctr> herdr pane read w1:p1 --source recent-unwrapped --lines N` (no `--follow`; no host-root-free attach yet — that's A4/#237).
- **Background forks/pollers/timers DIE on /clear**; the hourly host cron `~/poll-devs.sh` survives. Re-establish anything needed on resume.

## 🎫 OPEN TICKETS (ce-ops) snapshot
#236 dev-mode DoD (A1✅A2✅A3✅ A4=#444 A5=#443 / B=landed-dormant / C=#240+#241 built-parked) · #237/#238 (in PRs #444/#443) · **#239 B1 arm-blocker** (dev-1) · #240/#241 Leg C (parked) · **#242 self-push (dev-4)** · **#243 self-review (dev-3)** · #233 (PR #445) · #232 logging (merged #439) · #191 Release epic (DoD ratified) · #198 dogfooding · #230 Wave-D canary (parked) · #228 cred-injection parent · #219 Ring-1 · #190 ce-update (deferred).

**main tip:** `3083d6f6` (#440). **Open PRs:** #443 (approved), #444 (CI-fail, rebase), #445 (rebase).
