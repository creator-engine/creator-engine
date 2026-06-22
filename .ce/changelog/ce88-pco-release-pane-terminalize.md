---
slug: ce88-pco-release-pane-terminalize
date: 2026-06-22
kind: fixed
scope: substrate / pco-release (Pane Registry records)
issue: creator-engine#88
---

Terminalize matching Pane Registry records when `pco-release` closes a lapsed
claim.

The release path now maps `--release-reason lapsed` to terminal pane state
`status: closed` with `close_reason: lapsed`, validates the rewritten pane
record, and refreshes `claim_record_sha256` when that field is present.

Regression coverage exercises the CLI lapsed-release path so future changes
keep the Active-Work claim release and Pane Registry terminalization behavior
in sync.
