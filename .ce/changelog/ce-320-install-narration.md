---
slug: ce-320-install-narration
date: 2026-07-02
kind: docs
scope: agent-native install (docs/llms-install.md §0, docs/index.html)
issue: ce-ops#320
---

**Newcomer-clean narration for the agent-native install's §0 verification.**

The agent-native install ("paste into your coding agent") asked an assisting
agent to walk a newcomer through six expert-grade shell steps (curl / sed /
base64 -d / `ssh-keygen -Y verify` / DNS-TXT reconciliation) to verify the
install spec's signature. Narrated line-by-line, that reads as opaque, scary
shell noise to someone who isn't a security engineer.

Adds explicit narration instructions to `docs/llms-install.md` §0: run the
verification ceremony silently, then surface exactly one confirmation line on
success (`✓ verified CE's signed install spec against its published key
(ce-root-v1)`), or hard-stop with a plain-language failure message on any
other outcome — no troubleshooting or working around a failed verification.
Every verification command is unchanged byte-for-byte (including the three
principal-position strings `release_publish.py` parses back out of the
recipe); this is a narration/UX change only, not a weakening, reordering, or
removal of any verification step.

Reworded `docs/index.html`'s agent-native paste prompt (`#agentPrompt`) to
lead with the same plain-language provenance promise and quiet-verification
instruction, matching §0.

Because the spec's prose changed, its canonical bytes changed, so the
currently-embedded SSHSIG no longer verifies. `signature.value` and
`signature.content_sha256` in `docs/llms-install.md` need a controller-run
re-sign ceremony with the offline `ce-root-v1` key before merge (see the
ceremony plan handed to the controller; same class of follow-up as the prior
`ce-l1-install-doc-fix` re-sign, ce-ops#358).
