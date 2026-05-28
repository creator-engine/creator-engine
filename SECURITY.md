# Security Policy

Creator Engine is a pre-1.0 governance substrate. Security and privacy
are constitutional design constraints, not afterthoughts (see
[`docs/security/SECURITY_MODEL.md`](./docs/security/SECURITY_MODEL.md)),
and the project operates under an Operator-ratified governance model
(see [`GOVERNANCE.md`](./GOVERNANCE.md)).

## Supported versions

Creator Engine has not reached v1.0. There is no long-term-support
branch. The default branch (`main`) is the only version that receives
security fixes. Pre-1.0 spec/plan/tasks artifacts and the offline
validator may change without backward compatibility guarantees.

## Reporting a vulnerability

Please report suspected vulnerabilities **privately**. Do **not** open
public GitHub issues, public pull requests, or other public discussions
that include reproduction details, exploit payloads, or sensitive
identifiers for any suspected vulnerability.

- Preferred channel: email
  [`ubuntuaws745+security@gmail.com`](mailto:ubuntuaws745+security@gmail.com).
  This is the dedicated private security contact for Creator Engine.
  Do not post vulnerability details, exploit payloads, or sensitive
  identifiers in public GitHub issues, pull requests, or any other
  public discussion — use this private contact instead.

When reporting, please include:

- A short description of the issue and the affected component or file
  path.
- Reproduction steps or a minimal proof of concept where safe to share
  privately.
- The version, commit SHA, or branch you observed the issue on.
- Any known mitigations or workarounds.
- Whether you would like to be credited in any future advisory.

Please give maintainers a reasonable window to investigate and respond
before any public disclosure. We aim to acknowledge new reports
promptly and to coordinate disclosure timing with the reporter.

## What is in scope

In scope for a security report:

- Defects in the offline validator (`validators/`) that produce false
  positives or false negatives for the redaction gate, identity
  schema, mutation-class taxonomy, or LIMITLESS generic-path scan in
  ways that could mask a governance failure.
- Schema, template, or example bugs that could cause valid governance
  artifacts (attestations, ratifications, redactions) to be silently
  accepted in invalid form.
- Documentation that materially misrepresents the security model or
  the ratification boundaries (`docs/security/SECURITY_MODEL.md`,
  `docs/governance/`).
- Sensitive content (credentials, tenant secrets, personal data)
  inadvertently committed to this repository.

Out of scope:

- Hypothetical attacks against features that v0.1 has not implemented
  (for example, public-export or NDA-visible-corpus workflows are not
  part of v0.1 and will require their own redaction gate definitions
  before any future spec introduces them).
- Findings that depend on running the substrate in configurations
  the constitution or governance docs explicitly forbid.

## Public-issue and pull-request etiquette

Public issues and pull requests **must not** include vulnerability
details, exploit payloads, secrets, tenant-identifying data, or any
content that violates the redaction gate. Maintainers will close or
redact such content as needed. If you are unsure whether something is
sensitive, treat it as sensitive and use the private reporting channel
above.

## Related references

- [`docs/security/SECURITY_MODEL.md`](./docs/security/SECURITY_MODEL.md)
  — canonical security model summary, redaction gate, secrets policy.
- [`.specify/memory/constitution.md`](./.specify/memory/constitution.md)
  — constitution, including Principle XII (security and privacy as
  design constraints).
- [`docs/governance/MUTATION_CLASS_MODEL.md`](./docs/governance/MUTATION_CLASS_MODEL.md)
  — privileged mutation classes (including `security`).
- [`GOVERNANCE.md`](./GOVERNANCE.md) — ratification and authority
  on-ramp.
