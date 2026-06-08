# Contract: Two-mode installer + the cost opt-out (G-7.4)

**Status:** Canonical. The CI-pure decision substrate is
`creator_engine_validator/v3_installer.py`; the served artifacts are
`docs/install/install.sh` (the one-liner) and `docs/install/llms-install.md` (the
agent-native signed spec). The opt-out wires the G-5 fields validated by
`ce_spend_envelope`.

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
the `ce` exposure plan · `cev3 onboard` dry-run. **Deferred live seams:** the
actual `curl|bash` / privileged execution · the runtime backend provisioning
(gVisor + egress proxy) · the **interactive GitHub-App authorization click** · the
live transport probe. The read-only dependency *detection* is live; the privileged
*fix* is deferred.

## Standing requirements honored

- **G-4.1 naming hygiene:** `v3_installer` is v3-classified + residue-clean; pure;
  no `.hermes/`/`.claude/` state. **v1↔v3 coexistence:** additive; **v1 deleted =
  ∅** (the internal `cev3` console_script from G-7.0 is unchanged). **version
  boundary:** `v3_installer` imports stdlib only; `v3_cli`→`v3_installer` is
  v3→v3; no `shared→v3` edge.
- **G-5:** the opt-out fragment feeds `ce_spend_envelope` unchanged.

See also: `docs/architecture/pilot-deployment-transport.md`,
`docs/contracts/spend-envelope.md`, `docs/install/llms-install.md`,
`docs/install/install.sh`.
