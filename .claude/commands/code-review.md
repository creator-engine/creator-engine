---
description: Self-fire a fresh-context CE reviewer before PR open or merge.
argument-hint: "<pr-number-or-branch/ref>"
allowed-tools: Task, Bash(git status:*), Bash(git diff:*), Bash(git rev-parse:*), Bash(gh pr view:*), Bash(gh api:*)
---

# Code Review

Use this command as the self-fire reviewer wrapper before opening a PR and
again before merge. It must use the committed reviewer role at
`.claude/agents/reviewer.md` and must not broaden that role.

1. Start a fresh-context `Task` with `subagent_type: reviewer`. Give it only
   the PR number or branch/ref, the base/head refs, and the instruction to
   inspect the diff, tests, manifest, and governance evidence read-only.
2. Ask the reviewer worker for a strict reviewer-terminal v2 JSON object plus one reviewer verdict:
   `COMMENT` when no blocking defect is proven, or `REQUEST_CHANGES` when a
   blocking defect, regression, policy violation, or missing required evidence
   remains. If the worker reports no blocking findings using approval wording,
   convert that to `COMMENT`; this wrapper never emits approval.
3. Parse the terminal and use the trusted receipt-bound review-submission
   transport. It must reject prose, v1, `Verified: none`, empty verification,
   count-only verdicts, `CANNOT_REVIEW`, and `BLOCKED` before any source-host
   write. Do not use raw `gh api`, `gh pr review`, curl, GraphQL, stdin, or file
   payloads to bypass receipt binding. The transport renders the canonical body:

   ```json
   {
     "event": "COMMENT | REQUEST_CHANGES",
     "body": "<reviewer evidence>",
     "commit_id": "<current PR head sha>"
   }
   ```

   The parser-issued single-use receipt binds this exact event/body/repo/PR/head
   and must be consumed before credential minting or transport.
4. Refuse and report a wiring error if the requested event is anything other
   than `COMMENT` or `REQUEST_CHANGES`, if no PR number/head SHA is available
   for posting, or if posting would require reviewer-worker credentials.

Do not use the approval mode of `gh pr review`, do not submit an approval
review event, and do not treat this self-fired reviewer evidence as the
independent approval gate for merge.
