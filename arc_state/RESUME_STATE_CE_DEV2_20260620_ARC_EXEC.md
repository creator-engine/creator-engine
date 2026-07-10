# RESUME STATE — CE-DEV-2 Controller · 2026-06-20 (morning-arc execution + identity/credential rollout)

**WRITTEN BY / WHERE:** CE-DEV-2 controller as `cedev2` on the **DGX `spark-b824`** (aarch64, tailnet 100.100.105.50), cwd `/home/cedev2/creator-engine`, Opus 4.8 effort-high. Newest-by-mtime; SUPERSEDES `RESUME_STATE_CE_DEV2_20260620_MORNING_ARC.md`. Read this + `MEMORY.md` first.

## SEAT → HOST → REACH (all verified reachable this session)
- **dev-1** codex gpt-5.5, VPS — `ssh ce@100.72.252.20` → tmux `ce-orchestrator`. Authors `ce-dev-1`. PAT + `ce-forge-dev1.json`(app_id 4027068, now slug `ce-forge-dev-1`) at `/home/ce/.ce-keys/`.
- **dev-3** codex gpt-5.5, VPS — `ssh ce@100.72.252.20` → `sudo -n -u ce-dev-3 tmux ... -t dev3-onboard`. Authors/reviews `ce-dev-3`. ⚠️ App `ce-forge-dev-3` exists but **no local PEM/config** (unwired). PAT exists but was missing `Issues:write`.
- **dev-4** codex gpt-5.5, CONTAINED gVisor, LOCAL — `ssh cedev4@localhost` → tmux `dev4stage1`. Authors `ce-dev-4`. **No gh / no egress in container** (containment holds). No own App yet (provision `ce-forge-dev-4` = W5). NEVER C-c.
- **Me** dev-2 = `cedev2` (DGX). gh NOT logged in — every call uses per-command `GH_TOKEN`. Creds in `~/.ce-keys/`: `ce-dev-2.pat`(0600, own identity, Issues:write OK), `ce-dev-4.pat`(0600, HELD as publisher — ADR-0007 model b), `overwatch.env`(`CE_OVERWATCH_PAT`/`CHMOD_OVERWATCH_PAT` = `ce-overwatch`), `ce-forge-app.json`+pem(`ce-forge-dev-2`, app_id 4025879), `git-credential-ce-forge.sh`(push helper), `ce-root-v1`(signing). ⚠️ 3 identities on one disk → OpenBao migration owed (see below).
- **Tmux seeding quirk (codex):** pastes collapse to `[Pasted Content]` → need a SECOND Enter to submit; clear stale input with `C-u`×8. pkill patterns must be bracketed (`[/]opt/...`) or they self-kill the SSH shell.

## ▶ IMMEDIATE NEXT ACTIONS (merge gates + verification)
1. **Merge #280** (W1 re-point) when CI greens — I pushed the fix `73fe291f` (kept old logins as historical aliases in `identity_map` so ADR-0001's `ratified_by: chmod735` still resolves; CI had failed `VAL-PA-IDENTITY-UNRESOLVED`). Squash-merge as `ce-overwatch`.
2. **Peer-review (as `ce-dev-2`, distinct from author `ce-dev-3`) + merge #282** (W2 #142) when green.
3. **Review/merge #283** (ADR-0007, proposed) — docs-only.
4. **Verify dev-1/dev-3 `Issues:write`** once Operator toggles their fine-grained PATs (root cause of dev-3's ce-ops 403 = PAT missing the Issues:write permission, NOT repo access).
5. Monitor **W3** (dev-1, `ce-orchestrator`) + **W4** (dev-4, `dev4stage1`) → review/merge their PRs when they 📦.

## MORNING ARC #144 (RATIFIED) — status
- **W1 renames DONE** ✅ — ce-dev-1/2/4 + ce-overwatch live (IDs preserved), old logins 404. PR **#280** (CODEOWNERS `@ce-dev-1..4` + `.ce/coordination.yml` identity_map + completion report) — awaiting CI-green→merge.
- **W2 #142** → dev-3 → **PR #282** OPEN (computer-use authority envelope schema + worker-harness contract + validator check/tests; Ring-2 hook deferred to phase 2). BLOCKED on CI/review.
- **W3 #135** OpenBao broker / secret-zero → dev-1 WORKING (design+build behind SecretIdentityBackend; response-wrapped SecretID per dev).
- **W4** rescoped #121→**#132** (clean-room DGX install live-drive; #121 hard-block already resolved by merged #272) → dev-4 WORKING, surfaced an S1 blocker (`rpds has no __version__`).
- **W1.5** App renames mostly DONE (ce-forge-dev-1/2/3 hyphen-aligned, slugs re-synced); remaining = provision `ce-forge-dev-4` (gated on W5).
- **W5** (with Operator): dev-4 push doctrine RESOLVED → model (b) (contained, courier acts as ce-dev-4); + OpenClaw deep-dive review (VPS tmux `ce-research-openclaw`).

## TICKETS opened this session
#142 computer-use authority envelope · #143 rename exec (done) · #144 morning arc · #145 CE playbooks (overcut-style; first = computer-use workflow) · #146 SSDF/SLSA conformance matrix. ADR-0007 = PR #283.

## ⏳ CREDENTIAL CUSTODY — OpenBao migration OWED (also in [[ce-per-dev-identity-secret-storage]])
Per-dev PATs are on-disk at seat `~/.ce-keys/*` (0600) INTERIM. **Cannot write vault now** (root revoked, broker #135 unbuilt). On broker-land OR a vault write path → migrate ALL standing per-dev tokens off-disk to OpenBao (JIT); ce-dev-4's must never persist at dev-2. Acceptance criterion on #135; custody locations on #137.

## ⏸️ PENDING OPERATOR
- Toggle `Issues:write` on dev-1 + dev-3 fine-grained PATs (UI) → then I verify.
- Rotate leaked `ghp_…1XTgpz` (printed to a transcript during #143).
- #137 SSOT expansion (emails, repo inventory, boxes+cred-pointers, OpenBao integration, per-credential permission-scopes) — recommended, not yet built.

## KEY DESIGN/STRATEGY captured
- **Core thesis** (in [[ce-product-north-star]]): deterministic control layer wrapping the probabilistic agent → output provably meets **NIST SSDF (SP 800-218) + OpenSSF SLSA**; non-technical solo-dev → Google/MS-grade software by construction. → #146 conformance matrix.
- **ADR-0007**: when every agent is contained (#128), push egress moves to a deterministic non-agent gateway (OpenShell supervisor) = network-egress twin of the OpenBao broker. author-sign ≠ gateway-transport; human = ratifier not courier.
