# Your First Project

Make one small, visible improvement before you ask CE to handle a larger
change.

This tutorial adds a build-status badge to a repository README. It is small
enough to review quickly, while still taking you from a plan through review and
delivery.

## Before you begin

Open a terminal in the repository you want to change. You need a supported
coding agent available on your machine, permission to create a branch, and the
repository permissions your team normally requires when it is time to ship.

For setup help, see [Start Here](./start-here.md), the
[quickstart](./quickstart.md), and [troubleshooting](./troubleshooting.md).

## Install once; onboard each project

Install CE before it is available in your terminal. Onboard from inside a
project to check your setup, prepare the project, and open your coding-agent
session.

For a first local installation, run:

```bash
curl --proto '=https' --tlsv1.2 -fsSL https://creator-engine.dev/install.sh | bash
```

Then, from the repository root, run:

```bash
ce onboard
ce brain init
ce launch --backend host
```

Use this order for a first project: install, onboard, initialize project
context, then launch your coding-agent session. If CE reports that project
state is missing, restore it in this order:

```bash
ce brain init
ce onboard
```

If a command reports a session problem, stop and follow its guidance before
trying again.

## 1. Frame the change

Describe the outcome in one sentence before you write commands:

> Add a build-status badge near the top of the README, without changing the
> existing installation instructions.

A good first change has a clear place to inspect and a short list of things
that must be true when it is finished. For this change, the README is the place
to inspect.

## 2. Shape the work

Ask CE to turn the idea into a bounded piece of work:

```bash
ce shape readme-build-badge
```

Use the session to answer any questions it raises. Keep the change narrow. If
you discover that the README needs a broader redesign, create a separate plan
for that decision.

## 3. State what success means

Create a plan with a goal, completion checks, and the smallest accurate change
type:

```bash
ce scope readme-build-badge \
  --goal "Add the repository build-status badge near the top of the README" \
  --done-when "README shows the build-status badge near its title" \
  --done-when "The badge links to the repository's build workflow" \
  --done-when "Existing README installation instructions are unchanged" \
  --change-type docs
```

Read the goal and every completion check back to yourself. This is the moment
to catch a vague request such as "make the README better." If the plan is
wrong, revise it before starting work.

## 4. Confirm the plan

When the plan describes exactly what you want, create a fresh approver ref
and confirm it:

```bash
ce ratify readme-build-badge \
  --approver-ref "$(openssl rand -hex 32)"
```

Do not reuse a confirmation reference from another change. If you change the
goal, completion checks, or change type after this point, create a revised plan
rather than relying on a chat message as an update.

## 5. Let the agent build

Start the work:

```bash
ce drive readme-build-badge --spawn
```

The coding agent can now make the README change and collect evidence for the
completion checks. Stay available for questions about the repository, the
correct workflow URL, or project-specific wording.

## 6. Review the result

Ask for the result summary:

```bash
ce report readme-build-badge
```

A completed report identifies the outcome, the completion-check result, and
the next review action. For example:

```text
┌─ ◆ CE COMPLETION REPORT · run run-readme-build-badge-20260711T140000Z · Scope readme-build-badge ──────────────────
│ Outcome   PR opened → #24
│ Verdict   Done-when 3/3 met · tests green · in scope ✓
│ Next      → Review PR #24  (Change-type docs → your approval)
└────────────────────────────────────────────────────────────
```

Note the run ID in the report header (`run run-readme-build-badge-…`) — step 7 needs it.

Your pull-request number and wording will differ. Open the reported pull
request and inspect the README as a reader would. Check that the badge is
visible, points to the right workflow, and did not disturb the installation
instructions. Review the evidence against the three completion checks, not
just the summary.

## 7. Ship when review is complete

After the required repository review and checks have passed, use the run ID
shown by the report to prepare the recorded outcome for shipping:

```bash
ce merge readme-build-badge --run <run-id-from-report> --apply
```

Run this only when you hold the repository authority to ship the change. The
result should be the same small improvement you described at the start: a
useful build-status badge, with the rest of the README left intact.

## If something fails

If `ce onboard` says installation is required, return to the published install
instructions and install CE before trying onboarding again. That message does
not provide the installer URL.

If a build stops mid-flight, do not begin a second copy of the same change.
First inspect the current result:

```bash
ce report readme-build-badge
```

Keep the branch and report available while you decide whether to continue. If
you decide not to ship, do not run the shipping command and do not delete
project-local CE files by hand. Use your repository's normal branch and
pull-request practices to preserve or close the proposed change.

## What you just did

You turned a small request into explicit success checks, confirmed the exact
change before the coding agent started, and reviewed the result against those
checks. That same sequence works for the next project change: start small,
make success visible, and expand the scope only when the outcome calls for it.
