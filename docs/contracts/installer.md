# Contract: Two-mode installer + onboard apply (G-7.4 · E.1/E.2/E.3/E.4)

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

- **One-liner** — `curl --proto '=https' --tlsv1.2 -fsSL …/install.sh | bash`
  → authenticated `onboard --inventory` from a user-local venv. Served +
  hash-published.
- **Agent-native** — the operator points their agent at the CE site; the agent
  fetches the **signed install spec** (`llms-install.md`), **verifies it against a
  pinned CE public key plus an out-of-band fingerprint anchor BEFORE executing**,
  and assists from the same inventory artifact.

E1 stops at authenticated inventory. It does **not** run sudo, provision the
runtime backend, automate the GitHub-App click, mutate branch protections, or
create/adopt a project. Those remain explicit later apply gates. E1 does create
or reuse the venv and proves the `ce` entry point before inventory.

**Human contract:** the operator types nothing during E1. Later apply gates are
where the human approves sudo-scoped host changes and the GitHub-App
authorization click.

**Bootstrap prerequisites:** E1 requires stock OpenSSH `ssh-keygen` before it can
verify the spec, plus basic POSIX tools used by the shell bootstrap (`curl`,
`sed`, `awk`, `grep`, `base64`, `mktemp`, `chmod`, `uname`, `date`, `mkdir`,
`rm`, `cp`, `mv`, `ln`, and `tar`). If any are absent, the installer MUST refuse
before fetching artifacts and emit one actionable remediation block with exact
package-manager commands for Debian/Ubuntu, Fedora/RHEL/CentOS, and Alpine.
The installer must not auto-sudo before trust verification.

CPython 3.14 and `uv` are not host prerequisites for E1. After the signed spec
and trust anchor are verified, the installer uses the signature-covered
`python_acquisition` manifest to fetch a pinned `uv` tarball, verify its hash,
and install CPython 3.14 in user space when no compatible interpreter is already
present.

Default one-liner installs require outbound access to:

- `creator-engine.dev` for the signed spec, trust root, answers schema, and
  wheelhouse artifacts.
- `https://dns.google` for the default out-of-band trust-anchor assertion used by
  `CE_TRUST_ANCHOR_URL`.
- `github.com` for the `astral-sh/uv` releases that provide the
  manifest-pinned `uv` tarball and CPython 3.14 acquisition when the host has no
  local Python `>=3.14`.

Egress-restricted environments must allow all three destinations before running
the default one-liner; blocking any one of them can make installation fail
non-obviously during trust verification or Python acquisition.

## E1 real bootstrap

`docs/install.sh` is the shell I/O edge. Its ordered contract is:

1. Fetch only `llms-install.md`, `keys/ce-root-v1`, and the out-of-band
   trust-anchor assertion into a mode-0700 temp workspace. A trust-anchor URL
   with the same origin as `CE_SITE` is refused before fetch.
2. Reconstruct canonical bytes, check `content_sha256`, verify the embedded
   SSHSIG with stock `ssh-keygen -Y verify`, require the out-of-band anchor to
   match the fetched trust-root key fingerprint, and refuse before persistent
   mutation on any failure.
3. Parse the signature-covered artifact manifest from `llms-install.md`.
4. Fetch `downloads/<current-release>/SHA256SUMS`, verify its signed-manifest
   hash, and fetch/hash-check every required wheel and the answers schema.
5. If CPython `>=3.14` is absent, fetch the manifest-pinned uv 0.11.21 tarball,
   hash-check it before extraction/execution, and run `uv python install 3.14`
   in user space.
6. Build a staging venv under
   `${CE_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}/creator-engine}/bootstrap`,
   install the validator offline from the verified wheelhouse, prove `ce
   --help`, and atomically promote or reuse the existing matching venv.
7. Execute:

   ```text
   <venv>/bin/ce install --spec <verified-spec> --trust-root <verified-trust-root> --trust-anchor <source>=<verified-trust-anchor> --answers-schema <verified-schema> --inventory
   ```

This is the E1 stopping point. The inventory output is the handoff artifact for
the later governed-seat path: prepare/confirm the host and GitHub answers, run
`ce onboard --plan`, have the operator review the plan, and only then run the
explicit governed `ce onboard --apply`.

The Pages mirror lives under `docs/downloads/<current-release>/`; the signed
spec manifest is authoritative for the concrete release path and hashes. Its
`SHA256SUMS` publishes the wheel hashes and the `install.sh` hash; the signed
spec pins the `SHA256SUMS` hash and the answers-schema hash.

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
- **Bootstrap-token VERIFICATION** (`bootstrap_scope_table` /
  `bootstrap_required_scopes`): the installer's one-time credential is
  *checked, not asked*, and the requirement is **right-sized to the operation**
  being performed. A **plain-join** (joining an already-CE repo) writes nothing with
  this PAT — every forge op rides the App's JIT scoped token and protection is
  verify-only — so the requirement is **identity-only** (a valid login distinct
  from the App bot). A **greenfield** create needs `contents:write ·
  administration:write · actions:write · workflows:write` (+ org repo-create iff
  new-in-org). **Both classic and fine-grained PATs are accepted**: a classic
  PAT is verified via its `X-OAuth-Scopes`; a fine-grained PAT (GitHub's
  recommended default) emits none and is not permission-introspectable, so its
  greenfield write-capability is enforced **fail-closed at the write legs**
  (each refuses on a 403) rather than at the probe. Unprobed / unknown-and-
  unverifiable = fail-closed. Never stored: runtime forge access is the App's
  JIT scoped token, never this one. For brownfield live apply, branch-protection
  reads require `administration:read`, but that permission is requested on the
  GitHub App installation token minted by the live driver; it is not a bootstrap
  PAT scope.
- **App plan** (`plan_github_app`): `shared` (the CE-published App — the
  solo-pilot default) vs `own` (`app_id` / `client_id` / PEM **SecretRef,
  tmpfs custody**); **click-or-detect** — the click is the contract's
  irreducibly interactive human-approval step on the FIRST run; a detected
  (or declared) `installation_id` SKIPS it on re-run, so the *converged*
  state is fully declarative. The installation MUST expose the target
  `github.repo` to the App token. An installation that lists zero accessible
  repositories is unusable, even when GitHub reports `repo_selection=all` on
  an account that does not contain the target repo; the operator must install
  or reconfigure the App on the account that owns the target repo, or select
  the target repo explicitly.
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
- **Forge author identity binding**: any local Git commit authored during
  install/apply binds `user.name` / `user.email` from the install-time
  forge identity resolved by `GET /user` with the install-configured bootstrap
  token, sets `user.useConfigOnly=true`, surfaces the resolved identity in leg
  evidence, and refuses if that identity is unresolved. Ambient host `git
  config` or `gh auth` state is never an accepted fallback.

`build_github_leg_plan` composes all of it from a *validated* answers
document plus one probe dict; `converged: true` is the terraform
empty-plan analog.

## Greenfield first project (E4)

New projects use the same onboard surface and the same answers inventory. When
`github.mode: new`, the schema emits greenfield `project.*` rows:
`project.name` (optional local directory name; absent means derive the repo
basename) and `project.scaffold.kind` (default `minimal`). These rows are
schema-derived and show up in `ce onboard --inventory`; there is no parallel
greenfield prompt list.

`ce onboard --plan` adds `first_project`, a pure E4 read model:

- `mode: greenfield`
- `project_root: <host.workspace_root>/<project name>`
- `scaffold_input.kind: minimal`
- `scaffold_input.supplied_to_e2_leg: workspace_checkout`
- `e2_plan_ref: onboard.github_leg`
- `e2_apply_required: true` until an E2 apply result is folded
- E4-owned Frame->Ship flags for first Scope, ratification, Build, PR, Review,
  and merge
- `first_ship_not_yet_counted: true` until a governed post-scaffold PR merges

This block does not restate E2's scaffold/repo/App/protection/Actions plan and
does not recompute E2 convergence counters. After `ce onboard --apply`, the CLI
folds the returned E2 summary into `first_project.e2_convergence` as a
read-through of E2 counts and leg verification facts.

The minimal scaffold is an input contract supplied to E2's
`workspace_checkout` leg: project root, `.gitignore` for CE/local transient
state, neutral `README.md`, configured default branch, and a bootstrap commit
only to create the branch and install checks. That bootstrap is onboarding
evidence, not first ship.

The first ship is the first post-scaffold governed PR from a real human-shaped
Scope: Frame chat -> Scope confirmation -> `ce ratify` -> `ce drive --spawn` ->
forge PR -> distinct review venue or ratified waiver -> gated merge ->
completion report. E2's deterministic `first_project_smoke` Scope remains
separate and never satisfies E4's `first_scope_filed` counter.

## Brownfield adoption (E3)

Existing projects use the same onboard surface and the same answers inventory.
`schemas/install-answers.schema.yaml` now carries 11 `brownfield.*` step-5 rows
for project root correction, CI preservation policy, detected test commands,
history mode, branch/commit convention guidance, and secrets-scrub waivers.
There is no second prompt inventory and no brownfield-specific executor.

`ce onboard --inventory` adds a value-free `brownfield` JSON block with observed
workflows, test commands, history summary, advisory conventions, scrub status,
and blockers. The CLI reads only source-controlled metadata and read-only Git
facts. It does not write files, run scanners, call GitHub mutations, or invoke
E2.

`ce onboard --plan` adds `brownfield_adoption` with a canonical
`inventory_sha256`, checks to preserve, CE checks to add, detected validation
commands, history and convention summaries, a scrub preflight plan, a first
Scope seed, project skill artifacts, and ordered E2 apply-step descriptors.
Required checks are additive: existing checks are preserved and the CE validate
check is added only when missing. Unknown test commands remain unknown; the
planner does not invent commands from an empty project.

The project skill artifacts planned for E2 to write are
`.ce/skills/project-conventions.md` and `.ce/skills/project-validation.md`.
Their contents are value-free: no raw secrets, scanner snippets, actor ids, or
absolute local paths. The first Scope seed references them through `skill_refs`
and binds to the inventory hash.

Brownfield apply is E2-owned. If the current E2 `onboard_apply` build has no
brownfield extension legs, `ce onboard --apply` refuses with
`e2_brownfield_seam_unavailable` and returns the plan payload. See
[`brownfield-adoption.md`](./brownfield-adoption.md).

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
is refused as `brownfield_deferred`; E3 owns brownfield inventory and planning,
and live brownfield adoption waits for E2 brownfield extension legs. SecretRefs
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

E1 implementation branches hold at the signing seam with `value:` and
`content_sha256:` placeholders after all code, docs, wheelhouse, and mirror
artifacts are otherwise green. The release file carries the real values only
after the Operator offline-key signing act.

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
(+ the published hash for `install.sh` in
`docs/downloads/<current-release>/SHA256SUMS`);
the cryptographically **verified** trust anchor for the install *procedure* is
this signed spec (§0), not the one-liner. `install.sh`'s own posture is stated,
not overstated — it asserts no signature over its own body beyond TLS + the
published hash, and E1 takes no privileged action.

## Dependency resolution — detect-don't-assume, fix-with-permission

`v3_installer.plan_dependencies` plans, never fail-on-missing: it **detects** each
of `git · python · runsc · proxy · uv` (a **read-only** probe — the CLI does it
live via `shutil.which`; the planner is pure), then for the missing ones plans a
**permission-gated, idempotent** install (`runsc`/`proxy`/`git`/`python` need
sudo, **batched** into a single ask; `uv` is user-space). Present tools are
skipped (idempotent); the operator may gracefully decline. E1 itself does not
perform the privileged fix; missing `runsc`/`proxy` surface as inventory facts.

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

The wheel installs both `ce` and `cev3`. E1 invokes the internal `cev3` by
absolute venv path for the authenticated bootstrap handoff, then creates or
repairs durable user-local shims:

- `~/.local/bin/cev3` → `<verified-venv>/bin/cev3`
- `~/.local/bin/ce` → `<verified-venv>/bin/ce`

The shim step is idempotent and never creates a system-wide symlink. It refuses
to overwrite a non-symlink at either user-local command path, updates stale
symlinks to the current verified venv, and warns when `~/.local/bin` is not on
`PATH` because the installer cannot permanently mutate the parent shell's
environment. `ce` remains the user-facing command; the `cev3` shim is retained
for bootstrap/internal compatibility. A future version-stamped user command
(`cev4`, etc.) remains the anti-pattern this avoids.

## Gate-daemon installer environment contract

`deploy/systemd/install-gate-daemons-systemd.sh` installs the gate daemon units
but never creates or overwrites the operator's env file. The env file is the
only handoff for deployment-specific credentials and daemon configuration:

- `CE_GATE_REPO` — repository slug (`owner/name`) for the daemon fleet.
- `CE_GATE_AUTHORIZED_REVIEWERS` — comma-separated reviewer seats whose reviews
  may authorize merge-queue enqueue.
- `CE_BELT_IDENTITY` — work-pickup belt identity.
- `GH_TOKEN` — integrator token for the merge-queue daemon.
- `CE_PICKUP_TOKEN` — static review/work pickup token fallback.
- `BAO_ADDR` — OpenBao endpoint for the review-pickup token supplier.
- `BAO_TOKEN` — OpenBao client token; evidence and docs carry only the env name.
- `BAO_CACERT` — optional OpenBao CA bundle path.
- `CE_OPENBAO_ALLOWED_REFS` — allowlist entry binding the permitted review-pickup
  SecretRef fields and policy digest.
- `CE_PICKUP_TOKEN_SECRET_BACKEND` — SecretIdentity backend key; the reviewed
  deployment path uses `openbao`.
- `CE_PICKUP_TOKEN_SECRET_MOUNT` — OpenBao KV mount for the review-pickup
  SecretRef.
- `CE_PICKUP_TOKEN_SECRET_PATH` — OpenBao secret path for the review-pickup
  SecretRef.
- `CE_PICKUP_TOKEN_SECRET_FIELD` — field inside the OpenBao secret payload.
- `CE_PICKUP_TOKEN_SECRET_PURPOSE` — SecretRef purpose, normally
  `review-pickup-token`.
- `CE_PICKUP_TOKEN_SECRET_OWNER_REF` — owner binding for the SecretRef.
- `CE_PICKUP_TOKEN_SECRET_REF_POLICY_SHA` — 64-hex policy digest for the
  SecretRef allowlist.
- `CE_PICKUP_TOKEN_SECRET_TARGET_REF` — `file:` materialization target read after
  OpenBao delivery.
- `CE_BELT_INTERVAL_SECONDS` — optional belt poll interval.
- `CE_BELT_LABELS` — optional single work-pickup label filter.

The OpenBao-backed review-pickup path is armed only when the env file carries
the OpenBao client variables, `CE_OPENBAO_ALLOWED_REFS`, and the full
`CE_PICKUP_TOKEN_SECRET_*` SecretRef set above. The installed unit remains on the
static `CE_PICKUP_TOKEN` command until the operator switches to the documented
OpenBao-ready `ExecStart` after live verification.

## Boundary (pure planner; live executor seam)

CI-pure: parser/canonicalization · artifact-manifest validation · dependency
planner · profile/opt-out · answers/inventory engine · decomposed GitHub-leg
planners · the `ce` exposure plan. Live E1 shell work is confined to
`docs/install.sh`: network fetches, hash checks, venv creation, user-local CLI
shim creation, and authenticated inventory. The E2 live executor remains the
composition seam for host/runtime/GitHub/workspace actions and verifies each leg
before proceeding.
The read-only *detection* remains live; the privileged *fix* is explicit
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
