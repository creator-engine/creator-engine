# BRIEF — ce-401 + ce-403 hardening batch (TWO file-disjoint units, dev-1, foreman mode)

Role: implementer (dev-1, self-push, foreman). Run BOTH as parallel worker threads in separate
worktrees — territories are disjoint. Both tickets are readable directly: gh issue view in
creator-engine/ce-ops. SEMANTIC NOVELTY CHECK per item: these are pooled review follow-ups from
2026-07-02; verify each item is still unaddressed on fresh origin/main (BEHAVIORAL bar, not
grep-presence) — skip any that landed, note it in the PR body.

## UNIT A — branch `ce-401-doctrine-coverage-fastfollow` (ticket ce-ops#401, work class XS→tiny)
Deliver the 4 NOT-BLOCKING items from the ticket (docstring design-limit note ·
absent-vs-corrupt ledger message alignment w/ ce_brain_drift's authoritative_ledger_exists idiom
+ its missing test · duplicate-exception-entry + exception-outside-governed_trees tests ·
multi-root note/decision). Do NOT do the "governed_trees widen" tail item (separate mandate).
Territory: the ce_brain_doctrine_coverage module + its tests + changelog/carrier.

## UNIT B — branch `ce-403-scanner-hardening-fastfollow` (ticket ce-ops#403, work class S→story)
Deliver the 5 items (ALLOWED_OFFENSES shrink-only staleness test · stat-level OSError
fail-closed at ~public_docs_confidentiality.py:390 · empty-scan minimum-floor sanity ·
duplicate issue:-line collision test + git ls-files failure-path test · remove dead
public_doc_files() alias if truly zero callers — grep first).
Territory: validators/creator_engine_validator/public_docs_confidentiality.py + its tests +
changelog/carrier. ⚠️ This file was touched by merged PR #802 — branch off FRESH origin/main.

## Standing (both units)
Full `ce validate-pr` GREEN one pass before push (per playbooks/controller/briefs/dispatch.md).
Changelog fragment + carrier per branch (stem == branch). PR body: exactly one
`- **Declared work class:** <class>` line. Do NOT proactively rebase open PRs after pushing.
⛔ Never sign anything; signed-artifact gate failure = STOP + report bytes. No
review/approve/merge/enqueue. Report per unit: `READY <branch> <40-hex sha> PR=<url>`.
