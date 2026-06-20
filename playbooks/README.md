# CE Playbooks

This directory contains reusable Creator Engine playbooks. A playbook is a
validated directory with a human README, `workflow.ce.yml`, an envelope
template, stage briefs, and a harness contract.

## How A Seat Consumes A Playbook

1. Select the playbook from the index below.
2. Read that playbook's `README.md`, `workflow.ce.yml`, and `harness.md`.
3. Copy `envelope.template.yml` into the dispatch artifact and fill only the
   ticket-specific scope, authority, target, evidence, and reviewer fields.
4. Dispatch one stage at a time by giving the target seat the matching
   `briefs/<stage>.md`.
5. Stop at any halt condition in `harness.md`; do not improvise around missing
   credentials, 2FA, sudo prompts, broken authority, or dead-end substrates.
6. Close out with the playbook's stated DoD outputs and validator evidence.

## Index

| Playbook | Type | Purpose |
| --- | --- | --- |
| [computer-use-ticket](computer-use-ticket/) | workflow | Authenticated-browser ticket loop for bounded UI work. |
| [reviewer](reviewer/) | role-action | Full reviews and scoped re-reviews, including ce-ops#151 re-review branches. |
| [author](author/) | role-action | Base-only refresh and review-addressing loops for PR authors. |
| [controller](controller/) | role-action | Controller dispatch, merge-gate, seat-refresh, and courier forge operations. |
