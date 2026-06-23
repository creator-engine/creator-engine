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

## 3. Install — offline venv provisioning + installed scripts

The clone-mode contract is `source-bootstrap-offline-installed-app`: create the
target venv, run the checkout's stdlib-only bootstrap module, install cp314
runtime dependencies from `validators/wheelhouse`, link the local `validators/`
source into the venv, and write the `ce`/`cev3` console scripts. Clone-mode does
not commit or consume a first-party app wheel from `validators/wheelhouse`.

Create the target venv with uv when available:

```bash
uv venv --python 3.14
CE_VALIDATOR_PYTHON="${CE_VALIDATOR_PYTHON:-.venv/bin/python}"
```

Or with the stdlib venv fallback on uv-less hosts:

```bash
python3.14 -m venv .venv
CE_VALIDATOR_PYTHON="${CE_VALIDATOR_PYTHON:-.venv/bin/python}"
```

Then provision the venv offline from the source checkout:

```bash
PYTHONPATH=validators "$CE_VALIDATOR_PYTHON" -m creator_engine_validator.bootstrap_runtime bootstrap --repo-root . --venv .venv --json
```

The installed/controller-facing equivalent is:

```bash
ce bootstrap --repo-root . --venv .venv
```

The bootstrap uses `uv pip install --python "$CE_VALIDATOR_PYTHON" --no-index
--find-links validators/wheelhouse -r validators/requirements.txt` when `uv` is
on PATH. Otherwise it uses `"$CE_VALIDATOR_PYTHON" -m pip`; if pip is absent it
tries `"$CE_VALIDATOR_PYTHON" -m ensurepip --upgrade` and then pip. If neither
path can install, it fails closed with a named remediation.

## 4. Preflight — installed `ce doctor --json`

After bootstrap, run the governed-environment guard preflight through the
installed script:

```bash
CE_VALIDATOR_PYTHON="${CE_VALIDATOR_PYTHON:-.venv/bin/python}"
.venv/bin/ce doctor --repo-root . --venv .venv --json
```

The installed `ce doctor` evaluates DP-3 plus the target controller/seat env and
exits **non-zero** on any refused clause:

| Clause | Refusal |
|---|---|
| RED-G-1 | out-of-contract interpreter (not `>=3.14` / 3.14.x) |
| RED-G-2 | missing tmux for a visibility-required launch (PCO-049) |
| RED-G-3 | missing rootless Podman, or rootful Podman, for worker execution (PCO-045) |
| RED-G-4 | ungoverned `.hermes/` state-path posture (not git-ignored) |
| RED-G-5 | unsafe hidden continuation (no visible pane / dead-pane) |
| RED-G-6 | dependency wheelhouse drift from the Option B contract |
| CE-SEAT-ENV | target app package not importable or `ce`/`cev3` scripts missing |

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
.venv/bin/ce launch --json
# `hud` is an alias/seam label for the same launcher:
.venv/bin/ce hud --json
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
