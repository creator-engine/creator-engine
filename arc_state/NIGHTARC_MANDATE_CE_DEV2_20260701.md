# 🌙 NIGHT-ARC MANDATE — CE-DEV-2 Orchestrator — 2026-07-01 (night)

> Follows the day-arc (D1 forge autonomy PROVEN LIVE, D2 auto-merge LIVE + kill-switch, #709/#710/#711/#712 merged). Open with MEMORY.md + RESUME_STATE_...0745Z.md.
>
> ✅ **BATCH-RATIFIED 2026-07-01 (Operator, full):** ALL grants G-N1..G-N7 GRANTED. D-N1 = **code ≤ work-class M with TWO independent governed reviews (quorum, author≠approver)**; docs XS/S single-review as today. D-N2 = **conveyor FULL auto-gate** (harvest→push→route-review→auto-gate when independent review APPROVES + CI green, within envelope). Drive to completion; auto-halt→Operator on any RESERVED item or safety trip.

## Thesis
**Close the autonomy loop.** The day-arc PROVED the primitives (forge triage apply-mode, docs auto-merge, kill-switch, L7 releases) — but the harvest→validate→push→review→gate→re-dispatch cycle is still driven by hand (the controller). The night-arc converts those proven primitives into a **self-driving governed conveyor**: the fleet ships work end-to-end while the controller only steers + holds the ratify gate. Plus: eliminate the validator friction that taxes every PR, harden the infra for unattended overnight running, and advance brain/onboarding. Protect the live install/pitch path (nothing may break the demo).

## Lanes (highest-leverage first)

### N0 — Board closeout + infra cutover (opening)
- Gate **#713** (triage auto-labeling) — review in flight → merge.
- **#351 LIVE daemon cutover** (DGX→VPS, Restart=always) — deploy/queue-daemon/RELOCATION.md; time when board quiet; ~5-10min no-daemon window; verify a test approval auto-merges on VPS; retire DGX; rollback ready. [RATIFY G-N2]
- **Surface-B strangeLoop** autonomous-approve → run + promote to standing capability. [RATIFY G-N4]

### N1 — CONVEYOR GO-LIVE (headline force-multiplier)
Arm the governed **conveyor daemon** (core shipped #705/#708) so harvest→validate→push→review-dispatch is automated — literally mechanizing what the controller did by hand all day. Wire it to the seat fleet; prove it on the next real seat completion. [RATIFY G-N3 + D-N2 scope]

### N2 — Forge autonomy → work-DRIVING (not just advising)
Triage currently ADVISES. Make it DRIVE: triage-ready-queue → auto-pickup/dispatch loop feeding idle seats; #713 auto-labels live; close-bot standing verification; #376 unscheduled-sweep so nothing is invisible to the arc. [RATIFY G-N6 for triage-driven dispatch]

### N3 — Validator/preflight friction elimination (unblocks everything; parallel across seats)
The exact frictions that taxed the day-arc: **#379** installed-venv refresh (harvests keep hitting stale installed pr_preflight even after the source fix merged), **#382** brain-drift false-RED (onboarding footgun), **#373** subprocess timeouts (no-hang), **#370** test-coupling --pr-body-file local, **#368** CE-native test-coupling gate. Batch across seats — low-risk, high-relief.

### N4 — Infra hardening for unattended running
**#337** dev-3 self-push fix (trapped-work bug) [RATIFY G-N7], **#339** dev-4 libsodium, **#184** VPS tmpfs guard, **#369** Fleet-IaC guard (denylist from SSOT identity-registry).

### N5 — Onboarding + strategic (as capacity)
**#367** speckit init, **#304** ce-ops#63 scrub in contributing guide, **#320** install narration polish, **#166** Knowledge SSOT (brain), **#382** brain fix (also N3).

## Batch-ratification package (see companion decision record; grants G-N1..G-N7 + decisions D-N1/D-N2)
- **G-N1 Standing arc merge authority:** approve (as ce-dev-2, ONLY after independent governed review + full CI green) + merge any PR within envelope = docs + code up to **work-class M**. EXCLUDES privileged.
- **G-N2** #351 live cutover · **G-N3** conveyor arming · **G-N4** strangeLoop standing capability · **G-N5** autonomous saturation-dispatch (probe-not-already-landed FIRST — the #347 lesson) · **G-N6** triage-driven dispatch · **G-N7** #337 live-containment fix.
- **D-N1** auto-merge envelope (docs-only vs code-to-M w/ 2-reviewer quorum). **D-N2** conveyor scope (auto-gate-on-approved vs review-only controller-gates).

## RESERVED — will NOT touch without a fresh nod
External release/publish to users; install.sh / signed release artifacts (release op); Arad/Nitzan external comms; history rewrite; branch-protection / constitution; identity-registry real values; any net-new scope beyond this arc. Auto-halt → Operator on anything reserved or on a safety trip.

## Drive mechanics
3 seats (dev-1 non-contained, dev-3/dev-4 contained — probe ACTUAL paths not lane names; verify not-already-landed BEFORE dispatch). Independent governed review before every gate (author≠approver). Signing = controller's non-delegable act. Conveyor automates intake once armed. Checkpoint + dual-write resume each block. NO seat idle.

## Standing authority carried from day-arc
Merge gate = ce-dev-2 approval → queue-daemon (~120s). Kill-switch = CE_AUTOMERGE_KILL_SWITCH / `ce automerge-kill-switch on`. Auto-halt→Operator.
