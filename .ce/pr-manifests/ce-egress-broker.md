# PR path manifest - ce-egress-broker

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-egress-broker

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

Ratified:
RATIFIED BRIEF (Operator, 2026-06-20, "dispatch the egress relief"): build the
deterministic v0 of the ADR-0007 egress gateway / publish broker — a non-agent,
host-side broker that couriers a contained seat's signed commit to the forge
under fail-closed policy, attributed to the seat's own App. Strict TDD on the
verify/policy core; commit locally, do not push/merge.

The changes:
- A non-agent egress broker (`tools/egress-broker/`): a pure fail-closed policy
  core, host-side commit-fact extraction, generalized per-App minter +
  installation-id discovery, per-App config schema, append-only secret-free
  audit, the verify→mint→push→PR orchestration, and a thin CLI.
- Reuses (byte-unchanged) the frozen `forge.app_jwt_runner` / `forge.scoped_token`
  / `forge.change_push` / `forge.credential_runner` primitives; registers no
  validator check (the broker is host operations, not validator logic).
- Exhaustive unit tests under `validators/tests/unit/test_egress_*.py` (the
  CI-collected suite); a one-line conftest path addition makes the broker import
  root visible to that suite.
- A `docs/architecture/egress-broker.md` mapping v0 to ADR-0007 and what is
  deferred to the full gateway, plus a changelog fragment and this carrier.

Per-file purpose (the closed path-set - 23 paths; `(A)` add, `(M)` modify):
- **`.ce/changelog/ce-egress-broker.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce-egress-broker.md`** *(A)* - this carrier.
- **`docs/architecture/egress-broker.md`** *(A)* - ADR-0007 mapping + deferred.
- **`tools/egress-broker/README.md`** *(A)* - broker usage + safety invariants.
- **`tools/egress-broker/apps.example.json`** *(A)* - per-App config template
  (dev-1/2/3/4).
- **`tools/egress-broker/ce_egress_broker.py`** *(A)* - thin deterministic CLI.
- **`tools/egress-broker/egress_broker/__init__.py`** *(A)* - package surface.
- **`tools/egress-broker/egress_broker/audit.py`** *(A)* - append-only,
  secret-free JSONL audit + rate counter.
- **`tools/egress-broker/egress_broker/commit_facts.py`** *(A)* - host-side
  `%G?`/author extraction behind a git spawn seam.
- **`tools/egress-broker/egress_broker/config.py`** *(A)* - per-App + policy
  config schema + fail-closed loader.
- **`tools/egress-broker/egress_broker/installation.py`** *(A)* -
  `installation_id` discovery (`GET /app/installations`).
- **`tools/egress-broker/egress_broker/minter.py`** *(A)* - generalized per-App
  installation-token mint + openssl RS256 signer.
- **`tools/egress-broker/egress_broker/orchestrator.py`** *(A)* - verify → mint
  → push → open/update PR → revoke → audit.
- **`tools/egress-broker/egress_broker/policy.py`** *(A)* - the PURE fail-closed
  policy core (the TCB heart).
- **`validators/tests/conftest.py`** *(M)* - add the broker import root to the
  test path.
- **`validators/tests/unit/test_egress_audit.py`** *(A)* - audit tests.
- **`validators/tests/unit/test_egress_cli.py`** *(A)* - CLI tests.
- **`validators/tests/unit/test_egress_commit_facts.py`** *(A)* - extraction
  tests.
- **`validators/tests/unit/test_egress_config.py`** *(A)* - config tests.
- **`validators/tests/unit/test_egress_installation.py`** *(A)* - discovery
  tests.
- **`validators/tests/unit/test_egress_minter.py`** *(A)* - minter + signer
  tests.
- **`validators/tests/unit/test_egress_orchestrator.py`** *(A)* - orchestration
  tests.
- **`validators/tests/unit/test_egress_policy.py`** *(A)* - the policy-core TDD
  suite.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=23

AUTHORIZED_PATHS_SHA256=6a13975194c3f3d2982a9c78e1e3afaf8b6abaa9809982c1cb8402e21c8d4cb6

```text
.ce/changelog/ce-egress-broker.md
.ce/pr-manifests/ce-egress-broker.md
docs/architecture/egress-broker.md
tools/egress-broker/README.md
tools/egress-broker/apps.example.json
tools/egress-broker/ce_egress_broker.py
tools/egress-broker/egress_broker/__init__.py
tools/egress-broker/egress_broker/audit.py
tools/egress-broker/egress_broker/commit_facts.py
tools/egress-broker/egress_broker/config.py
tools/egress-broker/egress_broker/installation.py
tools/egress-broker/egress_broker/minter.py
tools/egress-broker/egress_broker/orchestrator.py
tools/egress-broker/egress_broker/policy.py
validators/tests/conftest.py
validators/tests/unit/test_egress_audit.py
validators/tests/unit/test_egress_cli.py
validators/tests/unit/test_egress_commit_facts.py
validators/tests/unit/test_egress_config.py
validators/tests/unit/test_egress_installation.py
validators/tests/unit/test_egress_minter.py
validators/tests/unit/test_egress_orchestrator.py
validators/tests/unit/test_egress_policy.py
```
