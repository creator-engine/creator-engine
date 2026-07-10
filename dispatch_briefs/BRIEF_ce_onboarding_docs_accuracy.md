# BRIEF — ce-onboarding-docs-accuracy — public onboarding docs describe a CLI that does not exist (QUEUED UNIT, dev-1)

Role: implementer (dev-1, self-push, foreman mode). Start after your ce-417 PR is opened (same
docs-surface serialization). Branch `ce-onboarding-docs-accuracy` off fresh origin/main.

## Bugs (live canary evidence, 2026-07-05, clean-env installs of signed 0.3.1)
1. docs/guide/solo-dev-onboarding(.md→.html) documents an entire Frame→Shape→Build→Review→Ship
   verb table — `ce scope, shape, ratify, drive, artifacts, show, merge, report, status, inbox` —
   NONE of which exist on the shipped `ce` (all fail `invalid choice`). A tenant has no working
   next step after install. Rip out/rewrite this page around the REAL surface (`ce onboard`,
   `ce launch`, actual verbs from `ce --help` on fresh main). Verify every command you leave in
   the page actually parses against the current CLI (run them --help in your checkout).
2. Contradictory first-command guidance: solo-dev-onboarding says "once installed, `ce launch` is
   your daily entry point" (bare `ce launch` right after install refuses G6-LAUNCH-BRAIN-BOOTSTRAP-
   REFUSED); welcome.md/zero-to-governed-seat-quickstart correctly say `ce onboard` first. Align
   ALL pages: onboard first, launch after.
3. Undocumented preconditions, add to welcome.md Day-One flow + quickstart: (a) a coding-agent
   CLI (Claude Code or Codex) must be installed — currently only pilot-runbook §0 mentions it;
   (b) the `.hermes/` gitignore precondition (RED-G-4 refusal) — the refusal text is good, the
   docs never warn.
4. welcome.md claims `ce onboard` is "idempotent... you can re-run it" — today re-run after a
   launch attempt refuses (SeatSurfaceReuseRefused). Until the product fix lands, soften the claim
   to match reality and document the safe recovery ONLY if one is officially supported (if none
   is, say "re-run support is being fixed" honestly rather than promising it).

## ADDENDUM (controller, post-recon): 5 more broken lines, same unit
Also fix the stale pre-rename `ce onboard --spec ...` spellings (the verb is `ce install --spec ...`;
`onboard` was deliberately excluded from the v3 forwarding shims because native `ce onboard` is the
first-run orchestrator — see test_ce_cli_v3_shim.py:79-84):
- docs/contracts/plain-join.md:23-24 (2 lines) → `ce install ...`
- docs/contracts/brownfield-adoption.md:19,21,22 (3 lines) → `ce install ...`
(docs/llms-install.md:239 has the same bug but is a SIGNED live artifact — explicitly EXCLUDED
here; it rides the 0.3.2 release re-sign. Do not touch it.)

## STOP lines
Public-docs product lens: ZERO ce-ops refs. Do NOT touch docs/install.sh, docs/downloads/**,
llms-install.md (SIGNED artifact — separate re-sign unit owns it). Do NOT document cev3 (retirement
direction); document only what works on `ce`. Never sign anything.

Evidence: full validate-pr GREEN one pass (docs-reconciliation coupling: verify test_v1_docs_*
fixtures if a verb list is asserted anywhere). Changelog + carrier. Work class story.
Report: `READY ce-onboarding-docs-accuracy <40-hex sha> PR=<url>`.
