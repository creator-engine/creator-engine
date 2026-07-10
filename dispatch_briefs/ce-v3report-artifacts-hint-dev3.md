# SEED BRIEF — Fix `ce artifacts` completion-report hint — SEAT: dev-3 (contained, no-egress)

**Lane:** CLI correctness fast-follow (found in #674 review). **Branch:** `ce-fix-artifacts-hint`. **Role:** implementer. **Work class:** declare by floor (likely `tiny`).

## Bug (self-contained — everything you need is here)
`validators/creator_engine_validator/v3_report.py` builds the completion-report "Inspect" hints. At ~line 154 and ~line 156 it emits:
```python
out.append({"kind": "evidence", "label": "evidence-chain ✓", "inspect": f"{CE_CMD} artifacts {run}"})
...
out.append({"kind": "spend", "label": "spend", "inspect": f"{CE_CMD} artifacts {run}"})
```
where `run = summary.get("run_id")`. But the `ce artifacts` subcommand takes a **scope_id positional** with an OPTIONAL `--run-id` (see `v3_cli.py`: `p_art.add_argument("scope_id", ...)` and `p_art.add_argument("--run-id", default=None)`). So the rendered hint `ce artifacts <run-id>` makes a user run `ce artifacts <run-id>` → "no Scope '<run-id>' found".

## Fix
- Emit the correct invocation: `ce artifacts <scope_id> --run-id <run_id>`. Get the scope id from the same `summary` dict (look for the scope/scope_id key it already carries — inspect the function and its callers in `v3_report.py` to find the right field; the report already knows the scope). If only `run_id` is reliably present, still produce a runnable form using the scope id that the surrounding report uses for the other hints (the `ce show <scope-id>` hint in the same block proves scope_id is available).
- Apply to BOTH the evidence (line ~154) and spend (line ~156) hints.
- Keep `CE_CMD` usage (do not hardcode `ce`).

## Tests
- Update/extend the unit test(s) for `enumerate_artifacts` (search `validators/tests/` for `enumerate_artifacts` or `v3_report`). Assert the emitted `inspect` string is `ce artifacts <scope_id> --run-id <run_id>` form, not `ce artifacts <run_id>`. Add a regression case.

## Contained-seat mechanics (FOLLOW EXACTLY)
- Worktree under **/var/tmp** (NOT /workspace): `git worktree add -b ce-fix-artifacts-hint /var/tmp/wt-artifacts-hint origin/main` (branch off **origin/main**; if origin is stale you cannot fetch — branch off newest local main and note it).
- venv has NO activate script — run `.venv/bin/python -m pytest ...` and the validator via the documented `ce validate-pr` entry (TMPDIR=/var/tmp hermetic).
- Add changelog `.ce/changelog/ce-fix-artifacts-hint.md` + regenerate carrier via `carrier_gen.write_carriers(base=<merge-base>)` (stem == branch slug; rm build/egg-info first).
- Run FULL `ce validate-pr` GREEN in one pass. Compute floor: `verify-work-sizing-floor --base <merge-base> --declared-work-class tiny .`.
- You are no-egress: COMMIT, then `git rev-parse HEAD` and report the SHA + branch (the controller harvests/pushes). Do NOT attempt to push.

## Stop line
Committed + preflight GREEN + test asserts correct hint form + carrier/changelog present. Report the commit SHA. Controller harvests.
