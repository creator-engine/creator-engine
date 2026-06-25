# Switching the codex fleet between OpenAI Pro subscriptions

Status: **READY — gated controller/Operator action.** This runbook is the
durable SSOT for moving the codex fleet (dev-1, dev-3, dev-4) from one OpenAI
Pro subscription ("acct A") to another ("acct B"), and back. We do this
**often** (to spread weekly usage across two pools), so the mechanics live here
and in `scripts/switch-openai-account.sh` — not in scrollback or tribal memory.

Companion docs (read these for the relaunch authority semantics):

- `docs/operations/SEAT_LAUNCH_GOVERNANCE_RUNBOOK.md` — canonical seat launch.
- `[[ce-seat-relaunch-canonical-launch-only]]` — **NEVER** relaunch a contained
  codex seat via raw `codex` / `ssh`+`tmux`; that breaks the bubblewrap (bwrap)
  sandbox and leaves a dead exec. Relaunch ONLY through the canonical launcher.

The helper script automates the **mechanical** parts (pre-stage login, on-disk
`auth.json` swap, and printing the exact per-seat relaunch plan). It never
executes a contained relaunch and never echoes a token — those steps are
operator/controller-gated.

---

## 0. Ground truth — why a switch is not free

These are load-bearing facts. The procedure below exists *because* of them.

1. **No zero-restart switch.** codex reads its auth **once** at startup and
   holds the token in memory for the life of the process. A running seat does
   **not** notice a new `auth.json`; it adopts the new account only on
   **RESTART**.

2. **Limits are per-account.** The weekly/usage pool is per OpenAI account.
   Switching accounts = a **fresh pool** — that is the entire point of keeping
   two subscriptions.

3. **Swapping `auth.json` on disk is non-disruptive to a running seat.** Because
   the token is already in memory (fact 1), copying acct B's `auth.json` over
   the file does **not** disturb the running process. This is what makes
   **pre-staging** acct B safe to do at any time, ahead of the drain.

4. **codex sessions persist on disk.** After a clean stop you can
   `codex resume <SESSION_ID>` to rehydrate the conversation. Resume is
   **imperfect on long / auto-compacted contexts**, so always capture a 1-line
   handoff before stopping and be ready to re-seed instead of resume.

5. **Containment changes the relaunch path, not the swap path.**
   - dev-3 (VPS) and dev-4 (DGX) are **contained**: their gVisor/runsc
     container **bind-mounts the host codex home read-write**, so the
     `auth.json` swap happens **host-side** exactly like a normal host. But the
     seat process MUST be relaunched through the **canonical launcher**
     (`ce launch` / `deploy/{vps,dgx}-runsc/run-*-runsc.sh`) — never raw
     `codex` or `ssh`+`tmux` (breaks bwrap, see companion doc).
   - dev-1 is **non-contained**: swap host-side, then relaunch `codex` in its
     own tmux pane.

---

## 1. Topology & paths (verify before acting)

| Seat  | Host                | Contained | Codex home (acct A)        | Relaunch path                                                  |
|-------|---------------------|-----------|----------------------------|----------------------------------------------------------------|
| dev-1 | Hetzner VPS (`ce-dev-1`) | no   | `~/.codex` (ce-dev-1)      | tmux pane `ce-dev1-orchestrator` %0 — relaunch `codex` inline  |
| dev-3 | Hetzner VPS (`ce-dev-3`) | yes  | `~/.codex` (ce-dev-3)      | `deploy/vps-runsc/run-vps-runsc.sh --harness codex` (canonical)|
| dev-4 | DGX Spark (`cedev4`)     | yes  | `/home/cedev4/.codex`      | `deploy/dgx-runsc/run-codex-runsc.sh` (canonical)              |

`CODEX_HOME` (or the launcher's `CE_VPS_CODEX_HOME` / `CE_DGX_CODEX_HOME`) is the
directory; the file we swap is `<codex-home>/auth.json`. Confirm the live path
per host before swapping — do not assume.

---

## 2. Pre-stage acct B (once per host, non-disruptive)

Done **ahead of time**, while seats keep running on acct A (fact 3). This logs
acct B into a **parallel** codex home so its `auth.json` is ready to copy in.

```bash
# Host-side, per host. Device-auth (headless) login into a parallel CODEX_HOME.
scripts/switch-openai-account.sh pre-stage ~/.codex-acctB
# (equivalently: CODEX_HOME=~/.codex-acctB codex login)
```

Follow the device-auth URL/code with **acct B** credentials. When it completes,
`~/.codex-acctB/auth.json` exists and is the acct B token. This file stays put;
the per-seat swap copies *from* it. Re-run only when acct B's credentials roll.

> The helper never prints token contents. The device-auth flow prints its own
> URL/code (that is OpenAI's UX, not a secret leak).

---

## 3. Per-seat switch — drain to a task boundary

Do **one seat at a time**, staggered (§4). For each seat:

1. **Record session + handoff.** In the seat: `/status` → copy the
   `SESSION_ID`. Write a 1-line handoff of what it was mid-task on (resume can
   be lossy on long/compacted contexts — fact 4).

2. **Drain to a task boundary.** Let the current work-unit reach a clean stop
   (committed / reported). Do not stop mid-edit or mid-push.

3. **Clean-stop codex.**
   - dev-1: stop `codex` in its tmux pane (let it exit; do not `C-c` mid-op).
   - dev-3 / dev-4 (contained): stop the seat **through its canonical
     lifecycle** (stop the container / `ce` seat). Never `kill -9` the bwrap.

4. **Swap `auth.json` host-side** (backs up acct A first, then copies acct B):
   ```bash
   scripts/switch-openai-account.sh swap <target-codex-home> ~/.codex-acctB
   # e.g. dev-1/dev-3:  ... swap ~/.codex ~/.codex-acctB
   #      dev-4:        ... swap /home/cedev4/.codex ~/.codex-acctB
   ```
   The helper refuses if either `auth.json` is missing, and writes a timestamped
   backup (`auth.json.bak.<UTC>`) before overwriting. To switch **back**, swap
   the saved acct-A home in, or restore the backup.

5. **Relaunch (canonical for contained).** Get the exact command:
   ```bash
   scripts/switch-openai-account.sh plan dev-1   # or dev-3 / dev-4
   ```
   - dev-1: run the printed `codex` in its tmux pane.
   - dev-3 / dev-4: the printed canonical launcher command is **operator/
     controller-gated** — the helper prints it but does NOT execute it. Run it
     through the governed launch path. **Raw `codex` / `ssh`+`tmux` is
     forbidden** (breaks bwrap).

6. **Rehydrate.** `codex resume <SESSION_ID>` from the recorded id, or re-seed
   from the handoff brief if resume is incomplete.

7. **Confirm.** In the seat: `/status` shows the **new account**, and `/usage`
   shows a **fresh/independent pool**. If it still shows acct A, the seat did
   not actually restart against the new `auth.json` — go back to step 3.

---

## 4. Order & staggering

**dev-1 (canary) → dev-3 → dev-4.** Never restart two seats at once: confirm
each seat is back up and on acct B (step 7) before draining the next. dev-1 is
non-contained and the simplest blast radius, so it validates the swap first;
dev-4 (DGX, strongest box / hardest work) goes last.

---

## 5. Verify the pools are independent (throwaway check)

Before relying on the second subscription, confirm acct B's pool is genuinely
separate — burn a throwaway turn on the freshly-switched canary and read
`/usage`. The acct B pool should be **untouched** by acct A's prior week's
consumption. If both accounts share a pool, they are the **same** OpenAI
subscription (or org) and switching buys nothing — stop and re-check the acct B
login.

---

## 6. Quick reference

```bash
# Once per host, ahead of time (non-disruptive):
scripts/switch-openai-account.sh pre-stage ~/.codex-acctB

# Per seat, at the drain boundary (host-side):
scripts/switch-openai-account.sh swap <codex-home> ~/.codex-acctB
scripts/switch-openai-account.sh plan <dev-1|dev-3|dev-4>   # prints relaunch + resume
# then: relaunch (canonical for contained) + codex resume <SESSION_ID> + /status,/usage
```
