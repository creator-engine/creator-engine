# HARVEST BRIEF — Phase 1: spec-kit skills removal (dev-3, contained no-egress)

**Program:** spec-kit FULL RETIREMENT (Operator-ratified 2026-06-30), Phase 1. **Branch:** `ce-speckit-retire-skills`. **Role:** harvest_intake.

## Source (contained, no-egress seat — you extract + push)
- Seat dev-3 = container `ce-vps-codex` on the Hetzner VPS. Reach: `ssh dev1 'sudo docker exec ce-vps-codex <cmd>'`.
- The completed work is on branch `ce-speckit-retire-skills`, commit `cc02717dbd912fc6fcdec4b2e3c0b576ba70b437` ("Retire vendored spec-kit skills"), inside the container repo. Locate the repo: try `/workspace/creator-engine` first, then `/var/tmp/wt-*` worktrees (`ssh dev1 'sudo docker exec ce-vps-codex bash -lc "git -C /workspace/creator-engine log --oneline -1 ce-speckit-retire-skills 2>/dev/null; ls -d /var/tmp/wt-* 2>/dev/null"'`). Confirm the commit SHA matches `cc02717d` before extracting.

## Extract → host (no-egress: the seat cannot push; you carry the commit out)
1. In the container, create a bundle of the branch range from origin/main to the commit:
   `ssh dev1 'sudo docker exec ce-vps-codex bash -lc "git -C <repo> bundle create /tmp/phase1.bundle origin/main..ce-speckit-retire-skills && git -C <repo> rev-parse ce-speckit-retire-skills"'`
   (If origin/main in-container is stale, bundle the full branch tip instead and reconcile against the AUTHORITATIVE host origin/main — see the stale-origin caution.)
2. Copy the bundle to the host: `ssh dev1 'sudo docker cp ce-vps-codex:/tmp/phase1.bundle -' > /var/tmp/phase1.bundle` (or docker cp to a VPS path then scp). Verify it's non-empty.
3. On THIS host, in an isolated worktree under `/home/cedev2/creator-engine/.ce/wt-phase1-harvest`: fetch the branch from the bundle, branch off the authoritative host `origin/main`, and apply the commit(s). The net change must be ONLY the deletion of the 13 `.claude/skills/speckit-*` skill directories (git rm). Verify with `git diff --stat origin/main...HEAD` — it must show only `.claude/skills/speckit-*` removals plus the carrier + changelog.

## Preflight + carriers (host)
4. Confirm a per-PR changelog `.ce/changelog/ce-speckit-retire-skills.md` exists and a path-manifest carrier `.ce/pr-manifests/ce-speckit-retire-skills.md` exists with stem == branch slug `ce-speckit-retire-skills`. If missing or mismatched: regenerate the carrier via the `carrier_gen.write_carriers(base=<merge-base>)` API (NOT hand-edit; rm any build/egg-info first) and author a short changelog.
5. Run the FULL local preflight GREEN in one pass on the host venv: `ce validate-pr` (TMPDIR=/var/tmp for a hermetic run; avoid the host `/tmp/.git` trap). Two-strikes → STOP and report, don't whack-a-mole.
6. Compute the work-sizing floor: `PYTHONPATH=.../validators python -m creator_engine_validator verify-work-sizing-floor --base <merge-base> --declared-work-class tiny .` — use the lowest class that PASSES (expected `tiny` for a pure deletion).

## Push + PR (you push; controller holds the gate)
7. Push `ce-speckit-retire-skills` to origin.
8. Open the PR (base main) with: title `chore: retire vendored spec-kit skills (spec-kit retirement Phase 1)`; body must include exactly one `- **Declared work class:** <class>` line (the floor-satisfying class) and a note: "Merge order: Phase 0 (#674) → Phase 4 → **Phase 1 (this)** → Phase 2 (#675) → Phase 3. Do not enqueue until predecessors merge."
9. STOP. Report: the PR number, the pushed HEAD SHA, `git diff --stat` summary, the declared work class, and the preflight result. Do NOT approve, merge, or enqueue.

## Stop line
PR open + preflight GREEN + diff is skills-only + carrier/changelog present + work class declared. Nothing merged.
