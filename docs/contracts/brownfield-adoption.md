# Contract: Brownfield Project Adoption (E3)

> **Not the same as joining an already-CE repo.** Brownfield *adoption* takes a
> **non-CE** project into CE and is E3-deferred. A new dev joining a repo that is
> **already** CE-governed is a *plain-join* (E2, auto-detected) — see
> `plain-join.md` (ce-ops#85). `onboard --apply` auto-detects already-CE and
> routes to plain-join; only an existing repo that is **not** already-CE reaches
> the brownfield/E3 refuse described here.

## Purpose

Brownfield adoption lets `ce onboard` connect CE to an existing project without
forking the installer engine or adding a second apply path. The same loop stays
load-bearing:

```bash
ce onboard --spec llms-install.md --inventory
# prepare ce-install.answers.yaml with the operator
ce onboard --spec llms-install.md --answers ce-install.answers.yaml --plan
ce onboard --spec llms-install.md --answers ce-install.answers.yaml --apply
```

`--inventory` and `--plan` are read-only. They inspect source-controlled project
metadata, produce value-free summaries, and emit an E2 handoff plan. They do not
write files, run scanners, call GitHub mutation APIs, rewrite history, delete
branches, or weaken protections.

## Inventory

The brownfield inputs live in `schemas/install-answers.schema.yaml` under the
single operator inventory as exactly these step-5 rows:

- `brownfield.enabled`
- `brownfield.project_root`
- `brownfield.inventory_depth`
- `brownfield.ci.adopt_existing_workflows`
- `brownfield.ci.required_checks_strategy`
- `brownfield.tests.required_commands`
- `brownfield.history.mode`
- `brownfield.conventions.branch_pattern`
- `brownfield.conventions.commit_style`
- `brownfield.secrets.preflight`
- `brownfield.secrets.waivers`

Detected facts use the existing precedence rule:
`interactive > answers-file > detected > default`. A file value that contradicts
detected reality is a conflict and refuses non-interactive mode until the
operator resolves it.

## Plan

`ce onboard --plan` adds `brownfield_adoption` to the JSON payload. It includes:

- a canonical value-free `inventory_sha256`;
- existing workflows and checks to preserve;
- the CE validate check as an additive check when missing;
- detected test commands, or an empty list when unknown;
- history mode and value-free history summaries;
- advisory branch and commit conventions;
- a secrets-scrub preflight plan;
- a first Scope seed and two project skill artifacts;
- ordered E2 apply step descriptors.

The project skill artifact paths are:

- `.ce/skills/project-conventions.md`
- `.ce/skills/project-validation.md`

The first Scope seed references those paths through `skill_refs` and binds to
the inventory hash. It is a seed only; normal Scope ratification still happens
through the existing Scope flow.

## Refusals

Normal adoption blocks when:

- no Git history is present (`needs_baseline_capture`);
- tracked working-tree changes make the inventory stale (`blocked_dirty_tree`);
- a required secrets scanner is known unavailable;
- scanner findings are unwaived;
- a waiver lacks `{ratified_prompt_sha, approver_ref, educate_acknowledged: true}`;
- detected-vs-file conflicts remain unresolved;
- the plan would drop existing workflows, checks, reviewers, or protections.

No synthetic history is generated. History rewrite, force push, branch deletion,
workflow deletion, check removal, raw secret persistence, and branch-protection
weakening are outside this gate.

## Apply Handoff

Brownfield apply is not implemented as an E3 executor. Apply must run through
E2's `onboard_apply` leg pipeline. The E3 plan describes the legs E2 must run:

1. re-run drift checks against the inventory hash;
2. run the secrets preflight;
3. write project skill artifacts;
4. write or stage the first Scope seed;
5. install the CE validate workflow when missing;
6. apply branch-protection drift without dropping existing checks;
7. verify existing and CE checks remain represented;
8. record value-free apply evidence.

If a current build lacks those E2 brownfield extension legs, `ce onboard --apply`
refuses with `e2_brownfield_seam_unavailable` and returns the planned
`brownfield_adoption` payload for inspection.
