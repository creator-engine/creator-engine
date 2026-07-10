# RESUME STATE — CE-DEV-2 · 2026-06-22 (latest) · 🚩 PIVOT: Fleet-retirement → clean-install program

**WRITTEN BY/WHERE:** CE-DEV-2 controller as `cedev2` on the **DGX `spark-b824`** (dgx-spark-1/100.100.105.50, GB10, aarch64), cwd `/home/cedev2/creator-engine`, Opus 4.8 effort-high. SUPERSEDES `RESUME_STATE_CE_DEV2_20260622_LAUNCH-LEG-HARNESS.md`. **Read this + MEMORY.md (esp. [[ce-fleet-retirement-clean-install-program]]) first.** origin/main ≈ `b3445498` (+ #348 merging).

## PEER-SEAT → HOST → REACH
- THIS host = DGX. dev-1 `ssh dev1` (tmux `ce-dev1-orchestrator`) · dev-3 `ssh dev3` (tmux `dev3-onboard`) [VPS] · dev-4 `ssh cedev4@localhost -i ~/.ssh/id_ed25519` (tmux session `dev4stage1` pane %0, codex) [DGX]. Validator from source: `cd ~/creator-engine && PYTHONPATH=validators python3 -m creator_engine_validator.ce_cli …` (no `ce` on PATH; `.venv/bin/python` for gates/pytest).
- overwatch gh: `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`.
- ISSUE TRACKER = creator-engine/ce-ops. CODE/PRs = creator-engine/creator-engine. Repo uses a **merge queue** (don't pass `--squash`; `gh pr merge <n> --auto`).

## 🚩 THE PIVOT (Operator line-in-the-sand 2026-06-22)
Retire the run-from-source patchwork fleet; canary-replace each seat with a **genuine clean `ce` install** (install lifecycle = the thing under test). Kills the "we pre-calibrated the measuring instrument" problem. **Decisions confirmed: (1) dev-4/DGX first; (2) build `ce brain init`; (3) two-milestone sequence.** Autonomy flip now flows THROUGH the reinstalled fleet, NOT the old patchwork crons (flip track FROZEN on patchwork).

### Why (grounded by probe this session)
- ✅ **Clean HOST install works today:** #80 signed-publish → pip wheel; `docs/install.sh` verifies signed spec → venv → offline wheels → `~/.local/bin/ce`. (#80/#190/#173 merged.)
- ❌ **Containerized/no-tmux end-state = scaffolded, not built:** gVisor (`runner/gvisor_proxy_backend.py`) + OpenShell (`runner/openshell_backend.py`) backends registered, unimplemented (A.2b); `deploy/dgx-*-runsc/Dockerfile` are lab scaffolds w/ no CE inside; tmux hard-wired (`lane_runtime.py:742`, RV1-030).
- ❌ **No brain bootstrap on install:** no `ce brain init`; `brain_runtime.verify_ledger` fail-closes if `.ce/state/brain/assertions.yaml` missing. Genesis creatable via `assert_claim` (SSOT) but never auto-run.

### M1 — retire source-patchwork → installed `ce` (NOW; still tmux)
Per seat: drain work → save identity/state → wipe patchwork checkout → clean-install via signed wheel → `ce brain init` → validate → promote. **ACCEPTANCE GATE:** clean-installed seat completes one real e2e cycle (pickup→claim→allocate→launch governed lane→work→PR) with ZERO source-tree/hand-bootstrap step. **dev-4 first.**

### M2 — containerize + retire tmux (after 3 builds)
Build order: `ce brain init` (#206) → headless/non-tmux visibility backend (#207) → CE container image consuming the signed wheel (#208, blocked-by #207). Then re-canary each seat into a container, drop tmux.

## ✅ PHASE 0 REACHED (clean stop, 2026-06-22)
- **Conveyor belt STOPPED:** FLEET HOLD sent to dev-1/dev-3/dev-4 → all acknowledged + IDLE (stop proactive pickup, no new claims). dev-1 clean (branch ce189-supersession-guard), dev-3 clean (ce141-docs-nav-refresh, closed its explorer subagents), dev-4 only untracked `.wave1-*.md`+`tmp/`. They will NOT self-pick until released.
- **#348 (launch-leg fix) MERGED**; **#350 (ce brain init) APPROVED by dev-1+dev-3, in merge queue** (monitor bxu7lh549). #337/#344 parked.
- **⚠️ dev-4 ce157 DRAIN QUESTION (runbook step 1):** dev-4's `~/ce-workspaces/creator-engine` is on `ce157-mint-broker`, **6 commits ahead of origin/main** (S1-S6 mint-broker, unpushed, no open PR). PR #300 already merged "#157 S1-S6" — so FIRST resolve: is this local branch already-merged-via-#300 (disposable) or divergent follow-on (must push/PR before retiring dev-4)? Diff `origin/main..ce157-mint-broker` content vs #300. dev-4 reported only untracked files (read "unpushed" as "uncommitted") — do NOT assume its branch is safe to wipe until this is checked.
- **Memory index trimmed** 43.5KB→27.5KB (demoted ~23 twins/superseded/historical/niche; critical+retirement-relevant intact). Company-brain project will solve index-size structurally.

## 🌙 NIGHT-ARC N1 RATIFIED → ce-ops#210 (Operator approved as-is 2026-06-22)
Drive autonomously per #210: W1 land release+dev-4 canary · W2 M1 rollout dev-3→dev-1 · W3 fleet→governed-on-installed-ce · W4 M2 gateway (#207 visibility backend→#208 container image, target=1 seat proven) · W5 #197 `ce onboard` one-shot · W6 hygiene(#209 flake,#351/#337/#344)+next arc. Grants R1(auto-merge on review+green) R2(re-sign 0.2.0 line, no version bump) R3(seat-retirement runbook) R4(lift HOLD per-seat) R5(trust-anchor DNS via stored token) R6(worker fan-out). ESCALATE: acceptance-fail/rollback · version bump · onboarding-agent autonomous-execution · M2 arch beyond #207/#208 · Arad/chmod735 (27 Jun) · <1 reviewer seat.

## 🔑 RELEASE-PUBLISH THREAD (M1 step 1 — the release dev-4 installs) — 2026-06-22
Goal: re-publish signed **0.2.0** built from current main (so it carries `ce brain init` #206) signed with **ce-root-v1** (primary root, key+passphrase on cedev2: `~/.ce-keys/ce-root-v1` + `.pass`; sign via `SSH_ASKPASS=/tmp/ce_askpass.sh SSH_ASKPASS_REQUIRE=force DISPLAY=:0 setsid -w ssh-keygen -Y sign -f ~/.ce-keys/ce-root-v1 -I ce-root-v1 -n ce-spec-v1`).
- **Publish mechanism:** `release-stage --repo-root <main checkout> --version 0.2.0 --out <dir> --sign-mode placeholder --signing-key-id ce-root-v1` → builds wheel+SHA256SUMS+canonical+placeholder spec → Operator/agent signs canonical → insert b64 sig into `llms-install.md` `value:` → publish = commit `docs/` to main → Pages auto-redeploys `creator-engine.dev/downloads/0.2.0/`. **Overlay, don't mirror:** preserve `docs/downloads/0.2.0/scanners/` (ce-ops#123 brownfield mirror, independent of SHA256SUMS). Closed 6-path set. Manifest needs a fenced ```text block (COUNT + SHA256 = sha256 of sorted-unique-paths+"\n")).
- **Two review-caught fixes (both via dev-3):** #352 `--signing-key-id` flag (MERGED) + #354 parameterize the verify-recipe principal (the rendered llms-install.md recipe grep/awk/`-I` must = signing_key_id, not the default) — **#354 MERGED-pending (monitor bd8kux96n)**.
- ✅ **DNS trust anchor DEPLOYED + verified:** `_ce-root-v1.creator-engine.dev` TXT = `ce-root-v1=SHA256:mkX7cRfHNrx6mtK8Ek30CcRn6fbfIPK/SU/6KKc0AOQ ce-dev1-root-v1=SHA256:tqPyyLJiJSJA3gdujT2tPv7MiJvdAevxHZSQCdPHC+s` (CF zone `a384e371157c93ad3ab9efe0d6ebc3ed`, rec id `4cbbc4bea7420d867bc4303dcb4452bc`, ttl 300). Was NXDOMAIN → **production install was broken at install.sh:520-523 anchor step for ALL signers**; now passes anchor_record() parse for both principals. CF token (working) at `~/.ce-keys/cloudflare.env` (0600). The FIRST token lacked DNS:Edit (auth 10000); 53-char length is NORMAL for these tokens.
- **PR #353** = the publish PR (branch `ce-republish-020-rootv1`, worktree `/home/cedev2/ce-pub-020`). Currently has STALE artifacts (signed before #354's recipe fix) + dev-3 CHANGES_REQUESTED. **NEXT after #354 merges: re-stage 0.2.0 from corrected main → recipe now names ce-root-v1 → re-sign → force-update #353 branch → dev-3 verifies FULL chain (sig + live DNS anchor + consistent recipe) → merge → Pages live → verify `curl creator-engine.dev/downloads/0.2.0/SHA256SUMS` → dev-4 installs.**
- ce157 drained: **PR #351** (8 commits, needs manifest+review to merge — post-canary).

## ⏳ IN FLIGHT
- **Worker `a29c952b` building #206 `ce brain init`** in worktree `/home/cedev2/ce206-worker` (branch `ce206-brain-init`). Idempotent genesis at `.ce/state/brain/assertions.yaml` via `assert_claim`; fail-closed on corrupt; wire into provisioning; production-realistic tests + manifest + changelog; commit, NO push. **NEXT: check its report/commit → review → push → PR (body needs `- **Declared work class:** story`) → single reviewer → merge.**
- **#348 (#205 launch-leg: bind LAUNCHED_STATE to `seat_lifecycle.REGISTRATION_STATE_GOVERNED` + offline e2e harness)** — dev-4 APPROVED, CI green, **queued to merge**. Monitor `bzk8ecpap` confirms merge + removes worktree `/home/cedev2/ce205-worker`. (Real bug: belt reported launched=False on every spawn.)

## TICKETS (filed this session)
- **#206** `ce brain init` (M1 prereq) · **#207** headless visibility backend (M2) · **#208** CE container image (M2, blocked-by #207). Parents: #198 dogfooding, #115 containment, #82, #205.

## PARKED (not on critical path — clean stop, no danglers)
- **#337** (mine, #151 forge.re_review reconciler) — BEHIND + CHANGES_REQUESTED; needs rebase + address review + re-approve. Land after M1.
- **#344** (dev-3, #162 seat-launch governance runbook) — CHANGES_REQUESTED; dev-3 self-picked, owns driving it.

## OPEN STRATEGIC (surface to Operator)
- **#197** self-driving onboarding / autonomous DevOps agent (Arad feedback) — now intertwined w/ clean-install (a new user IS the fresh-install path). North-star differentiator.

## NEXT-SESSION FIRST ACTIONS
1. Check worker `a29c952b` / worktree `/home/cedev2/ce206-worker` → review → push → PR → single reviewer → merge `ce brain init`.
2. Confirm #348 merged (monitor `bzk8ecpap`).
3. Begin M1 dev-4 retirement runbook: front-load preconditions (drain dev-4 work, save identity/keys, clean-install steps, brain-init, acceptance e2e) BEFORE retiring. dev-4 = `ssh cedev4@localhost` on THIS DGX.
4. After M1 dev-4 proven: #207 headless visibility backend → #208 container image (M2).
