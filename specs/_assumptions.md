# Creator Engine v1.0 — SDD Assumptions & Reconciliation Ledger (`_assumptions.md`)

Gate: **G0 — SDD/TDD bootstrap + repo-state reconciliation** (type: **DOC**).
Authored UTC: 2026-05-24T16:57:03Z.
Controlling roadmap: Option B re-issued definitive roadmap, SHA256
`5a7e5ba74adcaab32c892c3cf793384eec4f121a6991b1bd5bba34a30fd48e13`.

> Gate 0 **records** every assumption and reconciliation determination below. It performs **no git
> mutation** to act on any triage, and it **re-decides nothing** — items needing a decision are
> flagged for Source.

---

## 1. Baseline determination (RV1-002 context; prompt §9.1)

- **Canonical baseline = live `refs/heads/main` = `36377f8c4caf6817e01d58072062eb5caccc164b`**,
  obtained via the single authorized `git fetch origin main` (remote-tracking ref / `FETCH_HEAD`
  only) recorded in `_status.md` §6. The prior baseline `31229cdf9b1fe10f0cb64e111508ff6921112be6`
  is **superseded**; live main is 4 commits ahead of it (behind_by 0, clean fast-forward ancestry).
- The checked-out `remediation/oss-readiness-public-launch-blockers` branch
  (HEAD `e9f495334fa6e5ed3c486702c1a865e2806bcccb`) is **48 behind / 1 ahead** of the pinned
  baseline. **Determination:** `origin/main` is canonical; the remediation branch **predates the
  canonical substrate line** and is not the authoritative baseline.
- **No destructive or history-mutating git action** is part of Gate 0's authority. Reconciling the
  branch state (merge/rebase/reset/cherry-pick/branch deletion/force-push) is a separate
  Source-ratified Controller action. Gate 0 **records** the divergence; it does not **resolve** it.

## 2. Per-artifact triage of the dirty remediation working tree (RV1-002; prompt §9.2)

Every `git status --short` entry (snapshot in `_status.md` §5.1) is triaged into **exactly one** of
`already-on-main` / `superseded-by-main` / `candidate-for-ratified-cherry-pick`. Classification is
from a **read-only** content comparison of each working-tree path against the pinned baseline
`36377f8…` (`git cat-file -e` for existence, `git diff --quiet <base> -- <path>` for content). **No
artifact is silently inherited; no git mutation acts on this triage.**

### 2.1 `already-on-main` (working-tree content identical to baseline — nothing to carry)

| Path | Class basis |
|---|---|
| `docs/delivery/ASSIGNMENT_ENVELOPE_TEMPLATE.md` | exists on `36377f8…`, content-identical |
| `docs/delivery/ENVELOPE_CONSUMPTION_CHECKLIST.md` | exists on `36377f8…`, content-identical |
| `docs/delivery/SCOPE_AUDIT_CHECKLIST.md` | exists on `36377f8…`, content-identical |

### 2.2 `superseded-by-main` (baseline carries the canonical version; the dirty copy differs and is not authoritative)

| Path | Class basis |
|---|---|
| `docs/delivery/NEXT_TASK_PROTOCOL.md` | exists on `36377f8…`, dirty copy differs |
| `docs/delivery/RISK_REGISTER.md` | exists on `36377f8…`, dirty copy differs |
| `templates/hermes/session-state/STATE.template.md` | exists on `36377f8…`, dirty copy differs |
| `validators/creator_engine_validator/checks/__init__.py` | exists on `36377f8…` (carries the Slice-4 ledger-check registration); dirty copy differs |
| `validators/creator_engine_validator/cli.py` | exists on `36377f8…` (carries `scan-side-effect-ledger`); dirty copy differs |
| `docs/operations/CONTROLLER_BOUNDARY_POLICY.md` | exists on `36377f8…`, dirty copy differs |
| `docs/operations/NO_COPY_PASTE_PATTERN.md` | exists on `36377f8…`, dirty copy differs |
| `docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md` | exists on `36377f8…`, dirty copy differs |
| `docs/operations/TRANSCRIPT_ARCHIVE_PROTOCOL.md` | exists on `36377f8…`, dirty copy differs |
| `schemas/handoff.schema.yaml` | exists on `36377f8…`, dirty copy differs |
| `schemas/recommended-prompt.schema.yaml` | exists on `36377f8…`, dirty copy differs |
| `templates/hermes/visible-pane-pointer-prompt.template.md` | exists on `36377f8…`, dirty copy differs |
| `validators/creator_engine_validator/checks/handoff_schema.py` | exists on `36377f8…`, dirty copy differs |
| `validators/creator_engine_validator/checks/path_manifest_fidelity.py` | exists on `36377f8…`, dirty copy differs |
| `validators/creator_engine_validator/checks/role_boundary_attribution.py` | exists on `36377f8…`, dirty copy differs |
| `validators/tests/integration/test_handoff_examples.py` | exists on `36377f8…`, dirty copy differs |
| `validators/tests/unit/test_handoff_schema.py` | exists on `36377f8…`, dirty copy differs |
| `validators/tests/unit/test_path_manifest_fidelity.py` | exists on `36377f8…`, dirty copy differs |
| `validators/tests/unit/test_role_boundary_attribution.py` | exists on `36377f8…`, dirty copy differs |
| `examples/malformed/handoffs/count-mismatch.md` | exists on `36377f8…`, dirty copy differs |
| `examples/malformed/handoffs/hash-mismatch.md` | exists on `36377f8…`, dirty copy differs |
| `examples/malformed/handoffs/init-py-corruption.md` | exists on `36377f8…`, dirty copy differs |
| `examples/well-formed/handoffs/example-handoff.md` | exists on `36377f8…`, dirty copy differs |
| `templates/hermes/handoffs/HANDOFF.template.md` | exists on `36377f8…`, dirty copy differs |
| `templates/hermes/recommended-prompts/RECOMMENDED_PROMPT.template.md` | exists on `36377f8…`, dirty copy differs |

> The untracked directories shown in `git status` (`examples/malformed/handoffs/`,
> `examples/well-formed/handoffs/`, `templates/hermes/handoffs/`,
> `templates/hermes/recommended-prompts/`) exist on the baseline; their constituent files are triaged
> individually above. Any "differs" disposition means only that the canonical line lives on main; it
> is **not** an instruction to overwrite the dirty root (no git mutation is taken).

### 2.3 `candidate-for-ratified-cherry-pick` (absent on baseline — net-new; needs Source review before any cherry-pick)

| Path | Class basis |
|---|---|
| `sha-guarded-gate.md` | repo-root file absent on `36377f8…` (untracked working note, ~45 KB) |
| `review-merge` | repo-root file absent on `36377f8…` (untracked working note, ~16 KB) |

**Determination:** these two are candidates only. Whether either is canon-worthy is a **Source
decision**; Gate 0 records them as candidates and takes no cherry-pick or staging action.

## 3. Side-Effect Ledger correction — INVERTED from the prior gate's assumption (RV1-003; prompt §9.3)

The prior (blocked) Gate 0 / the roadmap §4 / the envelope §6 asserted the Side-Effect Ledger is
**"genuinely absent on `origin/main`" (no `schemas/*side-effect*`)**, to be built from scratch at G4.
**That claim is stale and is hereby inverted.** Authenticated read-only verification (carried in the
baseline-refresh architect report `21b092fa…` and verification notes `47910a90…`, and confirmed in
this lane: the pinned baseline tree contains `schemas/side-effect-ledger.schema.yaml`) establishes:

- **BUILT on live `refs/heads/main` under PCO Slice 4 (the G4 SVC / shapes layer):**
  - `schemas/side-effect-ledger.schema.yaml` — a real JSON-Schema (draft 2020-12), const-pinned
    `kind: side-effect-ledger-record` / `record_type: side_effect`, `unevaluatedProperties: false`,
    full typed `required` block. Framed as a **read-only evidence index**. Not a stub.
  - `validators/creator_engine_validator/checks/side_effect_ledger.py` — a registered 477-line check
    (`__init__.py` registers it).
  - `validators/creator_engine_validator/cli.py` — exposes a **`scan-side-effect-ledger`** conformance
    subcommand and wires well-formed + malformed examples into `check-examples`
    (PCO-056 missing-claim, PCO-057 duplicate-effect-id, PCO-059 secret-payload, PCO-063 unknown-field).
  - Unit tests (`validators/tests/unit/test_side_effect_ledger.py`, 257 lines) + integration tests
    (`validators/tests/integration/test_side_effect_ledger_examples.py`, 60 lines) + well-formed and
    malformed examples under `examples/{well-formed,malformed}/side-effect-ledger/`.
  - `docs/operations/SIDE_EFFECT_LEDGER_PROTOCOL.md` — the prose contract.
- **STILL A GAP on live main (the G4 runtime layer, RV1-041):** there is **no `ce ledger record` /
  `ce ledger verify` runtime** — `cli.py` exposes only conformance `scan-*`; no append / hash-chain /
  replay command exists. The schema explicitly states it "does not observe runtime effects
  automatically … or capture secrets."

The Side-Effect Ledger remains **distinct from the Active-Work Ledger**
(`.hermes/active-work-ledger/`, landed): the Active-Work Ledger answers *"who owns this lane right
now?"* (claims + lane events); the Side-Effect Ledger answers *"what governed side effects occurred,
in what order, with what classification?"* (append-only, classified, redacted, replayable evidence
index). The two **must not** be conflated. **The prior contrary absence claim is superseded and is not
restated as an operative assertion anywhere in this SDD spine.**

## 4. G4 reclassification flagged for Source — NOT re-decided by Gate 0 (prompt §9.4)

Because the Slice-4 substrate landed early, roadmap **G4 must be amended by Source** from
*"build the Side-Effect Ledger schema + validator + CLI from scratch"* to *"reconcile + ratify the
landed PCO-Slice-4 substrate and build the remaining runtime (`ce ledger record` / `ce ledger verify`,
append / hash-chain / replay per RV1-041), honoring the read-only-evidence-index framing."* This is a
**roadmap amendment exceeding Gate 0's "record, do not re-decide" authority**, so Gate 0 **flags it
for Source** rather than rewriting G4. The as-built status of RV1-040 / RV1-041 / RV1-042 is recorded
in `_traceability_matrix.md` (substrate landed; runtime pending) with a reconciliation-pending note.
**Source should sequence the G4 amendment before G4 execution.**

## 5. v1.1 dev-container seam — deferred, not rejected (RV1-004; prompt §9.5; roadmap §7)

The v1.1 project-dev-container seam (`ce dev shell` / `ce dev run`) is recorded as **deferred, not
rejected**. v1.0 keeps three boundaries distinct and individually addressable — host Controller state,
worker/container state (`.hermes/workers/`, rootless Podman), and the project workspace (the allocated
worktree); the DP-3=B governed-environment guard predicate is designed so a future dev-container mode
is a detectable/validatable PASS branch; the v1.0 Worker-Container Policy is the policy foundation a
v1.1 dev profile reuses; and the `ce dev …` namespace is reserved (v1.0 binds `dev` to no other
meaning). v1.0 docs (G8) state the deferral explicitly.

## 6. Option B language/packaging contract — §2.2 of the controlling re-issued roadmap (RV1-005; prompt §9.6)

Recorded as the controlling §2.2 contract (Source-locked Option B / 1B; **not re-decided** by Gate 0;
Source decision record `6bd9b87d…`):

- **Python floor `requires-python = ">=3.14"`**; tested/current **target Python 3.14.x** (current
  stable patch at decision time **3.14.5, released 2026-05-10**). Floor = compatibility promise;
  target = what is built/tested/shipped.
- **3.13 intentionally excluded** (cleaner/narrower support + cp314-only wheelhouse simplicity);
  **3.11 / 3.12 rejected** as security-only floors; **3.15 invalid** (unreleased/prerelease, planned
  2026-10-01).
- **v1.0 wheelhouse is cp314-only** (x86-64); any later ABI widening is a fresh Source decision.
- **Install is uv-first** (`uv pip install --no-index --find-links validators/wheelhouse …` /
  `uv sync --offline --locked`) **with a pip/`--no-index` fallback** retained for a uv-less host. No
  network fetch at install or runtime authority.
- **Reproducibility contract = `pyproject.toml` + `uv.lock` (per-file hashes) + offline wheelhouse**;
  `validators/requirements.txt` is a `uv export`-derived **fallback/export** artifact kept in lockstep,
  **not** the primary lock contract.
- **Pinned deps: `PyYAML==6.0.3`, `jsonschema==4.26.0`** with transitives (`attrs`,
  `jsonschema-specifications`, `referencing`, `rpds-py`) refreshed in lockstep. `rpds-py` is the
  binding offline-reproducibility constraint (compiled extension dragged in by `jsonschema`); named
  subject of a POST-V1 footprint review.
- **Format split (B6/B7):** JSON Schema 2020-12 (schema language) is unchanged; **new machine
  evidence/ledgers use stdlib `json`** (`sort_keys=True`, canonical, hashable); **new operator/developer
  config uses TOML read via stdlib `tomllib`** (read-only) **or** CE-managed JSON; existing
  `schemas/*.schema.yaml`, Spec Kit sidecars, and identity records **remain YAML** (read-only via
  `safe_load`). **No TOML writer dependency** (`tomli-w`/`tomlkit`) is added in v1.0. These three axes —
  schema language, schema serialization, validation engine (`jsonschema`) — are stated separately and
  must not be conflated.
- **Build backend `setuptools.build_meta`** retained; package stays **nested at
  `validators/pyproject.toml`**; no root distribution restructure; **DP-1 not reopened** (distribution
  stays `creator-engine-validator`; `ce` console-script name is independent of distribution name).
- **`uvx` one-line operator install is POST-V1 (B3)**; v1.0 install surface is source checkout
  (`git clone`) + offline wheelhouse.

**Implementation is Gate 6 (RV1-060); Gate 0 only records this contract** in `_traceability_matrix.md`
and ADR-0001. **Gate 0 authors no packaging/dependency/wheelhouse change.**

## 7. Integrity note carried for Source (informational)

Two upstream blocker-evidence files referenced by an earlier architect prompt
(`GATE0_LIVE_MAIN_BLOCKER_EVIDENCE.md`, `gate0_live_main_blocker_preflight.json`) had stale embedded
expected SHAs (a controller transcription defect, not tampering); their only material claim — that
live main advanced to `36377f8…` — is independently re-verified in `_status.md` §6. They are **not**
required inputs to this gate and nothing here relies on them. Source/controller should correct those
embedded SHAs on a future pass for chain consistency.
