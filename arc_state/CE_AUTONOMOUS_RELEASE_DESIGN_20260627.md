# CE Autonomous Release — Definitive Design (CEO-mode Release)

**Author:** research/design worker · **Date:** 2026-06-27 · **Host:** DGX Spark (CE-DEV-2 controller)
**Status:** design only — no code, no PR, no gate touch. Companion to the gate-doctrine (`ce-gate-authority-vs-containment-doctrine`), the auto-merge engine (#291/#561), the release-parity guard (#260), and `deploy = Source-only` policy.

---

## 0. The one-line thesis

> **Cut a CE release with a single human gesture — the offline `ce-root-v1` signature — and let a triggered pipeline do everything else (build, version-bump, changelog, stage, verify, and post-signature publish).**

This is the *release* analogue of CEO-mode auto-merge: the human stays the **root of trust and the ratifier**, the machine does the **mechanics**. We deliberately do **not** automate the root signing — that would hand the trust anchor to a pipeline and break `deploy = Source-only`. Instead we shrink the human's release work to one signing tap by automating both *sides* of it.

---

## 1. Recon verification (cited, re-checked 2026-06-27)

Everything in the brief verified against the live tree:

| Claim | Verified | Evidence |
|---|---|---|
| No autonomous release; only 2 workflows | ✅ | `.github/workflows/` = `validate.yml`, `ce-ops-autoclose.yml` only |
| `release-stage` helper exists | ✅ | `cli.py:260` parser, `cli.py:592` dispatch, `cli.py:599` `_release_stage` |
| Builds wheel + SHA256SUMS + stages mirror + rewrites `llms-install.md` placeholder | ✅ | `release_publish.py:433` `stage_signed_release`; `PLACEHOLDER_SIGNATURE = "<RESIGN-REQUIRED-ce-root-v1>"` (`:25`) |
| Hard-refuses real signing | ✅ | `release_publish.py:89-90` `if sign_mode != "placeholder": raise ... "root signing is Operator-gated"`; CLI `choices=["placeholder"]` (`cli.py:278`) |
| `ce-root-v1` Operator-held / offline / manual `ssh-keygen -Y sign` | ✅ | `release_publish.py:344-361` `_render_signing_instructions`; `BUILD_NOTE.md` "Operator Follow-Up" block: `ssh-keygen -Y sign -f ~/.ce-keys/ce-root-v1 -n ce-spec-v1` |
| `deploy = Source-only` invariant | ✅ | `DEPLOYMENT_APPROVAL_POLICY.md` §d "No agent may deploy without Source-ratified authority"; §f.5 "Any deploy-automation workflow, signing key, release pipeline ... is Feature 006 scope" |
| Versioning manual, `vMAJOR.MINOR.PATCH` | ✅ | `VERSIONING_AND_RELEASE_POLICY.md`; `version.py:__version__ = "0.2.0"` hand-set; `pyproject.toml:7 version = "0.2.0"`; coupled by packaging guard (AST read) |
| Download dirs hand-created | ✅ | `docs/downloads/0.2.0/` only |
| Changelog fragments hand-authored, no aggregator | ✅ | `.ce/changelog/` = ~250 `.md` fragments, no assembler script anywhere |
| Pages serves `docs/` on main | ✅ | `docs/CNAME` = `creator-engine.dev` |
| Parity guard (#260) landed | ✅ | commit `7e940764` added `checks/release_artifact_parity_guard.py` + tests; runs in-validator |

**New findings worth design weight:**

- `release-stage` is already **fail-closed and atomic**: HEAD-pinned (`_select_build_git_sha`), wheel/source parity verified (`verify_wheel_matches_source`), staged-hash re-verified (`verify_stage_hashes`), atomic `_promote_stage` with rollback. It is production-grade *up to* the signing seam. The pipeline should **wrap, not reimplement** it.
- The signing seam is already a **clean, machine-emittable contract**: `stage_signed_release` returns a `ReleaseStageResult` carrying `canonical_spec_sha256`, `signing_command`, and `signature_placeholder`, and writes `SIGNING-INSTRUCTIONS.md` + `release-stage-manifest.yml` + a `llms-install.canonical` byte-exact file into the staged dir. **The "one gesture" contract already exists in code** — we only need to deliver those bytes to the Operator and accept the signature back.
- `--signing-key-id` defaults to `ce-dev1-root-v1` (an allowed trust anchor alongside `ce-root-v1`). The pipeline must make the chosen anchor explicit per release (see §6).
- The parity guard (#260) is the **post-publish correctness oracle**: it asserts the published `docs/downloads/<v>/` artifacts match the signed `llms-install.md` manifest. The release pipeline can run it as the publish gate.

---

## 2. The CEO-mode release split (core thesis)

A release is a sequence of **eight steps**. We classify each as MACHINE (G-grantable automation) or HUMAN (R-reserved root gesture):

| # | Step | Today | Target | Class |
|---|---|---|---|---|
| 1 | **Trigger** | nonexistent | `release/vX.Y.Z` annotated tag push (see §3) | MACHINE |
| 2 | **Version-bump** | manual edit of `version.py`/`pyproject.toml` | semver source-of-truth + bumper (§4) | MACHINE |
| 3 | **Changelog-aggregate** | manual | fragment assembler → release notes (§4) | MACHINE |
| 4 | **Build wheel** | `release-stage` (automated) | wrap `release-stage` | MACHINE |
| 5 | **SHA256SUMS + mirror-stage** | `release-stage` (automated) | wrap `release-stage` | MACHINE |
| 6 | **Sign canonical bytes (`ce-root-v1`)** | manual `ssh-keygen -Y sign`, refused-by-design in pipeline | **stays manual — the ONE gesture** (§5) | **HUMAN / R-reserved** |
| 7 | **Inject signature → publish to `docs/`** | manual edit + commit | automated post-signature publish (§5, §6) | MACHINE (armed) → flips on HUMAN sig |
| 8 | **Pages deploy** | implicit (main push) | automated republish within Source-only (§5) | MACHINE |

**The split:** automate 1–5 and 7–8; keep **6** the single human gesture. Steps 1–5 produce a **staged, fully-verified, signature-shaped artifact**; the human reviews + signs offline; the signature flows back and steps 7–8 fire automatically. The Operator's release workload collapses from a documented multi-command `BUILD_NOTE.md` ritual to: *review the staged manifest, run one `ssh-keygen` (or hardware-token tap), paste the signature.*

**Why signing stays human (do not auto-sign):**
1. **Trust-root custody.** `ce-root-v1` is the anchor every installer verifies against (`docs/keys/ce-root-v1`, DNS anchor `_ce-root-v1.creator-engine.dev`). Auto-signing puts the root key on a pipeline-reachable surface — exactly the "irreversible-outside-set" / "credential-or-token issuance" class that `DEPLOYMENT_APPROVAL_POLICY.md` §c and FR-008 reserve to Source.
2. **It is the amortized ratification.** Mirrors the gate doctrine's "human-rooted ratification (amortizable)" moat: the human makes ONE decision ("this is the release"), the signature is the durable, attestable proof, and the pipeline executes deterministically around it. Same shape as the docs-only auto-merge first-flip (R2).
3. **Author/approver separation (FR-007).** A pipeline that both *builds* and *signs* is author==ratifier. Keeping the sign offline preserves separation structurally.

**One-gesture mechanics (the seam, already 90% built):**
- Pipeline stages everything and emits to the staged dir: `llms-install.canonical` (byte-exact bytes to sign), `release-stage-manifest.yml` (version, shas, signing key id), `SIGNING-INSTRUCTIONS.md` (the exact `ssh-keygen -Y sign … < llms-install.canonical` command), and `canonical_spec_sha256`.
- Pipeline opens a **"release ratification" surface** (a GitHub Release *draft* + a ce-ops "release-sign" issue, or a `⏸️ AWAITING-OPERATOR` marker per the queue rule) presenting: the version, the changelog, the `canonical_spec_sha256`, and the one command.
- Operator signs **offline** (laptop/host holding `~/.ce-keys/ce-root-v1`, or a hardware token tap). No private key ever touches the pipeline.
- Operator returns the base64 SSHSIG (paste into the release issue / `workflow_dispatch` input / a signed commit of `llms-install.md`).
- Pipeline verifies the signature against `docs/keys/ce-root-v1` for the staged `canonical_spec_sha256`, injects it into `llms-install.md`'s `value:` field, runs the parity guard (#260), and publishes (§5).

---

## 3. The trigger pipeline

**Recommended trigger: an annotated `release/vX.Y.Z` tag push, gated by a CODEOWNERS-protected tag ruleset.** Rationale:

- **Explicit + auditable.** A tag is a deliberate, named, signed-able act — it *is* the "this is a release" decision boundary. Unlike `workflow_dispatch` (ephemeral, no durable artifact) or "curated main state" (ambiguous — every merge looks like a candidate), a `release/*` tag is a single unambiguous event with a name that *is* the version.
- **Decouples from per-merge churn.** Auto-merge (#291/#561) lands many PRs to main; we do **not** want each to attempt a release. The tag is the explicit cut point over an already-green main.
- **Self-documents the version.** `release/v0.3.0` *is* the version input — no separate bump argument to get wrong (the bumper in §4 derives target from the tag and asserts source agreement).
- **Tag protection = the arm.** A GitHub **tag ruleset** restricting who may push `release/*` tags makes the *trigger itself* a governed act (only Operator or the merge-gate identity can arm a release), without making the *signing* automated.

**Secondary trigger (keep, for re-stage / dry-run):** `workflow_dispatch` with a `version` input and `dry_run` default-true, so the Operator can rehearse staging (and review the canonical bytes) before pushing the real tag. This maps directly onto `release-stage --dry-run`.

**Reject "curated main state" as the primary trigger:** it conflates "merged" with "released" — the exact category error `DEPLOYMENT_APPROVAL_POLICY.md` §g.5 warns against ("a merge approval … does NOT authorize any subsequent deploy").

### Staged flow (the pipeline DAG)

```
 push tag release/vX.Y.Z   (or workflow_dispatch, dry_run)
        │
        ▼
[1] preflight         resolve version from tag; assert clean main HEAD; run ce validate-pr parity (#252)
        │
        ▼
[2] version-bump      assert/raise version.py + pyproject to X.Y.Z (semver SoT); fail if mismatch w/ tag
        │
        ▼
[3] changelog-agg     assemble .ce/changelog/ fragments since last release tag → release-notes-X.Y.Z.md
        │
        ▼
[4-5] stage           creator-engine-validator release-stage --repo-root . --version X.Y.Z
        │              --out <stage> --signing-key-id ce-root-v1   (placeholder, atomic, fail-closed)
        │              → emits llms-install.canonical, release-stage-manifest.yml, canonical_spec_sha256
        ▼
[6] RATIFY (HUMAN)    open release-draft + sign surface; present canonical_spec_sha256 + one command
        │              Operator signs OFFLINE → returns base64 SSHSIG
        ▼  (signature arrives)
[7] inject+verify     replace placeholder value: with SSHSIG; ssh-keygen -Y verify against docs/keys/ce-root-v1;
        │              run release_artifact_parity_guard (#260) as publish gate
        ▼
[8] publish           commit signed llms-install.md + docs/downloads/X.Y.Z/ to main (Source-armed);
                       GitHub Release publish; Pages redeploys docs/  → live
```

Steps 1–5 are **one CI job** (fully automated, runs on the protected tag). Step 6 is a **manual_approval / environment-protection wait**. Steps 7–8 are a **second job** unblocked only by the returned signature.

---

## 4. Automate the two manual non-signing steps

### 4a. Version-bump

**Mechanism: tag-as-source + a `release-bump` subcommand on `creator-engine-validator` that drives `version.py`/`pyproject.toml` and asserts agreement with the parity guard.**

- **Single semver source of truth:** keep `version.py:__version__` as canonical (it's already AST-read by the packaging guard and coupled to `pyproject.toml:version`). The bumper writes both atomically and re-runs the existing packaging guard so the coupling can never drift.
- **Derive, don't invent:** the target version comes from the `release/vX.Y.Z` tag. The bumper **asserts** `tag_version == version.py.__version__` after bump (fail-closed) — this is exactly the `release-stage` pattern of `wheel_manifest.version != version → raise` (`release_publish.py:495`).
- **Semver discipline:** add a `release-bump --part {major,minor,patch}` mode for the `workflow_dispatch` rehearsal path that computes the next version from the last `release/*` tag (so the Operator picks "minor" not a literal string). For the tag-trigger path the version is the tag.
- **Why a subcommand, not a raw CI sed:** keeps version logic in the validator (testable, fail-closed, reused by the parity guard) instead of bash in YAML. Reuses the existing `version_runtime.render_build_file` machinery (`release_publish.py:488`).

`VERSIONING_AND_RELEASE_POLICY.md` already states "changing package versions … require a later, separate Operator-ratified publication gate." The bump *staging* is G-grantable; the bump only becomes *live* when it's committed as part of the Operator-signed publish (step 7–8). So the policy holds: nothing version-changing lands on main without the signature gesture.

### 4b. Changelog aggregation

**Mechanism: a `release-changelog` subcommand that assembles `.ce/changelog/*.md` fragments into dated release notes, then archives consumed fragments.**

- **Fragment model already exists** (~250 files in `.ce/changelog/`, named `ceNNN-<slug>.md`). Adopt a lightweight convention (a `towncrier`-style header or a YAML front-matter `{tier, ticket}`) so the assembler can group by category. Recommend **fork/rent `towncrier`** rather than build (per `ce-rent-or-fork-before-reinvent`) — it is the standard fragment-aggregator and matches the existing `.ce/changelog/` layout almost exactly.
- **Aggregate "since last release":** select fragments created/modified after the previous `release/*` tag's commit date, or (more robust) track a `last-released` marker so the set is deterministic and re-runnable.
- **Output:** `docs/changelog/X.Y.Z.md` + an updated top-level changelog index, and the GitHub Release body. The notes are part of the **staged, reviewable artifact** the Operator sees before signing — so the human still gets a final read of "what's in this release" at the one gesture.
- **Archive on publish:** move consumed fragments to `.ce/changelog/archive/X.Y.Z/` in the publish commit (step 8), keeping the active dir clean for the next cycle.

---

## 5. Publish / deploy within the Source-only invariant

Pages serves `docs/` from `main` (`docs/CNAME`), so **publishing = committing the signed artifacts to `docs/` on main**. The challenge: `DEPLOYMENT_APPROVAL_POLICY.md` §d/§f forbids an agent performing the deploy without Source-ratified authority, and §f.6 explicitly names "release tags pushed by an automated mechanism" and "deploy-automation workflow" as deferred/Source-gated.

**How automation stays inside the invariant — the signature IS the ratification token:**

1. **The Operator signature is the deploy authority.** The publish job (step 7–8) refuses to run unless it can `ssh-keygen -Y verify` a valid `ce-root-v1` signature over the exact staged `canonical_spec_sha256`. A valid signature is, by construction, a human Source act that cannot be forged by the pipeline (the key is offline). This satisfies §c.2 ("a separate ratification record … with Source as ratifier, on a surface the authority matrix designates as valid") — **the SSHSIG over the canonical install spec is that record**, machine-verifiable and durable.
2. **Record the ratification.** The publish job writes a `ratification record` (YAML, one file, per FR-016/FR-020a) under the tenant `ratification_storage_path` naming the release mutation id + the `ce-root-v1` signer, alongside committing the signature. This makes the deploy auditable from a fresh clone.
3. **Author/approver separation (FR-007).** The pipeline identity authors the staging; the Operator (signer) ratifies. Distinct actors — satisfied.
4. **Parity guard as the verifies-not-ratifies oracle (§g.1).** `release_artifact_parity_guard.py` (#260) runs as the publish precondition: it *verifies* the published `docs/downloads/X.Y.Z/` matches the signed manifest. Per §g it is verification, not ratification — correct: the signature ratifies, the guard verifies.
5. **Pages deploy is mechanical post-commit.** Once the signed `llms-install.md` + `docs/downloads/X.Y.Z/` are committed to main, Pages redeploys automatically. No separate "deploy environment" is created (consistent with §e "no deployment targets currently exist" — the deploy target is the public docs mirror, governed by the signature).

**Net:** the only thing that flips publish from armed→live is a cryptographic artifact only the human can produce. The machinery is fully built-and-armed; the human flips it. This is the **build+arm vs Operator-flip** pattern verbatim.

---

## 6. Integration with adjacent systems

- **Auto-merge engine (#291/#561, CEO-mode).** Auto-merge keeps `main` continuously green and releasable; the release pipeline is the **explicit cut over that stream**, triggered by the `release/*` tag — *not* per-merge. Clean separation of concerns: auto-merge owns "main is always shippable," release owns "this point is shipped." The tag ruleset (§3) is the handoff: only the merge-gate identity / Operator may arm a release tag.
- **Release-parity guard (#260).** Becomes the **publish gate** (step 7) and should also run in `validate.yml` on any PR touching `docs/downloads/**` or `docs/llms-install.md`, so a release can never stage against an already-inconsistent tree. Reuse `release_artifact_parity_guard.py` directly.
- **`ce validate-pr` (#252) preflight.** Step 1 runs the full local gate set on the clean release HEAD before staging — the standing "run full preflight before push" memory applied to releases.
- **Doc-autogen / support-bundle freshness.** A release is the natural **"rebuild the support corpus" checkpoint**, complementing per-merge doc-regen: at step 3–4 the pipeline regenerates the doc/support bundle from the exact released SHA so the published corpus is release-pinned (not drifting per-merge). Recommend the changelog-aggregate and doc-regen run in the same staging job so the Operator reviews a coherent snapshot.
- **Signing-key-id discipline (`ce-release-signing-key-id`, `ce-recipe-signer-parameterize`).** The pipeline must pass `--signing-key-id ce-root-v1` for public releases (the default in code is `ce-dev1-root-v1`); the chosen anchor is part of the signed canonical bytes and the verify-recipe principal (`release_publish.py:215` `_replace_recipe_principal`). Make the anchor an explicit, reviewed pipeline input, surfaced at the ratification gesture.

---

## 7. Governance / safety mapping

| Pipeline element | Class | Authority |
|---|---|---|
| Trigger workflow exists / runs | build-automation | **G-grantable** (CI authoring) |
| `release/*` tag ruleset (who may arm) | governance envelope | **R-reserved** to author (one-time setup, Source-ratified) — it *gates* who triggers, doesn't deploy |
| Version-bump staging | build-automation | **G-grantable** (staged only; lands on sig) |
| Changelog aggregation | build-automation | **G-grantable** |
| `release-stage` build/stage (placeholder) | build-automation | **G-grantable** — already refuses real signing by design |
| **Root signing (`ce-root-v1`)** | deploy / credential-issuance | **R-reserved — Source-only, offline, never automated** (FR-008, §c, §f.5) |
| Signature inject + publish commit to main | deploy | **MACHINE, armed; flips only on verified Source signature** — the signature is the FR-016 ratification record |
| Pages redeploy | deploy mechanics | MACHINE post-commit (no new environment; §e) |
| Ratification record write | governance record | MACHINE-written, Source-authored (records the human act) |

**Reconciliation with the wall + R-series:** the signing gesture is the wall — the human-in-the-loop credential gate. Building/staging/bumping/changelog up to the seam are within the day-shift G-grants (build/stage automation). The live publish-flip is R-reserved but **deterministic given the signature** — the Operator's single act of signing *is* exercising the reserved authority. No agent ever holds `ce-root-v1`; the pipeline can be fully autonomous and still never deploy without Source, because the only path to "live" runs through a cryptographic artifact only Source can mint.

**Auto-halt:** if the returned signature fails verification, or the parity guard fails, or the staged version disagrees with the tag, the pipeline halts → `⏸️ AWAITING-OPERATOR`. Fail-closed, mirroring `release-stage`'s existing posture.

---

## 8. Phased plan + ce-ops ticket list

**Phase A — Stage-to-seam (everything up to the gesture). Prove it, no publish automation.**
G-grantable; lands the autonomous staging half. Operator still publishes by hand (as today) but now from a one-command staged artifact.

- **ce-ops#A1 — `release-bump` subcommand.** Semver SoT bumper driving `version.py`+`pyproject.toml`, tag-derived, asserts coupling via packaging guard. (§4a)
- **ce-ops#A2 — `release-changelog` subcommand.** Fork/adopt towncrier over `.ce/changelog/`; assemble since-last-tag → `docs/changelog/X.Y.Z.md` + Release body; archive-on-publish. (§4b)
- **ce-ops#A3 — `release` orchestrator subcommand.** Wraps preflight→bump→changelog→`release-stage`; emits the ratification packet (canonical bytes, manifest, sha, one-command). Pure-staging, fail-closed, `--dry-run`. (§3 steps 1–5)
- **ce-ops#A4 — release workflow (trigger + stage job).** `release/vX.Y.Z` tag + `workflow_dispatch(dry_run)`; runs A3; uploads the staged ratification packet + opens the GitHub Release **draft** and the ce-ops release-sign surface. **No publish.** (§3)
- **ce-ops#A5 — `release/*` tag ruleset.** Governance: restrict who may push release tags to Operator/merge-gate identity (R-reserved one-time setup). (§3, §7)
- **ce-ops#A6 — parity guard in `validate.yml`.** Run #260's guard on PRs touching `docs/downloads/**` / `llms-install.md` so releases never stage on an inconsistent tree. (§6)

**Phase B — Post-sign publish automation (flip the gesture into a deploy).**
The R-reserved-but-deterministic half. Gated on Phase A proven on a real release (v0.3.0 candidate).

- **ce-ops#B1 — signature intake + verify.** Accept base64 SSHSIG (release-issue / dispatch input / signed commit); `ssh-keygen -Y verify` against `docs/keys/ce-root-v1` for the staged `canonical_spec_sha256`; inject into `value:`. Fail-closed. (§5.1)
- **ce-ops#B2 — publish job (armed→flip).** Second workflow job unblocked only by verified signature: commit signed `llms-install.md` + `docs/downloads/X.Y.Z/` to main, publish GitHub Release, archive consumed changelog fragments, write FR-016 ratification record. Runs parity guard (#260) as precondition. (§5.2–5.5, §6)
- **ce-ops#B3 — release ratification record schema.** YAML per-file record (mutation id + `ce-root-v1` signer + canonical sha) under `ratification_storage_path`. (§5.2, §7)
- **ce-ops#B4 — release doc/support-corpus rebuild.** Regenerate the release-pinned support bundle in the staging job; publish with the release. (§6)
- **ce-ops#B5 — `release-stage` signing-key-id surfacing.** Make `--signing-key-id ce-root-v1` an explicit, reviewed pipeline input shown at the gesture (default in code is `ce-dev1-root-v1`). (§6)

**Sequencing:** A1–A3 (validator subcommands, parallelizable) → A4–A6 (workflow + governance) → prove on a real dry-run + one hand-published release → B1–B5. Phase A alone already collapses the Operator's release work to "review staged packet + run the documented `ssh-keygen` + paste + push" — most of the win — while B turns the paste into the only manual step.

---

## 9. Risks / open questions

- **Towncrier vs bespoke aggregator:** towncrier expects a specific fragment naming/category scheme; the existing `.ce/changelog/` names (`ceNNN-slug.md`) need a thin adapter or a one-time rename. Recommend the adapter (non-destructive).
- **Tag-trigger on a fast-moving main:** main HEAD may advance between tag-push and staging. Mitigation: `release-stage` already pins to the *tagged* commit (`--build-git-sha` must match HEAD of the checkout); the workflow must `checkout` the tag ref, not `main`.
- **Signature return channel security:** a release-issue paste is convenient but the issue is public-ish; the SSHSIG is not secret (it's published anyway), so this is acceptable — the *key* never leaves the Operator. Prefer a signed commit of `llms-install.md` as the canonical return channel (it's self-verifying and lands exactly where it's needed).
- **`ce-dev1-root-v1` vs `ce-root-v1`:** the code defaults to the dev anchor. Public releases MUST use `ce-root-v1`; B5 makes this explicit and reviewed so a dev-signed artifact never publishes as a public release.
```
