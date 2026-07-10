# RESUME STATE — CE-DEV-2 — 2026-07-04 ~11:45Z (day-arc checkpoint, pre-/clear)
> MEMORY.md first. Supersedes RESUME_STATE_CE_DEV2_NIGHTARC_20260704T0845Z.md.
> **Arc SSOT: DAYARC_MANDATE_CE_DEV2_20260704.md** (RATIFIED; incl. ⚠️ priority directive:
> Arad/Nitzan work PARKED below core lanes for THIS arc + the FOLLOWING NIGHT-ARC).

## ⏸️ AWAITING-OPERATOR
**Nothing blocking.** Next Operator gate = CE-410 Re-Arming Evidence Bundle (several slices out).
Low-pri carryover: reviewer cyber-use-case exemption (Haiku workaround banked; hit once today on
NanoClaw research — re-dispatched Haiku+config-framing, worked).

## RATIFIED THIS ARC (all form-echoed on tickets; memories banked)
- **Arc mandate** + 3 Shape answers: autonomous approval IN-SCOPE of dependency retirement;
  docs-class already ratified+armed (tiers narrower than envelope = task A3); code-class per-PR
  until CE-410 9/10 → fresh R1. Harvest-daemon appetite = 1 arc to shadow (FLOOR — Operator
  called it conservative; extend within arc without re-asking). Belt = shadow-first + canary.
- **OneCLI ADOPT-WITH-CONDITIONS** as written (ce-ops#436; memory ce-onecli-adoption-ratified;
  NanoClaw reference topology banked: two docker networks, gateway only bridge, --internal
  egress net; their lockdown flag defaults FALSE → CE's isolation is mandatory+CI-guarded).
- **Slice-8 design** as written (ce-ops#410; SSOT CE410_SLICE8_SPIKE_DESIGN_20260704.md;
  receipt via side-effect-ledger; ephemeral-per-run; slicing 8a→8b→8c→9→10).
- **Engine tier-split** (memory ce-engine-podman-tier-split; spike CE_PODMAN_SPIKE_DGX_20260704.md):
  validation/PCO = rootless podman/crun (DGX-PROVEN, podman now installed on this host);
  seats stay Docker+runsc until ce-ops#439 (gvproxy port). Image engine-agnostic.
- **CLI unification** (ce-ops#440 + design SSOT CE440_CLI_UNIFICATION_DESIGN_20260704.md): ONE
  `ce` command; cev3 retired user-facing (~2-release hidden alias); subprocess-shim shape
  (v1⊥v3 = IMPORT invariant, mount/merge forbidden); naming: v3 onboard→`ce install`, bare
  `dispatch`=journey verb (planner→`ce pickup dispatch-plan`), bare `ce` stays usage (#441).
- **strangeLoop DISARMED** (drift; dev-3 self-review broker → dev; memory banked; re-arm = R1).

## MERGED THIS ARC
#769 ce-432 tenant embedding UX (Arad-path proven non-regressing) · #771 ADR-0014 two-plane ·
#770 N5 worktree-prune (in merge queue at checkpoint — verify merged, then run acceptance demo:
dry-run prune sweep over this host's 20+ stale worktrees). Review loops caught REAL defects in
all four PRs (60s launch stall / prune self-delete class ×2 / walkthrough teaching nonexistent
commands / launcher container-leak-on-timeout) — per-PR review is earning its keep on code.

## BOARD (all seats building; /clear dev-3+dev-4 before NEW dispatch — standing)
- **dev-1** (tmux ce-dev1-orchestrator:2.0): #773 rework — container-leak fix (name foreground
  runs + podman rm -f on TimeoutExpired via injected runner + fake-runner test). PR #773
  CHANGES_REQUESTED awaiting its push. Also holds #772 walkthrough rework (HELD on #440 S1).
- **dev-3** (ce-vps-codex via ssh dev1): ce-440-s1-cli-unification (brief sha 74028091…;
  design transferred to its /var/tmp). Signal: READY-FOR-HARVEST ce-440-s1-cli-unification <sha>.
  Its PRIOR task ce-437-portability-guard (00d9436e) signaled READY and is IN HARVEST
  (worker running at checkpoint-update time; PR + review leg follow). Queue item ① now claimed.
- **dev-4** (ce-dgx-codex local): ce-388-conveyor-discovery — the missing DiscoveryRunner leg
  (daemon core IS on main, disarmed default; recon's "design-only" was WRONG). Brief sha
  ed124f38…. Signal: READY-FOR-HARVEST ce-388-conveyor-discovery <sha>.
- PR #772 walkthrough: CHANGES_REQUESTED, HELD until #440 S1 lands (Operator: fix product first).

## DISPATCH QUEUE (priority per mandate lanes)
① #440 S1 (ce install rename + dispatch-plan nest + 32-verb shim + parity tests) → first free
seat (likely dev-1 after 773 fix) ② CE-410 8b (production sandbox runner on 8a launcher;
rootless podman; promote governance policy record; emit receipt) — after #773 merges ③ belt
shadow-arming A2 (two systemd units on dev1 host; shadow+canary; DevOps-shaped — controller may
run it) ④ automerge tier extension A3 (full ratified docs-class envelope) ⑤ #437 S3 containerize
daemons (encode singleton-LEASE gate requirement + verify deploy/queue-daemon landing first)
⑥ #772 rework post-#440-S1 ⑦ N5 acceptance dry-run post-#770-merge.

## WATCHERS (live at checkpoint — check before re-arming, DEDUPE on sight)
b3ugle6qd PR opens/closes (prior-session, auto-resumed) · biofk6atk PR head/review/checks
(prior-session) · b1ltmk3fi seat-signals dev-1/3/4 (mine) · bb0uytayt wall-daemon log (mine).
Gotcha: prior-session monitors can auto-resume LATE (TaskList showed empty right after /clear,
then old IDs fired) — I stopped my duplicate PR-board watcher; do the same if dups fire.

## MECHANICS GOTCHAS (new this arc)
- Seat-signals false positives ×3: brief-echo lines with literal `<sha>`/`+READY-FOR-HARVEST`
  (diff-render). Real signal = 40-hex. (Encoded as mandatory test fixtures in dev-4's brief.)
- dev-4 herdr dispatch: message can sit in input box looking idle — send Enter AGAIN and
  confirm `Working` before believing it landed (Operator caught one idle miss today).
- Verify recon claims against source: "harvest daemon design-only" was false (conveyor_daemon.py
  on main); "gated by #694" was stale (#694 merged Jun 30; CE_AUTOMERGE_RUN_MODE=ceo is SET —
  the gap is TIER breadth, not arming).
- Wall-daemon monitor delivers stale pre-merge lines late — trust `gh pr view mergedAt` +
  origin/main log, not event order. "already queued" + in_progress merge_group Validate = healthy.
- Rework harvests: cherry-pick ONLY new seat commits onto live PR head (seat history diverges
  after first harvest rebase); verify pre-rework content byte-identical first; staging branch
  name MUST equal carrier slug (rename gotcha hit again).
- Tenant repo access: mint mythos-ce App installation token via JWT+PEM (~/.ce-keys/mythos-ce…),
  never overwatch PAT. Worked clean today.
- Podman 4.9.3 + uidmap + slirp4netns now INSTALLED on this DGX host (spike artifact).

## KEY FILES THIS ARC (.ce/state/research/ unless noted)
DAYARC_MANDATE_CE_DEV2_20260704.md (arc SSOT) · CE410_SLICE8_SPIKE_DESIGN_20260704.md ·
CE440_CLI_UNIFICATION_DESIGN_20260704.md · CE_PODMAN_SPIKE_DGX_20260704.md ·
CE436_ONECLI_DILIGENCE_20260704T052354Z.md · tmp/threads-20260704/ (10 consolidated thread docs
+ INDEX, Operator-requested). New tickets: ce-ops#439 (gvisor-rootless port), #440 (CLI unify,
decision SSOT), #441 (bare-ce product question). Claims: ce-437-adr-two-plane (done),
ce-437-portability-guard, ce-388-conveyor-discovery, ce-410-s8a-shared-launcher,
ce-438-complete-walkthrough (held).
