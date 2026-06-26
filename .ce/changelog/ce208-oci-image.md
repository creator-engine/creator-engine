---
slug: ce208-oci-image
date: 2026-06-26
kind: added
scope: OCI image for CE CLI and validator wheel
issue: ce-ops#208
---

Added a portable OCI image recipe that builds the CE validator wheel from this
checkout, installs it offline from the repo wheelhouse, and exposes `ce` and
`creator-engine-validator` under a non-root runtime user.
