# RESUME STATE — CE-DEV-2 Orchestrator — 2026-06-28 ~10:20Z — 9 MERGED; brain ACTIVATED (keyword); relaunch GREEN-LIT

> NEWEST. Open this + MEMORY.md FIRST. Supersedes 1005Z.
> ⭐ STANDING ROLE: OVERARCHING ORCHESTRATOR — drive via seats/restricted workers, NEVER inline build. Each seat (me incl.) = born-a-foreman (multiple file-disjoint tickets; controller ensures parallel-safety via territory-map).

## AUTH
overwatch: `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. Approve as ce-dev-2: `GH_TOKEN=$(cat ~/.ce-keys/ce-dev-2.pat) gh pr review <n> --approve`. Merge: `gh pr merge <n> --auto` (NO strategy flag). ce-root-v1 = ~/.ce-keys/ce-root-v1{,.pass,.pub}.

## 🎯 OPERATOR PRIORITIES (28 Jun — ENGINE-FIRST; onboarding ~6h out, OPPORTUNISTIC)
1. **Forge/fleet automation** (Steinberger §5, throughput-engine lead): #291 auto-merge ✅MERGED(#610) · #341 AutoReview run_mode (dev-3, in flight) · #295 agent-AGENTS.md (dev-1→PR#611, in review) · #34 forge-side (queued).
2. **Company brain** UTMOST (ce-ops#79): Slice A ✅ACTIVATED (keyword recall); EmbeddingGemma install in flight for SEMANTIC recall. Posture RATIFIED = **product feature** (F5 MCP surface = CE product feature + NVIDIA-pitch exhibit, per-install user-scoped corpus — downstream).
3. **Convert dev-1 & dev-4 to contained** — ONLY AFTER contained-parity verified (needs a parity-verification lane first).
4. **Relaunch dev-2 governed** via `ce launch` — GATE CLEARED (ce244 merged); Operator may relaunch anytime → resume from THIS checkpoint. Background workers don't survive relaunch (seats do); relaunched session reconciles from checkpoint + live board.

## ✅ MERGED TODAY (9): #604/#605/#606/#592/#603/#607/#608/#609(ce244 RELAUNCH-GATE)/#610(CEO-mode auto-merge classifier — Steinberger top bet)

## 🔴 IN-FLIGHT (all parallel-safe, territory-checked)
- **PR #611** (ce-ops#295 annoyance→tool + agent-AGENTS.md, dev-1 self-pushed, tiny docs/config 5 paths): reviewer (Sonnet, a2f3c76d) running → ON APPROVE + CI green: approve ce-dev-2 + `gh pr merge 611 --auto`.
- **dev-3 #341** AutoReview run_mode (branch ce-341-autoreview-runmode; tools/egress-broker/ce_egress_self_review_broker.py + test + carriers): CARRIER-SLUG CORRECTION sent (rename carriers to DASHED ce-341- slug; regen via carrier_gen; re-validate). CONTAINED ce-vps-codex (poll `ssh dev1 'sudo docker exec -e HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock ce-vps-codex herdr pane read w1:p1'`; NO auto-notify). ⚠️ harvest-rebase hits same-file #608 egress-broker changes (base stale) — harvest_intake reconciles. → READY-FOR-HARVEST: harvest_intake(Sonnet) git-bundle→reviewer→gate.
- **dev-4 #342** validate.yml `edited` trigger (branch ce-342-ci-retrigger): CORRECTION 2 sent (brief .ce/briefs/brief-ce342-correction2.md sha 1d6cd3f7): validate.yml change trips brain drift-CI (ce177) — AUTHORIZED to add `.ce/brain/assertions.yaml` to allowed paths + update ONLY the validate.yml hash entry; dashed carrier slug ce-342-; regen; re-validate. CONTAINED ce-dgx-codex (poll `sudo docker exec -e HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock ce-dgx-codex herdr pane read w1:p1`; NO auto-notify). → READY-FOR-HARVEST: harvest_intake(Sonnet) git-bundle→reviewer→gate.
- **Brain EmbeddingGemma install** (implementer Sonnet, a8e4ee2b): install sentence_transformers + EmbeddingGemma-300m LOCALLY on DGX venv (.venv), re-ingest conservative corpus with --embedder embeddinggemma, re-run 5 smoke queries vs keyword baseline, record assertion. STOP-LINE if model is license/HF-auth gated (→ Operator action). → ON report: surface semantic-recall verdict; if blocked on license → surface to Operator.

## BRAIN STATE (Slice A done)
- Infra ALREADY BUILT (validators/creator_engine_validator/brain_*.py; merged ce176/178/206/177). CLI: `PYTHONPATH=validators .venv/bin/ce brain {init,ingest,recall,assert,verify}` from /home/cedev2/creator-engine.
- Slice A ingest: 370 sources (257 memory/*.md + 113 .ce/state/research/*.md excl TRANSCRIPT*), 1556 chunks → `.ce/state/brain/recall.sqlite` (11MB), embedder=ce-deterministic-fake (dim32, PLACEHOLDER → keyword-only recall via FTS5/BM25). 2 assertions in ledger (.ce/state/brain/assertions.yaml), `ce brain verify` valid. sqlite_vec extension ABSENT (falls back to python-cosine, non-blocking). Real semantic recall needs EmbeddingGemma (install in flight).
- Design doc: .ce/state/research/CE_BRAIN_DESIGN_20260628.md (sha 3db62aef). Open scope decisions still pending: live-injection authority (#2), ce-ops-issue ingestion (#5), MEMORY migration pace (#4) — surface when relevant.

## SEATS SUMMARY (10:20Z, all WORKING corrections)
dev-1 (VPS NON-contained, tmux ce-dev1-orchestrator:2.0, self-push, double-Enter, NO auto-notify): pushed #611; next lane after = #34 forge-side / contained-parity-verification. · dev-3 (contained ce-vps-codex): #341 correction. · dev-4 (contained ce-dgx-codex): #342 correction-2.

## HARD-WON DISCIPLINE
1. FULL `ce validate-pr` GREEN in ONE pass before push (declared-class+floor; path-manifest carrier via `carrier_gen.write_carriers(base=)` API — **do NOT hand-list carrier filenames in briefs; let carrier_gen derive the DASHED branch slug** [recurring bug: briefs wrote ce341-/ce342- no-dash → 2 stop-lines]; changelog; G5 body line; autogen cli.generated.md for new ce groups = 3-file coupling). baseline-diff=regression authority. Host /tmp/.git trap → ce validate-pr (TMPDIR=/var/tmp), not raw pytest.
2. G5 body line FORGE-ONLY gate; body-edit alone won't re-trigger CI → close+reopen (ce-342 adds `edited` to fix). Push dismisses approval → re-approve on new head.
3. Seat injections=file+pointer+SHA; **contained/VPS-seat briefs must be COPIED INTO the seat fs** (dev-3/VPS can't see DGX host .ce/briefs — `cat brief | ssh dev1 'sudo docker exec -i ce-vps-codex tee <path>'`; dev-1/VPS via `ssh dev1 'cat > ~/creator-engine/.ce/briefs/...'`; dev-4/DGX-local CAN see host .ce/briefs). Control-signal confirms ok inline. herdr clears input on submit (looks idle) → verify `Working` indicator (re-read; transient). tmux double-Enter.
4. Every subagent sets model: Haiku=mechanical, Sonnet=substantive, Opus=controller ONLY. ZERO fork, ZERO Opus subagents. Author briefs/design-docs with write-capable implementer(Sonnet) that writes the file directly.
5. ⚠️ TERRITORY-MAP incl WORKTREES before dispatch.
6. HARVEST contained via `git bundle` extract→host worktree→validate-pr→push. dev-1 self-pushes (confirm-to-self-push). Controller holds gate (review as ce-dev-2 + enqueue); seats NEVER approve/merge. Independent reviewer venue (author≠reviewer).
7. ENV: dev-4 check-examples FAIL = environmental (ce-ops#339 missing libsodium) non-blocking; WARN surfaces_manifest_python_digest_pending (ce-ops#272) warning-only.

## WATCHERS / HOUSEKEEPING
- PR-board Monitor **boamzqs8y** persistent. /loop heartbeat self-paced (~25min fallback).
- **OpenBao wall token: renew before 15:42Z** (G4; ~5h buffer at 10:20Z — defer).
- FOLLOW-UP (annoyance→tool, file via ops_triage Haiku): orphan `.ce/pr-manifests/ce291a-automerge-classifier-dryrun.md` on main has no code + verify-path-manifest gate counts D-status carriers (blocks orphan cleanup) — file cleanup+gate-fix ticket. ALSO: codify "briefs must not hand-list carrier filenames" into brief-writer pattern.
- dev-4 git remote URL embeds overwatch PAT plaintext (pane scrollback) — credential-in-URL leak surface; fix later.

## QUEUED LANES (conveyor as seats free)
dev-1 next: #34 forge-side / contained-parity-verification. · Brain F5 MCP surface (product-feature scoped) — BUILD, design+dispatch after semantic recall proven. · ce244 slice 2/3 (#344 prong2/3). · W6a ce push. · W2e/W2f/W6b/W6d = 🔒.
