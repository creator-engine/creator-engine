---
slug: ce228-cred-injection-proxy
date: 2026-06-25
kind: added
scope: credential injection proxy
issue: ce-ops#228
work_class: story
---

Adds a contained-agent credential-injection proxy that evaluates the
transport-deputy policy before minting, refuses without side effects on deny,
and injects minted scoped credentials only into the trusted outbound transport
request. Worker launch env/argv, policy metadata, and durable audit records stay
token-free and value-free.
