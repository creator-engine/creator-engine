# RESUME STATE — CE-DEV-2 controller — 2026-06-27 ~17:13Z — NIGHT-SHIFT ARC (locked) + ONBOARDING FOLLOW-THROUGH

> NEWEST checkpoint — open this + MEMORY.md FIRST. Supersedes RESUME_STATE_CE_DEV2_DAYARC_20260627T1130Z.md.
> Companion (READ for Wave 1): `RELEASE_030_CUTPREP_FOR_OPERATOR_SIGN_20260627.md` in this dir.

## ⚠️ IDENTITY / AUTH / TOPOLOGY (read first)
- **CE-DEV-2 controller** on DGX Spark (`spark-b824`, aarch64, `cedev2` uid1003, tailnet 100.100.105.50). Merge gate + Operator interface + foreman. ALL execution via WORKERS (no inlining — only approve+enqueue ratification, my own memory, SECRET-CUSTODY stay inline).
- overwatch (creator-engine + ce-ops): `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. Issues=ce-ops (private); CODE/PRs=creator-engine (PUBLIC).
- Approve as **ce-dev-2** (reviewer, distinct from author): `GH_TOKEN=$(cat ~/.ce-keys/ce-dev-2.pat) gh pr review <n> --approve`. NB ce-dev-2.pat is a FINE-GRAINED token scoped to creator-engine ONLY — it 404s on mythos (see PAT re-scope on Operator's desk).
- Merge queue (creator-engine): `gh pr merge <n> --auto` (no --squash; queue handles method). mythos has NO queue (private, no Pro) → merge directly.
- mythos creds: `~/.ce-keys/mythos-overwatch.pat` (NOT CE_OVERWATCH_PAT — that 404s on mythos).
- Arad machine: `ssh aradsky@100.74.214.78` (STANDING AUTH to write for onboarding). Her install = published 0.2.0 (broken; band-aids applied — see onboarding section).

## 🎯 NIGHT-SHIFT ARC — LOCKED IN by Operator 2026-06-27 ~17:10Z
**Primary objective = Wave 1: cut the fresh 0.3.0 release.** After it lands, CONTINUE driving Wave 0/2/3/4 in parallel autonomously. Operator green-lit the full plan + my recommendation (release-first). Theme: arm what we built + ship the release that closes the onboarding loop (turns "onboarding works if dev-2 hand-holds" → "just works").

- **Wave 0 — hygiene, parallel** ⚙️: diagnose close-bot non-fire + close the 7 drifted tickets (worker); land #591; (Operator UI: ce-dev-2 PAT re-scope to mythos — unblocks Arad reviews).
- **Wave 1 — CUT 0.3.0 (PRIMARY)** ⚙️ stage / 🔒 sign: see `RELEASE_030_CUTPREP_FOR_OPERATOR_SIGN_20260627.md`. Stage everything to the signing seam so the Operator's ce-root-v1 sign is ONE clean gesture. PREREQ: #591 merged (+ confirm #586/#587/#590 in main; band-aid real fixes #331/#332).
- **Wave 2 — arm the spine** (Operator gestures): AutoReview #292 lands (dev-3) → arm; R2 first live auto-merge flip 🔒; first unsupervised belt run 🔒 (#218 daemon built).
- **Wave 3 — finish ARC 2 + re-feed devs** ⚙️: #279 (render.py) → #280 (CI build-args) → #277 (carrier schema); re-feed dev-1/dev-4/dev-3; Nitzan BUILD arc kickoff (her starter-path PRs).
- **Wave 4 — compounding habit** ⚙️: institutionalize annoyance→tool (this session's bug-chain is proof) + agent-self-authored AGENTS.md.

## 🔧 IN-FLIGHT AT CHECKPOINT (verify on resume)
- **PR #591** (ce-ops#331 schemas-packaging, the release-blocker): APPROVED by ce-dev-2, auto-merge ARMED (squash). CI failed ONCE on work-sizing floor G5 (67 schema relocations counted delete+add → derived tier=epic, declared was story). **Implementer worker `addd3411ca1748daf` resumed** to bump PR body declared class story→epic + push empty commit to re-trigger CI. ON RESUME: check if it pushed; **re-approve the new head** (push likely dismissed my approval — verify reviewDecision==APPROVED on current head); confirm CI green → auto-merge fires. Branch `fix/ce-ops-331-package-schemas`.
- **PR #590** (ce-ops#332 tmux pane-parse): ✅ MERGED.
- **dev-3** → #292 (AutoReview) Working. **dev-1/dev-4** idle, available — re-feed in Wave 3.

## 🎫 TICKETS FILED THIS SESSION (onboarding dogfooding payoff)
#331 schemas-not-packaged (→PR #591) · #332 tmux pane-parse (→#590 MERGED) · #333 contributor dev-install docs gap · #334 packaging integration test silently SKIPs in CI · #335 make work-sizing+path-manifest rename-aware (mechanical relocations force epic/double-count). Earlier today: #326 os-native-default-solo · #327 per-user-App onboarding gap · #328→#587 brownfield-apply forge-identity.

## 👋 ONBOARDING STATE
- **Arad (test user)** — `~/ce-mythos/mythos` on her laptop. Hit a CHAIN of 0.2.0 install bugs, all band-aided live (see `ce-arad-pilot-onboarding` memory): (1) brain-bootstrap refused → schemas not packaged (#331) → shipped 0.2.0-SHA-4f4bd35e schemas into her CWD + `.git/info/exclude`; (2) tmux pane-parse (#332) → patched her installed `tmux_adapter.py` (backup `.bak`). `ce brain init` now writes a valid ledger; `verify_ledger.ok=True`. **She can retry `ce launch`.** Band-aids are install-scoped — the 0.3.0 release is the real fix. Still pending: her constitution ratify + first governed change; ce-dev-2 PAT re-scope so her mythos PRs get independent review.
- **Nitzan (collaborator on creator-engine, handle `Nitzan94`, email nitzanbarness1@gmail.com)** — welcome package FINALIZED + zipped at `~/creator-engine/tmp/nitzan-welcome-package.zip` (also delivered to Operator via SendUserFile). Operator is sending it to her manually. Package = from-source editable install on latest main (NOT 0.2.0 wheel), three-step starter path (use-CE-first → trivial plan.md Python-version fix PR → write CONTRIBUTING dev-install section). Contributes via fork (default) or collaborator access.

## 🟡 ON OPERATOR'S DESK (R-reserved / manual)
1. **0.3.0 release sign** 🔒 — the night's gating gesture; pre-drafted as ONE clean approval (see cut-prep doc).
2. **ce-dev-2 PAT re-scope** (UI: add chmod735-dor/mythos + mythos-ops to the fine-grained token; org must allow fine-grained PATs) — unblocks Arad mythos reviews.
3. **R2 first live auto-merge flip** · **first unsupervised belt run** — Wave 2 arming gestures.
4. Send Nitzan her zip (DONE on Operator side once sent).

## ▶️ NEXT ACTIONS (resumed session)
1. **Wave 1 FIRST**: finish #591 (re-approve new head → merge), then drive 0.3.0 cut-prep per `RELEASE_030_CUTPREP_FOR_OPERATOR_SIGN_20260627.md` to the signing seam; surface the ONE sign gesture to Operator.
2. In parallel (per Operator's standing direction to continue everything after release lands): Wave 0 close-bot diagnosis + drifted-tickets; Wave 3 ARC-2 re-feed; Wave 4 habit.
3. Watch for `addd3411ca1748daf` (PR #591 fix) + dev-3 #292 completion.

## 📌 KEY FILES / PATHS
- Cut-prep doc: `.ce/state/research/RELEASE_030_CUTPREP_FOR_OPERATOR_SIGN_20260627.md`
- Release tooling: `validators/creator_engine_validator/release_publish.py` (stages Pages mirror + placeholder sig + emits exact `ssh-keygen -Y sign` cmd; SIGNING_KEY_ID/ce-root-v1 — VERIFY #586 anchor fix is in fresh origin/main, NOT the polluted controller checkout). cev3 release subcommands in `v3_cli.py`.
- Controller checkout `/home/cedev2/creator-engine` is STALE/polluted (on ce11-test-tier-split) — workers branch off origin/main; don't rely on local HEAD for release facts. Verify against fresh origin/main.
