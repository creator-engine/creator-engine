# RESUME STATE — CE-DEV-2 controller — 2026-06-26T17:26Z

## ⚠️ SEAT IDENTITY & TOPOLOGY (read first)
- I am the **CE-DEV-2 controller** on the **DGX Spark** (`spark-b824` = dgx-spark-1, 100.100.105.50, GB10 **aarch64**, user `cedev2` uid1003). I am the merge gate + Operator interface + foreman; ALL substantive work runs through launched WORKERS (sonnet) — I review/sign/merge.
- Fleet: **dev-1** = non-contained codex controller on VPS (Hetzner 100.72.252.20, `ssh dev1`, tmux `ce-dev1-orchestrator` **active pane = window 2 / %2**, self-pushes as ce-dev-1). **dev-3** = contained container `ce-vps-codex` on VPS (the GATE β canary seat; `ssh dev1 'sudo docker exec ce-vps-codex …'`; herdr pane w1:p1 at /run/creator-engine/herdr/herdr.sock INSIDE the container; ce-dev-3 is in the host docker group). **dev-4** = contained container `ce-dgx-codex` LOCAL on this DGX (`sudo docker exec ce-dgx-codex …`; herdr w1:p1 inside; commit-only / controller intake-pushes its work).
- overwatch gh: `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`. Reviewer = `ce-dev-2.pat` (~/.ce-keys/ce-dev-2.pat) → approve as ce-dev-2. ISSUES=ce-ops; CODE/PRs=creator-engine (PUBLIC repo). Auto-merge: `gh pr merge <n> --auto` (no --squash; merge_group queue governs).
- Preflight = `PYTHONPATH=validators python3 -m creator_engine_validator.ce_cli validate-pr --base origin/main --declared-work-class <wc>` (sets TMPDIR=/var/tmp internally → immune to the stray /tmp/.git on this box). Work class ∈ {tiny|story|feature|epic}. Repo venv: /home/cedev2/creator-engine/.venv.

## TWO ACTIVE ARCS

### ARC 1 — GATE β: retire the COURIER role (contained seats self-push + self-review, vault-sourced, no key in container)
**Mechanism PROVEN but courier NOT yet retired.** Merged: #533 (ce-ops#266 vault signer lib), #534 (#267 self-push daemon vault wiring), #536 (#268 self-review daemon vault wiring). Broker AppRole created in OpenBao (policy `ce-egress-broker-dev3-read`, role `egress-broker-dev3`, creds at `/etc/ce-egress/dev3-approle.env` on VPS 0600; least-priv PROVEN: reads ce-kv/forge/dev-3, denied wall path). Both broker daemons running on VPS (ce-egress-broker-dev3.service, ce-egress-self-review-dev3.service); dev-3 relaunched (currently via a MANUAL docker run workaround — not canonical yet) with both sockets mounted; containment verified (no PEM in container, no approle env in container, Ring-1 deny on direct push).

**Canary (20260626 ~17:00Z) PASSED on the mechanism** (evidence: `.ce/state/research/GATE_BETA_CANARY_EVIDENCE_20260626.md`): self-push → PR #540 (vault AppRole→ce-kv/data/forge/dev-3 per-call, key never in container/logs); self-review on #535 (author≠reviewer enforced, APPROVE hard-refused); Ring-1 deny (hook 121 + no-creds 128). **HONEST CAVEAT:** the canary invoked the broker HOST-SIDE because the contained seat couldn't reach the mounted socket (uid/gid mismatch) — so the SEAT-DRIVEN path (the thing that actually retires the courier) is NOT yet proven. Operator confirmed: attached to dev-3's pane, saw it do nothing → corroborates.

**Last-mile to the REAL from-seat canary (Operator said "go"):**
- **ce-ops#281** (OPEN, impl in flight, branch ce281-broker-optional-signature) — per-policy commit-signature requirement, OFF for contained seats (broker login+namespace+rate-limit is the trust boundary; ratified decision to drop per-seat signing). Touches tools/egress-broker/** only. → my review.
- **ce-ops#282** (**PR #542 OPEN, ready for my review**, branch ce282-broker-socket-reachability, subsumes #270) — ExecStartPost sets socket group = `$CE_EGRESS_SEAT_GID` (unit env, not hardcoded) + 0660 so the contained seat uid can connect(); canonical CE_VPS_EGRESS_SELF_REVIEW_SOCKET / CE_VPS_CONTAINER_EGRESS_SELF_REVIEW_SOCKET launcher vars. Preflight 15/15. → review + enqueue. (DEPLOY note: set CE_EGRESS_SEAT_GID=1003 in the daemon EnvironmentFiles on the VPS before relaunch.)
- **NEXT after #281+#282 merge:** deploy (set socket gid + relaunch dev-3 CANONICALLY via run-vps-runsc.sh) → **re-canary FROM INSIDE dev-3's codex agent**. Operator watches dev-3 do the self-push/self-review live in the herdr pane = the real courier-retirement proof. Do NOT call courier retired until the seat drives it with NO host-side hand. Then FLEET SWITCH (dev-1/dev-4 onto vault-sourced self-push, same ceremony to store their App keys at ce-kv/forge/<seat>).
- Artifacts to resolve: PR #540 (canary marker file `.ce/canary/gate-beta-dev3.md`) is OPEN — close or merge it as the proof artifact after the real from-seat canary.

### ARC 2 — Rented-surface dependency governance (Operator directive: "no band-aids; one mechanism to update every rented surface; seats NEVER self-update their toolchain"). [[ce-govern-rented-surface-updates]]
Trigger: dev-3 prompted to `npm install -g @openai/codex` during the canary. Design = `.ce/state/research/RENTED_SURFACE_GOVERNANCE_ARC_20260626.md`.
- **ce-ops#271** (PR #541, APPROVED + auto-merge armed) — IMMEDIATE FIX: Ring-1 now DENIES toolchain self-update (npm -g, pip install [exempt --no-index], apt install, dpkg -i, curl|sh, wget|sh). Verified denies + exemption holds. This was the live-hole closer + prerequisite for the fleet switch.
- Backlog filed (phased, dependency-linked): **#272** manifest SSOT (`surfaces/manifest.yaml`) + completeness check [FOUNDATION, highest leverage], **#273** consistency CI guard (joins validate-pr), **#274** digest-pin base images, **#275** fix floating VPS image tag, **#276** `ce surfaces check-updates`, **#277** carrier schema+runbook, **#278** `ce surfaces fleet-rollout` (= clean-install/#207-208 rollout mechanism), **#279** `surfaces/render.py`, **#280** wire CI image build from manifest. Composes w/ fleet-retirement, Ring-1 #219, ce update #190. NOT yet dispatched — start with #272→#273.

## OTHER OPEN PRs AT MY GATE
- **#541** ce271 toolchain-block — APPROVED, auto-merging (verify it landed; close-bot auto-closes #271).
- **#539** registry — MERGED (confidentiality-reworked: public = schema + redacted example only; real registry internal via **ce-ops#269**). #137 stays "Progresses".
- **#537** ce146-ssdf-slsa-matrix (dev-1 #146) — REVIEW_REQUIRED → review + approve/enqueue.
- **#535** ce166 slice3 — CHANGES_REQUESTED (FLEET-BREAKER: global self-identity assertion pinned to dev-1's identity → refuses bootstrap on every other host; reproduced on DGX). dev-1 REWORKING now (seat-scope it, rebase over #539's assertions.yaml). Re-review when pushed. NOTE: #535 + #539 both touch .ce/brain/assertions.yaml (hash-chained) → serialize (#539 merged first; #535 rebases).
- **#540** ce-gate-beta-canary — the canary artifact PR (see ARC 1).
- **dev-1 #132** (ce132-cleanroom-install-s1) — **BLOCKED, NOT pushed**: preflight fails the release_artifact_parity_guard — docs/install.sh was changed (new sha df3a0629...) but docs/downloads/0.2.0/install.sh + docs/downloads/0.2.0/SHA256SUMS weren't synced, AND those 2 files aren't in the path manifest. Fix (route to dev-1): copy updated install.sh → docs/downloads/0.2.0/install.sh, update SHA256SUMS, expand the manifest AUTHORIZED_PATHS + recompute sha, re-preflight, then push. Commit is local-clean on the branch in dev-1's worktree.
- **dev-4 #91/#65/#81** — intake harvest in flight (aef867e4); verify #91∌AGENTS.md, #81∌llms-install.md held.

## IN-FLIGHT WORKERS (background agents; if not resumable post-/clear, verify outcomes via gh/git — PRs/tickets are the durable record)
- ✅ #281 → **PR #543** OPEN (5361 tests pass) → review + enqueue.
- ✅ #282 → **PR #542** OPEN → review + enqueue.
- ✅ dev-1 harvest done: #146=PR #537 ready; #132 BLOCKED (see above).
- aef867e4 — dev-4 harvester (#91/#65/#81 INTAKE) still in flight → PRs to gate (verify #91∌AGENTS.md, #81∌llms-install.md).
- ✅ dev-4 next envelope = **ce-ops#110** (Ring-1 harness-adapter; branch ce110-harness-adapter; commit-only; pick VETTED clean — 5 new files, imports-but-doesn't-modify hook_check.py). Brief QUEUED behind dev-4's in-progress ce65 validation run; lands when that finishes.
- dev-1 (its own pane) — reworking #535.
- PRs now sitting AT MY GATE on resume: #543 (#281), #542 (#282), #537 (#146), #541 (#271, auto-merging), #535 (reworked slice3, when dev-1 pushes). Plus dev-4 intake PRs (#91/#65/#81) incoming.

## STANDING DISCIPLINES REINFORCED THIS SESSION
- [[ce-dispatch-territory-map-before-dispatch]] — hold a LIVE in-flight file-territory map; intersect EVERY candidate before dispatch (incl shared/gate files .github/**, systemd installer; grounding files AGENTS.md/.claude/agents; SIGNED artifacts docs/llms-install.md); VET dispatcher picks post-report. (#101 mis-dispatch + #91→AGENTS.md + #81→llms-install caught this session.)
- [[ce-run-full-preflight-before-push]] — use `ce validate-pr` (handles TMPDIR), never hand-run pytest inline; a stray /tmp/.git (owned by cedev4) false-fails ~64 tests.
- Credential-path PRs (#266/#267/#268/#281/#271) get a genuine security review from me (verify the capability is WIRED + denies, not just present). Confidentiality: creator-engine is PUBLIC — scan public artifacts for real fleet values before approving (#539 caught).
- Operator declined the dev-3 codex self-update (mid-canary; out-of-band; → ARC 2).

## IMMEDIATE NEXT ACTIONS (on resume)
1. Confirm #541 merged + #271 closed.
2. Review #281 + #282 PRs (credential/launcher path) → approve + enqueue.
3. Review harvested PRs: #537 (#146), #132, dev-4 #91/#65/#81 (intake), dev-1's reworked #535. Gate each.
4. After #281+#282 merge: deploy (socket gid + canonical dev-3 relaunch) → **from-seat re-canary** (Operator watches live) → report → then FLEET SWITCH.
5. dev-4 next envelope (from a52397bb) — vet the pick against the territory map before it proceeds.
6. ARC 2: dispatch #272 (manifest SSOT) → #273 (CI guard) when ready.
7. Open ce-ops follow-ups still parked: #269 (internal identity registry), #270 (subsumed by #282), #244 (harness SSOT injection — needs Operator taxonomy ratification).
