# ce-ops#243 contained-seat review transport deputy

- Added a contained-seat PR review submission seam that accepts only
  `COMMENT` and `REQUEST_CHANGES` review events, routes the request through the
  transport-deputy credential-injection proxy, and executes the trusted `gh api`
  transport outside the seat sandbox with a JIT scoped token.
- The path fails closed without an injected credential, keeps token material out
  of worker env/argv/audit records, and refuses `APPROVE` before minting so
  approval-wall capability markers remain controller-only.
