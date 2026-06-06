# PR path manifest — v3 G-3.6b roadmap status-flip (`docs/v3-roadmap.md`)

This file is the **carrier** for this PR's ratified closed manifest (the
convention defined in `docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`).
CI (`.github/workflows/validate.yml`) passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`,
which enforces that this PR's `base..HEAD` diff equals exactly the authorized
path-set below (the diff-gate runs *active*, not neutral). The fidelity scan
(`scan-path-manifest`) additionally requires the declared count and SHA256 to
match the fenced block.

This is a **docs-only** PR. It updates `docs/v3-roadmap.md` to reflect that
**G-3.6b** (the offline composition-root assembly — `run_assembly.py`
`make_run_driver` wires the minter→runner `ScopedToken` bridge [a closure cell
sharing the one live token from `mint_scoped_token` into `authenticated_gh_runner`]
+ the production `token_minter` / `change_opener` [over `open_change(…,
apply=False)`] + the G-3.5 `file_evidence_sink` into one offline `run_plan()`
drive, with `revoke_scoped_token` in a `finally`; plus the injectable
`run_plan(evidence_sink=…)` seam + a post-`teardown` success-path persist in
`orchestrator.py`; PR #138, merge commit `2245426`) is MERGED. It flips the
G-3.6b gate-status row (`#138` / `2245426` / MERGED), advances the status-summary
prose + PR list (`…, #138`) + the "What's next" pointer (G-3.0…G-3.6b merged;
**G-3.7 next**), and adds the G-3.6b code-location notes to the "Where the v3
code lives" table (a new `run_assembly.py` composition-root row + the
`orchestrator.py` `run_plan(evidence_sink=…)` annotation). It touches **no**
Python, schema, or check surface → `--list-checks` is **unchanged at 43** and
`available_backends()` is unchanged at `('gvisor-proxy', 'local-noop')`; no
`ce_cli.py`/wheel change. The draft passes `ce_terminology_v2` and
`no_limitless_strings`.

- **base:** `2245426094ec5ff4948918b004ab0f27593af719`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=2

AUTHORIZED_PATHS_SHA256=66e7ad7ab04be13723de672338c4ee9eacc4ab3f2c3977350b8a3d52a9c47cb6

```text
.ce/pr-path-manifest.md
docs/v3-roadmap.md
```
