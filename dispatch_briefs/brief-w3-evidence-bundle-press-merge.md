# WORK CLAIM — W3 · Evidence-bundle "press-merge" ratification surface (aggregator + renderer)

**Seat:** dev-4 (DGX build seat). **Role:** implementer-foreman. **Born foreman** — fan out.

## Branch
```
git fetch origin && git checkout -b w3-evidence-bundle-press-merge origin/main
```

## Why (self-contained)
The Operator's merge gesture today requires hand-gathering, per PR, the diff, the test/CI results, the review state/notes, and (for UI-side work) computer-use evidence from separate places. W3 collapses that into ONE ratification surface so the gesture becomes "read the bundle, press merge." This feeds W1 (CEO-mode auto-merge) and the W2 release-sign surface, both of which need a single structured, deterministic artifact to reason over.

**This is an aggregator + renderer, NOT a new authority.** CE already has the adjacent no-authority evidence substrate you MUST reuse rather than reinvent:
- `validators/creator_engine_validator/fanin_runtime.py` — the Gate-7 `ce fanin build`/`inspect` runtime: deterministic, content-hashed (SHA256 of canonical bytes), no wall-clock fields, performs NO git/GitHub/CI/deploy mutation, and is constitutionally `has_authority: false` (refuses any ratify/enqueue/land). Mirror these invariants exactly.
- `schemas/evidence-fan-in-packet.schema.yaml` — the existing packet schema (kind, schema_version, packet_id, `has_authority: const false`, source_ratification {prompt_ref, sha256}, evidence[], side_effect_ledger, content_hash). Use it as your structural template.
- `schemas/review-evidence.schema.yaml`, `schemas/runtime-evidence.schema.yaml`, `schemas/implementer-evidence.schema.yaml`, `schemas/architect-evidence.schema.yaml` — the role-evidence record shapes to ingest/reference.
- `docs/operations/EVIDENCE_FAN_IN_PROTOCOL.md` — the prose contract for the fan-in protocol; the press-merge bundle is a PR-keyed sibling of this.
- `playbooks/computer-use-ticket/workflow.ce.yml` — computer-use evidence enters as the playbook's existing outputs (screenshot-evidence, machine-recheck, closed-set-report). Reference these; do not re-model them.
- `.ce/pr-manifests/` carrier convention (ce-ops#21) — the per-PR path-manifest pattern.

**Invariant to preserve:** the bundle carries NO ratification authority. Like the fan-in packet, any field equivalent to `has_authority` is `const false`, and the surface must never ratify/approve/enqueue/merge/deploy or mutate git/GitHub/CI. It REFERENCES evidence by ref+sha; it does not relocate or re-author it.

## Task
1. **New aggregator module.** Add a new module (suggested `validators/creator_engine_validator/press_merge_bundle.py`) that, given a PR number/head-ref, assembles a single structured **press-merge bundle** object aggregating: (a) a **diff summary** (files changed / additions / deletions / path-set — reuse the `.ce/pr-manifests/` path-set notion where a carrier exists), (b) **test/CI results** (status + per-gate pass/fail summary), (c) **review state + notes** (ingest/reference `review-evidence` records; carry reviewer verdict + non-ratification statement), and (d) **computer-use evidence where present** (reference the computer-use-ticket outputs by ref+sha). Build the bundle deterministically (no wall-clock fields; content-hash = SHA256 of canonical bytes with the hash field removed), exactly as `fanin_runtime.py` does — import/reuse its canonicalization helpers rather than duplicating them.
2. **Schema (propose, do not freeze).** If a new bundle schema is warranted, add it as `schemas/press-merge-bundle.schema.yaml` modeled on `evidence-fan-in-packet.schema.yaml` (include `has_authority: const false`, a `source_ratification` block, an `evidence[]`/refs block, and `content_hash`). If reusing/extending the existing fan-in packet is cleaner, do THAT and instead write a short design note (`docs/operations/PRESS_MERGE_BUNDLE.md`) recording the reuse decision for Orchestrator sign-off. State your choice and rationale in the PR body. Do NOT freeze a brand-new schema silently — surface the decision.
3. **Human-readable rendering.** Add a deterministic renderer (a function in the same module) that turns the bundle into a single human-readable Markdown ratification surface: header (PR ref + content-hash), diff summary, test/CI roll-up, review verdict(s) + notes, computer-use evidence section (when present), and an explicit "This bundle carries no merge authority" footer. The render must be pure/deterministic over the bundle object.
4. **Tests.** Unit tests proving: deterministic byte-identical bundle for identical inputs; `has_authority`/no-authority invariant enforced; missing/stale evidence ref → fail-closed before any output; renderer output is stable and contains each required section; computer-use evidence is included when present and omitted cleanly when absent.
5. **CLI registration — STUB ONLY, do NOT edit `ce_cli.py`.** The surface will eventually be a `ce press-merge build|render` (or `ce bundle …`) subcommand, BUT **dev-1 owns ALL edits to `validators/creator_engine_validator/ce_cli.py` during this fan-out — you MUST NOT touch it.** Instead expose clean public entrypoint functions in your new module (e.g. `build_bundle(...)`, `render_bundle(...)`) with the argument shape a subparser would pass, and leave a clearly-marked registration note at the top of your module:
   ```python
   # TODO(controller/dev-1): register `ce press-merge build|render` subparser in
   # ce_cli.py wiring to build_bundle()/render_bundle() below. ce_cli.py is owned
   # by dev-1 during this fan-out; this module is intentionally CLI-agnostic.
   ```
   Make the module fully testable WITHOUT `ce_cli.py` (tests call the entrypoints directly).

## Allowed paths (nothing else — `ce_cli.py` is EXPLICITLY EXCLUDED)
- `validators/creator_engine_validator/press_merge_bundle.py` (new module; name may vary)
- `schemas/press-merge-bundle.schema.yaml` (only if you choose the new-schema path)
- `docs/operations/PRESS_MERGE_BUNDLE.md` (design note / prose contract)
- `validators/tests/**` (new tests for this module)
- `.ce/changelog/**`
- `.ce/pr-manifests/**`
- **DO NOT EDIT** `validators/creator_engine_validator/ce_cli.py` (owned by dev-1 this fan-out) — leave the TODO stub instead.
- **Read-only / do not modify:** `governance/`, `schemas/evidence-fan-in-packet.schema.yaml`, `schemas/*-evidence.schema.yaml`, `validators/creator_engine_validator/fanin_runtime.py`, the validator binaries (import/reuse only).

## Evidence (DoD)
Full `ce validate-pr` GREEN (CI-parity, full suite).
⚠️ **G5 BODY FORMAT (mandatory):** the PR body MUST contain exactly ONE line formatted precisely as `- **Declared work class:** <tiny|story|feature|epic>` (a `**Work class:**` header or a `[PASS]` log line does NOT match — this papercut failed multiple PRs). Pick the tier the gate derives.
PR body must also state your Task-2 schema decision (new schema vs. extend fan-in) + rationale.

## Stop-line
- Green + self-push works → push + open PR ref ce-ops (W3 evidence-bundle press-merge). Do NOT approve/merge/enqueue — ratification stays with the Orchestrator/Operator.
- Green but push FAILS (contained-seat self-push gap #337; also note your container's libsodium gap fails `check-examples` on an unrelated fixture — **if that libsodium `check-examples` failure is your ONLY failure it is pre-existing**, not from your change) → STOP + report `READY-FOR-HARVEST: branch w3-evidence-bundle-press-merge, <N> commits, preflight green-except-libsodium`.
- Preflight RED on a NEW gate caused by your change → STOP + report the failing gate; do not whack-a-mole.
- If Task 2 forces a schema-freeze decision you're unsure about → STOP + report the option pair to the Orchestrator rather than freezing a new schema.
