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
PYTHONPATH=validators python -m creator_engine_validator \
  verify-path-manifest --base <PR base sha> [--manifest <path-manifest doc>]
```

- **`--manifest` supplied** → the gate is active. It flags:
  - `path_manifest_diff_outside_manifest` for each `diff ∖ manifest`
    path (a changed file the closed manifest does not authorize — the
    scope overrun this gate exists to catch); and
  - `path_manifest_unfulfilled_manifest_path` for each `manifest ∖ diff`
    path (a manifest path the PR never changed — an under-delivered
    closed manifest).
  - `path_manifest_diff_no_manifest_paths` when the supplied document
    declares no fenced manifest at all.
- **`--manifest` omitted** → the gate is **NEUTRAL** (a passing
  `CheckResult` with no errors). This is the transition-safe default:
  non-manifest PRs (e.g. docs-only changes) are not failed. The gate runs
  as a step of the **required** `Validate governance artifacts` status check
  (which runs both the pytest suite and this diff-gate), so a *gate* PR that
  carries its manifest cannot merge with a diff that drifts from it. Wiring
  that required check + the reviewer policy that pins the non-author approver
  is the work of **G-iii** — see `GITHUB_NATIVE_COORDINATION_PROTOCOL.md`.

### PR-carried-manifest convention (the standard for gate PRs)

**Every gate PR carries its ratified closed manifest** as a fenced
path-manifest document committed at **`.ce/pr-path-manifest.md`** (the §c
shape — `AUTHORIZED_PATHS_COUNT=` / `AUTHORIZED_PATHS_SHA256=` + a
```` ```text ```` block listing the authorized paths; the carrier lists
itself). The CI workflow (`.github/workflows/validate.yml`) runs the gate
on `pull_request` events against `github.event.pull_request.base.sha`,
passing `--manifest .ce/pr-path-manifest.md` when that file is present and
running neutral otherwise (so docs-only / non-gate PRs are not failed). This
supersedes the `.hermes/handoffs/`-based author-time enforcement: the
ratified manifest now travels *with the PR*, and the gate that enforces it
runs *on the diff*, where it cannot deadlock the author. Carrying the
manifest in the PR is what turns the diff-gate from *post-hoc-by-the-
Controller* verification into a *machine-enforced* merge gate (G-iii).

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
