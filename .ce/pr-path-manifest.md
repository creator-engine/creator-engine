# PR path manifest — v3 G-3.2 read-only forge change-status ops (`forge/change_status.py`)

This file is the **carrier** for this PR's ratified closed manifest (the
convention defined in `docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`).
CI (`.github/workflows/validate.yml`) passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`,
which enforces that this PR's `base..HEAD` diff equals exactly the authorized
path-set below (the diff-gate runs *active*, not neutral). The fidelity scan
(`scan-path-manifest`) additionally requires the declared count and SHA256 to
match the fenced block.

This is a **code** PR (G-3.2). It adds three pure, read-only, value-free forge-native
change-status ops so the orchestrator can OBSERVE the §8.3 merge-gates without mutating:

- `forge/change_status.py` (NEW) adds `review_state(change) -> ReviewState`,
  `checks_state(change) -> ChecksState`, and `change_conflicts(change) -> ConflictState`
  — each takes a value-free `ChangeRef`, issues exactly one GraphQL READ through the
  injectable `GhRunner` (the same derived gates `gh pr view` uses — `reviewDecision`, the
  head commit's `statusCheckRollup.state`, `mergeStateStatus`/`mergeable`), and returns a
  frozen value-free result type. There is **no** `apply` parameter (read-only). Each op
  refuses BEFORE any forge call (`ChangeStatusRefused`, code `V3-FORGE-CHANGESTATUS-REFUSED`)
  on a malformed `repo` or a change with no open PR (`pr_number is None`); a transport
  failure raises `ForgeConfigError`. It reuses `GhRunner`/`ForgeConfigError`/
  `ForgeConfigRefused` (and `ChangeRef`) by import and re-defines `_REPO_RE` locally.
- `forge/__init__.py` re-exports the three ops + the three result types + `ChangeStatusRefused`.
- `tests/unit/test_change_status.py` (NEW) drives every path through a fake `GhRunner`
  returning canned GraphQL JSON (`subprocess.run`/`Popen`/`socket.socket` monkeypatched to
  explode — zero live network/subprocess in CI), asserting `runner.calls == []` on refusals.

It registers **no** `@register` check, adds **no** backend (`register_backend`) and **no**
schema → `--list-checks` is **unchanged at 43** and `available_backends()` is unchanged at
`('gvisor-proxy', 'local-noop')`. The frozen forge siblings `change.py`,
`github_repo_config.py`, `scoped_token.py`, `plan_approval.py` are **byte-unchanged**
(reuse by import); the only existing-file edit is `forge/__init__.py`. No `cli.py`/
`ce_cli.py`/`pyproject.toml`/`requirements*` change; no new `schemas/*.yaml`.

- **base:** `4f92882e16bde0445e03a10831240cf86694e272`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=9d27b901a1162093e269c2017be8762a759d86844624d23dc4d987333501515e

```text
.ce/pr-path-manifest.md
validators/creator_engine_validator/forge/__init__.py
validators/creator_engine_validator/forge/change_status.py
validators/tests/unit/test_change_status.py
```
