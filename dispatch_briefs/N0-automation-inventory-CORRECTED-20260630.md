# N0 Automation-Completeness Inventory — CORRECTED — 2026-06-30 night

> Built from the architect audit, **corrected** against actual `origin/main` (audit ran in the stale `ce-release-0.3.1-rc2` checkout and mis-reported several "not in main" lanes). Verify-against-origin/main, never the local rc2 working tree.

| Lane | VERIFIED status | Finish-step | Authority |
|------|-----------------|-------------|-----------|
| **L2 auto-merge canary** | **ARMED** (`CE_AUTOMERGE_RUN_MODE=ceo` ∈ {ceo,strangeLoop}; `CE_AUTOMERGE_ENABLING_REF`=ce-ops#356 set). Live-data wiring = PR #694 (in review). | Approve+merge #694 → docs-class XS/S auto-approve+merge LIVE. Spot-check first. | R1+Option A GRANTED |
| **L3 forge triage** | **MERGED in origin/main (#692)** — `ce_ops_triage_queue.py` + `ce-ops-triage-queue.yml` BOTH present. Audit "not merged" = rc2 misread. Runs DRY-RUN every 30min. | Post ce-ops#67 sentinel `<!-- ce-triage-queue-issue:v1 -->` + workflow_dispatch apply=true first run, then flip cron to apply. | G3 + apply=R1-ish (kill=revert) |
| **Surface B autonomous approve** | built-not-armed. Broker run-mode coded; live broker (dev-1) runs `CE_EGRESS_RUN_MODE=dev`. | dev-1: set `CE_EGRESS_RUN_MODE=strangeLoop` + restart `ce-egress-self-review.service` + enable `ce-review-pickup-daemon.service` + approval-wall secret. | **Operator-gated (R1)** — stage to flip-point + surface |
| **L7 auto-releases** | partial. `release-finalize` CLI seam exists; NO CI tag-creation / post-sign finalize / Pages-publish. | Design → build CI: auto-tag on bump-merge + post-sign finalize step + Pages deploy + release-parity guard. **Biggest BUILD gap.** | G5 build (sign-gate = R5 per-instance) |
| **L1.b auto-update** | partial — VERIFY #371/#682 vs origin/main (audit rc2-misled). recall-floor likely not built. | startup notice (fail-open, time-boxed, off in seats) + recall-floor min-version field. | G5 build |
| **Conveyor/intake** | 3 belt daemons built + systemd units; harvest→push leg has NO daemon. | Verify daemons running on dev-1; build harvest→validate→push conveyor daemon. | G7 + G5 build |
| **close-bot #262** | built+live (`ce-ops-autoclose.yml` + `ceops_autoclose.py`, fail-open). | Verify `CE_CROSS_REPO_TOKEN` secret present. | G3 verify |

**Unlisted lanes found:** `ce-egress-self-push.service` (self-push broker, same run-mode gating); `workflow_registry.py` 8 catalogued workflow types all `ratified=False` (design specs, none wired).

## Cross-cutting unblocks (verified)
- **`CE_CROSS_REPO_TOKEN` secret MISSING** (only legacy `CE_OPS_TOKEN` set). Blocks BOTH (a) L3-triage-apply scheduled run and (b) close-bot auto-close (its `GH_TOKEN=CE_CROSS_REPO_TOKEN`). Fix = provision a **least-privilege** fine-grained PAT / App token (ce-ops `issues:write` only) as `CE_CROSS_REPO_TOKEN` — NOT the broad overwatch PAT. **Credential decision → Operator.**
- **dev-1 belt daemons ALL inactive** (`ce-integrator-daemon`, `ce-review-pickup-daemon`, `ce-belt-daemon` — user+system). Blocks Surface-B autonomous-approve + conveyor. (Merge automation still works: the DGX **wall queue-daemon PID 43010** merges ce-dev-2-approved PRs.)

## Audit corrections (rc2-checkout false negatives — all verified against origin/main)
- L3 triage #692 = **MERGED** (files present). - #682 auto-update startup notice = **MERGED** (2026-06-30); update.py has startup/recall/track hooks. - #371 is unrelated (codex-harness refusal). - L1.b is **more complete** than audit said; recall-floor = remaining piece (verify).

## L3 apply staged
Sentinel comment **created** on ce-ops#67 (id 4846673275). Remaining: provision `CE_CROSS_REPO_TOKEN` (or wire `CE_OPS_TOKEN` fallback into the triage workflow) → `workflow_dispatch apply=true`.

**Driving order tonight:** (1) #694 approve→L2 go-live [in flight]; (2) L3 apply-mode flip; (3) L7 design+build [dev-4]; (4) Surface B stage-to-flip + surface; (5) verify L1.b/#371 + conveyor daemons + close-bot secret.
