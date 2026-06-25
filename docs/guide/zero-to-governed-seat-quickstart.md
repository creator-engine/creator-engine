# Zero to Governed Seat Quickstart

This is the shortest first-host path from a blank Linux pilot host to a CE
governed seat. It keeps E1 trust verification separate from later human-approved
apply gates.

## 0. Host Bootstrap

Run the installer first. If the host is missing stock bootstrap tools, it refuses
before fetching artifacts and prints the exact package command for your distro.
Review that package action, run the matching command, then re-run the installer.

```bash
curl --proto '=https' --tlsv1.2 -fsSL https://creator-engine.dev/install.sh | bash
```

**Prereqs:** the host needs `curl` and `git` available. `curl` fetches the
installer; `git` is required for the first-value author→commit→push→PR→merge
flow once you reach a governed seat.

Python 3.14 and `uv` do not need to be installed ahead of time. After the signed
spec is verified with `ssh-keygen`, E1 downloads the manifest-pinned `uv`
tarball, verifies its hash, and installs CPython 3.14 in user space if needed.

## 1. E1 Inventory

A successful E1 run installs `ce` and `cev3` into a user-local verified venv,
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

## 2. Plan Then Apply

Run the plan first. It shows the exact remaining asks and the privileged changes
that still need human approval.

```bash
cev3 onboard \
  --spec <verified-spec> \
  --trust-root <verified-trust-root> \
  --trust-anchor <source>=<verified-trust-anchor> \
  --answers-schema <verified-schema> \
  --answers ce-install.answers.yaml \
  --plan
```

When the plan is acceptable, apply it explicitly:

```bash
cev3 onboard \
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

## 3. Governed Seat

After apply converges, open the governed session in the target repo:

```bash
cev3 session
```

Frame a concrete change, confirm the Scope, ratify it, drive the Build, review
the PR in a distinct venue, and merge through the governed merge path:

```bash
cev3 ratify <scope>
cev3 drive <scope>
cev3 report <scope>
cev3 merge --apply
```

The first bootstrap commit or scaffold is onboarding evidence only. The first
real shipped change is the first post-apply Scope that passes review and merges.
