# Contract: Two-mode installer + the cost opt-out (G-7.4 · E.3)

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

## Boundary (CI-pure; deferred live seams)

CI-pure: verify-before-execute · the dependency planner · the profile/opt-out ·
the answers/inventory engine (validation, precedence merge, missing list,
sudo-grant diff) · the decomposed GitHub-leg planners · the `ce` exposure plan ·
`cev3 onboard` dry-run. **Deferred live seams:** the actual `curl|bash` /
privileged execution · the runtime backend provisioning (gVisor + egress proxy) ·
the **interactive GitHub-App authorization click** (first run only — re-runs
detect the installation) · the live forge API mutations (repo create · App
install · protection PUT · workflow commit — the HTTPS-Bearer App-JWT mint leg) ·
the live transport probe. The read-only *detection* (dependency probe; the
GitHub probes injected into the planners) is live; the privileged *fix* is
deferred.

## Standing requirements honored

- **G-4.1 naming hygiene:** `v3_installer` is v3-classified + residue-clean; pure;
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
`docs/install.sh`, `schemas/install-answers.schema.yaml`.
