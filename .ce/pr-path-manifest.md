# PR path manifest — v3 G-3.6b offline composition-root assembly

This file is the **carrier** for this PR's ratified closed manifest (the
convention defined in `docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`).
CI (`.github/workflows/validate.yml`) passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`,
which enforces that this PR's `base..HEAD` diff equals exactly the authorized
path-set below (the diff-gate runs *active*, not neutral). The fidelity scan
(`scan-path-manifest`) additionally requires the declared count and SHA256 to
match the fenced block.

This PR builds the **G-3.6b offline composition root** — the first production
`run` driver. A new `run_assembly.py` `make_run_driver(...)` wires the already
fake-tested seams into ONE offline `run_plan(...)` drive that persists the run's
evidence: the production `token_minter` (over `forge.mint_scoped_token`/
`revoke_scoped_token` → the value-free `MintedCredential`), the **minter→runner
bridge** (a closure cell sharing the one live `ScopedToken` from the minter to
the `change_opener`'s authenticated `gh` runner via `authenticated_gh_runner`, so
the change-opener authenticates with the SAME minted token while the orchestrator
stays value-free), the production `change_opener` (over `forge.open_change(...,
apply=False)`), and the G-3.5 `file_evidence_sink`. The deferred-from-G-3.5
`run_plan(evidence_sink=…)` injectable + a post-`teardown` success-path persist
call-site land in `orchestrator.py` (the sink is injected; default `None` = no
I/O; `EvidencePersistRefused` propagates). The drive proves
**mint → authenticated runner → run → collect → typed `pr_opened` outcome →
persisted evidence**, entirely offline (a `RunChangeSet`-yielding fake backend +
a fake `GhRunner`/`spawn`/`write`, `subprocess`/`socket`/`Path.write_text`
monkeypatched to explode), with ZERO live side effects. `ScopedToken.value` lives
only in the composition root's closure cell and, at call time, only in the child
`gh` env — never the orchestrator, evidence, argv, input, log, disk, or the
parent env. `merge()` and the live drive (`apply=True`, App key) are DEFERRED to
G-3.7. No schema/spine/model change (the run-outcome model is settled in G-3.6a).
`--list-checks` is **unchanged at 43**; `available_backends()` is unchanged at
`('gvisor-proxy', 'local-noop')`; `check-examples` stays 77/0; no `ce_cli.py`/
wheel/requirements/pyproject change.

- **base:** `d7c6aa5fc67d5d6ce549c588ec2156d763404655`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=19e4520f9dcf8301cb45ca652275de0db317cf44f40cfc86f88b6859683301a4

```text
.ce/pr-path-manifest.md
docs/contracts/orchestrator.md
validators/creator_engine_validator/orchestrator.py
validators/creator_engine_validator/run_assembly.py
validators/tests/unit/test_orchestrator.py
validators/tests/unit/test_run_assembly.py
```
