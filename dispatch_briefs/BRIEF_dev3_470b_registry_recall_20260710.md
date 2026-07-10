# DISPATCH — dev-3 — 2026-07-10 — unit: identity-registry recall layer (ce-470 slice b) — class S
Role: implementer foreman. Signal: `READY-FOR-HARVEST ce-470b-registry-recall <full-40-hex-sha>`
or `BLOCKED ce-470b-registry-recall <one-line-reason>`.
Branch `ce-470b-registry-recall` off freshly fetched origin/main OR LATER. Worktree
/var/tmp/wt-ce-470b-registry-recall. Focused tests only.
PRE-SIGNAL CHECKLIST: focused tests green + confidentiality check:
`python -m pytest validators/tests/unit/test_public_docs_confidentiality.py::test_tracked_text_files_contain_no_new_confidential_or_internal_references -q`

## Context (embedded)
The identity registry is the fleet SSOT for infra identities (Apps, installations, key
POINTERS — never key material). Its schema + example + tests landed (see
validators/creator_engine_validator/schemas/identity-registry.schema.yaml and
docs/governance/identity-registry.example.yaml on main). MISSING: the recall layer — during
live work an App installation id had to be re-derived via an App JWT round-trip because
nothing could answer "what is the installation id for app X" from the registry. Also: the
shipped controller-bootstrap runbook explicitly caveats an identity-lookup verb as pending.

## Unit — queryable lookup, standalone entry point (NO ce_cli.py edit)
1. NEW `validators/creator_engine_validator/identity_recall.py`:
   - Load a registry YAML (path argument; sensible default resolution: explicit arg → env
     CE_IDENTITY_REGISTRY → refuse-with-message naming both; validate against the shipped
     schema before answering — fail-closed on schema mismatch).
   - Query API: `lookup(registry, kind, name)` returning the entry, plus field addressing
     (`--field installation_id` style) for scripting. List mode (all entries of a kind).
   - SECURITY: if a queried entry contains a key POINTER field, return the pointer verbatim;
     if any field LOOKS like key material (PEM markers, long base64), REFUSE loudly — the
     registry must never carry secrets and the tool must not become an exfil path.
2. Standalone console entry `ce-identity-lookup` added to validators/pyproject.toml
   [project.scripts] (mirror how ce-posture-banner was added; ce_cli.py stays untouched —
   the bootstrap runbook's pending-verb caveat gets satisfied by this entry point for now).
3. Tests `validators/tests/unit/test_identity_recall.py`: lookup happy path, field
   addressing, list mode, schema-invalid refusal, missing-registry refusal message,
   key-material refusal, env fallback precedence. Fixtures: SYNTHETIC registry data only
   (fictional apps/ids — never real fleet identifiers).

## Files (allowed writes)
identity_recall.py (NEW), test_identity_recall.py (NEW), validators/pyproject.toml
([project.scripts] one line), `.ce/changelog/ce-470b-registry-recall.md`, carrier
(slug=branch) with exactly `- **Declared work class:** S`. Product lens; zero real
identifiers anywhere in fixtures or prose.

## Stop lines
ce_cli.py, v3_cli.py, the registry schema + example (READ-ONLY inputs), posture_banner.py,
checks/**, pr_preflight.py, forge/**, deploy/**, .github/**, docs/**, all in-flight modules
(ticket_reconcile*, worktree_venv, release_acceptance, brain_intent_materializer,
secret_identity, seat_watch_runner), .ce/brain/assertions.yaml.
