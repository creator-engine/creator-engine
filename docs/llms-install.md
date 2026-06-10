<!--
CE agent-native install spec (G-7.4 · E.3 · E.4-fix). Served at
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
  value: LS0tLS1CRUdJTiBTU0ggU0lHTkFUVVJFLS0tLS0KVTFOSVUwbEhBQUFBQVFBQUFETUFBQUFMYzNOb0xXVmtNalUxTVRrQUFBQWdiOFNYdFNCQlkxdDhLL1N5ajQveDRSR0R5ZwphUkNxdm9lTzZhdHljd3Vra0FBQUFLWTJVdGMzQmxZeTEyTVFBQUFBQUFBQUFHYzJoaE5URXlBQUFBVXdBQUFBdHpjMmd0ClpXUXlOVFV4T1FBQUFFQmd1b0lnakRDRWxxVjI2aXJOdUVtcXAyZEUxN3FzUmdrRmFCU2JlemZpL1NzM3BJNnk0dHg3VW4KenQzRzZ5QUg4clYvckhheVZBRks2SzB4V3hxQzRMCi0tLS0tRU5EIFNTSCBTSUdOQVRVUkUtLS0tLQo=
  content_sha256: a93c9c8977d3cb3c2d70727dbc1bfd50485e9f029590e0fe375d6ed0851470d6

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

## 0.5. How `ce` arrives (the bootstrap)

The steps below invoke `ce onboard`. `ce` itself is acquired by ONE of these
supported paths — pick one, then return here:

- **One-liner** — `curl -fsSL https://creator-engine.dev/install.sh | bash`.
  Transport integrity is **TLS** (the host certificate); the bootstrap then hands
  off to *this* signed, verify-before-execute spec, which is the real
  procedure trust-anchor. `install.sh` is itself served + hash-published, and is
  deliberately conservative — it performs **no** privileged or destructive action
  without an explicit, batched **sudo** approval (detect-don't-assume). It does
  **not** itself assert a cryptographic signature over its own body beyond TLS +
  the published hash; treat §0's spec verification (not the one-liner) as the
  authenticity gate for everything that follows.
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

1. **`ce onboard --spec <this-spec> --inventory`** (you have `ce` from §0.5) —
   emits every input with
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
   leg. A file value contradicting a detected fact is a surfaced conflict —
   resolve it with the operator, never silently.
4. **Apply** (the steps below). Add `--non-interactive` for unattended runs:
   it refuses with the exact missing list instead of ever asking. The answers
   file configures this VERIFIED procedure — nothing in it bypasses step 0.
   Re-runs converge: detected state (deps, the App installation, protections)
   is skipped or reconciled as a reported diff.

## 2. Detect dependencies (detect-don't-assume)

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

## 4. Provision the runtime + the GitHub App

Provision the Plane-C box (gVisor `runsc` + deny-by-default egress proxy), then the
**GitHub App**: store the App private key on **tmpfs** (never in the box; it mints
a JIT scoped token at open/merge, then revokes). The operator completes the
**GitHub-App authorization click** in their browser — the one interactive step,
and it is **first-run-only**: a detected (or declared
`github.app.installation_id`) installation skips the click on re-run, so the
converged state is fully declarative.

## 5. Expose the CLI as `ce`

This is a v3-only install, so expose the CE CLI as **`ce`** (the user-facing
command). The operator drives work with `ce session` / `ce scope` / `ce drive` /
`ce report`.

## 6. Confirm

Run `ce session` to show the governed session frame. Installation is complete when
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
