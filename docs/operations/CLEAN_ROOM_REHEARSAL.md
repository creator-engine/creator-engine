# N6 Clean-Room Rehearsal Runbook

**Gate**: v0.3.0 N6 clean-room rehearsal (SHIP / SLIP gate scaffold)
**Status**: **Offline scaffold now; live controller-run gate later.** N6
defines the pass/fail shape for the v0.3.0 release rehearsal, but the live
controller-run gate is intentionally guarded until N1-N5 land and the N3 guarded
stub path is merged.
**Authority boundary**: N6 does not ship v0.3.0 by itself. It records evidence
for a SHIP / SLIP recommendation. Any nonzero exit is a **SLIP** and the gate
fails closed.

---

## 1. Purpose

The N6 clean-room rehearsal proves that a fresh host can install, inventory,
plan, apply, exercise first value, update, and tear down Creator Engine without
embedding local assumptions in the release process. In the current scaffold, the
run is offline and dry-run oriented: it validates command shape, evidence
layout, and fail-closed behavior without granting live controller authority.

The later live gate runs under controller authority after the N1-N5 dependency
chain is merged and the N3 guarded first-value stub has landed. Until then, N6
is a rehearsal scaffold and a checklist, not a release decision engine.

## 2. Prerequisites

Run from the repository root on branch `ce191-n6-clean-room-rehearsal` or the
later branch that carries the N6 script. The clean-room host needs:

- A fresh checkout with no required local runtime state outside the repo.
- POSIX shell and `bash`.
- Python / package tooling required by the currently ratified installer path.
- Network disabled or unused for dry-run unless a stage explicitly documents a
  read-only probe.
- No secrets in environment variables, command lines, fixtures, transcripts, or
  evidence files.
- A gitignored evidence root, normally under `.hermes/`.

The script path is expected to be:

```bash
bash scripts/clean-room-rehearsal.sh --dry-run
```

This branch intentionally carries `scripts/clean-room-rehearsal.sh`. If the
script is missing from a later release branch, not executable through `bash`, or
cannot print its help text, N6 is a **SLIP** for live readiness. Do not
substitute another script for the N6 gate.

## 3. Runtime configuration

All configuration is supplied through the script's documented `CE_REHEARSAL_*`
environment variables and command flags. Do not commit machine-specific values
or credentials into this runbook, the script, or evidence fixtures.

| Parameter | Meaning | Notes |
|---|---|---|
| `--dry-run` | Print the full staged plan and exit `0` | Does not require Docker, network, or secrets. This is the scaffold's primary command. |
| `--live` | Affirmatively enable live execution | Required for any full run or per-stage run that is not `--dry-run`. May use Docker, network, and externally supplied runtime auth. |
| `--stage NAME` | Run one script stage | `NAME` must be one of the values from `--list-stages`. Without `--live`, this is accepted only with `--dry-run`, which prints the safe full staged plan. |
| `--list-stages` | Print script stage names | Canonical stage list for per-stage diagnostics. |
| `CE_REHEARSAL_IMAGE` | Docker image | Default: `ubuntu:24.04`. |
| `CE_REHEARSAL_CONTAINER_NAME` | Docker container name | Defaults to a process-scoped N6 rehearsal name. |
| `CE_REHEARSAL_SITE` | Staged docs site | Default: `https://creator-engine.dev`. |
| `CE_REHEARSAL_INSTALL_URL` | Installer URL | Default derives from `CE_REHEARSAL_SITE`. |
| `CE_REHEARSAL_MYTHOS_REPO` | Runtime mythos repository locator | Defaults to `CE_MYTHOS_REPO` when set, then the non-secret scaffold locator. |
| `CE_REHEARSAL_INSTALLATION_ID` | Runtime GitHub App installation id for mythos access | Defaults to `CE_MYTHOS_INSTALLATION_ID` when set, then the non-secret scaffold id. |
| `CE_REHEARSAL_CONTAINER_ID` | Existing container id/name for per-stage runs | Cleanup will not remove an attached container unless teardown is run explicitly. |
| `CE_REHEARSAL_CLAUDE_INSTALL_CMD` | Optional Claude Code installation command | When unset, the `claude` stage writes a documented auth placeholder. |
| `CE_REHEARSAL_KEEP_CONTAINER` | Preserve live container for debugging | Off by default. Preserved containers remain operator-managed evidence. |

`CE_MYTHOS_REPO` and `CE_MYTHOS_INSTALLATION_ID` are compatibility aliases for
the rehearsal-specific variables. The mythos repo and installation id are
runtime configuration handles, not secrets, but they remain configurable so the
runbook stays portable across installations. Tokens, private keys, OAuth
material, cookies, and session files are never accepted as defaults or inline
parameters.

## 4. Dry-run execution

Primary scaffold command:

```bash
bash scripts/clean-room-rehearsal.sh --dry-run
```

Expected dry-run behavior:

1. Print `CE_REHEARSAL_PLAN` lines for runtime mythos repo,
   `installation_id`, installer URL, and the no-secret-defaults policy.
2. Print the ordered script stages it would execute: `provision`, `claude`,
   `install`, `inventory`, `onboard`, `first_value`, `update`, `teardown`.
3. Mark guarded TODO stages visibly instead of silently passing them.
4. Exit `0` after printing the dry-run plan without requiring Docker, network,
   or secrets.

Any nonzero exit is the gate result: **SLIP / fail-closed**. Do not continue to
later stages manually after a nonzero exit unless the resumed command is itself
captured as a new N6 run with fresh evidence.

### Per-stage execution

If the script documents per-stage execution in `--help`, use the documented
flag names rather than inventing aliases. Acceptable examples, only if
implemented by the script, are:

```bash
bash scripts/clean-room-rehearsal.sh --list-stages
bash scripts/clean-room-rehearsal.sh --dry-run --stage inventory
bash scripts/clean-room-rehearsal.sh --live --stage inventory
bash scripts/clean-room-rehearsal.sh --live --stage first_value
```

Per-stage runs are diagnostic evidence only. A non-dry-run per-stage command
must include `--live`; otherwise the script exits nonzero before touching
Docker, network, or secrets. A SHIP recommendation requires a single ordered
D1-D6 run unless the script explicitly documents resumable stage semantics and
records the resumed evidence chain.

## 5. Live-run warning

Live mode is guarded. Do not run a live N6 gate until:

- N1-N5 are merged into the target release base.
- The N3 guarded first-value stub is merged.
- The mythos repository and `installation_id` are supplied by runtime
  configuration.
- A controller has explicit authority for the live release rehearsal.
- The operator has confirmed that the evidence root is gitignored and contains
  no secrets.

Live mode may touch remote services, installation state, and controller-run
surfaces. It requires an explicit `--live` affirmative flag. Running the script
with no arguments, or with `--stage NAME` but without `--dry-run` or `--live`,
must exit nonzero before Docker, network, or secrets and recommend `--dry-run`
or `--live`. If live mode is requested before the dependencies above are true,
the script must exit nonzero and record **SLIP / fail-closed**.

## 6. D1-D6 pass/fail checklist

The script uses operational stage names, while the release checklist keeps the
D1-D6 gate labels. The mapping is:

| Checklist label | Script stage(s) |
|---|---|
| D1 install | `provision`, `claude`, `install` |
| D2 inventory | `inventory` |
| D3 plan/apply | `onboard` |
| D4 first value | `first_value` |
| D5 update cycle | `update` |
| D6 teardown/evidence | `teardown` |

| Stage | Pass condition | Fail / SLIP condition |
|---|---|---|
| D1 install | Installer command resolves from a fresh host, writes only approved runtime paths, and records install evidence. | Missing installer, undeclared network dependency, tracked-file mutation, or nonzero exit. |
| D2 inventory | Host inventory completes and records tool/version/config facts. N1 `git` / `curl` readiness warnings are allowed only as explicit WARN evidence in dry-run; they must be cleared or accepted by the live gate policy before live SHIP. | Inventory cannot run, omits required facts, hides N1 `git` / `curl` WARNs, or exits nonzero. |
| D3 plan/apply | Plan is produced before apply; dry-run apply is side-effect bounded and records the intended mutation set. | Apply runs without a plan, changes tracked files unexpectedly, skips evidence, or exits nonzero. |
| D4 first value | First-value path is exercised through the N3 guarded stub and records that the live value path remains guarded. | First-value bypasses the N3 guard, claims live value before N3 merge, lacks evidence, or exits nonzero. |
| D5 update cycle | Update / re-run cycle is idempotent or records expected drift with a bounded plan. | Update is not repeatable, changes unapproved state, loses prior evidence, or exits nonzero. |
| D6 teardown/evidence | Temporary resources are removed or explicitly preserved under evidence policy; transcript, manifest, checksums, and final summary are written. | Leaked workdir without `keep` policy, missing evidence, secret-shaped content, untracked surprise outside evidence root, or nonzero exit. |

The checklist is all-or-nothing. A skipped required stage is a SLIP unless the
script marks the stage as guarded and the guard is one of the TODO dependencies
listed below.

## 7. Stubbed and guarded stages

The scaffold must make guarded behavior visible rather than silently succeeding.

| Area | Current disposition |
|---|---|
| N6 live controller-run gate | Guarded until N1-N5 and N3 merge. Dry-run may rehearse command shape only. |
| N3 first-value path | Guarded stub only. D4 may prove the guard and stub contract; it must not claim live first value. |
| Mythos repository access | Runtime-configured through `CE_REHEARSAL_MYTHOS_REPO` / `CE_REHEARSAL_INSTALLATION_ID`, with `CE_MYTHOS_REPO` / `CE_MYTHOS_INSTALLATION_ID` aliases. Dry-run prints the resolved handles but never prints or defaults secrets. |
| Remote installation mutation | Disabled in dry-run. Live mode must be explicit and controller-authorized. |
| Per-stage replay | Available only if `scripts/clean-room-rehearsal.sh --help` documents it. Otherwise the canonical run is full D1-D6. |

## 8. TODO dependencies

- Land N1-N5 on the target release base.
- Merge the N3 guarded first-value stub.
- Promote `scripts/clean-room-rehearsal.sh` from scaffold to the live
  controller-run gate with evidence writing and an explicit live authorization
  envelope.
- Wire controller-owned runtime mythos configuration lookup for repository and
  `installation_id` where the live gate runs.
- Define the live controller authorization envelope for the N6 release gate.

Until those dependencies are complete, N6 can produce scaffold evidence and a
dry-run readiness result only. It cannot produce a live v0.3.0 SHIP decision.
