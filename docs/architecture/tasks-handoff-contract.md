# Tasks Handoff Contract

**Status:** Design pass for ce-ops#119. The Operator has ratified this contract
shape. This remains non-runtime design material until a later ratified build
adds validator/runtime enforcement.

## Purpose

`tasks.ce.yml` is the ratified-tasks to worker handoff contract. It turns a
vanilla Spec Kit `tasks.md` task batch into immutable, SHA-bound work packets
that a governed worker seat can consume without re-planning.

The contract closes the current gap between:

- Spec Kit planning, where `tasks.md` is the human-readable task list.
- Existing CE task sidecars, where `tasks.creator-engine.yml` records task-level
  mutation class, permitted actions, and author/approver metadata.
- v3 Scope and Dispatch, where `cev3 scope`, `cev3 ratify`, and `cev3 drive
  --spawn` produce a governed seat mandate, dispatch record, runtime policy, and
  brief.

Today a spawned seat receives a `brief.md` that points to the ratified Scope and
acceptance criteria. The seat still has too much freedom to reinterpret the task
batch. `tasks.ce.yml` makes the WHAT/HOW split explicit:

- **WHAT:** the task goal, done-when, allowed file scope, mutation class,
  permitted actions, validation evidence, ratification binding, and SHA-bound
  task body.
- **HOW:** implementation tactics inside the harness and runtime policy.

The worker may choose HOW to satisfy the task. It must not change WHAT, split the
task into new tasks, add scope, rewrite done-when, or otherwise re-plan.

## Relationship To Existing Artifacts

`tasks.ce.yml` is the only emitted canonical sidecar name. It is already named
in `specs/v2/001-v2-foundation-substrate/spec.md` and
`specs/v2/_crosswalk.yml`.

Legacy `tasks.creator-engine.yml` remains a v1 read-only import alias until v1
EOL. Tooling may transform the legacy name in, but emitters must write only
`tasks.ce.yml`. There is no dual-emit migration window because dual emission
creates two hashable sources of truth and breaks SHA-binding.

The mapping is:

| Existing artifact | Current role | `tasks.ce.yml` relationship |
| --- | --- | --- |
| `spec.md` | vanilla Spec Kit requirements narrative | referenced by `source.spec_ref` |
| `plan.md` | vanilla Spec Kit HOW plan | referenced by `source.plan_ref`; a worker must not re-plan it |
| `tasks.md` | vanilla Spec Kit task list | referenced by `source.tasks_ref`; human-readable source |
| `tasks.creator-engine.yml` | v1 task governance sidecar | read-only import alias / transform-in source; never emitted as canonical |
| Scope record | ratifiable outer work atom | dispatch may target one or more ratified task ids |
| Dispatch record | materialized seat handoff | future field points to `{tasks_ref, task_ids, task_set_sha256}` |
| `brief.md` | seat mandate | future brief includes `do_not_replan` and task SHA-binding preflight |

## Contract Shape

The reference schema is `schemas/tasks.schema.yaml`.

Top-level fields:

- `kind: tasks-handoff`
- `schema_version: "1"`
- `source`: repo-relative pointers to `spec.md`, optional `spec.ce.yml`,
  `plan.md`, optional `plan.ce.yml`, and `tasks.md`.
- `ratification`: value-free Operator/delegated-human binding for the task set.
- `sha_binding`: digest information for the source artifacts and ratified task
  set.
- `tasks`: the immutable task packets workers consume.

Each task entry carries:

- `id`: stable task id, matching a task id in `tasks.md`.
- `goal`: one-sentence WHAT for the worker.
- `done_when`: non-empty testable acceptance criteria for this task.
- `mutation_class`: CE mutation class.
- `permitted_actions`: bounded action vocabulary for this task.
- `scope.allowed_paths`: exact repo-relative paths, or limited globs anchored
  under a named directory. Recursive `**` and root-level bare globs are refused.
- `scope.prohibited_paths`: exact repo-relative refusal paths. Globs are refused.
- `verification.required_commands`: commands the worker must run when applicable.
- `verification.evidence_refs`: evidence files or log refs the worker must
  return.
- `sha_binding.task_spec_sha256`: SHA256 over the canonical task packet, excluding
  its own `sha_binding`.
- `do_not_replan: true`: the worker must implement this task as ratified.
- `harness`: seat/harness requirements and stop conditions.

The contract is value-free. It never carries raw credentials, hostnames, account
ids, installation ids, tokens, or secret values.

## Canonicalization

The future validator must implement this canonicalization exactly.

1. Load YAML with the same safe loader family the validator already uses.
2. For each task, compute `task_spec_sha256` over the task mapping with
   `sha_binding` removed, canonicalized as UTF-8 JSON with sorted keys,
   no insignificant whitespace, and normalized LF line endings.
3. Compute `task_set_sha256` over a sorted list of lines:

   ```text
   <task_id> <task_spec_sha256>\n
   ```

   The sort key is bytewise `task_id`.
4. Compute each `source_artifacts.*_sha256` over the referenced file bytes as
   committed in the same tree.
5. Refuse if any digest field does not match recomputation.

This deliberately avoids a self-referential hash: a task hash never includes its
own `sha_binding`, and the task-set hash includes only ids and task hashes.

## Handoff Lifecycle

1. **Planner generates human tasks.** Spec Kit creates `spec.md`, `plan.md`,
   and `tasks.md`. `tasks.md` is human WHAT with no CE governance metadata.
2. **Controller shapes the governed packet.** The Controller creates or updates
   `tasks.ce.yml` from the ratified task batch. This is judgment, not blind
   automation: the packet records task ids, done-when, allowed files, prohibited
   files, validation commands, mutation class, harness contract, and
   `do_not_replan: true`.
3. **`cev3 tasks bind` materializes and stamps digests.** The deterministic
   binding command reads the shaped `tasks.ce.yml`, validates the schema,
   computes `task_spec_sha256`, `task_set_sha256`, and
   `source_artifacts.*_sha256` per the canonicalization rule, and writes the
   digests back. Humans reproduce digests; they never hand-type them.
4. **Operator ratifies the task set.** The Operator ratifies the resulting
   `sha_binding.task_set_sha256` and source artifact digests. For privileged
   mutation classes, the Operator is the ratifier. Non-privileged delegation is
   allowed only if separately ratified by the authority matrix.
5. **Dispatch assembles from the ratified task set.** A future `cev3 drive` or
   assignment-envelope bridge selects task ids and records the selected
   `{tasks_ref, task_ids, task_set_sha256}` in the dispatch record before spawn.
6. **Worker preflight checks the binding.** Before any mutation, the worker
   harness or Ring-1 guard recomputes the task and source digests. Drift refuses
   the run before work begins.
7. **Worker executes without re-planning.** The worker may edit only the allowed
   paths, run the required validation, and report evidence. It never modifies
   `tasks.md`, `tasks.ce.yml`, the Scope, the plan, or the selected task packet.
8. **Worker stops on mismatch or scope pressure.** If the task is wrong,
   under-scoped, over-scoped, blocked by missing authority, or stale, the worker
   reports `needs_replan` evidence and stops. The Controller/Operator re-plans
   and ratifies a new task set.
9. **Collect folds evidence.** `cev3 collect` or the current evidence sink folds
   completion evidence and records whether the selected task ids were satisfied,
   blocked, or refused due to drift. Surfaces such as Cockpit may render task
   checkbox state derived from evidence without the worker writing task files.

## `do_not_replan` Enforcement

`do_not_replan: true` is not advisory. It means:

- The worker must not alter the selected task's `goal`, `done_when`, mutation
  class, permitted actions, file scope, validation list, or harness contract.
- The worker must not add new task ids or mark unrelated task ids done.
- The worker must not broaden allowed paths or delete prohibited paths.
- The worker must not substitute a different plan, Scope, or task batch.
- The worker must not edit `tasks.md` or `tasks.ce.yml`, including to check off
  completion.
- The worker must not convert a blocked task into a new implementation plan. It
  must stop and report `needs_replan`.

Allowed worker discretion is limited to implementation tactics inside the
ratified file scope and harness/runtime policy. Completion is evidence-only:
the Controller or `cev3 collect` folds worker evidence into CE state, and UI
surfaces render completion from that evidence.

## SHA Drift Detection

Drift detection has three gates:

1. **Controller/validator gate:** `tasks.ce.yml` is schema-valid and digest-valid
   before dispatch.
2. **Dispatch materialization gate:** the dispatch record names `tasks_ref`,
   selected `task_ids`, and the ratified `task_set_sha256`. If the selected task
   set no longer matches disk, materialization refuses.
3. **Worker preflight gate:** the worker recomputes the selected task digests
   before mutation. If any digest differs, the worker exits with a
   `task_sha_drift` refusal and leaves no source mutation.

The future dispatch record extension should be value-free:

```yaml
task_handoff:
  tasks_ref: specs/123-feature/tasks.ce.yml
  task_ids: [T012, T013]
  task_set_sha256: 64hex...
  do_not_replan: true
```

The future brief should render a concise mandate:

```text
You received ratified tasks T012,T013 from specs/123-feature/tasks.ce.yml.
Do not re-plan. If the SHA binding drifts or the task is under-scoped, stop and
report needs_replan.
```

## Harness Contract

Each task entry declares the harness contract the worker must obey:

- `role`: normally `implementer`; reviewer/security/release roles are future
  explicit variants and do not inherit implementer write authority.
- `allowed_harnesses`: `claude`, `codex`, or both.
- `runtime_policy_ref`: optional policy ref that `cev3 drive` must merge or
  enforce.
- `requires_containment`: whether the task requires contained execution.
- `required_validation`: command ids or command strings to run.
- `stop_conditions`: conditions that require halt rather than improvisation.

For Codex, this composes with the `codex_managed_pretooluse` posture in
`schemas/dispatch-record.schema.yaml`: Codex can consume low-risk work or work
with a ratified risk override, while containment remains the backstop for tool
surfaces not covered by Codex PreToolUse.

## Validator Mapping

This design intentionally stops before runtime implementation. The next
ratified build should add a check named `tasks_handoff` with these predicates:

- `VAL-TASKS-HANDOFF-SCHEMA`: schema validation against
  `schemas/tasks.schema.yaml`.
- `VAL-TASKS-HANDOFF-UNIQUE-ID`: ids are unique and non-empty.
- `VAL-TASKS-HANDOFF-SOURCE-EXISTS`: referenced `spec.md`, `plan.md`, and
  `tasks.md` files exist.
- `VAL-TASKS-HANDOFF-SHA-DRIFT`: source artifact, task, or task-set digest does
  not match recomputation.
- `VAL-TASKS-HANDOFF-REPLAN-FORBIDDEN`: every dispatched task has
  `do_not_replan: true`.
- `VAL-TASKS-HANDOFF-SCOPE-EMPTY`: every task has a non-empty allowed path set
  or an explicit `no_file_change: true` declaration.
- `VAL-TASKS-HANDOFF-SCOPE-BREADTH`: allowed globs are breadth-capped. Exact
  paths are preferred; globs must be anchored under a named directory such as
  `src/foo/*.py`; recursive `**`, root-level bare `*`, and globs not anchored
  under a named directory fail. `prohibited_paths` must be exact paths.
- `VAL-TASKS-HANDOFF-AUTHORITY`: privileged mutation classes have an
  Operator-human ratification binding.

Red tests for the implementation:

- A task with `do_not_replan: false` fails.
- A changed `done_when` with stale `task_spec_sha256` fails.
- A changed `tasks.md` with stale `source_artifacts.tasks_sha256` fails.
- A selected dispatch whose `task_set_sha256` no longer matches fails before
  spawn.
- A task with empty `allowed_paths` and no `no_file_change: true` fails.
- A task with `allowed_paths: ['**']` fails
  `VAL-TASKS-HANDOFF-SCOPE-BREADTH`.

Green tests:

- A minimal docs task with one allowed path, one validation command, and correct
  digests passes.
- A no-change research task with `no_file_change: true` and evidence refs passes.
- A legacy `tasks.creator-engine.yml` import can be transformed into a
  `tasks.ce.yml` shape but is not emitted as the new canonical name.
- `allowed_paths: ['src/foo/*.py']` passes
  `VAL-TASKS-HANDOFF-SCOPE-BREADTH`.
- `allowed_paths: ['docs/x.md']` passes
  `VAL-TASKS-HANDOFF-SCOPE-BREADTH`.

## Resolved Decisions

1. **Canonical sidecar name:** emit only `tasks.ce.yml`.
   `tasks.creator-engine.yml` is a read-only import alias until v1 EOL. There is
   no dual-emit window because two emitted sidecars create two hashable sources
   of truth.
2. **Dispatch binding granularity:** bind the full task set; dispatch selects ids
   by reference. `task_set_sha256` is the ratified atom, while per-task hashes
   let workers preflight only selected packets.
3. **Worker task-file mutation:** forbidden. Workers never edit `tasks.md` or
   `tasks.ce.yml`; completion lives in CE evidence and is folded by the
   Controller or `cev3 collect`.
4. **Who emits `tasks.ce.yml`:** three hands. The planner writes human
   `tasks.md`, the Controller shapes the governed packet, and deterministic
   `cev3 tasks bind` materializes, validates, and stamps digests before Operator
   ratification.
5. **Path scope:** limited globs are allowed, breadth-capped. Prefer exact
   paths; allow globs only under a named directory, forbid recursive `**` and
   root-level bare `*`, and require `prohibited_paths` to be exact.
