# DISPATCH — CI guard test: no ${{ }} in workflow run: blocks — dev-3

LANE: prevent the GitHub-Actions injection anti-pattern from regressing. PR #703 just removed all `${{ ... }}` interpolations from inside `run:` shell blocks (moved to `env:` indirection). Add a CI guard TEST that FAILS if any `.github/workflows/*.yml` reintroduces a `${{ }}` expression inside a `run:` block body.

WORKTREE under /var/tmp off CURRENT origin/main. Branch **ce-ci-runblock-injection-guard**. validate-pr via `TMPDIR=/var/tmp PYTHONPATH=$PWD/validators /workspace/creator-engine/.venv/bin/python -m creator_engine_validator.ce_cli validate-pr`. STOP before push.

## Scope
1. Add a unit test (e.g. validators/tests/unit/test_workflow_no_runblock_injection.py) that:
   - Parses every `.github/workflows/*.yml`, walks each job's steps, and for any step with a `run:` block, asserts the run STRING contains no `${{` ... `}}` GitHub expression. (Expressions in `env:`/`if:`/`with:`/`name:` are fine — only `run:` bodies are flagged.)
   - Use a YAML parser to locate run blocks precisely; a pure-text regex over the whole file would false-positive on env: lines, so scope to run: values.
   - Assert the CURRENT repo passes (it should, post-#703).
   - Include a NEGATIVE fixture/inline-YAML case proving a `run:` with `${{ }}` is REJECTED.
2. Keep it offline/pure (no network, no subprocess).

## Evidence
- The new test passes on current main; the negative case proves detection works.
- `ce validate-pr` GREEN. Carrier+changelog (carrier_gen.write_carriers head_ref=ce-ci-runblock-injection-guard, kind=test, scope=ci) + `- **Declared work class:** tiny` line in carrier. rm validators/build before git add.
- Verify vs origin/main, NOT rc2. Don't touch docs/install.sh or docs/downloads.
Report: branch, SHA, validate-pr PASS line.
