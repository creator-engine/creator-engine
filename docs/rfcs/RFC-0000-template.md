---
# Template — copy to RFC-NNNN-<slug>.md and fill every field.
# Files ending in `-template.md` are skipped by the `decision_record` check.
kind: decision-record
record_type: rfc
schema_version: "1"
id: RFC-0000
title: "<short noun-phrase title of the motion>"
status: proposed            # proposed | accepted | deprecated | superseded
date: 2026-01-01
decision_makers: ["<proposer>"]
consulted: []
informed: []
review_by: 2027-01-01       # REQUIRED freshness horizon
mutation_class: schema      # blast-radius axis; privileged classes need both peers (§A.5)
evidence_refs:
  - kind: doc
    ref: "<path-or-url>"
    tag: "<cite-tag>"
disposition: merge          # merge | close | postpone — the explicit motion
fcp:
  opened_at: 2026-01-01     # the timed comment window (Rust uses 10 days)
  concerns: []              # blocking concerns: [{name, status: open|resolved}]
                            # the FCP cannot complete while any concern is open
# ratification:             # REQUIRED once status: accepted (human event)
#   ratified_by: "<the OTHER peer for privileged classes>"
#   ratified_at: 2026-01-01
#   ratification_prompt_sha: "<64-hex>"
# crosswalk:
#   supersedes: []          # losing drafts this RFC deterministically closes
#   superseded_by: ""
#   informs: []
---

# <title>

## Summary

<One paragraph: what is proposed and what changes if adopted.>

## Motivation

<Why this needs the RFC instrument: the disagreement or structural stake.>

## Guide-level explanation

<The proposal as you would explain it to a CE user/peer.>

## Drawbacks and alternatives

<What we give up; the competing drafts this converges or closes.>

## Final Comment Period log

<Concern-by-concern record mirroring `fcp.concerns`: who raised it, how it
was resolved (or why it blocks).>
