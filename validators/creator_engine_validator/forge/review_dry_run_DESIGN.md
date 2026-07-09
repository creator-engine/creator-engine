# Review Dry-Run Design

## Purpose
The dry-run layer observes the path from "PR opened" to "reviewer detected"
without GitHub writes. It gives the controller a feed for validating reviewer
routing before promoting the existing review-pickup daemon to live `--apply`.

## Architecture
`forge.review_dry_run` wraps `forge.review_pickup.poll_review_pickup` with
`dry_run=True` and `apply=False`. It reuses the established poller decisions,
then adds an Operator-held gate and a named JSONL feed.

## Operator-Held Gate
The gate checks a hold label, defaulting to `awaiting-operator`, and an optional
held-list file. Label read failures are advisory and fail open because the
dry-run path never writes; held-list entries match either `owner/repo#N` or a
bare PR number.

## JSONL Feed
The feed is append-only, one line per PR per pass. `WOULD_ASSIGN` records show
which reviewer would be requested in apply mode; `WOULD_SKIP` records show PRs
excluded by the Operator-held gate or by review-pickup's internal skip reasons.
The controller consumes the feed offline.

## Slice 2 Hook
Slice 2 will add a `cev3 review-dry-run` subcommand that drives
`run_dry_run_loop` from the CLI and connects to the existing `gate-daemons.env`
token path.
