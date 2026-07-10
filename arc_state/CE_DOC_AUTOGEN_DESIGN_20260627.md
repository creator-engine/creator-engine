# CE Code/State → Documentation Auto-Generation — Definitive Design

Date: 2026-06-27
Author: CE-DEV-2 research/design worker (read-only on code; writes this doc only)
Status: DESIGN — for Operator ratification + ce-ops ticketing
Scope: the missing "code changes → doc regenerates" mechanism. Generalizes CE
from thin drift-DETECTION to deterministic doc GENERATION with a fail-closed
generate-then-verify guard.

---

## CORE FRAME — a MERGE to `main` IS the CE-state-change event

Doc-regeneration is **continuous / per-merge, not batched at release.** Every
state-changing PR is the unit of doc currency. The design splits into two
distinct tiers by *where the source of truth lives*:

- **TIER 1 — CODE-PROJECTED docs** (CLI reference, schema reference, code-derived
  tables). The source is IN the PR's diff. → **generate-then-verify ON THE PR**:
  the PR's own CI regenerates the doc from the changed code and FAILS the gate if
  the committed doc is stale. Every state-changing PR is FORCED to carry its
  regenerated docs. **No bot pushes to `main`.** This is the PRIMARY mechanism.
- **TIER 2 — LIVE-STATE docs** (identity/infra registry reconciled from the
  running fleet). The source is the live fleet, NOT the PR diff — a PR guard
  cannot probe live hosts. → a SEPARATE periodic/post-merge reconciler job, NOT
  the PR guard. Kept architecturally distinct from Tier 1.

The full autonomous loop: because Tier 1 is enforced ON the PR, a CEO-mode
**auto-merged** PR (#291/#561) keeps docs in sync with ZERO human in the loop —
doc-autogen + auto-merge + autonomous-release = "ship-and-document-yourself."
See §3.4.

---

## 0. Problem statement (grounded recon)

CE today has exactly one genuine code→doc guard and zero doc generators:

- The one code→doc guard:
  `validators/creator_engine_validator/checks/operator_runbook_refusal_sync.py`
  — AST-extracts `CLAUSE_*` string globals from the pure launcher specs
  (`claude_launch_spec.py`, `codex_launch_spec.py`), parses a marker-delimited
  markdown table in `docs/operations/SEAT_LAUNCH_GOVERNANCE_RUNBOOK.md`, and
  asserts set-equality (missing/extra/duplicate clause IDs fail closed). This
  is **detection only** — when the code changes, a human still hand-edits the
  table; the check just yells if they forgot.
- The one (preview-only, writes-nothing-live) generator:
  `scripts/gen-controller-bootstrap.py` — loads a tracked JSON SSOT
  (`docs/design/controller-bootstrap-ssot.json`), validates its shape, hashes
  it (sha256), and renders markdown to **stdout or an explicitly safe out-dir**
  with hard refusals against overwriting any live path. This is the embryo: a
  proper SSOT→render projector that is deliberately not yet wired to write the
  artifact it documents.
- Byte-parity guard precedent: `release_artifact_parity_guard.py` (#260) —
  proves "two surfaces must be byte-identical, fail closed on mismatch" via
  sha256. This is the exact CI shape the generate-then-verify loop needs.
- Brain drift: `ce_brain_drift.py` + `.ce/brain/assertions.yaml` — re-verifies
  assertions against `evidence_ref` via probes/projections, deliberately
  avoiding raw full-file hashes so unrelated churn doesn't false-positive.
  Relevant pattern: **semantic projection over raw hash** when the source has
  noise.

Everything else (CLI reference, schema reference docs, the identity/infra
registry, most of `docs/contracts/`) is hand-authored and silently drifts. The
giant `ce_cli.py` docstring (lines 1–60+) is itself a hand-maintained command
list that already drifts from the argparse tree below it — a perfect smoking
gun.

The validator architecture is a clean fit: checks self-register via the
`@register(name, frs)` decorator in `checks/__init__.py`, take `Iterable[Path]`,
return a `CheckResult` of `ValidationError`s. A generate-then-verify guard is
just another registered check.

---

## 1. Generatable surfaces — ranked by leverage

Principle: **auto-generate only deterministic projections of a tracked or
safely-probeable source.** Judgment prose (the "why", design rationale,
narrative runbooks, the compounding/learning loop) stays hand-authored and is
explicitly OUT OF SCOPE here.

Generatable set, ranked by (leverage × determinism × drift-pain) ÷ build-cost:

### Rank 1 — `ce --help` → CLI reference  [PILOT CANDIDATE A]
- **Source:** the argparse tree in `ce_cli.py` (`_build_parser()` at L185;
  ~40+ subcommands across `lane/ledger/worker/fanin/queue/event/pcl/brain/...`).
- **Projection:** walk the parser tree (subparsers, args, help, choices,
  defaults) → markdown reference. argparse exposes `_subparsers`,
  `_actions`, `option_strings`, `help`, `choices`, `default` — fully
  introspectable, no AST needed.
- **Why rank 1:** highest determinism (the parser IS the SSOT, zero declared
  intermediate), highest drift-pain (the docstring command-list at top of
  `ce_cli.py` already drifts; this is the public/dev CLI surface users read),
  near-zero source-maintenance burden (devs already write `help=` strings).
- **Bonus:** the same projector can REPLACE the hand-maintained module
  docstring command-list, collapsing two drifting copies into one generated
  artifact.

### Rank 2 — identity/infra registry reconciled from the LIVE fleet  [PILOT CANDIDATE B — highest *internal* value]
- **Source:** live fleet probes (hosts/seats/containers/OpenBao path existence)
  + a declared overlay for non-probeable facts.
- **Target:** the private ce-ops `infra/identity-registry.yaml` (schema
  `schemas/identity-registry.schema.yaml`), closing its `TODO_VERIFY`
  placeholders (github_id, noreply_commit_email, secret-store path existence,
  exposure class).
- **Why high:** the Operator hand-maintains fleet truth today; it is the
  single largest source of stale internal docs and the thing that drifts every
  time a seat/container/host changes. See §4 for the probe/declare split.
- **Why NOT rank 1 for the pilot's *mechanism* proof:** it has a live-probe +
  secrets-adjacency dimension that complicates the clean generate-then-verify
  proof. Recommend piloting the *mechanism* on CLI ref, then applying the
  proven loop here as the first high-value expansion (see §7).

### Rank 3 — JSON-schema → reference docs
- **Source:** `schemas/*.yaml` (~70 schemas), each paired (loosely) with a
  `docs/contracts/*.md`.
- **Projection:** for each schema, render a deterministic field table
  (property, type, required?, enum/pattern/const, description). This becomes the
  *reference* section of each contract doc; the hand-authored *prose/rationale*
  stays, fenced by markers (same marker pattern as the refusal-clause block).
- **Why rank 3:** very deterministic and high-count, but contract docs are
  prose-heavy and only the field table is mechanical — so it's a per-doc
  marker-block insertion, not whole-file generation. Big volume payoff once the
  loop exists.

### Rank 4 — code-derived tables (generalize `operator_runbook_refusal_sync`)
- **Source:** AST-extracted constants/enums from code (the refusal clauses are
  the first instance; mutation classes, check codes, seat-class policies are
  candidates).
- **Projection:** flip the existing *detector* into a *generator*: the same AST
  extraction that asserts the table can WRITE the table. The detector then
  becomes the verify half of the loop for free.
- **Why rank 4:** lower volume, but it's the cheapest to build because the
  extraction already exists — it's a refactor, not a new capability.

### Stays hand-authored (OUT OF SCOPE — judgment prose)
- ADRs, design docs, runbook narrative, the public README product-lens framing,
  onboarding stories, the compounding/learning-loop docs. These require
  judgment and are governed differently. Generators may inject deterministic
  *blocks* into them (marker-fenced) but never own the whole file.

---

## 2. Generator architecture — the SSOT→doc projector + generate-then-verify pairing

### 2.1 Core shape (build on `gen-controller-bootstrap.py`)

Every generator is a pure function:

```
project(source) -> rendered_text          # deterministic, no I/O beyond reading source
```

where `source` is one of: a tracked SSOT file (controller-bootstrap pattern),
introspected code (argparse tree / AST), a tracked schema, or a probe+overlay
bundle (registry reconciler). Determinism requirements, inherited from the
bootstrap generator: stable ordering (sort keys), no timestamps in the body,
no environment-dependent content. Any non-determinism = a bug that breaks the
verify half.

Two run modes per generator (mirror `gen-controller-bootstrap.py`'s
stdout-vs-out-dir, but now the out-path is the LIVE committed artifact):

- `--check` (default in CI): render in-memory, compare to the committed
  artifact, exit non-zero on diff. **Read-only. Never writes.**
- `--write` (developer/local): render and write the committed artifact, so the
  human's job is `run generator → commit`, not hand-edit.

### 2.2 The generate-then-verify pairing (the load-bearing invariant)

This is the heart of the design and the answer to "no silent drift":

> **The generator is the source of truth. The committed doc is a CHECKED
> ARTIFACT. CI re-runs the generator and asserts `regenerate == committed`,
> byte-for-byte (or projection-for-projection). A stale generated doc fails
> closed.**

Two verification strengths, chosen per surface:

1. **Byte-parity verify** (default; mirrors `release_artifact_parity_guard.py`):
   `sha256(project(source)) == sha256(committed_file)`. Used when the whole
   file is generated (CLI reference, a standalone registry snapshot doc).
2. **Marker-block projection verify** (mirrors `operator_runbook_refusal_sync`
   + `ce_brain_drift`'s semantic-projection stance): only the content between
   `<!-- ce-autogen:NAME:start -->` / `:end` markers must match
   `project(source)`; surrounding hand-authored prose is free to change. Used
   for schema field-tables and code-derived tables embedded in prose docs. This
   reuses the *exact* marker-parse machinery already in
   `operator_runbook_refusal_sync.py`.

### 2.2.1 The trigger: `pull_request` (Tier 1) — the spine

Tier 1 verification runs **on every PR**, on the `pull_request` trigger, as a
step in the existing gate (`validate.yml`). It is the spine of the whole design:

```yaml
# validate.yml (sketch) — Tier 1 PR-enforced doc currency
- name: doc-autogen verify (code-projected docs)
  run: python -m creator_engine_validator ... # the registered autogen-verify check
        # OR: ce docs gen --check   (aggregator, once it exists)
        # exits non-zero if any committed code-projected doc != project(changed source)
```

Mechanically this is identical to running the generator in `--check` mode and
diffing against the committed artifact: CI regenerates `docs/reference/cli.md`
from the PR's `ce_cli.py`, byte-compares to the committed file, and **fails the
check (blocks the gate) on any diff**, with remediation
*"run `ce docs gen --write` and commit"*. Because the check is registered in the
validator (`run_registered(paths)`), it rides the gate that already runs on
`pull_request` — no new workflow file, no bot, no push to `main`. The PR author
(human or auto-merge-eligible agent) MUST commit the regenerated doc to go green.

This is strictly stronger than the current detector-only guards: the PR cannot
merge stale. Since merge-to-`main` is the state-change event, enforcing on the
PR means `main` is doc-current *at every merge by construction*.

### 2.3 Where it lives (reuse the validator registry)

- Generators: `scripts/gen_*.py` (or a `creator_engine_validator/generators/`
  package) — pure `project()` + a thin CLI with `--check`/`--write`.
- Verify guards: one registered check per generator under
  `validators/creator_engine_validator/checks/`, using `@register(name, frs)`,
  taking `Iterable[Path]`, returning `CheckResult`. The check simply imports the
  generator's `project()`, renders, and emits a `ValidationError` (new
  `VAL-AUTOGEN-STALE-<NAME>` code) on mismatch with a remediation message:
  *"run `ce docs gen --write` and commit"*.
- This means the verify half rides the EXISTING gate with zero new CI plumbing —
  it's just another check in `run_registered(paths)`.

### 2.4 Optional convenience: `ce docs gen`

A single `ce docs gen [--check|--write] [--only NAME]` subcommand (added to the
`ce_cli.py` argparse tree) that runs every registered generator. `--check` is
what CI calls; `--write` is the dev affordance. Nice-to-have, not required for
the pilot (the pilot can ship a bare `scripts/gen_cli_reference.py` + one
check). Note the recursion: once `ce docs gen` exists, the CLI-reference
generator documents `ce docs gen` itself — clean dogfood.

---

## 3. Integration with existing machinery

### 3.1 Release/parity (#260)
- The verify guard IS the parity-guard pattern generalized: `parity` binds two
  pre-existing files; `autogen-verify` binds a file to a *function of a source*.
  Recommend a shared helper (`_sha256` already exists in the parity guard) —
  factor a tiny `byte_parity(rendered: str, committed: Path)` util both use.
- Generated docs that ship in releases (e.g. CLI reference if bundled) flow
  through the same release-artifact path; the autogen-verify check runs
  pre-release so a release can never carry a stale generated doc.

### 3.4 Auto-merge engine (#291/#561) — the "ship-and-document-yourself" loop
Because Tier 1 doc-regen is enforced ON the PR (not at release, not by a
post-merge bot), it composes cleanly with the auto-merge engine:
- An auto-merge-eligible PR must pass the gate, and the gate now includes the
  Tier-1 autogen-verify check. So a PR whose code changed but whose docs weren't
  regenerated simply **does not become green** and never auto-merges.
- The agent that authored the code change is responsible for committing the
  regenerated doc (it runs `ce docs gen --write` as part of its build). Once it
  does, the PR goes green and the auto-merge engine lands it — docs and code
  arrive on `main` together, **zero human in the loop.**
- Net: doc-autogen (Tier 1) + auto-merge (#291/#561) + autonomous-release = the
  full self-documenting pipeline. Every autonomously-shipped change is
  autonomously documented, and the gate is the single enforcement point. No bot
  ever pushes docs to `main`; the PR carries them.
- Tier 2 (live-state registry) is explicitly OUT of this loop — it cannot be
  satisfied by the PR and so must never be a merge-blocking check (that would
  deadlock auto-merge on a fleet probe). It reconciles asynchronously (§4.4).

### 3.2 Support-agent corpus / freshness (product-lens bundle)
- Generated docs are deterministic and freshness-guaranteed (CI proves they
  match HEAD), so they are the IDEAL feed for the support-agent corpus: the
  CLI reference and schema reference become always-current grounding without a
  human refresh step. Recommend tagging generated docs with a machine-readable
  `<!-- ce-autogen: source=... generator=... -->` header so the corpus builder
  can trust+prioritize them and distinguish generated (fresh-by-construction)
  from hand-authored (may-drift) content.

### 3.3 Public-docs confidentiality guard
- **Generated docs MUST pass the public-docs confidentiality guard like any
  other doc** — generation is not an exemption. The CLI reference is derived
  from `help=` strings; if a dev writes an internal-leaking help string it would
  surface in public docs, so the confidentiality guard runs DOWNSTREAM of the
  autogen-verify check on the generated artifact.
- The registry reconciler is the sharp edge: it reads infra. It MUST be
  internal-only, zero-secrets, pointers-only (see §5). Its generated artifact
  lives in the private ce-ops repo and is *never* a candidate for the public
  bundle. Encode this as a hard allowlist: the public-docs generator set and the
  internal generator set are disjoint and separately configured.

---

## 4. The fleet-reconciliation case — TIER 2 (live-state, NOT PR-enforced)

Goal: auto-derive the identity/infra registry from the live fleet instead of
hand-maintaining `infra/identity-registry.yaml`, closing `TODO_VERIFY`s.

**Why this is a SEPARATE tier, not a PR guard:** the source of truth is the
running fleet (live hosts/seats/containers/OpenBao paths), which is NOT present
in any PR's diff. A `pull_request`-triggered check cannot (and must not) probe
live infra — it would be non-deterministic, slow, credentialed, and would
deadlock auto-merge. So Tier 2 runs as a **periodic / post-merge reconciler
job**, completely distinct from the Tier-1 PR guard.

### 4.1 Probe / declare split

**Safely PROBEABLE (machine-derivable, non-secret):**
- Host reachability + identity: `ssh <host> hostname`, uname/arch, tailnet IP
  presence (existence, not credentials).
- Container inventory: `docker ps`/`podman ps` names + images per host (e.g.
  `ce-vps-codex`, `ce-dgx-codex`).
- Seat→pane mapping: `tmux list-panes` / herdr pane registry (existence of the
  declared panes).
- OpenBao path **existence + shape** (NOT values): `vault kv list ce-kv/forge/`
  → which `ce-kv/forge/<seat>` paths exist. Existence is non-secret; the secret
  value never leaves the store.
- GitHub identity facts via API: actor login, App slug, noreply commit email
  format — these are public-ish facts that close many `TODO_VERIFY`s.

**Stays DECLARED (judgment / authority / non-probeable):**
- `authority_context`, `human_ratifier_roles`, `mutation_classes`,
  `allowed_repositories`, exposure-class intent, role_category intent — these
  are governance decisions, not observable facts. They live in a tracked
  declared overlay.

### 4.2 Reconciler shape
`project(probe_results, declared_overlay) -> registry.yaml`:
- Probe results fill the observable fields; the declared overlay fills the
  judgment fields; the reconciler MERGES deterministically (sorted, stable).
- A `TODO_VERIFY` remaining after reconciliation = a real gap the probe
  couldn't close and the overlay didn't declare → the verify guard can be
  configured to FAIL on residual `TODO_VERIFY` (closing the loop the schema
  already anticipates).
- Drift detection becomes free: when the live fleet diverges from the committed
  registry, `--check` fails, signalling "fleet changed, re-reconcile". This is
  the registry analog of `ce_brain_drift`'s re-verification stance.

### 4.4 Trigger for Tier 2 (scheduled / post-merge, never PR-blocking)
- Runs on a `schedule:` (e.g. hourly, aligned with the existing seat-check cron)
  and/or a post-merge `push: main` job — NOT on `pull_request`, and NEVER as a
  merge-blocking gate check.
- On divergence it does NOT push to `main` autonomously (the registry lives in
  the private ce-ops repo and touches infra exposure). It opens an internal PR /
  surfaces a diff for governed review, OR writes to a controller-local state
  path. The reconciler PROPOSES; ratification stays governed.
- This keeps Tier 2 fully decoupled from auto-merge: a fleet change can never
  block a code PR, and a code PR can never trigger a fleet probe.

### 4.3 Safety rails specific to the reconciler
- Probes are read-only and existence-only. **No secret value is ever read,
  rendered, or hashed-into an artifact** — only pointers (`vault://...`,
  `openbao-ref:...` per the schema's existing pattern) and existence booleans.
- The reconciler runs only on a trusted controller host (it needs fleet reach);
  its output is internal-repo only. It is NOT in the public generator set.

---

## 5. Governance / safety

- **Generated docs need no per-doc ratification.** A deterministic projection of
  an already-governed source carries no new authority — the ratification lives
  at the SOURCE (the launcher spec, the schema, the argparse tree, the declared
  overlay), and the verify guard proves the doc is nothing more than that
  projection. This is consistent with CE's "deterministic projection = no new
  decision" stance.
- **Flag anything touching secrets/exposure.** The registry reconciler is the
  one generator that reads infra; it is governed as internal, zero-secrets,
  pointers-only, controller-host-only, private-repo-output-only. Encode these as
  hard refusals in the generator (mirror `ensure_safe_out_dir` /
  `is_live_agent_path` refusals in `gen-controller-bootstrap.py`).
- **Fail-closed everywhere.** Unreadable source, malformed marker block,
  non-deterministic render, residual `TODO_VERIFY`, or any mismatch → the check
  emits a `ValidationError` and the gate blocks. No generator silently degrades.
- **The generator never writes in CI.** `--check` is read-only by construction;
  only `--write` (local/dev) mutates, keeping the gate non-mutating.

---

## 6. Build-vs-rent

**Reuse (do not rebuild):**
- The `gen-controller-bootstrap.py` pattern (tracked-source → validate → hash →
  render → safe-write-with-refusals) — copy its bones.
- The `release_artifact_parity_guard.py` sha256 byte-parity pattern + `_sha256`
  helper — the byte-parity verify half.
- The `operator_runbook_refusal_sync.py` marker-block parser + AST extraction —
  the marker-projection verify half and the code-derived-table generator.
- The `@register` check registry — zero new CI plumbing.
- Python stdlib `argparse` introspection (`_subparsers`/`_actions`) — no library
  needed for the CLI reference.
- `jsonschema` / existing YAML loader (`loader.load_yaml`) — schema parsing for
  schema-reference projection (already a dependency).

**Build (thin):**
- One `project()` per surface (small, pure).
- One verify check per surface (tiny, wraps `project()`).
- The probe layer for the reconciler (the only genuinely new code).
- Optional `ce docs gen` subcommand.

**Thin first slice:** one generator + one verify check + the shared
byte-parity helper. Nothing else.

---

## 7. Phased plan + ce-ops ticket list

### Phase 0 — Pilot ONE generator end-to-end (prove the loop)
**Recommendation: pilot `ce --help` → CLI reference (Candidate A).**
Rationale: highest determinism, no probe/secrets complications, immediate
visible drift-pain relief (collapses the drifting `ce_cli.py` docstring
command-list), and it dogfoods cleanly. Prove the generate-then-verify loop
here before touching the higher-stakes registry reconciler.

- Build `scripts/gen_cli_reference.py` with `project(parser)->md`,
  `--check`/`--write`.
- Generate `docs/reference/cli.md` (whole-file byte-parity).
- Add `checks/cli_reference_autogen_sync.py` (`@register`, new
  `VAL-AUTOGEN-STALE-CLI` code), remediation message points at `--write`.
- **Wire it into the PR gate** (`validate.yml`, `pull_request` trigger) so the
  check runs on every PR — this is the spine (§2.2.1). No new workflow file; it
  rides `run_registered(paths)`.
- Factor the shared `byte_parity()` helper (shared with #260's `_sha256`).
- Exit criterion: a PR that edits a `help=` string without regenerating
  `docs/reference/cli.md` FAILS the gate (cannot merge / cannot auto-merge);
  `ce docs gen --write` + commit makes it green. `main` is doc-current at every
  merge by construction.

### Phase 1 — First high-value expansion: fleet registry reconciler (Candidate B) — TIER 2
- Build the probe layer (existence-only, zero-secrets, controller-host-only).
- Build `gen_identity_registry.py` (`project(probes, overlay)->yaml`).
- Runs as a **scheduled / post-merge job, NOT a PR gate check** (§4.4); proposes
  a diff for governed review, never auto-pushes to `main`, never blocks
  auto-merge.
- Internal-only; fail on residual `TODO_VERIFY`; private-repo output; NOT in
  public generator set.

### Phase 2 — Schema → reference docs (volume payoff)
- Build `gen_schema_reference.py`; marker-block projection into each
  `docs/contracts/*.md` field table; one verify check covering all schemas.

### Phase 3 — Generalize code-derived tables
- Refactor `operator_runbook_refusal_sync.py`: extraction → generator; the
  existing detector becomes the verify half. Apply to mutation classes, check
  codes, seat-class policies.

### Phase 4 — Convenience + corpus integration
- Add `ce docs gen [--check|--write|--only]` aggregator subcommand.
- Tag generated docs with `<!-- ce-autogen: ... -->` headers; wire the
  support-agent corpus to trust them as fresh-by-construction.

### ce-ops ticket list
- **ce-ops#A — TIER 1 doc-autogen substrate + CLI-reference pilot, PR-enforced
  (Phase 0).** `gen_cli_reference.py`, `docs/reference/cli.md`,
  `cli_reference_autogen_sync` check wired into the `pull_request` gate, shared
  `byte_parity()` helper. Generate-then-verify-ON-THE-PR loop proven: a stale
  doc fails the gate. *(parent / spine / first slice)*
- **ce-ops#B — `ce docs gen` aggregator subcommand** (`--check`/`--write`/
  `--only`); CI calls `--check` on `pull_request`. *(can fold into #A)*
- **ce-ops#C — TIER 2 fleet identity/infra registry reconciler (Phase 1)** —
  existence-only probe layer + declared overlay; runs as scheduled/post-merge
  job, NOT a PR gate (§4.4); proposes governed diff, never auto-pushes, never
  blocks auto-merge; zero-secrets, pointers-only, private-repo output,
  residual-`TODO_VERIFY` fails closed.
- **ce-ops#D — Schema → contract field-table generator (Phase 2)** —
  marker-block projection + one verify check across `schemas/*.yaml`.
- **ce-ops#E — Generalize `operator_runbook_refusal_sync` detector→generator
  (Phase 3)** — code-derived tables (refusal clauses first, then mutation
  classes / check codes / seat-class policies).
- **ce-ops#F — Autogen ↔ confidentiality + support-corpus integration
  (Phase 4)** — generated docs pass the public-docs confidentiality guard;
  `<!-- ce-autogen -->` headers; corpus trusts generated docs as fresh.

---

## Appendix — key file references (absolute)
- `/home/cedev2/creator-engine/validators/creator_engine_validator/checks/operator_runbook_refusal_sync.py` — the one code→doc guard (AST + marker-table; detector to generalize).
- `/home/cedev2/creator-engine/scripts/gen-controller-bootstrap.py` — SSOT→render embryo (validate+hash+safe-write-with-refusals).
- `/home/cedev2/creator-engine/validators/creator_engine_validator/checks/release_artifact_parity_guard.py` — sha256 byte-parity pattern (#260); `_sha256` helper to share.
- `/home/cedev2/creator-engine/validators/creator_engine_validator/ce_cli.py` — argparse tree `_build_parser()` @L185 + drifting docstring command-list (CLI-reference source).
- `/home/cedev2/creator-engine/validators/creator_engine_validator/checks/__init__.py` — `@register` check registry (verify guards plug in here).
- `/home/cedev2/creator-engine/validators/creator_engine_validator/checks/ce_brain_drift.py` — semantic-projection-over-raw-hash re-verification stance.
- `/home/cedev2/creator-engine/schemas/*.yaml` (~70) + `/home/cedev2/creator-engine/docs/contracts/*.md` — schema→reference docs source set.
- `schemas/identity-registry.schema.yaml` (present in `.ce/wt-deterministic-citations-brain/` worktree; `TODO_VERIFY` placeholders) + private ce-ops `infra/identity-registry.yaml` — reconciler target.
- `/home/cedev2/creator-engine/.ce/brain/assertions.yaml` — brain SSOT.
