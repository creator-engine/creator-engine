# PR path manifest — v3 G-3.9 version coexistence / separation

This file is the carrier for this PR's closed path manifest under
`docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`. CI passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below. The fidelity scan (`scan-path-manifest`) additionally requires the
declared count and SHA256 to match the fenced block.

Scope: **G-3.9 — version coexistence / separation** (replaces the spec §6
"deletion plan"). This is an **additive** gate; **CE v1.0 is retained whole, v1
deleted = ∅**. It declares the v1/v3/shared version-line taxonomy
(`validators/creator_engine_validator/_versions.py`) and adds the
`version_boundary` check (registered #44 in `checks/__init__.py`,
`checks/version_boundary.py`) that guards the **v1⊥v3** boundary — a HARD
runtime⊥runtime invariant plus a baselined `shared→version` allowlist ratchet —
with unit tests (`validators/tests/unit/test_version_boundary.py`) and the
contract doc (`docs/architecture/VERSION_BOUNDARY.md`). README / GOVERNANCE /
CONTRIBUTING gain coexistence wording; `docs/v3-roadmap.md` flips the G-3.9 row
to coexistence. The seven `validators/tests/unit/test_*.py` edits bump the
absolute registered-check count snapshot 43 → 44 (the only effect of adding the
check; each module-under-test still registers no check of its own). No v1 module
is removed; no behavior is stripped; the executable surface change is exactly the
one new check (`--list-checks` 43 → 44; `check-examples` STAYS 77/0).

- **base:** `b33b01ef1203dbd0d85fff48eef8714c8333133f`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=17

AUTHORIZED_PATHS_SHA256=cb241bc76a4bdd3e20d25edaf4daee3d8b359783ba2c9bfe3bbbe8c2a0981258

```text
.ce/pr-path-manifest.md
CONTRIBUTING.md
GOVERNANCE.md
README.md
docs/architecture/VERSION_BOUNDARY.md
docs/v3-roadmap.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/checks/__init__.py
validators/creator_engine_validator/checks/version_boundary.py
validators/tests/unit/test_app_jwt_runner.py
validators/tests/unit/test_change_status.py
validators/tests/unit/test_credential_runner.py
validators/tests/unit/test_evidence_sink.py
validators/tests/unit/test_merge.py
validators/tests/unit/test_open_change.py
validators/tests/unit/test_redact.py
validators/tests/unit/test_version_boundary.py
```
