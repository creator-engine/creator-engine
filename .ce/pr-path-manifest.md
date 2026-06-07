# PR path manifest — feat(v3): G-4.1 v3 naming-hygiene guard + neutral local-state convention

This file is the carrier for this PR's closed path manifest under
`docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`. CI passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below. The fidelity scan (`scan-path-manifest`) additionally requires the
declared count and SHA256 to match the fenced block.

Scope: **ADDITIVE** small green-now gate (G-4.1) keeping the v3 surface decoupled
from CE bootstrapping-harness residue **by machine**. A new self/structural check
`v3_naming_hygiene` (registered #45; sibling to `version_boundary`) FAILs on
`.hermes`/`Hermes`/`Nefarious` in the v3 CODE surface (`_versions` taxonomy) and
the declared v3 SCHEMA surface (`_versions.V3_SCHEMAS`) — green-on-day-one +
ratchet (`BASELINE_V3_NAMING_ALLOWLIST` EMPTY); legit adapter names
(Claude/gVisor/Codex/ACP/OpenShell) carved out; v3 docs + v1/shared + legacy
corpus excluded. A neutral `.ce/state` local-state convention
(`_versions.V3_LOCAL_STATE_ROOT`; the `evidence_sink(root)` seam already supports
it — never `.hermes/`, never `.claude/`). A standing requirement (roadmap +
`docs/contracts/v3-naming-hygiene.md`) that G-5…G-7 prompts cite both. Folds the
deferred G-4 roadmap-SHA fill (`#154` → `ec4eb3a`).

Invariants held: **v1 deleted = ∅** (no v1 runtime module modified); `version_boundary`
(#44) STAYS GREEN (0/0); the new check is `shared` and imports only `_versions`
(shared→shared) + `version_boundary` discovery helpers — no `shared→v3` edge;
`--list-checks` 44 → **45**; `check-examples` STAYS **78/0** (self/structural check
— teeth carried by the unit tests, not a per-dir example pair). Explicitly deferred:
the full legacy-terminology-corpus migration (`specs/001`/`002` + docs) + the v1
`.hermes/`→`.ce/` rename = one separate post-pilot terminology/naming gate.

Note: rebased onto `origin/main = 6da4079` after the disjoint site PR #155
(`docs/index.html` + its own carrier only) merged; base updated accordingly so the
head-pinned merge stays no-drift. The 7 `validators/tests/unit/test_*` count-pin
bumps (44→45) are the "registers no check" / "purity unchanged" assertions that
legitimately shift when the new #45 check registers; `test_version_boundary.py`
likewise.

- **base:** `6da40798433188ee7f6b2ee990627030f30c998d`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=16

AUTHORIZED_PATHS_SHA256=970d6181d3cff5ada0e9919981e634d6459aa6c0a68facf8474737ad6c46bf8f

```text
.ce/pr-path-manifest.md
docs/contracts/v3-naming-hygiene.md
docs/v3-roadmap.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/checks/__init__.py
validators/creator_engine_validator/checks/v3_naming_hygiene.py
validators/creator_engine_validator/evidence_sink.py
validators/tests/unit/test_app_jwt_runner.py
validators/tests/unit/test_change_status.py
validators/tests/unit/test_credential_runner.py
validators/tests/unit/test_evidence_sink.py
validators/tests/unit/test_merge.py
validators/tests/unit/test_open_change.py
validators/tests/unit/test_redact.py
validators/tests/unit/test_v3_naming_hygiene.py
validators/tests/unit/test_version_boundary.py
```
