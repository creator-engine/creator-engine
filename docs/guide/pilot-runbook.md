# Creator Engine — Pilot Runbook (v3.1 pilot-ready)

*The end-to-end pilot onboarding path: install CE, provision a repo + the GitHub
App, file work as a Scope, and get governed, cost-safe PRs + merges — all under
the branded `ce session` frame, on your own agent. Plain-language intro:
[`understanding-ce.md`](./understanding-ce.md). The mechanics live in the cited
contracts/designs.*

> **Pilot scope.** This runbook is the operator path for the **CI-pure** product
> surface. The **live install drive** (the privileged `curl|bash` / backend
> provisioning) and the **interactive GitHub-App click** are the first-pilot live
> seams — they are the only steps that touch your machine + your GitHub account,
> and you (the human) approve them explicitly.

## 0. What you need

- A coding agent you already use (Claude Code or Codex) — CE governs *your* agent.
- A greenfield (or existing) GitHub repository you want CE to drive work on.
- Permission to install dependencies (sudo) and to authorize a GitHub App.

## 1. Install (one engine, two modes — operator-typeless)

You type nothing during setup; you approve only **sudo** (privileged dependency
installs) and the **GitHub-App authorization click**. Contract:
[`../contracts/installer.md`](../contracts/installer.md).

- **One-liner** — `curl -fsSL https://creator-engine.dev/install.sh | bash`. It
  detects dependencies (`git · python · runsc · proxy · uv`), proposes a single
  batched sudo install for whatever is missing (idempotent; decline gracefully),
  and hands off to the verified onboard.
- **Agent-native** — point your agent at `https://creator-engine.dev/llms-install.md`.
  Your agent fetches the **signed** install spec, **verifies it against the pinned
  CE public key before executing**, and assists the GitHub-App step.

Both modes are the SAME journey; the only difference is *where answers come
from* (`interactive > answers-file > detected > default`). You can prepare
every answer **upfront, IaC-style**, in a committable
`ce-install.answers.yaml` (schema:
[`../../schemas/install-answers.schema.yaml`](../../schemas/install-answers.schema.yaml)) —
or answer interactively as each journey step batches its asks. The agent loop:

```
ce onboard --spec llms-install.md --inventory          # every input + live status
# prepare ce-install.answers.yaml (secrets ONLY as env:// file:// prompt:// refs;
# sudo pre-granted only as a scoped list, e.g. host.sudo_grant: [runsc, proxy])
ce onboard --spec llms-install.md --answers ce-install.answers.yaml --plan
ce onboard --spec llms-install.md --answers ce-install.answers.yaml --apply --non-interactive
```

`--plan` shows the full plan plus the *exact remaining asks*;
`--apply --non-interactive` is fail-closed — it refuses with that list instead
of ever asking (unattended/VPS runs). The one-liner passes a file through too:
`CE_ANSWERS=ce-install.answers.yaml curl … | bash` (or
`bash -s -- --answers <file>`). An answers value can configure anything
**except a weaker grader** — weakening (the cost opt-out, protections below
the CE floor) requires your explicit ratified binding, educate-first.

The installer exposes the CE CLI as **`ce`** (this is a v3-only install — there is
no v1 to collide with). Preview the plan first with a dry-run:

```
ce onboard --spec llms-install.md --sig-value <published>
```

### Cost safety (the #1 pilot question)

Cost-runaway protection is **on by default** (`spend_cap_enforcement: enforce`).
You may opt out of the per-run / per-fleet **budget caps** only with an explicit,
ratified choice — and CE educates you first:

> Turning this off won't speed up your runs; it only removes per-run / per-fleet
> budget friction. The runaway-detection net (global ceiling + anomaly → escalate)
> stays on.

So even opted-out, you are never blind — see
[`../contracts/spend-envelope.md`](../contracts/spend-envelope.md).

## 2. Provision the repo + the GitHub App

The installer provisions the Plane-C runtime box (gVisor `runsc` + a deny-by-default
egress proxy) and the **GitHub App** (its private key lives on tmpfs and mints a
JIT scoped token only at open/merge, then revokes — never in the box). You complete
the **GitHub-App authorization click** in your browser. CE opens and merges as the
**App bot identity** (≠ you), so on a solo repo **you are the reviewer** and
no-self-approval holds.

The GitHub leg is fully decomposed and **re-run convergent**:

- The **click is first-run-only** — a detected (or declared
  `github.app.installation_id`) installation skips it; the converged state is
  fully declarative.
- Your one-time **bootstrap token** enters only as a SecretRef
  (`prompt://github-bootstrap-token` asks at the moment of use); its minimal
  scopes are *verified by probe, not asked*, and it is never stored.
- **Branch protections reconcile as a desired-state diff** against the CE
  reference floor (required CE check · strict up-to-date · dismiss-stale ·
  enforce-admins · reviews ≥ 1 · squash-only): read current → diff → apply
  ONLY the drift, shown to you first. Same answers, second run → empty plan.

For an existing repo, `ce onboard --inventory` and `--plan` also report
`brownfield` / `brownfield_adoption`: workflows and checks to preserve, detected
test commands, Git history posture, branch/commit conventions, scrub preflight,
project skill artifacts, and a first Scope seed. These paths are read-only until
E2's `onboard_apply` brownfield extension legs perform the writes; a build
without those legs refuses apply with `e2_brownfield_seam_unavailable`.

## 3. Drive work as a Scope (Frame → Shape → Build → Review → Ship)

Launch the session frame:

```
ce session
◆ Creator Engine · governed session · repo <owner/repo> · transport cc-hooks · backend gvisor · state .ce/state
◆ CE · Frame 0 · Shape 0 · Build 0 · Review 0 · Ship 0  │  ctx 8%  │  spend —
```

The status line shows your **stage** (the canon Frame→Shape→Build→Review→Ship over
the conserved machine), plus a **unified context + spend meter** with a
boundary-aware checkpoint/`/clear` nudge. Vocabulary canon:
[`../architecture/stage-vocabulary.md`](../architecture/stage-vocabulary.md).

1. **Frame** — just chat with your agent about what you want. Nothing is tracked.
2. **Shape** — when a concrete change emerges, CE offers to crystallize it into a
   **Scope** (the chat→Scope detect-and-offer; cheap, inline, cancel-safe). The
   Scope card fills in the canon labels — **Goal · Done-when · Budget ·
   Change-type · Ready**. You set the **Budget** (your call); the agent drafts the
   rest and may make a change *safer* on its own but only *you* can make it
   riskier. Shaping design: [`../architecture/shaping-ux.md`](../architecture/shaping-ux.md).
   When the card reads **Ready ✓**, place the bet: `ce ratify <scope>`.
3. **Build** — `ce drive <scope>` dispatches one governed, boxed run (the front
   gate refuses unless Ready + ratified; the appetite becomes the run's spend cap).
4. **Review** — read the **◆ CE Completion Report**: `ce report <scope>`:

```
┌─ ◆ CE COMPLETION REPORT · run r-91a · Scope cs-4f2 ──────────────────
│ Outcome   PR opened → #7
│ Verdict   Done-when 3/3 met · tests green · in scope ✓ · 14% of Budget S
│ Next      → Review PR #7  (Change-type code → your approval)
│ Inspect   gh pr view 7   |   ce show cs-4f2   |   ce artifacts r-91a
└──────────────────────────────────────────────────────────
```

   You judge **artifacts** (the PR, the manifest-scoped diff, the evidence) — not a
   transcript. The grader lives outside the agent.
5. **Ship** — approve and merge the PR (the back gate is `mutation_class`-tiered;
   branch protection enforces independent review). `Ship` is plural — a merged PR,
   delivered research, or a ratified "no change."

## 4. Inspect anything

`ce artifacts <run>` and `ce show <scope>` enumerate every artifact (PR · Scope ·
ratification · closed manifest · evidence-chain · spend) with its inspect command.
For the plain-language tour, run `ce guide`.

## 5. Greenfield-OSS quickstart

For a fresh open-source repo: create the repo, run the installer pointed at it,
authorize the App, then `ce session` → file your first Scope (e.g. "set up CI") →
ratify → drive → review → merge. From there, every change is a governed,
cost-safe, evidence-backed Scope.

## Deferred (the first live pilot exercises these)

The live install drive (privileged execution + backend provisioning) · the
interactive GitHub-App click · the live status-line tap · the live run dispatch.
These are the human-gated live seams the CI-pure surface is built to drive.

## Companions

[`understanding-ce.md`](./understanding-ce.md) ·
[`../architecture/pilot-uiux-model.md`](../architecture/pilot-uiux-model.md) ·
[`../architecture/pilot-deployment-transport.md`](../architecture/pilot-deployment-transport.md) ·
[`../contracts/installer.md`](../contracts/installer.md) ·
[`../contracts/scope.md`](../contracts/scope.md) · [`../v3-roadmap.md`](../v3-roadmap.md).
