---
slug: ce-republish-020-rootv1
ticket: ce-ops#198
kind: changed
scope: re-publish signed 0.2.0 release (ce-root-v1) incl. ce brain init
---

Re-publishes the signed `0.2.0` release mirror at `docs/downloads/0.2.0/` built from
current `main` (so it now includes `ce brain init` #206, the launch-leg fix #205, and the
`--signing-key-id` flag #352). The install spec `llms-install.md` is re-signed with the
**`ce-root-v1`** trust anchor (the primary Fork-A root, held on the controller host) via
`ssh-keygen -Y sign -n ce-spec-v1`; `signature.key_id` is `ce-root-v1`. The brownfield
scanner mirror (`downloads/0.2.0/scanners/`) is preserved untouched. First step of the
fleet-retirement clean-install program: dev-4 installs this release.
