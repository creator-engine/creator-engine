# RESUME STATE — CE-DEV-2 · 2026-06-24 · 🏭 AUTONOMOUS FLEET · V10

**WHERE:** CE-DEV-2 controller, `cedev2` on DGX `spark-b824` (GB10 aarch64), cwd `/home/cedev2/creator-engine`, Opus 4.8 high. **SUPERSEDES V9.** READ THIS + MEMORY.md + `~/HERDR_CONNECT_REFERENCE.md` FIRST. Discipline: **verify-don't-trust** every seat "done", every CI "green", every commit SHA; **inline-only seat dispatch**; **codify don't rediscover**.

## 🔴 STANDING DIRECTIVES (Operator, 2026-06-24)
- Morning arc BATCH-RATIFIED → drive autonomously; ping only for genuine ratification.
- **I AM the forge triage system** until the belt is live: never idle a dev; restock after EACH completion (codex exec is ONE-SHOT). Parallelize via WORKERS/forks (Operator pushed this hard).
- **Peer-review practice RATIFIED:** route awaiting-review PRs to a non-author seat. ⚠️ Only **dev-1 (non-contained)** can SUBMIT reviews — contained seats (dev-3/dev-4) can't (no creds; [[ce-contained-seats-cannot-submit-reviews]]). I review dev-authored PRs as ce-dev-2; route ce-dev-2-authored PRs to dev-1.
- **OpenBao live bring-up: Operator GAVE GO** — ephemeral rehearsal autonomous-OK (BUT blocked by a now-FIXED+MERGED script perm bug #225/#413; rehearsal can re-run); REAL init/unseal+secret-load needs Operator AT A KEYBOARD (custody material must not enter controller context).
- **Belt merge AUTHORIZED** ("merge the belt once refactors land") — exercised with: verify green + fail-closed re-confirmed + independent review.

## ✅ MERGED TO MAIN THIS SESSION (9)
#404 OpenBao automation · #405 install fix (Friday blocker) · #406 ce-ops checkout (#215) · #407 capability matrix (#220) · #409 carrier scaffold (#214) · #413 OpenBao bring-up perm fix (#225) · #414 visibility backend (#207, the #226 peek substrate) · #415 contained-launch probed+fail-closed (#221) · #408 detached-launch + secret-retention fix. **main tip = 538bdd11.**

## 🔁 IN FLIGHT — THE BELT (W2 milestone, nearly landed)
- **#412 Integrator belt-poller (#218)** branch `ce218-belt-poller` head `54c6b7ae` → **CI GREEN, auto-merge LATCHED, ce-dev-2 approved.** dev-1 was nudged to clear its (body-only) CHANGES_REQUESTED — once it submits `--approve`, reviewDecision→APPROVED → **MERGES**. ⚠️ FRESH-ME: verify it merged; if dev-1 hasn't cleared, re-nudge dev-1 (or its CR is purely the G5 body format which is already fixed). dev-1 confirmed BOTH substantive blockers resolved (unscoped-poll fail-closed at CLI+programmatic layers; the --land CI fix).
- **#411 review-pickup belt (#188)** branch `ce188-belt-reviews-pickup` head `0fe42b52` → refactored clean (option-a shared-search-core: new `pickup_search.py` shared + `forge/review_pickup.py` v3 + `cev3 review-pickup`; `_versions` 54→55), verified 101 passed, body OK, carriers OK. **HELD pending #412 merge.** 🔴 **AFTER #412 MERGES:** rebase #411 onto new main + bump `_versions` `V3_RUNTIME` **55→56** + matching test-assertion (both belts each add one v3 module; second-to-merge collides) → then review (route to dev-1 or ce-dev-2) → merge.
- **#410 carrier-presence gate (#213)** head `c3da6970` → APPROVED + CLEAN, **HELD to merge LAST** (activates `--require-carrier` fleet-wide; merge after #412+#411 land).

## 🛠️ CRITICAL PLAYBOOK (hard-won this session — APPLY EVERY TIME)
- **STALE-REF TRAP (bit me ~5×):** `git fetch origin <branch>` only updates FETCH_HEAD, NOT the tracking ref. ALWAYS `git fetch origin 'refs/heads/X:refs/remotes/origin/X' --force` before reset/rebase/worktree. main moves FAST during a merge-train → **rebase every branch onto CURRENT origin/main before push**, else `git diff origin/main..HEAD` shows phantom mass-deletions/extra carriers. Verify carrier-commit parent == real remote tip before pushing.
- **CARRIER GATES (the "Validate governance artifacts" check runs gates in sequence — fix one, next appears):** (1) **G5 work-sizing:** PR BODY needs exactly one `- **Declared work class:** <tiny|story|feature|epic>` **bullet** (a `## heading` form matches ZERO → fail), ≥ diff floor. (2) **G-ii path-manifest:** diff must contain EXACTLY ONE `.ce/pr-manifests/<branch-slug>.md` (slug = branch name), path-set == diff. (3) changelog `.ce/changelog/<slug>.md`. Generator: **`/tmp/gen-manifest.py <slug> <issue> <title>`** (recreate if gone: computes count + `sha256("\n".join(sorted(paths))+"\n")`, two-phase commit→regen→amend). Verify: `verify-path-manifest --base origin/main --manifest-dir .ce/pr-manifests --head-ref <slug>`. **Fix-body-without-dismiss:** edit body + **close/reopen** (gate reads frozen event payload) + re-latch auto-merge.
- **v1⊥v3 VERSION BOUNDARY:** v1 modules (e.g. `ce_cli.py`, `pickup.py`) must NOT import v3 (`forge.*`); allowlist is FROZEN (3 edges, only-shrinks) — **decouple, don't allowlist**. Pattern: extract forge-coupled logic to a v3 module (`forge/X.py`, add to `V3_RUNTIME`), shared pure-stdlib infra to an unclassified `shared` module, route v3-coupled CLI commands to `v3_cli.py` (not v1 `ce_cli.py`). `version_boundary` failing CASCADES into `test_architect_evidence_examples` (any `ce check` sub-fail → exit 1).
- **DGX /tmp ENV ARTIFACT:** validator tests falsely fail (`/tmp`-as-repo-root `PacketRootNotIgnored`) on the DGX. Run host-side tests under `TMPDIR=/home/cedev2/cetmp` (mkdir it). Seats can't run pytest at all (no venv/uv/py3.14) → verify host-side via `/home/cedev2/creator-engine/.venv/bin/python`.
- **SEAT DISPATCH:** inline-only (no sub-agent — the foreman AGENTS.md fan-out STALLS under headless exec). Brief MUST end with a commit-SHA gate (`git commit && git rev-parse HEAD | tee /tmp/<slug>-sha.txt`; do-not-finish-without-it) — [[ce-seat-done-not-committed]]. dev-1 (non-contained tmux codex) dispatch = tmux send-keys to `ce-dev1-orchestrator:2` (window 0 is dead; controller is WINDOW 2, pane %64). dev-1 was reset via Operator `/compact` (was context-starved at 12%).
- **FORKS for push/PR/refactor on PUSHED branches** (avoids seat-local divergence); they inherit my context. Cost ~300-700k tokens each — for one-test/small fixes do it INLINE in a worktree instead.

## 🎫 TICKETS FILED THIS SESSION (ce-ops)
#223 PILOT install blocker (FIXED via #405/#413) · #224 restore dropped `lane` matrix row (follow-up to #407) · #225 OpenBao bring-up perm bug (FIXED via #413) · #226 mode-gated operator peek (cockpit) · #227 herdr-native dispatch / witnessability gap (ARC-PRIORITY; codex exec is headless→bypasses herdr) · #228 cred-injection principle / onecli (creds must never enter container env; #408's `-e` token = stopgap).

## 🧠 RESEARCH IN FLIGHT (ultracode Workflow)
**`ws657ng74`** — "CE Excessive-Agency defense" (indirect-injection → destructive authenticated GitHub action; OWASP Agentic). 6 lanes (L7 egress · JIT OpenBao tokens · MCP gateway · **NeMo Guardrails DEEP for NVIDIA pitch** · HITL escrow · dual-agent reader/writer) → adversarial verify → CE-specific defense-in-depth design doc. Auto-notifies on completion. **FRESH-ME: relay the design; OFFER to persist it to ce-ops `designs/` ([[ce-design-artifacts-in-ceops]]).** Transcript: `.../subagents/workflows/wf_3092f468-402`.

## 🖥️ FLEET (all idle at checkpoint; CIDs rotate — re-derive)
- **dev-1** (VPS, NON-contained tmux codex, window 2 %64) — reset+healthy (~63% ctx); was clearing #412 CR. THE only credentialed reviewer seat.
- **dev-3** (VPS, contained, CID was `dbebe1841521`) idle. **dev-4** (DGX, contained, CID was `925e1350194b`) idle. Both reserved for belt cross-review / restock.
- Tokens: `~/.ce-keys/ce-dev-2.pat` (my reviewer id), `ce-dev-4.pat`, overwatch (`~/.ce-keys/overwatch.env`, `GH_TOKEN=$CE_OVERWATCH_PAT`, push/admin). Repo `creator-engine/creator-engine`; ISSUES `creator-engine/ce-ops`.

## 🎛️ CONTROLLER QUEUE (fresh-me, in order)
1. **Verify #412 merged** (dev-1 clearing CR + green → auto-merge). If stuck, re-nudge dev-1 / check CR.
2. **#411:** rebase onto new main + `_versions` 55→56 + assertion → review → merge.
3. **#410 LAST** → carrier gate goes live fleet-wide.
4. **Workflow `ws657ng74`** design doc → relay + offer to persist to ce-ops/designs (NVIDIA-pitch relevant).
5. Restock idle seats from backlog (avoid deploy/_versions contention); the **belt landing = W2 "activate autonomy" milestone** → then flip G6-enforce/G8-launch-arm so the fleet self-picks (ends my manual intake).
6. Two peer-review catches this session (dev-1: #408 secret-retention, #412 unscoped-live-merge) prove the review belt's value — keep routing.
