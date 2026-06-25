# Creator Engine — Pilot Runbook (v3.1 pilot-ready)

*The end-to-end pilot onboarding path: install CE, provision a repo + the GitHub
App, file work as a Scope, and get governed, cost-safe PRs + merges — all under
the branded `cev3 session` frame, on your own agent. Plain-language intro:
[`understanding-ce.md`](./understanding-ce.md). The mechanics live in the cited
contracts/designs. For the shortest command sequence, see
[`zero-to-governed-seat-quickstart.md`](./zero-to-governed-seat-quickstart.md).*

> **Pilot scope.** The E1 one-liner now performs a real authenticated inventory
> bootstrap: it verifies the signed spec, installs CE into a user-local venv from
> hash-pinned artifacts, and runs `onboard --inventory`. Runtime provisioning and
> the interactive GitHub-App click remain later human-approved apply seams.

## 0. What you need

- A coding agent you already use (Claude Code or Codex) — CE governs *your* agent.
- A greenfield (or existing) GitHub repository you want CE to drive work on.
- Permission to install dependencies (sudo) and to authorize a GitHub App.

## 1. Install (one engine, two modes — operator-typeless)

You type nothing during setup; you approve only **sudo** (privileged dependency
installs) and the **GitHub-App authorization click**. Contract:
[`../contracts/installer.md`](../contracts/installer.md).

- **One-liner** — `curl --proto '=https' --tlsv1.2 -fsSL https://creator-engine.dev/install.sh | bash`.
  It fetches the signed spec and trust root, verifies the SSHSIG before any
  persistent mutation, fetches the Pages mirror wheelhouse and answers schema
  from signed-manifest-pinned hashes, creates/reuses a user-local venv, and runs
  authenticated `onboard --inventory`. It does not run sudo, provision the
  runtime, mutate GitHub, or create/adopt a project.
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
# the one-liner runs this once with verified absolute paths:
<venv>/bin/cev3 onboard --spec <verified-spec> --trust-root <verified-trust-root> --answers-schema <verified-schema> --inventory
# prepare ce-install.answers.yaml (secrets ONLY as env:// file:// prompt:// refs;
# sudo pre-granted only as a scoped list, e.g. host.sudo_grant: [runsc, proxy])
cev3 onboard --spec <verified-spec> --trust-root <verified-trust-root> --answers-schema <verified-schema> --answers ce-install.answers.yaml --plan
cev3 onboard --spec <verified-spec> --trust-root <verified-trust-root> --answers-schema <verified-schema> --answers ce-install.answers.yaml --apply --non-interactive
```

`--plan` shows the full plan plus the *exact remaining asks*;
`--apply --non-interactive` is fail-closed — it refuses with that list instead
of ever asking (unattended/VPS runs). The one-liner passes a file through too:
`CE_ANSWERS=ce-install.answers.yaml curl … | bash` (or
`bash -s -- --answers <file>`). An answers value can configure anything
**except a weaker grader** — weakening (the cost opt-out, protections below
the CE floor) requires your explicit ratified binding, educate-first.

The E1 venv installs both `ce` and `cev3`; the bootstrap invokes `cev3` by
absolute path. Durable user-facing `ce` exposure is user-local and belongs to
the later apply path, not a system-wide E1 symlink.

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

The later apply path provisions the Plane-C runtime box (gVisor `runsc` + a
deny-by-default egress proxy) and the **GitHub App** (its private key lives on
tmpfs and mints a JIT scoped token only at open/merge, then revokes — never in
the box). You complete the **GitHub-App authorization click** in your browser.
CE opens and merges as the **App bot identity** (≠ you), so on a solo repo **you
are the reviewer** and no-self-approval holds.

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

For a brand-new project, set `github.mode: new`, `github.repo`,
`project.name` (optional; defaults to the repo basename), and
`project.scaffold.kind: minimal` in the answers file. `cev3 onboard --plan` then
shows `first_project`: the project root under `host.workspace_root`, the minimal
scaffold input supplied to E2's `workspace_checkout` leg, and the Frame→Ship
flags that remain false until your first real Scope ships. The bootstrap README
and initial branch are onboarding evidence only; they do not count as first ship.

For an existing repo, `cev3 onboard --inventory` and `--plan` also report
`brownfield` / `brownfield_adoption`: workflows and checks to preserve, detected
test commands, Git history posture, branch/commit conventions, scrub preflight,
project skill artifacts, and a first Scope seed. These paths are read-only until
E2's `onboard_apply` brownfield extension legs perform the writes; a build
without those legs refuses apply with `e2_brownfield_seam_unavailable`.

## 3. Drive work as a Scope (Frame → Shape → Build → Review → Ship)

Launch the session frame:

```
cev3 session
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
   When the card reads **Ready ✓**, place the bet: `cev3 ratify <scope>`.
3. **Build** — `cev3 drive <scope>` dispatches one governed, boxed run (the front
   gate refuses unless Ready + ratified; the appetite becomes the run's spend cap).
4. **Review** — read the **◆ CE Completion Report**: `cev3 report <scope>`:

```
┌─ ◆ CE COMPLETION REPORT · run r-91a · Scope cs-4f2 ──────────────────
│ Outcome   PR opened → #7
│ Verdict   Done-when 3/3 met · tests green · in scope ✓ · 14% of Budget S
│ Next      → Review PR #7  (Change-type code → your approval)
│ Inspect   gh pr view 7   |   cev3 show cs-4f2   |   cev3 artifacts r-91a
└──────────────────────────────────────────────────────────
```

   You judge **artifacts** (the PR, the manifest-scoped diff, the evidence) — not a
   transcript. The grader lives outside the agent.
5. **Ship** — approve and merge the PR (the back gate is `mutation_class`-tiered;
   branch protection enforces independent review). `Ship` is plural — a merged PR,
   delivered research, or a ratified "no change."

## 4. Inspect anything

`cev3 artifacts <run>` and `cev3 show <scope>` enumerate every artifact (PR · Scope ·
ratification · closed manifest · evidence-chain · spend) with its inspect command.
For the plain-language tour, run `cev3 guide`.

## 5. Greenfield-OSS quickstart

For a fresh open-source repo: prepare answers with `github.mode: new`, run
`cev3 onboard --spec llms-install.md --answers ce-install.answers.yaml --plan`,
then apply after the plan is clean:

```
cev3 onboard --spec llms-install.md --answers ce-install.answers.yaml --apply --non-interactive
```

Authorize the App when prompted, then open `cev3 session`. Chat in Frame, confirm a
real first Scope, set the Budget, ratify it, drive the Build, review the PR in a
distinct venue, and merge through `cev3 merge --apply`. From there, every change is
a governed, cost-safe, evidence-backed Scope.

## Deferred (after E1)

Runtime provisioning · the interactive GitHub-App click · live status-line tap ·
live run dispatch. These are the human-gated live seams the authenticated
inventory bootstrap prepares but does not claim.

## Companions

[`understanding-ce.md`](./understanding-ce.md) ·
[`../architecture/pilot-uiux-model.md`](../architecture/pilot-uiux-model.md) ·
[`../architecture/pilot-deployment-transport.md`](../architecture/pilot-deployment-transport.md) ·
[`../contracts/installer.md`](../contracts/installer.md) ·
[`../contracts/scope.md`](../contracts/scope.md) · [`../v3-roadmap.md`](../v3-roadmap.md).
