# RESUME STATE — CE-DEV-2 · 2026-06-25 · 🏗️ RELEASE-WAVE LANDED + ARM BLOCKED ON OPENBAO ADMIN-RECOVERY · V18

**WHERE:** CE-DEV-2 controller, `cedev2` on DGX `spark-b824`, cwd `/home/cedev2/creator-engine`, Opus 4.8 high. **SUPERSEDES V17.** READ FIRST: this + MEMORY.md + [[ce-openbao-admin-recovery-blocked]] + [[ce-controllers-proactive-pickup]] + [[ce-fork-credential-drift-approval-leak]] + [[ce-herdr-dispatch-landing-misread]].

## 🔴 RESUME ACTIONS (in order)
1. **Re-sync:** `git -C ~/creator-engine fetch origin` (main was `9aa1af7c`); poll the 3 seats; check #452 merged (was queuing) + the trio #444/#445.
2. **IMMEDIATE NEXT TASK = "A": dispatch a research worker on OpenBao 2.5.5 root-recovery** (see ARM section). Operator approved A. This is the gate to arming.
3. Drive the release wave to completion → **run the N6 clean-room ship/slip gate** once N3 (#452) merges (the full N1–N6 set will be on main).
4. Keep the 3 seats saturated (no reserve); extract any parked contained-seat work → PRs.

## 🔐 THE ARM — BLOCKED ON OPENBAO 2.5.5 ADMIN-RECOVERY (the big delta)
Goal was: arm the credential-wall (#440/#446, merged dormant). Status after deep investigation this session:
- ✅ **OpenBao bundle passphrase RECOVERED + SECURED** at `~/.ce-keys/openbao-init-bundle.pass` (0600, 13 bytes; **Operator provided it from the laptop**). It decrypts `/home/ce/open_bao.json.gpg` (the `bao operator init` output: 5 unseal shares b64, threshold 3, recovery_keys, root_token). Relocation gap CLOSED.
- ❌ **`bao operator generate-root` → `{"errors":["unsupported operation"]}`** on this **OpenBao 2.5.5** server (confirmed via raw API; seal=plain shamir, audit device live+writable — NOT an audit-fail-closed artifact; generate-root genuinely not implemented/enabled on this build).
- ❌ **Bundle `root_token` → 403 (revoked)** — as the golive note said.
- Per-dev AppRoles (`ce-dev-1..4`) are scoped (no policy-write). **Net: can unseal, CANNOT get an admin token → cannot create the wall policy/secret → arm blocked.** Vault is currently **un-administerable** (unsealed+fine for scoped reads, but no admin/root recovery). NOT urgent (broker/secret-zero wiring was DEFERRED at golive — nothing load-bearing depends on it yet).
- **NEXT (A, Operator-approved):** research worker on *OpenBao 2.5.5 root recovery when generate-root is unsupported* (recovery-keys path? config flag re-enabling generate-root? OpenBao-specific operator procedure?). Non-destructive. Then arm as fast-follow. Last-resort = re-key/re-init in a window (viable since nothing load-bearing yet, but destructive).
- **SECOND-ORDER ARM CAVEAT (even after admin recovered):** arming enforces capability-checks on the LIVE integrator daemon. If the capability-mint-on-approval flow (transport deputy / #242/#243 self-push-review) isn't operational, arming → fail-closed → blocks the merge queue. So before flipping: verify the mint flow is live + the queue is quiet. **Standing arm authorization holds** (Operator's "finish autonomy/land it" + drove the passphrase recovery): arm once admin-recovered + round-trip verified + queue-safe; report at the flip.
- **OpenBao facts:** `BAO_ADDR=https://ce-dev-1.tailf3cfef.ts.net:8200` (alt `https://100.72.252.20:8200`); `BAO_CACERT=/usr/local/share/ca-certificates/ce-openbao-ca.crt`; `CE_OPENBAO_KV_MOUNT=ce-kv`; wall ref (per #456 predicate) = mount `ce-kv` path `forge/approval-capability/wall` field `signing_secret` purpose `approval-capability-wall` owner-ref `controller:integrator`. Arming runbook (dev-1) merged: `docs/devops/openbao-approval-wall-arming.md`. Decrypt: `cat ~/.ce-keys/openbao-init-bundle.pass | ssh dev1 'sudo -u ce gpg --pinentry-mode loopback --passphrase-fd 0 -d /home/ce/open_bao.json.gpg'`.

## 🖥️ ACCESS (gained this session)
- **VPS (dev1):** `ssh dev1` = user `ce-dev-1`; I have **passwordless `sudo -u ce` AND `sudo` (root)** there — that's how I read/decrypt `/home/ce/open_bao.json.gpg` + run `bao`.
- **Laptop:** tailnet node `ce-dev-2` (100.106.203.52), owner `neckar@`, **local unix user = `nefarious`**. Reach via **Tailscale SSH** `ssh nefarious@100.106.203.52` (NO `-i` key — identity-based; **check-mode**: first session needs Operator to approve a `https://login.tailscale.com/a/...` URL). DGX pubkey is authorized-identity. The laptop is where I'd operated pre-relocation; secrets I "stored on the laptop" live under `nefarious`'s `~/.ce-keys` / GUI store.

## 📦 RELEASE WAVE (N1–N6) — NEARLY COMPLETE
main `9aa1af7c`. **MERGED:** N1 (#449 install dep soft-inventory), N2 (#447 docs ce→cev3), N5 (#451 fault-injection failsafe), N6 (#453 clean-room scaffold), statusline (#450), OpenAI-switch runbook (#454), arming runbook (#455), #239 allowed_refs (#456), #244 .claude/agents roles (#457). N4/D4 = probed (mythos-ce App, installation_id 141552951, `~/.ce-keys/mythos-ce-app.env`). **STILL QUEUING:** **N3 (#452 first-value script)** — APPROVED, in merge queue.
- **NEXT after N3 merges:** run **N6 = the clean-room rehearsal SHIP/SLIP gate** (`scripts/clean-room-rehearsal.sh`, live run is controller-driven, needs N1–N5 merged ✓ + N3). Ship v0.3.0 IFF green. The N6 scaffold's first_value/update stages are TODO-guarded — wire them to the N3 script for the live run.
- **Merge mechanic:** GitHub **merge queue** is configured (branch protection: required check "Validate governance artifacts" + 1 review). Integrator daemon enqueues approved+green via `gh pr merge --auto`; queue re-runs CI per PR + merges SERIALLY (~4min each, looks slow/"UNKNOWN" mid-queue — NOT a stall). Don't manually merge (races the queue). I approve as **ce-dev-2** (`~/.ce-keys/ce-dev-2.pat`); integrator merges.

## 🛰️ FLEET (verify on resume — codex seats)
- **dev-1** (VPS tmux `ce-dev1-orchestrator:2.0`, self-pushes): did OpenBao standup → #455 (merged). Likely idle → re-task (no reserve).
- **dev-3** (VPS contained `0008529f5a0a`, via ssh dev3): last task = **self-pick** next ready ce-ops ticket (proactive-pickup). **VERIFY what it picked** + its branch/SHA (extract if done). Prior done+extracted: N5, N3, #239.
- **dev-4** (DGX contained `ce-dgx-codex`, local sudo docker): last task = **#244 injection** design+scaffold (branch `ce244-bootstrap-injection`, SSOT-sourced harness-uniform controller bootstrap — DESIGN+preview-only, don't clobber live CLAUDE.md). **VERIFY done + extract → PR.** Prior done+extracted: N1, N6, #244 agents.
- **Dispatch lesson [[ce-herdr-dispatch-landing-misread]]:** the codex input box clears on submit (looks idle but is Working); verify "Working" indicator not the box; `tab to queue message`=busy don't re-send; don't `/compact`+queue-task (drops). Contained dispatch: `ssh devN bash -s <<REMOTE` heredoc (avoids quoting hell); paren-free pointers.

## 🎯 THE DETERMINISTIC-SUBSTRATE ARC (#163/#166/#244 — Operator-emphasized this session)
Controller-divergence gap PROVEN + ticketed: codex controllers grounded by injected `~/.codex/AGENTS.md` FOREMAN directive (names roles); Claude-Code controller boots off a bare SpecKit `CLAUDE.md` stub + (was) empty `.claude/agents` → improvises. Fix = SSOT (#166) generates per-harness bootstrap identically. **#457 (.claude/agents role defs: architect_research/implementer/reviewer/verification + README, grounded in spec005 §d.2) MERGED.** dev-4 building #244 injection (generator). Evidence on #163 + #244. **Going forward: map sub-agents to CE roles (architect_research/implementer/reviewer/verification), don't improvise.** [[ce-worker-tier-definition-gap]]

## 🔀 TRIO (still open, controller-handled — low priority vs ship)
#444 (A4 herdr reach-plane, ce-ops#237) — needs `ce herdr` README/as-built-inventory reconciliation (CI-fail) + rebase. #445 (#233 verify-by-reaction, CONFLICTING) — rebase. Both share herdr_session.py history. Diffs cached `~/creator-engine/tmp/pr44{4,5}.diff`. Mechanical/controller work; deprioritized behind the ship.

## 🛠️ OPS ESSENTIALS
- **gh:** `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. Approvals = `ce-dev-2.pat`. ISSUES=ce-ops; CODE/PRs=creator-engine.
- **Review model (proven):** read-only `reviewer`-role worker returns verdict → I approve+submit → integrator merges. NEVER credentialed forks for gate-adjacent work.
- **Carrier (ce carrier stale):** `PYTHONPATH=validators ~/creator-engine/.venv/bin/python3` + `carrier_gen.write_carriers(CarrierSpec(head_ref=<branch>, issue, title, kind, scope, body, base="origin/main"))`. Slug MUST = head-ref. Commit source first → regen carrier → amend → verify `git diff --name-only origin/main..HEAD` == manifest path-set.
- **Extraction (contained seat→PR):** `docker exec <ctr> git format-patch $(merge-base origin/main <branch>)..<branch> --stdout` → host patch → worktree off origin/main → `git am` → carrier → push → `gh pr create` (body needs `- **Declared work class:** <tiny|story>` per G5 floor; ~400-line boundary). venv pytest = `~/creator-engine/.venv/bin/pytest`.
- **Gate daemons:** integrator + review-pickup live on DGX; logs `~/.ce/logs/{integrator,review}-daemon.log`.
- **Background forks/sub-agents DIE on /clear**; the OpenBao bundle passphrase + all keys persist in `~/.ce-keys/`. Re-establish workers on resume.

## 🎫 OPEN
#191 release epic (N1-N6, N3 #452 last to merge → then N6 ship gate) · #239✅ #244 (agents✅, injection dev-4) · #163/#166 SSOT arc · #455 arming runbook✅ · arm blocked on OpenBao admin-recovery (task A next) · #245 openai-switch runbook · trio #444/#445.
