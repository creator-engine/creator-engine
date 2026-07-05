# Contract: Plain-Join an Already-CE Repo (E2)

## Purpose

**Plain-join** is the path a *new dev takes to join a repository that is ALREADY
CE-governed* — e.g. a teammate joining `creator-engine/creator-engine`, or
`ce-dev-3`/`ce-dev-4` joining the team-mode milestone. It is deliberately
distinct from **brownfield adoption** (`brownfield-adoption.md`), which takes a
**non-CE** project *into* CE and stays E3-deferred.

The distinction is not cosmetic: adoption mutates a fresh project into CE shape
(installs the validate workflow, sets up protections, captures a baseline);
plain-join finds those governance artifacts already present and simply
**verifies and reconciles** them so the joining dev's local governance is wired
up. Mis-classifying a join as adoption can make install apply refuse a repo that
is already fully CE-governed.

The same single loop stays load-bearing — there is no second installer engine and
no new user knob; the path is **auto-detected**:

```bash
ce install --spec llms-install.md --answers ce-install.answers.yaml --plan
ce install --spec llms-install.md --answers ce-install.answers.yaml --apply
```

## Detection (FAIL-CLOSED)

A repo is treated as already-CE — and therefore routed to plain-join instead of
the brownfield/E3 refuse — **only** when `github.mode == existing` AND every one
of these read-only signals holds (`repo_is_already_ce_governed`):

1. the repo is reachable (`repo_exists`);
2. the CE validate workflow is present at the **pinned digest**
   (`.github/workflows/ce-validate.yml`, verified by the same read the install
   leg uses); AND
3. the **branch-protection reference floor** is present (the CE required checks
   are enforced on the default branch).

Any uncertainty — a missing signal, a digest mismatch, an unreachable repo, or a
driver error — returns **NOT already-CE**, and the caller falls through to the
unchanged brownfield/E3 refuse. Detection **never mutates**: every probe is a
read-only verify. In a build with no live forge driver wired, detection
fails-closed to the E3 refuse (plain-join defers until the live driver exists),
so the path can never silently proceed against a repo it could not actually read.

## Apply legs (idempotent verify / reconcile)

Plain-join reuses the E2 `onboard_apply` leg sequence; the existing-repo legs
become verify/reconcile rather than create:

| Leg | Plain-join behavior |
| --- | --- |
| `github_repo_create` | Detect already-CE → `already_satisfied` (`join_existing_ce_repo`); the repo is **not** re-created. NOT already-CE → `brownfield_deferred` (unchanged). |
| `github_app_install` | Existing installation detected → `already_satisfied`. |
| `github_workflow_install` | Verify the pinned digest is present → `already_satisfied`; the live workflow file is **never overwritten**. |
| `github_branch_protection` | **Reconcile** the live policy: union the live required checks with the CE floor so missing CE checks are **added** and **no existing check is ever removed**. This runs against the live OSS repo — preserving existing checks is a HARD requirement. |
| `workspace_checkout`, `first_project_smoke` | Local, normal. |

Genuine brownfield (`github.mode == existing` **and NOT** already-CE) is
unaffected: it stays E3-deferred and mutates nothing.

## `--plan` / `--apply` parity

`--plan` surfaces the routing decision (`plain_join.route`) so it never promises
brownfield apply-steps for a repo that `--apply` will actually plain-join — and
never claims plain-join for a repo it cannot verify. When the dry-run has no live
forge driver, the already-CE verdict is honestly reported as deferred to the
live apply read (`detection: deferred_to_apply_live_forge_read`).

Refs: `brownfield-adoption.md` · `onboard_apply.repo_is_already_ce_governed`.
