# Troubleshooting

Use the message printed by CE as your starting point. Fix the named problem,
then run the same command again.

## The installer cannot download files

**Symptom**

The installer reports that it could not download a file, or that a download
page returned 404 while it is updating.

**Cause**

Your machine cannot reach one of the required services.

**Fix**

Check access to:

- creator-engine.dev
- dns.google
- the download hosts that the `uv` tool uses for Python (not yet fully documented)

Then run the installer again:

```bash
curl --proto '=https' --tlsv1.2 -fsSL https://creator-engine.dev/install.sh | bash
```

It is safe to run the installer again after a network failure. CE reuses
verified downloads when possible and prevents two installs from running at
once.

## `ce`: command not found after installation

**Cause**

Your current shell has not loaded the new command path.

**Fix**

Run:

```bash
. ~/.profile && hash -r
command -v ce
ce --help
```

If that does not work, open a new terminal and try again. Shell-specific path
instructions are not yet documented—check back for updates.

## Git, OpenSSH, or shell tools are missing

**Symptom**

The installer reports that a required command is missing.

**Fix**

For Git:

```bash
# Debian/Ubuntu
sudo apt-get update && sudo apt-get install -y git

# Fedora/RHEL/CentOS
sudo dnf install -y git

# Alpine
sudo apk add git

# Arch
sudo pacman -Sy --needed git
```

For OpenSSH (`ssh-keygen`):

```bash
# Debian/Ubuntu
sudo apt-get update && sudo apt-get install -y openssh-client

# Fedora/RHEL/CentOS
sudo dnf install -y openssh-clients

# Alpine
sudo apk add openssh-client

# Arch
sudo pacman -Sy --needed openssh
```

If CE reports several missing shell tools, install the matching package set it
prints:

```bash
# Debian/Ubuntu
sudo apt-get update && sudo apt-get install -y ca-certificates curl openssh-client tar coreutils sed gawk grep

# Fedora/RHEL/CentOS
sudo dnf install -y ca-certificates curl openssh-clients tar coreutils sed gawk grep

# Alpine
sudo apk add ca-certificates curl openssh-client tar coreutils sed awk grep
```

Then run the installer again.

## Unsupported operating system or CPU

**Symptom**

The installer reports that your operating system or CPU is not supported.

**Cause**

The installer currently supports Linux on `x86_64`, `amd64`, `aarch64`, or
`arm64`.

**Fix**

- On macOS, install and run CE inside a Linux container or virtual machine.
  See the [macOS container guide](./onboarding-macos-container.md).
- A Windows installation path is not yet documented—check back for updates.

## Repository connection cannot continue

**Symptom**

A later install command reports missing GitHub information, a token problem,
or an authorization step.

**Cause**

Connecting a repository requires a GitHub repository you can configure,
permission to authorize the GitHub App, and, when requested, a short-lived
setup token.

**Fix**

1. Run the plan command printed by the installer.
2. Confirm that the target repository is correct.
3. Authorize the GitHub App for that repository.
4. If CE requests a setup token, create one with the access it requests and
   provide it only through the requested secure reference.
5. Run the plan again before applying changes.

Exact messages and recovery steps for every authorization failure are not yet
documented—check back for updates.

## `ce onboard` stops or reports incomplete setup

`ce onboard` checks your local environment, installation, command path,
project setup, and local project information. It starts one coding-agent
session unless you use `--no-launch`.

### No install found

CE reports that installation is required. Run the installer:

```bash
curl --proto '=https' --tlsv1.2 -fsSL https://creator-engine.dev/install.sh | bash
```

Run it, reload your shell path, then run `ce onboard` again.

### Install verification failed

CE reports that the installed files could not be verified. Run the public
installer again. Do not bypass the verification message.

### Project state is not ignored

CE explains that `.hermes/` must be listed in `.gitignore`. Add this line to
your project's `.gitignore`:

```text
.hermes/
```

Then run `ce onboard` again.

### Project state is not initialised

CE reports that local project state is missing. Run:

```bash
ce brain init
ce onboard
```

### No visible terminal session is available

CE completes safe setup steps but does not start the coding agent. Start a
supported terminal session, then run:

```bash
ce onboard
```

Terminal-specific setup guidance is not yet documented—check back for updates.

### More than one active session is detected

CE attempts to start a session and then stops when it detects an existing
active session. Do not start another copy. A recovery procedure for this
situation is not yet documented—check back for updates.

## Is it safe to run `ce onboard` again?

Usually, yes. It detects an existing install, keeps the shell-path update
repeatable, and repeats project setup safely. If an active session is
already running, it reports the conflict after the launch attempt rather
than creating a duplicate. Fix the reported prerequisite first, then run
the command again.
