# WORK CLAIM — ce-ops#338 harden self-fire APPROVE guard against the curl-to-reviews vector

**Seat:** dev-1. **Role:** implementer-foreman. **Born foreman** — fan out.

## Branch
```
git fetch origin && git checkout -b ce-338-curl-reviews-guard origin/main
```

## Why (self-contained)
PR #596 (just merged) made the reviewer-authority PreToolUse hook mechanically block a raw `gh api …/pulls/N/reviews` call carrying `event=APPROVE` from the self-fire reviewer path. But the approve-event classification + deny predicate (`_is_raw_gh_api_review_approve`) are wired ONLY into the gh-api parser (`_parse_gh_api_call`), NOT the curl parser (`_parse_curl_api_call`). So a parallel vector — `curl -X POST https://api.github.com/repos/<owner>/<repo>/pulls/<N>/reviews -d '{"event":"APPROVE"}'` — is classified `None` and NOT denied. Pre-existing + low-exploitability (zero-cred worker), but it leaves the "self-fire must never APPROVE" property incomplete for the curl spelling.

## Task — bring the curl path to parity with the gh-api path
In `validators/creator_engine_validator/hook_check.py`:
1. In `_parse_curl_api_call`, detect a POST to a `/pulls/N/reviews` endpoint carrying `event=APPROVE` in the body, and route it through the SAME deny path the gh-api side uses (the `pr_review` classification → fail-closed deny in `_authority_covers`).
2. Cover bypass forms: `-X POST`/`--request POST`, full `https://api.github.com/...` URL vs bare path, `-d`/`--data`/`--data-raw`/`--data-binary`, inline JSON with case/whitespace variants; and FAIL-CLOSED on `--data @file`/stdin where the body isn't inline (treat as approve-event when the reviews endpoint is targeted, same posture as the gh-api `--input` handling).
3. Add paired BEHAVIORAL unit tests (mirror the gh-api approve tests in `test_hook_check_reviewer_authority.py`) proving a curl raw-API APPROVE is DENIED — including the envelope-present case.

## Allowed paths (nothing else)
`validators/creator_engine_validator/hook_check.py`, `validators/tests/unit/test_hook_check_reviewer_authority.py` (+ a curl-parse test file if cleaner), `.ce/changelog/**`, `.ce/pr-manifests/**`.

## Evidence (DoD)
Full `ce validate-pr` GREEN; declare the G5-derived work-class. Keep parity/consistency with the gh-api guard (same deny predicate, same reason string shape).

## Stop-line
- Green + self-push works → push + open PR referencing ce-ops#338. Do NOT approve/merge/enqueue.
- Preflight RED → STOP + report the failing gate.
