# Support Matrix

Creator Engine is designed for Linux development environments. This page explains what
works today and what you need before you begin.

## Platforms

| Environment | Status | What to know |
| --- | --- | --- |
| Linux x86_64 / amd64 | Supported by the installer | The installer recognizes both architecture names and downloads the matching package set. |
| Linux arm64 / aarch64 | Supported by the installer | The installer recognizes both architecture names and downloads the matching package set. |
| Linux distributions | Not yet documented/tested — check back | A tested distribution list is not yet documented. The installer provides recovery instructions for Debian/Ubuntu, Fedora/RHEL/CentOS, Alpine, and Arch when basic tools are missing. |
| macOS | Use a Linux container or VM | CE does not ship a native macOS installer. Docker Desktop, Podman with Colima, or another Linux-backed VM can host CE. See the [macOS container guide](./onboarding-macos-container.md). |
| Windows | Not yet documented/tested — check back | A supported Windows installation path is not yet documented. |

## Coding agents

| Agent | Status | What you need |
| --- | --- | --- |
| Claude Code | Documented | Install it and sign in before starting a CE session. The macOS container guide specifically uses Claude Code inside the Linux environment. |
| Codex | Documented | Install it and sign in before starting a CE session. A version-by-platform support table is not yet documented — check back. |
| Other coding-agent CLIs | Not yet documented/tested — check back | The public guides name Claude Code and Codex; a broader compatibility promise is not yet documented. |

## GitHub and repositories

Installing CE does not require CE to change a GitHub repository.

To connect CE to a repository later, you need:

- A GitHub account and a repository you can configure.
- Permission to authorize the GitHub App for that repository.
- A short-lived setup token when the install plan asks for one. The documented setup checks
  for Administration, Contents, Actions, and Workflows access, then uses the App for later
  repository actions.
- A human review of the plan before applying repository changes.

## Docker and containers

| Need | Docker required? |
| --- | --- |
| Install and use CE on a supported Linux machine | No |
| Use CE from macOS | Yes, or another Linux-backed container/VM runtime |
| Use advanced container options | Not yet documented/tested — check the relevant documentation before relying on this path |

## GPUs and NVIDIA systems

A GPU is not required for installation: the installer checks operating system and CPU
architecture, not GPU hardware. CE includes optional GPU-aware components, but a supported
GPU, driver, and acceleration matrix is not yet documented/tested — check back.

## What CE installs, and what you provide

| CE installs after download checks pass | You provide first |
| --- | --- |
| A user-local Python environment and the `ce` command | Linux on a supported CPU architecture, or a Linux container/VM on macOS |
| Python 3.14 when a compatible version is not already available | A coding-agent CLI such as Claude Code or Codex, signed in |
| Required CE packages | Git, OpenSSH client (`ssh-keygen`), `curl`, and standard shell tools |
| Verified package files for the current release | Network access to the install services |
| — | GitHub access only when you choose to connect a repository |

If Git or OpenSSH is missing, the installer checks for it and provides or attempts the
documented package-manager remediation. If a required shell tool is missing, it stops and
prints the next step instead of continuing with a partial install.
