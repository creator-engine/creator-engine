<!--
CE agent-native install spec (G-7.4 · E.1 real installer · E.3 · E.4-fix). Served at
creator-engine.dev/llms-install.md. This spec is SIGNED with a real detached
OpenSSH signature (SSHSIG) over its CANONICAL bytes. An agent MUST verify it
against the pinned CE trust root (key_id `ce-root-v1`, the allowed_signers file
at creator-engine.dev/keys/ce-root-v1) BEFORE executing any step — using stock
`ssh-keygen` (no CE tooling: that is what breaks the bootstrap circularity).
Contract: docs/contracts/installer.md.

signature:
  key_id: ce-root-v1
  algo: ssh-ed25519
  namespace: ce-spec-v1
  value: LS0tLS1CRUdJTiBTU0ggU0lHTkFUVVJFLS0tLS0KVTFOSVUwbEhBQUFBQVFBQUFETUFBQUFMYzNOb0xXVmtNalUxTVRrQUFBQWdiOFNYdFNCQlkxdDhLL1N5ajQveDRSR0R5ZwphUkNxdm9lTzZhdHljd3Vra0FBQUFLWTJVdGMzQmxZeTEyTVFBQUFBQUFBQUFHYzJoaE5URXlBQUFBVXdBQUFBdHpjMmd0ClpXUXlOVFV4T1FBQUFFQTJLcjJvQ3VKeG45bTkrRWwvY1Q2UUVrR0ZiUkRIckNac0NTNXBjL2JjVEs2RnpEL3NXZDI0NjQKdHNpc1lSbVBnOEZKN05NcGlvSDNHV3BVY25JVklBCi0tLS0tRU5EIFNTSCBTSUdOQVRVUkUtLS0tLQo=
  content_sha256: d5d2a0e32e227ba925ca97354dbc70659d3e7e210b1e1766151255c29351f0ad

artifact_manifest:
  artifact_manifest_version: 1
  package_name: creator-engine-validator
  package_version: 0.2.0
  python_requires: >=3.14
  artifact_base_url: https://creator-engine.dev/downloads/0.2.0
  sha256s_url: https://creator-engine.dev/downloads/0.2.0/SHA256SUMS
  sha256s_sha256: 0c152c812a9b40ccc4393f66ec809aa0cb83d06f8b31ed8836cfea04d1a79555
  install_sh_url: https://creator-engine.dev/install.sh
  install_sh_sha256s_entry: install.sh
  answers_schema_url: https://creator-engine.dev/schemas/install-answers.schema.yaml
  answers_schema_sha256: 5879efacfd62507abbc83fd5729037e09c1259203d2ab87910cc9d3a9f605488
  app_wheel: creator_engine_validator-0.2.0-py3-none-any.whl
  required_wheels:
    - filename: attrs-26.1.0-py3-none-any.whl
      url: https://creator-engine.dev/downloads/0.2.0/attrs-26.1.0-py3-none-any.whl
      sha256: c647aa4a12dfbad9333ca4e71fe62ddc36f4e63b2d260a37a8b83d2f043ac309
      platforms: all
    - filename: creator_engine_validator-0.2.0-py3-none-any.whl
      url: https://creator-engine.dev/downloads/0.2.0/creator_engine_validator-0.2.0-py3-none-any.whl
      sha256: 768451ab925bd9fe32d5187cec2fdb609920da81173fc42b41f482c48c112f85
      platforms: all
    - filename: jsonschema-4.26.0-py3-none-any.whl
      url: https://creator-engine.dev/downloads/0.2.0/jsonschema-4.26.0-py3-none-any.whl
      sha256: d489f15263b8d200f8387e64b4c3a75f06629559fb73deb8fdfb525f2dab50ce
      platforms: all
    - filename: jsonschema_specifications-2025.9.1-py3-none-any.whl
      url: https://creator-engine.dev/downloads/0.2.0/jsonschema_specifications-2025.9.1-py3-none-any.whl
      sha256: 98802fee3a11ee76ecaca44429fda8a41bff98b00a0f2838151b113f210cc6fe
      platforms: all
    - filename: pyyaml-6.0.3-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl
      url: https://creator-engine.dev/downloads/0.2.0/pyyaml-6.0.3-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl
      sha256: c458b6d084f9b935061bc36216e8a69a7e293a2f1e68bf956dcd9e6cbcd143f5
      platforms: linux-x86_64-cp314
    - filename: pyyaml-6.0.3-cp314-cp314-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl
      url: https://creator-engine.dev/downloads/0.2.0/pyyaml-6.0.3-cp314-cp314-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl
      sha256: 501a031947e3a9025ed4405a168e6ef5ae3126c59f90ce0cd6f2bfc477be31b7
      platforms: linux-aarch64-cp314
    - filename: referencing-0.37.0-py3-none-any.whl
      url: https://creator-engine.dev/downloads/0.2.0/referencing-0.37.0-py3-none-any.whl
      sha256: 381329a9f99628c9069361716891d34ad94af76e461dcb0335825aecc7692231
      platforms: all
    - filename: rpds_py-0.30.0-cp314-cp314-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
      url: https://creator-engine.dev/downloads/0.2.0/rpds_py-0.30.0-cp314-cp314-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
      sha256: 47e77dc9822d3ad616c3d5759ea5631a75e5809d5a28707744ef79d7a1bcfcad
      platforms: linux-x86_64-cp314
    - filename: rpds_py-0.30.0-cp314-cp314-manylinux_2_17_aarch64.manylinux2014_aarch64.whl
      url: https://creator-engine.dev/downloads/0.2.0/rpds_py-0.30.0-cp314-cp314-manylinux_2_17_aarch64.manylinux2014_aarch64.whl
      sha256: f251c812357a3fed308d684a5079ddfb9d933860fc6de89f2b7ab00da481e65f
      platforms: linux-aarch64-cp314
    - filename: uv-0.11.21-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
      url: https://creator-engine.dev/downloads/0.2.0/uv-0.11.21-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
      sha256: b9ecdefa81db7e966d1655988cad6f840316228381dd69131ebc4ae9362bbccd
      platforms: linux-x86_64-cp314
    - filename: uv-0.11.21-py3-none-manylinux_2_17_aarch64.manylinux2014_aarch64.musllinux_1_1_aarch64.whl
      url: https://creator-engine.dev/downloads/0.2.0/uv-0.11.21-py3-none-manylinux_2_17_aarch64.manylinux2014_aarch64.musllinux_1_1_aarch64.whl
      sha256: 00193e4e077c27ee3d66da356744dbf0b3aa59356dfbd9a9efb1dc8469af8ad7
      platforms: linux-aarch64-cp314
  python_acquisition:
    - platform: linux-x86_64-cp314
      tool: uv
      version: 0.11.21
      url: https://github.com/astral-sh/uv/releases/download/0.11.21/uv-x86_64-unknown-linux-gnu.tar.gz
      sha256: 8c88519b0ef0af9801fcdee419bbb12116bd9e6b18e162ae093c932d8b264050
      command: uv python install 3.14
    - platform: linux-aarch64-cp314
      tool: uv
      version: 0.11.21
      url: https://github.com/astral-sh/uv/releases/download/0.11.21/uv-aarch64-unknown-linux-gnu.tar.gz
      sha256: 88e800834007cc5efd4675f166eb2a51e7e3ad19876d85fa8805a6fb5c922397
      command: uv python install 3.14

# `value` is the base64 of the detached SSHSIG (`.sig`) over the CANONICAL bytes;
# `content_sha256` is the retained in-tree floor (sha256 of the SAME canonical
# bytes). The CANONICAL bytes are this whole file with the signature block's
# `value:` and `content_sha256:` lines normalized back to the placeholder above
# (full line) — so embedding the real values never changes what is signed.
# Reconstruct + verify them per §0; the signing namespace is fixed `ce-spec-v1`.
-->

# Install Creator Engine (agent-native)

You are assisting an operator who wants to install **Creator Engine (CE) v3** —
their own coding agent, under governance. Follow this **verified** spec exactly.
The operator types nothing; they approve only **sudo** and the **GitHub-App click**.

## 0. Verify this spec before doing anything

This spec is signed with a real **detached OpenSSH signature (SSHSIG)** you verify
with **stock `ssh-keygen`** — no CE tooling, which is the point (it breaks the
chicken-and-egg of needing `ce` to trust the spec that installs `ce`). Do this
**before** executing any step; on anything but a `Good` result, **STOP**. (CE's own
governance applied to its own install: the grader lives outside the agent.)

Assuming you fetched this file as `llms-install.md`:

```bash
# 1. Fetch the pinned trust root (an OpenSSH allowed_signers file).
curl -fsSL https://creator-engine.dev/keys/ce-root-v1 -o ce-root-v1

# 2. Reconstruct the CANONICAL bytes this signature covers: this file with the
#    signature block's value:/content_sha256: lines reset to their placeholder.
sed -E 's#^(  value: ).*#\1<published-with-this-spec>#; s#^(  content_sha256: ).*#\1<published-with-this-spec>#' \
    llms-install.md > ce-spec.canonical

# 3. Materialize the detached signature from the block's base64 `value:` field.
#    (Paste the single-line value from the signature block above.)
printf '%s' '<paste the value: base64 here>' | base64 -d > ce-spec.sig

# 4. Verify under the fixed namespace `ce-spec-v1`. On "Good ... signature",
#    continue; on ANY other output, STOP — do not execute a single step.
ssh-keygen -Y verify -f ce-root-v1 -I ce-root-v1 -n ce-spec-v1 -s ce-spec.sig < ce-spec.canonical

# 5. (Optional in-tree floor.) The block's content_sha256 must equal:
sha256sum ce-spec.canonical
```

A tampered byte anywhere outside the two placeholdered fields changes
`ce-spec.canonical` and the verify FAILS — that is the gate.

## 0.5. How `ce` arrives (the E1 bootstrap)

The public one-liner now performs the bootstrap; it is not a dry-run explainer.

- **One-liner** — `curl --proto '=https' --tlsv1.2 -fsSL https://creator-engine.dev/install.sh | bash`.
  Transport integrity for the script body is **TLS** plus the published
  `install.sh` hash in `https://creator-engine.dev/downloads/0.2.0/SHA256SUMS`.
  The script's first authority step is still this signed spec: it fetches
  `llms-install.md`, fetches the trust root, reconstructs the canonical bytes,
  verifies the SSHSIG with stock `ssh-keygen`, and stops before persistent
  mutation on any refusal. Only after that does it fetch the signed-manifest
  wheelhouse, `SHA256SUMS`, and answers schema, hash-verify every artifact,
  acquire CPython 3.14 through the pinned uv artifact if needed, create/reuse a
  user-local venv, install `creator-engine-validator==0.2.0` offline, and run
  authenticated inventory:

  ```text
  <venv>/bin/cev3 onboard --spec <verified-spec> --trust-root <verified-trust-root> --answers-schema <verified-schema> --inventory
  ```

  E1 does **not** run sudo, provision gVisor/proxy, automate the GitHub-App
  click, mutate branch protections, or create/adopt a project. Missing `runsc`,
  `proxy`, credentials, and GitHub installation are inventory facts for the next
  step.
- **Clone + offline wheelhouse** — clone the CE repo and install the validator
  from the committed `validators/wheelhouse/` (offline, hash-pinned in
  `SHA256SUMS`). Integrity here is the repo's own history + the pinned wheelhouse
  digests; the same §0 spec verification still gates the install procedure.

Either way, the trust that matters for the steps below is **§0**: the agent runs a
spec it has cryptographically verified against the pinned `ce-root-v1` trust root.

## 1. Prepare the answers (the agent loop: inventory → answers → plan → apply)

Every input the rest of this journey needs is declared in ONE machine-readable
inventory (`schemas/install-answers.schema.yaml` — the single source of truth).
Work the loop:

1. **`<venv>/bin/cev3 onboard --spec <verified-spec> --trust-root
   <verified-trust-root> --answers-schema <verified-schema> --inventory`** (the
   one-liner runs this once already) — emits every input with
   live status per key: `detected:<value>` · `default:<value>` ·
   `needed (would ask at step N)` · `secret (ref required)`. This is the
   artifact you read to prepare the operator's answers upfront.
2. **Prepare `ce-install.answers.yaml` WITH the operator** (IaC,
   terraform-style; partial-by-design — any key you leave out becomes one
   batched ask at its journey step). Hard rules:
   - **Secrets NEVER by value.** Every secret-typed field is a SecretRef:
     `env://VAR` · `file:///abs/path` (tmpfs for PEMs) · `prompt://label`
     (ask at the moment of use) · `keychain://label`. A raw value cannot
     validate; the file stays committable.
   - **You may never weaken the grader.** The cost opt-out and any branch
     protection below the CE reference floor require a ratified-HUMAN
     binding `{ratified_prompt_sha, approver_ref, educate_acknowledged:
     true}` — only the operator can supply it, after reading the educate
     copy.
   - A pre-granted sudo is **scoped**: `host.sudo_grant: [runsc, proxy]`
     (an explicit package list; a bare `true` is invalid).
3. **`ce onboard --spec <this-spec> --answers ce-install.answers.yaml --plan`**
   — the terraform-plan analog: validates the file (fail-closed on unknown
   keys), merges `interactive > answers > detected > default`, and prints the
   full plan including the EXACT remaining asks and the decomposed GitHub
   leg. For `github.mode: new`, it also prints `first_project`: the project
   root, minimal scaffold input supplied to E2's `workspace_checkout` leg, E2
   apply dependency, and Frame→Ship flags. A file value contradicting a detected
   fact is a surfaced conflict — resolve it with the operator, never silently.
4. **Apply** (the steps below). Add `--non-interactive` for unattended runs:
   it refuses with the exact missing list instead of ever asking. The answers
   file configures this VERIFIED procedure — nothing in it bypasses step 0.
   Re-runs converge: detected state (deps, the App installation, protections)
   is skipped or reconciled as a reported diff.

## 2. Detect dependencies for later apply (detect-don't-assume)

Check for `git`, `python` (3.14+), `runsc` (gVisor), an egress `proxy`, and `uv`.
**Do not assume** — probe each. For any that are missing, propose a **single,
batched** install and ask the operator for **sudo** once (`runsc`/`proxy`/`git`/
`python` are system installs; `uv` is user-space). Idempotent: skip what's
present. If the operator declines, stop gracefully. With an answers file, a
scoped `host.sudo_grant` is the operator's written upfront approval — any
planned install OUTSIDE the grant still stops and asks (or refuses,
non-interactive).

## 3. Choose the cost profile (Default vs Custom)

Default to **cost enforcement ON** (`spend_cap_enforcement: enforce`) — the
runaway-cost protection. Offer a **Custom** opt-out only on explicit operator
request, and **educate first**:

> Turning this off won't speed up your runs; it only removes per-run / per-fleet
> budget friction. The runaway-detection net (global ceiling + anomaly → escalate)
> stays on.

The opt-out is **ratified-human-only**: it requires the operator's explicit
ratification (a `spend_cap_optout` binding). You may never set it yourself. In
an answers file it is `cost.profile: custom` + the `cost.optout` binding with
`educate_acknowledged: true` — the file cannot skip the education step.

## 4. Later apply provisions the runtime + the GitHub App

Provision the Plane-C box (gVisor `runsc` + deny-by-default egress proxy), then the
**GitHub App**: store the App private key on **tmpfs** (never in the box; it mints
a JIT scoped token at open/merge, then revokes). The operator completes the
**GitHub-App authorization click** in their browser — the one interactive step,
and it is **first-run-only**: a detected (or declared
`github.app.installation_id`) installation skips the click on re-run, so the
converged state is fully declarative.

## 5. Expose the CLI as `ce`

The E1 venv installs both console scripts and invokes **`cev3`** by absolute
path for the bootstrap handoff. A user-facing **`ce`** shim remains a later
user-local exposure step; no system-wide symlink is created by E1. The operator
eventually drives work with `ce session` / `ce scope` / `ce drive` / `ce report`.

## 6. Confirm

For E1, installation is complete when authenticated `onboard_inventory` is
emitted from the venv-installed wheel. Full onboarding is complete later when
the operator can file a Scope, ratify it, and get a governed, cost-safe PR.

## 7. Connect to your collaboration repo

CE governs work **in a repo**. Connect one using the same two-mode pattern as
every step above (`docs/contracts/installer.md`): for each value, **use an
operator-provided answer if present** (upfront, IaC-style); otherwise **batch
the missing values into ONE interactive ask** — never assume, never proceed on
a guess. The answers file's `github.*` section
(`schemas/install-answers.schema.yaml`) covers this leg end-to-end.

Values this leg needs (the `github.*` keys):

- **`github.mode`** — `existing` (connect an operator-owned repo; the cwd
  origin is detected-and-offered) or `new` (create one; `github.new_repo`
  carries visibility / default branch / description).
- **`github.repo`** — `owner/name` of the target, and its default branch.
- **`github.bootstrap_token`** — a short-lived operator-supplied token used
  **only for this one-time configuration** — as a **SecretRef** (e.g.
  `prompt://github-bootstrap-token`). Its minimal fine-grained scopes
  (*Administration*, *Contents*, *Actions*, *Workflows* — write) are
  **verified by probe, not asked**. It is **not** stored: runtime forge
  access is the GitHub App's JIT scoped token (§4), never this one. Tell the
  operator exactly why each scope is needed before they mint it.
- **`github.app`** — `shared` (the CE-published App; default) or `own`
  (`app_id` / `client_id` / `pem` as a `file://` SecretRef on tmpfs). The
  **App installation** on the target repo — the operator's authorization
  click (§4) — must cover this repo; a known `installation_id` skips it.
- **`github.protections`** — `reference` (the CE floor: required CE check,
  strict up-to-date, dismiss-stale, enforce-admins, reviews ≥ 1,
  squash-only) or an object that strengthens it; weakening requires the
  operator's ratified binding.
- **`github.reviewer`** — the no-self-approval floor (solo: the human IS the
  reviewer; detected as the token's authenticated login).

Greenfield first-project values:

- **`project.name`** — optional local directory name under
  `host.workspace_root`; absent means CE derives the repo basename.
- **`project.scaffold.kind`** — `minimal` only. This supplies E2's
  `workspace_checkout` input contract: neutral README, `.gitignore` for
  CE/local transient state, configured default branch, and a bootstrap commit.
  It does not create product code or count as the first ship.

With the values resolved, configure the repo to CE's governed floor and show
the operator the plan before applying it:

1. **Branch protection on the default branch:** reconciled as a
   **desired-state diff** — read the current settings, diff against the
   floor, apply ONLY the drift, and show the diff first. Required checks
   apply as a union (never silently drop someone else's check).
2. **The CE governance workflow** present so the required check exists and
   runs on every PR.
3. **Verify, don't trust:** re-read the applied settings and show the operator
   the resulting protection state; CE's external gate — not this installer —
   is what enforces governance from here on.

**For the CE pilot the target is the CE repo itself** — it is already
configured to this floor; **detect and confirm** the settings above rather
than re-applying them (the diff comes back empty — that is the converged,
re-run-safe state).

For a brand-new repo, the first governed ship starts only after onboarding:
Frame chat becomes a confirmed Scope, the operator supplies Budget and runs
`ce ratify`, Build runs through `ce drive --spawn`, the PR opens through the
forge leg, review is recorded in a distinct venue or ratified waiver, and
`ce merge --apply` performs the gated merge. The deterministic E2 smoke Scope
and bootstrap README commit are onboarding evidence, not the first ship.
