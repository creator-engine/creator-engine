TICKET ce-ops#322 (child of EPIC ce-ops#312) — TIER-1 doc-autogen generator #2: JSON-schema → schema-reference (PR-enforced generate-then-verify). WORK CLASS: story. SEAT: dev-4 (SELF-PUSH — implement + commit + FULL preflight green + push a PR, then STOP; do NOT self-approve or merge — the controller holds the gate).
WORKTREE: create a FRESH worktree off origin/main (current local branch is stale): `git fetch origin main && git worktree add ../wt-ce322 -b ce322-doc-autogen-schema-reference origin/main` (work there).
PATTERN TO MIRROR (READ FIRST): PR #581 / ce-ops#316 (MERGED). Read these merged files on origin/main and mirror their structure exactly:
  - `scripts/gen_cli_reference.py` (pure `project(source) -> markdown`; `--check` byte-parity/fail-closed + `--write`; deterministic, no timestamps/env-dependent content).
  - `validators/creator_engine_validator/checks/cli_reference_autogen_sync.py` (the `@register`'d gate check).
  - `validators/tests/unit/test_cli_reference_autogen_sync.py` (generate-then-verify unit test).
  - committed artifact `.ce/reference/cli.generated.md`.
SOURCE FOR THIS SLICE: the committed `schemas/*.yaml` JSON-schema set (~40 files) → a deterministic schema reference. This is the highest-determinism, NO-secrets, NO-network source #581 did NOT cover. It is a pure file→text projection. MUST NOT probe live hosts/fleet (that is Tier-2, OUT of scope).
DELIVERABLES:
  - `scripts/gen_schema_reference.py` — pure `project(schemas) -> markdown`; `--check` (read-only byte-parity vs committed doc, exit non-zero on drift) + `--write`. Deterministic ordering (sort schemas), no timestamps.
  - committed reference artifact `.ce/reference/schemas.generated.md` with a `<!-- ce-autogen: ... -->` provenance header (corpus-trust hook).
  - `@register`'d check `schema_reference_autogen_sync` (new code `VAL-AUTOGEN-STALE-SCHEMA`) in `validators/creator_engine_validator/checks/schema_reference_autogen_sync.py`, riding the existing validator gate in `validate.yml` on `pull_request`. No new workflow plumbing.
  - unit test `validators/tests/unit/test_schema_reference_autogen_sync.py` proving generate-then-verify (fails closed on stale/missing, passes on fresh, generator round-trips).
TERRITORY / CONFLICT-AVOIDANCE (IMPORTANT): the registration import in `validators/creator_engine_validator/checks/__init__.py` is ALSO appended at the file tail by in-flight PR #578 (`skill_antidrift_guard`). To avoid a trailing-append merge conflict, insert THIS generator's registration import in the existing alphabetical/block position (not at the very end of the import block). Expect a possible trivial rebase if #578 lands first.
HARD EXCLUSIONS: tools/egress-broker/**, systemd units, .claude/skills/**, README.md, docs/guide/**, .github/** (do not add new workflow plumbing — reuse the existing validate.yml gate), `ce_cli.py`, `scripts/gen_cli_reference.py` and its check/test (do not modify #581's files).
GOVERNANCE: canonical carriers `.ce/changelog/ce322-*.md` + `.ce/pr-manifests/ce322-*.md` (front matter incl issue: ce-ops#322); the PR BODY must include the line `- **Declared work class:** story`.
PREFLIGHT (FULL, on a CLEAN tree before push): `PYTHONPATH=validators python3 -m creator_engine_validator.ce_cli validate-pr --base origin/main --declared-work-class story`. Must be green (and `gen_schema_reference.py --check` must pass against the committed artifact).
STOP LINE: push the PR and STOP. Do NOT self-approve, do NOT merge, do NOT enqueue — the controller holds the merge gate. Report the PR number when done.
