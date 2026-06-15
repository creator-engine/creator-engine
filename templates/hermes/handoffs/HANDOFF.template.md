# Hermes Handoff Template

<!--
This file is the canonical template for a Hermes-authored handoff
relayed pointer-only from a controller pane to an implementer pane.

An instance fills this template into an instance-local file under
`.hermes/handoffs/<UTC-timestamp>-<batch-slug>-<role>.md` and relays
that path (plus its byte-level SHA256) to the implementer pane via
the visible-pane pointer-only prompt in
`templates/hermes/visible-pane-pointer-prompt.template.md`.

The required front matter and §1–§9 below are validated by the
Creator Engine validator's `handoff_schema` check (see
`schemas/handoff.schema.yaml`) and the
`path_manifest_fidelity` check (see
`docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`).

Upstream Creator Engine MUST NOT track an instance's filled-in copy.
Keep `.hermes/` ignored. Do not commit live PR numbers, absolute
local paths, runtime pane identifiers, or instance-specific
secrets / tokens.

See also:
  - `docs/operations/CONTROLLER_BOUNDARY_POLICY.md`
  - `docs/operations/NO_COPY_PASTE_PATTERN.md`
  - `docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`
  - `docs/operations/TRANSCRIPT_ARCHIVE_PROTOCOL.md`
  - `docs/delivery/ASSIGNMENT_ENVELOPE_TEMPLATE.md`
  - `docs/delivery/ENVELOPE_CONSUMPTION_CHECKLIST.md`
  - `docs/delivery/SCOPE_AUDIT_CHECKLIST.md`
-->

---
kind: hermes-handoff
role: <architect | implementer | controller | reviewer>
mode: <research | tracked-file-implementation | scope-audit | other>
controller: <controller-identity-or-coordinator-name>
ratifier: <ratifier-role-or-identity>
source_authorization_path: <repo-relative-or-absolute-path-to-recommended-prompt>
source_authorization_sha256: <64-lowercase-hex-or-tbd>
repo: <repo-name-or-repo-relative-root>
base_branch: <canonical-branch-typically-main>
base_commit: <full-commit-sha-or-tbd>
allowed_paths_count: <integer-or-tbd>
allowed_paths_sha256: <64-lowercase-hex-or-tbd>
stop_line: <exact-stop-line-the-implementer-pane-must-emit>
---

# Handoff: <one-line-title>

Role: <role-restated-from-front-matter>
Repo: <repo-restated>
Mode: <mode-restated>

## 1. Source authorization

Source authorized `<controller>` to use this prompt file:

```text
<source_authorization_path-restated>
```

Expected and verified Source prompt SHA256:

```text
<source_authorization_sha256-restated>
```

When the handoff is preceded by an architect research handoff or by
a prior batch's report, cite the predecessor handoff and its expected
transcript SHA256:

```text
<predecessor-handoff-path-or-none>
```

```text
<predecessor-transcript-sha256-or-none>
```

## 2. Current Git state observed before handoff

```text
branch: <branch>
HEAD: <commit-sha>
origin/<base_branch>: <commit-sha>
HEAD tree: <tree-sha>
origin/<base_branch> tree: <tree-sha>
HEAD tree equals origin/<base_branch> tree: <true | false>
status:
<short-status-output>
```

State explicitly if the local branch is ahead/behind origin and why.

## 3. Controller / implementer boundary

State which seat the implementer pane is in, and what the controller
is and is not authorized to do under this batch. Reference
[`docs/operations/CONTROLLER_BOUNDARY_POLICY.md`](../../../docs/operations/CONTROLLER_BOUNDARY_POLICY.md).

## 4. Objective

Bulleted, ordered list of the substantive outcomes the implementer
pane is expected to produce under this envelope.

## 5. Authorized path manifest

```text
ALLOWED_PATHS_COUNT=<integer>
ALLOWED_PATHS_SHA256=<64-lowercase-hex>
```

```text
<path-1>
<path-2>
...
```

Normalize exactly as: sorted unique UTF-8 path lines, LF line
endings, one trailing newline, no blank lines. The implementer
recomputes this from the fenced block on receipt; mismatch is a
halt.

Suggested recomputation command:

```bash
python3 - <<'PY'
from pathlib import Path
import hashlib
text = Path('<absolute-path-to-this-handoff>').read_text()
start = text.index('```text\n', text.index('ALLOWED_PATHS_SHA256=')) + len('```text\n')
end = text.index('```', start)
paths = [line for line in text[start:end].splitlines() if line]
norm = '\n'.join(sorted(set(paths))) + '\n'
print('count=', len(paths), sep='')
print('unique_count=', len(set(paths)), sep='')
print('sha256=', hashlib.sha256(norm.encode('utf-8')).hexdigest(), sep='')
PY
```

## 6. Forbidden surfaces and operations

State the forbidden surfaces and forbidden operations by name. At
minimum the standing list from
[`docs/delivery/ASSIGNMENT_ENVELOPE_TEMPLATE.md`](../../../docs/delivery/ASSIGNMENT_ENVELOPE_TEMPLATE.md)
§c.6 applies (`.github/`, `CODEOWNERS`, `specs/`, `tenants/`,
canonical `docs/` subtrees, deploy automation, repo settings, secrets).
Restate forbidden mechanics: `git add`, `git commit`, `git push`,
`gh pr` mutation, merge, branch deletion, worktree removal,
force-push, history rewrite, hook bypass, signing bypass, stash
mutation, deploy action, external-tracker mutation.

## 7. Implementation guidance

Optional but recommended. One short paragraph per artifact named in
the manifest, describing the file's purpose and the content smoke
criteria it must satisfy. Mirror conventions in adjacent files in
the same directory.

## 8. Required validation evidence

Enumerate the exact commands the implementer pane MUST run before
the stop line, with expected exit codes and salient output. Common
shapes (invoke the validator as `${CE_VALIDATOR_PYTHON:-python}`; set
`CE_VALIDATOR_PYTHON` for lane worktrees that have no local `.venv` —
see [`validators/README.md`](../../../validators/README.md), creator-engine#82):

```bash
PYTHONPATH=validators "${CE_VALIDATOR_PYTHON:-python}" -m creator_engine_validator --list-checks
PYTHONPATH=validators "${CE_VALIDATOR_PYTHON:-python}" -m creator_engine_validator check examples/well-formed/
PYTHONPATH=validators "${CE_VALIDATOR_PYTHON:-python}" -m creator_engine_validator check examples/malformed/
git diff --check
```

State for each command: expected exit code, what counts as success
(e.g., "malformed examples MUST exit non-zero with the expected
error class"), and whether the implementer may proceed past failure.

## 9. Report-back format and stop line

At completion the implementer reports:

1. Manifest preflight count/SHA result.
2. Files created / amended.
3. Summary of implemented behavior.
4. Validation commands with exit codes and salient output.
5. Final changed-file manifest count/SHA result.
6. Confirmation of no staged files, no commits, no pushes, no PR /
   GitHub / repo-setting mutation.
7. Any caveats / blockers.
8. The exact stop line below.

### Stop line

End the final response with exactly:

```text
<stop-line-restated-from-front-matter>
```

If blocked before implementation or validation cannot be completed,
end with exactly:

```text
<BLOCKED-stop-line>
```

## 10. Transcript archive

On reaching the stop line, the controller archives the implementer
pane's transcript per
[`docs/operations/TRANSCRIPT_ARCHIVE_PROTOCOL.md`](../../../docs/operations/TRANSCRIPT_ARCHIVE_PROTOCOL.md)
§d at the path shape:

```text
.hermes/transcripts/<UTC-timestamp>-<batch-slug>-<role>-pane-%<pane-id>.txt
```

The expected byte-level SHA256 of the archive is recorded back into
this handoff after close. The verifier recomputes that SHA256 to
confirm non-tampering.
