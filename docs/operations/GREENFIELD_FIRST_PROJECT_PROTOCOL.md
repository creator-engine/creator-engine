# Greenfield First-Project Protocol

Status: canonical for ce-ops#53 E4.

This protocol defines the first project path for a new CE user creating a new
repo. It extends the existing onboard journey; it does not create a second
installer, Scope lifecycle, forge coordinator, or apply executor.

## Boundary

Greenfield onboarding is split deliberately:

- E2 `onboard_apply` owns side effects: signed-spec verification, dependency
  convergence, runtime posture, GitHub repo/App/workflow/protection convergence,
  workspace checkout, and the deterministic first-project smoke.
- E4 owns the read model over that result: the first-project payload, the
  Frame->Ship completeness counters, the "bootstrap is not first ship" gate,
  and the review/merge evidence agreement.

E4 reads E2's apply result and leg ledger. It does not recompute E2 counters or
emit a parallel scaffold/repo/App/protection/Actions plan.

## Inventory

The input inventory remains schema-derived from
`schemas/install-answers.schema.yaml`. For `github.mode: new`, the greenfield
rows include:

- `host.workspace_root`
- `project.name` (optional; defaults by projection to the repo basename)
- `project.scaffold.kind` (default `minimal`)
- `github.mode`
- `github.repo`
- `github.new_repo.*`
- `github.bootstrap_token` as a SecretRef
- `github.app.*`
- `github.protections`
- `github.actions.install_validate_workflow`
- `github.reviewer`
- `provider.harness`
- `cost.profile`

Secrets are still references only. Branch-protection weakening still requires
the existing ratified binding.

## Plan Payload

`ce onboard --answers ce-install.answers.yaml --plan --json` adds
`first_project` when the merged answers describe `github.mode: new`:

```json
{
  "mode": "greenfield",
  "project_root": "<workspace-root>/<project-name>",
  "scaffold_input": {
    "kind": "minimal",
    "supplied_to_e2_leg": "workspace_checkout"
  },
  "e2_plan_ref": "onboard.github_leg",
  "e2_apply_result_ref": null,
  "e2_apply_required": true,
  "frame_to_ship": {
    "first_scope_filed": false,
    "first_scope_ratified": false,
    "first_build_spawned": false,
    "first_pr_opened": false,
    "first_review_recorded": false,
    "first_pr_merged": false
  },
  "first_ship_not_yet_counted": true
}
```

The `first_project` block points at E2's GitHub leg and later folds E2's apply
result. It does not list E2's internal legs as a second plan.

## Minimal Scaffold

The only ratified scaffold kind is `minimal`. E4 supplies the content contract to
E2's `workspace_checkout` leg:

- create the local project root
- create `.gitignore` excluding `.ce/state` and transient local tool state
- create `README.md` with neutral starter text
- initialize the configured default branch
- create an initial bootstrap commit only so GitHub has a branch and checks can
  be installed

The scaffold creates no product code, generated app boilerplate, deployment
config, secrets, CI bypass, or protection exception.

## First Scope And First Ship

E2's `first_project_smoke` Scope is deterministic onboarding evidence. It is not
the first governed Scope and it cannot count as first ship.

The E4 first Scope is human-shaped:

1. The user chats freely in Frame.
2. E3 detect-and-offer or explicit `ce scope` drafts a Scope.
3. The user confirms and supplies the human-only Budget.
4. `ce ratify <scope>` places the front-gate bet.
5. `ce drive <scope> --spawn` starts Build.
6. `ce pr ... --apply`, `ce review ... --spawn`, `ce collect ...`, and
   `ce merge ... --apply` carry Review and Ship through existing forge gates.

First ship is counted only when a governed post-scaffold PR is opened through
the forge leg, reviewed in a distinct venue or explicitly waived by a ratified
review-gate waiver, merged through the gated merge path, and represented in the
runtime evidence, manifest evidence, merge evidence, and completion report.

Repo creation, README bootstrap, App installation, CI green, PR open, and review
verdict are not first ship by themselves.
