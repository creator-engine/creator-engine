# Controller Bootstrap Injection Design

**Status**: Draft design for ce-ops#244 follow-up.
**Scope**: Design plus dry-run scaffold only. Applying generated
controller bootstrap is a separate ratified step.

## a. Purpose

Creator Engine controllers currently receive different bootstrap
instructions depending on harness. Codex controllers are grounded by
an injected `AGENTS.md` foreman directive, while Claude-Code
controllers can fall back to a generic `CLAUDE.md` stub and whatever
role definitions happen to exist under `.claude/agents/`. That drift
lets controller behavior become harness-specific even when the CE
governance model is not.

This design defines one tracked source of truth (SSOT),
`docs/design/controller-bootstrap-ssot.json`, that generates preview-only
bootstrap artifacts for both harnesses:

* Claude-Code preview outputs: `CLAUDE.md`, `.claude/agents/` role
  definitions, and a launcher charter.
* Codex preview output: `AGENTS.md`.

The generator MUST NOT overwrite live `CLAUDE.md`, live `AGENTS.md`,
or live `.claude/agents/` files. It emits to stdout and/or a preview
directory only. Promotion from preview into live harness bootstrap is
separate, Source-ratified work.

## b. Non-goals

* No mutation of live harness bootstrap files.
* No runtime controller launch, pane launch, worktree allocation,
  credential issuance, network policy application, or container
  execution.
* No change to spec005 role enums, Slice 2I safety defaults, PCO
  records, validators, or runtime policy machinery. This
  design-plus-scaffold slice may add a preview generator and changelog
  entry, but it does not install generated bootstrap into live harness
  files.
* No automatic acceptance of generated bootstrap into canonical
  `CLAUDE.md` or `AGENTS.md`.

## c. SSOT Shape

The SSOT is the tracked machine-readable JSON document at
`docs/design/controller-bootstrap-ssot.json`. Its values are stable
enough to render both Claude-Code and Codex bootstrap surfaces without
harness-specific reinterpretation, and JSON keeps the scaffold on the
Python standard library. The initial shape contains these sections.

| Section | Required content |
|---|---|
| `metadata` | SSOT schema version, source issue or arc id, generated-artifact warning text, and ratification status. |
| `canonical_roles` | Canonical Spec005 §d.2 roles: `architect_research`, `implementer`, and `verification`, with aliases, role intent, allowed work, disallowed work, default delegation lane, and expected evidence. |
| `schema_roles` | Harness/schema roles that are not canonical Spec005 roles. Initially this includes `reviewer`, mapped to canonical `verification`. |
| `foreman_directive` | Controller operating doctrine: plan, dispatch, monitor, triage, delegate substantive work, preserve author/reviewer separation, avoid inline implementation. |
| `worker_selection_policy` | Rules for choosing which role receives a task and when to split work across roles. |
| `isolation_boundaries` | Spec005 §d.2 role-shaped policy defaults plus §f safety defaults for mounts, credentials, egress, and engine socket denial. |
| `harness_outputs` | Templates or template references plus output metadata for Claude-Code and Codex preview artifacts. |
| `acceptance_safety_notes` | Preview-only checks and PR-body language required before generated bootstrap can be applied later. |

The SSOT is not itself a runtime policy engine. It is an input to a
preview generator and a human-reviewable contract for future
ratification.

## d. Canonical Vocabulary

The canonical worker-role enum is the spec005 §d.2 enum:
`architect_research`, `implementer`, and `verification`. That enum
remains normative for Slice 2I policy records and for controller
bootstrap language.

Current vocabulary drift is reconciled as follows.

| Canonical role | Codex bootstrap term | Claude role-definition term | Notes |
|---|---|---|---|
| `architect_research` | `explorer` | architect/research or explorer-style role definition | `explorer` approximates `architect_research`: it frames, reads, researches, reproduces, and reports, but does not own source mutation. The canonical name remains `architect_research`. |
| `implementer` | `implementer` | implementer role definition | Owns scoped source edits and implementation evidence under a delegated envelope. |
| `verification` | `reviewer` when performing read-only review; verifier when replaying checks | reviewer/verifier role definition | `verification` remains the canonical role. Reviewer is a harness-facing schema role or task mode used for read-only review and grading, mapped to `verification`; it is not a fourth canonical Spec005 role. |

The SSOT should include aliases so generated text can speak naturally
to each harness without changing the underlying role identity. For
example, Codex may say "dispatch an explorer worker" while embedding
the canonical mapping `explorer -> architect_research`. Claude-Code
may render `.claude/agents/explorer.md` if that is the local role
file name, but the generated file must state that the canonical role
is `architect_research`.

Reviewer vocabulary needs special handling. Codex names an
`explorer/implementer/reviewer` trio for practical delegation. Spec005
names `architect_research/implementer/verification` as the normative
worker-container role enum. The tracked SSOT therefore models
`reviewer` under `schema_roles` as a harness-facing review
specialization mapped to canonical `verification`, while preserving
`verification` as the canonical role for policy, isolation, and
evidence. Generated `.claude/agents/reviewer.md` may use frontmatter
`name: reviewer`, but its body and description must state that
canonical role `verification` supplies the Spec005 §d.2/§f boundary.

## e. Foreman Directive

The generated controller bootstrap should carry the same foreman
doctrine for every harness:

1. The controller plans, dispatches, monitors, triages, and routes
   work. It does not perform substantive implementation or review
   inline when worker fan-out is available.
2. Substantive code-writing, tracked source mutation, feature build
   work, full PR review, reproduction, and verification are delegated
   to governed workers with an explicit role.
3. The controller preserves author/reviewer separation. The worker
   that authored a change must not be the worker that supplies the
   external review verdict for that same change.
4. The controller treats harness files as generated bootstrap only
   after ratification. Until then, generated artifacts are previews.
5. The controller respects worktree ownership, does not revert other
   workers' edits, and does not touch files outside the delegated
   scope.

Harness-specific prose may differ, but these semantics must not.

## f. Worker Selection Policy

The SSOT should encode a deterministic selection policy that each
harness renders in its own idiom.

| Task shape | Default role | Selection notes |
|---|---|---|
| Problem framing, spec reading, dependency research, reproduction planning, branch reconnaissance | `architect_research` | Codex may render this as `explorer`. Mounts remain read-only by default. |
| Scoped implementation, tracked source edits, fixture updates, docs edits under ownership, focused tests for authored changes | `implementer` | Requires a delegated envelope and write access only to the allocated worktree paths. |
| Read-only PR review, acceptance grading, test replay, CI log review, evidence validation | `verification` | Codex may render this as `reviewer`; verification remains distinct from exploration even when both are read-heavy. |
| Mixed build plus review work | split between `implementer` and `verification` | Author and reviewer must be distinct workers or distinct governed seats. |
| High-risk unclear work | start with `architect_research` | Escalate to implementer only after scope and acceptance are concrete. |

The policy should prefer the least-authority role that can complete
the task. It should also make role escalation explicit: an
`architect_research` worker can recommend implementation, but it does
not silently become an implementer; a controller must dispatch the
implementation role with the proper envelope.

## g. Isolation Boundaries

The SSOT must embed or reference spec005 §d.2 and §f boundaries so
bootstrap text does not train controllers to over-grant workers.

### g.1 Role-Shaped Defaults

| Canonical role | Mount default | Egress default | Credential default |
|---|---|---|---|
| `architect_research` | Read-only allocated worktree, tmpfs scratch, read-only governance tree. | Model-provider hosts, ratified documentation/web domains, and source-host read API. | Model-provider key by name; no write token, no SSH key, no controller key. |
| `implementer` | Read-write on exactly one allocated worktree, tmpfs scratch, read-only governance tree. | Model-provider hosts, ratified dependency registries, and source-host write API for the one granted branch. | Model-provider key by name and per-task scoped PAT or GitHub App token with claim-lifetime TTL; no SSH key, no controller key. |
| `verification` | Read-only allocated worktree, tmpfs scratch, read-only governance tree, writable build-output tmpfs. | None by default, or a ratified dependency-registry-only allowlist when cached dependencies are not viable. | None by default. Tests should not require internet or model-provider access. |

### g.2 Safety Floor

Generated bootstrap must preserve these safety defaults:

* Mounts default to read-only. Any read-write mount requires explicit
  per-path declaration and justification.
* Host home directories are never mounted. This includes `~/.ssh/`,
  `~/.gnupg/`, `~/.aws/`, `~/.config/gh/`, `~/.claude/`, Codex
  config, browser cookies, shell rc files, and shell history.
* Credentials are withheld by default. Only named, scoped,
  time-bounded credentials may be injected by the host-side broker.
* The Slice 2.5 controller-key private key is never injected into a
  worker. Workers do not sign leases.
* Docker, Podman, and equivalent container-engine sockets are never
  mounted into worker containers.
* Network egress is role-specific and enforced before model or tool
  network I/O.
* Secret values never appear in generated records, logs, manifests,
  bootstrap text, or preview output.

These are bootstrap instructions, not runtime enforcement. Runtime
enforcement belongs to the separately ratified Slice 2I-R machinery.

## h. Generator Behavior

The preview generator should read the SSOT and render deterministic
files into one of two safe destinations:

* stdout, with file boundaries clearly marked; or
* a preview directory such as `tmp/controller-bootstrap-preview/` or
  another ignored/generated path chosen by the implementation.

The generator must refuse any destination that resolves to live
bootstrap paths:

* `CLAUDE.md`
* `AGENTS.md`
* `.claude/agents/*`

The generator should also:

1. Stamp each generated artifact as preview-only.
2. Include the SSOT version and hash or path in every artifact.
3. Be deterministic for identical SSOT input.
4. Validate required SSOT sections before rendering.
5. Fail closed on unknown canonical roles or unknown harness output
   kinds.
6. Support a dry-run command suitable for CI or local review.
7. Avoid reading secrets, provider configs, host home directories, or
   live credential stores.

The generator can later grow schema validation, but the initial
follow-up should keep the important invariant simple: generated
bootstrap is inspectable and non-destructive.

## i. Per-Harness Outputs

### i.1 Claude-Code

The Claude-Code preview bundle should contain:

* `CLAUDE.md`: controller bootstrap with the foreman directive,
  delegation doctrine, scope/ownership rules, and preview-only
  warning.
* `.claude/agents/<role>.md`: role definitions generated from the
  canonical taxonomy and alias map. If the file names use
  harness-friendly aliases such as `explorer.md` or `reviewer.md`,
  each file must state the canonical role it maps to.
* Launcher charter: the controller launch-time charter that binds the
  visible controller session to the SSOT-generated doctrine and names
  the generated preview bundle.

Claude-Code role definitions must include Claude agent-definition
frontmatter with at least `name`, `description`, and a role-appropriate
`tools` allowlist. The frontmatter is still preview-only output and
must not grant authority beyond the role taxonomy. Role bodies should
describe the role, allowed work, prohibited work, credential/mount/egress
expectations, evidence expectations, and when to hand back to the
controller.

### i.2 Codex

The Codex preview bundle should contain:

* `AGENTS.md`: controller bootstrap with the foreman directive,
  worker-selection policy, role vocabulary mapping, and preview-only
  warning.

Codex-specific wording may continue to use `explorer`, `implementer`,
and `reviewer` where that is the natural harness idiom, but the file
must include the canonical mapping and must preserve `verification` as
the canonical role behind reviewer/verifier work.

## j. Acceptance and Safety Notes

A design-plus-preview implementation should be accepted only when:

* The SSOT exists at `docs/design/controller-bootstrap-ssot.json` and
  contains role taxonomy, foreman directive,
  worker-selection policy, harness output definitions, and spec005
  §d.2/§f boundary references.
* Preview generation is dry-run-able without touching live
  `CLAUDE.md`, `AGENTS.md`, or `.claude/agents/`.
* Generated artifacts contain visible preview-only warnings.
* Generated artifacts reconcile role vocabulary drift and preserve
  the canonical `architect_research`, `implementer`, `verification`
  enum.
* Generated reviewer artifacts state that `reviewer` is a
  schema/harness review specialization mapped to canonical
  `verification`, not a fourth canonical Spec005 role.
* Generated Claude `.claude/agents/<role>.md` previews include
  agent-definition frontmatter with `name`, `description`, and a
  role-appropriate `tools` allowlist.
* Checks include the touched-file validator expected by the project
  and `git diff --check`.

The PR body for any implementation PR must explicitly state:

> This PR generates preview-only controller bootstrap artifacts.
> Applying generated bootstrap to live `CLAUDE.md`, `AGENTS.md`, or
> `.claude/agents/` is separate ratified work.

That statement is part of the safety boundary. Review should treat
any live bootstrap overwrite in the design/scaffold PR as a scope
violation.
