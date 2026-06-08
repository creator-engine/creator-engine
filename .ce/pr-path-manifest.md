# PR path manifest — feat(v3): G-7.0 v3 work-driving CLI (cev3) + seat entry

This file is the carrier for this PR's closed path manifest under
`docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`. CI passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below. The fidelity scan (`scan-path-manifest`) additionally requires the
declared count and SHA256 to match the fenced block.

Scope: **G-7 slice 7A — the v3 work-driving CLI + seat-launch entry** (the first
of the ratified G-7 product-surface slices). Adds a NEW v3-classified module
`v3_cli.py` and a DISTINCT `cev3` console_script (alongside the retained v1 `ce`
launcher — additive, never a subcommand on `ce`/`ce_cli`). The CLI files / ratifies
/ drives / inspects work as a **Scope**: it surfaces the canon vocabulary (stage
phases Frame→Shape→Build→Review→Ship and the Scope-card labels
`Goal · Done-when · Budget · Change-type · Ready`) over the conserved schema
fields, and `drive` assembles the governed dispatch via
`coordination.assemble_dispatch` (the front gate — REFUSES unless DoR-ready AND
ratified; the appetite→cap `run` spend envelope is merged in for G-5). The LIVE
run spawn is the deferred seam (inputs produced, not executed) — exactly the
G-4/G-5/G-6 CI-pure cut.

Local state (G-4.1): Scope artifacts persist under the neutral CE-namespaced
`_versions.V3_LOCAL_STATE_ROOT` = `.ce/state` (NEVER `.hermes/`, NEVER
`.claude/`); `.gitignore` adds the targeted `.ce/state/` instance-zone line (no
wholesale `.ce/` ignore — governance subtrees stay trackable).

Standing requirements honored: **v1↔v3 coexistence** (ADDITIVE; **v1 deleted = ∅**;
no v1 module touched — the `cev3` script is additive and `packaging_runtime`'s
`CONSOLE_SCRIPTS` retention check passes unchanged); **G-4.1 naming hygiene**
(`v3_cli` is v3-classified + residue-clean; `v3_naming_hygiene` GREEN 0/0,
`BASELINE_V3_NAMING_ALLOWLIST` empty); **version boundary** (`v3_cli`→`coordination`
is a v3→v3 edge; v3→shared `_versions` allowed; no `shared→v3` edge —
`BASELINE_SHARED_TO_VERSION_ALLOWLIST` unchanged; `version_boundary` GREEN 0/0);
**vocabulary fidelity** (labels are a skin derived from `coordination`/the canon
dual-mapping — no third vocabulary; schema enums conserved); **grader-outside**
(the front gate is enforced by `coordination`, the human ratifies the bet).
Check surface unchanged (**47** — 7A adds no registered check). `V3_RUNTIME`
**21→22** (the `len(V3_RUNTIME)` pin in `test_version_boundary.py` is bumped).
`check-examples` stays **78/0** (no new bundled examples; Scope artifacts live in
the gitignored `.ce/state`). Deferred follow-ons (named): the session frame +
unified status line (7B); the shaping detect-and-offer dialogue (7C); the
◆ CE Completion Report + rich artifact awareness (7D); the live run spawn.

- **base:** `c90ce03a571804b4795c025357c78ca1cd970bd8`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=464c224a0f93150e8e085fd890f6ca1f553207eea301765d70ebe28223d4bd8a

```text
.ce/pr-path-manifest.md
.gitignore
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/v3_cli.py
validators/pyproject.toml
validators/tests/unit/test_v3_cli.py
validators/tests/unit/test_version_boundary.py
```
