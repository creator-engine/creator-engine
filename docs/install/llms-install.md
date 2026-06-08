<!--
CE agent-native install spec (G-7.4). Served at creator-engine.dev/llms-install.md.
This spec is SIGNED. An agent MUST verify it against the pinned CE public key
(key_id `ce-root-v1`, published at creator-engine.dev/keys/ce-root-v1) BEFORE
executing any step — `creator_engine_validator.v3_installer.require_verified`
refuses an unverified or tampered spec. Contract: docs/contracts/installer.md.

signature:
  key_id: ce-root-v1
  algo: sha256-content   # in-tree floor; the asymmetric verify uses the published key
  value: <published-with-this-spec>   # the content digest / detached signature
-->

# Install Creator Engine (agent-native)

You are assisting an operator who wants to install **Creator Engine (CE) v3** —
their own coding agent, under governance. Follow this **verified** spec exactly.
The operator types nothing; they approve only **sudo** and the **GitHub-App click**.

## 0. Verify this spec before doing anything

Verify this spec's signature against the pinned CE public key `ce-root-v1`. If it
does not verify, **STOP** — do not execute any step. (CE's own governance applied
to its own install: the grader lives outside the agent.)

## 1. Detect dependencies (detect-don't-assume)

Check for `git`, `python` (3.14+), `runsc` (gVisor), an egress `proxy`, and `uv`.
**Do not assume** — probe each. For any that are missing, propose a **single,
batched** install and ask the operator for **sudo** once (`runsc`/`proxy`/`git`/
`python` are system installs; `uv` is user-space). Idempotent: skip what's
present. If the operator declines, stop gracefully.

## 2. Choose the cost profile (Default vs Custom)

Default to **cost enforcement ON** (`spend_cap_enforcement: enforce`) — the
runaway-cost protection. Offer a **Custom** opt-out only on explicit operator
request, and **educate first**:

> Turning this off won't speed up your runs; it only removes per-run / per-fleet
> budget friction. The runaway-detection net (global ceiling + anomaly → escalate)
> stays on.

The opt-out is **ratified-human-only**: it requires the operator's explicit
ratification (a `spend_cap_optout` binding). You may never set it yourself.

## 3. Provision the runtime + the GitHub App

Provision the Plane-C box (gVisor `runsc` + deny-by-default egress proxy), then the
**GitHub App**: store the App private key on **tmpfs** (never in the box; it mints
a JIT scoped token at open/merge, then revokes). The operator completes the
**GitHub-App authorization click** in their browser — the one interactive step.

## 4. Expose the CLI as `ce`

This is a v3-only install, so expose the CE CLI as **`ce`** (the user-facing
command). The operator drives work with `ce session` / `ce scope` / `ce drive` /
`ce report`.

## 5. Confirm

Run `ce session` to show the governed session frame. Installation is complete when
the operator can file a Scope, ratify it, and get a governed, cost-safe PR.
