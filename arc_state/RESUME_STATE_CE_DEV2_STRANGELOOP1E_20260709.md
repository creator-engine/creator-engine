# RESUME STATE — CE-DEV-2 — 2026-07-09 ~15:55 UTC — STRANGELOOP1E
# Supersedes STRANGELOOP1D. Read order: MEMORY.md → DECISIONS_20260708.md → this file.
# Context: DGX host rebooted 12:54, recovered 13:40; prior session cleared.
# All session-owned workers (review agents, watchers, heartbeat, session cron) ARE DEAD
# and must be re-created. Seats and gate survived the /clear.

---

## SURVIVES /clear — STILL RUNNING

| Item | State | Note |
|---|---|---|
| dev-4 container (ce-dgx-codex) | Running | Pane now **w4:p1** (post-reboot herdr restart); w1:p1 is GONE |
| dev-3 container (ce-vps-codex, via dev1) | Running | Pane w1:p1 |
| dev-1 tmux (ce-dev1-orchestrator:2.0) | Running | |
| ce-queue-daemon | **systemd active** | Pass 93, clean; 2 deferring (likely #929+#927 waiting CI checks) |
| Host crontab watchdog | Running | `*/10 * * * * ~/.ce/strangeloop1-watchdog.sh` (telemetry-only; remove at arc close) |
| Arad-install codex controller | Running | tmux `ce-orchestrator:arad-install` · stage 5 in progress · 34% ctx used · waiting for Arad Goal/Done-when/Change-type |
| ⛔ Session cron 21,51 dev-check | **DEAD** | Session-only; **must recreate immediately on resume** |
| ⛔ Fleet signal watcher | **DEAD** | Must re-arm |
| ⛔ All in-session review/harvest workers | **DEAD** | See IN-FLIGHT section |

---

## BOARD — live as of ~15:55 UTC

**Today's merges: 18** (#908 through #928; all 2026-07-09)

| PR | Unit | State | Next action |
|---|---|---|---|
| **#929** | README review minors / Unit C (ratchet 103→104) | **APPROVED → gate** | Drain; on merge → brain-ledger window opens (see queue below) |
| **#927** | fix(smoke): chown signing secret + dump pass logs | **APPROVED → gate** | Drain |
| **#925** | Extend identity registry app schema (ce-470 s1) | **REVIEW_REQUIRED** | Re-dispatch reviewer — controller MUST create worktree from head `d539a5f2` FIRST (absolute rule: reviewer has no Bash) |
| **#912** | design: ratification authorization binding (ce-513) | ⏸️ Operator-held | No action until Operator |

---

## SEATS — live as of ~15:55 UTC

### dev-4 — DGX (ce-dgx-codex) · pane **w4:p1** ← always use this after the reboot

- **State:** READY (idle)
- **Unit:** ce-490-contained-launch-preflight-s1
- **SHA:** `221c8bd87be3ca03b286ce5ab38c3f9bd6fdfb98`
- **Manifest:** `.ce/pr-manifests/ce-490-contained-launch-preflight-s1.md`
- **Ctx:** 24% used (76% left)
- **Next:** Controller harvests → open PR → dispatch reviewer; then restock next backlog unit

### dev-3 — VPS (ce-vps-codex, via `ssh dev1`) · pane w1:p1

- **State:** READY (idle)
- **Unit:** ce-497-controller-state-sync-s1 (independence-lane s1: snapshot .ce/state+briefs+claims→forge, secrets-denylist pinned)
- **SHA:** `4871b8990adcb511857fef1bf1d57981725c830e`
- **Manifest:** `.ce/pr-manifests/ce-497-controller-state-sync-s1.md`
- **Ctx:** ~15-25% used (worked 9m16s)
- **Next:** Controller harvests → open PR → dispatch reviewer; next unit after harvest confirms

### dev-1 — Hetzner (ce-dev1-orchestrator:2.0)

- **State:** BLOCKED · **NOT PUSHED**
- **Unit:** ce-496-controller-bootstrap-doc-s1 (independence-lane: VPS replacement-controller runbook, hydrate-from-SSOT, harness-agnostic)
- **Local SHA:** `6f85f4de1f1153ec11176bfbecb0fe7bc705a78f` (unpushed)
- **Ctx:** 35% left (65% used) — approaching limit; corrective must be surgical
- **Blocker:** 2 failing tests: `test_public_docs_internal_trees_have_only_known_exceptions` + `test_tracked_text_files_contain_no_new_confidential_or_internal_references` — doc literals contain internal tree paths / confidential strings outside authorized scope
- **Next:** Controller sends targeted corrective: identify the specific strings tripping the tests, scrub or replace with public-safe equivalents in the doc literals; run targeted tests only; then push

---

## IN-FLIGHT CONTROLLER WORKERS

**All prior-session workers are dead.** Resume via SendMessage from transcripts under:
`/tmp/claude-1003/-home-cedev2-creator-engine/*/tasks/`

| Worker | Status | Resume action |
|---|---|---|
| T5.1 authorship fork (CEO scrub + 0.3.4 truthfulness + toggle uniformity) | **COMPLETED** | Artifacts written 15:49 — `index.html` (197 KB), `build.py`, `how-to-install-ce.md`, `template.html`, `T5.1-CHANGES.md` all at `/home/cedev2/creator-engine/tmp/ce-welcome-pack-t5/`; pack is READY |
| #925 reviewer | **DEAD** | Re-dispatch: controller creates review worktree from head `d539a5f2` THEN dispatches reviewer; lenses = SSOT-fitness + example-truthfulness + confidentiality-boundary (placeholders only, no real App IDs) |
| dev-4 harvest worker (ce-490) | Not yet started | First controller action post-resume |
| dev-3 harvest worker (ce-497) | Not yet started | First controller action post-resume |
| dev-1 targeted corrective | Not yet started | Send immediately; ctx window is closing |

---

## OPERATOR MANDATES ACTIVE — priority order

1. **MAIN-CONTROLLER INDEPENDENCE** — controller must be spawnable on VPS via `ce launch` (claude OR codex harness), ALL controller state from SSOT/centralized CE location, DGX death must not halt the factory. Evidence: today's 12:54 reboot (factory down, all in-session state lost ~45 min). Units in flight: **ce-497** (dev-3 READY) + **ce-496** (dev-1 BLOCKED). STRANGELOOP-2 mandate must include: controller→VPS migration plan + IaC-redeployable face + SSOT acceleration.
2. **NO IDLE SEATS** while ce-ops backlog has 159 tickets. All 3 seats must be Working within 10 min of any READY signal.
3. **SUBAGENTS**: never `model: sonnet`/Sonnet 5; omit `model` key on pinned roles entirely.

---

## COMPLETED TODAY (state update)

- **T5.1 welcome pack SENT to Arad** (Operator, 2026-07-09) — pack at `/home/cedev2/creator-engine/tmp/ce-welcome-pack-t5/index.html`; her CE 0.3.4 install SUCCEEDED = Decision-15 fresh-tenant rehearsal PASSED live with evidence bundle at `/home/cedev2/creator-engine/.ce/state/research/ARAD_REHEARSAL_EVIDENCE_20260709/`. **Mythos tenant is LIVE on 0.3.4.** First tenant feedback loop is now open — Arad's usage will produce the first real product signal; any defects she hits go to ce-ops as tenant-class tickets.

---

## ⏸️ AWAITING-OPERATOR — absolute paths, priority order

1. **PR #912** — design preview `https://github.com/creator-engine/creator-engine/pull/912`
2. **Arc report** — `/home/cedev2/creator-engine/.ce/state/research/ARC_STRANGELOOP1_REPORT_20260709.md` (to be written at arc close)
3. **Nitzan D6** — next unit in Nitzan onboarding sequence
4. **STRANGELOOP-2 mandate** — must now include: (a) controller→VPS migration + IaC-spawnable face; (b) SSOT acceleration (#496/#497 as s1 artifacts); (c) mechanization of all LESSONS LEDGERED TODAY

**NEXT-ACTIONS NOTE:** First tenant feedback loop is open (Arad LIVE on 0.3.4). Monitor for defects from her first-journey session → file as tenant-class ce-ops tickets. Stage 5 first-journey is in progress in `ce-orchestrator:arad-install` (seat waiting for Arad's Goal/Done-when/Change-type).

---

## BRAIN-LEDGER WINDOW QUEUE — serialized; **#929 merge opens the window**

Queue in strict serial order (do not parallelize; brain is a singleton resource):

1. **ce-516 Item-3** — workflow comment edit + alert permissions + pin cascade (deferred: comment-only edit trips brain-pin sha → needs byte-change-safe approach or fresh precompute of record 65)
2. **ce-478** — pyproject.toml pin (brain-PINNED; pyproject.toml now on precompute list after byte-change-rule violation)
3. **ce-453 Part A** — hash-pin gate (also covers the `answers_schema_sha256` gap)
4. **#500 slices a/d** — launcher scripts (territory freed post-#918 hermes retirement)

---

## LESSONS LEDGERED TODAY — STRANGELOOP-2 mechanization items (one line each)

- **Brief template must ban committed READY files** — 5 harvest-fix occurrences; template-level prohibition in place; enforce via composer checklist step
- **Dev-1 self-push PR bodies omit the G5 line** — 2 CI bounces; G5-body-line must be a BOLDED required step in dev-1 brief template
- **Reviewer role has NO Bash → controller MUST create review worktree BEFORE dispatch** — 3 occurrences today; now an absolute unconditional rule
- **Composer briefs must carry the public/private boundary check for any docs/ content** — real mythos App IDs (4103119/inst 141552951) nearly merged into a public example; public-docs confidentiality gate does NOT cover App IDs; gap is #423-lane candidate
- **Brain-pin precompute must use the BYTE-CHANGE rule** — comment-only edit trips a pinned sha; ANY byte change to ANY evidence_ref path trips the pin; pyproject.toml added to precompute list
- **Targeted-tests-only rule must be in every contained-seat brief** — dev-4 ran full `validate-pr` → resource-killed; rule did not survive restock brief template (composer gap #3)
- **After any container/herdr restart, `herdr pane list` FIRST, never assume pane id** — dispatch landed in dead pane (old w1:p1) for ~30 min; pane had moved to w4:p1
- **Harvest venv runs the LEGACY work-class enum (tiny|story|feature|epic; NOT S/T aliases)** — CI accepts both; version skew between installed validator and repo head; S2 item

---

## INCIDENT GOTCHAS — DGX reboot 2026-07-09 12:54 (verbatim; hard-won)

- **Launcher config toml lives in /tmp** → host reboot bricks `docker start` (bind-mount source missing). Regen from `/home/cedev2/creator-engine/deploy/dgx-runsc/run-codex-runsc.sh` lines ~287-315 with UNQUOTED env values in the hook command. `fs.protected_regular` prevents root from rewriting others' /tmp files → use `sed -i` (rename-based rewrite); do NOT use `tee` or output redirect.
- **Stale `.gvisor.overlay.img.<cid>` in the overlay2 diff dir blocks container start** after unclean shutdown. That img IS the container's runtime filesystem (77 GB for dev-4) → `mv` it aside to unblock start (preserves data). Salvage copy at `/home/cedev2/.ce/dev4-crash-recovery-20260709/gvisor.overlay.img`.
- **Seat /var/tmp WIP lives ONLY in that overlay image** → commit-early doctrine is load-bearing; any uncommitted WIP in a seat is lost on container kill or host reboot.
- **On dev-4 restart, codex TUI needs NO re-auth** (CODEX_HOME is bind-mounted) but pane starts fresh with new context and new pane id. Worktrees + briefs in /var/tmp are GONE — re-stream brief from SSOT and re-dispatch with explicit no-committed-READY correction.
- **After restart, always run `herdr pane list`** before any send — pane ids shift on herdr restart (this reboot: w1:p1 → w4:p1).
