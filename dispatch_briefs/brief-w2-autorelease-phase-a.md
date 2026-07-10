# WORK CLAIM — Autonomous Release Phase A: stage-to-seam release pipeline (`release-bump` / `release-changelog` / `release` / release workflow)

**Seat:** dev-1. **Role:** implementer-foreman. **Born foreman** — fan out.

## Branch
```
git fetch origin && git checkout -b ce-autorelease-phase-a origin/main
```

## Why (self-contained — design embedded; do NOT rely on any external doc path)

CE has **no autonomous release path** today. The live tree has only two workflows (`.github/workflows/validate.yml`, `ce-ops-autoclose.yml`); versioning is a hand-edit of `version.py` + `pyproject.toml`; the ~268 `.ce/changelog/*.md` fragments have **no assembler**; and the existing `release-stage` helper (`validators/creator_engine_validator/release_publish.py`, today reached via the validator `cli.py`) builds the wheel + `SHA256SUMS`, stages the mirror, rewrites the `llms-install.md` placeholder, and **hard-refuses real signing by design** (it only emits the placeholder `<RESIGN-REQUIRED-ce-root-v1>` and the `ssh-keygen -Y sign` instructions for the Operator).

**The release thesis (CEO-mode):** cut a release with a single human gesture — the offline `ce-root-v1` signature — and let a triggered pipeline do the mechanics around it. The release splits into eight steps; this work delivers the MACHINE half **up to the human gesture only** (steps 1–5 plus the trigger/draft surface). The human still signs and publishes by hand, exactly as today, but now from a one-command staged, fully-verified, signature-shaped artifact.

**Phase A scope = stage-to-seam. No publish automation. No auto-sign. No signature intake.** That is Phase B and is OUT OF SCOPE here.

The four Phase A units (do these IN SEQUENCE — see the collision note below):

- **W2a `release-bump`** — a new validator subcommand. The semver source of truth is `version.py:__version__` (already AST-read by the packaging guard and coupled to `pyproject.toml:version`). The bumper writes BOTH atomically and **re-runs the existing packaging guard** so the coupling can never drift. For the tag path the target version is **derived from** a `release/vX.Y.Z` tag and the bumper **asserts** `tag_version == version.py.__version__` after bump (fail-closed; mirrors the existing `release_publish.py` `wheel_manifest.version != version → raise` pattern). Also support a `--part {major,minor,patch}` rehearsal mode that computes the next version from the last `release/*` tag. Reuse the existing `version_runtime.render_build_file` machinery; do NOT do version edits as raw CI `sed`.

- **W2b `release-changelog`** — a new validator subcommand that assembles `.ce/changelog/*.md` fragments into dated release notes. Fragments already use YAML front-matter (`slug`/`ticket`/`type`/`scope`, or `slug`/`date`/`kind`/`scope`/`issue`) + a prose body. **Fork/adopt `towncrier`** (do not build a bespoke aggregator — rent/fork before reinvent) with a thin, **non-destructive adapter** for the existing `ceNNN-slug.md` naming so towncrier can group by category. Select fragments **since the last `release/*` tag** (prefer a deterministic `last-released` marker over commit-date heuristics so the set is re-runnable). Output `docs/changelog/X.Y.Z.md` + the GitHub Release body. **Do NOT delete/move consumed fragments in Phase A** — archive-on-publish (`.ce/changelog/archive/X.Y.Z/`) is a Phase B publish-step concern; here, leave the active dir intact.

- **W2c `release` orchestrator** — a new validator subcommand wrapping the staging DAG steps 1–5: **preflight** (resolve version from tag; assert clean HEAD; run `ce validate-pr` parity) → **bump** (W2a) → **changelog** (W2b) → **release-stage** (WRAP the existing `release_publish.py` `stage_signed_release`; do NOT reimplement it — it is already fail-closed/atomic/HEAD-pinned). Pure-staging, fail-closed, `--dry-run`. It **emits the ratification packet**: the canonical bytes to sign (`llms-install.canonical`), `release-stage-manifest.yml` (version, shas, signing key id), `SIGNING-INSTRUCTIONS.md` (the exact `ssh-keygen -Y sign … < llms-install.canonical` command), and `canonical_spec_sha256`. The packet surfaces the intended anchor `ce-root-v1` for public releases (code default is `ce-dev1-root-v1`; do not change the default in Phase A, just surface the intended anchor in the packet).

- **W2d release workflow** — `.github/workflows/release.yml`: trigger on `release/vX.Y.Z` **annotated tag push** PLUS `workflow_dispatch` with a `version` input and `dry_run` (default **true**). The job MUST `checkout` the **tag ref**, not `main` (main may have advanced; `release-stage` pins to the tagged commit). The job runs the `release` orchestrator (W2c), uploads the staged ratification packet, and **opens a GitHub Release DRAFT + a sign surface (release-sign issue / `⏸️ AWAITING-OPERATOR` marker)** presenting the version, changelog, `canonical_spec_sha256`, and the one signing command. **NO PUBLISH. NO SIGNATURE INTAKE. NO COMMIT TO `docs/` ON MAIN.** Signing stays a human offline `ce-root-v1` step (FR-008); the only path to "live" is a cryptographic artifact only the Operator can mint — that flip is Phase B.

**Why signing stays human (do not auto-sign, do not stage anything but the placeholder):** `ce-root-v1` is the installer trust anchor; auto-signing puts the root key on a pipeline-reachable surface (the reserved deploy/credential-issuance class, FR-008). Author/approver separation (FR-007) requires the builder ≠ the ratifier. Phase A's pipeline only ever emits the placeholder + instructions — the existing `release-stage` refusal posture is preserved verbatim.

## ⚠️ ce_cli.py collision ownership (READ — this governs sequencing)

For this fan-out **dev-1 OWNS all `ce_cli.py` subcommand registrations.** The release subcommands all register parsers + dispatch entries in `validators/creator_engine_validator/ce_cli.py`, which is a high-churn shared file. Other in-flight CLI work (`ce push`, `ce dispatch plan`) will **rebase on top of** dev-1's release changes. Therefore:

- Do the four units **STRICTLY IN SEQUENCE**: W2a → W2b → W2c → W2d. Either **one coherent PR** for the whole Phase A, or **one PR per unit landed in order** (do NOT run them as parallel concurrent branches — they all touch `ce_cli.py` and would conflict). If splitting, each subsequent branch is cut from the merged/pushed prior branch (or rebased on it), never independently from `origin/main` in parallel.
- Keep every `ce_cli.py` edit additive and localized to the new `release*` parsers + dispatch table entries; do not refactor neighboring parsers.

## Allowed paths (nothing else)
- `validators/creator_engine_validator/ce_cli.py` (new `release-bump` / `release-changelog` / `release` parser + dispatch registrations only)
- `validators/creator_engine_validator/release_bump.py` (new)
- `validators/creator_engine_validator/release_changelog.py` (new)
- `validators/creator_engine_validator/release_orchestrator.py` (new)
- `validators/creator_engine_validator/release_publish.py` (read/WRAP only — minimal seam changes if strictly required to call `stage_signed_release`; do NOT relax its signing refusal)
- `.github/workflows/` (new `release.yml`)
- `.ce/changelog/` (towncrier config / adapter + a new fragment for this work; do NOT delete existing fragments)
- `validators/tests/**` (new tests for each unit)
- `.ce/pr-manifests/**`

## Evidence (DoD)
Full `ce validate-pr` GREEN (CI-parity, full suite) on a clean tree before push. Demonstrate, per unit:
- `release-bump`: tag-derived version drives `version.py`+`pyproject.toml` atomically; packaging-guard coupling re-asserted; tag/version mismatch fails closed.
- `release-changelog`: fragments assembled into `docs/changelog/X.Y.Z.md` via towncrier + adapter; existing fragments untouched.
- `release` orchestrator: `--dry-run` produces the ratification packet (`llms-install.canonical`, `release-stage-manifest.yml`, `SIGNING-INSTRUCTIONS.md`, `canonical_spec_sha256`); placeholder signature only; fail-closed.
- `release.yml`: validates as a workflow; tag-ref checkout; opens a Release DRAFT + sign surface; performs no publish/commit-to-main/signature-intake.

⚠️ **G5 BODY FORMAT (mandatory):** each PR body MUST contain exactly ONE line formatted precisely as `- **Declared work class:** <tiny|story|feature|epic>` (a `**Work class:**` header or a `[PASS]` log line does NOT match — this papercut has failed PRs). Pick the tier the gate derives.

## Stop-line
- Green + self-push works (dev-1 has its own creds) → push + open PR refs ce-ops Autonomous Release Phase A. **Do NOT approve, merge, or enqueue.**
- **Do NOT publish a release.** No GitHub Release publish (draft only), no commit of signed `llms-install.md` / `docs/downloads/X.Y.Z/` to main, no signature intake/verify. The offline `ce-root-v1` signature stays with the Operator — that is the single reserved human gesture and is Phase B, out of scope.
- Preflight RED on a NEW gate from your change → STOP + report the failing gate.
- If you find the `release` command family belongs in the validator `cli.py` dispatcher rather than `ce_cli.py` (where `release-stage` already lives) → STOP + report before splitting the work, so the Orchestrator can confirm the dispatcher seam.
