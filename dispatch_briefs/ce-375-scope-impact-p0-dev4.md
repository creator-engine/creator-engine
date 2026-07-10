# SEED BRIEF — ce-ops#375 P0: scope-impact propagation (WARNING-only) — SEAT: dev-4

**Ticket:** ce-ops#375 (L8 SDD feedback loop). **Branch:** `ce-375-scope-impact-p0` (off origin/main). **Role:** implementer. **Work class:** declare by floor (likely S/M; legacy story/feature aliased).

## Goal (self-contained — embed; do not rely on reading the private ticket)
CE has the FORWARD spec-driven loop but not the reverse "living-spec" feedback loop. P0 delivers the doctrine-compatible core: **scope-change impact propagation + flagging** — when a Scope changes, SURFACE which downstream artifacts are affected, as non-blocking WARNINGS for human ratification. **NEVER auto-mutate specs. Never block CI.** (Architect design is on ce-ops#375; this brief embeds P0.)

## Scope — exactly these (P0)
1. **Add `downstream_refs` to `schemas/scope.schema.yaml`:** an OPTIONAL typed-reference array. Each item `{kind, ...}` where `kind ∈ {plan, decision_record, test_pattern, validator_check, scope}` with the matching ref field (e.g. `path` for plan, `id` for decision_record, `glob` for test_pattern, `name` for validator_check, `scope_id` for scope). Backward-compatible (Scopes without it stay green). The schema uses `unevaluatedProperties: false` → extend it to allow the new field. Value-free (repo paths/ids only; no secrets).
2. **Define canonical serialization** for `ratified_scope_sha` in `docs/contracts/scope.md` (e.g. `json.dumps(scope_dict, sort_keys=True, ensure_ascii=True)` over the parsed YAML, with the `value`/`ratified_scope_sha` fields placeholdered out) so the drift check is stable.
3. **Add `validators/creator_engine_validator/checks/ce_scope_impact.py`** — a WARNING-ONLY check:
   - Iterate ratified-state Scope records; recompute `sha256(canonical-bytes)`; compare to `ratification.ratified_scope_sha`. On mismatch → `IMPACT-SCOPE-CONTENT-DRIFT` **warning** (closes the existing gap where `ce_scope.py` only format-checks that sha).
   - When drift AND `downstream_refs` non-empty → one `IMPACT-DOWNSTREAM-AFFECTED` **warning per ref** naming the affected artifact.
   - Populate ONLY `CheckResult.warnings`, leave `errors` empty (CI stays green; flags visible as `WARN ...`).
   - PURE: no disk write / subprocess / socket; **shared-tier — `hashlib` only, do NOT import `coordination.py` or `v3_shaping.py`** (version_boundary forbids shared→v3). Mirror `ce_scope.py`'s defensive style.
   - Register in `checks/__init__.py`.
4. **Tests:** drift detected → warning (not error); downstream_refs each flagged; no-drift → silent; Scopes without downstream_refs stay green; CI never blocked by this check.

## Hard out-of-scope
No `ce scope impact` command (P1). No auto-apply / auto-rewrite of anything. No production→spec feedback (P2). Do not change the LOC/work-class metric.

## Stop line
FULL `ce validate-pr` GREEN locally (one pass) BEFORE self-push. Then `git commit && echo <SHA>`, push + open PR. Report branch/SHA/PR#/preflight. Foreman mode. Controller holds the gate.
