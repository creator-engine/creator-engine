# 🌅 DAY-SHIFT ARC — 2026-06-26 — "Earn & Grant Autonomy + Ship" (MAX-THROUGHPUT)

Operator directive: max it out across all THREE programs (containment, autonomy, release), 2-3 waves each, depth + breadth. Operator assists on gates. OpenBao wall-arm flip = INCLUDED today.

## Critical path (the spine that orders everything)
CONTAINMENT substrate (#221/#222/#219/#228) + #239 wall→OpenBao wiring  →  **GATE α: flip wall armed:true**  →  #234 credential-walled gate  →  #242/#243 seat self-push & self-review  →  **GATE β: autonomy go-live (canary 1 seat)**.
RELEASE track (#198/#208/#205/#191) runs PARALLEL — independent of the spine until #191's gate.

## WAVE 0 — RUNNING (harvest ~04:31Z)
- C: **#221** probed-containment re-derive (dev-4) · **#222** egress fail-closed (dev-3)
- A: **#107(B)** §7 guard on 4 gh-api forge ops (dev-1)
- Controller lane: **#249** full relocate (worker; public-delete held for review)

## WAVE 1 — Containment substrate (morning) — unblocks autonomy
- **#219** Ring-1 per-tool-call governance for codex seats (THE core gap; 3/4 seats) — biggest unit, route to dev-4 (strongest). Brief ready: scratchpad/BRIEF_ce219.md (diagnostic-first).
- **#228** creds NEVER in container env/metadata — principle + adopt (transport-deputy aligned)
- ✅ **#239** wire approval-wall daemon → OpenBao — ALREADY MERGED (PR #446, acd9d6ff7, 2026-06-25). DONE.

## ✅ GATE α — DONE (verified 2026-06-26): wall state.json = {"armed": true} since Jun 25 22:21; daemon live (PID 1180751); secret materialized (0600); queue quiet. PROVEN: overnight's 10 PRs merged THROUGH this armed wall.
   - Hardening FYIs (non-blocking): (a) audit `ce-approval-wall-read` OpenBao policy = canonical path only; (b) daemon token is 72h-periodic, minted Jun 25 15:42 → renew before ~Jun 28 15:42 or daemon fails closed.

## WAVE 2 — Autonomy grant (afternoon) — depends on Wave 1 + GATE α
- **#234** credential-wall the approval gate (approval requires a capability, not just custody)
- **#242** contained-seat SELF-PUSH via injected credential (transport-deputy wiring)
- **#243** contained-seat SELF-REVIEW via injected credential
- **#244** define the Worker tier (in-process governed sub-agents) — design-heavy, parallel

## ▶ GATE β (Operator): autonomy go-live — canary ONE seat (dev-3) self-push+self-review before fleet-wide

## WAVE 3 — Release-to-traction (PARALLEL from morning)
- **#198** dogfood installed-ce (fleet runs installed `ce`, not `python -m`) — R1, independent, start early
- **#208** containerized CE OCI image (M2 — doubles as containment) — R2
- **#205** S3 belt launch-leg + offline harness — R2
- **#191** pre-canary release gate for Arad onboarding — R3, depends on #198/#208
- **#172** installer WSL2 — stretch

## WAVE 4 — Knowledge/SSOT + canon (capacity fill)
- **#166** SSOT slices · **#137/#147** identity+infra registry · **#163** foreman/swarm deterministic canon

## DoD (end of day-shift)
1. Containment: #221+#222 merged; #219 Ring-1 landed or in-review; #228 adopted. 2. Wall armed:true. 3. #239+#234 merged; #242/#243 at canary-green on dev-3. 4. Release: #198 merged (installed-ce dogfood), #208 image building. 5. Board moving, zero bad merges, all governed.

## Gates needing Operator (you said you'll assist)
- GATE α — wall arm flip. - GATE β — autonomy go-live canary. - #249 public-delete push (review diff). - any cross-repo / irreversible push.
