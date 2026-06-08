# PR path manifest — feat(v3): G-7.1 session frame + unified context/spend status line

This file is the carrier for this PR's closed path manifest under
`docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`. CI passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below. The fidelity scan (`scan-path-manifest`) additionally requires the
declared count and SHA256 to match the fenced block.

Scope: **G-7 slice 7B — the session frame + the unified resource status line**
(the second ratified G-7 product-surface slice, atop 7A's `cev3` CLI). Adds a NEW
v3-classified PURE render module `v3_session.py` and enriches `cev3 session` to
render the branded **"your agent, under CE"** frame: a launch banner + ONE
persistent status line fusing (a) the canon **stage skin**
(Frame→Shape→Build→Review→Ship, counts) reused from `coordination` — no third
vocabulary; (b) the **context-window meter** (GH #157 — `warn ≥ 45% / urgent ≥
60%`, the harness number CONSUMED never recomputed); and (c) the **spend meter**
(the G-5 `runner.spend_gate.project_spend` projection vs the run cap, reusing the
soft `SOFT_BREACH_RATIO` / hard ratios verbatim). Nudges are **boundary-aware**
(the checkpoint/`/clear` nudge fires only at a turn boundary; a hard spend breach
surfaces immediately). The decision is documented in
`docs/architecture/session-status-line.md` (project-level / CE-native surface —
survives the governed `--setting-sources project` posture).

Boundary (CI-pure): `v3_session.py` is the pure render + threshold + nudge logic
fed `(context_pct, spend projection)`; the spend meter folds the REAL G-5
projection. The LIVE `statusLine`-command tap into a running TUI (the per-turn
context read + line wiring) is the named DEFERRED seam — exactly the G-4/G-5/G-6
cut.

Standing requirements honored: **v1↔v3 coexistence** (ADDITIVE; **v1 deleted = ∅**;
no v1 module touched); **G-4.1 naming hygiene** (`v3_session` v3-classified +
residue-clean; default surface root `.ce/state`, never `.hermes/`/`.claude/`;
`v3_naming_hygiene` GREEN 0/0); **version boundary** (`v3_session`→`coordination` /
`runner.spend_gate` are v3→v3 edges; `v3_cli`→`v3_session` v3→v3; no `shared→v3`
edge; `version_boundary` GREEN 0/0; `V3_RUNTIME` **22→23**); **vocabulary fidelity**
(the stage skin derives from the canon dual-mapping; no third vocabulary); the
**unified meter** reuses the G-5 ratios as the single source of truth. Check
surface unchanged (**47** — no registered check). `check-examples` stays **78/0**
(the new doc carries no example fixtures; no malformed examples added).
**Rebased onto #165 (`554b263`, the Completion-Report 3rd-canon-pass docs)** per
the concurrent-PR discipline — content-disjoint from that docs PR; only the shared
carrier was resolved. Deferred follow-ons (named): the live status-line tap; the
shaping detect-and-offer dialogue (7C); the ◆ CE Completion Report (7D).

- **base:** `554b263` (origin/main after #165).
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=ba4f0f0e35c14b822b1168026f341e3630ea3b12e4fec09da6cf0ba5ed01245b

```text
.ce/pr-path-manifest.md
docs/architecture/session-status-line.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/v3_cli.py
validators/creator_engine_validator/v3_session.py
validators/tests/unit/test_v3_cli.py
validators/tests/unit/test_v3_session.py
validators/tests/unit/test_version_boundary.py
```
