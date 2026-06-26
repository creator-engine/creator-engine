# Contract: CE Playbook Format

Gate: ce-ops#145
Validator check: `ce_playbook_format`
Schema: `schemas/playbook.schema.yaml`

## Purpose

A CE playbook is a reusable, dispatchable operating procedure stored in-tree
under `playbooks/`. It is not a free-form runbook. Each playbook carries a
human-facing README, a machine-checkable workflow descriptor, a scope/authority
envelope template, governed stage briefs, and a harness contract.

The format is repo-native and PR-mediated. Seats consume playbooks by reading
the index, selecting one playbook directory, validating the scaffold, filling
the envelope template for the ticket, and dispatching only the stage brief that
matches the intended action.

## Required Directory Shape

Every immediate child directory of `playbooks/` is a playbook and MUST contain:

| Path | Rule |
| --- | --- |
| `README.md` | Human summary: what it does, when to use it, DoR preconditions, DoD outputs. |
| `workflow.ce.yml` | Machine-checkable workflow descriptor valid against `schemas/playbook.schema.yaml`. |
| `envelope.template.yml` | Scope/authority envelope skeleton for dispatching work. |
| `briefs/<stage>.md` | One governed dispatch brief for each stage referenced by `workflow.ce.yml`. |
| `harness.md` | Runtime/substrate contract, halt conditions, dead ends, and sunset criteria. |

The top-level `playbooks/README.md` MUST index every playbook directory with a
link to that directory and MUST describe how a seat consumes a playbook.

## `workflow.ce.yml`

The workflow descriptor MUST declare:

- `kind: ce-playbook`
- `schema_version: "1"`
- `playbook.name`, matching the folder name exactly
- `playbook.type`, either `workflow` or `role-action`
- `playbook.owner_issue`, normally `ce-ops#145` for this scaffold
- non-empty `preconditions`, `outputs`, `gates`, and `stages`
- `dispatch.authority_envelope: envelope.template.yml`
- stage `brief` paths in the form `briefs/<stage>.md`

Stages reference gate IDs by name. A stage may not reference a gate that is not
declared in `gates[]`.

For executable playbooks, each `stages[]` entry MAY also include runtime fields:

| Field | Rule |
| --- | --- |
| `description` | Human-readable stage description. |
| `action` | Human-readable governed action to perform when no shell command is declared. |
| `command` | Optional shell command. `ce playbook run` evaluates the command through the CE hook-check governance seam before execution. |
| `expected_result` | Human-readable pass condition surfaced in run output. |

`ce playbook run <name>` resolves playbooks from local `playbooks/` by id or
path. `--dry-run` prints the ordered plan and executes nothing. A live run
executes stages in order, emits `PASS`/`FAIL` for each stage, stops on the first
failed command, and emits a final result. Stages without `command` are treated
as action steps: the runner records the action as acknowledged and does not
spawn a shell.

Public dual-use `PLAYBOOK.md` files are accepted as a frontmatter authoring
layer. Their frontmatter uses the same `id`, `title`, `goal`, `status`, `mode`,
`work_class`, `gates`, `prerequisites`, `steps`, and `expected_outcome` fields
validated by the public playbook runtime. Each `steps[]` entry MUST carry `id`
and `action`; it MAY carry `description`, `command`, and `expected_result`.
The runtime projects those entries into the internal `stages[]` descriptor above
before listing, showing, dry-running, or running.

## Validator Behavior

`ce_playbook_format` scans playbook directories when a path is `playbooks/`, a
repo root containing `playbooks/`, a playbook directory, or a
`workflow.ce.yml` file. It validates:

| Error code | Refusal |
| --- | --- |
| `VAL-PLAYBOOK-REQUIRED-FILE` | Required playbook files or `briefs/` directory are missing, or the workflow does not point to `envelope.template.yml`. |
| `VAL-PLAYBOOK-SCHEMA` | `workflow.ce.yml` fails `schemas/playbook.schema.yaml` or references an undeclared gate. |
| `VAL-PLAYBOOK-NAME` | `playbook.name` does not match the folder name. |
| `VAL-PLAYBOOK-BRIEF` | A stage brief path is malformed or points to a missing file. |
| `VAL-PLAYBOOK-INDEX` | `playbooks/README.md` is missing or does not list every playbook directory. |

The check is shape-only. It does not execute a playbook, approve work, merge,
publish, mutate source-host state, or widen the authority carried by an
envelope.
