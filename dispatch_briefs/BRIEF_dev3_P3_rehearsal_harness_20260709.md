# BRIEF — dev-3 — 2026-07-09 — P3: Fresh-Tenant Rehearsal harness, slice 1 (STRANGELOOP-1 pool)

Role: **implementer**. Contained COMMIT-ONLY seat (controller harvests — self-push infra is down).
Fresh worktree `/var/tmp/wt-p3-rehearsal` off `origin/main` (fetch first). Branch
`ce-p3-rehearsal-s1`. Declared work class: **story**.
Signal: `READY ce-p3-rehearsal-s1 <sha> .ce/pr-manifests/ce-p3-rehearsal-s1.md`
or `BLOCKED ce-p3-rehearsal-s1 <reason>`.
NO `.ce/brain/assertions.yaml` edits. SEAT-TARGETED-TESTS-ONLY — full `ce validate-pr` preflight
is controller-side; in-seat tests are targeted unit/smoke tests for new files only.

---

## Authorizing decisions

Decision 14 (STRANGELOOP-1 pool P3) + Decision 15; ratified 2026-07-08.

---

## Scope: Fresh-Tenant Rehearsal harness — slice 1

Build a scripted Fresh-Tenant Rehearsal harness at **`deploy/rehearsal/`**. The harness runs
inside a **pinned clean container with no repo checkout** and:

1. Installs CE from the latest signed release exactly per the public install docs.
2. Onboards a scratch repo (using `ce onboard` / `cev3 onboard --plan && --apply`).
3. Walks the documented CEO first-hour journey as a **script of the documented steps** —
   each agent-mediated step that requires a live model is **STUBBED** with an explicit
   `CE_REHEARSAL_STUB:` marker in code and output.
4. Emits a **machine-readable evidence bundle** (JSON) to a defined output path.

Slice 1 deliverables (only these; nothing more):
- `deploy/rehearsal/run-rehearsal.sh` — main CLI/make entrypoint
- `deploy/rehearsal/evidence-format.md` — authoritative schema doc for the evidence bundle
- `deploy/rehearsal/README.md` — usage, env vars, container image requirement, stub inventory
- `deploy/rehearsal/test_rehearsal_smoke.sh` — in-seat targeted smoke test (dry-run only;
  no Docker required in test)
- `.ce/pr-manifests/ce-p3-rehearsal-s1.md` — path-manifest carrier
- `.ce/changelog/ce-p3-rehearsal-s1.md` — changelog fragment (work class: story)

NO gating flip. NO release-process changes. NO CI wiring (that is slice 2 after Operator
reviews the evidence format). NO edits outside `deploy/rehearsal/`, `.ce/pr-manifests/`,
`.ce/changelog/`.

---

## Territory collision check — READ BEFORE TOUCHING ANYTHING

**OFF LIMITS (ce-512 is in flight on these paths; any edit = conflict):**
- `deploy/singleton-redeploy/*`
- `deploy/queue-daemon/*`

**PREDECESSOR — do not overwrite or replace:**
- `scripts/clean-room-rehearsal.sh` — the existing N6 harness (stages: provision, claude,
  install, inventory, onboard, first_value, update, teardown). P3's harness is a different
  artifact with a different purpose: it walks the CEO journey and emits a typed evidence
  bundle. Do not modify `scripts/clean-room-rehearsal.sh`. Do not import from it (the
  P3 harness must be self-contained).

**SAFE HOME — no existing content, no collision:**
- `deploy/rehearsal/` — create new; this directory does not exist on origin/main.

If you find any unexpected file at `deploy/rehearsal/` on the fresh worktree, signal
`BLOCKED ce-p3-rehearsal-s1 territory-collision: unexpected file at deploy/rehearsal/<path>`.

---

## Grounding: install path + signed-release mechanics

The public install one-liner (exactly as documented in `docs/guide/welcome.md` and
`docs/guide/zero-to-governed-seat-quickstart.md`):

```bash
curl --proto '=https' --tlsv1.2 -fsSL https://creator-engine.dev/install.sh | bash
```

What the installer does (source: `docs/install.sh` on origin/main):
- Fetches the signed install spec from `https://creator-engine.dev/llms-install.md`
- Fetches the trust root key from `https://creator-engine.dev/keys/ce-root-v1`
- Verifies the spec signature using `ssh-keygen -Y verify` with key `ce-root-v1` (ed25519,
  namespace `ce-spec-v1`)
- Resolves an out-of-band trust anchor from DNS TXT `_ce-root-v1.creator-engine.dev`
  (fetched from `https://dns.google/resolve?...`) and asserts the fingerprint matches
- Downloads the manifest-pinned `uv` tarball, verifies SHA256, extracts it
- Uses uv to install CPython 3.14 if no compatible Python is present
- Downloads and verifies SHA256 for each required wheel from the manifest
- Installs the `creator-engine-validator` package offline from the verified wheelhouse
- Exposes `ce` and `cev3` CLI shims at `~/.local/bin/`
- Runs `cev3 onboard --inventory` as the final bootstrap step

Signed-release coupling facts the harness must record:
- The signed spec pins the package version; `ce --version` / `cev3 --version` reports the
  installed package version. Capture this in the evidence bundle.
- The `SHA256SUMS` file (fetched and verified by the installer) pins install.sh itself.
  The harness must NOT re-verify this; it need only record the package version and venv path
  from `cev3 onboard --inventory` output.
- `CE_SITE` env var overrides the base URL; useful for staging rehearsals pointing at a
  pre-release mirror. The harness must plumb this through.

After install, the `ce onboard` path (from `docs/guide/zero-to-governed-seat-quickstart.md`):

```bash
ce onboard                   # one-shot: verifies install, init state, opens governed pane
# OR for plan/apply sequence:
cev3 onboard --plan
cev3 onboard --apply
```

---

## Grounding: CEO first-hour journey (docs/guide/solo-ceo-onboarding.md, post-#906/#907)

The harness must walk ALL phases below as discrete named stages. Phases that require a
live model are STUBBED; the stub must print `CE_REHEARSAL_STUB: <stage> <reason>` to
stdout and write a corresponding `status: stub` entry to the evidence bundle.

**Phase 1 — Launch governed session**
```bash
ce launch    # opens coding agent in governed terminal pane
```
STUB — requires live model/agent. Stub records: `{stage: launch, status: stub,
reason: requires_live_model}`.

**Phase 2 — Frame intent (conversational)**
Human tells the agent what to build in plain language. Agent drives Frame stage.
STUB — agent conversation required. Stub records: `{stage: frame, status: stub,
reason: requires_live_model, simulated_input: "Add a README to the scratch repo."}`.

**Phase 3 — Review and ratify the Scope**
Agent presents a Scope (Goal, Done-when, Budget, Change-type, Ready flag).
Human ratifies with:
```bash
ce ratify <scope-id> --approver-ref $(openssl rand -hex 32)
```
STUB — requires real Scope from live agent. Stub records simulated scope fields and
a synthetic approver-ref. Mark in code as `# STUB: ce ratify — no live Scope`.
The harness may run `ce ratify --help` (or `cev3 --help`) to verify the binary is
present and the subcommand is wired; record the exit code in the evidence bundle.

**Phase 4 — Build and Review (agent lane)**
After ratification, agent drives Build, opens PR, dispatches reviewer. Human judges
diff vs Done-when criteria.
STUB — agent + live GitHub required. Stub records: `{stage: build_review, status: stub,
reason: requires_live_model_and_github}`.

**Phase 5 — Gate the merge**
```bash
ce merge <scope-id> --run <run-id> --apply
```
STUB — requires real PR + run-id. Stub records: `{stage: merge, status: stub,
reason: requires_live_pr}`. Run `ce merge --help` (or `cev3 merge --help`) to verify
the subcommand is wired; record exit code.

**Phase 6 — Completion Report**
```bash
ce report <scope-id> --run-id <run-id>
```
STUB — requires completed run. Stub records: `{stage: report, status: stub,
reason: requires_completed_run}`. Run `ce report --help` to verify wiring.

**Non-stubbed checkpoints the harness must actually execute:**
- `ce onboard` (or `cev3 onboard --inventory`) — captures installed version
- `ce status` (or `cev3 status --help`) — verify CLI is wired
- `ce --version` / `cev3 --version` — capture installed package version
- `ce inbox --help` (or `cev3 inbox --help`) — verify inbox subcommand is wired

---

## Evidence bundle format (define in deploy/rehearsal/evidence-format.md)

The harness emits a single JSON file. Default output path:
`${CE_REHEARSAL_EVIDENCE_OUT:-/tmp/ce-rehearsal-evidence.json}`

Top-level schema:

```json
{
  "schema_version": "1",
  "rehearsal_id": "<uuid-v4>",
  "run_timestamp_utc": "<ISO-8601>",
  "harness_version": "ce-p3-rehearsal-s1",
  "container_image": "<image used>",
  "ce_package_version": "<from cev3 --version or null>",
  "ce_site": "<CE_SITE value used>",
  "stages": [
    {
      "stage": "<name>",
      "status": "pass | fail | stub | skip",
      "started_at": "<ISO-8601>",
      "completed_at": "<ISO-8601>",
      "duration_ms": <integer>,
      "stub_reason": "<string or null>",
      "exit_code": <integer or null>,
      "notes": "<string or null>"
    }
  ],
  "summary": {
    "total_stages": <integer>,
    "passed": <integer>,
    "failed": <integer>,
    "stubbed": <integer>,
    "skipped": <integer>
  },
  "failures": [
    {
      "stage": "<name>",
      "message": "<string>"
    }
  ]
}
```

The evidence-format.md must document this schema, every field's semantics, valid values
for `status`, and the versioning policy (schema_version bumps are slice 2+).

---

## Implementation guidance for run-rehearsal.sh

Model after `scripts/clean-room-rehearsal.sh` for structure (argument parsing, stage
dispatch, `--dry-run` / `--live`, `--list-stages`, per-stage `--stage NAME` support,
cleanup trap). Do NOT import from it; duplicate only the structural pattern.

Named stages in order (use these exact names; they map to evidence bundle `stage` fields):

```
provision       docker run --rm pinned clean container
install         curl ... | bash  (via docker exec)
install_verify  cev3 --version + ce --version capture
onboard         cev3 onboard --inventory (inventory only, no apply; captures state)
scratch_repo    init a scratch git repo inside the container (git init /tmp/scratch-repo)
ceo_launch      STUB: ce launch
ceo_frame       STUB: frame intent
ceo_scope       STUB: ce ratify; verify ce ratify --help exits 0
ceo_build       STUB: build + review
ceo_merge       STUB: ce merge --apply; verify ce merge --help exits 0
ceo_report      STUB: ce report; verify ce report --help exits 0
teardown        docker rm -f (cleanup trap also handles this)
```

Required env vars:
- `CE_REHEARSAL_IMAGE` — pinned Docker image tag (default: `ubuntu:24.04`; the
  brief requires a PINNED image; callers must override for reproducibility)
- `CE_REHEARSAL_SITE` — base URL for installer (default: `https://creator-engine.dev`)
- `CE_REHEARSAL_EVIDENCE_OUT` — evidence JSON output path (default: `/tmp/ce-rehearsal-evidence.json`)
- `CE_REHEARSAL_KEEP_CONTAINER` — set to `1` to preserve container for debug (default: `0`)
- `CE_REHEARSAL_CONTAINER_NAME` — container name (default: `ce-p3-rehearsal-$$`)

No secrets accepted as defaults. The harness must fail-closed if `--live` is not
affirmatively supplied (same pattern as clean-room-rehearsal.sh).

Container must be started with `--rm` disabled so the cleanup trap can call `docker rm -f`.
Mount nothing from the host checkout (no `-v` to repo root) — the harness runs
install-from-scratch, no pre-seeded repo.

---

## Targeted in-seat tests

**test_rehearsal_smoke.sh** must pass without Docker (dry-run only):

1. `./deploy/rehearsal/run-rehearsal.sh --dry-run` exits 0 and prints plan lines.
2. `./deploy/rehearsal/run-rehearsal.sh --list-stages` exits 0 and prints all 11 stage names.
3. `./deploy/rehearsal/run-rehearsal.sh --help` exits 0.
4. `./deploy/rehearsal/run-rehearsal.sh` (no args, no `--live`) exits non-zero with a
   clear "fail-closed" message.
5. The dry-run output contains `CE_REHEARSAL_STUB:` markers for every stubbed stage name
   (grep check).

Run these tests from the worktree root. Do not require network, Docker, or credentials.

---

## Carrier + changelog

`.ce/pr-manifests/ce-p3-rehearsal-s1.md` — path-manifest carrier with AUTHORIZED_PATHS_COUNT
and AUTHORIZED_PATHS_SHA256 matching exactly the files this PR touches. Include itself.

`.ce/changelog/ce-p3-rehearsal-s1.md` — one-paragraph fragment, work class story:
"Add Fresh-Tenant Rehearsal harness (slice 1) at deploy/rehearsal/..."

No other changelog files need updating for this slice.

---

## Public lens

`deploy/rehearsal/README.md` must not contain internal hostnames, internal identities,
or non-public token names. Use `<your-docker-image>`, `<CE_SITE>`, `<output-path>` as
placeholders where actual values are caller-supplied. The harness is intended to be
published alongside the rest of `deploy/`.
