# PR path manifest — v3 G-3.1 orchestrator wiring (`run_plan` → `forge.open_change`)

This file is the **carrier** for this PR's ratified closed manifest (the
convention defined in `docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`).
CI (`.github/workflows/validate.yml`) passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`,
which enforces that this PR's `base..HEAD` diff equals exactly the authorized
path-set below (the diff-gate runs *active*, not neutral). The fidelity scan
(`scan-path-manifest`) additionally requires the declared count and SHA256 to
match the fenced block.

This is a **code** PR (G-3.1). It threads the audited run's in-manifest work into
the already-merged `forge.open_change()` from the thin orchestrator so the §5.1
lifecycle ends at "PR opened" rather than "evidence collected":

- `runner/backend.py` adds a value-free, frozen `RunChangeSet`
  (`branch`/`base`/`manifest_paths`/`head_sha` — desired-state POINTERS only, NO
  diff blob, NO secret) and an optional, defaulted `change_set` field on both
  `RunResult` and `CollectedEvidence` (defaults preserve every existing
  construction — backward-compatible).
- `runner/__init__.py` re-exports `RunChangeSet`.
- `orchestrator.py` adds an injected `change_opener: ChangeOpener | None = None`
  seam on `run_plan` (mirroring the `token_minter`/`approval_resolver` idiom,
  keyword-only, `None` ⇒ the existing G-2.x lifecycle, unchanged). After
  `collect`, when a `change_opener` is injected and the run produced a change-set,
  it opens/claims the PR **plan-by-default** (the production closure captures the
  repo + a `gh_runner` factory and calls `forge.open_change(..., apply=False)` —
  the orchestrator passes a factory, never a raw token), attests the resulting
  value-free `ChangeRef` as a terminal `change-opened` record, and folds it into
  the returned evidence. `ChangeRef` is referenced under `TYPE_CHECKING` only, so
  the orchestrator imports ZERO from `forge` at runtime.
- `tests/unit/test_orchestrator.py` adds the wiring/attestation/backward-compat
  tests, driving the open-change path through a **fake `GhRunner`** as the sole
  transport (`subprocess.run`/`Popen`/`socket.socket` monkeypatched to explode —
  zero live network/subprocess in CI).

It registers **no** `@register` check, adds **no** backend (`register_backend`)
and **no** schema → `--list-checks` is **unchanged at 43** and
`available_backends()` is unchanged at `('gvisor-proxy', 'local-noop')`. All of
`forge/*`, `runner/audit_overlay.py`, `runner/noop_backend.py`, `cli.py`,
`ce_cli.py`, `pyproject.toml` and `requirements*` are **byte-unchanged**
(`forge.open_change`/`ChangeRef`/`GhRunner` reused by import; `forge.__all__`
unchanged). No `ce_cli.py`/wheel change.

- **base:** `a8f7c422a56e45da76f9f55b106175b24692bcc3`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=6621ecafe346804648a0ef7fbb827152b37a1c8ba211c78dfe74e73a3890641d

```text
.ce/pr-path-manifest.md
validators/creator_engine_validator/orchestrator.py
validators/creator_engine_validator/runner/__init__.py
validators/creator_engine_validator/runner/backend.py
validators/tests/unit/test_orchestrator.py
```
