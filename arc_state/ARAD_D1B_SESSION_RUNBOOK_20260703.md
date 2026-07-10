# D1B SESSION RUNBOOK — Arad onboarding, 2026-07-03 07:30Z (variant B1 pending Operator confirm)
Grants: R-A ratified (runbook-bound, halt-on-deviation ON HER MACHINE). B1 deviation (apply
runs controller-side) pending explicit Operator "B1". Access verified: aradsky@100.74.214.78,
Ubuntu 24.04.4 x86_64, key auth OK. Subscription auth (no provider keys). Answers file:
.ce/state/research/ARAD_D1B_ce-install.answers.yaml

## PRE-SESSION (controller, before 07:30Z)
- [ ] PEM lands at ~/.ce-keys/ (Operator scp) → chmod 600, update env pointer to DURABLE path
      (not /dev/shm). If mythos App key: verify installation via App JWT
      (scratchpad/check_install.py pattern) → if installation live on chmod735-dor with mythos
      access, App-click becomes VERIFY-ONLY. If shared App key: click creates installation,
      then discover installation_id via GET /app/installations.
- [ ] Controller-side apply prep (B1): fresh clone of chmod735-dor/mythos under
      /var/tmp/d1b-mythos-apply/ (mythos-overwatch PAT for clone only).
- [ ] Docs/package fix landed? (implementer in flight) — package MUST be final before handoff.
- [ ] Session transcript capture: `script -f /var/tmp/d1b-session-$(date +%H%M).log` for every
      ssh leg (mandate D1c requires full evidence).

## SESSION FLOW (07:30Z, Arad present)
1. TOKEN SEAM (Arad, guided): she creates a fine-grained PAT — NO permissions needed
   (identity-only for existing mode), any expiry ≥ today. She saves it:
   `mkdir -p ~/.ce-secrets && chmod 700 ~/.ce-secrets; cat > ~/.ce-secrets/github-bootstrap-token.txt`
   (paste, Ctrl-D), `chmod 600` it. NEVER through our chat/transcripts.
2. INSTALL (controller drives via ssh, she watches): transfer answers file →
   `~/ce-install.answers.yaml`. Run documented one-liner with CE_ANSWERS pointing at it.
   Expect: signed spec verify → 0.3.1 venv → shims updated from 0.2.0 → inventory table.
   NO sudo should EVER be requested (os-native). Sudo prompt appearing = DEVIATION → halt.
3. APP CLICK SEAM: ✅ SKIPPED — verified 06:45Z: mythos-ce App (4103119, org-owned) installation
   141552951 live on chmod735-dor, scoped to exactly mythos, token mint proven. No click needed.
4. PLAN: from ~/ce-mythos/mythos run onboard --plan per runbook; review plan output with her.
5. APPLY (B1 CONFIRMED, controller host): from /var/tmp/d1b-mythos-apply (staged, HEAD 9f46024):
   CE_FORGE_LIVE_FORGE=1 CE_FORGE_ADOPTION_WRITE=1
   CE_FORGE_APP_CLIENT_ID=$MYTHOS_CE_CLIENT_ID (source ~/.ce-keys/mythos-ce-app.env)
   CE_FORGE_INSTALLATION_ID=141552951
   CE_FORGE_APP_PEM=/home/cedev2/.ce-keys/mythos-ce.2026-06-20.private-key.pem. Expect join-PR.
   Review join-PR content with her → SHE merges it (admin, her repo, her act).
   Her machine: git pull in ~/ce-mythos/mythos.
6. SMOKE: she runs `ce launch` in ~/ce-mythos/mythos — verify governed session banner +
   Claude Code starts (subscription login prompt if first time).
6b. SEAT IDENTITY (Operator-decided): stage mythos-arad App key to HER machine:
   scp ~/.ce-keys/mythos-arad.2026-06-27.private-key.pem aradsky@100.74.214.78:~/.ce-secrets/mythos-arad.private-key.pem
   then ssh chmod 600. Answers file already carries kind: own / app_id 4159494 /
   client_id Iv23liYX7gwrsQb01c2f / installation 142925881 / that pem path. Her CE authors
   as mythos-arad[bot]; she reviews as aradSmith (author≠approver clean). Broker migration
   when ce-ops#419 ships.
7. HANDOFF: welcome package (updated) — reading order per README; constitution ratification
   = HER act (manual path: commit docs/constitution.md); point at day-to-day-with-ce.md.

## STOP LINES
Any deviation from documented behavior ON HER MACHINE → halt + report, no improvisation.
Apply refusing (e2_brownfield_seam_unavailable etc.) on controller host → diagnose there,
her machine untouched. No PEM/secrets ever transit to her machine or chat.

## FALLBACK (B2 or PEM missing at window)
Run steps 1-4 + 6-7 (skip 5). Session still delivers: working install, plan, governed launch,
package. Apply in second window after broker wrapper (ce-ops#419) or PEM logistics resolve.
