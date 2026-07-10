# RESUME STATE - CE-DEV-2 - 2026-07-07T1006Z

Read first on resume:
1. `AGENTS.md`
2. `.ce/state/research/ORCHESTRATOR_HANDOFF_PACKAGE_20260628.md`
3. `.ce/state/research/RESUME_STATE_CE_DEV2_NIGHTARC_20260707T0900Z.md`
4. this file

Correction still applies:
- Ignore/retract all PRDv2.1/html_prdv2 work in this repo.
- Do not resume or dispatch PRDv2.1/html_prdv2 here.

## Controller hard stop

Repo `AGENTS.md` says all agents must NEVER approve or merge PRs. The handoff
says the controller holds the merge gate, but this is in conflict. I have not
submitted GitHub approvals, merges, queue/enqueue, or PR comments. #876 and
#878 local review evidence can only become GitHub approval after operator/policy
resolves this conflict.

## Current open PR board

- #878 `feat: seed shaping from PRD context`
  - head `846af99a0c9f5320da9bc96d808846213e62b1c0`
  - GitHub checks green; reviewDecision still `CHANGES_REQUESTED`
  - dev-3 reviewer active now:
    worker `019f3c07-719f-7f70-a926-7f4b63d61577` (Lovelace)
  - Brief:
    `.ce/briefs/dev3-review-pr878-current-20260707.md`
    sha `525a074b2cddfed8de5817eac28a8b21e3fab68a833c722325e979a48650484e`
  - dev-3 verified brief hash and exact head before spawn.
  - Need poll for `APPROVE #878 ...` / `REQUEST_CHANGES #878 ...` / `BLOCKED`.

- #877 `docs: add canonical CE journey guides`
  - GitHub head still `ee1647bc8e1064fec0721b0bb21c80a3093e0693`
  - GitHub Validate red at old pushed head. Root cause from CI logs:
    branch lacked `verify-harness-promotion-matrix` CLI subcommand after main
    advanced through #880/#875.
  - dev-1 worker active now:
    worker `019f3bfe-e729-7e10-b3ce-0de9043ae965` (Russell)
  - Brief:
    `.ce/briefs/dev1-pr877-current-main-refresh-20260707.md`
    sha `cd84c987fe14342674ed07392e54b3aa6e5161c12c2a917c6297f2163e69bfb1`
  - Direct worktree inspection showed:
    - worktree `/home/ce-dev-1/worktrees/ce-485-canonical-journey-doc-pair`
    - local head `05e1517c8e1573e86e5ce5f53cc2c7a7670ca43d`
    - merge-base with origin/main and origin/main both
      `faf9307d3d178caba240a4da3bbd588d79ccf067`
    - status `## ce-485-canonical-journey-doc-pair...origin/main [ahead 8]`
    - full validate-pr process alive under `.venv-test/bin/python -m creator_engine_validator.ce_cli validate-pr`
  - Need wait for READY/BLOCKED. If READY, verify remote branch, then wait for
    GitHub checks and route independent review (not dev-1).

- #876 `feat(cli): teach CE journey next steps`
  - head `e45088ecc6afbe2b1782c28ed438cfb77df808e3`
  - GitHub checks green; reviewDecision still `CHANGES_REQUESTED`
  - dev-3 returned local `APPROVE` earlier:
    exact head matched, checks green, path manifest 12 paths hash
    `a54b729539a129c8bdf12820d2cec614a58fb79904784e97fe8f2566b47044eb`,
    `git diff --check` passed.
  - Ready-to-gate only after approval/merge hard-stop conflict is resolved.

- #864 `feat(launch): in-launcher reviewer-authority envelope minting`
  - GitHub head still `d74a18b71b963c90e8d6e2e78c8e9364ffe17a81`, Validate red.
  - Previous dev-4 r2 worker produced contained commit
    `9bbff9037f07a4831b8cdb4e298abfac7652ecc0` but blocked due missing final
    full preflight evidence.
  - dev-4 validation/export worker active now:
    worker `019f3bfe-590b-7133-b662-98bf3955bde4`
  - Brief:
    `.ce/briefs/dev4-pr864-export-validate-current-fix-20260707.md`
    sha `2bcec2fc44c7c5410699c7c001c83853d69b4c861ad71fb86c91b0c12819d96c`
  - Contained worktree `/var/tmp/ce-426-g11-reviewer-authority-minting`
    had branch head `9bbff903` and clean status when worker started.
  - Full validate-pr process is alive in `ce-dgx-codex`:
    `python -m creator_engine_validator.ce_cli validate-pr --repo-root .`
  - Need wait for READY/BLOCKED. If READY, import/verify bundle, harvest/push
    #864 branch, then wait for GitHub checks and route independent review.

## Active seat inspection commands

dev-1:
`ssh dev1 'tmux capture-pane -p -S -140 -t ce-dev1-orchestrator:2.0'`

dev-3:
`ssh dev1 'sudo docker exec -e HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock ce-vps-codex herdr pane read w1:p1 --lines 140'`

dev-4:
`sudo docker exec -e HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock ce-dgx-codex herdr pane read w1:p1 --lines 140`

PR board:
`GH_TOKEN=${GH_TOKEN:-$(cat ~/.ce-keys/ce-dev-2.pat 2>/dev/null || true)} gh pr list --repo creator-engine/creator-engine --state open --limit 20 --json number,title,headRefName,headRefOid,mergeStateStatus,reviewDecision,statusCheckRollup`
