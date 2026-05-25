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

## 3. Preflight — `ce doctor --json`

The bootstrap **MUST** run the governed-environment guard preflight first:

```bash
ce doctor --json
```

`ce doctor` evaluates the governed-environment guard predicate (DP-3 = B,
`docs/governance/V1_GOVERNED_ENVIRONMENT_GUARD_REQUIREMENT.md`) and exits
**non-zero** on any refused clause:

| Clause | Refusal |
|---|---|
| RED-G-1 | out-of-contract interpreter (not `>=3.14` / 3.14.x) |
| RED-G-2 | missing tmux for a visibility-required launch (PCO-049) |
| RED-G-3 | missing rootless Podman, or rootful Podman, for worker execution (PCO-045) |
| RED-G-4 | ungoverned `.hermes/` state-path posture (not git-ignored) |
| RED-G-5 | unsafe hidden continuation (no visible pane / dead-pane) |
| RED-G-6 | dependency / wheelhouse drift from the Option B contract |

## 4. Blocked-report semantics on failed preflight

If `ce doctor --json` exits non-zero, the bootstrap **MUST**:

1. **Stop** (`preflight.blocked_report.stop: true`). Do not continue.
2. Emit a **blocked report** naming the refused guard clauses from the
   `refused_clauses` array of the JSON output.
3. **Not** ratify any in-flight work and **not** fall back to a hidden/headless
   continuation. There is no hidden fallback.

## 5. Install — uv-first with pip fallback (offline)

The install contract is `uv-first-with-pip-fallback`, **offline** (`--no-index`),
against the **cp314-only** offline wheelhouse. Python floor is `>=3.14`.

uv-first:

```bash
uv pip install --no-index --find-links validators/wheelhouse creator-engine-validator
```

pip fallback (uv-less host):

```bash
python -m pip install --no-index --find-links validators/wheelhouse creator-engine-validator
```

No network fetch occurs at install or runtime authority
(`docs/governance/V1_PRODUCT_CONTRACT.md` §6).

## 6. Launch — visible Controller seat

After a PASS preflight and a successful offline install, the agent enters the
visible Controller seat:

```bash
ce launch --json     # ce hud --json is an alias/seam label for the same launcher
```

`ce launch` opens/attaches a **visible** tmux Controller seat (DP-2 = B). It
refuses hidden/headless continuation; `ce hud` is an **alias**, not a CE-native
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
