# PR path manifest — v3 G-3.0 `forge.open_change()` / `ChangeRef` (the change-lifecycle "PR opened" primitive)

This file is the **carrier** for this PR's ratified closed manifest (the
convention defined in `docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`).
CI (`.github/workflows/validate.yml`) passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`,
which enforces that this PR's `base..HEAD` diff equals exactly the authorized
path-set below (the diff-gate runs *active*, not neutral). The fidelity scan
(`scan-path-manifest`) additionally requires the declared count and SHA256 to
match the fenced block.

This is a **code** PR. It adds a NEW pure, idempotent, desired-state forge module
`validators/creator_engine_validator/forge/change.py` exposing `open_change()` (the
§5.1 step-5 / §8.1 step-4 "PR opened" primitive) and a frozen, secret-free `ChangeRef`,
behind the already-merged injectable `GhRunner` seam (ZERO live network in CI; the
default `gh`-shelling runner is `# pragma: no cover`). It MODIFIES only
`validators/creator_engine_validator/forge/__init__.py` to export the three new symbols
(`open_change`, `ChangeRef`, `OpenChangeRefused`). It registers **no** `@register` check,
adds **no** schema, and calls **no** `register_backend` -> `--list-checks` is **unchanged
at 43** and `available_backends()` is unchanged at `('gvisor-proxy', 'local-noop')`; no
`ce_cli.py`/wheel change. The byte-unchanged sibling forge modules
(`github_repo_config.py`, `scoped_token.py`, `plan_approval.py`) are reused by import only
and are out of this diff.

- **base:** `2e440f53d62239de54c4aff5b204836df95921b2`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=b50e5114ec10f418315e90ae328d4ff67fbdd26fff2400a9d8f2aa1b4b0ea568

```text
.ce/pr-path-manifest.md
validators/creator_engine_validator/forge/__init__.py
validators/creator_engine_validator/forge/change.py
validators/tests/unit/test_open_change.py
```
