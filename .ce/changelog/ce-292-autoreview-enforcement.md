---
slug: ce-292-autoreview-enforcement
date: 2026-06-27
kind: fixed
scope: reviewer authority hook
issue: ce-ops#292
work_class: small
---

The reviewer-authority PreToolUse hook now treats raw `gh api` review
submissions carrying `event=APPROVE` as a restricted `pr_review` mechanic and
denies them even when a normal reviewer-authority envelope is present.
