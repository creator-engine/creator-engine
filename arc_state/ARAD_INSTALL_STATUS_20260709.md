# Arad CE 0.3.4 Install Status — 2026-07-09

Mission brief: `.ce/briefs/HANDOFF_codex_arad_install_20260709.md`
Brief sha256 verified: `5af60e67050af90cdb113a8dc1fa7ff2927cb92879248c459e8570c9f516626c`

Target: `aradsky-vostro-3400` / `100.74.214.78`
Operator ratification channel: Operator physically present with Arad.

## Stage Status

| Stage | Status | Updated UTC | Evidence |
|---|---|---:|---|
| inventory | PASS | 2026-07-09T14:51:54Z | `.ce/state/research/ARAD_REHEARSAL_EVIDENCE_20260709/raw/stage0_inventory_20260709T1452Z.txt` |
| install | PASS | 2026-07-09T14:53:36Z | `.ce/state/research/ARAD_REHEARSAL_EVIDENCE_20260709/raw/stage1_install_20260709T1453Z.txt` |
| doctor | PASS | 2026-07-09T14:54:20Z | `.ce/state/research/ARAD_REHEARSAL_EVIDENCE_20260709/raw/stage2_doctor_20260709T1454Z.txt` |
| onboard | PASS | 2026-07-09T14:56:35Z | `.ce/state/research/ARAD_REHEARSAL_EVIDENCE_20260709/raw/stage3_onboard_20260709T1455Z.txt` |
| launch | PASS after ratified recovery | 2026-07-09T15:04:10Z | `.ce/state/research/ARAD_REHEARSAL_EVIDENCE_20260709/raw/stage4_launch_20260709T1457Z.txt`; `.ce/state/research/ARAD_REHEARSAL_EVIDENCE_20260709/raw/stage4_reap_20260709T1505Z.txt`; `.ce/state/research/ARAD_REHEARSAL_EVIDENCE_20260709/raw/stage4_claude_probe_20260709T1505Z.txt` |
| first-journey | IN PROGRESS — restored; awaiting Arad Goal/Done-when/Change-type | 2026-07-09T16:18:00Z | `.ce/state/research/ARAD_REHEARSAL_EVIDENCE_20260709/raw/stage5_first_journey_20260709T1506Z.txt`; `.ce/state/research/ARAD_REHEARSAL_EVIDENCE_20260709/raw/restore_crash_20260709T1618Z.txt` |

## Stage 0 Inventory Findings

- Host reachable over SSH as `aradsky`; Ubuntu kernel reports `Linux aradsky-Vostro-3400 6.8.0-124-generic`.
- Required base prerequisites present: `git 2.43.0`, `curl 8.5.0`, `ssh-keygen`, `python3 3.12.3`, `node v18.19.1`, `npm 9.2.0`.
- Coding-agent CLIs not currently available on noninteractive PATH: `claude` missing, `codex` missing. `gh`, `pipx`, and standalone `uv` also missing.
- Existing CE install is user-local:
  - `~/.local/bin/ce -> ~/.local/share/creator-engine/bootstrap/venv/bin/ce`
  - `~/.local/bin/cev3 -> ~/.local/share/creator-engine/bootstrap/venv/bin/cev3`
  - explicit version: `0.3.1+91d20efc`
  - active bootstrap venv symlink points to `venv-0.3.1-da44ce6b1bf3cc68e1fad9fedbaae3e67c510465e2f7e03edd58545cfa287cd3`
- `~/.ce-secrets` exists with directory mode `700`; metadata-only check saw `github-bootstrap-token.txt` and `mythos-arad.private-key.pem`, each mode `600`. No secret contents were read, moved, or copied.
- Welcome package exists at `~/ce-welcome`.
- Mythos checkout state:
  - Active repo: `/home/aradsky/ce-mythos/mythos`, origin `git@github.com:chmod735-dor/mythos.git`, branch `main`, aligned with `origin/main` at `43d92bf`.
  - Repo has untracked CE state and install/onboard artifacts from prior 0.3.1 adoption, including `.ce/state/*`, `.hermes/`, `CLAUDE.md`, `ce-install.answers.yaml`, `llms-install.md`, and trust-root/schema files.
  - No `.gitignore` exists in the active repo, so the known 0.3.4 `.hermes` gitignore gotcha is expected during onboard.
  - Secondary stale workspace: `/home/aradsky/ce-workspaces/mythos`, branch `ce/adopt-governance`, HTTPS origin, old grafted head `4ed1cab`; not selected for the live install.

## Install Path Decision

Proceed with the canonical signed one-liner as an upgrade-in-place. The 0.3.4 installer is user-local, inventory-only, and creates/reuses versioned bootstrap venvs under `~/.local/share/creator-engine/bootstrap`; this matches the existing 0.3.1 layout and avoids touching Arad's `~/.ce-secrets` custody.

## Stage 1 Install Findings

- Ran canonical signed installer: `curl --proto '=https' --tlsv1.2 -fsSL https://creator-engine.dev/install.sh | bash`.
- Installer verified signed spec canonical sha256 `535a2650a9621931201531147cf52424287d3b3b0e41612f090e59757880fc8c` against `ce-root-v1` and DNS TXT trust anchor.
- New venv created and linked: `~/.local/share/creator-engine/bootstrap/venv-0.3.4-71e82840f2693ad341e328bfeff2aa8d980d7d88f9e79dd24967a1589f9ee160`.
- `~/.local/bin/ce` and `~/.local/bin/cev3` shims updated.
- Verified installed version: `ce --version` and `cev3 --version` both report `0.3.4+010ef3de`.

## Stage 2 Doctor Findings

- `ce doctor` returned exit code 0.
- Summary: `ce doctor: PASS (repo_root=., version=0.3.4+010ef3de)`.
- Notable skips are expected for this tenant host context: rootless Podman unavailable, brain recall unconfigured, and visible launch harness binary check skipped because visible launch was not requested.

## Stage 3 Onboard Findings

- First `ce onboard --repo-root . --no-launch --yes` refused on the known 0.3.4 `.hermes/` gitignore gotcha:
  - refusal: `RED-G-4`
  - stale guidance observed: `Run ce init --repo-root .`
- Applied only the expected one-line repository hygiene fix: `.gitignore` now contains `.hermes/`.
- Reran `ce onboard --repo-root . --no-launch --yes`; it returned exit code 0 with `ce onboard: OK (install-mode=guided)`.
- Onboard completed doctor, install provenance verification, PATH block, and bootstrap; launch intentionally skipped for the separate launch stage.
- Explicit workflow verification:
  - `.github/workflows/ce-validate.yml` exists but still lacks `merge_group:`.
  - The workflow still installs hash-pinned `creator-engine-validator` 0.3.1 artifacts. This was recorded as tenant workflow drift; no product/tenant workflow fix was improvised during the rehearsal.

## Stage 4 Launch Findings — FAILED / STOP

- Ran `ce launch --backend host --preflight --repo-root . --purpose arad-0.3.4-live-rehearsal --controller-id mythos-arad --host-id aradsky-vostro-3400`.
- Preflight refused with two blockers:
  - `G6-LAUNCH-SEAT-SURFACE-REUSE`: seat surface `.ce/state/dispatches/ce-controller--controller` already has a launched sentinel event and the old `ce-controller` tmux session still exists from 2026-07-03.
  - `RED-G-HARNESS-PATH`: configured Claude harness binary `claude` is not on PATH.
- Follow-up probe found no `claude` or `codex` binary under `$HOME` at max depth 4, and global npm package list is empty.
- Per stop line, the rehearsal is stopped here. I did not run `ce reap once`, install a third-party coding-agent CLI, or mutate old launch state without Operator ratification.

## Operator Decision Needed

Choose the launch recovery path:

1. Install or otherwise make an approved coding-agent CLI available on Arad's host, then rerun launch.
2. Ratify reaping the stale July 3 `ce-controller` launch surface with `ce reap once` before rerun.
3. If this failed rehearsal outcome is accepted as evidence, persistent controller should ticket the missing-harness/prereq drift and stale-surface recovery issue.

## Operator Ratification — 2026-07-09

- Relayed by persistent controller: APPROVED to reap/clear the stale July 3 launch surface with `ce reap` or guided equivalent; record as evidence.
- Operator also clarified Claude Code is installed on Arad's machine and instructed a broader non-login-shell PATH investigation across user-local, npm global, and nvm locations; use full path or fix PATH for launch.

## Stage 4 Recovery + Launch Findings

- Located Claude Code at `~/.nvm/versions/node/v20.20.0/bin/claude`; verified version `2.1.205 (Claude Code)`.
- Added `~/.nvm/versions/node/v20.20.0/bin` to PATH for launch commands.
- Ran `ce reap once --repo-root . --root .ce/state`; it escalated because stale July 3 surface still had live tmux/PID.
- Guided equivalent under Operator ratification:
  - killed stale `ce-controller` tmux session created 2026-07-03.
  - identified stale sentinel wrapper PID `44016` and terminated it with `TERM`; the wrapper wrote an exit event.
  - reran preflight; harness gate passed and stale surface was classified as archivable during live launch.
- Ran `ce launch --backend host --repo-root . --purpose arad-0.3.4-live-rehearsal --controller-id mythos-arad --host-id aradsky-vostro-3400`; command exited 0.
- Verified new visible tmux session `ce-controller` created 2026-07-09 18:03:45 local / 15:03:45 UTC.
- Verified new dispatch event in `.ce/state/dispatches/ce-controller--controller/events.jsonl`; old July 3 surface archived to `.ce/state/dispatches/ce-controller--controller.archived-20260709T150345Z/`.

## Stage 5 First-Journey Status

- Live Claude Code seat is running in tmux session `ce-controller`.
- Sent first-journey starter prompt directing the governed session to ask Arad for:
  - Goal
  - Done-when
  - Change-type
- The session responded in CEO-mode vocabulary and is waiting for Arad's three inputs. No work has begun.

## Stage 5 Visible-Session Incident + Restore

- Reported symptom: Arad's visible CE session disappeared/crashed.
- Inspection at 2026-07-09T16:16Z found no tmux server, but Claude Code daemon/background processes were running.
- CE lifecycle evidence showed the launcher wrapper exited cleanly, not with a crash:
  - `.ce/state/dispatches/ce-controller--controller/events.jsonl`
  - `launched` at `2026-07-09T15:03:45Z`, PID `78714`
  - `exited` at `2026-07-09T16:13:41Z`, `exit_code: 0`
  - `outcome_resolved` remained `unresolved`
- Claude logs showed a transient daemon start at `2026-07-09T16:13:33Z` and a forked/resumed session from the prior transcript:
  - `~/.claude/daemon.log`
  - resumed prior transcript `~/.claude/projects/-home-aradsky-ce-mythos-mythos/6234095a-b192-4e84-84d7-3977ab1d60f1.jsonl`
- Working conclusion: the visible tmux/launcher surface was lost after Claude Code daemonized/resumed cleanly; no CE nonzero crash was recorded.
- Restore action:
  - Preflighted `ce launch` with `--claude-arg=--resume --claude-arg=6234095a-b192-4e84-84d7-3977ab1d60f1`; preflight passed.
  - Relaunched host backend with the same resume args.
  - Verified new tmux session `ce-controller` created at `2026-07-09T16:17:05Z`, pane PID `85733`.
  - Verified pane restored the prior first-journey transcript and is again waiting for Arad's Goal / Done-when / Change-type.
