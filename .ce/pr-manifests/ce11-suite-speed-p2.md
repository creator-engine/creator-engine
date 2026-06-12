# PR path manifest — ce-ops#11 · suite-speed PHASE 2 (zero-tolerated-failure surface + local fast lane)

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce11-suite-speed-p2
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below
(the carrier lists itself); the repo-wide fidelity scan requires the declared count and
SHA256 to match the fenced block.

Ratified gate:
Operator-RATIFIED ce-ops#11 phase-2 gate spec
(`designs/ce-11-suite-speed-gate-spec-DRAFT-20260612.md`, sha `61110faa…`); the W2 fork
was resolved to the **conftest-derived `sweep` marker** (RECOMMENDED, 6-row manifest) and
the roadmap row (manifest row 6) was pre-authorized to **DROP if no lane row exists** at
execution time. Re-ground confirmed `docs/v3-roadmap.md` carries no suite-speed row →
row 6 dropped → **5-row manifest**. Tests/docs-only mutation class; **no wheel pair, no
registry/counter movement** by construction (zero `validators/creator_engine_validator/**`
or `validators/wheelhouse*/**` diffs → `verify_wheel_matches_source` green by construction).

Base:
`4878306de4642a9126370607849e5b28143ebe4c` (origin/main = #208). The ratified spec pinned
`0e379d91` (#206); main moved #206→#207→#208 (the D3 mcp-fix), a base-only motion
pre-authorized under the base-only-refresh micro-auth and declared by the orchestrator. The
§8 re-ground re-verified at this base all seven conditions: (1) `validate.yml` single xdist
invocation intact; (2) conftest fixtures/markers as cited; (3) the two target test functions
at their cited assertions; (4) `.claude/hooks/*.sh` all `100755` in the git index; (5) exactly
12 `check_examples_result` consumers; (6) no in-flight PR touches any manifest row; (7) no
suite-speed roadmap row → row 6 dropped. None of the #207/#208 drift touches a manifest path.

Per-file purpose (the closed path-set — 5 paths):
- **`.ce/pr-manifests/ce11-suite-speed-p2.md`** *(A)* — this carrier (self-inclusive).
- **`validators/tests/conftest.py`** *(M)* — W2: register the `sweep` marker + a
  `pytest_collection_modifyitems` hook that auto-marks every consumer of the session-scoped
  `check_examples_result` fixture, so the fast lane (`-m "not sweep"`) is derived from a
  fixture-request property, not a hand-maintained list. No existing fixture touched.
- **`validators/tests/unit/test_orchestrator.py`** *(M)* — W1b: monkeypatch
  `gvisor_proxy_backend.shutil.which` to deterministic absence in
  `test_gvisor_backend_unavailable_raises_backend_unavailable` so the refusal CONTRACT is
  asserted on every host (runsc installed or not); add a hermetic positive-probe companion
  `test_gvisor_subprocess_runner_available_when_binary_present` (stub executable via the
  injectable `binary=` seam, zero live runsc). All other tests byte-identical.
- **`validators/tests/integration/test_claude_hook_pack_settings.py`** *(M)* — W1a:
  umask-independent mode assertion in `test_hook_scripts_are_executable_posix_sh` — assert
  the git-index mode `100755` (the durable repo property) + an owner-exec on-disk sanity
  check, replacing the `mode == 0o755` equality that failed under non-022 umasks. Shebang
  and `sh -n` assertions unchanged. All other tests byte-identical.
- **`validators/README.md`** *(M)* — document the three sanctioned invocations
  (full-serial · full-parallel = the merge-green gate · fast lane `-m "not sweep"`) and the
  rule that the fast lane is NEVER valid green-gate evidence (extends the dev/test section).

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=22ceafc6bba854fae3375567c409b53417636b3e10a93163b04337b18dd59762

```text
.ce/pr-manifests/ce11-suite-speed-p2.md
validators/README.md
validators/tests/conftest.py
validators/tests/integration/test_claude_hook_pack_settings.py
validators/tests/unit/test_orchestrator.py
```
