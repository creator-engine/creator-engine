# Start Here

Creator Engine helps you use the coding agent you already know with clearer plans, review
steps, and a record of what changed.

## Before you start

- Use Linux on an x86_64/amd64 or arm64/aarch64 machine. Mac users should use the
  [macOS container guide](./onboarding-macos-container.md).
- Install and sign in to Claude Code or Codex.
- Have Git and the OpenSSH client (`ssh-keygen`) available.
- Make sure your network can reach `creator-engine.dev`, `dns.google`, and, when Python is
  needed, `github.com`.

## Install

Run:

```bash
curl --proto '=https' --tlsv1.2 -fsSL https://creator-engine.dev/install.sh | bash
```

The installer checks the download, installs CE in your user account, and prepares the `ce`
command. It does not make system changes or connect a GitHub repository during this first
step.

## Success looks like

Look for output like:

```
◆ CE · summary: downloaded=… reused=… verified=… installed=… skipped_already_current=… failed=0
◆ CE · next: reload PATH in this shell with '. ~/.profile && hash -r'
```

If asked, reload your shell path:

```
. ~/.profile && hash -r
```

## Start your first project

From the project directory where you want to use CE, run:

```
ce onboard
```

This checks your local setup, prepares CE for the project, and starts your coding-agent
session.

## Where to go next

Follow the [quickstart guide](./quickstart.md) for your first planned change, review, and
pull request.
