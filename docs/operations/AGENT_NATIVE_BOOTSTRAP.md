# Agent-Native Bootstrap (`AGENT_NATIVE_BOOTSTRAP.md`)

Gate: **G6 — `ce` CLI umbrella + deterministic launch/doctor/init packaging surface** (RUN; strict TDD).
Requirement: **RV1-064** (`specs/_traceability_matrix.md`).
Machine-readable companion: `templates/hermes/agent-native-bootstrap.yaml`.

> **Authority.** This document defines how an agent harness bootstraps the
> Creator Engine v1.0 **local governed runtime kernel** (`ce`). It grants **no**
> hosted-service, team-mode, or GitHub-connector authority, starts **no** daemon,
> and makes **no** network call at install or runtime authority. It is a
> deterministic, offline, fail-closed bootstrap.

---

## 1. Purpose

An agent (Claude Code / Codex / Hermes / a compatible harness) uses this contract
to prepare and enter the kernel **without a human hand-holding each step** and
**without drifting out of the governance contract**. The machine-readable form is
`templates/hermes/agent-native-bootstrap.yaml`; this prose document is its
normative companion. Both are read-only inputs — the agent consumes them, it does
not mutate them.

## 2. One-directional authority transfer

Authority flows **one way**: from the host-local **Operator/Controller seat** to
the **launched agent lane**.

- The lane **never** gains authority over the Controller seat.
- The lane **never** promotes itself to hosted/team-mode/GitHub authority
  (`authority_model.hosted_team_github_authority: false`).
- The lane **cannot ratify its own work**; it returns results to the Controller
  seat as **evidence for ratification only**.

This is the same fail-closed posture as the governed lane-launch primitive
(`docs/operations/GOVERNED_LANE_LAUNCH_PROTOCOL.md`): visible-or-refuse, no hidden
fallback.

## 3. Install — offline runtime dependencies + source path

The clone-mode install contract is `source-pythonpath-with-offline-runtime-deps`,
**offline** (`--no-index`), against the **cp314-only** dependency wheelhouse.
Python floor is `>=3.14`. The first-party validator code is loaded from the
checkout with `PYTHONPATH=validators`; clone-mode does not install an app wheel
from `validators/wheelhouse`.

The bootstrap **MUST** install these runtime dependencies before running the
source-backed `ce doctor` preflight, because the source `ce` command graph imports
runtime modules such as PyYAML and jsonschema at startup.

uv-first:

```bash
uv venv --python 3.14
CE_VALIDATOR_PYTHON="${CE_VALIDATOR_PYTHON:-.venv/bin/python}"
UV_PYTHON_DOWNLOADS=never uv pip install --python "$CE_VALIDATOR_PYTHON" --no-index --find-links validators/wheelhouse -r validators/requirements.txt
```

pip fallback (uv-less host):

```bash
python3.14 -m venv .venv
CE_VALIDATOR_PYTHON="${CE_VALIDATOR_PYTHON:-.venv/bin/python}"
"$CE_VALIDATOR_PYTHON" -m pip install --no-index --find-links validators/wheelhouse -r validators/requirements.txt
```

No network fetch occurs at install or runtime authority
(`docs/governance/V1_PRODUCT_CONTRACT.md` §6).
All source-backed validator invocations below **MUST** use
`$CE_VALIDATOR_PYTHON` so the checkout source runs under the same interpreter
environment that received the offline runtime dependencies.

## 4. Preflight — source `ce doctor --json`

After the offline runtime dependency install succeeds, the bootstrap **MUST** run
the governed-environment guard preflight:

```bash
CE_VALIDATOR_PYTHON="${CE_VALIDATOR_PYTHON:-.venv/bin/python}"
PYTHONPATH=validators "$CE_VALIDATOR_PYTHON" -m creator_engine_validator.ce_cli doctor --json
```

The source-backed `ce doctor` module invocation evaluates the governed-environment
guard predicate (DP-3 = B,
`docs/governance/V1_GOVERNED_ENVIRONMENT_GUARD_REQUIREMENT.md`) and exits
**non-zero** on any refused clause. The public/package-installed `ce doctor`
entry point is equivalent, but clone-mode bootstrap does not require a committed
first-party app wheel:

| Clause | Refusal |
|---|---|
| RED-G-1 | out-of-contract interpreter (not `>=3.14` / 3.14.x) |
| RED-G-2 | missing tmux for a visibility-required launch (PCO-049) |
| RED-G-3 | missing rootless Podman, or rootful Podman, for worker execution (PCO-045) |
| RED-G-4 | ungoverned `.hermes/` state-path posture (not git-ignored) |
| RED-G-5 | unsafe hidden continuation (no visible pane / dead-pane) |
| RED-G-6 | dependency wheelhouse drift from the Option B contract |

## 5. Blocked-report semantics on failed preflight

If the doctor preflight exits non-zero, the bootstrap **MUST**:

1. **Stop** (`preflight.blocked_report.stop: true`). Do not continue.
2. Emit a **blocked report** naming the refused guard clauses from the
   `refused_clauses` array of the JSON output.
3. **Not** ratify any in-flight work and **not** fall back to a hidden/headless
   continuation. There is no hidden fallback.

## 6. Launch — visible Controller seat

After a successful offline install and PASS preflight, the agent enters the
visible Controller seat:

```bash
CE_VALIDATOR_PYTHON="${CE_VALIDATOR_PYTHON:-.venv/bin/python}"
PYTHONPATH=validators "$CE_VALIDATOR_PYTHON" -m creator_engine_validator.ce_cli launch --json
# `hud` is an alias/seam label for the same launcher:
PYTHONPATH=validators "$CE_VALIDATOR_PYTHON" -m creator_engine_validator.ce_cli hud --json
```

The launch command opens/attaches a **visible** tmux Controller seat (DP-2 = B).
It refuses hidden/headless continuation; `hud` is an **alias**, not a CE-native
HUD/TUI.

## 7. Boundaries (POST-V1 / seam-only)

The bootstrap explicitly does **not** enable any of:

- hosted service / SaaS (`boundaries.hosted_service: false`),
- team mode (`boundaries.team_mode: false`),
- GitHub connector (`boundaries.github_connector: false`),
- a daemon (`boundaries.daemon: false`),
- network at runtime authority (`boundaries.network_at_runtime: false`).

These remain `SEAM` / `POST-V1` per `docs/governance/V1_PRODUCT_CONTRACT.md` §3–§4.

## 8. References

- `templates/hermes/agent-native-bootstrap.yaml` — machine-readable contract.
- `docs/governance/V1_PRODUCT_CONTRACT.md` — DP-1/DP-2/DP-3, Option B contract.
- `docs/governance/V1_GOVERNED_ENVIRONMENT_GUARD_REQUIREMENT.md` — guard predicate.
- `docs/operations/GOVERNED_LANE_LAUNCH_PROTOCOL.md` — visible-or-refuse lane launch.
- `specs/_traceability_matrix.md` — RV1-060 .. RV1-064.
