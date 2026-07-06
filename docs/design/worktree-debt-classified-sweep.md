# Worktree Debt Classified Sweep Design

Status: design only. This document does not authorize deletion, pruning,
archive mutation, worktree removal, branch deletion, or live host cleanup.

Scope: define a deterministic classified sweep for accumulated CE worktrees and
staging directories, especially `.ce/wt-*` and `/var/tmp/ce-*`, so operators
can distinguish safe cleanup candidates from live claims, unpushed work,
evidence holds, and unknown state.

## Problem

Controller hosts accumulate worktrees, validation bases, review sandboxes,
pytest scratch directories, and manually named `/var/tmp/ce-*` staging roots.
Naive age-based pruning is unsafe because a directory can contain unpushed
commits, active claim or lease evidence, canary state, or validation artifacts
needed to explain an in-flight branch. The sweep must therefore classify first,
publish an operator-visible manifest, and only then perform staged cleanup with
an undo window.

## Goals

- Classify every candidate with deterministic, auditable signals.
- Make dry-run classification the default behavior.
- Produce an operator-visible manifest before any apply step.
- Archive each deletion candidate with a git bundle, plus metadata, before
  removing the filesystem path.
- Preserve unpushed, active, evidence-held, and unknown directories.
- Separate reusable product behavior from operator runbook judgment.

## Non-Goals

- No immediate deletion of any existing worktree or staging directory.
- No branch deletion, remote mutation, PR mutation, or GitHub lookup in the
  first implementation.
- No hidden allowlist based only on directory name or mtime.
- No attempt to prove semantic usefulness of old evidence; the sweep only
  classifies filesystem and git state.

## Candidate Discovery

The first implementation should scan only explicit roots supplied by default
configuration or CLI flags:

| Root | Candidate rule |
|---|---|
| Repo-local worktree debt | `.ce/wt-*`, `.worktrees/*`, and `git worktree list --porcelain` paths under the controller repo root. |
| Host staging debt | `/var/tmp/ce-*` and `/tmp/ce-*` when explicitly enabled for that host profile. |
| Validation scratch | `/tmp/ce-validate-pr-base-*` and equivalent known validator scratch stems. |

Discovery must record whether a path is a Git worktree according to
`git -C <path> rev-parse --is-inside-work-tree` and whether it appears in
`git worktree list --porcelain`. Those are separate signals: a directory can be
a useful staging root without being a registered git worktree.

## Artifact-Only Dirt-Clearing Pass

Before the final safety classification, the sweep should run an artifact-only
dirt-clearing pass. The purpose is not to make a worktree look clean; it is to
remove generated noise that would otherwise mask the real disposition. The
sequence is:

1. Discover candidates and record the pre-clear snapshot.
2. Identify generated or derived artifacts with deterministic signals.
3. Clear only those artifacts, using configured safe commands or path removals.
4. Re-run git/status/stat inspection and classify only what remains dirty.
5. Record both snapshots in the manifest so operators can audit what changed.

A derived artifact is a file or directory that can be recreated from committed
source, declared dependencies, or a documented generator without carrying
reviewable human intent. Deterministic signals include:

- path is under a configured build/cache/test-output location such as
  `build/`, `dist/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`,
  `__pycache__/`, `.coverage`, `htmlcov/`, `node_modules/`, or known validator
  scratch stems like `/tmp/ce-validate-pr-base-*`;
- file is ignored by the repo's own ignore rules and has no explicit evidence
  retention rule;
- file is produced by a command listed in the manifest policy, for example
  test cache, coverage output, generated package metadata, or downloaded
  release-staging payloads;
- file content is reproducible from checked-in inputs or external immutable
  references recorded in metadata;
- path has no active claim, no PR carrier role, no evidence-hold role, and no
  operator-authored marker.

A work product is any file or directory that may contain human-authored intent,
coordination state, review evidence, or unrecoverable host-local facts.
Deterministic signals include:

- tracked source, docs, specs, tests, migrations, or configuration changes;
- untracked files outside configured generated-artifact paths;
- `.ce/changelog/**`, `.ce/pr-manifests/**`, `.ce/state/**`,
  `.ce/claims/**`, `.ce/leases/**`, `.ce/locks/**`, `evidence/**`, `runs/**`,
  `review/**`, or `gate/**`;
- git commits ahead of upstream or `origin/main`;
- files containing operator approval, validation logs, canary output, branch
  disposition, claim ownership, or archive metadata;
- any path whose origin cannot be proven by the derived-artifact policy.

The pass must never delete or rewrite work product. If a dirty candidate
contains both derived artifacts and possible work product, the sweep clears the
derived artifacts first, records the clear operation, and then re-classifies the
remaining state. For example, a pytest scratch directory such as
`/var/tmp/ce-445-g9-pytest.5Qds6m` can be recognized as validator scratch by
files like `started`, `stop`, and `engine-argv.txt`, but this design still keeps
non-git scratch as `unknown` until a retention policy says those files are
discardable. In contrast, a clean registered worktree such as
`/var/tmp/ce-294-press-merge-read` should not need dirt clearing before its
merged-safe check; clearing would be a no-op recorded in the manifest.

The initial implementation should support a dry-run clear report before it
supports apply. A row that becomes clean after artifact clearing may continue to
`merged-safe` only when all other merged-safe requirements hold. A row with
remaining tracked or untracked work product becomes `unpushed-work`,
`evidence-hold`, or `unknown` according to the ordered taxonomy below.

## Classification Taxonomy

Classification is ordered. The first matching class wins, and a candidate that
cannot be inspected cleanly becomes `unknown`.

| Class | Deterministic signals | Sweep action |
|---|---|---|
| `active-claim` | A non-expired claim/lease/lock record exists in known coordination paths such as `.ce/state/**`, `.ce/claims/**`, `.ce/worktree-leases/**`, `.ce/leases/**`, or `.ce/locks/**`; or the path is the current worktree of a running seat recorded in an operator-supplied active-seat inventory; or its branch is the current branch for a registered live worktree. | Never delete automatically. Report owner, branch, mtime, and claim path. |
| `merged-safe` | Git worktree is clean; HEAD is an ancestor of `origin/main` or the configured base; local branch is not ahead of upstream and not ahead of `origin/main`; no active claim signal; no evidence-hold signal; candidate age is older than the configured cool-down. | Eligible for staged deletion only after manifest review, archive, and undo window. |
| `unpushed-work` | Git worktree has commits ahead of upstream or `origin/main`; or no upstream exists and HEAD is not merged to `origin/main`; or `git status --porcelain` reports tracked, untracked, staged, or unstaged changes. | Never delete automatically. Report ahead counts and dirty summary. |
| `evidence-hold` | Candidate contains known evidence, carrier, validation, canary, run, or review artifacts in configured paths, for example `.ce/pr-manifests/**`, `.ce/changelog/**`, `.ce/state/runs/**`, `evidence/**`, `runs/**`, `review/**`, `gate/**`, or validation scratch files, and the evidence retention window has not expired or no owning branch/PR disposition is known. | Never delete automatically until retention policy or operator override reclassifies it. |
| `unknown` | Not a git worktree; git commands fail; branch/upstream cannot be resolved; mtime/stat fails; path is a symlink escaping the allowed roots; permissions prevent complete inspection; signals conflict. | Never delete automatically. Report the failure reason and require manual triage. |

### Signal Details

Git signals:

- `git -C <path> status --porcelain=v1` must be empty for `merged-safe`.
- `git -C <path> rev-list --left-right --count HEAD...@{upstream}` gives
  upstream ahead/behind when an upstream exists.
- `git -C <path> rev-list --left-right --count HEAD...origin/main` gives
  controller-base ahead/behind.
- `git -C <path> merge-base --is-ancestor HEAD origin/main` proves HEAD is
  already reachable from current `origin/main`.
- Detached HEAD can be `merged-safe` only if HEAD is merged, clean, outside the
  evidence window, and not actively claimed.

Claim signals:

- Claim discovery must be path-scoped to known coordination directories. A
  whole-repo filename scan for `*claim*` is too noisy because historical
  changelog and manifest names contain claim-like words.
- A claim is active only when its schema-specific expiry or heartbeat is valid.
  Expired claims are still evidence-hold until the manifest records why they no
  longer block deletion.

Mtime signals:

- mtime is a tie-breaker and retention input, not a deletion proof.
- The default cool-down should be at least seven days after last directory mtime
  and at least one controller cycle after the branch is merged.
- A recent mtime can upgrade a candidate to `evidence-hold` or `unknown`; an old
  mtime cannot downgrade `unpushed-work`.

## Sweep Procedure

1. Classify every candidate and write a JSONL manifest plus a human-readable
   Markdown summary. Each row records path, inode/device, git status, branch,
   HEAD, upstream, ahead counts, merge status, mtime, class, reasons, and
   deletion eligibility.
2. Report the manifest in an operator-visible location before apply. The
   report groups candidates by class and highlights all `unknown` and
   `unpushed-work` entries first.
3. Require an explicit apply step that references the exact manifest hash.
   Apply refuses to run if a fresh classification changes any eligible row.
4. Stage deletion candidates into an undo window. For every `merged-safe`
   candidate selected for cleanup, write a git bundle and metadata record before
   removal:

   ```bash
   git -C <path> bundle create <archive>/<stem>.bundle --all
   git -C <path> status --porcelain=v1 > <archive>/<stem>.status
   git -C <path> rev-parse HEAD > <archive>/<stem>.head
   ```

   Non-git staging directories must be archived with a metadata tarball only
   when a future ratified retention policy allows it. Until then, non-git
   candidates remain `unknown` or `evidence-hold`.
5. Move or remove only after archive verification succeeds. The initial apply
   should prefer move-to-quarantine over `rm -rf`; final deletion occurs after
   the undo window expires.
6. Record apply evidence: manifest hash, archive path, bundle verification
   result, paths moved or removed, operator approval reference, and kill-switch
   state.

## Worktree Lifecycle Rule

Debt should stop accumulating at worktree creation time. Every CE worktree or
host staging root must have a lifecycle record that names the owner, branch or
claim, creation reason, and retirement trigger. Paths without such a record are
allowed for emergency recovery only and immediately classify as `unknown` or
`evidence-hold` until an operator records ownership.

| Stage | Owner | Required record | Exit condition |
|---|---|---|---|
| `created` | dispatching controller or seat foreman | path, branch, claim/ticket, intended base, created_at, creating command, and owner seat | handoff to active owner with claim accepted |
| `owned-active` | implementing or reviewing seat | heartbeat/lease, current branch, PR or claim reference, and expected next action | PR closed, claim released, or work explicitly handed off |
| `validation-hold` | author seat until harvest, then controller/reviewer named in the record | validation artifacts, carrier paths, run IDs, and retention deadline | validation evidence copied to durable location or superseded |
| `retirement-pending` | controller cleanup owner | merged/closed disposition, archive plan, undo-window deadline, and manifest row hash | archive verified and undo window elapsed |
| `retired` | cleanup owner of record | archive path, bundle hash when git-backed, metadata hash, and final action timestamp | no further action; later restoration starts a new lifecycle |

The default retirement trigger for a git-backed worktree is all of:

- claim or ticket is closed or explicitly released;
- associated branch is merged to `origin/main` or otherwise recorded as
  abandoned with no ahead commits requiring preservation;
- validation and review evidence has been copied or its retention window has
  elapsed;
- artifact-only dirt-clearing and re-classification still leave the candidate
  `merged-safe`;
- the configured undo window has elapsed after quarantine/archive verification.

Ownership must be path-scoped. A branch name alone is not enough because the
current host sample shows multiple kinds of roots: branch worktrees such as
`/var/tmp/ce-351-queue-daemon-relocation`, detached validation/read worktrees
such as `/var/tmp/ce-294-press-merge-read`, and non-git scratch such as
`/var/tmp/ce-445-g9-pytest.5Qds6m`. The current repo-local `.ce` tree sampled on
2026-07-06 had no `.ce/wt-*` directories, which is useful evidence but not an
allowlist; lifecycle enforcement still applies when `.ce/wt-*` paths appear.

The `ce worktree sweep --classify` command should report lifecycle gaps as
classification reasons, for example `missing_lifecycle_owner`,
`retirement_trigger_incomplete`, or `undo_window_open`. Apply must refuse a
candidate whose lifecycle owner, branch, claim, archive hash, or retirement
deadline changed since the approved manifest.

## Operator-Visible Manifest

The manifest should be a first-class artifact, not console-only output. The
recommended shape is:

- `.ce/state/worktree-sweeps/<timestamp>/manifest.jsonl`
- `.ce/state/worktree-sweeps/<timestamp>/summary.md`
- `.ce/state/worktree-sweeps/<timestamp>/archives/<stem>.bundle`
- `.ce/state/worktree-sweeps/<timestamp>/archives/<stem>.metadata.json`

Each JSONL row should contain:

```json
{
  "path": "/var/tmp/ce-example",
  "class": "unpushed-work",
  "eligible_for_apply": false,
  "reasons": ["ahead_origin_main=1", "head_merged_to_origin_main=false"],
  "git": {
    "is_worktree": true,
    "registered_worktree": true,
    "branch": "ce-example",
    "head": "0123456789abcdef",
    "upstream": "origin/main",
    "ahead_upstream": 1,
    "behind_upstream": 42,
    "ahead_origin_main": 1,
    "behind_origin_main": 42,
    "dirty_count": 0
  },
  "mtime": "2026-07-02T10:31:42Z"
}
```

## Command Versus Runbook

Productize deterministic mechanics as a `ce` command:

```bash
ce worktree sweep --classify --roots .ce,/var/tmp --output .ce/state/worktree-sweeps
ce worktree sweep --apply --manifest <sha256> --class merged-safe --undo-window 7d
ce worktree sweep --verify-archive <archive-dir>
```

The command should own discovery, classification, manifest rendering, archive
creation, archive verification, quarantine moves, kill-switch checks, and apply
refusal when the manifest is stale.

Keep judgment in the runbook:

- selecting host roots for a given controller;
- deciding retention windows for evidence directories;
- approving the first controller-repo cleanup;
- resolving `unknown`, `active-claim`, and `unpushed-work` rows;
- deciding when fleet hosts are ready for apply rather than classify-only.

## Safety Invariants

- Dry-run classify is the default. Apply requires an explicit flag and an exact
  manifest hash.
- `unpushed-work`, `active-claim`, `evidence-hold`, and `unknown` are never
  deleted automatically.
- A global kill-switch, for example `CE_WORKTREE_SWEEP_DISABLE=1`, makes both
  classify and apply refuse unless an operator-only diagnostic override is used.
- Apply never acts on a path whose class, inode/device, HEAD, dirty count, or
  mtime changed since the approved manifest.
- Archive and verification happen before any move or remove.
- Deletion eligibility is monotonic toward safety: conflicting signals always
  choose the safer class.
- The command must not delete branches or prune Git worktree metadata unless a
  later ratified design explicitly adds that behavior.

## Rollout

1. Controller repo classify-only: run on the controller host, publish manifest,
   and compare classes with operator expectations.
2. Controller repo archive dry-run: create bundles and metadata for a small
   `merged-safe` set without removing paths.
3. Controller repo staged apply: quarantine a tiny approved `merged-safe` set
   with a seven-day undo window.
4. Fleet classify-only: run on fleet hosts with host-local roots and publish
   manifests, but keep apply disabled.
5. Fleet staged apply: enable only after controller-host evidence shows archive,
   restore, and kill-switch behavior working.

## Appendix: Read-Only Sample From Current Host

Sample collected on 2026-07-06 from real `/var/tmp/ce-*` directories. Commands
used read-only git/status/stat inspection after fetching current `origin/main`.
The sample intentionally does not delete, move, or rewrite anything.

| Path | Observed signals | Class |
|---|---|---|
| `/var/tmp/ce-294-press-merge-read` | Detached HEAD `22907983`; clean; `ahead_origin_main=0`, `behind_origin_main=110`; `HEAD` merged to `origin/main`; mtime `2026-07-02 16:58:25Z`. | `merged-safe` candidate, pending evidence-retention review. |
| `/var/tmp/ce-351-queue-daemon-relocation` | Branch `ce-351-queue-daemon-relocation`; clean; upstream `origin/main`; `ahead_origin_main=1`, `behind_origin_main=142`; HEAD not merged; mtime `2026-07-01 06:46:06Z`. | `unpushed-work` |
| `/var/tmp/ce-366-mainhead-resolver-adr` | Branch `ce-366-mainhead-resolver-adr`; clean; `ahead_origin_main=1`, `behind_origin_main=134`; HEAD not merged; mtime `2026-07-02 03:26:56Z`. | `unpushed-work` |
| `/var/tmp/ce-381-automerge-decide-pathset` | Branch `ce-381-automerge-decide-pathset`; clean; `ahead_origin_main=1`, `behind_origin_main=145`; HEAD not merged; mtime `2026-07-01 01:50:14Z`. | `unpushed-work` |
| `/var/tmp/ce-382-brain-drift-local-reconcile` | Branch `ce-382-brain-drift-local-reconcile`; clean; `ahead_origin_main=1`, `behind_origin_main=128`; HEAD not merged; mtime `2026-07-02 05:48:23Z`. | `unpushed-work` |
| `/var/tmp/ce-388-a1` | Branch `ce-388-conveyor-harvest-daemon`; clean; `ahead_origin_main=1`, `behind_origin_main=71`; HEAD not merged; mtime `2026-07-04 15:15:52Z`. | `unpushed-work` |
| `/var/tmp/ce-388-conveyor-redesign-adr` | Branch `ce-388-conveyor-redesign-adr`; clean; `ahead_origin_main=1`, `behind_origin_main=129`; HEAD not merged; mtime `2026-07-02 04:33:27Z`. | `unpushed-work` |
| `/var/tmp/ce-388-payload-data-only` | Branch `ce-388-payload-data-only`; clean; `ahead_origin_main=5`, `behind_origin_main=110`; HEAD not merged; mtime `2026-07-02 10:31:42Z`. | `unpushed-work` |
| `/var/tmp/ce-390-confidentiality-scanner-coverage` | Branch `ce-390-confidentiality-scanner-coverage`; clean; `ahead_origin_main=1`, `behind_origin_main=127`; HEAD not merged; mtime `2026-07-02 06:33:33Z`. | `unpushed-work` |
| `/var/tmp/ce-445-g9-pytest.5Qds6m` | Not a git worktree; contains pytest scratch files such as `fake-queue-daemon`, `started`, `stop`, and `engine-argv.txt`; mtime `2026-07-05 04:40:47Z`. | `unknown` until a retention policy classifies validator scratch. |

The sample also showed noisy filename matches under `.ce/changelog/**` and
`.ce/pr-manifests/**`; those are evidence/carrier signals, not live claim
signals by themselves. Claim detection should therefore inspect known
coordination paths and schema fields rather than broad filename substrings.
