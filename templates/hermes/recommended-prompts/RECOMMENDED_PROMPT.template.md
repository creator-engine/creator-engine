# Hermes Recommended-Prompt Template

<!--
This file is the canonical template for a Source-authored / Source-
ratified recommended prompt. The controller fills this template into
an instance-local file under
`.hermes/recommended-prompts/<UTC-timestamp>-<batch-slug>-<role>.md`
and (a) cites the filled file's path + byte-level SHA256 from the
implementer-facing handoff (see
`templates/hermes/handoffs/HANDOFF.template.md` §1), and (b) relays
the filled file pointer-only to the visible pane per
`templates/hermes/visible-pane-pointer-prompt.template.md`.

The required front matter and §1–§7 below are validated by the
Creator Engine validator's `handoff_schema` check (see
`schemas/recommended-prompt.schema.yaml`) and the
`path_manifest_fidelity` check.

Upstream Creator Engine MUST NOT track an instance's filled-in copy.
Keep `.hermes/` ignored. Do not commit live PR numbers, absolute
local paths, runtime pane identifiers, or instance-specific
secrets / tokens.

See also:
  - `docs/operations/CONTROLLER_BOUNDARY_POLICY.md`
  - `docs/operations/NO_COPY_PASTE_PATTERN.md`
  - `docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`
  - `docs/delivery/ASSIGNMENT_ENVELOPE_TEMPLATE.md`
-->

---
kind: hermes-recommended-prompt
role: <architect | implementer | controller | reviewer>
ratifier: <ratifier-role-or-identity>
controller: <controller-identity-or-coordinator-name>
authorized_actor: <human-readable-actor-description>
repo: <repo-name-or-repo-relative-root>
base_branch: <canonical-branch-typically-main>
base_commit: <full-commit-sha-or-tbd>
allowed_paths_count: <integer-or-tbd>
allowed_paths_sha256: <64-lowercase-hex-or-tbd>
stop_line: <exact-stop-line-the-implementer-pane-must-emit>
---

# Recommended Prompt: <one-line-title>

## 1. Source ratification

Restate the Source-ratification record that authorizes this prompt.
Include:

- The ratifier identity (typically `source`).
- The ratification scope (what mutation classes, what paths, what
  prohibited surfaces, what mechanics are authorized).
- Any explicit named waivers in effect.

## 2. Roles in scope

Identify the authorized actor (consumer pane), the controller, the
architect (if any), and the Source role. Cite
[`docs/operations/CONTROLLER_BOUNDARY_POLICY.md`](../../../docs/operations/CONTROLLER_BOUNDARY_POLICY.md)
for the role split.

## 3. Mutation classes

Enumerate the anticipated Feature 001 mutation classes the batch
authorizes and the dominant class. Privileged classes (`deploy`,
`governance`, `identity`, `security`, `attestation`, `redaction`)
trigger Feature 001 FR-008 and require Source ratification.

## 4. Authorized path manifest

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
endings, one trailing newline, no blank lines.

## 5. Forbidden surfaces and operations

Restate, by name, the standing forbidden-surface list (`.github/`,
`CODEOWNERS`, `specs/`, `tenants/`, canonical `docs/` subtrees,
deploy automation, repo settings, secrets) and the forbidden Git /
GitHub mechanics (`git add`, `git commit`, `git push`, `gh pr`
mutation, merge, branch deletion, worktree removal, force-push,
history rewrite, hook bypass, signing bypass, stash mutation,
deploy action, external-tracker mutation).

## 6. Implementation, validation, and report-back

Cite the implementation guidance, validation commands, and
report-back format the consumer follows. These typically mirror the
handoff §7–§9 fields.

## 7. Stop line

End the consumer's final response with exactly:

```text
<stop-line-restated-from-front-matter>
```

The consumer MUST NOT cross the stop line unless Source separately
ratifies the mechanics in a follow-up envelope clause.
