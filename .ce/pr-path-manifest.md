# PR path manifest — feat(v3): G-7.2 Scope-shaping grill-me + chat→Scope detect-and-offer dial

This file is the carrier for this PR's closed path manifest under
`docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`. CI passes it to
`verify-path-manifest --base <PR base sha> --manifest .ce/pr-path-manifest.md`
and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below. The fidelity scan (`scan-path-manifest`) additionally requires the
declared count and SHA256 to match the fenced block.

Scope: **G-7 slice 7C — the Frame→Shape shaping dialogue** (the third ratified
G-7 product-surface slice, atop 7A's CLI + 7B's session frame). Adds a NEW
v3-classified PURE module `v3_shaping.py` + a `cev3 shape` command:

- **One grill-me engine, per-locus rubric = an existing CE check.** `shape(draft)`
  flags the missing/invalid DoR gaps using `coordination.scope_is_ready` as the
  rubric (reuses governance — does not re-derive "ready"); returns each gap's
  user-facing label + the minimum question + whether it is human-only.
- **Budget (`appetite`) is human-only** — `agent_may_draft` returns False for it;
  the grill-me flags it as the human's to set (the agent drafts every other field).
- **Change-type (`mutation_class`) is safe-by-default** — `retier()` lets the human
  TIGHTEN to a higher blast-radius class for free, but LOOSENING requires
  ratification (the agent can never unilaterally enlarge the permitted blast
  radius).
- **The chat→Scope detect-and-offer dial** — `should_offer(persona, mutation_class,
  signal)` implements `f(persona, risk-class)` at the conservative default
  (dev/low=clear · dev/high=explicit · ceo/low=actionable · ceo/high=clear; unknown
  → strictest). The offer is a cheap inline cancel-safe decision (never a modal);
  this decides only WHETHER it fires.

Implements the ratified design `docs/architecture/shaping-ux.md` (authored by the
design lane). Boundary (CI-pure): the engine + dial are pure decision logic; the
LIVE interactive chat invocation + the dial's telemetry-tune loop are named
DEFERRED seams — the G-4/G-5/G-6 cut.

Standing requirements honored: **v1↔v3 coexistence** (ADDITIVE; **v1 deleted = ∅**;
no v1 module touched); **G-4.1 naming hygiene** (`v3_shaping` v3-classified +
residue-clean; pure — no local state; `v3_naming_hygiene` GREEN 0/0); **version
boundary** (`v3_shaping`→`coordination` and `v3_cli`→`v3_shaping` are v3→v3 edges;
no `shared→v3` edge; `version_boundary` GREEN 0/0; `V3_RUNTIME` **23→24**);
**vocabulary fidelity** (the card uses the canon Scope-card labels over conserved
fields; the rubric IS the DoR predicate; no third vocabulary; schema enums
conserved); **grader-outside** (the rubric is `coordination.scope_is_ready`; the
human supplies the budget + ratifies). Check surface unchanged (**47** — no
registered check). `check-examples` stays **78/0**. Deferred follow-ons (named):
the live shaping chat + telemetry-tune loop; the ◆ CE Completion Report (7D); the
two-mode installer (7E).

- **base:** `d420937dca541f2ec21b8a8e7c67a1ca695202dc`.
- **canonicalization:** `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=0bf0504847920f11d5b9f090aa6866f53a882daa4bea5aacc80810cc57b6f342

```text
.ce/pr-path-manifest.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/v3_cli.py
validators/creator_engine_validator/v3_shaping.py
validators/tests/unit/test_v3_cli.py
validators/tests/unit/test_v3_shaping.py
validators/tests/unit/test_version_boundary.py
```
