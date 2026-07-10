# RESUME STATE — CE-DEV-2 — 2026-07-08 afternoon — DAY-ARC-2 late checkpoint

> Supersedes DAYARC2B (read it for rules/watcher specs). READ ORDER: MEMORY.md →
> DECISIONS_20260708.md (11 items) → this file.

## MERGED TODAY (through containerized gate)
#896 seat-ready profile · #897 Ring-1 provenance (decision 4a EXECUTED) · #898 broker v1
slice 1. Main ~6255a0f8+.

## OPEN PRS + LANES IN FLIGHT
- #895 IaC redeploy: APPROVED; CI re-run after body fix (G5 = EXACTLY ONE work-class line;
  it had zero after a body rewrite). On merge → decision-1 precondition met.
- #899 ce-503 refresh-guard (dev-3 authored, harvested): reviewer running (security focus:
  generation-aware guard must not weaken foreign-file refusal).
- dev-1 WORKING ce-followups-20260708 (batch: #896/#898 minors, ce-ops#504 checklist,
  -n auto isolation race). Brief BRIEF_dev1_followups_20260708.md.
- dev-4 WORKING ce-491-optiona-slice1 (Option A materializer slice 1, DRY-RUN ONLY,
  ARMING_ENABLED=False hard inv). Brief BRIEF_dev4_491_optiona_slice1_20260708.md.
- 0.3.4 staging agent still assembling (stops before signature; I sign per decision 9).

## ce-materializer APP — PROVISIONED + CHAIN VERIFIED (decision 11 executed)
App 4244593 / inst 145152358 / contents:write / single-repo. PEM ~/.ce-keys/
ce-materializer.2026-07-07.private-key.pem (0600) + env mirror; OpenBao migration TODO
(pickup token read-only). Ruleset ce-reference-protection-floor = SOLE protection on main
(classic protection DELETED — was 1:1 subset); App = only bypass actor (always). Verified:
mint→scratch-ref 201/204→404-on-ce-ops→revoke. Push-to-main untested by design until arming
(gates: #895 merge + Option A slice2+ + Operator arming call).

## DEV-3 REBUILD IN PROGRESS
Root cause of recurring BLOCKED: VPS image built 2026-06-27 predates openssh-client in
Dockerfile (ssh-keygen present in dev-4 image, missing dev-3). ce-503 work EXTRACTED (safe).
amd64 image building on VPS: ~ce-dev-1/ce-image-build (clean main clone), build2.log, tag
creator-engine/codex-runsc:x86_64-new, build-args from `surfaces/render.py --arch amd64`
(build-image.sh HARDCODES arm64 — bug in followups ledger). NEXT: when build done → stop
ce-vps-codex → canonical relaunch `ce launch --harness codex` from new image → ssh-keygen
probe → self-push canary re-prove.

## TICKETS FILED TODAY
ce-ops#503 (refresh-guard gap; fix = PR #899) · #504 (broker slice-2 arming blockers:
3 MAJORs + minors checklist) · #184 CLOSED (VPS swap+tmpfs cap applied, verified).

## ARAD LANE
Apply attempted via App lane (dual escalation env: CE_FORGE_LIVE_FORGE=1 +
CE_FORGE_ADOPTION_WRITE=1 + CE_FORGE_APP_{CLIENT_ID,PEM}/CE_FORGE_INSTALLATION_ID; driver
mints own token — GH_TOKEN irrelevant). REFUSED: tenant workflow = old advisory-only
generation, guard didn't recognize (→#503→#899). NOTE: her CI does NOT fail closed
(advisory `|| true`) — #494 urgency assumption falsified. RETRY apply after #899 merges,
from a main-source checkout, same env recipe, from /home/cedev2/ce-pilots/mythos (fetch
first). Then send blocks only on Operator T4 pack + md-sources.

## FOLLOW-UPS LEDGER
.ce/state/research/FOLLOWUPS_DAYARC2_20260708.md (Dockerfile arch bug, #895 smoke minor,
G5-exactly-one-line lesson CORRECTED entry, etc.). Sweep into next intake wave.

## ⏸️ AWAITING-OPERATOR (2)
1. Arad T4 pack + md-sources. 2. Nitzan D6. (Materializer ARMING will be a 3rd once
slice 2 lands — returns to Operator by design.)
