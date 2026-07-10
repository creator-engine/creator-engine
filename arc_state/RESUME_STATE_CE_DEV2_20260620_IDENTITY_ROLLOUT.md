# RESUME STATE — CE-DEV-2 Controller · 2026-06-20 (per-dev identity rollout complete + launch-infra fixed + cockpit Slice 1 awaiting checkpoint)

**WRITTEN BY / WHERE:** CE-DEV-2 controller as `cedev2` on the **DGX `spark-b824`** (aarch64, tailnet 100.100.105.50), cwd `/home/cedev2/creator-engine`, Opus 4.8 effort-high. Newest-by-mtime; **SUPERSEDES** `RESUME_STATE_CE_DEV2_20260620_ARC_EXEC.md`. Read this + `MEMORY.md` first. main HEAD = `e8e40b2c` (post #280+#282 merges).

## ⚠️ #1 PENDING OPERATOR — COCKPIT VISUAL CHECKPOINT (high value)
The **cockpit seat finished Slice 1** of the #45 journey-cockpit elevation and is **STOPPED awaiting the Operator's visual checkpoint**. Screenshots saved under `/home/cedev2/ce-cockpit-seat/tmp/cockpit-shots/`. **Slice 2 (interactive governance write-seam) must NOT start until the Operator reviews the screenshots** (design-green never self-assessed — [[ce-website-design-routing]]). The seat's input has a smart-suggested "start slice 2" — do NOT submit it un-reviewed.

## SEAT → HOST → REACH (UPDATED this session)
- **Me dev-2** = `cedev2` (DGX). gh NOT logged in — per-command `GH_TOKEN`. Creds `~/.ce-keys/`: `ce-dev-2.pat`(own, Issues:write✓), `ce-dev-4.pat`(HELD, dev-4 model-b), `overwatch.env`(`CE_OVERWATCH_PAT`/`CHMOD_OVERWATCH_PAT`=ce-overwatch, both fine-grained, REPO-scoped only — can't introspect other PATs), `ce-forge-app.json`+pem, push helper, `ce-root-v1` signing. (ce-dev-1.pat was held then **shredded** after #150.)
- **Cockpit seat** (DGX): tmux **`ce-cockpit`**, worktree `/home/cedev2/ce-cockpit-seat`, branch `ce45-journey-cockpit-elevation`, claude **Opus 4.8 xhigh**. Slice 1 DONE (journey-default + CEO/Dev mode switch + visual dev-arc + first-class decision inbox, on L2/L3 law). AWAITING visual checkpoint → then Slice 2 (interactive write-seam, separate governance review). Ratified brief: `/home/cedev2/ce-briefs/ce45-journey-cockpit-elevation.md` (SHA `5bc70c04…`).
- **dev-1** = **NOW the `ce-dev-1` OS user** (uid 1004) on VPS — `ssh ce@100.72.252.20` → `sudo -n -u ce-dev-1 tmux ... -t ce-dev1-orchestrator`. codex gpt-5.5 xhigh, checkout `/home/ce-dev-1/creator-engine`. Identity fully wired (own PAT/gh, App ce-forge-dev1, signing ce-dev1-root-v1, git=ce-dev-1). Working **#281**. (#150 re-wire DONE; old `ce`-user `ce-orchestrator` retired.)
- **dev-3** codex, VPS — `sudo -n -u ce-dev-3 tmux ... -t dev3-onboard`. ce-dev-3 PAT has Issues:write ✓. **REFRESHED to 100% context 2026-06-20** (saved pre-refresh resume `RESUME_STATE_dev-3_20260620_PRE_REFRESH.md` → codex exited → relaunched `~/.npm-global/bin/codex`) — now doing the **SCOPED #283 re-review** (verify the 2 anchor fixes → approve).
- **dev-4** codex, CONTAINED gVisor, LOCAL DGX — `ssh cedev4@localhost` → tmux `dev4stage1`. ce-dev-4.pat held by publisher (dev-2). NEVER C-c.
- **Reviewer seat** (ce-review, DGX) — RETIRED after approving #282+#284.

## PR BOARD (main=e8e40b2c)
- **#280** (W1 re-point) — ✅ MERGED. **#282** (envelope, #142) — ✅ MERGED (after ce-dev-2 caught+dev-3 fixed a numeric-secret bypass).
- **#281** (OpenBao broker, ce135) — dev-3 CHANGES_REQUESTED + BEHIND; **ce-dev-1 seat working it now** (address dev-3 + rebase, author as ce-dev-1).
- **#283** (ADR-0007) — anchors fixed + rebased (`7bb917c4`); **awaiting dev-3 re-review** (dev-3 low context — see above).
- **#284** (launcher .hermes→.ce/state, ce149) — ✅ APPROVED+green but **merge-CONFLICTS after #282** → needs conflict-rebase + artifact regen (wheel/check-count) by **ce-dev-1**; QUEUE after #281. Do NOT hand-resolve hashes.

## IDENTITY ROLLOUT — ✅ COMPLETE
All dev controllers now run as their own identities: dev-1=ce-dev-1 (NEW, #150), dev-2=ce-dev-2, dev-3=ce-dev-3, dev-4=ce-dev-4. ce-dev-1/2/3 PATs have Issues:write (verified by behavioral probe — the only method until an owner-account PAT with `organization_personal_access_tokens:read` exists; see #137/#147).

## LAUNCH INFRA (NEW — #148)
`ce launch` now works after `uv pip install --python .venv/bin/python --no-index --find-links validators/wheelhouse creator-engine-validator` (the .venv was empty). **BUG:** `ce launch`'s TmuxAdapter direct-spawns claude → seat exits instantly (window vanishes). **WORKAROUND USED:** spawn via shell-wrapper — `tmux new-session` (shell) + `remain-on-exit on` + `send-keys '<governed argv>'`, where governed argv = `claude --model=claude-opus-4-8 --dangerously-skip-permissions --setting-sources project --strict-mcp-config --mcp-config <empty {"mcpServers":{}}>`. The `--setting-sources project` loads the §7 hooks → governed. Both cockpit + reviewer seats launched this way. #148 tracks the fix.

## TICKETS OPENED THIS SESSION
#147 (SSOT expansion child of #137) · #148 (launch-infra gap + ce launch direct-spawn bug) · #149 (launcher .hermes→.ce = PR #284) · #150 (ce-dev-1 re-wire — CLOSED/done). Plus earlier: #142/#144/#145/#146, ADR-0007=PR#283.

## ▶ IMMEDIATE NEXT ACTIONS
1. **Operator: cockpit visual checkpoint** (screenshots `/home/cedev2/ce-cockpit-seat/tmp/cockpit-shots/`) → then I tell the cockpit seat to start Slice 2.
2. Monitor **ce-dev-1** on #281 → when done, **queue #284 conflict-rebase** to it.
3. Resolve **#283 re-review** (dev-3 low context — nudge save+/clear+resume, or fresh reviewer venue). Then merge #283 (overwatch) when approved+green.
4. Merge #281/#284 (overwatch) once rebased+approved+green.

## ⏸️ PENDING OPERATOR
- Cockpit visual checkpoint (#1 above). · Rotate leaked `ghp_…1XTgpz`. · (optional) mint an owner-account PAT w/ `organization_personal_access_tokens:read` to enable the #137/#147 declared-vs-actual permission audit.

## KEY DESIGN/STRATEGY captured this session
- **#45 cockpit elevation = full vision + interactive** (Operator-ratified): journey=default face, CEO/Dev mode switch demoting ops board, full visual dev-arc, decision-inbox; Slice 2 wires ratify/resolve via the canonical gate + form-echo (breaks the cockpit no-write law deliberately → governance review).
- **Org-PAT audit finding:** overwatch PATs are repo-scoped only; GitHub has no cross-token introspection; the clean audit path (`GET /orgs/{org}/personal-access-tokens` w/ per-PAT permissions) needs org-OWNER + `organization_personal_access_tokens:read`. Behavioral probe is the interim verification.
- **ADR-0007 anchors** corrected (#135 retitled to its real scope + PR #281; ADR-0005 path → `0005-…` no prefix).

## ═══ LATE-SESSION DELTA (2026-06-20, supersedes above where conflicting) ═══
- **#283 ADR-0007 → APPROVED** by ce-dev-3 (scoped re-review post-refresh — full #151 procedure demo'd). READY TO MERGE as overwatch (likely BEHIND post-#282 → base-only rebase first).
- **dev-3 REFRESHED (91%) then DISPATCHED the PLAYBOOKS build** — now on branch `ce145-playbooks-scaffold` building the in-tree `playbooks/` library (scaffold + `docs/contracts/playbook-format.md` + `schemas/playbook.schema.yaml` + `ce_playbook_format` CI gate + first playbooks: computer-use-ticket, reviewer[absorbs #151], author, controller[incl. courier-forge-op]). Brief: `/home/cedev2/ce-briefs/playbooks-scaffold-build.md`. dev-3 is NO LONGER on #283.
- **#145 DECISION LOCKED: in-tree `creator-engine/playbooks/`** (mono-repo; CE has no external untrusted writer — contribution via PR/triage, customization via fork; subpath-scoping never the constraint). #151 folded into the reviewer playbook.
- **#152 filed** (dev-4's website copy ticket — remove OpenShell honesty-check + hero headline → "FULL AUTOMATION: FROM IDEA TO WORKING APP") couriered AS ce-dev-4 via held PAT (ADR-0007 model-b live demo; dev-4 contained, got 404 from inside the container).
- **#151 filed** (scoped/rebase-aware re-review procedure + refresh-low-context rule) → folded into #145.
- **▶ NEXT:** merge #283 (rebase if behind) · review dev-3's `ce145-playbooks` PR when up · #284 conflict-rebase by ce-dev-1 after #281 · **cockpit visual checkpoint (Operator)** · dispatch nothing else till checkpoint.
