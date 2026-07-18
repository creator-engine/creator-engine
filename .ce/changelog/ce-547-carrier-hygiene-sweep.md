---
slug: ce-547-carrier-hygiene-sweep
date: 2026-07-18
kind: fix
scope: dead carrier-manifest hygiene sweep
issue: ce-ops#547
work_class: S
---

**fix(carrier): ce carrier gc sweeps dead carrier manifests**

Adds `ce carrier gc`, which enumerates every carrier under `.ce/pr-manifests/`,
reads its slug (frontmatter `slug:`, falling back to the filename stem), and
classifies it DEAD when no local branch, no remote-tracking `origin` ref, and
not the current branch matches the slug. The sweep is dry-run by default and
reports each dead carrier with the refs it checked; `--apply` removes them. It
never touches live carriers and never deletes a carrier whose slug cannot be
parsed (reported UNPARSEABLE). Liveness reads only local refs — it never
contacts `origin` — so operators should `git fetch --prune` first for the
remote-tracking view to reflect deleted upstream branches.

Also purges the two long-dead carriers `ce38-work-claims` and
`ce57-datebomb-fix`, whose branches are gone, and drops their now-stale
confidentiality-allowlist entries.
