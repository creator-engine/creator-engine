# RESUME STATE — CE-DEV-2 Controller · 2026-06-20 (morning arc + computer-use dogfood)

**WRITTEN BY / WHERE:** CE-DEV-2 controller as `cedev2` on the **DGX `spark-b824`** (aarch64, tailnet 100.100.105.50), cwd `/home/cedev2/creator-engine`, Opus 4.8 effort-high. Read this + `MEMORY.md` first.

## SEAT → HOST → REACH (all confirmed reachable this session)
- **dev-1** codex ctrl, VPS — `ssh ce@100.72.252.20` → tmux `ce-orchestrator`. Authors `cedev1vps-cmd`.
- **dev-3** codex ctrl, VPS — `ssh ce@100.72.252.20` → `sudo -n -u ce-dev-3 tmux ... -t dev3-onboard`. Authors/reviews `ce-dev-3`.
- **dev-4** codex ctrl, CONTAINED gVisor, LOCAL — `ssh cedev4@localhost` → tmux `dev4stage1`. Authors `cedev4vps-coder`. NEVER C-c.
- **Laptop (ce-dev-2 host)** = `nefarious@100.106.203.52` (Tailscale SSH; user **nefarious**). Computer-use venue. tmux **`ce devops`** (note the SPACE) has GUI (DISPLAY=:0, Wayland) but NO DBUS_SESSION_BUS_ADDRESS.
- **Me** dev-2 = `cedev2` (DGX). Push wired via `~/.ce-keys/git-credential-ce-forge.sh` (App-token helper, repo-scoped). Merge as chmod735 via `~/.ce-keys/overwatch.env` (`CE_OVERWATCH_PAT`).

## ▶ IMMEDIATE NEXT ACTION — dispatch the ratified arc (#144)
Arc **ce-ops#144 RATIFIED**. Seats reachable. **Dispatch (post `🔒 in-compose` lock + check first per [[ce-check-parallel-tracks]]):**
- **W4** #121 ARM wheelhouse → **dev-4** (`dev4stage1`, local) — pitch-critical; strongest machine.
- **W2** #142 computer-use authority envelope (scoped phase-1: schema+contract+validator-check+worker-harness contract w/ today's substrate learnings) → **dev-3** (`dev3-onboard`).
- **W3** #135 OpenBao broker / secret-zero wiring (response-wrapped SecretID mint per dev) → **dev-1** (`ce-orchestrator`).
Each: ratified-flow (build→green→PR→peer-review→I-merge-as-overwatch). Controller holds merge gate.

## 🔄 W1 IN FLIGHT (Operator-driven — do NOT send keys to laptop tmux)
**#143 computer-use rename loop.** Interactive **claude (Sonnet 4.6, --dangerously-skip-permissions)** in laptop tmux `ce devops`, cwd `~/projects/creator-engine`. It picks up #143, renames 4 GitHub accounts via browser, then opens the **re-point PR** (`.github/CODEOWNERS` v2 + `tenants/` SSOT + registry #137). **Operator is driving it directly + completing per-account GitHub sudo-mode 2FA/passkey** (each rename triggers re-auth — controller correctly HALTS+escalates, never bypasses). **My job when it lands: review + merge the re-point PR.** Renames: `cedev1vps-cmd→ce-dev-1`, `ubuntuaws745-cmyk→ce-dev-2`, `cedev4vps-coder→ce-dev-4`, `chmod735→ce-overwatch` (ce-dev-3 already conformant).

## 🧩 COMPUTER-USE SUBSTRATE — what works (feeds #142 + W1.5)
- Browser MCP = **`ce-browser` = `chrome-devtools-mcp --autoConnect`** → attaches to the Operator's LIVE authed Chrome (after they enable `chrome://inspect/#remote-debugging` → exposes 127.0.0.1:9222). This is THE working path.
- **DEAD ENDS (don't retry):** (1) `chrome-devtools-mcp` plugin default → fresh unauthed profile (now DISABLED); (2) `--remote-debugging-port` on default profile → Chrome refuses ("non-default data dir"); (3) playwright `--user-data-dir`=real profile → HANGS on gnome-keyring (no DBUS in tmux); (4) `--browserUrl http://127.0.0.1:9222` → the chrome://inspect mechanism doesn't expose classic `/json`.
- claude auth on laptop: token had expired w/ empty refresh; Operator re-`/login`'d → now valid (Max). `~/.npm-global/bin` PATH; playwright-core installed at `~/.npm-global/lib/node_modules/playwright-core`.
- ⚠️ pkill self-match footgun: bracket the pattern (`pkill -f "[/]opt/google/chrome/chrome"`, `[c]e-...`) or it kills the SSH shell.

## ⏸️ W1.5 (gated on W1) — App renames, scheme APPROVED
Rename GitHub Apps for `ce-*` uniformity, **UI-only → rides the #142 computer-use controller** (2nd dogfood). Scheme: `creator-engine-forge`→**`ce-forge-dev-2`**, `ce-forge-dev1`→**`ce-forge-dev-1`** (+ dev-3/dev-4 if present), automation App→**`ce-devops`**. App ID/client ID/installation ID/PEM all STABLE (mint scripts unaffected). **Only blast radius = `<slug>[bot]` login** → audit branch-protection bypass/CI/`tenants/` refs first; CODEOWNERS currently has no bot. First: ENUMERATE actual org Apps (registry #137).

## ⏸️ W5 (with Operator) — OpenClaw deep-dive (VPS tmux `ce-research-openclaw`; report `.ce/state/research/OPENCLAW_CE_RESEARCH_20260619.md`) + dev-4 container-push doctrine (#128-adjacent: contained worker push vs commit-and-signal).

## ACTION ITEMS / OPS
- ⚠️ **Rotate leaked token `ghp_…1XTgpz`** (the #143 controller printed it to transcript).
- Tickets: **#142** (envelope schema gap), **#143** (rename exec), **#144** (morning arc, RATIFIED). #275 OpenBao merged; night arc #139 wrapped.
- Crons: all cancelled (interactive).
