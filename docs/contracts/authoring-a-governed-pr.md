# Authoring a Governed PR

This contract defines the local author loop for a Creator Engine governed PR.
The source of truth is the committed PR diff, not the working tree.

## Reportable mechanical preconditions

Before every diff used for commit-for-harvest or PR readiness, run `git fetch
--prune origin`, re-derive the base with `git rev-parse origin/main`, and report
that exact base SHA. Do not reuse a previously observed base for a later diff.

Stage only explicit, authorized paths; `git add -A` is prohibited. Before each
commit, report the exact staged set from `git diff --cached --name-only` and
verify it is the intended closed set. A handoff is ready only when the change is
committed: report the committed `HEAD` and a clean worktree. Cleanliness alone
never substitutes for a committed head.

## Required declaration

Every PR body must contain exactly one declared work class line:

```text
- **Declared work class:** <XS|S|M|L>
```

Before PR readiness, compute and report the work-sizing floor from the committed
diff and report the declared class alongside it. Legacy inputs normalize as
`tiny` → `XS`, `story` → `S`, `feature` → `M`, and `epic` → `L`. A declared
class at or above the computed floor clears this check; a lower declaration must
be raised or the work split.

## Local preflight

Run from the PR worktree:

```bash
scripts/ce-preflight.sh --base origin/main --head-ref "$(git branch --show-current)" --declared-work-class M
```

The command refuses a dirty worktree by default because it validates committed
state only. If you need to inspect committed state while unrelated local files
exist, pass `--allow-dirty`; the diff gates still use `git diff <base>..HEAD`,
never working-tree content.

The preflight resolves the comparison base by fetching the base branch and
using `git merge-base <base> HEAD`; record its derived base SHA. It then runs
the same gate families as
`.github/workflows/validate.yml`:

1. Pytest suite: `python -m pytest -p no:cacheprovider validators/tests/ -m "not wheel_bake_gate" -q -n auto --dist loadgroup`.
   Remedy: fix the failing validator test or dependency fixture. For local parity, pytest runs with `TMPDIR=/var/tmp` and without `GH_TOKEN`, `BAO_TOKEN`, `OPENBAO_TOKEN`, or `CE_OVERWATCH_PAT`.
2. Workflow YAML parse: every `.github/workflows/*.yml` must parse.
   Remedy: fix invalid YAML before pushing.
3. Artifact YAML parse: every YAML file under `schemas/`, `templates/`, `docs/contracts/`, `examples/`, and `playbooks/` must parse.
   Remedy: fix syntax or move non-YAML text out of `.yml`/`.yaml` files.
4. Aggregate examples: `python -m creator_engine_validator check-examples`.
   Remedy: fix the well-formed or malformed example fixture reported by the aggregate examples gate.
5. Well-formed examples: `python -m creator_engine_validator check examples/well-formed/`.
   Remedy: repair examples or the validator contract they exercise.
6. Playbook format: `python -m creator_engine_validator check playbooks/`.
   Remedy: keep playbooks valid for `ce_playbook_format`; do not substitute a narrower scan command.
7. Malformed examples: `python -m creator_engine_validator check examples/malformed/` must fail.
   Remedy: if malformed examples pass, tighten the validator or restore the malformed fixture.
8. Check registry: `python -m creator_engine_validator --list-checks`.
   Remedy: fix import, registration, or packaging defects.
9. Brain drift: `python -m creator_engine_validator.ce_cli brain verify --drift --state-root .ce/state`.
   Remedy: update committed brain state through the governed brain commands or restore the expected state.
10. Work-sizing floor: `python -m creator_engine_validator verify-work-sizing-floor --base <comparison-base> --declared-work-class <class> .`.
   Remedy: raise the declared class or split the PR until the floor is satisfied.
11. Path manifest: `python -m creator_engine_validator verify-path-manifest --base <comparison-base> --manifest-dir .ce/pr-manifests --head-ref <head-ref> --require-carrier`.
    Remedy: regenerate this PR's carrier files from the committed diff; do not hand-edit the path list.
12. Workflow permissions audit: `validate.yml` must not request any `write` permission.
    Remedy: remove write scopes from workflow-level or job-level `permissions`.

The command prints exactly one final summary: `GREEN` when every gate passes or
`FAIL` when any gate fails.

## Two-strikes rule

A failed preflight is strike one. Make the smallest concrete correction and run
the preflight again.

If the same gate fails a second time, stop widening the PR. Either split the PR,
ask for review on the specific gate, or document why the declared work class and
manifest need to change before continuing.

## Carrier discipline

Each PR must add exactly one changelog carrier and one path-manifest carrier for
its branch slug:

```text
.ce/changelog/<branch-slug>.md
.ce/pr-manifests/<branch-slug>.md
```

The branch slug is produced by
`creator_engine_validator.checks.path_manifest_fidelity.branch_slug(head_ref)`;
it converts `/` to `-` as part of canonical normalization. Before commit and
before PR readiness, report the exact branch slug and verify both carrier
filenames exactly match it. For implementation PRs like this lane, the declared work class is normally
`M` unless the committed diff proves a smaller or larger class.

## Manifest-fidelity recipe

`AUTHORIZED_PATHS` must equal the committed `base..HEAD` path set exactly. Once
the PR is committed, that diff includes the PR's own `.ce/changelog/<slug>.md`
and `.ce/pr-manifests/<slug>.md` carrier files. Never hand-edit the fenced list.

Use the public carrier generator so the manifest uses the same canonicalization
as the validator. Preferred:

```python
from creator_engine_validator.carrier_gen import CarrierSpec, write_carriers

written = write_carriers(
    ".",
    CarrierSpec(
        head_ref="your-branch-name",
        base="origin/main",
        issue="ce-ops#<issue>",
        title="Short PR title",
        kind="added",
        scope="validator tooling",
        body="- Describe the governed change.",
        date="YYYY-MM-DD",
    ),
)
print(written.manifest_path)
```

`write_carriers` is the public orchestration that writes the changelog first,
calls `compute_path_set(repo_root, slug, base)` for the `base..HEAD` path set,
and renders the manifest with `render_manifest(...)`. If you need to inspect
the path set before writing, use the same public pieces:

```python
from creator_engine_validator.carrier_gen import compute_path_set, render_manifest
from creator_engine_validator.checks.path_manifest_fidelity import branch_slug

slug = branch_slug("your-branch-name")
paths, count, sha = compute_path_set(".", slug, base="origin/main")
text = render_manifest(
    slug,
    "ce-ops#<issue>",
    "Short PR title",
    paths,
    count,
    sha,
)
```
