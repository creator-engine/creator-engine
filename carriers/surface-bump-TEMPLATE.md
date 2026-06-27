---
surface: "codex"
from_version: "0.141.0"
to_version: "0.142.0"
from_digest: "sha256-or-commit-hash-of-old-version"
to_digest: "sha256-or-commit-hash-of-new-version"
changelog_summary: "Brief human-readable summary of relevant changes."
cve_check:
  status: "pass" # "pass" | "fail"
  notes: "Record CVE sources checked, findings, and any mitigations."
vendor_capability_grounding: "Reference [[verify-vendor-capability-vs-our-wiring]] and ground capability claims in current vendor documentation."
canary_seat: "seat-name"
ratified_by: "operator-identity"
ratified_at: "YYYY-MM-DDTHH:MM:SSZ"
---

# Surface Bump Carrier

Real surface-bump carriers are named:

`carriers/surface-bump-<surface-name>-<to_version>.md`

Copy this template for each surface bump and fill every field before opening the manifest-bump PR.
