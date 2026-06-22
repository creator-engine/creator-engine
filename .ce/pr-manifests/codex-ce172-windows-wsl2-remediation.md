# PR path manifest - codex-ce172-windows-wsl2-remediation

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref codex/ce172-windows-wsl2-remediation
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Scope:
ce-ops#172 non-release-signing Windows via WSL2 remediation. Native Windows
platform names refuse with WSL2 + Ubuntu instructions in the Python installer
planner; WSL2 itself remains on the normal Linux path. Public unsigned install
copy directs Windows users to use WSL2/Ubuntu and run the existing Linux
installer inside WSL2. No Windows wheel/platform entries, wheelhouse rebuilds,
scanner binaries, runtime refactors, signed installer-script edits, or release
artifact re-pins are included.

Release-artifact note:
This PR intentionally restores `docs/install.sh` and
`docs/downloads/0.2.0/SHA256SUMS` to `origin/main` and leaves
`docs/llms-install.md` byte-for-byte unchanged. Native Windows one-liner
remediation for the signed installer script is deferred to an authorized
ce-root-v1 signing lane.

Per-file purpose (closed path-set - 7 paths):

- **`.ce/changelog/ce172-windows-wsl2-remediation.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/codex-ce172-windows-wsl2-remediation.md`** *(A)* - this PR's closed path-set carrier.
- **`docs/index.html`** *(M)* - unsigned website install copy for Windows via WSL2/Ubuntu, with signed-installer remediation deferred.
- **`docs/llms.txt`** *(M)* - unsigned agent-discovery install guidance for Windows via WSL2/Ubuntu, with signed-installer remediation deferred.
- **`validators/creator_engine_validator/v3_installer.py`** *(M)* - pure platform-plan remediation for native Windows names.
- **`validators/tests/integration/test_install_bootstrap.py`** *(M)* - unsigned-docs coverage for WSL2 guidance and signing-lane deferral.
- **`validators/tests/unit/test_v3_installer.py`** *(M)* - source platform-plan coverage for Windows/win32/MINGW/MSYS/Cygwin messages.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=d7af14faab75786586f5df22772389f54163b6c7d243820e6b9bba5ca8039aa2

```text
.ce/changelog/ce172-windows-wsl2-remediation.md
.ce/pr-manifests/codex-ce172-windows-wsl2-remediation.md
docs/index.html
docs/llms.txt
validators/creator_engine_validator/v3_installer.py
validators/tests/integration/test_install_bootstrap.py
validators/tests/unit/test_v3_installer.py
```
