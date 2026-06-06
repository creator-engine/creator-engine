# PR path manifest — v3 G-3.7.1 App-JWT mint seam (forge/app_jwt_runner.py)

This file is the **carrier** for this PR's ratified closed manifest (the
convention defined in `docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`).
CI (`.github/workflows/validate.yml`) passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`,
which enforces that this PR's `base..HEAD` diff equals exactly the authorized
path-set below (the diff-gate runs *active*, not neutral). The fidelity scan
(`scan-path-manifest`) additionally requires the declared count and SHA256 to
match the fenced block.

This is the third (CI-pure) slice of the **G-3.7 live spike**. It adds a new
`forge/app_jwt_runner.py` supplying the App-authenticated runner
`mint_scoped_token` needs: it mints a short-lived RS256 GitHub App JWT behind an
**injectable signer** (the App private key never enters the module) and issues the
installation-token POST with `Authorization: Bearer <JWT>` behind an **injectable
HTTPS transport**, returning a `GhRunner`-shaped `(argv, input_text) ->
CompletedProcess` so `mint_scoped_token` consumes it **byte-unchanged**.

Doc-grounded (current GitHub-App docs): `gh`/`gh api` cannot authenticate as a
GitHub App via a JWT — it sends `Authorization: token`, but App auth requires
`Bearer`, and a `-H` flag would leak the JWT into argv — so the mint leg is a
direct-HTTPS Bearer adapter, NOT a `gh` shell. The App JWT uses RS256 with
`iss`=client id, `iat`=now−60s, `exp`=now+540s (under the 10-minute ceiling); the
JWT lives in the in-process Bearer header ONLY (never argv/body/log/the returned
process/disk). RED→GREEN, **CI-pure** (fakes for signer + transport; the lone
live `urllib` transport is `# pragma: no cover`; ZERO real network/`gh`/PEM/PR).
It touches **no** schema/spine/check/backend/CLI/wheel surface and adds **no**
dependency (stdlib only) -> `--list-checks` is **unchanged at 43** and
`available_backends()` is unchanged at `('gvisor-proxy', 'local-noop')`;
`check-examples` stays 77/0. The runner is NOT yet wired into `run_assembly` (that
is the live 3.7.3); `scoped_token.py` is byte-unchanged. Corrections-of-record +
the verified ground truth are in
`.hermes/research/v3-g3-7-live-spike-planning-20260606T053007Z/REGROUNDING_LEDGER_G3_7_20260606T063941Z.md`.

- **base:** `91af464325be591ca1879cad7ff74e2a3e5e059b`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=fb737bdaea28b50928308a8911161e3143ce739ff923033e366330d62fd4a971

```text
.ce/pr-path-manifest.md
validators/creator_engine_validator/forge/__init__.py
validators/creator_engine_validator/forge/app_jwt_runner.py
validators/tests/unit/test_app_jwt_runner.py
```
