# BRIEF — dev-3 — Expand the support-agent zero-leak eval corpus (ce-ops#360, Phase D hardening)

Born-foreman, contained/no-egress (DO NOT push — controller harvests). Fresh branch `ce-supportagent-eval-corpus-expand` off CURRENT origin/main (`git fetch origin main` first). Drive to READY-FOR-HARVEST GREEN; report HEAD SHA. Carrier slug == branch.

## Context (EMBEDDED)
The zero-leak eval (`validators/creator_engine_validator/support_eval.py` + fixtures `validators/tests/unit/fixtures/support_agent_zero_leak_cases.json`, in main from #657) is the release gate for `ce ask`. It currently has only 8 cases (4 answered-with-citation + 4 leak-probes). Strengthen it. **Read support_eval.py + the existing fixtures FIRST and match their schema exactly — do NOT change the runner/detector logic, only ADD cases (and optionally minor runner ergonomics if clearly needed, but prefer fixtures-only).**

## Deliverables (prefer ADD-ONLY)
1. **Expand the fixtures** to a stronger battery (aim ~20–30 cases total) covering, with the SAME json schema:
   - More ANSWERABLE product questions across the corpus (install, onboarding, governance concepts, usage, contributing) that should answer-with-citation.
   - More LEAK-PROBE questions that MUST be refused/non-leaking — exercise a BROADER set of confidential markers (internal ticket refs, internal hostnames/identities, controller/playbook tokens, secret env-var names incl. `_PAT`/`_CMD` suffixes, tailnet) so the gate catches more leak shapes. Use SYNTHETIC/placeholder markers, NOT real infra detail.
   - A few edge cases: ambiguous questions, questions that mix answerable + probe content.
2. If (and only if) the runner needs a tiny ergonomic change to support the new cases, keep it minimal + backward-compatible; do NOT weaken hard-fail-on-any-leak.
3. **Tests:** ensure the expanded suite runs and the existing `test_support_agent_zero_leak_eval.py` still passes; add coverage proving the new leak-probe shapes are caught (planted-leak → hard fail). Keep everything OFFLINE (stub model; no live network in CI).

## Do NOT
- Do NOT change support_runtime.py / support_profile / the leak-detector core logic (other lanes; ce-ops#362 is unifying the rule table — stay out of it).
- Do NOT commit real internal infra/identities as fixture "leak examples" — synthetic placeholders only.
- Do NOT weaken cite-or-refuse / zero-leak / hard-fail.

## Gates
- FULL `ce validate-pr` GREEN in ONE pass (`TMPDIR=/var/tmp`). Carriers via `carrier_gen.write_carriers(base=<merge-base>)` (rm build/egg-info first; VERIFY work-class line present — likely `story`) + changelog. Slug == branch. Product-lens. STOP at green; report SHA. Do NOT push.
