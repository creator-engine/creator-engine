# Creator Engine Validator

Offline, repository-local validator for the Creator Engine governance substrate,
and the home of the v1.0 `ce` command-line runtime (`ce` is a second console
script on this same distribution — DP-1 = A, no rename).

## Language and packaging contract (Option B)

- **Python `>=3.14`** (floor and target 3.14.x); `ce doctor` refuses an
  out-of-contract interpreter.
- **uv-first** offline install with a **pip `--no-index` fallback**.
- `validators/uv.lock` is the primary lockfile; `validators/requirements.txt`
  is the lockstep `uv export`-derived fallback.
- Runtime dependencies are pinned at **PyYAML 6.0.3** and **jsonschema 4.26.0**.
- The checked-in `validators/wheelhouse/` is a **cp314**, x86-64 offline
  wheelhouse with a `SHA256SUMS` manifest. The `uvx` one-line operator install
  is POST-V1 (B3); the v1.0 install surface is a source checkout.

## Offline runtime install

From a fresh clone, install only the validator runtime dependencies from the
checked-in cp314 wheelhouse, with no network access.

**uv-first (primary):**

```bash
uv venv --python 3.14
UV_PYTHON_DOWNLOADS=never uv pip install --no-index --find-links validators/wheelhouse creator-engine-validator
```

**pip fallback:**

```bash
python3.14 -m venv .venv
source .venv/bin/activate
pip install --no-index --find-links validators/wheelhouse -r validators/requirements.txt
```

The validator must not call external services during installation from `validators/wheelhouse/` or during validation. Runtime installs intentionally do not include pytest or other test-only dependencies.

## Offline dev/test install

To run the validator test suite from a fresh clone without network access, install the runtime and test-only dependency sets from their separate checked-in wheelhouses:

```bash
python -m venv .venv-test
source .venv-test/bin/activate
pip install --no-index \
  --find-links validators/wheelhouse \
  --find-links validators/wheelhouse-dev \
  -r validators/requirements.txt \
  -r validators/requirements-dev.txt
PYTHONPATH=validators python -m pytest validators/tests -q
```

`validators/requirements-dev.txt` and `validators/wheelhouse-dev/` are for developer/test tooling only. Keep `validators/requirements.txt` and `validators/wheelhouse/` runtime-only.

### Sanctioned test invocations

Parallelism is opt-in per invocation (there is no `addopts`), so choose the lane
that matches what you are doing. `PYTHONPATH=validators` is required for every form,
and every form runs the interpreter `${CE_VALIDATOR_PYTHON:-python}` (see
**Validator-Python (`CE_VALIDATOR_PYTHON`)** below — this keeps the commands correct
in isolated worktrees that have no local `.venv`).

```bash
# 1. Full suite, serial — minimal environment, no xdist needed.
PYTHONPATH=validators "${CE_VALIDATOR_PYTHON:-python}" -m pytest validators/tests -q

# 2. Full suite, parallel — THE merge-green gate. CI runs this with
#    CE_VALIDATOR_PYTHON unset, so by default it is the CI-identical invocation.
PYTHONPATH=validators "${CE_VALIDATOR_PYTHON:-python}" -m pytest validators/tests -q -n auto --dist loadgroup

# 3. Fast lane — inner loop only: deselects the memoized `check-examples` sweep
#    (its consumers carry the auto-applied `sweep` marker), cutting the wall-time
#    floor. Use while iterating on an unrelated unit.
PYTHONPATH=validators "${CE_VALIDATOR_PYTHON:-python}" -m pytest validators/tests -q -n auto --dist loadgroup -m "not sweep"
```

#### Validator-Python (`CE_VALIDATOR_PYTHON`)

Every sanctioned command runs the interpreter `${CE_VALIDATOR_PYTHON:-python}` — the
`CE_VALIDATOR_PYTHON` environment variable when set, otherwise `python` (the active
interpreter). This keeps the documented commands portable to **isolated git
worktrees** (CE lane worktrees under `ce-worktrees/*`), which contain tracked source
but **no local `.venv`**: `.venv/` is gitignored and lives only in the canonical
checkout, so a hardcoded worktree-relative `.venv/bin/python` fails there
(creator-engine#82). When a lane runs in a worktree with no active venv, point
`CE_VALIDATOR_PYTHON` at a known interpreter — e.g. the canonical checkout's venv
(an absolute path):

```bash
export CE_VALIDATOR_PYTHON=/path/to/canonical-checkout/.venv/bin/python
PYTHONPATH=validators "${CE_VALIDATOR_PYTHON:-python}" -m pytest validators/tests -q
```

Do not hardcode a worktree-relative `.venv/bin/python` in lane prompts, templates, or
docs; use `${CE_VALIDATOR_PYTHON:-python}` so the command holds whether or not the
worktree has its own venv. A regression guard
(`validators/tests/unit/test_lane_venv_assumption.py`) enforces this.

The `sweep` marker is derived automatically at collection time from every test that
requests the session-scoped `check_examples_result` fixture — there is no
hand-maintained list to drift. **The fast lane (`-m "not sweep"`) is NEVER valid
green-gate evidence**: it skips the example-sweep coverage on purpose. Only the
full-suite parallel run (form 2) is a green-gate result; CI runs exactly that.

## Invocation

```bash
python -m creator_engine_validator --list-checks
python -m creator_engine_validator check examples/well-formed/
python -m creator_engine_validator check-examples
python -m creator_engine_validator scan-no-limitless
python -m creator_engine_validator scan-pane-registry examples/well-formed/pane-registry
python -m creator_engine_validator scan-side-effect-ledger examples/well-formed/side-effect-ledger
echo '{"hook_event_name":"PreToolUse","tool_name":"Edit","tool_input":{"file_path":"README.md"},"ce":{"posture":"governed","manifest_paths":["schemas/x.yaml"]}}' \
  | python -m creator_engine_validator hook-check --stdin
```

## Exit codes

- `0`: all enabled checks passed.
- `1`: at least one validation failure.
- `2`: invocation error.

Each validation failure cites the violated FR or contract clause, the specific field/path, and the contract document to consult.

## Pane Registry

The `pane_registry` check validates PCO Slice 3 Pane Registry records:

- `PCO-046` schema validation for `kind: pane-registry-record`, `record_type: pane_identity`, schema version, controller/lane/claim/host/pane identity, role/status, `record_timestamp`, `registered_at`, `last_seen_at`, visibility, terminal identity, and protocol-declared optional fields.
- `PCO-047` identifier format constraints for controller, lane, claim, host, and pane identifiers; host and pane ids must not encode secret, durable account, model, or provider authority.
- `PCO-048` role/status enum and terminal lifecycle requirements, including `starting` and `closed`/`aborted` records requiring `closed_at` plus `close_reason`.
- `PCO-049` operator-visible compliance: only `terminal.kind: tmux` with `session_id`, `window_id`, and `pane_id` satisfies the contract.
- `PCO-050` live pane records must bind to a live unreleased Active-Work Ledger claim with matching controller and lane.
- `PCO-051` duplicate active panes for the same `(claim_ref, role)` are refused while transitional and terminal history is allowed.
- `PCO-052` optional `container_instance_id` / `container_instance_ref` bindings must resolve to a matching `container-instance-record` whose claim context matches the Pane Registry claim context.
- `PCO-053` unknown fields are refused.

## Claude hook bridge (`hook-check`, CC-G-B)

`creator_engine_validator hook-check` is the Ring 2 (VALIDATOR) bridge that a
future Ring 1 Claude `command`-type hook-pack (CC-G-C) calls in-band. It reads
a single Claude hook event as JSON (`--stdin` or `--input-json <path>`) and
emits a machine-readable allow/deny/block decision so that real-time enforcement
and post-hoc verification never diverge. The decision logic is **reused** from
the existing validator surfaces — it is not a parallel shell-only policy engine:

- **Posture** (`docs/operations/CLAUDE_CODE_CONTROLLER_SEAT_CONTRACT.md` §7) is
  resolved via `checks.pane_registry.evaluate_posture`: governed iff a live
  `terminal.kind: tmux` pane binds to a live unreleased Active-Work claim with
  matching controller/lane; ambiguous-inside-a-lane fails **closed** (governed);
  otherwise ungoverned (advisory/allow, but still reports what would be denied).
- **Scope** (`Edit`/`Write`/`MultiEdit`): tracked paths outside the ratified
  manifest are denied under governed posture. The manifest is parsed by
  `checks.path_manifest_fidelity.extract_manifest_paths` from the active
  handoff's fenced `ALLOWED_PATHS` block; `.hermes/**` writes are allowed only
  under the gate's `--evidence-root`.
- **Mechanics** (`Bash`): `git push`, `gh pr merge/review/comment`, branch
  deletion, force push, package publish, and live Integration-Queue commands are
  denied unless the event carries an explicit (future) side-effect authority
  token. Mappable verbs anchor to `checks.mutation_class.RESERVED_RESTRICTED`.
- **Secrets** (`Read`): `.env`, `.env.*`, `secrets/**`, private keys/certs, and
  credential stores are denied. Decision reasons name the matched rule class and
  never read or echo secret bytes.
- **Stop / completion**: a `Stop` event whose closeout lacks the canonical
  terminal sections (`Summary`, `Recommended immediate next step`, the next
  Source pointer/SHA **or** an explicit no-next-gate statement) blocks; a
  referenced completion-report artifact that fails `completion_report_schema` /
  `completion_report_required_for_envelope` blocks.

By default (`--format raw`) the CLI emits the full CC-G-B decision dict. An
evaluated allow/deny/block exits `0` (a denial is a decision, not a CLI
failure); only invalid input or arguments exit non-zero.

### `--format claude` presentation seam (CC-G-C)

`hook-check --format {raw,claude}` (default `raw`) selects the output shape.
`--format claude` is an **additive presentation seam** — it changes no decision
semantics — that renders the minimal Claude Code hook output the committed
hook-pack passes through verbatim:

- **PreToolUse** → `{"hookSpecificOutput": {"hookEventName": "PreToolUse",
  "permissionDecision": "deny"|"allow", "permissionDecisionReason": …}}`. An
  ungoverned *advisory* deny maps to `permissionDecision: "allow"` (an
  ungoverned lane is never hard-denied), with the advisory context kept in the
  reason.
- **Stop** block → `{"decision": "block", "reason": …}`; a Stop allow/advisory
  emits no `decision` key.

`--format raw` (the default) is byte-for-byte backward-compatible with CC-G-B;
`HookDecision.to_claude_hook_dict()` backs the `claude` shape.

## Claude hook-pack (`.claude/`, CC-G-C)

CC-G-C ships the committed Ring 1 hook-pack that calls this bridge in-band:
`.claude/settings.json` (PreToolUse for `Edit|Write|MultiEdit|Read|Bash` plus an
advisory Stop hook) and the POSIX-sh wrappers `.claude/hooks/ce-hook-common.sh`,
`ce-pretooluse.sh`, and `ce-stop.sh`. The wrappers fail open by contract and the
Stop hook is advisory/observability-only in v1.0. The pack is **RUNTIME
(launch-pinned) and defeasible — not HARD**; the HARD floor and the Stop
arming/`--setting-sources` pinning are the Ring 0 kernel's job (CC-G-D). See
[`docs/operations/CLAUDE_CODE_HOOK_PACK.md`](../docs/operations/CLAUDE_CODE_HOOK_PACK.md)
and the three-ring model in
[`docs/operations/CLAUDE_CODE_CONTROLLER_SEAT_CONTRACT.md`](../docs/operations/CLAUDE_CODE_CONTROLLER_SEAT_CONTRACT.md)
(§8).

## Side-Effect Ledger

The `side_effect_ledger` check validates PCO Slice 4 Side-Effect Ledger records:

- `PCO-055` strict schema validation for `kind: side-effect-ledger-record`, `record_type: side_effect`, schema version, controller/lane/claim/effect identity, timestamps, summary, and protocol-declared optional references.
- `PCO-056` every scanned record must bind to a discovered Active-Work Ledger claim with matching controller and lane.
- `PCO-057` `effect_id` must be unique within `(controller_id, lane_id, UTC day)` based on `occurred_at`.
- `PCO-058` `effect_kind` and `effect_status` must match the protocol enums.
- `PCO-059` records refuse obvious secret-bearing fields and secret-shaped payloads; use redaction-safe references instead.
- `PCO-060` optional `pane_ref`, when resolvable, must match controller, lane, and claim context.
- `PCO-061` optional `completion_report_ref`, when resolvable, must match controller/lane context and hash-match `completion_report_sha256` when supplied.
- `PCO-062` `integration_queue_ref` is reserved before Slice 6; unresolved refs emit a clear deferred warning, while resolvable records are checked for matching context when they carry context fields.
- `PCO-063` unknown fields are refused and `*.tmp.*` side-effect artifacts are skipped.

### `ce ledger` runtime (RV1-040/041/042)

The `ce` kernel exposes the append-only Side-Effect Ledger runtime that writes
and verifies records validated by the `side_effect_ledger` check above. Records
are deterministic stdlib-JSON bytes grouped by `controller_id/lane_id/<UTC-day>/`
with a per-lane hash chain (`sequence` + `previous_record_sha256`) and a
`_head.json` manifest. It adds no dependency and performs no GitHub/git/CI/
deploy/provider/MCP/plugin/container/network mutation, no pane spawn, and no
automatic observation. See `docs/operations/SIDE_EFFECT_LEDGER_PROTOCOL.md` §11.

```bash
# Append one redaction-safe record bound to a live Active-Work Ledger claim.
ce ledger record \
  --controller-id hermes-primary --lane-id pco-slice4-impl \
  --claim-ref claims/hermes-primary/pco-slice4-impl.yaml \
  --effect-id effect-tracked-file-change-001 \
  --effect-kind tracked_file_change --effect-status succeeded \
  --summary "Created a schema file." --occurred-at 2026-05-25T12:10:00Z \
  --repo-root . \
  --side-effect-ledger-root .hermes/side-effect-ledger \
  --active-work-ledger-root .hermes/active-work-ledger

# Validate the hash chain + claim binding and emit a deterministic replay summary.
ce ledger verify \
  --side-effect-ledger-root .hermes/side-effect-ledger \
  --active-work-ledger-root .hermes/active-work-ledger --json
```

`ce ledger record` refuses — before any write, leaving no partial record/head —
on secret-shaped fields, non-object `--details-json`, a missing/invalid/
mismatched/released claim, or a filename collision. `ce ledger verify` exits
non-zero on schema violations, a broken `previous_record_sha256` link, a
sequence gap (tampered or deleted record), head/manifest drift, or an unbound
claim when `--active-work-ledger-root` is supplied.

### `ce worker` runtime (RV1-050..054; Slice 2I-R)

The `ce` kernel exposes the worker isolation runtime that turns the Slice 2I-S
worker-container substrate into a local rootless-Podman surface. The container
engine and credential broker are reached **only** through injectable seams
(`PodmanCommandRunner`, `NullCredentialBroker`); the live CLI fails closed
(`G5-PODMAN-UNAVAILABLE`) when `podman` is unavailable. It performs no image
build/pull/push, no registry login, and no Podman installation. See
`docs/operations/WORKER_CONTAINER_PROTOCOL.md` §7.

```bash
# Allocate a worker container bound to a live claim + lease under a ratified policy.
ce worker allocate \
  --policy governance/policies/worker-container/podman-implementer.yaml \
  --controller-id hermes-primary --lane-id pco-slice2ir-worker \
  --claim-ref claims/hermes-primary/pco-slice2ir-worker.yaml \
  --lease-ref leases/hermes-primary/pco-slice2ir-worker.yaml \
  --active-work-ledger-root .hermes/active-work-ledger \
  --container-instance-root .hermes/container-instances \
  --instance-id inst-pco-slice2ir-worker-001 \
  --side-effect-ledger-root .hermes/side-effect-ledger --repo-root .

# Revoke broker grants, stop the container, write the stopped record.
ce worker terminate \
  --instance-id inst-pco-slice2ir-worker-001 --claim-id pco-slice2ir-worker \
  --container-instance-root .hermes/container-instances --reason normal_release

# Reap container-instance records that outlived a released claim (PCO-043).
ce worker gc --container-instance-root .hermes/container-instances

# Read a single container-instance record (read-only).
ce worker status --container-instance-root .hermes/container-instances \
  --claim-id pco-slice2ir-worker --instance-id inst-pco-slice2ir-worker-001
```

`ce worker allocate` refuses — before any broker grant, `podman run`, or record
write — on a missing/invalid policy, a controller-key secret name
(`G5-CONTROLLER-KEY-REFUSED`), secret-shaped `--details-json`
(`G5-SECRET-REFUSED`), a missing/released/mismatched claim or lease, a non-empty
`egress_allowlist` with no proven enforcement primitive
(`G5-EGRESS-UNENFORCEABLE`), or absent Podman (`G5-PODMAN-UNAVAILABLE`). Secret
values never enter argv, container-instance records, secret-grant manifests, or
side-effect details (names/grant-ids/TTLs only). The cross-record companion
predicate **PCO-042** (`active_work_ledger_conflicts`) refuses a live claim with
no running container-instance, but only when a `PCO-040`-valid worker-container
policy is present under the ratified governance path
`governance/policies/worker-container/`; trees without such a policy preserve
Slice 2R behavior.

## `role_boundary_attribution` scope and limitations

The `role_boundary_attribution` check (contract: `docs/operations/CONTROLLER_BOUNDARY_POLICY.md`) is a Phase-1 audit aid for R-011 controller-seat-edit pressure. It runs in two distinct modes, and its limitations matter when reading its output:

- **Default whole-tree mode (advisory, not a hard failure).** Invoked through `python -m creator_engine_validator check <paths>` (and `check-examples`). It scans documents whose front matter declares `kind: hermes-handoff` or `kind: hermes-recommended-prompt` and emits *warnings* — never errors — when a `role: controller` document also carries a fenced path manifest. Whole-tree mode is intentionally conservative: it gives the verifier a starting point and MUST NOT be relied on as a hard governance gate. A clean default run does not by itself prove that no boundary breach occurred; conversely, a warning is a signal to investigate, not a CI-blocking error.
- **`verify-attribution --base <commit>` mode (best-effort, fresh-clone limited).** Compares the changed files between `<base>..HEAD` against the active handoff manifests under `.hermes/handoffs/` and emits errors for any changed file not covered by an active handoff. This mode REQUIRES `.hermes/handoffs/` to be present and readable in the worktree. A fresh clone of the upstream public repository does NOT carry `.hermes/` and so this mode is unavailable there; the check emits `role_boundary_no_active_handoff` rather than silently passing. Operators relying on attribution evidence outside of an environment with `.hermes/` populated must use an alternative attribution record.

Both modes are verifier evidence. Neither ratifies a batch.
