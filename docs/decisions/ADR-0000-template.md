---
# Template — copy to ADR-NNNN-<slug>.md and fill every field.
# Files ending in `-template.md` are skipped by the `decision_record` check.
kind: decision-record
record_type: adr
schema_version: "1"
id: ADR-0000
title: "<short noun-phrase title of the decision>"
status: proposed            # proposed | accepted | deprecated | superseded
date: 2026-01-01            # ISO date the decision was recorded
decision_makers: ["<owner>"]   # the owner stamp; ratifier must differ for privileged classes
consulted: []               # two-way communication trail (MADR)
informed: []                # one-way communication trail (MADR)
review_by: 2027-01-01       # REQUIRED freshness horizon — decisions rot
mutation_class: docs        # blast-radius axis; privileged classes raise the ratification bar
evidence_refs:              # REQUIRED non-empty; every ref carries a citation tag
  - kind: doc
    ref: "<path-or-url>"
    tag: "<cite-tag>"
# policy_sha: "<64-hex pin of the governing policy/mandate document>"
# ratification:             # REQUIRED once status: accepted (human event, never agent-promoted)
#   ratified_by: "<the OTHER peer for privileged classes>"
#   ratified_at: 2026-01-01
#   ratification_prompt_sha: "<64-hex>"
# crosswalk:
#   supersedes: []
#   superseded_by: ""       # REQUIRED + resolvable once status: superseded
#   informs: []
---

# <title>

## Context and Problem Statement

<What is the issue we are deciding? Why now? 2–5 sentences.>

## Decision Drivers

- <driver 1>
- <driver 2>

## Considered Options

1. <option 1>
2. <option 2>

## Decision Outcome

Chosen option: **<option N>**, because <justification grounded in the
decision drivers and the cited evidence (`evidence_refs` tags)>.

## Consequences

- Good: <positive consequence>
- Bad: <accepted trade-off>
