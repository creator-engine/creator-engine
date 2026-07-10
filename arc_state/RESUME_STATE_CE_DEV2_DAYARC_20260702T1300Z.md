# RESUME STATE — CE-DEV-2 Orchestrator — 2026-07-02 ~13:00Z
> Open MEMORY.md first. ARC = DAYARC 20260702. Supersedes 1210Z_CKPT.

## 🔴 LIVE BOARD (verify on resume — do NOT trust as merged)
1. **#740** ce-388-payload-data-only: round 3 harvested+pushed (head 9eb5f2b7), fresh review APPROVE,
   **approved by ce-dev-2 12:3xZ**, in merge queue position 1 AWAITING_CHECKS at 12:55Z. CONFIRM MERGED.
   Non-blocking residuals recorded on ce-ops#388 (untested unsupported-item-type branch; discovered_count
   semantic). After merge: ADR-0004 independent security review (distinct venue) = precondition for G-N3.
2. **#742** ce-402-preflight-failclosed: **DRAFTED by controller to stop a queue-fail loop.** Merge-group
   Validate failed 2× on test_ce_brain_drift — brain assertions d1b-01/-42/-43 (records 41/97/99) pin
   evidence_sha256 of pr_preflight.py; #739 landed them on main AFTER approval; branch modifies that file.
   Diagnosis commented on PR. **dev-4 dispatched round-2 fix** (merge origin/main into branch + append
   superseding brain records via documented supersede mechanism; brief /var/tmp/ce-402-brain-drift-fix-BRIEF.md
   in ce-dgx-codex, sha cd19cc54…). On READY-FOR-HARVEST ce-402-preflight-failclosed <sha>: harvest
   (bundle out via `docker exec cat` — docker cp BROKEN on runsc, see new memory), preflight, push,
   **UNDRAFT #742** (gh pr ready), re-approve as ce-dev-2 on new head, strip stale ce-approval-capability
   marker line from body if daemon skips (ce-ops#404).
3. **dev-3** dispatched ce-369-denylist-from-ssot (REDO of rejected #729). Brief
   .ce/briefs/ce-369-denylist-from-ssot-BRIEF.md (sha 1e32a82f…, copy in container /var/tmp). Key design:
   SHA-256-at-rest artifact + scheduled freshness workflow `.github/workflows/identity-denylist-freshness.yml`
   referencing `secrets.CE_OPS_READ_TOKEN`. **Controller follow-ups on harvest: (a) provision
   CE_OPS_READ_TOKEN org/repo secret (fine-grained PAT, ce-ops read-only), (b) run
   scripts/gen_identity_denylist.py --write against ~/ce-ops/infra/identity-registry.yaml to regenerate
   the artifact from the live registry (seat only migrates the hand list 1:1).** Acceptance bar = #729's
   two blocking findings: irreversible-at-rest + CI-enforced freshness (NOT manual helper).
4. **dev-1** dispatched ce-ops#395 items 1+2 ONLY (release-bump --commit mode + delete
   release_orchestrate.py). Brief /var/tmp/ce-395-bump-to-main-BRIEF.md on VPS (sha e8a456a6…). dev-1
   self-pushes its PR; watch for `PR-OPENED <n> <sha>` in its pane. Item 3 (auto-tag timing) = ⏸️ Operator;
   item 4 (token docs) still open on ticket.
5. Watchers: 3-seat b7wo8reit (5m; STILL false-fires on d3 stale scrollback READY-FOR-HARVEST — anchor
   pattern when re-arming) + PR-board b0lfdc6qd.

## ⏸️ AWAITING-OPERATOR (surface FIRST after /clear)
1. ce-ops#390 GitHub Support portal submission (staged on issue, ~2 min org-owner click).
2. ce-ops#395 item 3: auto-tag timing policy (bump-as-trigger vs marker-gated) — blocks arming the full
   bump→tag chain (item 1 code lands inert without it).
3. With evidence: G-N3 arming (#740 merge + ADR-0004 security review + dry run) · #397 Phase B ADR.

## ⏭️ NEXT AFTER BOARD CLEARS
Prune worktrees: wt-739-review, wt-742-review, wt-ce388-harvest (after #740 merge), wt-369-research
(after #369 harvest). Dispatch queue: #398 A3+A5 · #399 slices · #396 · #401 · ce-ops#404 fix · #400 seat
toolchain · D1b batch 2 (NOTE: touches .ce/brain/assertions.yaml — serialize vs #742 fix, same file).
ce-dev-2 re-review queue empty. Main checkout sits on ce-release-0.3.1-rc2 (behind main, lacks newer
files) — use .ce/wt-369-research (pinned origin/main 9d7ed64dd) or fresh worktrees for main-tree reads.

## HOT MECHANICS (delta vs 1210Z checkpoint — that file's list still valid)
- **runsc containers: docker cp BROKEN** → `sudo docker exec ce-dgx-codex cat <file> > <dest>`; ref-range
  bundles not full-history. Memory: ce-runsc-docker-cp-stream-via-exec-cat.
- **herdr on VPS lives INSIDE ce-vps-codex** (not on dev1 host): `ssh dev1 'sudo docker exec ce-vps-codex
  env HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock herdr …'`. dev-4 local: same via ce-dgx-codex.
- Enter-retry needed on BOTH dev-3 (herdr) and dev-1 (tmux) dispatches today: send → grep Working → if
  absent, second Enter. Worked every time.
- To HOLD a PR from the daemon: GraphQL convertPullRequestToDraft (used on #742); undraft = gh pr ready.
- gh repo owner = creator-engine/creator-engine (NOT chmod735/…).

## ⚠️ 13:00Z+ DELTA — D1B PIN FREEZE (supersedes board items above)
- **SYSTEMIC: every file hash-pinned by a -v2 brain assertion is FROZEN for merges** until
  ce-brain-chained-supersede (dev-4, in flight) merges — chained supersede unrepresentable (ce-ops#407,
  filed + scope-escalated). Pinned hot files: pr_preflight.py (d1b-01/42/43), forge/integrator_belt.py
  (d1b-10/11/12), validators/pyproject.toml (d1b-39), wheelhouse/SHA256SUMS, ce_brain_drift.py,
  install_spec_signature_guard.py, work_sizing_floor.py + workflows/docs.
- **#740 ALSO failed merge-group on this** (d1b-10/11/12 via integrator_belt.py) → DRAFTED + diagnosed
  in PR comment. #742 already drafted same class.
- **dev-4 now on precursor branch ce-brain-chained-supersede** (brief /var/tmp/ce-brain-chained-supersede-BRIEF.md
  sha b8feab60…; brain_runtime.py NOT itself pinned → precursor safe to queue). Its ce-402 worktree preserved.
- **dev-3 steered mid-task**: expected d1b-39 drift RED on preflight → will emit
  `BLOCKED-ON-PRECURSOR ce-369-denylist-from-ssot <sha>` instead of READY-FOR-HARVEST (watcher greps
  READY-FOR-HARVEST only — check for BLOCKED-ON-PRECURSOR manually).
- **UNBLOCK SEQUENCE (serialize — all touch assertions.yaml, chain-hashed):** 1) precursor: harvest →
  review → approve → merge. 2) dev-4 resumes ce-402 fix (supersede d1b-01/42/43) → undraft #742 →
  re-approve → merge. 3) #740: supersede d1b-10/11/12 on its branch (dev-4) → undraft → re-approve →
  merge. 4) dev-3/#369: merge main + supersede d1b-39 → harvest. dev-1/#395 paths NOT pinned → unaffected.
- Design follow-up parked on #407: per-edit supersede obligation needs tooling (`ce brain repin`) or
  probe-scoped pins — else D1b froze core files by stealth.
