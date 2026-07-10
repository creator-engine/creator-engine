# SEED BRIEF — ce-ops#367 (REDIRECTED): CE-native `ce init` project scaffolding

**Context (self-contained):** Operator retired spec-kit COMPLETELY (constitution 2.0.0 / #676).
The old `ce speckit init` approach (PR #722) is CLOSED. Build a **CE-native** `ce init` that
replicates the *capability* — scaffolding a new/existing user project into CE's governed
spec-driven SDLC — with ZERO spec-kit dependency, naming, or `.specify/` layout. This is the
"start a CE-governed project" front door, relevant to first-external-contributor onboarding.

**Build `ce init`:**
- New top-level `ce init` CLI group (validators/creator_engine_validator/ce_cli.py + a new
  `project_init.py` module). Idempotent, offline (embed templates in-package, no network).
- Scaffolds into a target project dir:
  - CE spec-driven structure per the SHIPPED work-sizing tiers (docs/contracts/work-sizing-tiers.md:
    XS=scope_card; S=intent+scope+tasks; M=full spec/plan/tasks) — do NOT claim every unit needs a
    full spec.
  - Anchored to the canonical stage vocabulary Frame→Shape→Build→Review→Ship
    (docs/architecture/stage-vocabulary.md).
  - CE conventions: per-PR changelog fragment template, path-manifest carrier, declared-work-class
    line, and `ce validate-pr` wiring/README notes.
  - CE-native skills/templates authored FOR CE — NOT ported spec-kit skills.
- **Explicitly OUT:** no `.specify/` tree, no `speckit` name, no spec-kit skill files.
- Prior embedded-template mechanics on branch `ce-367-speckit-init` may be salvageable for the
  template-embedding plumbing (but re-author content CE-native).

**GATE COUPLINGS (bake into the work):**
- New top-level `ce` CLI group → trips `test_v1_docs_reconciliation` AND requires regenerating
  `.ce/reference/cli.generated.md` via `python scripts/gen_cli_reference.py --write` (this was the
  mechanical blocker on the old PR). Carrier MUST name README.md, cli.generated.md, and any coupled test.
- Regenerate carrier via carrier_gen.write_carriers(base=<merge-base>) API (rm build/egg-info first).

**Branch:** `ce-367-ce-native-init` (off origin/main). **Role:** implementer (foreman may fan out
templates vs CLI vs tests). **Work class:** feature (M). Run FULL `ce validate-pr` GREEN in one pass
before commit-for-harvest (contained seat: PYTHONPATH=validators worktree source, not stale installed
venv). Commit-for-harvest + echo SHA (contained) OR self-push (dev-1). Done-report = branch, SHA,
files, preflight evidence.
