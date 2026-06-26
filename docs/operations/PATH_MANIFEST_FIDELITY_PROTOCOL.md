# Path Manifest Fidelity Protocol

**Status**: Workflow-hardening normative protocol. Part of the
**minimum repo-native delivery control plane** and **not a Jira
clone**. Layered onto, and subordinate to, the Feature 001 substrate
and the Feature 002 operating model. A fresh clone is sufficient to
apply this protocol; no external tracker credential or network state
is required.

## a. Purpose

Every governed batch is scoped by an **exact, closed** set of paths
the consumer is permitted to create or update (see
[`../delivery/ASSIGNMENT_ENVELOPE_TEMPLATE.md`](../delivery/ASSIGNMENT_ENVELOPE_TEMPLATE.md)
§c.5). The scope is meaningful only if every party — the Source
ratifier, the controller, the architect, and the implementer — agrees
on **the same** set of paths. Drift between the parties' views of the
manifest is a substrate-corruption pathway with two well-attested
failure modes:

1. **Markdown / paste-pipeline corruption** of paths such as
   `validators/creator_engine_validator/checks/__init__.py` arriving
   as `validators/creator_engine_validator/checks/init.py`. <!-- path_manifest_fidelity: pedagogical -->
2. **Silent off-by-one** in the number of paths (a duplicated path, a
   stripped blank line, an interpolated extra path inside a fenced
   block).

This protocol makes one operational fact answerable from a fresh
clone:

> Given an envelope or handoff that names an authorized path manifest,
> are the manifest's normalized count and SHA256 the same as the
> consumer / verifier independently recomputes from the document on
> disk?

A mismatch is a halt under any envelope. The verifier-side check is
implemented in
`validators/creator_engine_validator/checks/path_manifest_fidelity.py`.

## b. Source-of-truth relationship

| Upstream source of truth | Role |
|---|---|
| [`./NO_COPY_PASTE_PATTERN.md`](./NO_COPY_PASTE_PATTERN.md) | Pointer-only relay shape; the manifest never travels through a paste pipeline. |
| [`./CONTROLLER_BOUNDARY_POLICY.md`](./CONTROLLER_BOUNDARY_POLICY.md) | Controller / implementer split; both run this protocol against the same on-disk file. |
| [`../delivery/ASSIGNMENT_ENVELOPE_TEMPLATE.md`](../delivery/ASSIGNMENT_ENVELOPE_TEMPLATE.md) §c.5 | Allowed-paths field shape inside the envelope; the closed-set semantics. |
| [`../delivery/ENVELOPE_CONSUMPTION_CHECKLIST.md`](../delivery/ENVELOPE_CONSUMPTION_CHECKLIST.md) §c, §d | Consumer-side preflight; the manifest-fidelity check belongs here before any mutation. |
| [`../delivery/SCOPE_AUDIT_CHECKLIST.md`](../delivery/SCOPE_AUDIT_CHECKLIST.md) §c | Verifier-side scope audit; the verifier recomputes the manifest after the stop line and compares it to the diff. |
| `validators/creator_engine_validator/checks/path_manifest_fidelity.py` | The validator implementation. |
| `docs/delivery/RISK_REGISTER.md` R-012 | Path-manifest / Markdown corruption as a standing risk. |

## c. The fidelity protocol

An envelope or handoff that names an authorized path manifest MUST
provide three pieces of evidence side by side, in this order:

1. A declaration line of the shape

   ```text
   AUTHORIZED_PATHS_COUNT=<integer>
   ```

   stating the number of unique, normalized path lines in the
   manifest. Other manifest names are permitted (e.g.,
   `ALLOWED_CREATE_PATHS_COUNT`, `ALLOWED_UPDATE_PATHS_COUNT`); the
   validator parses any `*_PATHS_COUNT=` line that precedes a
   manifest block.

2. A declaration line of the shape

   ```text
   AUTHORIZED_PATHS_SHA256=<64 lowercase hex chars>
   ```

   stating the SHA256 of the normalized manifest. The matching name
   shape applies (e.g., `ALLOWED_CREATE_PATHS_SHA256=`).

3. The manifest itself, as a fenced ```` ```text ```` block whose
   body is one repo-relative path per non-empty line. The fenced
   block MUST follow the declarations and MUST be the first such
   block to follow.

A normalized manifest is computed by:

1. Splitting the fenced body on `\n`.
2. Dropping empty lines.
3. Deduplicating by exact byte match.
4. Sorting ascending lexicographically.
5. Joining with `\n` and appending exactly one trailing `\n`.
6. Encoding as UTF-8.

The normalized **count** is the length of the deduplicated, sorted
list. The normalized **SHA256** is the SHA256 of the normalized
manifest's UTF-8 bytes.

A duplicate path in the fenced block is permitted under this
normalization (it does not change count or hash), but the document
authoring convention SHOULD be deduplicated and sorted at write time
so the human reading matches the validator's recomputed view.

## d. Preflight: where it runs

The protocol MUST be applied at each of the following gates:

| Gate | Actor | Result on mismatch |
|---|---|---|
| Envelope / handoff publication | Author (controller or architect) computes the count/hash from their own draft and embeds them in the document before sending the pointer-only relay. | Halt; recompute and amend the document on disk before relaying. |
| Implementer-pane handoff consumption | Implementer recomputes count/hash from the on-disk document immediately on receipt, before any tool edits a tracked file. | Halt with "BLOCKED — manifest preflight mismatch"; do not edit. |
| Tracked-file authoring | Implementer keeps the manifest open and edits only paths in the normalized set. | Editing a path outside the set is a halt. |
| Controller scope audit | Controller recomputes count/hash from the on-disk document **and** compares the union of the implementer's diff + untracked files to the normalized manifest. | Halt; route any out-of-manifest path back to implementer or escalate to Source per [`./CONTROLLER_BOUNDARY_POLICY.md`](./CONTROLLER_BOUNDARY_POLICY.md) §d. |
| Mechanics (staging / commit / push / PR / merge) | Controller re-verifies count/hash and the diff-vs-manifest equivalence one final time. | Halt mechanics; resolve before any commit lands. |

## e. Error classes

The `path_manifest_fidelity` check emits explicit error codes the
verifier and the controller use to disambiguate failures:

| Code | Meaning |
|---|---|
| `path_manifest_count_mismatch` | The declared `*_PATHS_COUNT` does not equal the unique line count of the fenced manifest. |
| `path_manifest_hash_mismatch` | The declared `*_PATHS_SHA256` does not equal the recomputed SHA256 of the normalized manifest. |
| `path_manifest_missing_declaration` | The document contains a fenced manifest block but no `*_PATHS_COUNT=` or `*_PATHS_SHA256=` line that precedes it. |
| `path_manifest_missing_block` | A `*_PATHS_COUNT=` or `*_PATHS_SHA256=` declaration is present but no fenced manifest block follows. |
| `path_manifest_init_py_corruption` | A fenced manifest line, or a free-text path reference in the document body, is the literal string `<package>/checks/init.py`. This is the regression class motivated by [`./NO_COPY_PASTE_PATTERN.md`](./NO_COPY_PASTE_PATTERN.md) §i; the validator emits this code whether or not the count/hash also fail. |
| `path_manifest_carrier_required` | CI required-mode (`--require-carrier`) found no added `.ce/pr-manifests/<branch-slug>.md` carrier in `<base>..HEAD`. |
| `path_manifest_changelog_required` | CI required-mode (`--require-carrier`) found no added `.ce/changelog/<branch-slug>.md` fragment in `<base>..HEAD`. |

`path_manifest_init_py_corruption` is intentionally emitted at the
ERROR level even when the declared count/hash happen to match, because
the corrupted path is observable evidence that a paste pipeline
collapsed `__init__.py` into `init.py` and the recovered envelope is
not safe to author against.

## f. Recomputation command shapes

The canonical reference command is the one embedded in the handoff /
envelope so that the implementer can reproduce it verbatim:

```bash
python3 - <<'PY'
from pathlib import Path
import hashlib
text = Path('<absolute-path-to-handoff-on-disk>').read_text()
start = text.index('```text\n', text.index('AUTHORIZED_PATHS_SHA256=')) + len('```text\n')
end = text.index('```', start)
paths = [line for line in text[start:end].splitlines() if line]
norm = '\n'.join(sorted(set(paths))) + '\n'
print('count=', len(paths), sep='')
print('unique_count=', len(set(paths)), sep='')
print('sha256=', hashlib.sha256(norm.encode('utf-8')).hexdigest(), sep='')
PY
```

The Creator Engine validator's `scan-path-manifest` CLI subcommand
performs the same computation and emits any of the §e error classes
that apply.

## g. Final boundary verification

After authoring, the controller runs a **final boundary verification**
before any mechanics. The verification compares the union of changed
tracked files (`git diff --name-only`) and untracked, non-ignored
files (`git ls-files --others --exclude-standard`) against the
normalized manifest. Equality is the success condition; any extra
path or any missing path is a halt. The verification computes the
sorted-set SHA256 of the actual file list and compares it to the
manifest's SHA256, providing a single hash the controller can quote in
the report-back.

This last step is what makes the manifest a **closed** scope rather
than a polite suggestion: the report-back's hash equals the envelope's
hash if and only if the implementer authored exactly the manifest.

## h. PR-diff gate mode (`verify-path-manifest --base`) — v3

As of the v3 kickoff the **real** scope-containment mechanism is a
**PR-diff gate**, not author-time enforcement. The author-time
PreToolUse manifest enforcement (the in-band hook bridge in
`validators/creator_engine_validator/hook_check.py`) is now **advisory**:
a governed path-manifest mismatch yields an *allow-with-warning*, not a
hard deny, so the substrate no longer deadlocks a governed author who
must touch a path the manifest did not anticipate. **The secret-path and
dangerous-mechanic denies remain HARD** — only the *manifest* outcome was
relaxed.

Scope containment instead moves to where it can be enforced without
blocking authoring: the **PR diff**. The check
`path_manifest_fidelity.run_with_base(paths, base, manifest)` (reachable
via the CLI subcommand `verify-path-manifest`) compares the set of paths
changed between `<base>..HEAD` (`git diff --name-only`) to the ratified
manifest path-set loaded from a **PR-carried manifest document**:

```bash
# Per-PR carrier mode (the standard for gate PRs):
PYTHONPATH=validators python -m creator_engine_validator \
  verify-path-manifest --base <PR base sha> \
  --manifest-dir .ce/pr-manifests --head-ref <PR head branch>

# CI required-mode, used by Validate:
PYTHONPATH=validators python -m creator_engine_validator \
  verify-path-manifest --base <PR base sha> \
  --manifest-dir .ce/pr-manifests --head-ref <PR head branch> \
  --require-carrier

# Single-doc mode (ad-hoc / local verification of one carrier):
PYTHONPATH=validators python -m creator_engine_validator \
  verify-path-manifest --base <PR base sha> [--manifest <path-manifest doc>]
```

`--manifest` and `--manifest-dir` are **mutually exclusive**, and
`--manifest-dir` **requires** `--head-ref`. `--require-carrier` is the
CI posture: it is used by the required Validate workflow and turns absent
governance carriers into hard failures. When `--require-carrier` is absent,
the verifier keeps its transition-neutral behavior for local and legacy callers.

- **`--manifest-dir` supplied** (per-PR mode) → the gate discovers this PR's
  own carrier from the diff and enforces it:
  - **zero** carrier files under the directory → **NEUTRAL only when
    `--require-carrier` is absent** (a passing `CheckResult`; transition-safe
    for local / legacy callers);
  - **zero** carrier files under the directory with `--require-carrier` →
    `path_manifest_carrier_required`;
  - with `--require-carrier`, the diff must also add
    `.ce/changelog/<branch-slug>.md`; missing or non-added changelog status →
    `path_manifest_changelog_required`;
  - **exactly one**, status **A** (added), filename stem ==
    `branch_slug(<head ref>)` → **active**: the carrier's path-set is enforced
    against the diff with the same `path_manifest_diff_outside_manifest` /
    `path_manifest_unfulfilled_manifest_path` / `path_manifest_diff_no_manifest_paths`
    classes below;
  - **two or more** carrier files in the diff → `path_manifest_multiple_carriers`
    (one PR carries exactly one carrier; every foreign path is reported — this is
    what catches a PR editing a *merged* carrier alongside its own);
  - **slug mismatch** (the single carrier's stem ≠ `branch_slug(<head ref>)`) →
    `path_manifest_carrier_slug_mismatch`;
  - **status M or D** on the PR's own slug (a merged ledger entry being reused
    or tampered) → `path_manifest_carrier_not_added` (merged carriers are
    immutable; a legitimate in-flight re-pin stays status **A** because the file
    does not exist on base until merge);
  - the **retired** shared carrier `.ce/pr-path-manifest.md` may only be
    **deleted** (status D); adding or modifying it → `path_manifest_legacy_carrier_path`.
- **`--manifest` supplied** (single-doc mode) → the gate is active against that
  one document. It flags:
  - `path_manifest_diff_outside_manifest` for each `diff ∖ manifest`
    path (a changed file the closed manifest does not authorize — the
    scope overrun this gate exists to catch); and
  - `path_manifest_unfulfilled_manifest_path` for each `manifest ∖ diff`
    path (a manifest path the PR never changed — an under-delivered
    closed manifest).
  - `path_manifest_diff_no_manifest_paths` when the supplied document
    declares no fenced manifest at all.
- **neither supplied** → the gate is **NEUTRAL** (a passing `CheckResult` with
  no errors). The gate runs as a step of the **required** `Validate governance
  artifacts` status check (which runs both the pytest suite and this diff-gate).
  Validate uses `--require-carrier`, so a pull request cannot pass that required
  check unless `<base>..HEAD` contains both the added per-PR path-manifest
  carrier and the matching added changelog fragment, and the diff equals the
  carrier's closed path-set.

### Per-PR-carrier convention (the standard for gate PRs)

**Every gate PR carries its ratified closed manifest** as its **own** fenced
path-manifest file committed at **`.ce/pr-manifests/<branch-slug>.md`**, where
`<branch-slug>` is `branch_slug(<head branch>)` — a lowercase id of shape
`^[a-z][a-z0-9-]{2,63}$` (`schemas/scope.schema.yaml:58`). The file uses the §c
shape — `AUTHORIZED_PATHS_COUNT=` / `AUTHORIZED_PATHS_SHA256=` + a ```` ```text ````
block listing the authorized paths; **the carrier lists itself**. The CI workflow
(`.github/workflows/validate.yml`) runs the gate on `pull_request` events against
the resolved live comparison base with
`--manifest-dir .ce/pr-manifests --head-ref <head ref> --require-carrier`; a PR
with no added carrier under that directory fails Validate, and a PR without the
matching added `.ce/changelog/<branch-slug>.md` fragment also fails Validate.
Neutral zero-carrier behavior remains available only when `--require-carrier` is
not passed. This **supersedes the single shared
`.ce/pr-path-manifest.md`**: because every PR's carrier has a distinct path, two
concurrently-open PRs never conflict on the carrier file regardless of real
overlap, and merged carriers accumulate as a per-PR scope-audit ledger. The
retired shared path may never reappear (`path_manifest_legacy_carrier_path`).

**Directory rule:** `.ce/pr-manifests/` admits **only** carrier files — no
`README`/index — so discovery never needs an exclusion list. **Branch reuse:** a
merged carrier is an immutable ledger entry; if a new branch normalizes to an
existing carrier's slug, the author renames the branch (the collision is blocked
loudly by the added-not-modified rule, not silently disambiguated). Carrying the
manifest in the PR is what turns the diff-gate from *post-hoc-by-the-Controller*
verification into a *machine-enforced* merge gate (G-iii).

## i. Acceptance posture

This document satisfies the workflow-hardening requirement to enforce
fenced or machine-readable path manifests with normalized counts and
SHA256 hashes:

- Names the fenced-block shape and the declaration lines in §c.
- Names the gates at which preflight runs in §d.
- Enumerates the validator's explicit error classes — including
  `path_manifest_init_py_corruption` — in §e.
- Names the canonical recomputation command shape in §f.
- Names the final controller-side boundary verification in §g.
- Names the v3 PR-diff gate mode + PR-carried-manifest convention, and
  records that author-time PreToolUse manifest enforcement is now
  advisory (secret/mechanic denies remain hard), in §h.
