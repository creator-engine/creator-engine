# PR path manifest — ce38-work-claims · ce-ops#38 Work-Claim Locks

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce38-work-claims
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below
(the carrier lists itself); the repo-wide fidelity scan requires the declared count and
SHA256 to match the fenced block.

Ratified gate:
Operator-RATIFIED rev-3 gate spec `ce-38-work-claims-gate-spec-RATIFIED-20260612.md`
(file sha256 `682319dac6caa520aea7bc4aff5323ba415c509baf932031e090fae8c700b184`) on ce-ops#38.
Pinned @ `c486cf71`. Re-grounded at execution: `gh issue view 38` + `git log -1` confirm the pin is
current `main` and no newer requirement invalidates the spec; the legacy `🔒 in-compose ce-dev-2`
lock comment is present and is treated as legacy claim evidence by the implementation.

Base:
`c486cf71fead3bd58ccd9cbbb1525ebb38cdcbbe` (`main` = #217, the 0.1.0→0.2.0 dev-process
self-hosting bump). The closed manifest's wheel pair is the 0.2.0 app wheel; the path-set + hash are
satisfiable at this base.

OPERATOR-RATIFIED MANIFEST AMENDMENT (15 → 17 paths, 2026-06-12):
The ratified rev-3 manifest (15 paths, hash `24e983e6…`) was UNSATISFIABLE: the spec-mandated
top-level `ce claim` group (acceptance gate #3) trips two `test_v1_docs_reconciliation.py` guards —
the hardcoded as-built `ce` inventory and the README-documents-every-group check — yet neither
`README.md` nor `validators/tests/unit/test_v1_docs_reconciliation.py` was in the closed manifest.
No code-side workaround exists (a new top-level `ce` group always trips the inventory guard). The
Operator ratified adding exactly those two paths (15 → 17), recomputing the path-set hash to
`2bf0c995…`. `README.md` now documents `ce claim`; the inventory set adds `"claim"`. This is the
only amendment; all other paths and behavior are unchanged from the rev-3 mandate.

DECLARED DEVIATION (forced by the closed manifest — `--ticket` optional):
The spec ratifies `--ticket` as REQUIRED on `cev3 drive --spawn` / `cev3 review --spawn`. The
manifest does NOT include `validators/tests/unit/test_v3_cli.py`, whose existing `--spawn` tests (and
the pr/collect/review/merge/e2e fixtures built on them) invoke `--spawn` WITHOUT a ticket. Enforcing
`required` would fail 47 in-suite tests this carrier may not touch — violating acceptance criterion
#1 (zero out-of-manifest diffs). Rather than expand the manifest further, `--ticket` is implemented
as OPTIONAL-but-HONORED on the v3 spawn paths: when supplied, the claim is acquired + verified before
any dispatch/venue side effect (a foreign active claim refuses the spawn); when absent, legacy
behavior is preserved. This mirrors the v1 `--claim-ticket` posture and the spec's own
"manual-dispatch gap" mitigation. The full required-ticket enforcement is a follow-up that must
re-open this gate spec to add `test_v3_cli.py` to the manifest.

The change (rev-3 MVP):
A new shared, version-neutral `work_claims.py` runtime (ticket parser, structured + legacy marker
parsers, the pure deterministic state machine, and the `acquire`/`release`/`status` operations over
an injectable `GhRunner`) — imports no v1, no v3, and not `forge.*`, so it stays `shared` by
classification and the V1=23 / V3=36 / registry=53 counters are UNCHANGED. `ce claim
acquire|release|status` is the user-facing MVP; `cev3 drive/review --spawn --ticket` and v1
`ce launch`/`ce lane launch --claim-ticket` acquire+verify the claim before any side effect. The
Cockpit gains a view-only `claims.json` cache → `load_claims()` seam → pure `_fold_claims` →
`snapshot["claims"]` → an L3 ops-board band (cache is display data only; dispatch never reads it).
The app wheel + `SHA256SUMS` are rebuilt from this branch's source (mandatory wheelhouse rule).

Per-file purpose (the closed path-set — 17 paths):
- **`.ce/pr-manifests/ce38-work-claims.md`** *(A)* — this carrier (self-inclusive).
- **`README.md`** *(M)* — document the `ce claim acquire|release|status` group in the v1 `ce`
  command table (the docs-reconciliation guard requires every shipped group be documented).
- **`docs/architecture/work-claim-locks.md`** *(A)* — the prose design of record (authority,
  honest non-hard-lock posture, atomic dispatch posture, code shape, Cockpit feed, rollback).
- **`validators/creator_engine_validator/work_claims.py`** *(A)* — the shared claim runtime
  (parser, marker grammar, pure state machine, `acquire`/`release`/`status`, view-only cache writer;
  private `GhRunner`/`gh api` copy — no `forge.*` import).
- **`validators/creator_engine_validator/ce_cli.py`** *(M)* — the `ce claim acquire|release|status`
  group + `--claim-ticket` on `ce launch`/`ce hud`/`ce lane launch` (acquire-before-side-effect,
  best-effort release on a refused launch leg).
- **`validators/creator_engine_validator/v3_cli.py`** *(M)* — `--ticket` on `cev3 drive`/`review`;
  the claim hook acquires+verifies before `materialize_dispatch`/`materialize_review_dispatch` and
  best-effort-releases on a spawn refusal (see DECLARED DEVIATION re: optional `--ticket`).
- **`validators/creator_engine_validator/forge/__init__.py`** *(M)* — docstring amendment naming the
  ce-ops#38 exception: live forge access is no longer exclusively under `forge/` (the shared
  `work_claims` runtime also talks to a live forge, with its own `GhRunner` copy).
- **`validators/creator_engine_validator/runner/cockpit_readmodel.py`** *(M)* — `CLAIMS_SUBDIR`,
  `load_claims()`, the pure `_fold_claims`, the `claims` input + availability bit on `fold_snapshot`,
  `snapshot["claims"]`, and `watch_paths` support (fold stays pure; I/O only in the load seam).
- **`validators/creator_engine_validator/v3_cockpit.py`** *(M)* — the L3 work-claim band rendered
  from the precomputed `snapshot["claims"]` only (no governance computation in the view).
- **`validators/tests/unit/test_work_claims.py`** *(A)* — ticket/marker parsers, malformed refusal,
  legacy lock, deterministic winner + tie-break, release matching, stale status, takeover,
  idempotency replay, fake-`GhRunner` API shapes, lost-reread fail-closed.
- **`validators/tests/unit/test_ce_claim_cli.py`** *(A)* — `ce claim` CLI exit contract, JSON,
  ambiguous-ticket / unavailable-`gh` / conflict refusals, cache write.
- **`validators/tests/unit/test_v3_claim_dispatch.py`** *(A)* — `cev3 drive/review --spawn --ticket`
  claims before materialization; foreign claim → no dispatch dir / no spawn; spawn refusal posts a
  best-effort release; no-ticket path unchanged.
- **`validators/tests/unit/test_cockpit_claims.py`** *(A)* — `load_claims()` tolerance, pure fold
  section, stale/invalid counts, availability honesty, L3 render binding (textual-guarded).
- **`validators/tests/unit/test_v1_docs_reconciliation.py`** *(M)* — add `"claim"` to the as-built
  `ce` inventory guard (the README documentation assertion is satisfied by the README edit above).
- **`validators/tests/unit/test_wheelhouse_built_surface.py`** *(M)* — assert the built `ce` wheel
  registers the `claim acquire|release|status` surface.
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* — app wheel
  rebuilt from this branch's source (the byte-parity guard checks every bundled `.py` against source).
- **`validators/wheelhouse/SHA256SUMS`** *(M)* — re-pinned for the rebuilt app wheel (line 2).

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=17

AUTHORIZED_PATHS_SHA256=2bf0c995224c4943c7575f78d4f128d3345394e77f8f90d5edc924de70a9e9b8

```text
.ce/pr-manifests/ce38-work-claims.md
README.md
docs/architecture/work-claim-locks.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/forge/__init__.py
validators/creator_engine_validator/runner/cockpit_readmodel.py
validators/creator_engine_validator/v3_cli.py
validators/creator_engine_validator/v3_cockpit.py
validators/creator_engine_validator/work_claims.py
validators/tests/unit/test_ce_claim_cli.py
validators/tests/unit/test_cockpit_claims.py
validators/tests/unit/test_v1_docs_reconciliation.py
validators/tests/unit/test_v3_claim_dispatch.py
validators/tests/unit/test_wheelhouse_built_surface.py
validators/tests/unit/test_work_claims.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
