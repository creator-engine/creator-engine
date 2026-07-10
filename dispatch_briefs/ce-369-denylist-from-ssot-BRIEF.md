# Seed Brief: ce-369-denylist-from-ssot

- Ticket: ce-ops#369 (private tracker — you cannot read it; full context is embedded below)
- Branch: `ce-369-denylist-from-ssot` off `origin/main`
- Role: implementer
- Worktree: create under `/var/tmp` (NOT `/workspace`)

## Ticket context (ce-ops#369 — embedded, you have no ce-ops access)

Follow-up from the Fleet-IaC P0 guard (PR #679,
`validators/creator_engine_validator/checks/fleet_manifest_guard.py`):

1. **MAIN (Operator-ratified, binding):** `fleet_manifest_guard.py` currently
   hand-maintains a Python tuple `INTERNAL_LITERAL_TOKENS` of CE-internal
   identifiers (repo names, seat logins, host names, container names, etc.)
   that must never appear in a customer's fleet-manifest deployment file. This
   hand-maintained list already missed real identities (seat logins, a
   reviewer login) until a human review caught it. Fix: derive this denylist
   from the authoritative SSOT identity registry
   (`ce-ops:infra/identity-registry.yaml`, a **private** repo you cannot read)
   so new/changed internal identities cannot silently fall out of coverage.
2. **Non-blocking, same review — evaluate only, do not let it block item 1:**
   (a) the literal token `"forge/"` is a broad substring — it risks
   false-positives on legitimate external Forgejo paths such as
   `secretref://org.forge/...`; consider narrowing it to the internal
   `ce-kv/forge/<seat>` context. (b) `"dev-1"`..`"dev-4"` are matched as plain
   substrings, so a legitimate external value like `"lead-dev-1"` would be
   wrongly rejected; consider word-bounded matching. These are advisory —
   note findings, do not restructure the whole matcher to fix them unless it
   falls out naturally from the item-1 redesign.

## Design context: this is a REDO of rejected PR #729

A prior attempt (PR #729) was closed on a unanimous 2-review REQUEST_CHANGES
with two blocking findings, which are the acceptance bar for this redo:

1. Committed registry-derived values must be **irreversible** — no
   recoverable internal identifiers vendored into this public repo. The
   SHA-256-at-rest design below satisfies this.
2. Snapshot↔source **freshness must be an enforced CI check, not a manual
   helper**. #729 shipped a "maintainers with access can run the helper and
   regenerate" model — that exact shape was rejected. This redo ships a
   scheduled CI freshness workflow (see deliverable 5 below) per the
   generate-then-verify doctrine's Tier-2 pattern (private/live-state source →
   separate scheduled job re-derives and fails loudly on drift; the PR gate
   itself stays offline/fork-safe).

Read the current `INTERNAL_LITERAL_TOKENS` implementation for what you are
replacing, but do **not** resurrect #729's manual-helper freshness model.

## The core design problem you must solve

`creator-engine` is a **public** repo (source of `creator-engine.dev`) whose
**PR-gate CI has no read access** to the private `ce-ops` repo (fork PRs never
get secrets). So the per-PR gate cannot "generate from the live registry" the
way `schema_reference_autogen_sync` regenerates its doc from `schemas/*.yaml`
(a same-repo source) — read
`validators/creator_engine_validator/checks/schema_reference_autogen_sync.py`
and `scripts/gen_schema_reference.py` as the closest existing precedent for
the "generate-then-verify" shape, but note the key difference: its SOURCE
lives inside this repo; ours does not. Freshness is therefore enforced by a
**scheduled workflow with an access-scoped secret**, not by the PR gate.

**Chosen mechanism (Operator-ratified — implement this, do not improvise a
different one):**

1. A **generator script**, `scripts/gen_identity_denylist.py`, modeled on
   `scripts/gen_schema_reference.py`'s `--check`/`--write` CLI shape. It takes
   a **required, non-hardcoded** `--registry <path>` argument pointing at a
   local checkout of a file that conforms to
   `validators/creator_engine_validator/schemas/identity-registry.schema.yaml`.
   You will **never run it against the real ce-ops registry** — you have no
   access to that file. Build and unit-test it against a schema-conformant
   fixture only (see "Testing" notes below). At runtime it is invoked in two
   places: manually by a party with ce-ops access (`--write`, to regenerate
   the artifact), and by the scheduled freshness workflow (`--check`, to
   detect drift).
2. A **committed derived artifact** that the PR gate can verify without
   ce-ops access:
   `validators/creator_engine_validator/data/identity_denylist.generated.yaml`.
   This file MUST NOT contain any internal identifier in the clear — every
   identity-bearing token is stored as a SHA-256 hex digest of its normalized
   (casefolded) form, never the plaintext. Store alongside each hash: a
   non-identifying category label (e.g. `account-login`, `owning-seat`,
   `host-name`, `os-user`, `repo-name` — the schema FIELD the token came from,
   never the value) and enough non-identifying metadata (e.g. the set of
   token character-lengths present) for the matcher below to work. This
   satisfies the hard requirement: no internal identifiers in the clear —
   hashed/derived-safe form only.
3. A **verify/sync check**,
   `validators/creator_engine_validator/checks/identity_denylist_autogen_sync.py`
   (register it in `validators/creator_engine_validator/checks/__init__.py`,
   same way every other check is registered — see the end of that file).
   Scoped honestly to what the offline PR gate CAN verify: (a) the committed
   artifact is well-formed and internally consistent (minimal structural
   checks in code are fine); (b) `fleet_manifest_guard.py` actually loads its
   runtime denylist FROM this artifact (not from a hardcoded fallback) and the
   loaded ruleset is non-empty; (c) the artifact contains no accidental
   plaintext leak (defensive self-scan — you may take inspiration from
   `validators/creator_engine_validator/public_docs_confidentiality.py`'s
   pattern set, but that module is a different guard with a different job —
   don't wire into it). The check's docstring must state explicitly that
   freshness against the live ce-ops registry is enforced by the **scheduled
   freshness workflow** (deliverable 5), not by this per-PR check — mirror
   `schema_reference_autogen_sync.py`'s docstring honesty about what it
   verifies.
4. `fleet_manifest_guard.py`'s matching logic changes from a hardcoded
   plaintext-substring scan to a **hash-based bounded-substring membership
   check** against the committed artifact, preserving TODAY's
   containment-matching *semantics* (a candidate manifest string fails if it
   contains a denylisted token anywhere) while the denylist stays hashed at
   rest: for each string value found in the manifest, enumerate its substrings
   at the character-lengths recorded in the artifact's metadata, hash each
   substring the same way (normalize/casefold first), and check set
   membership. `INTERNAL_REGEX_PATTERNS` (the tailnet-IP, herdr-socket,
   brain/vLLM-endpoint structural regexes) are **out of scope** — they detect
   patterns, not specific identities, and stay as committed Python code
   unchanged.
   *Flexibility:* if this scheme proves awkward in practice, you may propose a
   simpler matching design in your done-report — but only if ALL hard
   requirements still hold: irreversible-at-rest (no cleartext identifiers in
   the committed artifact), today's containment semantics preserved
   byte-for-byte against the existing tests, and enforced CI freshness.
   Implement the specified scheme first; propose alternatives as commentary,
   don't unilaterally substitute one.
5. A **scheduled freshness workflow** (new file —
   `.github/workflows/identity-denylist-freshness.yml`). This is the enforced
   CI freshness mechanism that #729 lacked. Shape:
   - Triggers: `schedule` (daily is fine) + `workflow_dispatch`.
   - Checks out this repo, then checks out `creator-engine/ce-ops` using an
     access-scoped secret token referenced as `secrets.CE_OPS_READ_TOKEN`.
     You **reference** the secret; you do NOT provision it — the controller
     provisions the org/repo secret after merge. Structure the job so a
     missing secret produces a clear failure message, not a silent pass.
   - Runs `scripts/gen_identity_denylist.py --registry
     <ce-ops-checkout>/infra/identity-registry.yaml --check`.
   - On drift, the job **FAILS loudly** — the failing scheduled run IS the
     alert. It must NOT auto-push, auto-commit, or auto-open PRs in v1;
     propose-a-governed-diff is an explicit follow-up, state that in a
     workflow comment.
   - Minimal permissions block (`permissions: contents: read`), no secrets
     echoed to logs (no `set -x` around token use, no printing the registry
     contents), and it must pass the repo's existing workflow-permissions
     audit check (the preflight runs one).

## Which registry fields feed the denylist (positive allowlist — do not walk every string in the registry)

Read `validators/creator_engine_validator/schemas/identity-registry.schema.yaml`
yourself to confirm field names before you code. Only these IDENTIFIER-shaped
fields should ever produce a denylisted token — do NOT derive from free-text
descriptive fields:

- `repos[].name`, `repos[].owner`
- `accounts[].login`, `accounts[].owning_seat`, `accounts[].host`
- `host_topology[].name`, `host_topology[].host`, `host_topology[].users[]`
- `signing_keys[].custody_seat`, `signing_keys[].custody_host`
- `authoring_review_matrix[].seat`, `.authors_as[]`, `.may_review[]`

Explicitly EXCLUDE from derivation:
- Free-text/descriptive fields: `role`, `reach_method`, `purpose`,
  `description`, `visibility`, `status` — these are prose or enum labels, not
  identifiers, and denylisting them would make the guard reject ordinary
  words.
- Pointer/path fields: `pem_custody`, `key_path_pointer`,
  `storage_pointer.*`, `credential_pointers[]` — these are structural
  pointers (openbao-ref:/vault:///file:// forms), not stable identity tokens.
- `apps[].repo_scope` — at least one legitimate value in this field family is
  a glob over the PUBLIC repo (`creator-engine/*`), so blanket inclusion risks
  denylisting ordinary public-repo mentions. Exclude for v1; note as an open
  question if you think it's needed.
- The literal placeholder value `TODO_VERIFY` (used pervasively by
  `todo_or_string`/`todo_or_integer` fields per the schema) — never denylist
  this string itself; it is a placeholder, not an identity, and would produce
  a mass false-positive matching almost any manifest.
- Any candidate token shorter than a sane minimum length (the current
  hand-maintained list's shortest entries are 3 chars, e.g. `"DGX"`). Enforce
  a minimum-length floor and verify against the existing test fixtures (the
  `_manifest()` builder in `test_fleet_manifest_guard.py`, which legitimately
  uses words like `container`, `policyref`, `identityref`, `egressref`,
  `openbao`) that nothing in a normal, clean manifest starts matching after
  your change. If in doubt, raise the floor rather than lower it.

## Seeding the initial artifact for THIS PR

Since you have no ce-ops access, do not attempt to run the generator against
a real registry. The correctness-preserving move is to migrate the CURRENT
`INTERNAL_LITERAL_TOKENS` tuple's existing values (already committed in
plaintext in this repo's git history today, so hashing them introduces no new
disclosure) into the new artifact format 1:1, so guard behavior is
byte-for-byte equivalent to today (all current parametrized tests in
`validators/tests/unit/test_fleet_manifest_guard.py` must still pass
unchanged). State explicitly in your changelog fragment and PR description
that: (a) this PR ships the MECHANISM plus a like-for-like migration of the
existing hand list into hashed form; (b) the scheduled freshness workflow —
once the controller provisions its `CE_OPS_READ_TOKEN` secret — is the
enforced mechanism that will immediately surface any gap between the migrated
hand list and the real registry; (c) the controller regenerates the artifact
against the live registry as an immediate follow-up (you cannot do this — do
not claim you did).

## Packaging correctness (read `validators/creator_engine_validator/schema.py` lines ~17-70 before you write the loader)

The new artifact is data the guard must load AT RUNTIME, including from an
**installed wheel**, not only from a source checkout. `schema.py` documents a
real prior bug class here (its own comments describe how JSON-schema YAML
files were originally repo-root-only and crashed every installed, non-source
CLI until they were moved under `creator_engine_validator/schemas/` and added
to `[tool.setuptools.package-data]` in `validators/pyproject.toml`). Follow
the same pattern for your new file:
- Put the artifact under
  `validators/creator_engine_validator/data/identity_denylist.generated.yaml`.
- Add a matching glob to `[tool.setuptools.package-data]` in
  `validators/pyproject.toml` (it currently lists
  `["schemas/*.schema.yaml", "forge/*.yaml"]` — add your own entry the same
  way).
- Resolve the file path anchored to `Path(__file__).resolve().parent` (the
  package directory), the same technique `schema.py`'s `_resolve_schema_path`
  uses, so loading works both from a source tree and an installed wheel. You
  do not need to reuse `_resolve_schema_path` itself (it is schema-specific)
  — write your own small resolver, either inline in the guard module or in a
  new shared module `validators/creator_engine_validator/identity_denylist.py`
  if you want the loader/matcher shared between the guard and the sync check
  (recommended, to avoid duplicating the hashing/matching logic in two
  files).
- Run the full local preflight (below) — this is exactly the kind of change
  that trips the packaging/wheel-parity gates if the data-file wiring is
  wrong, and preflight is how you catch it before push, not CI.

## Allowed paths

- `validators/creator_engine_validator/checks/fleet_manifest_guard.py`
- `validators/tests/unit/test_fleet_manifest_guard.py`
- `scripts/gen_identity_denylist.py` (new)
- `validators/creator_engine_validator/data/identity_denylist.generated.yaml` (new)
- `validators/creator_engine_validator/checks/identity_denylist_autogen_sync.py` (new)
- `validators/creator_engine_validator/checks/__init__.py` (register the new check)
- `validators/creator_engine_validator/identity_denylist.py` (new, optional — shared loader/matcher, only if you choose the shared-module design)
- `validators/tests/unit/test_identity_denylist_autogen_sync.py` (new)
- `.github/workflows/identity-denylist-freshness.yml` (new — the scheduled freshness workflow, deliverable 5)
- `validators/pyproject.toml` (package-data entry only)
- `.ce/changelog/ce-369-denylist-from-ssot.md` (mandatory)
- `.ce/pr-manifests/ce-369-denylist-from-ssot.md` (carrier — regenerate via the `carrier_gen` API, do not hand-edit; see `validators/creator_engine_validator/carrier_gen.py`)

Do not touch `.github/workflows/validate.yml` — the NEW freshness workflow
file above is explicitly in scope, but the existing PR-gate workflow is not.
Precedent (`schema_reference_autogen_sync`) needed zero changes to
`validate.yml` because registered checks are exercised through the existing
pytest suite / the existing `check`/`--list-checks` CLI surfaces already
wired into it. If your local preflight run surfaces concrete evidence that a
`validate.yml` change really is required, STOP and report that evidence
instead of editing it yourself.

## Contained-seat mechanics

- Worktree lives under `/var/tmp` (NOT `/workspace`).
- Branch off `origin/main`.
- The venv has no `activate` — always invoke via
  `.venv/bin/python -m pytest ...` (never bare `pytest`/`python`).

## Preflight (standing directive, ce-ops#303)

Run the FULL local validator preflight (`ce validate-pr`, CI-parity) GREEN in
ONE pass before you commit for harvest. Do not discover gates via CI — if
something fails, fix it locally and re-run the full preflight, don't push and
find out. Pay particular attention to: the existing
`test_fleet_manifest_guard.py` parametrized cases (must all still pass
unchanged — you migrated their coverage, you did not remove it), any
packaging/wheel-parity test that exercises `[tool.setuptools.package-data]`,
the workflow-permissions audit (your new scheduled workflow must pass it),
and the path-manifest/carrier gate.

**Known exception:** this container may lack `ssh-keygen` (ce-ops#400, a
known gap). If preflight fails ONLY on the known ssh-keygen install-spec
exception, report that explicitly as the known exception rather than
churning on it.

## Work-class and changelog

Declare a work-class line in your done-report: with the scheduled workflow
included, `- **Declared work class:** feature` is the likely fit — but
self-assess against the actual diff size once you've written the change; if
it lands clearly smaller than expected, say so and use `story` instead. Don't
force a mis-declared class to fit a guess made before you wrote the code. You
must add `.ce/changelog/ce-369-denylist-from-ssot.md` describing: what
changed, why (SSOT-derivation + confidentiality-safe storage + enforced
scheduled freshness), and the explicit caveats from the "Seeding" section
above (like-for-like migration; freshness workflow pending secret
provisioning; controller regeneration follow-up).

## Stop line

- No pushes, no PR, no approvals, no merges.
- No gate/wall/daemon config changes.
- No toolchain self-update.
- Do not provision, request, or fabricate any secret or token — the freshness
  workflow only REFERENCES `secrets.CE_OPS_READ_TOKEN`; provisioning is the
  controller's act.
- Do not attempt to reach, guess at, or fabricate the contents of the real
  `ce-ops:infra/identity-registry.yaml` — you have no access to it and must
  not simulate having read it.
- If any part of the design above turns out not to be satisfiable within the
  allowed paths (e.g. you discover the packaging wiring genuinely requires
  touching a file not on the allowed-path list), STOP and report the specific
  blocker rather than improvising a workaround or widening your own path
  list.

## Expected evidence

- Targeted tests for every new/changed file green.
- Full local preflight GREEN in one pass (paste the final summary line/exit
  code in your done-report).
- `git commit && echo SHA`, then emit exactly:
  `READY-FOR-HARVEST ce-369-denylist-from-ssot <full-sha>`
- A done-report without a verifiable commit SHA is not done.
