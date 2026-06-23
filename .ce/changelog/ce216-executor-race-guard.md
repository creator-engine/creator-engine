# ce-ops#216 Unit 3 - Integrator executor race guard

- Added a v3 forge integrator executor that consumes Unit 1 repair-needed
  events and Unit 2 deterministic resolver output, while keeping write/push
  authority behind an injected adapter.
- The executor refuses unresolved, semantic, or content-less resolver results
  before any write-authority call, re-checks PR head and base SHA before write,
  and re-checks both again before push/requeue.
- Executor results are structured and secret-free, reporting applied paths,
  push/requeue state, refusal reason, and redacted evidence.
