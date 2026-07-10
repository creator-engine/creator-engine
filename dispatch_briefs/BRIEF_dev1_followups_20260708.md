# BRIEF — dev-1 — 2026-07-08 — 1 STORY unit: review-findings follow-up batch (merged-PR minors)

Role: implementer, self-push lane. Branch `ce-followups-20260708` off fresh origin/main
(`git fetch origin && git checkout -b ce-followups-20260708 origin/main`). Full `ce validate-pr`
green locally (TMPDIR=$HOME/tmp, -n 4, serialize suites, clean pytest tmpdirs) → push → PR →
`READY ce-followups-20260708 <sha> PR#<n>`. If blocked: `BLOCKED ce-followups-20260708 <reason>`.

⚠️ PR BODY RULE (a sibling PR failed CI on this today): the body must contain EXACTLY ONE line
matching `- **Declared work class:** <value>` — count matches before pushing; do not let a quoted
manifest or prose duplicate it.

All items below are non-blocking findings from today's independent reviews of MERGED PRs
(#896 seat-ready profile, #898 broker slice 1) plus one test-isolation race found during harvest.
The three MAJOR broker findings (audit "value" substring, image allowlist, state_root_prefixes)
are NOT in scope — they are slice-2 arming blockers with their own lane.

## Items

F1 — `tools/host-ops-broker/host_ops_broker/kill_switch.py` (~line 29): `raw.get("disabled") is
True` only engages on the exact boolean. Change to fail-closed truthiness: engage broker-wide
disable for ANY truthy value (1, "yes", "true", …) and ALSO for a present-but-non-boolean-falsy
ambiguous value? No — rule: `disabled` present and not exactly `false` → disabled (fail-closed:
only the explicit boolean false means enabled when the key exists). Add tests for integer 1,
string "yes", string "false" (string is truthy → disabled), and explicit false.

F2 — `tools/host-ops-broker/host_ops_broker/audit.py`: remove the unused `now` parameter from
`append_audit` (dead API surface; timestamps are pre-computed in records). Fix the one/two call
sites and any test that passes it.

F3 — Broker missing-test trio (code is correct; pin it): (a) `disabled_verbs` present but not a
Mapping (e.g. `"all"`) → broker-wide disabled; (b) `BrokerConfig.load` fail-closed on missing
file and malformed JSON (currently no unit test constructs via load); (c) per-verb disable emits
audit and leaves the rate-limit store EMPTY (ordering pin, mirroring
test_kill_switch_precedes_rate_limit_accounting).

F4 — `validators/creator_engine_validator/pr_preflight.py` `_commit_staged_autogen`: append
`"--", str(spec.artifact)` to the git commit argv so the autogen refresh commit can never sweep
unrelated pre-staged index content (reachable under --allow-dirty). Plus the missing end-to-end
test: seat-ready profile run with a touched source surface AND `autogen_artifact_changed=True`
asserting the git add + git commit argv sequence appears (extend the FakeRunner pattern already
in test_pr_preflight.py).

F5 — Test-isolation race (found under `-n auto`): the test that exercises stale-checkout
artifact dirs (`test_surface_determinism_ignores_stale_checkout_artifact_dirs`, find it under
validators/tests/) creates `validators/build/` inside the REAL repo checkout mid-test; a
concurrently running `test_release_finalize_docs_copy_passes_release_guards` does
`shutil.copytree(REPO_ROOT, …)` and dies on the transient dir. Fix by isolation, not ordering:
point the surface-determinism test at a COPIED/tmp repo root (follow whatever fixture the
release-finalize test itself uses to get a repo copy), so it never mutates the real checkout.
Verify: run the two tests together under `-n 8` repeatedly (5×) with zero flakes, and note the
command + result in the PR body.

F6 — `tools/host-ops-broker/host_ops_broker/verb_schema.py` `_SAFE_TEXT`: drop the literal
space from the character class (daemon/unit/root names never contain spaces); adjust/extend the
schema tests accordingly (a space-containing daemon name must now be rejected at SCHEMA level,
not just allow-list level).

## Obligations
Changelog `.ce/changelog/ce-followups-20260708.md`; carrier `.ce/pr-manifests/
ce-followups-20260708.md` (slug == branch, every changed path, one work-class line — declare
honestly, likely story/S). PR body references PR #896 review, PR #898 review, ce-ops#504
(checklist items F1/F2/F3/F6 — say "partially addresses #504: minors only; MAJORs remain").

## Stop line
Only: tools/host-ops-broker/** (the named files), validators/creator_engine_validator/
pr_preflight.py (the one function), the involved test modules under validators/tests/, and the
changelog+carrier. NO changes to broker MAJOR-finding surfaces (config allowlists, audit
forbidden-key list, _resolve_target), no deploy/, no docs/. No approve/merge/sign/gate acts.
