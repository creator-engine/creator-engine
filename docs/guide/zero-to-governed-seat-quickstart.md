# Zero to Governed Seat Quickstart

This is the shortest first-host path from a blank Linux pilot host to a CE
governed seat. It keeps E1 trust verification separate from later human-approved
apply gates.

Before you start:

- Install a supported coding-agent CLI such as Claude Code or Codex.
- Add `.hermes/` to the target repository's `.gitignore` before onboarding, so
  CE's local Hermes state can never become tracked project content.
- Have `curl` and `git` available on the host.

## 1. Host Bootstrap

Run the installer first. If the host is missing stock bootstrap tools, it refuses
before fetching artifacts and prints the exact package command for your distro.
Review that package action, run the matching command, then re-run the installer.

```bash
curl --proto '=https' --tlsv1.2 -fsSL https://creator-engine.dev/install.sh | bash
```

`curl` fetches the installer; `git` is required for the first-value
author→commit→push→PR→merge flow once you reach a governed seat.

Python 3.14 and `uv` do not need to be installed ahead of time. After the signed
spec is verified with `ssh-keygen`, E1 downloads the manifest-pinned `uv`
tarball, verifies its hash, and installs CPython 3.14 in user space if needed.

## 2. First CE Command: Onboard

After the installer, run the one-shot onboarder from the repository you want to
use with CE:

```bash
ce onboard
```

`ce onboard` is the first CE command on a new host. It verifies the local
install, initializes CE state, checks onboarding prerequisites, and opens the
first governed agent pane unless you opt out.

If you are continuing directly into the repo-connected install plan/apply steps
below and do not want to open the pane yet, run:

```bash
ce onboard --no-launch
```

## 3. E1 Inventory

A successful E1 run installs `ce` into a user-local verified venv,
adds user-local CLI shims, and runs authenticated inventory. Save the verified
paths printed by the installer summary:

```text
--spec <verified-spec>
--trust-root <verified-trust-root>
--trust-anchor <source>=<verified-trust-anchor>
--answers-schema <verified-schema>
```

Prepare `ce-install.answers.yaml` with your host, provider, GitHub, and project
answers. Keep secrets as refs such as `env://GITHUB_TOKEN`, `file://...`,
`prompt://...`, or `keychain://...`; never put raw secrets in the file.

## 4. Plan Then Apply

Run the plan first. It shows the exact remaining asks and the privileged changes
that still need human approval.

```bash
ce install \
  --spec <verified-spec> \
  --trust-root <verified-trust-root> \
  --trust-anchor <source>=<verified-trust-anchor> \
  --answers-schema <verified-schema> \
  --answers ce-install.answers.yaml \
  --plan
```

When the plan is acceptable, apply it explicitly:

```bash
ce install \
  --spec <verified-spec> \
  --trust-root <verified-trust-root> \
  --trust-anchor <source>=<verified-trust-anchor> \
  --answers-schema <verified-schema> \
  --answers ce-install.answers.yaml \
  --apply --non-interactive
```

`--apply --non-interactive` is fail-closed: it refuses with the unresolved input
list instead of guessing. The GitHub App authorization click and any sudo-scoped
host changes remain human-approved apply seams.

## 5. Governed Seat

After onboarding and apply converge, open or return to the governed session in
the target repo:

```bash
ce launch
```

Frame a concrete change in the governed pane, confirm the work boundary CE
offers, review the PR in a distinct venue, and ship only through the governed
merge path.

The first bootstrap commit or scaffold is onboarding evidence only. The first
real shipped change is the first post-apply Scope that passes review and merges.
