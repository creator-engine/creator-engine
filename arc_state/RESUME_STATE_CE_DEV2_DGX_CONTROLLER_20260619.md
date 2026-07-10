# RESUME STATE — CE-DEV-2 Controller (DGX) · 2026-06-19 (post Wave-A dispatch)

**WRITTEN BY / WHERE:** the CE-DEV-2 controller running as **`cedev2` on the DGX `spark-b824`** (aarch64, tailnet 100.100.105.50), cwd `/home/cedev2/creator-engine`. Saved **before an Operator context-clear + relaunch to re-auth `/remote-control`** (unset the shadowing `CLAUDE_CODE_OAUTH_TOKEN`, see RE-AUTH NOTE). Read this FIRST on cold start, then `~/CONTROLLER_HANDOFF_dgx-cedev2.md`, then `MEMORY.md`. **NEXT ACTION on resume is in the "▶ RESUME ENTRY POINT" section.**

## SEAT → HOST → REACH (verify a handle resolves before acting)
- **dev-1** (codex work seat, VPS) — **🟢 WORKING ce-ops#126**: `ssh ce@100.72.252.20` → tmux `ce-orchestrator:codex-ctrl`. Clone `/home/ce/creator-engine`.
- **dev-3** (codex, VPS) — **🟢 WORKING ce-ops#94+#127**: `ssh ce@100.72.252.20` → `sudo -n -u ce-dev-3 tmux ... -t dev3-onboard`. Clone `/home/ce-dev-3/creator-engine`.
- **dev-4** (codex, CONTAINED gVisor, LOCAL; idle): `ssh cedev4@localhost` → tmux `dev4stage1`. **NEVER C-c its pane.** Container `/workspace/creator-engine` is a **bind mount** from host **`/home/cedev4/ce-workspaces/creator-engine`** (git-bundle from there via `ssh cedev4@localhost`; do NOT enter the container).
- **Me** = cedev2. Creds: `~/.ce-secrets/controller.env` (Max OAUTH — **the shadowing var; see RE-AUTH**), `~/.ce-keys/ce-root-v1*` (signing), `~/.ce-keys/ce-forge-app.*` + `mint-forge-token.py` (`GH_TOKEN=$(python3 ~/.ce-keys/mint-forge-token.py)`).

## ▶ RESUME ENTRY POINT — MONITOR WAVE A, then dispatch Wave B
**Wave A (arc #129 W3 forge-identity cluster) is DISPATCHED and in-flight** (both seats Working at save):
- **dev-3 → ce-ops#94 + #127** on branch **`ce94-127-forge-identity`** (ONE branch, single PR cross-linking both — avoids the onboard_apply shared-file merge-tax). #94 = accept fine-grained PATs + right-size bootstrap scopes (ratified design `.ce/state/research/DESIGN_CE_OPS_94_bootstrap_finegrained_rightsize-capability.md`); #127 = bind forge identity from the install token's `GET /user`, not ambient git/gh.
- **dev-1 → ce-ops#126** on branch **`ce126-app-zero-repos`** — scope App installation to the configured target repo + clear zero-repos error.
- Both carry the **rebase→rebuild-wheel-on-rebased-HEAD→full `validators/tests/` suite→commit-local** done-gate; push/merge controller-gated. Signals: **`DEV3 94-127-DONE <sha>`** / **`DEV1 126-DONE <sha>`**.
- `🔒 in-compose` markers posted on #94/#126/#127.

**ON RESUME:** re-arm the cron (below), verify reach, then **monitor for the two DONE signals**. On each signal: bundle the branch → verify diff is scope-only + no served-trust-root paths (docs/install.sh, docs/downloads/**, docs/llms-install.md, docs/contracts/installer.md — NOTE #94 legitimately touches `docs/contracts/installer.md:122-127` for the mislabel fix, that one IS in-scope) → push (qualified refspec) → CI → independent review as `cedev1vps-cmd` → **merge per standing auto-merge grant** (these are pre-ratified arc-W3 fixes). **Watch the merge-cascade wheel trap**: whichever of the two merges first, the other must rebase + rebuild its wheel before it can merge.

**THEN Wave B — #88 → dev-4 (RE-SCOPE FIRST, do NOT assume from-scratch):** #88 **Phase 1 already MERGED** (PR #233, 06-15 — production ApplyDriver + ceiling-driven minter). The old resume's "existing-repo onboard inert until #88" framing was STALE. Before dispatching dev-4, **read the open #88 ticket to scope what Phase-2 remainder actually remains** (if any) — don't rebuild wired code. Build on the post-Wave-A base.

## DISPATCH / BANK MECHANICS (reuse)
- **Drive a codex seat:** `tmux send-keys -t <tgt> C-u; send-keys -t <tgt> -l '<single-line-msg-NO-apostrophes-NO-quotes-NO-$-NO-backtick>'; send-keys Enter; (sleep 1; Enter again)`. Confirm "Working" via capture-pane. Through ssh+sudo: wrap the msg in single quotes inside the double-quoted ssh arg.
- **Extract a seat's branch:** seat `git bundle create /tmp/x.bundle <branch>; chmod 644` → `git fetch /tmp/x.bundle <branch>:refs/tmp`.
- **Bank a PR:** verify diff vs current `origin/main` (scope-only, fresh `.ce/pr-manifests/<branch>.md` carrier, no served-trust-root paths) → `git push https://x-access-token:$GH_TOKEN@github.com/creator-engine/creator-engine.git refs/tmp:refs/heads/<branch> [--force]` (QUALIFIED refspec) → `gh pr create/checks --watch` → review.
- **Independent review (author≠reviewer):** approve as `cedev1vps-cmd` via `ssh ce@VPS "set -a; . ~/.ce-keys/reviewer.env; set +a; gh pr review <n> --approve --body '...'"`. **A force-push DISMISSES the approval → re-approve after each force-push.**
- **MERGE-CASCADE WHEEL TRAP:** two PRs that both rebuild `validators/wheelhouse/*.whl` conflict (binary) once the first merges; the second MUST rebase onto new main + rebuild the wheel on the rebased HEAD before merging. Permanent fix = ADR-0006/#133.

## WHAT SURVIVES vs RE-DO ON RESUME
- **RE-DO:** **the :08/:38 day-shift cron is SESSION-ONLY → re-arm via CronCreate** (it was `a76e6d4b`; prompt body in `~/CONTROLLER_HANDOFF...` + the one I armed this session — sweeps all 3 panes + open PRs, flags stalls/⏸️/`DEV{n} …-DONE` signals). Task list = session state. No background watchers active at save.
- **SURVIVES:** all git/forge state, memory files, this resume file, the `🔒` markers + dispatched work on dev-1/dev-3 (they keep running through the auth gap; they can't push — controller-gated — so nothing is lost).

## BOARD (as of save)
- **main HEAD = `b7980e6c`** (= OpenBao P3 #268).
- **✅ MERGED today (10 PRs):** #257(#123) #259(#122) #262(#128) #263(#124) #264(#125) #265(#113-P1) #266(#120) **#267(#115 controller-containment Wave1, a6ad1897)** **#268(#113 OpenBao P3, b7980e6c)**.
- **🟢 IN-FLIGHT (Wave A):** dev-3 `ce94-127-forge-identity` (#94+#127); dev-1 `ce126-app-zero-repos` (#126).
- **arc ce-ops#129 RECONCILED** earlier this session (10 landings logged; #122/#123/#124/#125 closed; #113/#115/#120/#128 kept-open-with-notes).
- **Only open PR = #216 `site-v8-pr1`** — APPROVED but BEHIND main + stale (06-12); needs rebase + visual checkpoint. Operator's call.

## PENDING OPERATOR ITEMS
- **ce-ops#113 OpenBao P3→prod go-live** — 7 ⏸️ AWAITING-OPERATOR items (recs approved). Items **2 & 3 (secret-zero injection, Shamir unseal/share custody) are Operator-personal trust-root acts**; 4/5/6 dev-1 can build+test; #7 (B.6 live-secret migration) HELD until restore drill passes.
- **#216 site-v8** — rebase + visual checkpoint, or leave it.
- **ADR-0006 / ce-ops#133** design-seat dispatch — UNBLOCKED (the #115-Wave1 + #113-P3 tracks landed). Folds in #91 (doc-currency) + #65 (changelog gate). Dispatchable next if Operator wants.

## RE-AUTH NOTE (the reason for this save)
`/remote-control` is blocked because the session uses the **inference-only Max OAUTH token** in `~/.ce-secrets/controller.env` via `CLAUDE_CODE_OAUTH_TOKEN`, which **shadows** the full-scope `claude auth login` credential. FIX, in the launcher shell: `unset CLAUDE_CODE_OAUTH_TOKEN` (do NOT re-source controller.env's token line; if you need its other vars, source then unset again) → verify `echo "${CLAUDE_CODE_OAUTH_TOKEN:-<unset>}"` shows `<unset>` → relaunch `claude --dangerously-skip-permissions` from `~/creator-engine`. Verify Max-tier auth + `/remote-control` available + reach to all 3 seats, **re-arm the cron**, then monitor Wave A.

## CAPTURED THIS SESSION
- `[[ce-derived-artifact-trust-path-fix]]` — ADR-0006/#133, the wheel/doc-drift permanent fix. Packaging-contract footgun hit ~5× incl merge-cascade.
- **#88 Phase 1 already merged (PR #233, 06-15)** — Wave B must re-scope, not rebuild.
