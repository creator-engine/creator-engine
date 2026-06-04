# PR path manifest — v3 G-3.4 credential value-injection seam (`forge/credential_runner.py`)

This file is the **carrier** for this PR's ratified closed manifest (the
convention defined in `docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`).
CI (`.github/workflows/validate.yml`) passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`,
which enforces that this PR's `base..HEAD` diff equals exactly the authorized
path-set below (the diff-gate runs *active*, not neutral). The fidelity scan
(`scan-path-manifest`) additionally requires the declared count and SHA256 to
match the fenced block.

This is a **code** PR (it touches Python under `validators/`). It adds the
G-3.4 credential value-injection seam: a new `forge/credential_runner.py`
exporting `authenticated_gh_runner(token, *, spawn=None) -> GhRunner`, which
takes a JIT-minted `ScopedToken` and returns a `GhRunner` whose child `gh`
subprocess env carries the live token value (`GH_TOKEN`) so the forge ops
authenticate as the scoped per-run credential. The token value reaches the
child env only — never the argv, never the input body, never a log, never disk,
never the parent `os.environ`, never the agent task container; competing ambient
auth (`GITHUB_TOKEN` and the GHES variants) is dropped from the child env. The
only existing-file edit is `forge/__init__.py` (it adds `authenticated_gh_runner`
to the imports and `__all__`). The frozen forge siblings (`change.py`,
`change_status.py`, `github_repo_config.py`, `scoped_token.py`,
`plan_approval.py`, `merge.py`) and `orchestrator.py` stay byte-unchanged. It
adds no `@register` check, no backend, and no schema → `--list-checks` is
**unchanged at 43** and `available_backends()` is unchanged at
`('gvisor-proxy', 'local-noop')`; no `ce_cli.py`/`cli.py`/wheel/`requirements`/
`pyproject.toml` change. The new `tests/unit/test_credential_runner.py` drives
every path with a fake `spawn` (zero live `gh` / network / subprocess).

- **base:** `99b56d5ff9c33b63451edb5f34a6cae5c2a16197`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=fa466d7eea57e1ebbb414aa1ec195e121a943dab76fe500c102e0792835aaa46

```text
.ce/pr-path-manifest.md
validators/creator_engine_validator/forge/__init__.py
validators/creator_engine_validator/forge/credential_runner.py
validators/tests/unit/test_credential_runner.py
```
