---
slug: resign-llms-install-spec
date: 2026-06-30
kind: fix
scope: install-spec-signing
issue: ce-ops#358
---

**Re-sign llms-install.md install spec with ce-root-v1.**

PR #654 changed the install spec body, invalidating its SSHSIG, and shipped the placeholder value <RESIGN-REQUIRED-ce-root-v1> to main and the live published spec, so the public installer fail-closed for everyone (signature_refused). Re-signs the current spec canonical bytes with the offline ce-root-v1 trust root (Operator-authorized; the one non-delegable act). content_sha256 floor unchanged (already correct); only the signature value line changes. Verified through the real apply gate (ssh-ed25519 verifier vs pinned ce-root-v1): Good signature.
