# ce-ops#214 PR-open governance scaffold

- Added the required `- **Declared work class:**` line to the forge PR-open
  body by default, with an optional caller-provided work class for computed
  G5 floor integration.
- Added PR-open body guidance for the per-branch path manifest carrier and
  changelog fragment so authors see the expected `.ce/` carrier files before
  opening or marking a PR ready.
- Clarified that callers should pass a `declared_work_class` derived from
  `verify-work-sizing-floor` / the computed G5 floor when available; the helper
  default is only a valid conservative scaffold fallback.
- Covered the scaffold and invalid work-class refusal path in the
  `open_change` unit tests.
