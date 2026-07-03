## Tenant Record Schema

- Added the `tenant-record` schema with closed-object validation for tenant
  identity, credential references, confidentiality posture, issue venue, fleet
  allocation, and governance ratification fields.
- Added the `tenant_record` validator check, a fictional well-formed tenant
  example, and focused unit coverage for required sections, pointer-only
  credential refs, unknown keys, enum failures, and ratification digest shape.
