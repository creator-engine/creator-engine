# Contract: Two-mode installer + onboard apply (G-7.4 · E.2/E.3)

**Status:** Canonical. The CI-pure decision substrate is
`creator_engine_validator/v3_installer.py`; the served artifacts are
`docs/install.sh` (the one-liner) and `docs/llms-install.md` (the
agent-native signed spec) — both at the Pages root, so the served URLs
(`creator-engine.dev/install.sh`, `creator-engine.dev/llms-install.md`) are the
file paths. The opt-out wires the G-5 fields validated by
`ce_spend_envelope`; the answers file is validated by the `install_answers`
check against `schemas/install-answers.schema.yaml`.

## Purpose

The **operator-typeless** install: a developer installs CE without typing setup
commands. Two modes, one human contract.

- **One-liner** — `curl …/install.sh | bash` → `onboard` (the OpenClaw
  `curl … | bash` pattern). Served + hash-published.
- **Agent-native** — the operator points their agent at the CE site; the agent
  fetches the **signed install spec** (`llms-install.md`), **verifies it against a
  pinned CE public key BEFORE executing**, and assists the interactive GitHub-App
  step.

Both provision the runtime backend (gVisor `runsc` + a deny-by-default egress
proxy) + the GitHub App (PEM-on-tmpfs custody → a JIT scoped token, never in the
box) + the policy bundle, and **expose the v3 CLI as `ce`** (see below).

**Human contract:** the operator types nothing and approves only **sudo**
(privileged dependency installs) + the **GitHub-App authorization click**.

## One engine, two modes — the answers file + the input inventory (v3.5-E.3)

The two modes are ONE pipeline of journey steps (verify → answers → probe →
plan → apply), each declaring its inputs against a single **operator-input
inventory** derived from `schemas/install-answers.schema.yaml` — the single
source of truth: its `x-ce-*` annotations carry each input's journey step,
sensitivity (`plain`/`consent`/`ratification`/`secret`), supply modes
(`F` file-by-value · `R` by-reference · `I` interactive · `D` detected), and
applicability; the interactive prompts, the `--inventory` emission, and the
file validation all derive from it (never hand-maintained). Mode is just
*where answers come from*:

> **`interactive > answers-file > detected > default`** — one precedence
> rule, no exceptions. A file value that *contradicts* a detected fact
> (e.g. `github.repo` ≠ the cwd origin) is a SURFACED CONFLICT (ask
> interactively / refuse non-interactively, `merge_answers`), never a silent
> override of reality.

- **The answers file** (`ce-install.answers.yaml`, IaC-style): declarative,
  schema-validated, **partial-by-design** (every key optional; absent keys
  join ONE batched ask at their journey step), **fail-closed on unknown
  keys** (`additionalProperties: false` everywhere — a typo'd key ERRORS,
  never *looks* consumed), and **committable** — it lands via governed PR,
  and the `install_answers` Ring-1 check (`VAL-IA-*`) holds the same floor
  in CI that the engine holds at apply time.
- **Secrets never by value:** every secret-typed field is a **SecretRef**
  (`env://` · `file://` · `prompt://` · `keychain://`) — the schema pattern
  PLUS a belt-and-braces raw-value refusal in the engine
  (`require_secret_ref`). Refs resolve at apply time only, in memory;
  evidence records the *ref*, never the value.
- **Governance-weakening answers require ratification:** the cost opt-out
  and any `github.protections` below the CE reference floor take the SAME
  ratified-HUMAN-only binding `{ratified_prompt_sha, approver_ref,
  educate_acknowledged: true}` (`valid_ratification`, generalizing the G-5
  opt-out into an installer-wide invariant). *An agent preparing an answers
  file can configure anything except a weaker grader.*
- **The scoped sudo pre-grant:** `host.sudo_grant` is an explicit package
  allowlist (a bare `sudo: true` is schema-invalid by construction);
  `sudo_grant_diff` stops on any planned privileged install OUTSIDE the
  grant — drift never silently widens a privileged action.
- **`--non-interactive` is fail-closed:** `missing_answers` +
  `require_complete` refuse with EXACTLY the unresolved inputs (the
  terraform `-input=false` analog) — never proceed on a guess, never ask.
- **Nothing in the file bypasses `require_verified`:** the answers file
  configures the VERIFIED procedure; the signature gate stays first and
  unbypassed in both modes.

## The GitHub leg, decomposed (pure planners, injected probes)

What was one named step ("the operator approves the GitHub-App authorization
click") is decomposed into plannable parts — all PURE with injected read-only
probes (mirroring `plan_dependencies`); the live API **mutations** stay the
deferred seam behind the forge mint leg (`forge.app_jwt_runner`, HTTPS-Bearer
App-JWT — `gh` cannot App-JWT auth; the protection PUT shape lives in
`forge.github_repo_config`):

- **Repo plan** (`plan_repo`): `existing` (detect-and-offer the cwd origin)
  vs `new` (visibility / default branch / description); idempotent — a
  re-run where the repo already exists converges to use-existing.
- **Bootstrap-token scope VERIFICATION** (`bootstrap_scope_table`): the
  installer's one-time credential is *checked, not asked* — minimal
  fine-grained scopes `administration:write · contents:write ·
  actions:write · workflows:write` (+ org repo-create iff new-in-org);
  unprobed = fail-closed. Never stored: runtime forge access is the App's
  JIT scoped token, never this one.
- **App plan** (`plan_github_app`): `shared` (the CE-published App — the
  solo-pilot default) vs `own` (`app_id` / `client_id` / PEM **SecretRef,
  tmpfs custody**); **click-or-detect** — the click is the contract's
  irreducibly interactive human-approval step on the FIRST run; a detected
  (or declared) `installation_id` SKIPS it on re-run, so the *converged*
  state is fully declarative.
- **Branch-protection desired-state diff** (`plan_branch_protection`): the
  reference posture lives AS DATA in the answers schema
  (`x-ce-reference-posture` — strict, dismiss-stale, enforce-admins,
  required reviews ≥ 1, the CE required check, squash-only); read current
  state → diff → plan ONLY the drift → report the diff before any mutation
  (declarative reconciliation; same answers, second run → empty plan).
  `required_checks` apply as a UNION — configuring never silently drops a
  check someone else registered.
- **Actions plan** (`plan_actions_workflow`): enable Actions + install CE's
  validate workflow so the required check exists and runs on every PR.
- **Reviewer-identity floor** (`reviewer_identity_floor`): a reviewer must
  exist and differ from the AUTHOR identity of CE's PRs (the App bot) —
  solo: the human (the bootstrap token's authenticated login) IS the
  reviewer, so no-self-approval holds.

`build_github_leg_plan` composes all of it from a *validated* answers
document plus one probe dict; `converged: true` is the terraform
empty-plan analog.

## Onboard apply (E2 live-drive seam)

`creator_engine_validator/onboard_apply.py` is the side-effecting v3 runtime
module for `ce onboard --apply`. `v3_installer.py` remains pure; `v3_cli.py`
loads files, performs read-only probes, verifies the signed spec, and delegates
the bounded apply pass.

Apply is explicit. `--inventory` and `--plan` remain non-mutating, and
`--plan --apply` is invalid. Apply refuses content-digest self-attestation and
accepts only the real SSHSIG path over canonical bytes (`ssh-ed25519`,
`ce-root-v1`, namespace `ce-spec-v1`, matching `content_sha256`).

The apply executor acquires `<state_root>/onboard/apply.lock`, appends
non-secret leg evidence to `<state_root>/onboard/ledger.ndjson`, and runs the 12
ratified E2 legs in order: signed-spec verify, answers merge, host dependencies,
runtime posture, CLI exposure, bootstrap-token probe, greenfield repo create,
App install, workflow install, branch protection, workspace checkout, and
first-project smoke. All environment-specific work is behind injectable
runners/transports so tests use fakes and live rehearsals can supply concrete
host/GitHub drivers.

E2 is greenfield-only. A repo created by an earlier E2 pass can be reused only
when ledger provenance and live verification match. An arbitrary existing repo
is refused as `brownfield_deferred`; E3 owns brownfield adoption. SecretRefs
resolve only at the moment of use, and summaries/ledger entries carry refs or
redacted facts, never secret values.

The first-project smoke uses the existing v3 Scope front gate: file a
deterministic Scope, ratify it with a value-free local test approver digest, and
run `drive` to assemble governed dispatch inputs. Optional spawn smoke records
either spawn metadata or an explicit conserved refusal; E2 does not claim a PR
delivery proof.

## Verify-before-execute (the load-bearing gate)

The agent-native spec is **signed**; the installer **refuses to execute an
unverified spec**. `v3_installer.require_verified` is the gate — it refuses
(`InstallRefused`) unless the signature names a **pinned** `key_id`
(`PINNED_KEYS`) AND the verifier accepts the value. This is "the grader lives
outside the agent" at install time: the human ratifies the privileged step; the
rest runs under a **verifiable** spec.

This repo ships no asymmetric-crypto dependency, so the **in-tree floor** is a
content-address (sha256) integrity binding, with the real asymmetric verify
supplied through an **injectable verifier** seam (the published CE public key +
the algorithm backend) — mirroring the forge App-JWT injected-signer pattern. The
load-bearing logic (verify before execute · refuse on tamper / unknown key) is
CI-pure; only the cryptographic primitive is the injected/deferred backend.

### The served trust root + the real detached signature (E.4-fix)

The served `llms-install.md` carries a **real detached OpenSSH signature
(SSHSIG)**, verifiable with **stock `ssh-keygen`** — no CE tooling, which is what
breaks the install-time bootstrap circularity (you should not need `ce` to trust
the spec that installs `ce`).

- **Trust root** — `docs/keys/ce-root-v1` (Pages → `creator-engine.dev/keys/ce-root-v1`,
  extension-less) is an OpenSSH `allowed_signers` file: one
  `ce-root-v1 ssh-ed25519 <pubkey>` line (the principal IS the `key_id`), listed
  in `docs/llms.txt`. **Custody (Fork A, ratified 2026-06-10):**
  Operator-authorized, orchestrator-generated 2026-06-10; the **private key is
  Operator-held offline** at `~/.ce-keys` (0700/0600) and never enters the repo
  or any seat. Signing a spec is a **manual Operator act per release**
  (`ssh-keygen -Y sign`). Single key, v1 — **no rotation machinery**.
- **Namespace** — the SSHSIG namespace is fixed in-spec: **`ce-spec-v1`**
  (`v3_installer.SSH_SIG_NAMESPACE`). A wrong namespace fails verification.
- **Canonical-bytes rule** — the signature (and the retained `content_sha256`
  floor) cover the **canonical bytes**: the whole spec with the signature block's
  `value:` and `content_sha256:` lines normalized back to the placeholder token
  `<published-with-this-spec>` (full line; everything else byte-for-byte UTF-8).
  This reuses the E.3 content canonicalization and extends it to every dynamic
  signature field, so embedding the real values never changes what is signed; an
  agent reproduces the bytes with one stock `sed` (`canonical_spec_bytes` is the
  in-tree mirror). The agent recipe lives in `llms-install.md` §0.
- **Validator seam** — `v3_installer.ssh_ed25519_verifier(runner)` is the
  `algo: ssh-ed25519` verifier built on an **injected runner** (the CLI/tests
  shell `ssh-keygen -Y verify`; the module stays subprocess-free) — a missing
  runner / missing binary / any runner error ⇒ fail-closed `VerifyResult(False)`.
  `parse_allowed_signers` loads the pinned key from the served file (PURE; text
  injected). The content floor (`content_sha256`) is retained as the in-tree
  integrity check. `sign_spec(..., signer=…, algo="ssh-ed25519")` /
  `operator_sign_recipe()` document the Operator's offline signing flow — never
  automated, the private key never touches the repo.

### How `ce` arrives (the bootstrap leg)

`llms-install.md` §0.5 states the supported acquisition paths for `ce` itself —
the served **one-liner** (`curl …/install.sh | bash`) and **clone + offline
wheelhouse** — each with an **honest** integrity note: transport integrity is TLS
(+ the published hash for `install.sh`); the cryptographically **verified** trust
anchor for the install *procedure* is this signed spec (§0), not the one-liner.
`install.sh`'s own posture is stated, not overstated — it asserts no signature
over its own body beyond TLS + the published hash, and takes no privileged action
without an explicit batched sudo approval.

## Dependency resolution — detect-don't-assume, fix-with-permission

`v3_installer.plan_dependencies` plans, never fail-on-missing: it **detects** each
of `git · python · runsc · proxy · uv` (a **read-only** probe — the CLI does it
live via `shutil.which`; the planner is pure), then for the missing ones plans a
**permission-gated, idempotent** install (`runsc`/`proxy`/`git`/`python` need
sudo, **batched** into a single ask; `uv` is user-space). Present tools are
skipped (idempotent); the operator may gracefully decline.

## The Default-vs-Custom profile + the cost opt-out

`v3_installer.build_profile` surfaces the cost-enforcement choice at install
(`docs/contracts/spend-envelope.md`):

- **Default** → `spend_cap_enforcement: enforce` (cost-runaway protection on — the
  #1 pilot blocker stays closed).
- **Custom opt-out** → `spend_cap_enforcement: off` + a **REQUIRED**
  `spend_cap_optout {ratified_prompt_sha, approver_ref}` (64-hex) binding. The
  opt-out is **ratified-HUMAN-only** — `build_profile` raises `InstallRefused`
  without a valid binding (an agent can never opt out). The emitted fragment is
  exactly what `ce_spend_envelope` accepts (`VAL-SPEND-OPTOUT-UNRATIFIED`
  otherwise).
- **Educate-at-opt-out (verbatim):** *"Turning this off won't speed up your runs;
  it only removes per-run / per-fleet budget friction. The runaway-detection net
  (global ceiling + anomaly → escalate) stays on."*
- **Cap / detection split:** the opt-out disables only the budget **CAPS**; the
  always-on runaway **DETECTION** net (the mandatory global `$` ceiling +
  anomaly → escalate) stays on. *Caps off ≠ blind.*

## The `ce` exposure (Operator-ratified user-facing-name directive)

The pilot installs **v3 only** (no v1 `ce` to collide with), so the installer
exposes this CLI **as `ce`** (`ce_exposure_plan` — an alias/symlink onto the
internal `cev3` console_script, or a v3-only distribution whose script is named
`ce`). The user types `ce`; the internal monorepo entry `cev3` exists only to
avoid the v1 collision in the coexistence repo and is never shown. A
version-stamped user command (`cev3`/`cev4`) is the anti-pattern this avoids.

## Boundary (pure planner; live executor seam)

CI-pure: verify-before-execute · the dependency planner · the profile/opt-out ·
the answers/inventory engine (validation, precedence merge, missing list,
sudo-grant diff) · the decomposed GitHub-leg planners · the `ce` exposure plan ·
`ce onboard` dry-run. The E2 live executor is the composition seam: it drives
host/runtime/GitHub/workspace actions only through injected drivers and verifies
each leg before proceeding. The read-only *detection* (dependency probe; GitHub
facts injected into planners) remains live; the privileged *fix* is explicit
`--apply`.

## Standing requirements honored

- **G-4.1 naming hygiene:** `v3_installer` and `onboard_apply` are v3-classified;
  `v3_installer` is residue-clean and pure;
  no `.hermes/`/`.claude/` state. **v1↔v3 coexistence:** additive; **v1 deleted =
  ∅** (the internal `cev3` console_script from G-7.0 is unchanged). **version
  boundary:** `v3_installer` imports stdlib plus (lazily, answers-validation
  only) the pinned `jsonschema` — the schema document is injected; the module
  never reads disk. `v3_cli`→`v3_installer` is v3→v3; no `shared→v3` edge (the
  `install_answers` check is shared and imports no v3 module — the invariant
  predicates are deliberately mirrored, exactly as `ce_spend_envelope` mirrors
  the opt-out shape).
- **G-5:** the opt-out fragment feeds `ce_spend_envelope` unchanged (the
  answers-file binding is stripped of `educate_acknowledged` by
  `optout_binding_from_answers` — the policy fragment is
  `unevaluatedProperties: false`).
- **Registry:** the `install_answers` check registered 51 → 52 (declared,
  E3-G1); `schemas/install-answers.schema.yaml` declared in
  `_versions.V3_SCHEMAS`.

See also: `docs/architecture/pilot-deployment-transport.md`,
`docs/contracts/spend-envelope.md`, `docs/llms-install.md`,
`docs/install.sh`, `docs/operations/ONBOARD_APPLY_PROTOCOL.md`,
`schemas/install-answers.schema.yaml`.

## E2 carrier baseline

For the per-gate E2 commit on `v35e-prime-wave`, wheel/source parity is a named
intra-branch baseline: the ratified night mandate rebuilds the source/wheel pair
once at branch end under the E1 manifest leg. The union branch must clear this
baseline before merge.
