# PR path manifest — v3 G-3.7.0a revoke-routing fix + child-env scrubber

This file is the **carrier** for this PR's ratified closed manifest (the
convention defined in `docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`).
CI (`.github/workflows/validate.yml`) passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`,
which enforces that this PR's `base..HEAD` diff equals exactly the authorized
path-set below (the diff-gate runs *active*, not neutral). The fidelity scan
(`scan-path-manifest`) additionally requires the declared count and SHA256 to
match the fenced block.

This is the first (CI-pure) hardening slice of the **G-3.7 live spike**. It
(a) FIXES the load-bearing revoke-routing bug — `run_assembly.make_run_driver`
revoked the JIT scoped token through the **App-level** `gh_runner`, but
`DELETE /installation/token` must authenticate **AS the token being revoked**;
the fix routes the revoke through `authenticated_gh_runner(token, spawn=spawn)`,
best-effort in the `finally` (a revoke-transport failure is swallowed and made
alertable value-free — it never masks the run exception nor manufactures a
success-path error) — and (b) adds a **child-env scrubber** to
`authenticated_gh_runner` so an inherited host var can neither echo the token
(`GH_DEBUG`) nor redirect the `Authorization` header to a non-github host
(`GH_HOST`/`GITHUB_API_URL`/`GH_CONFIG_DIR`) nor leak the GitHub App private key
(any `*_PEM`/`*PRIVATE_KEY*`/`*APP_KEY*` var) into the child `gh` env. RED→GREEN,
**CI-pure** (every path driven by fakes; `subprocess`/`socket`/`Path.write_text`
monkeypatched to explode; ZERO real `gh`/network/disk/PR). It touches **no**
schema/spine/check/backend/CLI/wheel surface -> `--list-checks` is **unchanged at
43** and `available_backends()` is unchanged at `('gvisor-proxy', 'local-noop')`;
`check-examples` stays 77/0. Corrections-of-record + the verified ground truth are
in `.hermes/research/v3-g3-7-live-spike-planning-20260606T053007Z/REGROUNDING_LEDGER_G3_7_20260606T063941Z.md`.

- **base:** `8466cdaa75bc47c7e9651b45c95d53b35ee125f6`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=50ed59d138511b118f8bc0eb5b0b388ad31d009fbb1c8eb3f8aa75f516dd8662

```text
.ce/pr-path-manifest.md
validators/creator_engine_validator/forge/credential_runner.py
validators/creator_engine_validator/run_assembly.py
validators/tests/unit/test_credential_runner.py
validators/tests/unit/test_run_assembly.py
```
