---
slug: ce-481-signing-deputy-design
date: 2026-07-06
kind: story
scope: release-signing
issue: ce-ops#481
---

**Design SSHSIG signing deputy for ce-root-v1 custody.**

Adds a design for moving `ce-root-v1` private-key custody behind a constrained
SSHSIG-aware signing deputy, with OpenBao as the preferred backend and a
dedicated `ce-signer` OS-user bridge if OpenBao recovery blocks. The design
binds each signing act to canonical release hashes, install-spec content SHA,
release id, ratification ref, and a short-lived single-use Operator co-sign
artifact minted off controller hosts.

Round-2 revision clarifies per-request short-TTL backend authorization,
break-glass escalation after three failed ceremony attempts, deputy-compromise
response, Operator-controlled co-sign verification, and hash-check ordering for
referenced canonical bytes.
