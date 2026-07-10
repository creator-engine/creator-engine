# BRIEF — dev-4 — 2026-07-08 — 1 unit: ce-ops#482 host-ops broker v1, Slice 1 (skeleton + `status` + `restart-daemon`)

This is the first implementation slice for the host-ops broker v1 design (ce-ops#482, merged as PR #884, design at `docs/design/host-ops-broker-v1.md`). No prior slice exists. Role: **implementer**. You are a COMMIT-ONLY contained seat: when preflight is green, signal `READY ce-482-broker-v1-slice1 <commit-sha> .ce/pr-manifests/ce-482-broker-v1-slice1.md` in the pane. If blocked, signal `BLOCKED ce-482-broker-v1-slice1 <one-line reason>`. Worktree: `git fetch origin main` first, then create a fresh worktree at `/var/tmp/ce-482-broker-v1-slice1` from `origin/main`. Do NOT activate any venv.

## U1 — branch `ce-482-broker-v1-slice1` (declare work class honestly; likely story or feature)

CONTEXT (ce-ops#482 — ticket unreachable from seat; summary embedded): The host-ops broker v1 design ratified and merged as `docs/design/host-ops-broker-v1.md` specifies a narrow systemd-supervised host-side daemon that exposes a static set of convergent repair verbs to controllers and workers, replacing raw container-runtime socket reachability with a constrained local API. The core model is: one request envelope, one response envelope, one audit path shared by all verbs, a broker-wide kill switch, per-verb disable flags, per-caller-per-target rate limits, and nine typed verbs with fixed schemas — no passthrough, no shell, no arbitrary command. The transport and caller-auth mechanism and the ratified allow-list values for production CE-owned unit names, daemon names, state roots, and container labels are designated Open Operator Questions in the design and remain unresolved; Slice 1 must not block on them.

GOAL: Implement Slice 1. The design contains no explicit phase markers, so the controller has defined the slice boundary as follows.

**SLICE 1 — IN SCOPE:**

New Python package `tools/host-ops-broker/host_ops_broker/` (pure stdlib only; do not add any third-party dependency without recording the gap in the evidence file). Suggested internal module layout:
- `__init__.py`
- `envelope.py` — request envelope validation and response envelope construction
- `verb_schema.py` — typed parameter schemas for every one of the nine design verbs (validation only; no host calls)
- `audit.py` — append-only JSONL audit sink, secret-free (see HARD INVARIANTS)
- `kill_switch.py` — broker-wide kill switch and per-verb disable flag reader; fails closed on unreadable config
- `rate_limit.py` — per-caller-identity per-target bucket accounting using the rate-limit defaults from the design's rate-limit table; injectable for tests
- `config.py` — `BrokerConfig` dataclass loaded fail-closed from a config file; fields covering CE-owned unit allow-list or prefixes, CE-owned daemon map, state-root prefix list, container namespace list, backup profile list, kill-switch path, and per-verb rate-limit overrides; tests use stubs with minimal valid values, no live host config needed
- `broker.py` — main dispatch function: accepts a raw dict, validates the request envelope, checks broker-wide kill switch and per-verb disable flag, resolves target against the CE-owned allow-list from `BrokerConfig` (fail-closed on unknown target), enforces rate limit, dispatches to the verb handler, emits pre-mutation audit (fail-closed before mutation) and final audit, returns response envelope
- `verbs/__init__.py`
- `verbs/status.py` — full `status` verb implementation; all host-subsystem calls behind an injectable `StatusAdapter` interface so tests run without live systemd, container runtime, or OpenBao; returns `degraded` naming the classes it could not inspect when the adapter raises; read-only
- `verbs/restart_daemon.py` — full `restart-daemon` verb implementation; resolves `daemon` against the CE-owned daemon map from `BrokerConfig` (refused if unknown); calls an injectable `SystemdAdapter` interface for pre-state query, restart, post-state query, and ready-wait; enforces `wait_ready_seconds` bound (0–120); returns `already-converged` for `try-restart` on an inactive daemon

Unit tests in `validators/tests/unit/` (one module per concern):
- `test_host_ops_broker_envelope.py` — schema `ce.host_ops.request.v1` accepted; unknown/extra/command-like fields rejected; RFC 3339 UTC `Z`-terminated timestamp enforcement; missing required fields rejected; response envelope covers all result classes
- `test_host_ops_broker_verb_schema.py` — valid params accepted and invalid/extra/command-like params rejected for every one of the nine verb param schemas (schema matrix: all nine verbs, even for the seven deferred verbs whose handlers are not implemented in this slice)
- `test_host_ops_broker_audit.py` — append-only JSONL write; credential-by-name key rejection (forbidden key substrings); token-shaped value rejection; `params_redacted` contains only non-secret fields; clock is injectable; `started_at`/`finished_at` are RFC 3339 UTC with trailing `Z`; missing parent directory is created; never truncates
- `test_host_ops_broker_kill_switch.py` — broker-wide kill switch returns `disabled` for every verb including `status`; per-verb disable leaves other verbs available; unreadable flag file fails closed as broker-wide disabled; every disabled invocation emits an audit record with `result=disabled`, `disabled_scope`, `disabled_reason_ref`; kill-switch check precedes rate-limit accounting
- `test_host_ops_broker_rate_limit.py` — accepted, refused, and rate-limited requests; rate-limit check precedes mutation; rate-limited result emits audit without host state change; per-caller-per-target bucket isolation; clock injection for determinism; defaults match the design table
- `test_host_ops_broker_verb_status.py` — valid `include` variants; optional `target` resolution against allow-list; `detail` levels; `degraded` result naming failed classes when adapter raises; read-only (no state changes); audit emits `include`, `target`, `detail`, `health_summary`, `degraded_checks`, `result`; rate-limit honored
- `test_host_ops_broker_verb_restart_daemon.py` — unknown daemon is `refused` before adapter is called; valid daemon dispatches to adapter with correct `mode`; `wait_ready_seconds` outside 0–120 is `refused`; `try-restart` on inactive daemon returns `already-converged`; audit emits `daemon`, `unit`, `mode`, `pre_state`, `post_state`, `wait_ready_seconds`, `changed`, `result`; rate limit at 3 per 15 minutes per daemon; pre-mutation audit fail-closed (adapter not called when audit cannot be written)

Carrier and changelog:
- `.ce/changelog/ce-482-broker-v1-slice1.md`
- `.ce/pr-manifests/ce-482-broker-v1-slice1.md` — carrier slug MUST equal branch name exactly; list every changed file path explicitly; include `- **Declared work class:** <honest assessment>`

**SLICE 1 — OUT OF SCOPE (defer to later slices):**

- Verb handlers for verbs 3–9: `prepare-owned-state-root`, `rotate-attempt-log`, `repair-systemd-unit`, `run-ephemeral-container`, `prune-stopped-owned-containers`, `snapshot-openbao`, `restore-drill-openbao`. Their param schemas MUST be defined and schema-tested; their execution is deferred.
- The systemd unit file (`ce-host-ops-broker.service`), supervised process entry-point, and live `systemd_adapter` / `StatusAdapter` implementations. Slice 1 ships the library; the service wrapper and adapter implementations come in a later slice.
- The local transport and caller-auth mechanism. The design flags this as an Open Operator Question. Slice 1's `broker.py` dispatch function accepts dicts directly; no socket server, no IPC wiring.
- The broker admin utility for toggling kill switches and disable flags out-of-band.
- The host-local janitor for ephemeral-restore-verify scratch cleanup (no `run-ephemeral-container` in Slice 1).
- Ratified production allow-list values for specific CE-owned unit names, daemon names, state-root paths, container labels, and backup profiles. Config schema is in scope; specific production values are not.
- The repeated-failure auto-disable enforcement ("after three failures for the same caller, verb, and target within the configured window, the broker should self-disable that target or verb"). Define the data shape in config and audit; defer enforcement; record the deferral decision in the evidence file.

HARD INVARIANTS (from the design's authority boundary and threat model):

- Broker-wide kill switch and per-verb disable flags MUST be checked before rate-limit accounting and before any mutation. The design makes this ordering explicit; tests must prove it.
- Pre-mutation audit event is mandatory and fail-closed: if it cannot be written, the broker returns `failed` and does NOT invoke the verb handler. Test this path.
- Param schemas MUST reject extra, unknown, or command-like fields for every verb. Specifically: no `command`, `argv`, `script`, `shell`, `environment`, `mount`, `socket`, `exec`, or `pipe` fields are ever accepted in any verb param schema. Adding one is a security boundary violation.
- Audit records are secret-free: credential-by-name keys and token-shaped values are rejected before any write to the JSONL sink. Follow the egress-broker audit pattern at `tools/egress-broker/egress_broker/audit.py` exactly: forbidden key substring list (case-insensitive substring match on key names) and a token-shape regex on values. Do NOT import from `egress_broker`; copy the pattern into `host_ops_broker/audit.py` as its own implementation.
- `params_redacted` in every audit record must contain only non-secret, schema-safe field names and values. No command text, no credential values, no raw log snippets.
- `started_at` and `finished_at` in every audit record and `created_at` in every request envelope MUST be RFC 3339 UTC timestamps with trailing `Z`. The clock must be injectable (accept a `now: Callable[[], datetime] | None = None` parameter) so tests are deterministic.
- The broker config loads fail-closed: a missing file, malformed content, or missing required field is a `BrokerConfigError`, never a silent default.
- No verb handler is invoked before the CE-owned allow-list resolution step. An unknown daemon in `restart-daemon` returns `refused` without calling the adapter.
- Pure stdlib for `host_ops_broker`. Injectable adapters for every host-syscall surface (systemd, runtime, filesystem, OpenBao). Tests must run without any live host services.

TERRITORY NOTE: The egress-broker at `tools/egress-broker/egress_broker/` is the closest structural prior art in this codebase: a host-side Python package with `audit.py`, `config.py`, `policy.py`, and injectable test boundaries. The unit tests for it live in `validators/tests/unit/test_egress_host_broker.py` and sibling modules. Match the same placement pattern for host-ops broker tests. Where `docs/design/host-ops-broker-v1.md` is silent on an implementation detail (for example: exact JSONL field names for the rate-limit store, exact forbidden-key substring list for the audit, exact config file format), choose the conservative fail-closed reading, record the choice in a top-level docstring or in the evidence file, and do not improvise policy without documenting the gap. Do not modify any file in `tools/egress-broker/`, `validators/creator_engine_validator/`, or any existing test module.

EVIDENCE: Carrier slug must equal branch name exactly (`ce-482-broker-v1-slice1`); self-inclusive; honest `- **Declared work class:**` line. Changelog fragment at `.ce/changelog/ce-482-broker-v1-slice1.md`. Evidence summary must include: total test count and count per test module, confirmation that the schema-validation matrix covers all nine verb param schemas by name, confirmation that kill-switch ordering tests pass, audit secret-free coverage note, any design gaps encountered with the conservative resolution chosen, and any Open Operator Question from the design that affected a Slice 1 decision (so the controller can route it).

Standing preflight directive (ce-ops#303): run the FULL local validator preflight (`ce validate-pr --profile contained-seat`, CI-parity) before commit-for-harvest. Do not discover gates via CI.

STOP LINE: no pushes, no PRs, no gate acts, no signing, no approval or merge actions, no files outside the authorized scope below. If the design is too thin on a detail that requires inventing governance policy (not just choosing a conservative default), stop and signal `BLOCKED ce-482-broker-v1-slice1 <one-line reason>` — do not improvise governance semantics.

Authorized paths for this slice (carrier must enumerate every changed file path individually; these are the only files this brief authorizes):

```
tools/host-ops-broker/           (new package root; all new files within are authorized)
validators/tests/unit/test_host_ops_broker_envelope.py
validators/tests/unit/test_host_ops_broker_verb_schema.py
validators/tests/unit/test_host_ops_broker_audit.py
validators/tests/unit/test_host_ops_broker_kill_switch.py
validators/tests/unit/test_host_ops_broker_rate_limit.py
validators/tests/unit/test_host_ops_broker_verb_status.py
validators/tests/unit/test_host_ops_broker_verb_restart_daemon.py
.ce/changelog/ce-482-broker-v1-slice1.md
.ce/pr-manifests/ce-482-broker-v1-slice1.md
```

No other paths. On green preflight emit exactly:

```
READY ce-482-broker-v1-slice1 <commit-sha> .ce/pr-manifests/ce-482-broker-v1-slice1.md
```

If blocked emit:

```
BLOCKED ce-482-broker-v1-slice1 <one-line reason>
```
