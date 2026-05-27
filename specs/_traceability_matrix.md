# Creator Engine v1.0 — Traceability Matrix (`_traceability_matrix.md`)

Gate: **G0 — SDD/TDD bootstrap + repo-state reconciliation** (type: **DOC**).
Authored UTC: 2026-05-24T16:57:03Z.
Controlling roadmap: Option B re-issued definitive roadmap, SHA256
`5a7e5ba74adcaab32c892c3cf793384eec4f121a6991b1bd5bba34a30fd48e13`.
Canonical baseline: live `refs/heads/main` = `36377f8c4caf6817e01d58072062eb5caccc164b`.

Maps the roadmap's requirements **RV1-000..083** to design references, test plans, and the
verification evidence each gate must produce. **Gate-level granularity** is intentional for Gate 0;
each later gate refines its own rows. The chain is **Goal → Requirement → Design → Task → Test → Code
→ Verification evidence**: no requirement without a test plan; no done claim without evidence.

Status legend: **landed** = on live main; **substrate-landed/runtime-pending** = SVC/shapes layer on
main, runtime gap; **pending** = not yet built; **recorded** = captured as a contract/decision in this
spine.

---

## Gate 0 — SDD/TDD bootstrap + repo-state reconciliation (DOC; this gate)

| Req | Requirement | Design ref | Test plan | Evidence | Status |
|---|---|---|---|---|---|
| RV1-000 | SDD spine exists: `specs/_status.md`, `_traceability_matrix.md`, `_assumptions.md` | envelope §5/§6; roadmap §6 G0 | markdown/link lint; spine files present | the three spine files (this gate) | **this gate** |
| RV1-001 | ADR home exists: `docs/adr/ADR-0001-v1-baseline-and-product-form.md` records live-main baseline, local-kernel boundary, DP-1/2/3 locked | roadmap §0–§2; ADR-0001 | lint; `grep` DP locks without hedged wording | ADR-0001 (this gate) | **this gate** |
| RV1-002 | Dirty-branch artifacts each triaged into already-on-main / superseded-by-main / candidate-for-ratified-cherry-pick | prompt §9.2; `_assumptions.md` §2 | every `git status` entry classified once; no git mutation | `_assumptions.md` §2 | **this gate** |
| RV1-003 | Side-Effect Ledger assumption corrected: **substrate built on live main (PCO Slice 4), runtime pending**, distinct from Active-Work Ledger (inverted from "unbuilt") | prompt §9.3; report `21b092fa…`; notes `47910a90…` | `grep` proves substrate-built + runtime-pending + distinct + G4 reconcile/complete | `_assumptions.md` §3 | **this gate** |
| RV1-004 | v1.1 dev-container seam recorded as deferred, not rejected | roadmap §7; prompt §9.5 | `grep` "deferred, not rejected" | `_assumptions.md` §5; ADR-0001 | **this gate** |
| RV1-005 | Option B §2.2 language/packaging contract recorded as the controlling §2.2 contract | roadmap §2.2; Source record `6bd9b87d…`; prompt §9.6 | `grep` floor `>=3.14` / target 3.14.x / cp314 / uv-first / `uv.lock` / PyYAML 6.0.3 / jsonschema 4.26.0; RV1-060 carries Gate 6 scope | `_assumptions.md` §6; ADR-0001; RV1-060 row below | **this gate** |

## Gate 1 — Canonical terminology + product-contract lock (DOC; lint)

| Req | Requirement | Design ref | Test plan | Evidence | Status |
|---|---|---|---|---|---|
| RV1-010 | Canonical terminology lock: `ce`; `ce launch`/`ce hud` alias; lane / lane-launch / Controller seat; **Side-Effect Ledger ≠ Active-Work Ledger** | roadmap §2.3, §4 | lint; `grep` two ledgers distinct; no hedged DP wording | `docs/governance/V1_CANONICAL_TERMINOLOGY.md` | **Gate 1 complete / ready for Source ratification** |
| RV1-011 | Product contract (§2) recorded as tracked governance doc(s) with IN/SEAM/POST-V1 table (§3), incl. Option B §2.2 | roadmap §2, §3 | doc lint; traceability entry | `docs/governance/V1_PRODUCT_CONTRACT.md` (IN/SEAM/POST-V1 table reconciled w/ Gate 0 corrections: live-main baseline; Side-Effect Ledger substrate-landed/runtime-pending) | **Gate 1 complete / ready for Source ratification** |
| RV1-012 | Governed-environment guard predicate (DP-3=B) recorded as requirement + RED test plan (ungoverned host refused) for G6 impl | roadmap §2.7, §3 | RED-case test plan recorded | `docs/governance/V1_GOVERNED_ENVIRONMENT_GUARD_REQUIREMENT.md` (RED-G-1..6; impl deferred to RV1-061/G6) | **Gate 1 complete / ready for Source ratification** |
| RV1-013 | v1.1 dev-container seam recorded as tracked seam contract | roadmap §7 | doc lint | `docs/governance/V1_DEV_CONTAINER_SEAM_CONTRACT.md` (`ce dev shell`/`ce dev run` v1.1/post-v1 seam; deferred not rejected) | **Gate 1 complete / ready for Source ratification** |

## Gate 2 — Controller Runtime Contract + State Boundary (SVC; strict TDD)

| Req | Requirement | Design ref | Test plan | Evidence | Status |
|---|---|---|---|---|---|
| RV1-020 | CRC schema + validator: Controller seat identity, host-local authority boundary, seat↔harness classification (Hermes/Codex/Claude Code `IN`; OpenClaw `SEAM`; hosted/SaaS/GitHub-connector unauthorized) | roadmap §2.1, §2.6; `CONTROLLER_RUNTIME_CONTRACT_PROTOCOL.md` | RED→GREEN: misclassified-hosted-authority (`RV1-020-AUTH`) + secret-value (`RV1-020-SECRET`) refused; well-formed passes | `schemas/controller-runtime-contract.schema.yaml`; `checks/controller_runtime_contract.py`; unit `test_controller_runtime_contract.py` (16) + integration `test_controller_runtime_contract_examples.py` (3); `scan-controller-runtime-contract` CLI | **Gate 2 complete / ready for Source ratification** |
| RV1-021 | State-boundary check: governed writes target only `.hermes/` (ignored), never tracked governance artifacts; config carries secret names/refs only, never values | roadmap §2.5; Feature 001 storage; `STATE_BOUNDARY_PROTOCOL.md` | RED→GREEN: tracked-write-root (`RV1-021-WRITE`) + secret-config-value (`RV1-021-SECRET`) + hermes-not-ignored (`RV1-021-IGNORE`, declared + live `git check-ignore`) refused; well-formed passes | `schemas/state-boundary-contract.schema.yaml`; `checks/state_boundary_contract.py`; unit `test_state_boundary_contract.py` (18) + integration `test_state_boundary_contract_examples.py` (4); `scan-state-boundary-contract` CLI | **Gate 2 complete / ready for Source ratification** |
| RV1-022 | State version/migration record shape defined + validated (`migration_status` enum: not-required/pending/applied/blocked; supported state layout = v1) | roadmap §2.5; `STATE_BOUNDARY_PROTOCOL.md` | RED→GREEN: stale-version (`RV1-022-STALE`) + invalid-status (`RV1-022`) refused; well-formed (current=1) passes | `schemas/state-version-record.schema.yaml`; `checks/state_version_record.py`; unit `test_state_version_record.py` (13) + integration `test_state_version_record_examples.py` (3); `scan-state-version-record` CLI | **Gate 2 complete / ready for Source ratification** |

## Gate 3 — Governed lane-launch primitive `ce lane launch/status/verify/archive` (SVC+RUN; strict TDD)

| Req | Requirement | Design ref | Test plan | Evidence | Status |
|---|---|---|---|---|---|
| RV1-030 | `ce lane launch` spawns/attaches a tmux pane, writes a Pane Registry record bound to a live Active-Work claim (PCO-050), refuses any non-visible surface for a visibility-required role (PCO-049) | roadmap §2.3, §2.6; Pane Registry schema; `GOVERNED_LANE_LAUNCH_PROTOCOL.md` | RED→GREEN: headless/non-tmux (`G3-VISIBILITY-REFUSED`), missing/released/mismatched claim, tmux-unavailable, and conflict-guard refusals leave no pane file; pane record binds the live claim and validates under `pane_registry` | `creator_engine_validator/{ce_cli,lane_runtime,tmux_adapter}.py`; pane record `terminal.kind: tmux`, `visibility: operator_visible`; RED/GREEN/negative logs | **Gate 3 complete / ready for Source ratification** |
| RV1-031 | `ce lane launch` verifies consumed prompt/handoff pointer + SHA before launch; refuses on mismatch | handoff/recommended-prompt schemas; `GOVERNED_LANE_LAUNCH_PROTOCOL.md` | RED→GREEN: prompt-SHA mismatch (`G3-PROMPT-SHA-MISMATCH`) + missing prompt + handoff-SHA mismatch refused before side effects, no pane file | `lane_runtime.launch` byte-level SHA gate; unit `test_lane_runtime.py` / `test_ce_lane_cli.py`; RED/GREEN/negative logs | **Gate 3 complete / ready for Source ratification** |
| RV1-032 | `ce lane verify` checks stop line + completion report; `ce lane archive` hashes the transcript per `TRANSCRIPT_ARCHIVE_PROTOCOL.md`; `ce lane status` reads live state | TRANSCRIPT_ARCHIVE_PROTOCOL.md; `GOVERNED_LANE_LAUNCH_PROTOCOL.md` | RED→GREEN: missing transcript / missing stop line refused; non-ignored archive root inside repo refused; byte-level transcript SHA256 emitted; status reads live record | `lane_runtime.{status,verify}`; `transcript_archive.archive`; unit `test_transcript_archive.py` + integration `test_ce_lane_cli.py` / `test_lane_launch_tmux.py`; RED/GREEN/negative logs | **Gate 3 complete / ready for Source ratification** |

> The **live pane spawn** at G3 requires its own Source ratification beyond the schema/CLI ratification.

## Gate 4 — Side-Effect Ledger substrate + runtime (SVC; strict TDD) — RECONCILED + RUNTIME LANDED (this gate)

| Req | Requirement | Design ref | Test plan | Evidence | As-built status |
|---|---|---|---|---|---|
| RV1-040 | Side-Effect Ledger schema (`schemas/side-effect-ledger.schema.yaml`) + validator check: append-only w/ hash chain; classified by mutation class; redaction enforced | roadmap §2.7, §4; mutation-class schema | RED: secret value / missing class / append tamper / invalid redaction refused → GREEN | schema validation; well-formed/malformed examples; runtime append + hash chain | **substrate reconciled + runtime landed**: landed PCO Slice 4 substrate reused unchanged; schema gains optional backward-compatible `sequence` + `previous_record_sha256` chain fields; `side_effect_ledger_runtime.record` appends a per-lane hash chain (genesis sentinel → `previous_record_sha256` over prior record bytes, `_head.json` manifest, no-overwrite). Protocol doc §11 reconciles the stale "deferred" posture |
| RV1-041 | `ce ledger record` appends a classified entry; `ce ledger verify` validates the hash chain and replays deterministically | roadmap §4; redaction gate | RED → GREEN record→verify→replay | `ce ledger record/verify` + deterministic replay summary | **runtime landed** (this gate): `ce ledger record` + `ce ledger verify` (stdlib `json`, no new dependency); `verify --json` emits a deterministic replay summary (record count, per-chain first/last refs, head SHA256, effect kind/status counts); tamper/deleted-record/head-drift/unbound-claim exit non-zero |
| RV1-042 | Ledger **never** stores secret values; redaction references only | roadmap §2.7 | RED: secret value refused (PCO-059) → GREEN | malformed `secret-payload` example fails; runtime secret refusal leaves no record/head | **substrate-landed + runtime-enforced**: redaction enforced by landed check (PCO-059) and re-enforced by `ce ledger record`, which refuses secret-shaped fields **before any write** (no partial record/head mutation) |

> **G4 reclassification (was flagged in `_assumptions.md` §4) executed this gate:** Gate 4 did **not**
> build from scratch — it reconciled + reused the landed PCO-Slice-4 substrate and completed only the
> remaining runtime (`ce ledger record/verify`). Packaging (`validators/pyproject.toml`), the
> conformance CLI (`cli.py`), and `checks/__init__.py` were **not** modified. The Side-Effect Ledger
> remains **distinct** from the Active-Work Ledger (it answers "what governed side effects occurred?",
> not "who owns this lane?").

## Gate 5 — Worker isolation runtime (Slice 2I-R, rootless Podman + credential broker) (RUN; strict TDD) — RUNTIME LANDED (this gate)

| Req | Requirement | Design ref | Test plan | Evidence | As-built status |
|---|---|---|---|---|---|
| RV1-050 | `ce worker` lifecycle: allocate→start→status→terminate→gc; each Container-Instance bound to one Active-Work claim + one Worktree Lease | roadmap §2.7; `specs/005-…/worker-isolation-runtime.md` §e.1/§e.8/§e.9 | RED → GREEN lifecycle | lifecycle logs; Side-Effect Ledger records | **runtime landed** (this gate): `worker_runtime.{allocate_worker,terminate_worker,garbage_collect_worker}` + `ce worker {allocate,terminate,gc,status}`; allocate binds a live claim **and** live lease, writes a `PCO-041/043/044`-valid Container-Instance record only **after** a successful rootless `podman run --detach`; container-engine reached only via the injectable `PodmanCommandRunner` seam |
| RV1-051 | Policy enforcement (PCO-045 + PCO-042): rootless engine from policy; default-deny mounts; no host-home; **no controller key**; no engine socket; declared egress only; live claim requires a running container | roadmap §2.7; `WORKER_CONTAINER_PROTOCOL.md` | RED: each violation refused → GREEN | refusal logs (no instance/side-effect record left) | **runtime + validator landed**: allocate reuses `PCO-040/045` policy validation and refuses controller-key secret names (`G5-CONTROLLER-KEY-REFUSED`) and non-empty unenforceable egress (`G5-EGRESS-UNENFORCEABLE`) before container start; `PCO-042` (`active_work_ledger_conflicts`, governance-path-armed per §m.1) refuses a live claim with no running container. (The optional `policy_sha == policy_ref.policy_sha` strengthening from handoff §4 was not added — `PCO-046` is already `pane_registry` and the schema+runtime guarantee the equality by construction.) |
| RV1-052 | Host-side per-task credential broker issues scoped short-lived material; **names-only** in records; values never enter ledgers/transcripts/argv | roadmap §2.7; spec §n | RED: value leakage refused → GREEN | broker refusal logs | **runtime landed**: `NullCredentialBroker` seam grants/revokes by `(secret_name, ttl)` returning opaque grant ids only — no value ever handled; secret-grant manifest, instance record, side-effect details, and the `podman` argv carry **names only** (`--secret name,type=…`); secret-shaped `--details-json` is refused before any side effect (`G5-SECRET-REFUSED`); terminate revokes grants **before** the stopped-record write |
| RV1-053 | `garbage_collect_worker` sweeps containers outliving a released claim (PCO-043) | roadmap §2.7; spec §m.2 | RED → GREEN GC | GC report | **runtime landed**: `garbage_collect_worker` (and `ce worker gc`) identifies the `PCO-043` condition (`claim_released_at` set + `stopped_at` null), revokes open grants, force-reaps (`SIGKILL`), and updates each record deterministically (clearing the PCO-043 hit); a healthy running instance is untouched |
| RV1-054 | Every worker start/stop/GC recorded in the Side-Effect Ledger (`effect_kind=container_action`) | roadmap §4; G4 | integration: ledger entry per side effect | ledger records | **runtime landed**: allocate records `container_started` and terminate records `container_stopped` via the landed `side_effect_ledger_runtime.record` when the Side-Effect Ledger + Active-Work Ledger roots are supplied; GC of an already-released claim does not write a misleading record (the live-claim binding guard refuses it) — the reap itself is still persisted |

> The **live container run** at G5 requires its own Source ratification beyond the schema/CLI/runtime
> ratification. Host Podman was absent during this gate; the runtime is unit/integration-tested through
> fake Podman/broker seams and fails closed (`G5-PODMAN-UNAVAILABLE`) on a real host without Podman.

## Gate 6 — Packaging + launcher + agent-native install + governed-environment guard (SVC; strict refusal-TDD)

| Req | Requirement | Design ref | Test plan | Evidence | Status |
|---|---|---|---|---|---|
| RV1-060 | **DP-1=A packaging:** add `ce` console script to `creator-engine-validator`; retain `creator-engine-validator` script; `ce` wraps validator subcommands; no rename. **Also carries Source Option B §2.2:** `requires-python=">=3.14"`; bump `PyYAML==6.0.3` / `jsonschema==4.26.0` (+ transitives); rebuild **cp314, x86-64** offline wheelhouse; introduce **uv-first** install (`uv.lock` + `uv export`-derived `requirements.txt`) w/ **pip/`--no-index` fallback**; `ce doctor` interpreter-contract assertion (floor+target `>=3.14`/3.14.x; refuse out-of-contract interpreter; `UV_PYTHON_DOWNLOADS=never`) | roadmap §2.2, §2.3, §0; Source record `6bd9b87d…` | RED: missing prereq / out-of-contract interpreter (3.13/3.15) refused → GREEN; offline install via **both** uv-first and pip-fallback; `uv.lock` ↔ `requirements.txt` lockstep proof; cp314 wheelhouse manifest | offline-install logs; `ce doctor --json`; wheelhouse manifest | **complete / ready for Source ratification** — pyproject `>=3.14` + PyYAML 6.0.3 / jsonschema 4.26.0; `validators/uv.lock` (primary) + lockstep `requirements.txt`; cp314-only wheelhouse (cp311 replaced) + `SHA256SUMS`; uv-first **and** pip `--no-index` offline installs proven; `uv lock --locked --offline` reproducible; `packaging_runtime.py` + `test_packaging_contract.py` (21); `_status.md` §13 |
| RV1-061 | `ce doctor` preflights host/repo/tooling, reports missing prereqs by name + non-zero exit, runs the **governed-environment guard predicate** (DP-3=B): refuses ungoverned host drift | roadmap §2.4, §2.7 | RED: ungoverned-host posture refused → GREEN | doctor PASS/guard-FAIL logs | **complete / ready for Source ratification** — `environment_guard.py` (RED-G-1..6 pure predicate) + `doctor_runtime.py` (offline detection, `ce doctor --json`, non-zero + named refused clauses); `ce check` wraps the retained validator; `test_environment_guard.py` (13) + `test_ce_doctor_cli.py`/`test_ce_check_cli.py` unit+integration |
| RV1-062 | `ce init` initializes `.hermes/` state dirs idempotently; refuses to overwrite tracked governance artifacts | roadmap §2.5 | RED → GREEN idempotent init | init logs | **complete / ready for Source ratification** — `init_runtime.py` idempotent `.hermes/` state tree + JSON marker; refuses non-git / ungoverned (`.hermes` not ignored) / tracked-artifact overwrite; `test_init_runtime.py` (8) + `test_ce_init_cli.py` unit (5) + integration (1) |
| RV1-063 | **DP-2=B launcher:** `ce launch` (alias `ce hud`) opens/attaches the named tmux session, runs the chosen harness as Controller seat; `--resume` re-attaches; refuses hidden continuation on harness exit/crash/auth-loss. **No CE-native TUI built.** | roadmap §2.6 | RED: hidden launch / dead-pane continuation refused → GREEN launch→status→resume | launch/attach/resume tests | **complete / ready for Source ratification** — `launch_runtime.py` deterministic visible Controller-seat launcher; `ce hud` is `alias_of: launch` (no CE-native TUI); `--dry-run --json` pure/offline, `--resume` attach (missing/dead session refused), hidden/headless continuation refused; `ce lane launch` preserved; `test_launch_runtime.py` (11) + `test_ce_launch_cli.py` unit (8) + integration (4) |
| RV1-064 | Agent-native bootstrap: `docs/operations/AGENT_NATIVE_BOOTSTRAP.md` + `templates/hermes/agent-native-bootstrap.yaml`; preflight via `ce doctor --json`; one-directional authority transfer; blocked-report on failed preflight; follows **uv-first install w/ pip fallback (B1)** | roadmap §2.8 | RED: failed preflight → blocked report; → GREEN bootstrap dry-run | bootstrap dry-run + blocked-report snapshot | **complete / ready for Source ratification** — `AGENT_NATIVE_BOOTSTRAP.md` + `templates/hermes/agent-native-bootstrap.yaml` (safe-loadable); preflight `ce doctor --json`, one-directional authority, `on_failure: blocked-report` (stop), uv-first+pip-fallback offline (`--no-index`), hosted/team/github/daemon/network all `false`; bootstrap-contract tests in `test_ce_doctor_cli.py` integration |

> Source Option B §2.2 ratification at G6 covers: floor `>=3.14`, cp314 wheelhouse, uv-first + `uv.lock`,
> PyYAML 6.0.3 / jsonschema 4.26.0, and the bootstrap authority transfer. **`uvx` one-line install is
> POST-V1 (B3)**, not the v1.0 canonical path.

## Gate 7 — Local read-only evidence fan-in packet (SVC; strict TDD)

| Req | Requirement | Design ref | Test plan | Evidence | Status |
|---|---|---|---|---|---|
| RV1-070 | `ce fanin build` produces a deterministic content-hashed packet under `.hermes/fan-in/` aggregating evidence manifests + Side-Effect Ledger refs; `ce fanin inspect` reads it. New fan-in output authored as **stdlib JSON** (§2.2 format split) | roadmap §2.5, §3 | RED → GREEN deterministic-hash packet | packet hash; no-authority test | **runtime landed** (this gate): new `creator_engine_validator/fanin_runtime.py` + `ce fanin {build,inspect}`; the packet body carries **no wall-clock fields** so identical inputs serialize byte-identically and the content-addressed filename `{packet_id}-{content_hash}.json` is stable (idempotent rebuild proven); evidence is aggregated from `sha256sum`-style manifests + Side-Effect Ledger chain refs via the landed `side_effect_ledger_runtime.verify` seam; `inspect` recomputes the canonical-bytes hash and re-validates shape read-only against `schemas/evidence-fan-in-packet.schema.yaml`. Output is written **only** under the ignored `.hermes/fan-in/` root (read-only `git check-ignore` guard) |
| RV1-071 | Fan-in packet has **no authority**: any attempt to ratify/enqueue/land is refused; stale evidence + missing Source-ratification refs flagged | roadmap §5 | RED: authority attempt / stale / missing-ref / SHA mismatch refused/flagged → GREEN | refusal logs; no live git mutation | **runtime landed** (this gate): `has_authority` is schema-`const false`; `--ratify`/`--enqueue`/`--land` are refusal-only flags (`G7-AUTHORITY-REFUSED`); stale manifest (pinned≠actual `manifest_sha256`, `G7-STALE-EVIDENCE`), entry SHA mismatch/missing file (`G7-SHA-MISMATCH`), missing `source_ratification` (`G7-MISSING-RATIFICATION`), and tampered referenced ledger (`G7-LEDGER-EVIDENCE`) all refuse **fail-closed before any write** (no packet left). No git/GitHub/tracker/CI/deploy/provider mutation — only local reads + a read-only `git check-ignore` |

## Gate 8 — v1.0 docs finalization + reconciliation + delivery rehearsal (Mixed)

| Req | Requirement | Design ref | Test plan | Evidence | Status |
|---|---|---|---|---|---|
| RV1-080 | README/install/operations docs match as-built `ce` inventory (DP-1=A; `ce launch`/`ce hud`; no `ce dev` in v1.0) and the Option B install story (uv-first + pip fallback; Python `>=3.14`; cp314 wheelhouse) | roadmap §2, §3 | docs-vs-CLI consistency check | doc diff | **complete / ready for Source ratification** — `README.md` v1.0 `ce` runtime section documents all ten command groups (`lane`/`ledger`/`worker`/`fanin`/`queue`/`check`/`doctor`/`init`/`launch`/`hud`), states **no `ce dev`** in v1.0, and the Option B install (Python `>=3.14`, uv-first + pip `--no-index` fallback, `uv.lock`/`requirements.txt`, cp314 wheelhouse, PyYAML 6.0.3 / jsonschema 4.26.0); `validators/README.md` carries the full Option B install story; `test_v1_docs_reconciliation.py` derives the as-built inventory from the argparse parser and fails on drift |
| RV1-081 | IN/SEAM/POST-V1 table reconciled vs shipped surface; CE-native HUD + `ce dev shell` documented as POST-V1/v1.1 seams (deferred not rejected); `uvx` one-liner documented POST-V1 (B3) | roadmap §3, §7, §8 | seam-doc checks: no live connector/HUD/`ce dev` registered in v1.0 | reconciled table | **complete / ready for Source ratification** — `docs/governance/V1_PRODUCT_CONTRACT.md` IN/SEAM/POST-V1 table (Gate 1) records `ce dev shell`, `uvx` one-liner, CE-native HUD beyond the tmux launcher, hosted/team/GitHub connector, CE-event, PCL, and distributed identity as deferred-not-rejected / POST-V1 seams, and the Integration Queue as a dry-run `SEAM` with live landing POST-V1; reconciliation re-verified by `test_v1_docs_reconciliation.py`; `ce dev` is not a registered command group |
| RV1-082 | Integration Queue **dry-run** seam contract authored (local serialized landing; **no live landing**); CE-event/PCL/distributed-identity seam stubs recorded | roadmap §8 | seam stub + verify test | seam contracts | **complete / ready for Source ratification** (this gate, strict RED→GREEN): `schemas/integration-queue-dry-run.schema.yaml` (`has_authority` `const false`, `mode` `const dry-run`); `creator_engine_validator/integration_queue_dry_run.py` reconstructs a deterministic content-hashed serialized landing preview from **verified fan-in packet evidence** and refuses live `enqueue`/`land`/`merge` fail-closed before any write (`G8-QUEUE-AUTHORITY-REFUSED`), plus missing-ratification / tampered-evidence / landing-conflict / un-ignored-root refusals; `ce queue dry-run`/`inspect` CLI; CE-event/PCL/distributed-identity recorded as `deferred-not-rejected` seam stubs; well-formed/malformed examples + `test_integration_queue_dry_run_contract.py` (31). Prose contract `docs/operations/INTEGRATION_QUEUE_DRY_RUN.md` |
| RV1-083 | End-to-end rehearsal: fresh clone → offline install (uv-first **and** pip fallback) → `ce doctor` (guard + interpreter contract) → `ce init` → `ce check` → `ce lane launch --dry-run` → `ce worker` smoke → `ce ledger verify` → `ce fanin build` → `ce launch --dry-run`, hashed evidence + clean `git status` | all prior gates | end-to-end rehearsal smoke; no-daemon/no-web/no-GitHub/no-leak checks | rehearsal transcript + hashes | **complete / ready for Source ratification** (this gate): offline install proven **both** uv-first and pip-fallback from the cp314 wheelhouse (the committed G6-era wheel exposes `{lane,ledger,worker,check,doctor,init,launch,hud}`; `ce fanin`/`ce queue` are rehearsed from source as the wheel predates them — wheel rebuild is a pre-ratification packaging step); dry-run-safe pipeline (`ce init`/`check`/`doctor`/`launch --dry-run`/`fanin`/`queue` succeed; `ce lane launch --no-tmux` and `ce worker status` and `ce queue … --land` refuse fail-closed) leaves the tracked tree clean. Evidence archived under ignored `.hermes/rehearsals/<ts>/` (transcript + install logs + clean-status + `SHA256SUMS_REHEARSAL.txt`); reproducible via `test_v1_delivery_rehearsal.py` (9) |

---

## Gate 9 — final packaging + landing-readiness (validator wheel rebuild) (SVC; evidence-first + RED→GREEN)

| Req | Requirement | Design ref | Test plan | Evidence | Status |
|---|---|---|---|---|---|
| RV1-090 | Tracked `creator-engine-validator` wheel in `validators/wheelhouse/` must be built from current source so an **offline** install exposes the full v1.0 `ce` surface incl. `ce fanin` (G7) + `ce queue` (G8) and **no** `ce dev`; preserve Option B (cp314-only, `>=3.14`, PyYAML 6.0.3 / jsonschema 4.26.0, uv-first + pip `--no-index` fallback) | RV1-060; RV1-083 (G8 flagged stale wheel); roadmap §2.2 | RED→GREEN wheel-surface contract test; offline install (uv-first **and** pip-fallback) command-surface proof; cp311=0 preservation | wheel-surface test; offline-install logs; `ce --help`/`fanin`/`queue` proof + `dev` refusal; wheelhouse inventory + `SHA256SUMS` | **complete / ready for Source ratification** (this gate): stale wheel (`60582fba…`, pre-G7 `{lane,ledger,worker}`) rebuilt via `setuptools.build_meta` to `3995d21e…` bundling `{lane,ledger,worker,fanin,queue,check,doctor,init,launch,hud}`, no `ce dev`; `validators/wheelhouse/SHA256SUMS` regenerated; new `test_wheelhouse_built_surface.py` (4) RED on the stale wheel → GREEN after rebuild; fresh-venv offline install proven **both** uv-first (`--no-cache --no-index --reinstall --find-links`) and pip (`--no-cache-dir --no-index --find-links`) — `--no-cache`/`--no-cache-dir` required to defeat the stale cached `0.1.0` wheel; cp314-only preserved (cp311=0, 7 wheels); pyproject/`uv.lock`/`requirements.txt` unchanged; full suite **821** passes; evidence under ignored `.hermes/final-packaging/20260525T113407Z/` (`SHA256SUMS_FINAL_PACKAGING.txt`); `_status.md` §16 |

---

## CC-G-D — Ring 0 Claude Code launcher/kernel (SVC+RUN; strict TDD)

Extends (does not rewrite) the shipped Gate 3 (`ce lane launch`) and Gate 6
(`ce launch`/`ce hud`) launch substrate. **HARD claim is only the Ring 0
launch/accept refusal before side effects**; the committed CC-G-C hook-pack
remains **RUNTIME/DEFEASIBLE** and is not strengthened to HARD here, and hard
Stop blocking is **not** armed (`.claude/hooks/ce-stop.sh` unchanged).

| Req | Requirement | Design ref | Test plan | Evidence | Status |
|---|---|---|---|---|---|
| RV1-CC-D-1 | Ring 0 refuses ungoverned Claude surfaces **before Claude starts**: `--bare` (`CC-D-1`), `-p`/`--print` for a governed authoring lane (`CC-D-2`), `agents`/`--agents` (`CC-D-3`), `--remote-control`/`remoteControlAtStartup` (`CC-D-4`), `settings.local.json` weakening / `--setting-sources` omitting `project` or including `local` (`CC-D-5`), `--dangerously-skip-permissions` without a confirmed hook-pack (`CC-D-6`), uncontrolled/global MCP (`CC-D-7`) | seat contract §5; `environment_guard` pure-predicate pattern | RED→GREEN per-clause unit refusals + per-surface end-to-end CLI sweep; each refuses before any tmux spawn / Pane Registry write | `creator_engine_validator/claude_launch_spec.py`; `tests/unit/test_claude_launch_spec.py` (24); `tests/integration/test_claude_launch_refusal.py` (10) | **CC-G-D complete / ready for Source ratification** |
| RV1-CC-D-2 | Governed command pins `--setting-sources project` + `--strict-mcp-config` + CE-owned `--mcp-config`; hook-pack confirmation validates `.claude/settings.json` parse, PreToolUse/Stop registrations, exec-bit, validator reachability (injectable probe; never launches Claude/network) | seat contract §4/§6 | RED→GREEN builder idempotency + conflict refusal; confirm present/parse/registration/exec/probe fail-closed | `claude_launch_spec.build_governed_claude_command`; `hook_pack_confirm.confirm_hook_pack`; `tests/unit/test_hook_pack_confirm.py` (7) | **CC-G-D complete / ready for Source ratification** |
| RV1-CC-D-3 | Refusals wired into `launch_runtime.launch` (`G6-LAUNCH-CLAUDE-REFUSED`) and `lane_runtime.launch` (`G3-CLAUDE-REFUSED`) before side effects; non-Claude launch/lane behavior unchanged; deterministic closeout pointers injected to `LaunchResult` + ignored sidecar and verified via Ring 2 Stop logic (`lane_runtime.verify_closeout`) **without** arming `ce-stop.sh` | Gate 3/Gate 6 runtimes; `hook_check` Ring 2 decision reuse | RED→GREEN refusal-before-spawn + governed-command pin + non-Claude regression; closeout block/allow/advisory | `launch_runtime.py`, `lane_runtime.py`, `ce_cli.py` (`--claude-arg`/`--mcp-config`/`--completion-report-ref`/`--closeout-file`); `tests/unit/{test_launch_runtime,test_lane_runtime,test_ce_launch_cli}.py` + integration CLI suites | **CC-G-D complete / ready for Source ratification** |

> CC-G-D authors implementation only; the pane-registry record stays schema-clean
> (`schemas/pane-registry.schema.yaml` pins `unevaluatedProperties: false` and is
> outside the CC-G-D allowlist), so governed-Claude audit + closeout pointers ride
> `LaunchResult` and an ignored sidecar rather than the tracked-shape record.

---

## Cross-cutting recorded contracts

- **Two ledgers are distinct primitives** (load-bearing, verification requirement): Active-Work Ledger
  (landed; "who owns this lane?") vs Side-Effect Ledger (substrate landed / runtime pending; "what
  governed side effects occurred?"). Must not be conflated — see `_assumptions.md` §3.
- **Option B §2.2 language/packaging contract** (RV1-005 recorded here; RV1-060 implements at Gate 6):
  Python floor `>=3.14`, target 3.14.x, **cp314-only** wheelhouse, **uv-first** install w/ pip fallback,
  `uv.lock` reproducibility, **PyYAML==6.0.3 / jsonschema==4.26.0**, `uvx` POST-V1. Source-locked; not
  re-decided by Gate 0.
- **Locked product decisions** (recorded; not reopened): DP-1=A, DP-2=B, DP-3=B, v1.1 dev-container seam
  deferred-not-rejected — see ADR-0001.
