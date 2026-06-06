# PR path manifest — v3 G-3.7.0b gh-stderr redaction sweep + opaque-token regression

This file is the **carrier** for this PR's ratified closed manifest (the
convention defined in `docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`).
CI (`.github/workflows/validate.yml`) passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`,
which enforces that this PR's `base..HEAD` diff equals exactly the authorized
path-set below (the diff-gate runs *active*, not neutral). The fidelity scan
(`scan-path-manifest`) additionally requires the declared count and SHA256 to
match the fenced block.

This is the second (CI-pure) hardening slice of the **G-3.7 live spike**. It
adds a shared `forge/_redact.py` helper (`redact_gh_stderr`, stdlib `re` only)
that masks token / JWT / `Authorization`-header material in a `gh` subprocess's
stderr **before** that stderr is interpolated into a `ForgeConfigError` message
(a message that may be logged or surfaced into the runtime-evidence chain), and
applies it at **all 11 leak sites across the 6 forge ops** that today interpolate
raw `stderr.strip()` into an exception (`scoped_token` ×2, `change` ×2, `merge`
×1, `change_status` ×1, `github_repo_config` ×3, `plan_approval` ×2). It also
adds an **opaque-token regression**: a ~520-char `ghs_<appid>_<jwt>` installation
token flows verbatim through mint (no length/format assumption) and is fully
masked by the redactor regardless of length. This is **belt-and-suspenders** —
the primary custody invariant (the token lives only in the child `gh` env, never
in argv/stderr) is unchanged from G-3.4/G-3.7.0a; this slice adds a secondary net.
RED→GREEN, **CI-pure** (every path driven by fakes; `subprocess`/`socket`/
`Path.write_text` monkeypatched to explode; ZERO real `gh`/network/disk/PR). It
touches **no** schema/spine/check/backend/CLI/wheel surface -> `--list-checks` is
**unchanged at 43** and `available_backends()` is unchanged at
`('gvisor-proxy', 'local-noop')`; `check-examples` stays 77/0. The two `checks/*`
`stderr.strip()` sites (`role_boundary_attribution.py`, `path_manifest_fidelity.py`)
interpolate `git diff` plumbing stderr (no credential material) and are OUT of
scope. Corrections-of-record + the verified ground truth are in
`.hermes/research/v3-g3-7-live-spike-planning-20260606T053007Z/REGROUNDING_LEDGER_G3_7_20260606T063941Z.md`.

- **base:** `856a8d0a5f83dbb8c6e1bde5dbb5e4ab49f6ee09`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=15

AUTHORIZED_PATHS_SHA256=d792b21a314d9f220e2c7b9bbbc4fc14bc1fe368abd8059911f352d19c8fb440

```text
.ce/pr-path-manifest.md
validators/creator_engine_validator/forge/_redact.py
validators/creator_engine_validator/forge/change.py
validators/creator_engine_validator/forge/change_status.py
validators/creator_engine_validator/forge/github_repo_config.py
validators/creator_engine_validator/forge/merge.py
validators/creator_engine_validator/forge/plan_approval.py
validators/creator_engine_validator/forge/scoped_token.py
validators/tests/unit/test_change_status.py
validators/tests/unit/test_github_repo_config.py
validators/tests/unit/test_merge.py
validators/tests/unit/test_open_change.py
validators/tests/unit/test_plan_approval.py
validators/tests/unit/test_redact.py
validators/tests/unit/test_scoped_token.py
```
